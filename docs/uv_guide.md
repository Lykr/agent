# uv 使用指南

[uv](https://github.com/astral-sh/uv) 是一个快速的Python包管理器和解析器，由 Astral 开发（Ruff 的创建者）。它比传统的 `pip` 和 `venv` 更快，并且提供了更好的依赖管理。

## 为什么使用 uv？

1. **速度快**: 比 pip 快 10-100 倍
2. **一体化工具**: 替代 pip、pip-tools、virtualenv、pipx
3. **现代功能**: 支持 pyproject.toml、锁定文件、依赖解析
4. **跨平台**: 支持 Windows、macOS、Linux
5. **与现有工具兼容**: 与 pip、setuptools、poetry 兼容

## 安装 uv

### Linux/macOS
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 使用 pip
```bash
pip install uv
```

## 基本使用

### 1. 创建虚拟环境
```bash
# 创建 .venv 虚拟环境
uv venv

# 指定 Python 版本
uv venv --python 3.12

# 指定虚拟环境路径
uv venv --path .venv
```

### 2. 激活虚拟环境
```bash
# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. 安装依赖
```bash
# 从 pyproject.toml 安装
uv pip install -e .

# 安装开发依赖
uv pip install -e ".[dev]"

# 安装特定组
uv pip install -e ".[llm,vector-db]"

# 安装所有可选依赖
uv pip install -e ".[all]"
```

### 4. 同步依赖
```bash
# 同步虚拟环境与锁文件
uv sync

# 生成/更新锁文件
uv lock

# 升级所有依赖
uv pip compile --upgrade pyproject.toml -o uv.lock
uv sync
```

## 项目中的 uv 配置

### pyproject.toml 配置
```toml
# uv 特定配置
[tool.uv.sources]
pypi = { url = "https://pypi.org/simple/" }

# 可选：自定义索引源
# [tool.uv.sources]
# pypi = { url = "https://pypi.org/simple/" }
# private = { url = "https://private.pypi.org/simple/", username = "token", password = { env = "PYPI_TOKEN" } }
```

### Makefile 命令
项目提供了以下 `make` 命令来简化 uv 的使用：

```bash
# 创建虚拟环境
make uv-venv

# 安装生产依赖
make uv-install

# 安装开发依赖
make uv-dev-install

# 同步依赖
make uv-sync

# 更新锁文件
make uv-lock

# 更新所有依赖
make uv-update

# 运行所有检查
make uv-check
```

## 开发工作流

### 1. 初始设置
```bash
# 克隆项目
git clone https://github.com/Lykr/agent.git
cd agent

# 创建虚拟环境并安装依赖
make dev
# 或手动
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 2. 日常开发
```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行测试
make test

# 代码检查
make lint

# 代码格式化
make format

# 类型检查
make type-check
```

### 3. 添加新依赖
```bash
# 编辑 pyproject.toml，添加依赖
# 然后更新锁文件并同步
make uv-update
```

### 4. 清理
```bash
# 清理所有临时文件
make clean

# 重新创建虚拟环境
rm -rf .venv
make dev
```

## 高级功能

### 1. 依赖解析
```bash
# 查看依赖树
uv pip tree

# 检查依赖冲突
uv pip check

# 列出过时的包
uv pip list --outdated
```

### 2. 环境管理
```bash
# 创建多个环境
uv venv --python 3.11 .venv-311
uv venv --python 3.12 .venv-312

# 在不同环境间切换
source .venv-311/bin/activate
source .venv-312/bin/activate
```

### 3. 锁定文件管理
```bash
# 生成锁定文件
uv lock

# 从锁定文件安装
uv pip sync uv.lock

# 更新特定包
uv pip compile --upgrade-package pydantic pyproject.toml -o uv.lock
```

### 4. 脚本运行
```bash
# 在虚拟环境中运行脚本
uv run python script.py

# 运行测试
uv run pytest

# 运行任意命令
uv run black src tests
```

## 故障排除

### 1. 权限问题
```bash
# 如果遇到权限错误
chmod +x .venv/bin/activate
```

### 2. 依赖冲突
```bash
# 清理并重新安装
make clean
make dev
```

### 3. 锁定文件问题
```bash
# 重新生成锁定文件
rm uv.lock
make uv-lock
make uv-sync
```

### 4. 虚拟环境问题
```bash
# 删除并重新创建
rm -rf .venv
make uv-venv
source .venv/bin/activate
make uv-dev-install
```

## 性能提示

1. **使用缓存**: uv 会自动缓存下载的包
2. **并行安装**: uv 支持并行安装依赖
3. **增量更新**: 只更新变化的依赖
4. **预编译**: 预编译常用包以加快安装

## 与其它工具比较

| 功能 | uv | pip + venv | poetry | pdm |
|------|-----|------------|---------|-----|
| 速度 | ⚡ 极快 | 🐢 慢 | 🚀 快 | 🚀 快 |
| 虚拟环境 | ✅ 内置 | ✅ 需要 | ✅ 内置 | ✅ 内置 |
| 锁定文件 | ✅ 支持 | ❌ 需要 pip-tools | ✅ 支持 | ✅ 支持 |
| 依赖组 | ✅ 支持 | ❌ 不支持 | ✅ 支持 | ✅ 支持 |
| 脚本运行 | ✅ uv run | ❌ 需要激活 | ✅ poetry run | ✅ pdm run |

## 更多资源

- [uv 官方文档](https://docs.astral.sh/uv/)
- [uv GitHub 仓库](https://github.com/astral-sh/uv)
- [uv 基准测试](https://github.com/astral-sh/uv#benchmarks)
- [Python 包管理指南](https://packaging.python.org/en/latest/)

## 项目特定提示

对于本 AI Agent 项目：

1. **开发依赖**: 使用 `make uv-dev-install` 安装所有开发工具
2. **AI 依赖**: 可选依赖组 `llm`、`vector-db` 包含 AI 相关包
3. **测试**: 使用 `make test` 运行完整的测试套件
4. **代码质量**: 使用 `make uv-check` 运行所有代码检查

享受快速的 Python 开发体验！ 🚀