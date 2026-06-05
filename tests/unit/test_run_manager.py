"""Tests for RunManager."""
import json
from pathlib import Path

from booking.observability.run_manager import RunManager, RunRecord, get_run_manager


class TestRunManager:
    """Tests for RunManager."""

    def test_start_run(self, tmp_path):
        """start_run 创建运行记录"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        record = rm.start_run(campus="粤海校区", sport="网球")

        assert record.trace_id is not None
        assert len(record.trace_id) == 36  # UUID
        assert record.campus == "粤海校区"
        assert record.sport == "网球"
        assert record.status == "running"
        assert record.dry_run is False
        assert Path(record.run_dir).exists()

    def test_start_run_with_trace_id(self, tmp_path):
        """start_run 使用指定 trace_id"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        record = rm.start_run(trace_id="my-trace-id")

        assert record.trace_id == "my-trace-id"

    def test_start_run_dry_run(self, tmp_path):
        """start_run 干跑模式"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        record = rm.start_run(dry_run=True)

        assert record.dry_run is True

    def test_end_run_success(self, tmp_path):
        """end_run 标记成功"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run()
        rm.end_run(success=True)

        # Query to verify
        runs = rm.query_runs(limit=1)
        assert runs[0]["status"] == "success"

    def test_end_run_failed(self, tmp_path):
        """end_run 标记失败"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run()
        rm.end_run(success=False, error_message="测试错误")

        runs = rm.query_runs(limit=1)
        assert runs[0]["status"] == "failed"
        assert runs[0]["error_message"] == "测试错误"

    def test_log(self, tmp_path):
        """log 写入日志"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        record = rm.start_run()

        rm.log("测试消息", level="INFO", key="value")
        rm.log("警告消息", level="WARNING")
        rm.log("错误消息", level="ERROR", error_code="E001")

        # Read log file
        log_file = Path(record.run_dir) / "run.json.log"
        assert log_file.exists()

        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

        entries = [json.loads(line) for line in lines]
        assert entries[0]["message"] == "测试消息"
        assert entries[0]["level"] == "INFO"
        assert entries[0]["key"] == "value"
        assert entries[2]["level"] == "ERROR"

    def test_log_step(self, tmp_path):
        """log_step 记录步骤"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run()

        rm.log_step("初始化浏览器", "success", duration_ms=100)
        rm.log_step("登录", "success", duration_ms=500)
        rm.log_step("选择校区", "failed", duration_ms=50, error="未找到元素",
                     campus="丽湖校区")

        steps_file = Path(rm.current_run.run_dir) / "steps.json"
        assert steps_file.exists()

        steps = json.loads(steps_file.read_text(encoding="utf-8"))
        assert len(steps) == 3
        assert steps[0]["step"] == "初始化浏览器"
        assert steps[0]["status"] == "success"
        assert steps[2]["step"] == "选择校区"
        assert steps[2]["status"] == "failed"
        assert steps[2]["error"] == "未找到元素"
        assert steps[2]["campus"] == "丽湖校区"

    def test_save_summary(self, tmp_path):
        """save_summary 保存摘要"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run()

        summary = {"total": 5, "success": 3, "failed": 2}
        rm.save_summary(summary)

        summary_file = Path(rm.current_run.run_dir) / "summary.json"
        data = json.loads(summary_file.read_text(encoding="utf-8"))
        assert data == summary

    def test_query_runs(self, tmp_path):
        """query_runs 查询运行记录"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))

        # Create multiple runs
        for i in range(5):
            rm.start_run(campus=f"校区{i}")
            rm.end_run(success=i % 2 == 0)

        runs = rm.query_runs(limit=3)
        assert len(runs) == 3

        # Filter by status
        success_runs = rm.query_runs(status="success", limit=10)
        assert len(success_runs) == 3  # i=0,2,4

        failed_runs = rm.query_runs(status="failed", limit=10)
        assert len(failed_runs) == 2  # i=1,3

    def test_query_runs_offset(self, tmp_path):
        """query_runs 分页"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        for i in range(5):  # noqa: B007
            rm.start_run()
            rm.end_run(success=True)

        runs = rm.query_runs(limit=2, offset=2)
        assert len(runs) == 2

    def test_get_run_by_trace(self, tmp_path):
        """get_run_by_trace 通过 trace_id 查询"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        record = rm.start_run(trace_id="abc-123")  # noqa: F841

        run = rm.get_run_by_trace("abc-123")
        assert run is not None
        assert run["trace_id"] == "abc-123"

        # Non-existent trace
        run = rm.get_run_by_trace("nonexistent")
        assert run is None

    def test_get_run_logs(self, tmp_path):
        """get_run_logs 获取运行日志"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="test-logs")
        rm.log("消息1")
        rm.log("消息2")

        logs = rm.get_run_logs("test-logs")
        assert len(logs) == 2
        assert logs[0]["message"] == "消息1"

    def test_get_run_steps(self, tmp_path):
        """get_run_steps 获取运行步骤"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="test-steps")
        rm.log_step("步骤1", "success")
        rm.log_step("步骤2", "success")

        steps = rm.get_run_steps("test-steps")
        assert len(steps) == 2

    def test_run_isolation(self, tmp_path):
        """run 日志隔离 - 不同运行互不干扰"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))

        # Run 1
        rm.start_run(trace_id="run-1")
        rm.log("run-1 日志")
        rm.log_step("run-1 步骤", "success")
        rm.end_run(success=True)

        # Run 2
        rm.start_run(trace_id="run-2")
        rm.log("run-2 日志")
        rm.log_step("run-2 步骤", "success")
        rm.end_run(success=False)

        # Verify isolation
        logs_1 = rm.get_run_logs("run-1")
        logs_2 = rm.get_run_logs("run-2")
        assert logs_1[0]["message"] == "run-1 日志"
        assert logs_2[0]["message"] == "run-2 日志"

        # Verify traces are in different directories
        run1 = rm.get_run_by_trace("run-1")
        run2 = rm.get_run_by_trace("run-2")
        assert run1["run_dir"] != run2["run_dir"]

    def test_current_run_property(self, tmp_path):
        """current_run 属性"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        assert rm.current_run is None

        rm.start_run()
        assert rm.current_run is not None

        rm.end_run()
        assert rm.current_run is None

    def test_log_without_active_run(self, tmp_path):
        """没有活跃运行时 log 不报错"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.log("这条日志不会被写入")

    def test_nonexistent_run_logs(self, tmp_path):
        """不存在的运行返回空日志"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        assert rm.get_run_logs("nonexistent") == []
        assert rm.get_run_steps("nonexistent") == []


class TestRunRecord:
    """Tests for RunRecord."""

    def test_run_record_defaults(self):
        """RunRecord 默认值"""
        record = RunRecord(
            trace_id="test", run_dir="/tmp/test",
            start_time="2026-01-01T00:00:00"
        )
        assert record.trace_id == "test"
        assert record.status == "running"
        assert record.campus == ""
        assert record.sport == ""


class TestGetRunManager:
    """Tests for get_run_manager singleton."""

    def test_get_run_manager_returns_same_instance(self, tmp_path):
        """get_run_manager 返回同一个实例"""
        rm1 = get_run_manager()
        rm2 = get_run_manager()
        assert rm1 is rm2
