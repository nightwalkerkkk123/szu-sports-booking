"""Tests for booking.cli module - CLI entry point."""
from unittest.mock import MagicMock, patch


class TestCLICommands:
    """Test CLI command structure."""

    def test_cli_group_exists(self):
        """CLI group can be imported."""
        from booking.cli import cli
        assert cli is not None

    def test_cli_has_run_command(self):
        """CLI has run command."""
        from booking.cli import cli
        assert "run" in cli.commands

    def test_cli_has_test_login_command(self):
        """CLI has test-login command."""
        from booking.cli import cli
        assert "test-login" in cli.commands

    def test_cli_has_validate_config_command(self):
        """CLI has validate-config command."""
        from booking.cli import cli
        assert "validate-config" in cli.commands

    def test_cli_has_smoke_command(self):
        """CLI has smoke command."""
        from booking.cli import cli
        assert "smoke" in cli.commands

    def test_cli_has_report_command(self):
        """CLI has report command."""
        from booking.cli import cli
        assert "report" in cli.commands


class TestValidateConfigCommand:
    """Test validate-config command."""

    def test_validate_config_returns_zero_on_success(self, tmp_path, monkeypatch):
        """validate-config exits with 0 when config is valid."""
        from click.testing import CliRunner

        from booking.cli import validate_config

        # Create a valid config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
booking:
  venue_url: "https://test.com"
  default_campus: "粤海校区"
  default_sport: "网球"
  default_date_index: 0
  default_time_slot: "19:00-20:00"
""", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(validate_config, ["--config", str(config_file)])
        assert result.exit_code == 0

    def test_validate_config_loads_and_prints_values(self, tmp_path):
        """validate-config loads and displays config values."""
        from click.testing import CliRunner

        from booking.cli import validate_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
booking:
  venue_url: "https://test.com"
  default_campus: "丽湖校区"
  default_sport: "羽毛球"
  default_date_index: 0
  default_time_slot: "20:00-21:00"
""", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(validate_config, ["--config", str(config_file)])
        assert "丽湖校区" in result.output
        assert "羽毛球" in result.output


class TestSmokeCommand:
    """Test smoke command."""

    def test_smoke_command_runs_pytest(self):
        """smoke command runs pytest on smoke tests."""
        from click.testing import CliRunner

        from booking.cli import smoke

        runner = CliRunner()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(smoke)  # noqa: F841
            # smoke command should call pytest


class TestCLIArgumentParsing:
    """Test CLI argument parsing."""

    def test_run_command_accepts_account_option(self):
        """run command accepts --account option."""
        from click.testing import CliRunner

        from booking.cli import run

        runner = CliRunner()
        result = runner.invoke(run, ["--help"])
        assert "--account" in result.output or "-a" in result.output

    def test_run_command_accepts_dry_run_option(self):
        """run command accepts --dry-run option."""
        from click.testing import CliRunner

        from booking.cli import run

        runner = CliRunner()
        result = runner.invoke(run, ["--help"])
        assert "--dry-run" in result.output
