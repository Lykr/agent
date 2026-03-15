# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A teaching-oriented AI Agent framework (Chinese documentation) for learning AI Agent concepts. It implements a perceive-think-act loop with tool calling, memory, and LLM integration via DeepSeek API. Educational focus — not for production deployment.

## Commands

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"    # or: make setup

# Test
pytest tests/ -v --cov=src/agent --cov-report=term-missing   # or: make test
pytest tests/test_agent.py -v                                  # single test file
pytest tests/test_agent.py::TestClassName::test_method -v      # single test

# Code quality
ruff check src tests          # or: make lint
black src tests               # or: make format
mypy src                      # or: make type-check
make uv-check                 # run all checks (lint + type-check + test)
```

## Architecture

The agent runs a **perceive → think → act** loop (`Agent.run()` in `src/agent/core/agent.py`):

1. **Perceive** (`_perceive`): Builds message context from system prompt + conversation history + user input
2. **Think** (`_think`): Calls LLM to generate a response
3. **Act** (`_act`): Parses response for JSON tool calls, executes tools, feeds results back to LLM for follow-up

Key modules under `src/agent/`:

- **`core/`** — `Agent` (main orchestrator), `StateManager`/`AgentState` (session state, conversation history, tool call records via Pydantic models), `AgentConfig`/`ConfigManager` (layered config: defaults → YAML → env vars)
- **`llm/`** — `BaseLLM` abstract interface with `generate()` and `chat()` methods. `DeepSeekLLM` is the concrete implementation using the OpenAI-compatible chat completions API
- **`tools/`** — `BaseTool` ABC (implement `name`, `description`, `_execute_impl`). `FileSystemTool` adds path permission checks. `ToolRegistry` for registration. File tools: read, write, list, info, search
- **`modules/`** — Placeholder packages for perception, reasoning, execution, memory (not yet implemented)

## Configuration

Config is loaded in priority order: defaults → YAML file (`configs/`) → environment variables. The `.env` file requires `DEEPSEEK_API_KEY` and `DEEPSEEK_BASE_URL`. See `.env.example` for all options.

## Adding New Tools

Subclass `BaseTool`, implement `name`, `description`, and `_execute_impl(input_text: str) -> str`. For file system tools, subclass `FileSystemTool` instead.

## Adding New LLM Providers

Subclass `BaseLLM`, implement `generate()`, `chat()`, and `get_model_info()`.

## Style

- Python 3.9+, line length 88 (black + ruff)
- Pydantic v2 for data models and config
- All code and comments are in Chinese; maintain this convention

## Working Style Guidelines

When working on this project, follow these principles:

### Be Concise
- Keep thinking and answers brief and to the point
- Avoid unnecessary explanations unless specifically requested
- Focus on the task at hand without digressions

### Do Only What's Requested
- Do not add features, refactor code, or make "improvements" beyond what was explicitly asked
- A bug fix doesn't need surrounding code cleaned up
- A simple feature doesn't need extra configurability
- Do not add docstrings, comments, or type annotations to code you didn't change
- Only add comments where the logic isn't self-evident

### Avoid Over-Engineering
- Do not create helpers, utilities, or abstractions for one-time operations
- Do not design for hypothetical future requirements
- The right amount of complexity is the minimum needed for the current task
- Three similar lines of code is better than a premature abstraction

### Trust Internal Code
- Do not add error handling, fallbacks, or validation for scenarios that can't happen
- Trust internal code and framework guarantees
- Only validate at system boundaries (user input, external APIs)
- Do not use feature flags or backwards-compatibility shims when you can just change the code
