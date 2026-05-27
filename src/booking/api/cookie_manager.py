"""Cookie persistence manager."""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("booking.api")


class CookieManager:
    """
    Manages cookie persistence to/from files.

    Cookies are stored as JSON with metadata (timestamp, expiry).
    """

    DEFAULT_COOKIE_DIR = Path("data/cookies")
    DEFAULT_EXPIRY_HOURS = 12  # CAS tokens typically expire in 12h

    # Required cookies for API calls
    REQUIRED_COOKIES = [
        "MOD_AUTH_CAS",
        "_WEU",
        "EMAP_LANG",
        "insert_cookie",
        "route",
    ]

    def __init__(self, cookie_dir: Optional[Path] = None):
        self._cookie_dir = cookie_dir or self.DEFAULT_COOKIE_DIR
        self._cookie_dir.mkdir(parents=True, exist_ok=True)

    def _get_cookie_path(self, username: str) -> Path:
        """Get cookie file path for a username"""
        return self._cookie_dir / f"{username}_cookies.json"

    def save(
        self,
        username: str,
        cookies: dict,
        expiry_hours: Optional[int] = None,
    ) -> bool:
        """
        Save cookies for a username.

        Args:
            username: Student ID
            cookies: Dict of cookie name -> value
            expiry_hours: Cookie expiry in hours (default: 12)

        Returns:
            True if all required cookies were saved
        """
        # Validate required cookies present
        missing = [c for c in self.REQUIRED_COOKIES if c not in cookies]
        if missing:
            logger.warning(f"Missing required cookies: {missing}")
            return False

        data = {
            "username": username,
            "cookies": cookies,
            "saved_at": datetime.now().isoformat(),
            "expires_at": (
                datetime.now() + timedelta(hours=expiry_hours or self.DEFAULT_EXPIRY_HOURS)
            ).isoformat(),
        }

        path = self._get_cookie_path(username)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved cookies for {username} to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False

    def load(self, username: str) -> Optional[dict]:
        """
        Load cookies for a username.

        Args:
            username: Student ID

        Returns:
            Cookie dict if valid, None if not found or expired
        """
        path = self._get_cookie_path(username)
        if not path.exists():
            logger.debug(f"No cookie file for {username}")
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check expiry
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.now() > expires_at:
                logger.info(f"Cookies expired for {username}")
                return None

            logger.info(f"Loaded valid cookies for {username}")
            return data["cookies"]

        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return None

    def is_valid(self, username: str) -> bool:
        """
        Check if username has valid (non-expired) cookies.

        Args:
            username: Student ID

        Returns:
            True if valid cookies exist
        """
        cookies = self.load(username)
        return cookies is not None

    def delete(self, username: str) -> bool:
        """
        Delete cookies for a username.

        Args:
            username: Student ID

        Returns:
            True if deleted, False if not found
        """
        path = self._get_cookie_path(username)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted cookies for {username}")
            return True
        return False

    def list_users(self) -> list[str]:
        """List usernames with saved cookies"""
        users = []
        for path in self._cookie_dir.glob("*_cookies.json"):
            username = path.stem.replace("_cookies", "")
            users.append(username)
        return users

    def cleanup_expired(self):
        """Remove all expired cookie files"""
        for path in self._cookie_dir.glob("*_cookies.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.now() > expires_at:
                    path.unlink()
                    logger.info(f"Cleaned up expired cookies: {path.stem}")
            except Exception:
                pass