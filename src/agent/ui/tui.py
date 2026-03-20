"""
Agent TUI (Terminal User Interface)

提供简洁优雅的终端界面，实时显示Agent运行状态。
使用Textual框架实现。
"""

import time
from datetime import datetime
from typing import Callable, Optional

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, RichLog, Static


class AgentTUIState:
    """Agent TUI状态容器"""

    def __init__(self, agent_name: str = "AI Agent"):
        self.agent_name = agent_name

        # 状态跟踪
        self.current_phase: str = "空闲"
        self.current_content: str = ""
        self.activity_log: list[dict] = []  # 合并的活动日志(工具+记忆)
        self.start_time: Optional[float] = None
        self.step_count: int = 0
        self.is_running: bool = False

    def update(self, phase: str, content: str) -> None:
        """更新TUI状态"""
        self.current_phase = phase
        self.current_content = content

        # 只记录工具调用和记忆更新到活动日志
        if phase in ("工具", "记忆"):
            self.activity_log.append({
                "phase": phase,
                "content": content,
                "time": time.time(),
            })
            if len(self.activity_log) > 20:
                self.activity_log = self.activity_log[-20:]

        if phase == "步骤" and "第" in content:
            try:
                self.step_count = int(content.split("第")[1].split("/")[0])
            except (IndexError, ValueError):
                pass

    def get_elapsed(self) -> str:
        if not self.start_time:
            return "0.0s"
        return f"{time.time() - self.start_time:.1f}s"


