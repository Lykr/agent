#!/usr/bin/env python3
"""
交互式 Agent 运行脚本 - 带TUI界面

支持命令行参数配置，提供丰富的交互体验。
使用示例:
  python run_tui.py
  python run_tui.py --config configs/custom.yaml --name "我的助手"
  python run_tui.py --dir . --dir ./data --no-memory

依赖: 需要安装 UI 可选依赖 (rich)。
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Callable

# 检查必要依赖
try:
    from rich.console import Console
except ImportError:
    print("错误: 缺少 rich 库，请安装 UI 依赖")
    print("安装命令: uv pip install -e '.[ui]' 或 pip install rich")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.agent.core.agent import Agent
    from src.agent.llm.deepseek import DeepSeekLLM
    from src.agent.tools.file_tools import FileToolsFactory
    from src.agent.tools.memory_tools import MEMORY_TOOLS
    from src.agent.ui import run_with_tui
except ImportError as e:
    print(f"错误: 无法导入 Agent 模块: {e}")
    print("请确保已安装项目依赖: uv pip install -e '.[dev]'")
    sys.exit(1)


def create_agent(
    on_log: Optional[Callable[[str, str], None]] = None,
    config_path: Optional[str] = None,
    allowed_directories: Optional[list[str]] = None,
    agent_name: Optional[str] = None,
    include_memory_tools: bool = True,
    enable_planning: bool = False,
    enable_reflection: bool = False,
) -> Agent:
    """
    创建 Agent 的工厂函数

    Args:
        on_log: 日志回调函数
        config_path: 配置文件路径
        allowed_directories: 允许访问的目录列表
        agent_name: Agent 名称（覆盖配置）
        include_memory_tools: 是否包含记忆工具

    Returns:
        Agent 实例
    """
    # 创建 LLM
    try:
        llm = DeepSeekLLM()
    except Exception as e:
        raise RuntimeError(f"创建 LLM 失败: {e}") from e

    # 设置文件工具允许访问的目录
    if allowed_directories is None:
        allowed_directories = [os.getcwd()]
    else:
        # 转换为绝对路径
        allowed_directories = [str(Path(dir_path).absolute()) for dir_path in allowed_directories]

    # 创建文件工具
    file_tools = FileToolsFactory.create_basic_tools(
        allowed_directories=allowed_directories,
    )

    # 创建工具列表
    all_tools = list(file_tools)

    # 添加记忆工具（如果启用）
    if include_memory_tools:
        all_tools.extend(MEMORY_TOOLS)

    # 创建 Agent
    agent = Agent(
        llm=llm, tools=all_tools, on_log=on_log, config=config_path,
        enable_planning=enable_planning, enable_reflection=enable_reflection,
    )

    # 覆盖 Agent 名称（如果提供）
    if agent_name:
        agent.config.name = agent_name

    return agent


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="运行带 TUI 界面的 AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s
  %(prog)s --config configs/custom.yaml
  %(prog)s --name "我的助手" --dir . --dir ./data
  %(prog)s --help
        """
    )
    parser.add_argument(
        "--config",
        "-c",
        help="配置文件路径 (YAML格式)",
        default=None,
    )
    parser.add_argument(
        "--name",
        "-n",
        help="Agent 名称 (覆盖配置)",
        default=None,
    )
    parser.add_argument(
        "--dir",
        "-d",
        action="append",
        help="允许访问的目录 (可多次使用)",
        default=None,
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="禁用记忆工具",
        default=False,
    )
    parser.add_argument(
        "--planning",
        "-p",
        action="store_true",
        help="启用任务规划（将复杂任务分解为子任务）",
        default=False,
    )
    parser.add_argument(
        "--reflection",
        "-r",
        action="store_true",
        help="启用反思（任务完成后分析执行过程）",
        default=False,
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    console = Console()

    # 显示启动信息
    console.print(f"[bold cyan]🤖 启动 AI Agent TUI[/bold cyan]")
    console.print(f"[dim]Agent 名称: {args.name or '使用配置默认值'}[/dim]")

    # 检查配置文件
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            console.print(f"[green]使用配置文件: {config_path}[/green]")
        else:
            console.print(f"[yellow]警告: 配置文件不存在: {config_path}[/yellow]")
            console.print("[dim]将使用默认配置[/dim]")

    # 检查允许访问的目录
    if args.dir:
        for i, dir_path in enumerate(args.dir, 1):
            dir_path_obj = Path(dir_path)
            if dir_path_obj.exists():
                console.print(f"[green]允许访问目录 {i}: {dir_path_obj.absolute()}[/green]")
            else:
                console.print(f"[yellow]警告: 目录不存在: {dir_path_obj}[/yellow]")
    else:
        console.print(f"[dim]允许访问目录: 当前工作目录 ({os.getcwd()})[/dim]")

    # 记忆工具状态
    if args.no_memory:
        console.print("[yellow]记忆工具: 禁用[/yellow]")
    else:
        console.print("[green]记忆工具: 启用[/green]")

    # 高级功能状态
    if args.planning:
        console.print("[cyan]任务规划: 启用[/cyan]")
    if args.reflection:
        console.print("[cyan]反思引擎: 启用[/cyan]")

    # 检查 DeepSeek API 密钥
    if not os.getenv("DEEPSEEK_API_KEY"):
        console.print("[yellow]警告: 未设置 DEEPSEEK_API_KEY 环境变量[/yellow]")
        console.print("[dim]请设置环境变量或创建 .env 文件[/dim]")
        console.print("[dim]示例: export DEEPSEEK_API_KEY='your-key-here'[/dim]")

    # 创建 Agent 工厂函数（闭包捕获参数）
    def agent_factory(on_log=None):
        return create_agent(
            on_log=on_log,
            config_path=args.config,
            allowed_directories=args.dir,
            agent_name=args.name,
            include_memory_tools=not args.no_memory,
            enable_planning=args.planning,
            enable_reflection=args.reflection,
        )

    # 使用 TUI 运行 Agent
    console.print("\n[bold cyan]启动 TUI 界面...[/bold cyan]")
    console.print("[dim]输入 'quit' 或 'exit' 退出，按 Ctrl+C 中断[/dim]\n")

    run_with_tui(agent_factory, agent_name=args.name or "教学AI助手")


if __name__ == "__main__":
    main()