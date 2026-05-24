"""Tests for ReportGenerator."""
from pathlib import Path

import pytest

from booking.observability.report_generator import generate_html_report
from booking.observability.run_manager import RunManager


class TestReportGenerator:
    """Tests for report_generator."""

    def test_generate_html_report(self, tmp_path):
        """generate_html_report 生成 HTML 报告"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="test-report", campus="粤海校区", sport="网球")
        rm.log("程序启动", level="INFO", campus="粤海校区")
        rm.log_step("初始化浏览器", "success", duration_ms=100)
        rm.log_step("用户登录", "success", duration_ms=500)
        rm.log_step("选择校区", "failed", duration_ms=0, error="未找到元素",
                     campus="丽湖校区")
        rm.end_run(success=False, error_message="选择校区失败")

        html_path = generate_html_report("test-report", rm)
        assert html_path is not None
        assert Path(html_path).exists()

    def test_report_has_correct_stats(self, tmp_path):
        """报告包含正确的统计信息"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="stats-report")
        rm.log_step("步骤1", "success", duration_ms=100)
        rm.log_step("步骤2", "success", duration_ms=200)
        rm.log_step("步骤3", "failed", duration_ms=50, error="错误")
        rm.end_run(success=False)

        html_path = generate_html_report("stats-report", rm)
        content = Path(html_path).read_text()

        # Verify stats are present
        assert "stats-report" in content
        assert "3 步骤" in content
        assert "2" in content  # success count
        assert "1" in content  # failed count

    def test_report_shows_steps(self, tmp_path):
        """报告显示步骤详情"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="steps-report")
        rm.log_step("初始化", "success", duration_ms=50)
        rm.end_run(success=True)

        html_path = generate_html_report("steps-report", rm)
        content = Path(html_path).read_text()

        assert "初始化" in content
        assert "success" in content

    def test_report_valid_html(self, tmp_path):
        """报告是有效的 HTML"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="valid-html")
        rm.end_run(success=True)

        html_path = generate_html_report("valid-html", rm)
        content = Path(html_path).read_text()

        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content
        assert "<head>" in content
        assert "<body>" in content

    def test_report_with_logs(self, tmp_path):
        """报告包含日志条目"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="logs-report")
        rm.log("启动", level="INFO")
        rm.log("警告", level="WARNING")
        rm.log("错误", level="ERROR")
        rm.end_run(success=False)

        html_path = generate_html_report("logs-report", rm)
        content = Path(html_path).read_text()

        assert "启动" in content
        assert "警告" in content
        assert "错误" in content

    def test_report_nonexistent_run(self, tmp_path):
        """不存在的运行抛出 ValueError"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        with pytest.raises(ValueError, match="Run not found"):
            generate_html_report("nonexistent", rm)

    def test_report_empty_steps(self, tmp_path):
        """空步骤的报告"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="empty-steps")
        rm.end_run(success=True)

        html_path = generate_html_report("empty-steps", rm)
        content = Path(html_path).read_text()
        assert "暂无步骤记录" in content

    def test_report_empty_logs(self, tmp_path):
        """空日志的报告"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="empty-logs")
        rm.end_run(success=True)

        html_path = generate_html_report("empty-logs", rm)
        content = Path(html_path).read_text()
        assert "暂无日志记录" in content

    def test_report_dry_run(self, tmp_path):
        """干跑模式的报告"""
        rm = RunManager(base_dir=str(tmp_path / "runs"))
        rm.start_run(trace_id="dry-run-report", dry_run=True)
        rm.log("干跑模式", level="INFO")
        rm.end_run(success=True)

        html_path = generate_html_report("dry-run-report", rm)
        content = Path(html_path).read_text()
        assert "干跑模式" in content
