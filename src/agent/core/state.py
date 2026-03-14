"""
Agent 状态管理模块

管理Agent的运行状态，包括对话历史、工具调用记录、当前步骤等。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """运行日志条目"""
    phase: str = Field(description="阶段: 感知/思考/执行/工具")
    content: str = Field(description="日志内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="日志时间")


class ToolCall(BaseModel):
    """工具调用记录"""
    tool_name: str = Field(description="工具名称")
    input_text: str = Field(description="输入文本")
    output_text: str = Field(description="输出文本")
    timestamp: datetime = Field(default_factory=datetime.now, description="调用时间")
    success: bool = Field(default=True, description="是否成功")


class Message(BaseModel):
    """消息记录"""
    role: str = Field(description="角色: user, assistant, system, tool")
    content: str = Field(description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间")


class AgentState(BaseModel):
    """Agent 运行状态"""

    # 会话信息
    session_id: str = Field(description="会话ID")
    start_time: datetime = Field(default_factory=datetime.now, description="开始时间")

    # 执行状态
    current_step: int = Field(default=0, description="当前步骤")
    is_running: bool = Field(default=False, description="是否正在运行")
    last_error: Optional[str] = Field(default=None, description="最后错误信息")

    # 历史记录
    messages: List[Message] = Field(default_factory=list, description="消息历史")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="工具调用历史")
    logs: List[LogEntry] = Field(default_factory=list, description="运行日志")

    # 上下文数据
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文数据")

    def add_log(self, phase: str, content: str) -> None:
        """添加运行日志"""
        self.logs.append(LogEntry(phase=phase, content=content))

    def drain_logs(self) -> List[LogEntry]:
        """取出并清空所有日志"""
        logs = list(self.logs)
        self.logs.clear()
        return logs

    def add_message(self, role: str, content: str) -> None:
        """添加消息到历史"""
        self.messages.append(Message(role=role, content=content))

    def add_tool_call(self, tool_name: str, input_text: str, output_text: str, success: bool = True) -> None:
        """添加工具调用记录"""
        self.tool_calls.append(ToolCall(
            tool_name=tool_name,
            input_text=input_text,
            output_text=output_text,
            success=success
        ))

    def increment_step(self) -> None:
        """增加步骤计数"""
        self.current_step += 1

    def reset_steps(self) -> None:
        """重置步骤计数"""
        self.current_step = 0

    def get_conversation_history(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        """获取对话历史，用于LLM上下文"""
        messages = self.messages
        if max_messages:
            messages = messages[-max_messages:]

        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def get_recent_tool_calls(self, count: int = 5) -> List[ToolCall]:
        """获取最近的工具调用"""
        return self.tool_calls[-count:] if self.tool_calls else []

    def clear_history(self) -> None:
        """清空历史记录"""
        self.messages.clear()
        self.tool_calls.clear()
        self.logs.clear()
        self.context.clear()
        self.reset_steps()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "current_step": self.current_step,
            "is_running": self.is_running,
            "last_error": self.last_error,
            "message_count": len(self.messages),
            "tool_call_count": len(self.tool_calls),
            "context_keys": list(self.context.keys()),
        }

    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"AgentState(session={self.session_id[:8]}..., "
            f"step={self.current_step}, "
            f"messages={len(self.messages)}, "
            f"tools={len(self.tool_calls)})"
        )


class StateManager:
    """状态管理器"""

    def __init__(self, session_id: Optional[str] = None):
        """
        初始化状态管理器

        Args:
            session_id: 会话ID，如果为None则生成一个
        """
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())

        self.state = AgentState(session_id=session_id)

    def start(self) -> None:
        """开始运行"""
        self.state.is_running = True
        self.state.start_time = datetime.now()

    def stop(self) -> None:
        """停止运行"""
        self.state.is_running = False

    def record_error(self, error: str) -> None:
        """记录错误"""
        self.state.last_error = error

    def clear_error(self) -> None:
        """清除错误"""
        self.state.last_error = None

    def set_context(self, key: str, value: Any) -> None:
        """设置上下文数据"""
        self.state.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return self.state.context.get(key, default)

    def get_state(self) -> AgentState:
        """获取当前状态"""
        return self.state

    def reset(self, clear_history: bool = False) -> None:
        """重置状态"""
        if clear_history:
            self.state.clear_history()
        else:
            self.state.reset_steps()
        self.state.is_running = False
        self.state.last_error = None


if __name__ == "__main__":
    # 测试状态管理
    manager = StateManager()
    manager.start()

    # 添加一些测试数据
    manager.state.add_message("user", "你好")
    manager.state.add_message("assistant", "你好！有什么可以帮助你的？")
    manager.state.add_tool_call("read_file", "test.txt", "文件内容...")

    manager.state.increment_step()

    print("状态信息:")
    print(manager.state)
    print("\n状态详情:")
    print(manager.state.to_dict())