"""Tests for render_log_html (was trace_viewer)."""

from pathlib import Path

from booking.observability.report_generator import render_log_html


class TestRenderLogHtml:
    """Tests for trace_viewer."""

    def test_render_log_html(self, tmp_path):
        """generate_trace_html 生成 HTML"""
        entries = [
            {
                "timestamp": "2026-05-24T15:00:00.000000",
                "level": "INFO",
                "message": "程序启动",
                "trace_id": "test-trace",
            },
            {
                "timestamp": "2026-05-24T15:00:01.000000",
                "level": "INFO",
                "message": "登录成功",
                "trace_id": "test-trace",
            },
            {
                "timestamp": "2026-05-24T15:00:02.000000",
                "level": "ERROR",
                "message": "选择校区失败",
                "trace_id": "test-trace",
                "error": "未找到元素",
            },
        ]

        html_path = str(tmp_path / "trace_test.html")
        html = render_log_html("test-trace", entries, html_path)

        assert "<!DOCTYPE html>" in html
        assert "test-trace" in html
        assert Path(html_path).exists()

    def test_generate_trace_html_empty(self, tmp_path):
        """generate_trace_html 空条目"""
        html_path = str(tmp_path / "trace_empty.html")
        html = render_log_html("test-empty", [], html_path)

        assert "<!DOCTYPE html>" in html
        assert "test-empty" in html

    def test_generate_trace_html_has_stats(self, tmp_path):
        """generate_trace_html 包含统计信息"""
        entries = [
            {"timestamp": "2026-05-24T15:00:00", "level": "INFO", "message": "消息1"},
            {"timestamp": "2026-05-24T15:00:01", "level": "WARNING", "message": "消息2"},
            {"timestamp": "2026-05-24T15:00:02", "level": "ERROR", "message": "消息3"},
        ]

        html_path = str(tmp_path / "trace_stats.html")
        html = render_log_html("test-stats", entries, html_path)

        assert "INFO" in html
        assert "WARNING" in html
        assert "ERROR" in html

    def test_generate_trace_html_no_output_path(self):
        """generate_trace_html 不指定输出路径"""
        entries = [{"timestamp": "2026-05-24T15:00:00", "level": "INFO", "message": "测试"}]
        html = render_log_html("test-no-path", entries)
        assert "test-no-path" in html

    # generate_report_html was removed: use generate_html_report for the
    # full report (with steps + plan + logs).
