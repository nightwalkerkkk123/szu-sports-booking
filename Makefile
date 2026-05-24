.PHONY: help install lint format test test-unit test-integration test-smoke test-all cov clean ci check-repo doctor

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make lint          - Run ruff check"
	@echo "  make format        - Run ruff format"
	@echo "  make test          - Run pytest (skip real_env)"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-smoke    - Run smoke tests only"
	@echo "  make test-all      - Run all tests including real_env"
	@echo "  make cov           - Run pytest with coverage"
	@echo "  make ci            - Run lint + test (CI pipeline)"
	@echo "  make check-repo    - Run repository self-check"
	@echo "  make clean         - Remove cache files"

install:
	uv sync --dev

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

test:
	PYTHONPATH=src pytest tests/ -m "not real_env"

test-unit:
	PYTHONPATH=src pytest tests/unit/ -v

test-integration:
	PYTHONPATH=src pytest tests/integration/ -v

test-smoke:
	PYTHONPATH=src pytest tests/smoke/ -v

test-all:
	PYTHONPATH=src pytest tests/ -m ""

cov:
	PYTHONPATH=src pytest tests/ --cov=src/booking --cov-report=html --cov-report=term-missing

ci:
	$(MAKE) lint
	$(MAKE) test

check-repo:
	PYTHONPATH=src python3 scripts/check_repo.py

doctor:
	@echo "检查环境..."
	@python3 --version
	@echo "检查依赖..."
	@python3 -c "import click; import pytest; import yaml; print('核心依赖: OK')"

clean:
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true