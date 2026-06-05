#!/usr/bin/env python3
"""\u73af\u5883\u5065\u5eb7\u68c0\u67e5 - szu-sports-booking skill

\u68c0\u67e5\u9879:
1. Python \u7248\u672c (>= 3.10)
2. Skill \u81ea\u5e26\u7684 .env
3. \u51ed\u8bc1\u662f\u5426\u5b8c\u6574 (SZU_USERNAME + SZU_PASSWORD_xxxx)
4. \u4f9d\u8d56 (httpx, curl_cffi, pydantic, click, dotenv)
5. Cookie \u72b6\u6001 (24h \u6709\u6548)
6. \u7f51\u7edc (ehall.szu.edu.cn)
7. \u9879\u76ee\u4f4d\u7f6e (src/booking/cli.py)

\u9000\u51fa\u7801: 0 = OK, 1 = WARN, 2 = FAIL
"""
from __future__ import annotations

import os
import sys
import json
import socket
import time
from pathlib import Path


class C:
    G = "\033[92m"
    Y = "\033[93m"
    R = "\033[91m"
    B = "\033[94m"
    BOLD = "\033[1m"
    X = "\033[0m"


def col(color, text):
    return f"{color}{text}{C.X}" if sys.stdout.isatty() else text


OK = "[OK]"
WARN = "[WARN]"
ERR = "[FAIL]"
INFO = "[INFO]"


def section(title):
    print()
    print(col(C.BOLD, f"--- {title} ---"))


def ok(msg):
    print(f"  {col(C.G, OK)} {msg}")


def warn(msg):
    print(f"  {col(C.Y, WARN)} {msg}")


def err(msg):
    print(f"  {col(C.R, ERR)} {msg}")


def info(msg):
    print(f"  {col(C.B, INFO)} {msg}")


def get_skill_dir():
    return Path(__file__).resolve().parent.parent


def get_project_root():
    # 优先从 SZU_BOOKING_DIR 读取 (全局部署场景)
    env_dir = os.environ.get('SZU_BOOKING_DIR', '').strip()
    if env_dir:
        p = Path(env_dir)
        if (p / 'src' / 'booking' / 'cli.py').exists():
            return p
    # 否则假设 skill 在 <project>/.agents/skills/szu-sports-booking/
    return get_skill_dir().parent.parent.parent


def check_python():
    section("1. Python")
    v = sys.version_info
    if v >= (3, 10):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    err(f"Python {v.major}.{v.minor} \u592a\u8001, \u9700 3.10+")
    return False


def check_skill_env():
    section("2. Skill \u81ea\u5e26 .env")
    skill_dir = get_skill_dir()
    env_file = skill_dir / ".env"
    example_file = skill_dir / ".env.example"

    if not env_file.exists():
        err(f"\u672a\u627e\u5230: {env_file}")
        if example_file.exists():
            info(f"\u8bf7\u590d\u5236\u6a21\u677f: cp {example_file} {env_file}")
            info("\u7136\u540e\u7f16\u8f91 .env, \u586b\u5165 SZU_USERNAME \u548c SZU_PASSWORD_xxxx")
        return False

    ok(f"\u627e\u5230: {env_file}")

    try:
        from dotenv import dotenv_values
        env = dotenv_values(env_file)
    except Exception as e:
        err(f"\u89e3\u6790\u5931\u8d25: {e}")
        return False

    username = env.get("SZU_USERNAME", "").strip()
    if not username or username == "2023150090":
        warn("SZU_USERNAME \u672a\u586b\u6216\u4ecd\u4e3a\u9ed8\u8ba4")
        info(f"\u8bf7\u7f16\u8f91 {env_file}, \u586b\u5165\u771f\u5b9e\u5b66\u53f7")
        return False
    ok(f"SZU_USERNAME = {username}")

    suffix = username[-4:] if len(username) >= 4 else username
    pwd_key = f"SZU_PASSWORD_{suffix}"
    pwd = env.get(pwd_key, "").strip()
    pwd_fallback = env.get("SZU_PASSWORD", "").strip()

    if pwd and pwd != "your_password_here":
        ok(f"{pwd_key} = ******** ({len(pwd)} \u4f4d)")
    elif pwd_fallback and pwd_fallback != "your_password_here":
        warn(f"{pwd_key} \u672a\u8bbe\u7f6e, \u4f46 SZU_PASSWORD \u5df2\u8bbe\u7f6e (\u5151\u5e95)")
        ok(f"SZU_PASSWORD = ******** ({len(pwd_fallback)} \u4f4d)")
    else:
        err(f"{pwd_key} \u672a\u8bbe\u7f6e")
        info(f"\u8bf7\u7f16\u8f91 {env_file}, \u8bbe\u7f6e {pwd_key}=\u5bc6\u7801")
        return False

    if pwd and len(pwd) < 6:
        warn(f"{pwd_key} \u503c\u592a\u77ed ({len(pwd)} \u5b57\u7b26)")

    campus = env.get("SZU_DEFAULT_CAMPUS", "").strip()
    sport = env.get("SZU_DEFAULT_SPORT", "").strip()
    if campus:
        ok(f"SZU_DEFAULT_CAMPUS = {campus}")
    if sport:
        ok(f"SZU_DEFAULT_SPORT = {sport}")

    return True


