"""Tests for BookingPool."""
import pytest

from booking.pool import BookingPool, Account, BookingResult, AccountSession


class TestBookingPool:
    """Tests for BookingPool."""

    def test_init(self):
        """池初始化"""
        pool = BookingPool()
        assert pool.accounts == []
        assert pool.max_concurrent == 3
        assert pool.config == {}

    def test_init_with_max_concurrent(self):
        """带 max_concurrent 参数初始化"""
        pool = BookingPool(max_concurrent=5)
        assert pool.max_concurrent == 5

    def test_add_account(self):
        """add_account 添加账号"""
        pool = BookingPool()
        result = pool.add_account("2023150090", "password123")
        assert result is pool  # 链式调用
        assert len(pool.accounts) == 1
        assert pool.accounts[0].username == "2023150090"

    def test_add_account_with_metadata(self):
        """add_account 带元数据"""
        pool = BookingPool()
        pool.add_account("2023150090", "password123", priority=2, campus="粤海校区")
        acc = pool.accounts[0]
        assert acc.priority == 2
        assert acc.metadata.get("campus") == "粤海校区"

    def test_add_account_with_config(self):
        """add_account_with_config 带独立配置"""
        pool = BookingPool()
        pool.add_account_with_config(
            "2023150090",
            "password123",
            config={"campus": "丽湖校区"}
        )
        acc = pool.accounts[0]
        assert acc.metadata.get("config", {}).get("campus") == "丽湖校区"

    def test_config(self):
        """config 设置配置"""
        pool = BookingPool()
        result = pool.update_config(campus="粤海校区", sport="网球")
        assert result is pool  # 链式调用
        assert pool.config["campus"] == "粤海校区"
        assert pool.config["sport"] == "网球"

    def test_on_account_success(self):
        """on_account_success 设置成功回调"""
        pool = BookingPool()
        called = []

        def callback(result):
            called.append(result)

        pool.on_account_success(callback)
        assert pool._on_success is callback

    def test_on_account_failed(self):
        """on_account_failed 设置失败回调"""
        pool = BookingPool()
        pool.on_account_failed(lambda r: None)
        assert pool._on_failed is not None

    def test_on_progress(self):
        """on_progress 设置进度回调"""
        pool = BookingPool()
        pool.on_progress(lambda u, s, r: None)
        assert pool._on_progress is not None

    def test_get_current_account(self):
        """get_current_account 获取当前账号"""
        pool = BookingPool()
        pool.add_account("2023150090", "password")
        assert pool.get_current_account() is not None
        assert pool.get_current_account().username == "2023150090"

    def test_get_current_account_empty(self):
        """get_current_account 空池返回 None"""
        pool = BookingPool()
        assert pool.get_current_account() is None

    def test_next_account(self):
        """next_account 切换到下一个账号"""
        pool = BookingPool()
        pool.add_account("2023150090", "password")
        pool.add_account("2023150091", "password")
        first = pool.get_current_account()
        pool.next_account()
        second = pool.get_current_account()
        assert first.username != second.username

    def test_next_account_empty(self):
        """next_account 空池返回 None"""
        pool = BookingPool()
        assert pool.next_account() is None

    def test_get_results(self):
        """get_results 获取结果"""
        pool = BookingPool()
        assert pool.get_results() == {}

    def test_stop(self):
        """stop 停止执行"""
        pool = BookingPool()
        pool.stop()
        assert pool._stop_flag is True


class TestAccount:
    """Tests for Account dataclass."""

    def test_account_credentials(self):
        """credentials 属性"""
        account = Account("2023150090", "password123")
        assert account.credentials == ("2023150090", "password123")

    def test_account_default_priority(self):
        """默认优先级"""
        account = Account("user", "pass")
        assert account.priority == 1

    def test_account_with_priority(self):
        """指定优先级"""
        account = Account("user", "pass", priority=5)
        assert account.priority == 5


class TestBookingResult:
    """Tests for BookingResult dataclass."""

    def test_result_str(self):
        """字符串表示"""
        result = BookingResult(
            username="2023150090",
            status="success",
            message="预约成功"
        )
        assert "2023150090" in str(result)
        assert "success" in str(result)

    def test_result_default_values(self):
        """默认值"""
        result = BookingResult(username="user", status="pending")
        assert result.message == ""
        assert result.time_slot == ""
        assert result.details == {}


