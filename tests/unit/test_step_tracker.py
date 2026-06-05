"""Tests for StepTracker."""

from booking.observability.step_tracker import Step, StepTracker


class TestStep:
    """Tests for Step dataclass."""

    def test_step_creation(self):
        """Step 创建"""
        step = Step(name="初始化")
        assert step.name == "初始化"
        assert step.status == "pending"
        assert step.error is None

    def test_step_finish_success(self):
        """Step 完成成功"""
        step = Step(name="登录")
        step.finish(status="success")
        assert step.status == "success"
        assert step.end_time is not None

    def test_step_finish_failed(self):
        """Step 完成失败"""
        step = Step(name="选择校区")
        step.finish(status="failed", error="未找到元素")
        assert step.status == "failed"
        assert step.error == "未找到元素"

    def test_step_duration_ms(self):
        """Step 时长计算"""
        step = Step(name="测试")
        step.finish(status="success")
        duration = step.duration_ms
        assert duration >= 0

    def test_step_defaults(self):
        """Step 默认值"""
        step = Step(name="测试")
        assert step.details == {}


class TestStepTracker:
    """Tests for StepTracker."""

    def test_start_step(self):
        """start_step 开始步骤"""
        tracker = StepTracker(trace_id="test-123")
        tracker.start_step("初始化")
        assert len(tracker.steps) == 1
        assert tracker.steps[0].name == "初始化"
        assert tracker.steps[0].status == "pending"

    def test_finish_step(self):
        """finish_step 完成步骤"""
        tracker = StepTracker(trace_id="test-123")
        tracker.start_step("登录")
        tracker.finish_step(status="success")
        assert tracker.steps[0].status == "success"

    def test_step_success(self):
        """step_success 快捷标记成功"""
        tracker = StepTracker(trace_id="test-123")
        tracker.start_step("测试")
        tracker.step_success()
        assert tracker.steps[0].status == "success"

    def test_step_failed(self):
        """step_failed 快捷标记失败"""
        tracker = StepTracker(trace_id="test-123")
        tracker.start_step("测试")
        tracker.step_failed("错误消息")
        assert tracker.steps[0].status == "failed"
        assert tracker.steps[0].error == "错误消息"

    def test_step_skipped(self):
        """step_skipped 标记跳过"""
        tracker = StepTracker(trace_id="test-123")
        tracker.start_step("测试")
        tracker.step_skipped()
        assert tracker.steps[0].status == "skipped"

    def test_get_summary(self):
        """get_summary 获取摘要"""
        tracker = StepTracker(trace_id="test-123")
        tracker.start_step("步骤1")
        tracker.step_success()
        tracker.start_step("步骤2")
        tracker.step_success()
        tracker.start_step("步骤3")
        tracker.step_failed("错误")

        summary = tracker.get_summary()
        assert summary["trace_id"] == "test-123"
        assert summary["total_steps"] == 3
        assert summary["success_count"] == 2
        assert summary["failed_count"] == 1
        assert len(summary["steps"]) == 3

    def test_get_summary_empty(self):
        """get_summary 空步骤"""
        tracker = StepTracker(trace_id="test-123")
        summary = tracker.get_summary()
        assert summary["total_steps"] == 0
        assert summary["success_rate"] == 0

    def test_print_summary(self, capsys):
        """print_summary 打印摘要"""
        tracker = StepTracker(trace_id="test-123")
        tracker.start_step("步骤1")
        tracker.step_success()
        tracker.print_summary()

        captured = capsys.readouterr()
        assert "执行报告" in captured.out
        assert "test-123" in captured.out

    def test_save_report(self, tmp_path):
        """save_report 保存报告"""
        tracker = StepTracker(trace_id="test-save")
        tracker.start_step("步骤1")
        tracker.step_success()
        tracker.start_step("步骤2", details={"campus": "粤海校区"})
        tracker.step_success()

        report_path = tracker.save_report(output_dir=str(tmp_path))
        # save_report 使用 trace_id[:8] 作为文件名
        assert "test-sav" in report_path

    def test_multiple_steps(self):
        """多步骤追踪"""
        tracker = StepTracker(trace_id="test-multi")

        for i in range(10):
            tracker.start_step(f"步骤{i}")
            tracker.step_success()

        assert len(tracker.steps) == 10
        summary = tracker.get_summary()
        assert summary["total_steps"] == 10
        assert summary["success_count"] == 10
