"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for tests."""
    return tmp_path


@pytest.fixture
def sample_config_yaml(temp_dir):
    """Sample config.yaml content."""
    config_path = temp_dir / "config.yaml"
    config_path.write_text(
        """
booking:
  venue_url: "https://test.example.com"
  default_campus: "粤海校区"
  default_sport: "网球"
  default_date_index: 0
  default_time_slot: "19:00-20:00"

retry:
  max_attempts: 3
  base_delay_seconds: 1

logging:
  level: "debug"
  dir: "logs"
  rotation: "daily"
  retention_days: 7
""",
        encoding="utf-8",
    )
    return str(config_path)


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("SZU_LOG_LEVEL", "debug")
    monkeypatch.setenv("SZU_ENV", "test")
    return monkeypatch


@pytest.fixture
def sample_accounts():
    """Sample account data for testing."""
    return {
        "test_user_1": "password_1",
        "test_user_2": "password_2",
    }


@pytest.fixture
def fake_browser():
    """Fake browser for testing without real browser."""
    from booking.browser import FakeBrowserLifecycle

    browser = FakeBrowserLifecycle()
    browser.launch()
    return browser


@pytest.fixture
def fake_page():
    """Fake page for testing."""
    from booking.browser import FakePage

    return FakePage()
