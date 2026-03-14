# Makefile for Agent project (uv version)

.PHONY: help uv-install uv-dev-install uv-sync uv-lock test lint format type-check clean setup run-example uv-venv uv-update uv-check

help:
	@echo "可用命令 (使用uv):"
	@echo "  make uv-install     使用uv安装生产依赖"
	@echo "  make uv-dev-install 使用uv安装开发依赖"
	@echo "  make uv-sync        同步依赖到虚拟环境"
	@echo "  make uv-lock        生成/更新锁文件"
	@echo "  make uv-venv        创建虚拟环境"
	@echo "  make uv-update      更新所有依赖"
	@echo "  make uv-check       运行所有检查"
	@echo ""
	@echo "  make test           运行测试"
	@echo "  make lint           代码检查"
	@echo "  make format         代码格式化"
	@echo "  make type-check     类型检查"
	@echo "  make clean          清理临时文件"
	@echo "  make setup          设置开发环境"
	@echo "  make run-example    运行示例"

# uv commands
uv-install:
	uv pip install -e .

uv-dev-install:
	uv pip install -e ".[dev]"

uv-sync:
	uv sync

uv-lock:
	uv lock

uv-venv:
	@echo "虚拟环境已创建在 .venv/"
	@echo "激活命令:"
	@echo "  source .venv/bin/activate  # Linux/Mac"
	@echo "  .venv\\Scripts\\activate    # Windows"

uv-update:
	uv pip compile --upgrade pyproject.toml -o uv.lock
	uv sync

uv-check: lint type-check test
	@echo "所有检查通过"

# Development commands (assumes virtual environment is activated)
test:
	pytest tests/ -v --cov=src/agent --cov-report=term-missing

lint:
	ruff check src tests

format:
	black src tests
	ruff check src tests --fix

type-check:
	mypy src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf build/ dist/ *.egg-info/ .venv/ uv.lock

setup: uv-dev-install
	@echo "开发环境设置完成"
	@echo "请复制 .env.example 为 .env 并配置API密钥:"
	@echo "  cp .env.example .env"
	@echo "然后编辑 .env 文件设置你的DeepSeek API密钥"

run-example:
	@if [ -f "examples/basic_usage.py" ]; then \
		python examples/basic_usage.py; \
	else \
		echo "示例文件不存在，请先创建 examples/basic_usage.py"; \
	fi

# Quick setup for development
dev: uv-venv uv-dev-install
	@echo "开发环境已准备就绪"
	@echo "激活虚拟环境: source .venv/bin/activate"

# Hatch commands (alternative)
hatch-test:
	hatch run test

hatch-lint:
	hatch run lint

hatch-format:
	hatch run format

# Install all dependencies (including optional)
all: uv-venv
	uv pip install -e ".[all]"