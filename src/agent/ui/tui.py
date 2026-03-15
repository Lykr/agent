"""
Agent TUI (Terminal User Interface)

提供简洁优雅的终端界面，实时显示Agent运行状态。
"""

import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.markdown import Markdown


class AgentTUI:
    """Agent终端用户界面"""

    def __init__(self, agent_name: str = "AI Agent"):
        """
        初始化TUI

        Args:
            agent_name: Agent名称
        """
        self.console = Console()
        self.agent_name = agent_name
        self.live: Optional[Live] = None

        # 状态跟踪
        self.current_phase: str = "空闲"
        self.current_content: str = ""
        self.tool_calls: List[Dict] = []
        self.memory_updates: List[Dict] = []
        self.start_time: Optional[float] = None
        self.step_count: int = 0
        self.input_text: str = "等待输入..."
        self.waiting_for_input: bool = False

        # 颜色主题
        self.colors = {
            "primary": "cyan",
            "secondary": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "info": "magenta",
            "phase": "bright_cyan",
            "tool": "bright_yellow",
            "memory": "bright_magenta",
            "input": "bright_white",
            "cursor": "bright_green",
        }

    def _create_header(self) -> Panel:
        """创建头部面板"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header_text = Text()
        header_text.append(f"🤖 {self.agent_name}", style=f"bold {self.colors['primary']}")
        header_text.append(" | ")
        header_text.append("状态: ", style="dim")
        header_text.append(self.current_phase, style=f"bold {self.colors['phase']}")
        header_text.append(" | ")
        header_text.append("步骤: ", style="dim")
        header_text.append(str(self.step_count), style="bold")
        header_text.append(" | ")
        header_text.append(now, style="dim")

        return Panel(
            header_text,
            title="[bold]AI Agent 控制台[/bold]",
            border_style=self.colors["primary"],
            padding=(1, 1),  # 上下各1行内边距，使面板更清晰
        )

    def _create_status_panel(self) -> Panel:
        """创建状态面板"""
        status_table = Table(show_header=False, box=None, padding=(0, 1))
        status_table.add_column("项目", style="dim", width=12)
        status_table.add_column("值", style="bold")

        # 运行时间
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_str = f"{elapsed:.1f}s"
        else:
            elapsed_str = "0.0s"

        status_table.add_row("运行时间", elapsed_str)
        status_table.add_row("当前阶段", f"[{self.colors['phase']}]{self.current_phase}[/]")
        status_table.add_row("工具调用", str(len(self.tool_calls)))
        status_table.add_row("记忆更新", str(len(self.memory_updates)))

        return Panel(
            status_table,
            title="[bold]状态[/bold]",
            border_style=self.colors["secondary"],
            padding=(1, 1),
        )

    def _create_activity_panel(self) -> Panel:
        """创建活动面板"""
        activity_content = []

        if self.current_content:
            # 当前活动
            activity_content.append(
                Text("当前活动: ", style="bold") +
                Text(self.current_content, style=self.colors["info"])
            )
            activity_content.append("")  # 空行

        # 最近工具调用
        if self.tool_calls:
            activity_content.append(Text("最近工具调用:", style="bold"))
            for tool in self.tool_calls[-3:]:  # 显示最近3个
                tool_name = tool.get("name", "未知工具")
                tool_input = tool.get("input", "")[:50]
                if len(tool.get("input", "")) > 50:
                    tool_input += "..."

                activity_content.append(
                    Text(f"  • {tool_name}: ", style=self.colors["tool"]) +
                    Text(tool_input, style="dim")
                )
            activity_content.append("")  # 空行

        # 最近记忆更新
        if self.memory_updates:
            activity_content.append(Text("最近记忆更新:", style="bold"))
            for memory in self.memory_updates[-2:]:  # 显示最近2个
                memory_type = memory.get("type", "未知")
                memory_content = memory.get("content", "")[:40]
                if len(memory.get("content", "")) > 40:
                    memory_content += "..."

                activity_content.append(
                    Text(f"  • {memory_type}: ", style=self.colors["memory"]) +
                    Text(memory_content, style="dim")
                )

        if not activity_content:
            activity_content.append(Text("等待活动...", style="dim italic"))

        return Panel(
            Group(*activity_content),
            title="[bold]活动日志[/bold]",
            border_style=self.colors["info"],
            padding=(1, 1),
        )

    def _create_input_panel(self) -> Panel:
        """创建输入面板"""
        input_text = Text()

        # 显示输入文本（包含 "> " 前缀）
        if self.input_text.startswith("> "):
            # 分开样式：提示符用绿色，内容用输入颜色
            input_text.append("> ", style="bold green")
            content = self.input_text[2:]  # 移除 "> " 前缀
            input_text.append(content, style=self.colors["input"])
        else:
            # 没有前缀，直接显示
            input_text.append(self.input_text, style=self.colors["input"])

        # 添加光标（如果正在等待输入）
        if self.waiting_for_input:
            input_text.append("█", style=f"bold {self.colors['cursor']}")

        return Panel(
            input_text,
            title="[bold]输入[/bold]",
            border_style=self.colors["success"],
            padding=(1, 1),
        )

    def _create_layout(self) -> Layout:
        """创建布局"""
        layout = Layout()

        # 分割布局: 顶部留空、头部、主区域、输入区域
        layout.split(
            Layout(name="top_padding", size=1),
            Layout(name="header", size=5),
            Layout(name="main"),
            Layout(name="input", size=5),
        )

        # 主区域进一步分割为左右两部分
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=3),
        )

        # 填充内容
        layout["top_padding"].update("")  # 顶部留空，避免被终端顶部截断
        layout["header"].update(self._create_header())
        layout["left"].update(self._create_status_panel())
        layout["right"].update(self._create_activity_panel())
        layout["input"].update(self._create_input_panel())

        return layout

    def start(self) -> None:
        """启动TUI"""
        self.live = Live(
            self._create_layout(),
            console=self.console,
            refresh_per_second=2,  # 很低的刷新频率，避免干扰
            screen=False,
            transient=False,  # 不清除屏幕上的旧内容
        )
        self.live.start()
        self.start_time = time.time()

    def stop(self) -> None:
        """停止TUI"""
        if self.live:
            self.live.stop()
            self.live = None

    def update(self, phase: str, content: str) -> None:
        """
        更新TUI显示

        Args:
            phase: 阶段名称（感知、思考、执行、工具、记忆等）
            content: 内容描述
        """
        self.current_phase = phase
        self.current_content = content

        # 记录工具调用
        if phase == "工具":
            tool_name = content.split("执行")[1].split("，")[0].strip() if "执行" in content else "未知工具"
            self.tool_calls.append({
                "name": tool_name,
                "input": content,
                "time": time.time()
            })
            # 保持最近10个工具调用
            if len(self.tool_calls) > 10:
                self.tool_calls = self.tool_calls[-10:]

        # 记录记忆更新
        elif phase == "记忆":
            memory_type = "长期" if "长期" in content else "短期"
            self.memory_updates.append({
                "type": memory_type,
                "content": content,
                "time": time.time()
            })
            # 保持最近5个记忆更新
            if len(self.memory_updates) > 5:
                self.memory_updates = self.memory_updates[-5:]

        # 更新步骤计数
        if phase == "步骤" and "第" in content:
            try:
                step_part = content.split("第")[1].split("/")[0]
                self.step_count = int(step_part)
            except (IndexError, ValueError):
                pass

        # 刷新显示
        if self.live:
            self.live.update(self._create_layout())

    def set_input_text(self, text: str) -> None:
        """
        更新输入面板文本

        Args:
            text: 要显示的文本
        """
        self.input_text = text
        self.waiting_for_input = False  # 显示文本时不显示光标
        if self.live:
            self.live.update(self._create_layout())

    def set_waiting_for_input(self, waiting: bool) -> None:
        """
        设置输入等待状态

        Args:
            waiting: 是否正在等待输入
        """
        self.waiting_for_input = waiting
        if self.live:
            self.live.update(self._create_layout())

    def log_message(self, role: str, message: str) -> None:
        """
        记录对话消息

        Args:
            role: 角色（user/assistant）
            message: 消息内容
        """
        # 可以扩展此方法以在TUI中显示对话历史
        pass  # pragma: no cover

    def show_final_response(self, response: str, wait_for_input: bool = True) -> None:
        """
        显示最终回复

        Args:
            response: Agent的最终回复
            wait_for_input: 是否等待用户输入（在非交互式环境中设为False）
        """
        if self.live:
            # 记录最终回复到活动日志
            self.memory_updates.append({
                "type": "回复",
                "content": response[:100] + "..." if len(response) > 100 else response,
                "time": time.time()
            })

            # 保持最近5个记忆更新
            if len(self.memory_updates) > 5:
                self.memory_updates = self.memory_updates[-5:]

            # 更新TUI显示
            if self.live:
                self.live.update(self._create_layout())

            # 在控制台显示完整回复（在TUI下方）
            self.console.print()
            self.console.print("[bold green]🤖 Agent 回复:[/bold green]")
            self.console.print(response)
            self.console.print()


def create_tui_logger(agent_name: str = "AI Agent") -> Tuple[Callable[[str, str], None], AgentTUI]:
    """
    创建TUI日志回调函数和TUI实例

    Args:
        agent_name: Agent名称

    Returns:
        (日志回调函数, TUI实例)
    """
    tui = AgentTUI(agent_name)

    def log_callback(phase: str, content: str) -> None:
        """TUI日志回调函数"""
        tui.update(phase, content)

    return log_callback, tui


def run_with_tui(agent_factory, agent_name: str = "AI Agent") -> None:
    """
    使用TUI运行Agent的便捷函数

    Args:
        agent_factory: 创建Agent的函数
        agent_name: Agent名称
    """
    from rich.console import Console

    console = Console()

    # 创建TUI
    log_callback, tui = create_tui_logger(agent_name)

    try:
        # 创建Agent（传入TUI日志回调）
        agent = agent_factory(on_log=log_callback)

        console.print(f"\n[bold {tui.colors['primary']}]Agent 已启动 ({agent.config.name})[/]")
        console.print(f"[dim]可用工具: {list(agent.tools.keys())}[/]")

        # 启动TUI
        tui.start()

        console.print("\n[dim]输入 'quit' 或 'exit' 退出[/]\n")

        # 初始化输入面板
        tui.set_input_text("> 等待输入...")

        while True:
            # 更新输入面板显示准备输入状态（显示光标）
            tui.set_input_text("> ")
            tui.set_waiting_for_input(True)

            try:
                # 获取用户输入（使用空提示，输入面板已显示提示符和光标）
                # 注意：用户输入时字符显示在终端光标位置，输入面板仅显示提示和输入后的内容
                user_input = console.input(prompt="").strip()
            except KeyboardInterrupt:
                console.print("\n[yellow]中断，退出...[/]")
                tui.set_waiting_for_input(False)
                tui.set_input_text("已中断")
                break
            except EOFError:
                console.print("\n[yellow]EOF，退出...[/]")
                tui.set_waiting_for_input(False)
                tui.set_input_text("已退出")
                break

            # 更新输入面板显示用户输入的内容（隐藏光标）
            tui.set_waiting_for_input(False)
            if user_input:
                display_text = user_input[:50] + "..." if len(user_input) > 50 else user_input
                tui.set_input_text(f"> {display_text}")
                # 短暂显示用户输入
                time.sleep(1.0)
            else:
                tui.set_input_text("> 等待输入...")
                continue

            if user_input.lower() in ("quit", "exit"):
                console.print("[green]再见！[/]")
                tui.set_input_text("已退出")
                break

            # 运行Agent
            response = agent.run(user_input)

            # 显示最终回复
            tui.show_final_response(response, wait_for_input=False)

            # 重置输入面板等待下一次输入
            tui.set_input_text("> 等待输入...")

    finally:
        # 确保TUI被正确关闭
        tui.stop()