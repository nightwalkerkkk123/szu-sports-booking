"""
多账号调度池 - 支持并发多账号预约
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("booking.pool")


@dataclass
class BookingResult:
    """预约结果"""

    username: str
    status: str  # success / failed / timeout / pending
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    time_slot: str = ""
    details: dict = field(default_factory=dict)

    def __str__(self):
        return f"[{self.username}] {self.status}: {self.message}"


@dataclass
class Account:
    """账号"""

    username: str
    password: str
    priority: int = 1
    metadata: dict = field(default_factory=dict)

    @property
    def credentials(self) -> tuple:
        return (self.username, self.password)


class BookingPool:
    """
    多账号调度池

    示例:
        pool = BookingPool(max_concurrent=2)
        pool.add_account("2023150090", "11282577")
        pool.add_account("2023150091", "password456")
        pool.config(campus="粤海校区", sport="网球", time_slot="19:00-20:00")
        result = pool.run_until_success()
    """

    def __init__(self, max_concurrent: int = 3, dry_run: bool = False, trace_id: str = None):
        self.accounts: list[Account] = []
        self.max_concurrent = max_concurrent
        self._dry_run = dry_run
        self._trace_id = trace_id
        self._config: dict = {}
        self.results: dict[str, BookingResult] = {}
        self._current_index = 0
        self._lock = threading.Lock()
        self._stop_flag = False

        # 回调函数
        self._on_success: Callable | None = None
        self._on_failed: Callable | None = None
        self._on_progress: Callable | None = None

    @property
    def config(self) -> dict:
        """获取配置属性"""
        return self._config

    def add_account(
        self, username: str, password: str, config: dict = None, **metadata
    ) -> "BookingPool":
        """添加账号

        参数:
            username: 学号
            password: 密码
            config: 该账号的独立预约配置（覆盖全局配置），如
                    {"campus": "丽湖校区", "sport": "羽毛球"}
            **metadata: 其他元数据（priority 等）
        """
        priority = metadata.pop("priority", 1)
        if config:
            metadata["config"] = config
        self.accounts.append(
            Account(username=username, password=password, priority=priority, metadata=metadata)
        )
        return self

    def _get_merged_config(self, account: Account) -> dict:
        """合并全局配置和账号独立配置（账号配置优先）

        config.yaml 中账号字段名为 default_campus 等，内部统一映射为 campus 等短名。
        """
        merged = dict(self._config)
        account_config = account.metadata.get("config", {})
        # 标准化 config.yaml 字段名到内部短名
        key_map = {
            "default_campus": "campus",
            "default_sport": "sport",
            "default_time_slot": "time_slot",
            "default_date_index": "date_index",
        }
        normalized = {key_map.get(k, k): v for k, v in account_config.items()}
        merged.update(normalized)
        return merged

    def update_config(self, **kwargs) -> "BookingPool":
        """更新全局配置（链式调用）"""
        self._config.update(kwargs)
        return self

    def add_account_with_config(
        self, username: str, password: str, config: dict = None, **metadata
    ) -> "BookingPool":
        """添加账号（带独立配置）"""
        account = Account(
            username=username,
            password=password,
            priority=metadata.pop("priority", 1),
            metadata={**metadata, "config": config or {}},
        )
        self.accounts.append(account)
        return self

    def on_account_success(self, callback: Callable) -> "BookingPool":
        """预约成功回调"""
        self._on_success = callback
        return self

    def on_account_failed(self, callback: Callable) -> "BookingPool":
        """预约失败回调"""
        self._on_failed = callback
        return self

    def on_progress(self, callback: Callable) -> "BookingPool":
        """进度回调"""
        self._on_progress = callback
        return self

    def run_all(self, concurrent: bool = True) -> list[BookingResult]:
        """
        并发运行所有账号

        参数:
            concurrent: 是否并发执行

        返回:
            List[BookingResult]: 所有账号的执行结果
        """
        if not self.accounts:
            print("错误: 没有添加任何账号")
            return []

        print(f"\n开始执行，共 {len(self.accounts)} 个账号")
        print("=" * 60)

        results = []
        if concurrent:
            # 并发执行
            threads = []
            for i, account in enumerate(self.accounts, 1):
                t = threading.Thread(target=self._run_account, args=(account, results, i))
                t.daemon = True
                t.start()
                threads.append(t)

            for t in threads:
                t.join()
        else:
            # 顺序执行
            for account in self.accounts:
                self._run_account(account, results)

        print("=" * 60)
        success_count = sum(1 for r in results if r.status == "success")
        print(f"执行完成，成功: {success_count}")
        for r in results:
            if r.status == "failed":
                print(f"  [X] {r.username}: {r.message}")
        print()

        return results

    def run_until_success(self, timeout: int = 300) -> BookingResult | None:
        """
        运行直到某个账号成功

        参数:
            timeout: 超时时间（秒）

        返回:
            Optional[BookingResult]: 成功的账号结果，没有则返回 None
        """
        if not self.accounts:
            print("错误: 没有添加任何账号")
            return None

        print(f"\n开始执行（直到成功），共 {len(self.accounts)} 个账号")
        print(f"超时时间: {timeout}秒")
        print("=" * 60)

        start_time = time.time()
        current_index = 0

        while time.time() - start_time < timeout:
            if self._stop_flag:
                print("收到停止信号")
                break

            # 按顺序选择账号
            account = self.accounts[current_index]
            print(f"\n尝试账号: {account.username}")

            result = self._execute_account(account)

            if result.status == "success":
                print(f"\n🎉 预约成功! 账号: {result.username}")
                self._report_progress(account.username, "success", result)
                if self._on_success:
                    self._on_success(result)
                return result

            self._report_progress(account.username, "failed", result)
            if self._on_failed:
                self._on_failed(result)

            # 切换到下一个账号
            current_index = (current_index + 1) % len(self.accounts)

            # 如果所有账号都尝试过了，等待一下再重试
            if current_index == 0:
                print("所有账号都尝试过，等待5秒后重试...")
                time.sleep(5)

        print("\n超时，所有账号都未能成功预约")
        return None

    def stop(self):
        """停止执行"""
        self._stop_flag = True

    def get_results(self) -> dict[str, BookingResult]:
        """获取所有结果"""
        return self.results

    def get_current_account(self) -> Account | None:
        """获取当前账号"""
        if self.accounts:
            return self.accounts[self._current_index % len(self.accounts)]
        return None

    def next_account(self) -> Account | None:
        """切换到下一个账号"""
        if self.accounts:
            self._current_index = (self._current_index + 1) % len(self.accounts)
            return self.accounts[self._current_index]
        return None

    def _run_account(self, account: Account, results: list[BookingResult], task_index: int = 1):
        """运行单个账号"""
        result = self._execute_account(account, task_index=task_index)
        results.append(result)

    def _execute_account(self, account: Account, task_index: int = 1) -> BookingResult:
        """执行单个账号的预约流程

        使用 BookingClient 执行实际的预约逻辑。
        """
        T = f"[任务{task_index}]"  # noqa: N806
        try:
            from .client import BookingClient
            from .selectors.slot_selector import SlotUnavailableError

            print(
                f"{T} 正在执行: {account.username} → {account.metadata.get('config', {}).get('default_sport', '?')}"
            )
            logger.info("开始执行账号", extra={"username": account.username, "task": task_index})

            # 创建 BookingClient
            client = BookingClient(use_fake_browser=self._dry_run, trace_id=self._trace_id)

            # _ensure_browser() 内部已处理 launch，无需再调用
            client._ensure_browser()

            # 获取配置（账号独立配置覆盖全局配置）
            cfg = self._get_merged_config(account)
            url = cfg.get("url")
            campus = cfg.get("campus")
            sport = cfg.get("sport")
            date_index = cfg.get("date_index", 0)
            time_slot = cfg.get("time_slot")

            # 打开预约页面
            client.open(url)
            client.wait(1)

            # 登录
            client.login(account.username, account.password)
            client.wait(1)

            # 选择校区
            try:
                client.select_campus(campus)
                client.wait(0.5)
            except Exception as e:
                return BookingResult(
                    username=account.username,
                    status="failed",
                    message=f"选择校区失败: {e}",
                    time_slot=time_slot,
                )

            # 选择项目
            try:
                client.select_sport(sport)
                client.wait(0.5)
            except Exception as e:
                return BookingResult(
                    username=account.username,
                    status="failed",
                    message=f"选择项目失败: {e}",
                    time_slot=time_slot,
                )

            # 选择日期
            try:
                client.select_date(date_index)
                client.wait(0.5)
            except Exception as e:
                return BookingResult(
                    username=account.username,
                    status="failed",
                    message=f"选择日期失败: {e}",
                    time_slot=time_slot,
                )

            # 选择时间段
            try:
                client.select_time_slot(time_slot)
                client.wait(0.5)
            except SlotUnavailableError as e:
                return BookingResult(
                    username=account.username,
                    status="failed",
                    message=f"时间段不可用: {e}",
                    time_slot=time_slot,
                )
            except Exception as e:
                return BookingResult(
                    username=account.username,
                    status="failed",
                    message=f"时间段选择失败: {e}",
                    time_slot=time_slot,
                )

            # 选择场地
            try:
                client.select_venue()
                client.wait(0.5)
            except SlotUnavailableError as e:
                return BookingResult(
                    username=account.username,
                    status="failed",
                    message=f"场地不可用: {e}",
                    time_slot=time_slot,
                )
            except Exception as e:
                return BookingResult(
                    username=account.username,
                    status="failed",
                    message=f"场地选择失败: {e}",
                    time_slot=time_slot,
                )

            # 确认预约
            try:
                confirmed = client.confirm()
            except Exception as e:
                return BookingResult(
                    username=account.username,
                    status="failed",
                    message=f"确认预约失败: {e}",
                    time_slot=time_slot,
                )

            client.wait(2)
            client.close()

            if confirmed:
                return BookingResult(
                    username=account.username,
                    status="success",
                    message="预约完成",
                    time_slot=time_slot,
                )
            else:
                return BookingResult(
                    username=account.username,
                    status="failed",
                    message="预约被拒绝或状态未知",
                    time_slot=time_slot,
                )
            return BookingResult(
                username=account.username,
                status="success",
                message="预约完成",
                details={"logged": True},
                time_slot=time_slot,
            )

        except SlotUnavailableError as e:
            return BookingResult(
                username=account.username,
                status="failed",
                message=f"时间段/场地不可用: {e}",
                time_slot=self.config.get("time_slot", ""),
            )
        except Exception as e:
            return BookingResult(
                username=account.username,
                status="failed",
                message=str(e),
                time_slot=self.config.get("time_slot", ""),
            )

    def _report_progress(self, username: str, status: str, result: BookingResult):
        """报告进度"""
        if self._on_progress:
            self._on_progress(username, status, result)

    def from_config_file(self, filepath: str) -> "BookingPool":
        """从配置文件加载"""
        import json

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # 加载账号
        for acc in data.get("accounts", []):
            self.add_account(acc["username"], acc["password"])

        # 加载全局配置
        if "global_config" in data:
            self._config.update(data["global_config"])

        return self

    def to_config_file(self, filepath: str):
        """保存配置到文件"""
        import json

        data = {
            "accounts": [
                {"username": acc.username, "password": acc.password} for acc in self.accounts
            ],
            "global_config": self._config,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class AccountSession:
    """
    单账号独立会话（可选的进程隔离方案）

    使用方法:
        session = AccountSession("2023150090", "11282577")
        session.config(campus="粤海校区", sport="网球", time_slot="19:00-20:00")
        result = session.run()
    """

    def __init__(self, username: str, password: str, session_id: str = None, dry_run: bool = False):
        self.username = username
        self.password = password
        self.session_id = session_id or f"session_{username}"
        self._dry_run = dry_run
        self._config = {}
        self._status = "pending"
        self._result = None

    @property
    def config(self) -> dict:
        """获取配置"""
        return self._config

    def update_config(self, **kwargs) -> "AccountSession":
        """更新配置"""
        self._config.update(kwargs)
        return self

    def run(self) -> BookingResult:
        """运行单账号预约流程

        使用 BookingClient 执行完整的预约流程：
        1. 启动浏览器
        2. 打开预约页面
        3. 登录
        4. 选择校区
        5. 选择项目
        6. 选择日期
        7. 选择时间段
        8. 选择场地
        9. 确认预约

        Returns:
            BookingResult: 预约结果
        """
        self._status = "running"
        time_slot = self.config.get("time_slot", "")

        try:
            from .client import BookingClient
            from .selectors.slot_selector import SlotUnavailableError

            print(f"\n开始执行预约: {self.username}")
            print("=" * 50)

            # 创建 BookingClient
            client = BookingClient(use_fake_browser=self._dry_run)
            client._ensure_browser()

            # 获取配置
            url = self._config.get("url")
            campus = self._config.get("campus")
            sport = self._config.get("sport")
            date_index = self._config.get("date_index", 0)

            # 打开预约页面
            if url:
                client.open(url)

            # 登录
            client.login(self.username, self.password)
            client.wait(1)

            # 选择校区
            if campus:
                try:
                    client.select_campus(campus)
                    client.wait(0.5)
                except Exception as e:
                    return self._fail_result(f"选择校区失败: {e}", time_slot)

            # 选择项目
            if sport:
                try:
                    client.select_sport(sport)
                    client.wait(0.5)
                except Exception as e:
                    return self._fail_result(f"选择项目失败: {e}", time_slot)

            # 选择日期
            try:
                client.select_date(date_index)
                client.wait(0.5)
            except Exception as e:
                return self._fail_result(f"选择日期失败: {e}", time_slot)

            # 选择时间段
            if time_slot:
                try:
                    client.select_time_slot(time_slot)
                    client.wait(0.5)
                except SlotUnavailableError as e:
                    return self._fail_result(f"时间段不可用: {e}", time_slot)
                except Exception as e:
                    return self._fail_result(f"时间段选择失败: {e}", time_slot)

            # 选择场地
            try:
                client.select_venue()
                client.wait(0.5)
            except SlotUnavailableError as e:
                return self._fail_result(f"场地不可用: {e}", time_slot)
            except Exception as e:
                return self._fail_result(f"场地选择失败: {e}", time_slot)

            # 确认预约
            try:
                confirmed = client.confirm()
            except Exception as e:
                return self._fail_result(f"确认预约失败: {e}", time_slot)

            client.wait(2)
            client.close()

            self._status = "completed"
            if confirmed:
                self._result = BookingResult(
                    username=self.username,
                    status="success",
                    message="预约完成",
                    time_slot=time_slot,
                )
                print("=" * 50)
                print(f"预约成功: {self.username}")
            else:
                self._result = BookingResult(
                    username=self.username,
                    status="failed",
                    message="预约被拒绝或状态未知",
                    time_slot=time_slot,
                )
                print("=" * 50)
                print(f"预约失败: {self.username}")
            return self._result

        except SlotUnavailableError as e:
            return self._fail_result(f"时间段/场地不可用: {e}", time_slot)
        except Exception as e:
            return self._fail_result(str(e), time_slot)
        finally:
            # 确保浏览器关闭
            try:
                if "client" in locals():
                    client.close()
            except Exception:
                pass

    def _fail_result(self, message: str, time_slot: str) -> BookingResult:
        """生成失败结果"""
        self._status = "completed"
        self._result = BookingResult(
            username=self.username, status="failed", message=message, time_slot=time_slot
        )
        print(f"预约失败: {message}")
        print("=" * 50)
        return self._result

    def stop(self):
        """停止会话"""
        self._status = "stopped"

    @property
    def status(self) -> str:
        return self._status

    @property
    def result(self) -> BookingResult:
        return self._result
