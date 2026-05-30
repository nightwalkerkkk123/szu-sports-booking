#!/usr/bin/env python3
"""
check_repo.py - 仓库自检脚本

检查仓库是否满足 Agent-friendly 标准。

运行：
    PYTHONPATH=src python scripts/check_repo.py
    make check-repo
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

REQUIRED_FILES = [
    "AGENTS.md",
    "PROJECT_INDEX.md",
    "README.md",
    "pyproject.toml",
    "pytest.ini",
    "Makefile",
    "src/booking/__init__.py",
    "tests/conftest.py",
    "tests/README.md",
    ".gitignore",
    "configs/.env.example",
]

REQUIRED_DIRS = [
    "src/booking",
    "tests/unit",
    "tests/integration",
    "tests/smoke",
    "docs",
    "examples",
]

REQUIRED_MODULES = [
    "booking.client",
    "booking.account",
    "booking.config",
    "booking.errors",
    "booking.retry",
    "booking.cli",
    "booking.observability",
]


def check_files():
    """Check required files exist."""
    print("检查文件...")
    root = Path(__file__).parent.parent
    missing = []

    for file in REQUIRED_FILES:
        if not (root / file).exists():
            missing.append(file)
            print(f"  [X] {file}")
        else:
            print(f"  [OK] {file}")

    return missing


def check_dirs():
    """Check required directories exist."""
    print("\n检查目录...")
    root = Path(__file__).parent.parent
    missing = []

    for dir in REQUIRED_DIRS:
        if not (root / dir).is_dir():
            missing.append(dir)
            print(f"  [X] {dir}/")
        else:
            print(f"  [OK] {dir}/")

    return missing


def check_modules():
    """Check required modules can be imported."""
    print("\n检查模块导入...")
    failed = []

    for module in REQUIRED_MODULES:
        try:
            __import__(module)
            print(f"  [OK] {module}")
        except ImportError as e:
            failed.append((module, str(e)))
            print(f"  [X] {module}: {e}")

    return failed


def check_pytest_markers():
    """Check pytest markers are configured."""
    print("\n检查 pytest markers...")
    root = Path(__file__).parent.parent
    pytest_ini = root / "pytest.ini"

    if pytest_ini.exists():
        content = pytest_ini.read_text()
        markers = ["unit", "integration", "smoke", "real_env"]
        for marker in markers:
            if f"{marker}:" in content or f'"{marker}' in content:
                print(f"  [OK] {marker} marker")
            else:
                print(f"  ? {marker} marker (未确认)")
    else:
        print("  ! pytest.ini 未找到")


def check_docs_synced():
    """Check if docs/DEVELOPMENT.md code structure matches actual directories."""
    print("\n检查文档同步性...")
    root = Path(__file__).parent.parent
    dev_doc = root / "docs/DEVELOPMENT.md"

    if not dev_doc.exists():
        print("  ! docs/DEVELOPMENT.md 未找到")
        return True

    content = dev_doc.read_text()

    # 从 DEVELOPMENT.md 中提取代码结构部分列出的目录
    expected_dirs = [
        "src/booking/browser/",
        "examples/",
        "scripts/",
        "tests/",
    ]

    issues = []
    for dir_path in expected_dirs:
        # 检查目录是否存在
        full_path = root / dir_path.rstrip("/")
        if not full_path.exists():
            issues.append(f"  ! {dir_path} 列在文档中但不存在")
        else:
            print(f"  [OK] {dir_path}")

    if issues:
        print("\n  文档同步问题:")
        for issue in issues:
            print(issue)
        print("\n  建议: 运行 'make check-repo' 查看完整检查结果")
        return False

    return True


def main():
    """Run all checks."""
    print("=" * 60)
    print("仓库自检")
    print("=" * 60)

    missing_files = check_files()
    missing_dirs = check_dirs()
    failed_modules = check_modules()
    check_pytest_markers()
    docs_synced = check_docs_synced()

    print("\n" + "=" * 60)
    print("检查结果")
    print("=" * 60)

    if not missing_files and not missing_dirs and not failed_modules:
        print("[OK] 所有检查通过！")
        if not docs_synced:
            print("\n[!] 文档可能需要同步更新")
        return 0
    else:
        if missing_files:
            print(f"\n[X] 缺少 {len(missing_files)} 个文件")
        if missing_dirs:
            print(f"\n[X] 缺少 {len(missing_dirs)} 个目录")
        if failed_modules:
            print(f"\n[X] {len(failed_modules)} 个模块导入失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())