REQUIRED = {
    "httpx": "0.27",
    "curl_cffi": "0.15",
    "pydantic": "2.0",
    "click": "8.0",
    "dotenv": "1.0",
}


def check_deps():
    section("3. \u4f9d\u8d56\u5305")
    all_ok = True
    for mod, ver in REQUIRED.items():
        try:
            __import__(mod)
            ok(f"{mod} >= {ver}")
        except ImportError:
            err(f"{mod} \u7f3a")
            all_ok = False
    if not all_ok:
        info("\u8fd0\u884c: pip install -e .  \u6216  make install")
    return all_ok


def check_project():
    section("4. \u9879\u76ee\u4f4d\u7f6e")
    root = get_project_root()
    cli = root / "src" / "booking" / "cli.py"
    if cli.exists():
        ok(f"\u9879\u76ee\u6839: {root}")
        return True
    err(f"\u672a\u627e\u5230 src/booking/cli.py: {root}")
    return False


def check_cookies():
    section("5. Cookie \u72b6\u6001 (24h \u6709\u6548)")
    root = get_project_root()
    cookies_dir = root / "data" / "cookies"
    if not cookies_dir.exists():
        warn("data/cookies/ \u4e0d\u5b58\u5728")
        info("\u9996\u6b21\u4f7f\u7528\u9700\u6d4f\u89c8\u5668\u767b\u5f55\u4e00\u6b21:")
        info("  source scripts/load_env.sh   (bash)")
        info("  python -m booking.cli api -s \u7f51\u7403 --dry-run")
        return True

    cookies = list(cookies_dir.glob("*.json"))
    if not cookies:
        warn("data/cookies/ \u4e3a\u7a7a")
        return True

    now = time.time()
    one_day = 24 * 3600
    for c_path in cookies:
        try:
            with open(c_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            age = now - c_path.stat().st_mtime
            if age < one_day:
                remaining = int((one_day - age) / 3600)
                ok(f"{c_path.name}: \u6709\u6548 (\u8fd8\u53ef\u7528 {remaining} \u5c0f\u65f6)")
            else:
                warn(f"{c_path.name}: \u5df2\u8fc7\u671f ({int(age / 3600)} \u5c0f\u65f6)")
        except Exception as e:
            warn(f"{c_path.name}: \u89e3\u6790\u5931\u8d25 - {e}")
    return True


def check_network():
    section("6. \u7f51\u7edc\u53ef\u8fbe\u6027")
    try:
        start = time.time()
        socket.create_connection(("ehall.szu.edu.cn", 443), timeout=5)
        ok(f"ehall.szu.edu.cn:443 \u53ef\u8fbe ({int((time.time() - start) * 1000)} ms)")
        return True
    except (socket.timeout, OSError) as e:
        err(f"ehall.szu.edu.cn:443 \u4e0d\u53ef\u8fbe: {e}")
        info("\u68c0\u67e5\u7f51\u7edc, \u6216\u4f7f\u7528 --proxy")
        return False


def main():
    print(col(C.BOLD, "=" * 60))
    print(col(C.BOLD, " szu-sports-booking skill \u73af\u5883\u68c0\u67e5"))
    print(col(C.BOLD, "=" * 60))

    results = [
        check_python(),
        check_skill_env(),
        check_deps(),
        check_project(),
        check_cookies(),
        check_network(),
    ]

    print()
    print(col(C.BOLD, "=" * 60))
    print(col(C.BOLD, " \u603b\u7ed3"))
    print(col(C.BOLD, "=" * 60))
    failed = sum(1 for r in results if not r)
    passed = len(results) - failed
    if failed == 0:
        print(col(C.G, f"  [OK] {passed}/{len(results)} \u9879\u5168\u90e8\u8d70\u8fc7"))
        print()
        print(col(C.BOLD, "  \u4e0b\u4e00\u6b65:"))
        print("    bash/zsh:    source .agents/skills/szu-sports-booking/scripts/load_env.sh")
        print("    PowerShell:  . .\\agents\\skills\\szu-sports-booking\\scripts\\load_env.ps1")
        print("    \u7136\u540e:        python -m booking.cli api -s \u7f51\u7403 -t 19:00-20:00 --dry-run")
        return 0
    elif failed <= 2:
        print(col(C.Y, f"  [WARN] {passed} OK, {failed} \u9700\u5173\u6ce8"))
        return 1
    else:
        print(col(C.R, f"  [FAIL] {passed} OK, {failed} \u51fa\u9519"))
        return 2


if __name__ == "__main__":
    sys.exit(main())