class AgentTUI:
    """Agent终端用户界面(公共API)"""

    def __init__(self, agent_name: str = "AI Agent"):
        self.state = AgentTUIState(agent_name)

    def update(self, phase: str, content: str) -> None:
        self.state.update(phase, content)

    def set_input_text(self, text: str) -> None:
        pass  # 兼容旧接口

    def set_waiting_for_input(self, waiting: bool) -> None:
        pass  # 兼容旧接口

    def log_message(self, role: str, message: str) -> None:
        pass  # pragma: no cover

    def show_final_response(self, response: str, wait_for_input: bool = True) -> None:
        self.state.update("回复", response)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class AgentTUIApp(App):
    """Agent TUI 应用"""

    CSS = """
    Screen {
        background: $surface;
        layers: base;
    }

    /* 主布局: 左侧聊天 + 右侧活动 */
    #main {
        height: 1fr;
    }

    /* 聊天区域 */
    #chat-panel {
        width: 3fr;
        border-right: solid $panel;
    }

    #chat-log {
        height: 1fr;
        padding: 0 1;
    }

    /* 活动面板(右侧) */
    #activity-panel {
        width: 1fr;
    }

    #activity-header {
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
        text-align: center;
    }

    #activity-log {
        height: 1fr;
        padding: 0 1;
    }

    /* 底部状态栏 */
    #status-bar {
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }

    /* 输入区域 */
    #input-area {
        height: 3;
        border-top: solid $panel;
        padding: 0 1;
    }

    Input {
        width: 1fr;
        border: none;
        background: transparent;
    }

    Input:focus {
        border: none;
    }
    """

    def __init__(self, state: AgentTUIState, agent_factory):
        super().__init__()
        self.state = state
        self.agent_factory = agent_factory
        self.agent = None
        self._last_activity_count = 0

    def compose(self) -> ComposeResult:
        """组合UI布局"""
        # 顶部标题栏
        yield Static(id="title-bar")

        # 主区域: 聊天 + 活动面板
        with Horizontal(id="main"):
            # 左侧聊天历史
            with Vertical(id="chat-panel"):
                yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)

            # 右侧活动日志
            with Vertical(id="activity-panel"):
                yield Static("── 活动 ──", id="activity-header")
                yield RichLog(id="activity-log", highlight=False, markup=True, wrap=True)

        # 底部状态栏
        yield Static(id="status-bar")

        # 输入框
        with Vertical(id="input-area"):
            yield Input(placeholder="输入消息… (Ctrl+C 退出)", id="input")

    def on_mount(self) -> None:
        """初始化"""
        self.state.start_time = time.time()
        self.agent = self.agent_factory(on_log=lambda p, c: self.state.update(p, c))
        self._update_title()
        self._update_status()
        self.set_interval(0.5, self._refresh_ui)
        self.query_one("#input", Input).focus()

        # 欢迎消息
        chat = self.query_one("#chat-log", RichLog)
        chat.write(Text("欢迎使用 AI Agent! 输入问题开始对话。", style="dim"))
        chat.write(Text(""))

    def _update_title(self) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        title = self.query_one("#title-bar", Static)
        title.update(f" 🤖 {self.state.agent_name}  [{now}]")

    def _update_status(self) -> None:
        status = self.query_one("#status-bar", Static)
        phase = self.state.current_phase
        elapsed = self.state.get_elapsed()
        steps = self.state.step_count

        if self.state.is_running:
            status_text = f" ⏳ {phase}  |  {elapsed}  |  步骤 {steps}"
        else:
            status_text = f" ○ 就绪  |  {elapsed}  |  步骤 {steps}"
        status.update(status_text)

    def _refresh_ui(self) -> None:
        """定时刷新标题和状态栏"""
        self._update_title()
        self._update_status()

        # 只在有新活动时更新活动日志
        count = len(self.state.activity_log)
        if count > self._last_activity_count:
            activity = self.query_one("#activity-log", RichLog)
            for entry in self.state.activity_log[self._last_activity_count:]:
                phase = entry["phase"]
                content = entry["content"]
                # 截断长内容
                short = content[:60] + "…" if len(content) > 60 else content
                ts = datetime.fromtimestamp(entry["time"]).strftime("%H:%M:%S")
                if phase == "工具":
                    activity.write(Text(f"[{ts}] 🔧 {short}", style="yellow"))
                else:
                    activity.write(Text(f"[{ts}] 💾 {short}", style="blue"))
            self._last_activity_count = count

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理用户输入"""
        user_input = event.value.strip()
        self.query_one("#input", Input).value = ""

        if not user_input:
            return

        if user_input.lower() in ("quit", "exit", "q"):
            self.exit()
            return

        # 显示用户消息
        chat = self.query_one("#chat-log", RichLog)
        chat.write(Text(f"你  {user_input}", style="bold cyan"))
        chat.write(Text(""))

        # 在工作线程运行Agent
        self._run_agent(user_input)

    @work(thread=True)
    def _run_agent(self, user_input: str) -> None:
        """工作线程: 运行Agent并显示回复"""
        self.state.is_running = True
        self.state.update("思考", "正在处理…")

        try:
            response = self.agent.run(user_input)
            self.state.is_running = False
            self.state.update("空闲", "")

            # 在主线程更新聊天
            self.call_from_thread(self._show_response, response)

        except Exception as e:
            self.state.is_running = False
            self.state.update("错误", str(e))
            self.call_from_thread(self._show_error, str(e))

    def _show_response(self, response: str) -> None:
        """在主线程显示Agent回复"""
        chat = self.query_one("#chat-log", RichLog)
        chat.write(Text("AI", style="bold green"))
        # 按行写入, 支持长回复
        for line in response.split("\n"):
            chat.write(Text(line if line else " "))
        chat.write(Text(""))

    def _show_error(self, error: str) -> None:
        """显示错误"""
        chat = self.query_one("#chat-log", RichLog)
        chat.write(Text(f"错误: {error}", style="bold red"))
        chat.write(Text(""))


def create_tui_logger(agent_name: str = "AI Agent") -> tuple[Callable[[str, str], None], AgentTUI]:
    """创建TUI日志回调函数和TUI实例"""
    tui = AgentTUI(agent_name)

    def log_callback(phase: str, content: str) -> None:
        tui.update(phase, content)

    return log_callback, tui


def run_with_tui(agent_factory, agent_name: str = "AI Agent") -> None:
    """使用TUI运行Agent的便捷函数"""
    tui = AgentTUI(agent_name)
    app = AgentTUIApp(tui.state, agent_factory)
    app.run()
