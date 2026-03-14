"""
状态管理模块测试
"""

from datetime import datetime
from src.agent.core.state import StateManager, AgentState, ToolCall, Message


class TestMessage:
    """Message 测试"""

    def test_message_creation(self):
        """测试消息创建"""
        message = Message(role="user", content="Hello")

        assert message.role == "user"
        assert message.content == "Hello"
        assert isinstance(message.timestamp, datetime)

    def test_message_equality(self):
        """测试消息相等性"""
        msg1 = Message(role="user", content="Hello")
        msg2 = Message(role="user", content="Hello")

        # 时间戳不同，所以不相等
        assert msg1 != msg2
        assert msg1.content == msg2.content


class TestToolCall:
    """ToolCall 测试"""

    def test_tool_call_creation(self):
        """测试工具调用创建"""
        tool_call = ToolCall(
            tool_name="read_file",
            input_text="test.txt",
            output_text="File content"
        )

        assert tool_call.tool_name == "read_file"
        assert tool_call.input_text == "test.txt"
        assert tool_call.output_text == "File content"
        assert tool_call.success is True
        assert isinstance(tool_call.timestamp, datetime)

    def test_tool_call_with_error(self):
        """测试错误工具调用"""
        tool_call = ToolCall(
            tool_name="read_file",
            input_text="test.txt",
            output_text="File not found",
            success=False
        )

        assert tool_call.success is False


class TestAgentState:
    """AgentState 测试"""

    def test_state_creation(self):
        """测试状态创建"""
        state = AgentState(session_id="test-session")

        assert state.session_id == "test-session"
        assert state.current_step == 0
        assert state.is_running is False
        assert state.last_error is None
        assert state.messages == []
        assert state.tool_calls == []
        assert state.context == {}

    def test_add_message(self):
        """测试添加消息"""
        state = AgentState(session_id="test")

        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi there")

        assert len(state.messages) == 2
        assert state.messages[0].role == "user"
        assert state.messages[0].content == "Hello"
        assert state.messages[1].role == "assistant"
        assert state.messages[1].content == "Hi there"

    def test_add_tool_call(self):
        """测试添加工具调用"""
        state = AgentState(session_id="test")

        state.add_tool_call("read_file", "test.txt", "Content")
        state.add_tool_call("write_file", "test.txt", "Done", success=False)

        assert len(state.tool_calls) == 2
        assert state.tool_calls[0].tool_name == "read_file"
        assert state.tool_calls[0].success is True
        assert state.tool_calls[1].tool_name == "write_file"
        assert state.tool_calls[1].success is False

    def test_increment_step(self):
        """测试增加步骤"""
        state = AgentState(session_id="test")

        assert state.current_step == 0
        state.increment_step()
        assert state.current_step == 1
        state.increment_step()
        assert state.current_step == 2

    def test_reset_steps(self):
        """测试重置步骤"""
        state = AgentState(session_id="test")
        state.current_step = 5

        state.reset_steps()
        assert state.current_step == 0

    def test_get_conversation_history(self):
        """测试获取对话历史"""
        state = AgentState(session_id="test")

        # 添加一些消息
        for i in range(10):
            state.add_message("user", f"Message {i}")

        # 获取所有历史
        history = state.get_conversation_history()
        assert len(history) == 10

        # 获取最近5条
        recent = state.get_conversation_history(max_messages=5)
        assert len(recent) == 5
        assert recent[0]["content"] == "Message 5"
        assert recent[4]["content"] == "Message 9"

    def test_get_recent_tool_calls(self):
        """测试获取最近工具调用"""
        state = AgentState(session_id="test")

        # 添加一些工具调用
        for i in range(10):
            state.add_tool_call(f"tool_{i}", f"input_{i}", f"output_{i}")

        # 获取最近3个
        recent = state.get_recent_tool_calls(3)
        assert len(recent) == 3
        assert recent[0].tool_name == "tool_7"
        assert recent[2].tool_name == "tool_9"

    def test_clear_history(self):
        """测试清空历史"""
        state = AgentState(session_id="test")

        # 添加一些数据
        state.add_message("user", "Hello")
        state.add_tool_call("test", "input", "output")
        state.context["key"] = "value"
        state.current_step = 5

        # 清空历史
        state.clear_history()

        assert len(state.messages) == 0
        assert len(state.tool_calls) == 0
        assert len(state.context) == 0
        assert state.current_step == 0

    def test_to_dict(self):
        """测试转换为字典"""
        state = AgentState(session_id="test-session-123")
        state.add_message("user", "Hello")
        state.add_tool_call("test", "input", "output")
        state.context["test_key"] = "test_value"

        state_dict = state.to_dict()

        assert state_dict["session_id"] == "test-session-123"
        assert state_dict["current_step"] == 0
        assert state_dict["message_count"] == 1
        assert state_dict["tool_call_count"] == 1
        assert "test_key" in state_dict["context_keys"]

    def test_str_representation(self):
        """测试字符串表示"""
        state = AgentState(session_id="test-session-12345")
        state.add_message("user", "Hello")
        state.add_tool_call("test", "input", "output")

        str_repr = str(state)
        assert "test-ses" in str_repr  # 截断的session_id (前8个字符)
        assert "step=0" in str_repr
        assert "messages=1" in str_repr
        assert "tools=1" in str_repr


class TestStateManager:
    """StateManager 测试"""

    def test_manager_creation(self):
        """测试管理器创建"""
        manager = StateManager("test-session")
        state = manager.get_state()

        assert state.session_id == "test-session"
        assert state.is_running is False

    def test_auto_session_id(self):
        """测试自动生成会话ID"""
        manager1 = StateManager()
        manager2 = StateManager()

        assert manager1.state.session_id != manager2.state.session_id
        assert len(manager1.state.session_id) == 36  # UUID长度

    def test_start_stop(self):
        """测试开始和停止"""
        manager = StateManager()

        assert manager.state.is_running is False
        manager.start()
        assert manager.state.is_running is True
        manager.stop()
        assert manager.state.is_running is False

    def test_record_error(self):
        """测试记录错误"""
        manager = StateManager()

        assert manager.state.last_error is None
        manager.record_error("Test error")
        assert manager.state.last_error == "Test error"
        manager.clear_error()
        assert manager.state.last_error is None

    def test_context_management(self):
        """测试上下文管理"""
        manager = StateManager()

        manager.set_context("key1", "value1")
        manager.set_context("key2", 123)

        assert manager.get_context("key1") == "value1"
        assert manager.get_context("key2") == 123
        assert manager.get_context("key3") is None
        assert manager.get_context("key3", "default") == "default"

    def test_reset(self):
        """测试重置"""
        manager = StateManager()

        # 添加一些数据
        manager.start()
        manager.state.add_message("user", "Hello")
        manager.state.add_tool_call("test", "input", "output")
        manager.set_context("key", "value")
        manager.record_error("Test error")

        # 重置（不清空历史）
        manager.reset(clear_history=False)

        assert manager.state.is_running is False
        assert manager.state.last_error is None
        assert manager.state.current_step == 0
        # 历史应该保留
        assert len(manager.state.messages) == 1
        assert len(manager.state.tool_calls) == 1
        assert len(manager.state.context) == 1

        # 重置（清空历史）
        manager.reset(clear_history=True)

        assert len(manager.state.messages) == 0
        assert len(manager.state.tool_calls) == 0
        assert len(manager.state.context) == 0


if __name__ == "__main__":
    # 运行测试
    import pytest
    pytest.main([__file__, "-v"])