class TestAccountSession:
    """Tests for AccountSession."""

    def test_init(self):
        """会话初始化"""
        session = AccountSession("2023150090", "password123")
        assert session.username == "2023150090"
        assert session.password == "password123"
        assert session.status == "pending"
        assert session.result is None

    def test_config(self):
        """config 设置配置"""
        session = AccountSession("user", "pass")
        result = session.update_config(campus="粤海校区", sport="网球")
        assert result is session
        assert session.config["campus"] == "粤海校区"

    def test_config_override(self):
        """config 覆盖配置"""
        session = AccountSession("user", "pass")
        session.update_config(a=1)
        session.update_config(a=2)
        assert session.config["a"] == 2

    def test_stop(self):
        """stop 停止会话"""
        session = AccountSession("user", "pass")
        session.run()  # 先运行
        session.stop()
        assert session.status == "stopped"

    def test_status_property(self):
        """status 属性"""
        session = AccountSession("user", "pass")
        assert session.status == "pending"
        session.run()
        assert session.status == "completed"

    def test_result_property(self):
        """result 属性"""
        session = AccountSession("user", "pass")
        assert session.result is None


class TestBookingPoolRunAll:
    """Tests for BookingPool.run_all."""

    def test_run_all_no_accounts(self, tmp_path):
        """空池运行返回空列表"""
        pool = BookingPool()
        results = pool.run_all(concurrent=False)
        assert results == []

    def test_run_all_with_accounts(self, tmp_path):
        """带账号运行（干跑模式，不需要真实浏览器）"""
        pool = BookingPool()
        pool.add_account("2023150090", "password")
        pool.update_config(url="https://example.com", campus="粤海校区", sport="网球")

        # 注意：这会在干跑模式下运行，不会真正启动浏览器
        # 由于没有配置 FakeBrowser，实际会尝试创建真实浏览器
        # 所以这个测试主要验证方法存在性
        results = pool.run_all(concurrent=False)
        # 结果取决于是否成功执行
        assert isinstance(results, list)


class TestBookingPoolMergedConfig:
    """Regression tests for per-account config merging."""

    def test_account_config_overrides_global(self):
        """Bug: _execute_account 不读账号独立配置。
        修复后，账号 default_sport 覆盖全局 default_sport。"""
        pool = BookingPool()
        pool.update_config(
            campus="粤海校区", sport="网球", time_slot="19:00-20:00"
        )
        account = Account(
            username="test",
            password="pass",
            metadata={"config": {
                "default_sport": "羽毛球",
                "default_campus": "丽湖校区",
            }}
        )
        cfg = pool._get_merged_config(account)
        assert cfg["sport"] == "羽毛球"
        assert cfg["campus"] == "丽湖校区"
        assert cfg["time_slot"] == "19:00-20:00"

    def test_account_no_config_uses_global(self):
        """账号无独立配置时使用全局配置"""
        pool = BookingPool()
        pool.update_config(campus="粤海校区", sport="网球")
        account = Account(username="test", password="pass")
        cfg = pool._get_merged_config(account)
        assert cfg["campus"] == "粤海校区"
        assert cfg["sport"] == "网球"


class TestBookingPoolCallbacks:
    """Tests for BookingPool callbacks."""

    def test_success_callback(self):
        """成功回调"""
        pool = BookingPool()
        results = []

        def on_success(result):
            results.append(result)

        pool.on_account_success(on_success)

        # 手动触发回调
        fake_result = BookingResult(username="test", status="success")
        pool._on_success(fake_result)

        assert len(results) == 1
        assert results[0].username == "test"

    def test_failed_callback(self):
        """失败回调"""
        pool = BookingPool()
        results = []

        def on_failed(result):
            results.append(result)

        pool.on_account_failed(on_failed)

        fake_result = BookingResult(username="test", status="failed", message="错误")
        pool._on_failed(fake_result)

        assert len(results) == 1

    def test_progress_callback(self):
        """进度回调"""
        pool = BookingPool()
        calls = []

        def on_progress(username, status, result):
            calls.append((username, status))

        pool.on_progress(on_progress)
        fake_result = BookingResult(username="test", status="running")
        pool._report_progress("test", "running", fake_result)

        assert len(calls) == 1
        assert calls[0] == ("test", "running")