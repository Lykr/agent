"""
短期记忆模块

管理Agent的短期记忆，包括：
1. 对话历史管理
2. 工作记忆（当前任务上下文）
3. 上下文窗口管理
4. 记忆压缩和摘要
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ShortTermMemoryEntry(BaseModel):
    """短期记忆条目"""
    content: str = Field(description="记忆内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="记忆时间")
    importance: float = Field(default=0.5, description="重要性评分 (0-1)")
    category: str = Field(default="general", description="记忆类别")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ShortTermMemory:
    """短期记忆管理器"""

    def __init__(self, max_entries: int = 20, max_history: int = 10):
        """
        初始化短期记忆管理器

        Args:
            max_entries: 最大记忆条目数
            max_history: 最大对话历史数
        """
        self.max_entries = max_entries
        self.max_history = max_history
        self.memories: List[ShortTermMemoryEntry] = []
        self.conversation_history: List[Dict[str, str]] = []
        self.working_memory: Dict[str, Any] = {}

    def add_memory(self, content: str, importance: float = 0.5,
                   category: str = "general", metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        添加短期记忆

        Args:
            content: 记忆内容
            importance: 重要性评分 (0-1)
            category: 记忆类别
            metadata: 元数据
        """
        if metadata is None:
            metadata = {}

        entry = ShortTermMemoryEntry(
            content=content,
            importance=importance,
            category=category,
            metadata=metadata
        )

        self.memories.append(entry)
        self._prune_memories()

    def add_conversation(self, role: str, content: str) -> None:
        """
        添加对话历史

        Args:
            role: 角色 (user, assistant, system, tool)
            content: 内容
        """
        self.conversation_history.append({"role": role, "content": content})
        self._prune_conversation()

    def set_working_memory(self, key: str, value: Any) -> None:
        """
        设置工作记忆

        Args:
            key: 键
            value: 值
        """
        self.working_memory[key] = value

    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """
        获取工作记忆

        Args:
            key: 键
            default: 默认值

        Returns:
            工作记忆值
        """
        return self.working_memory.get(key, default)

    def get_recent_memories(self, count: int = 5, min_importance: float = 0.0) -> List[ShortTermMemoryEntry]:
        """
        获取最近的记忆

        Args:
            count: 数量
            min_importance: 最小重要性

        Returns:
            记忆条目列表
        """
        filtered = [m for m in self.memories if m.importance >= min_importance]
        return filtered[-count:]

    def get_memories_by_category(self, category: str, count: int = 5) -> List[ShortTermMemoryEntry]:
        """
        按类别获取记忆

        Args:
            category: 类别
            count: 数量

        Returns:
            记忆条目列表
        """
        filtered = [m for m in self.memories if m.category == category]
        return filtered[-count:]

    def get_conversation_history(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        """
        获取对话历史

        Args:
            max_messages: 最大消息数，如果为None则使用配置值

        Returns:
            对话历史列表
        """
        if max_messages is None:
            max_messages = self.max_history

        if max_messages <= 0:
            return []

        return self.conversation_history[-max_messages:]

    def get_relevant_memories(self, query: str, count: int = 3) -> List[ShortTermMemoryEntry]:
        """
        获取相关记忆（基于简单关键词匹配）

        Args:
            query: 查询文本
            count: 返回数量

        Returns:
            相关记忆列表
        """
        # 简单的关键词匹配实现
        # 在实际应用中，可以使用更复杂的语义匹配
        query_words = set(query.lower().split())

        scored_memories = []
        for memory in self.memories:
            memory_words = set(memory.content.lower().split())
            common_words = query_words.intersection(memory_words)
            score = len(common_words) / max(len(query_words), 1)

            # 考虑重要性权重
            weighted_score = score * (0.5 + memory.importance * 0.5)

            if weighted_score > 0:
                scored_memories.append((weighted_score, memory))

        # 按分数排序
        scored_memories.sort(key=lambda x: x[0], reverse=True)

        # 返回前count个
        return [memory for _, memory in scored_memories[:count]]

    def summarize_conversation(self) -> str:
        """
        生成对话摘要

        Returns:
            对话摘要
        """
        if not self.conversation_history:
            return "暂无对话历史"

        # 简单的摘要生成
        # 在实际应用中，可以使用LLM生成更好的摘要
        user_messages = [msg["content"] for msg in self.conversation_history if msg["role"] == "user"]
        assistant_messages = [msg["content"] for msg in self.conversation_history if msg["role"] == "assistant"]

        summary_parts = []

        if user_messages:
            summary_parts.append(f"用户提出了 {len(user_messages)} 个问题/请求")
            if len(user_messages) <= 3:
                summary_parts.append(f"最近的问题: {user_messages[-1]}")

        if assistant_messages:
            summary_parts.append(f"助手回复了 {len(assistant_messages)} 次")

        return "。".join(summary_parts)

    def clear_memories(self) -> None:
        """清空所有记忆"""
        self.memories.clear()

    def clear_conversation(self) -> None:
        """清空对话历史"""
        self.conversation_history.clear()

    def clear_working_memory(self) -> None:
        """清空工作记忆"""
        self.working_memory.clear()

    def reset(self) -> None:
        """重置所有短期记忆"""
        self.clear_memories()
        self.clear_conversation()
        self.clear_working_memory()

    def _prune_memories(self) -> None:
        """修剪记忆，保持最大条目数"""
        if len(self.memories) > self.max_entries:
            # 按重要性排序，保留最重要的记忆
            self.memories.sort(key=lambda m: m.importance, reverse=True)
            self.memories = self.memories[:self.max_entries]
            # 恢复时间顺序
            self.memories.sort(key=lambda m: m.timestamp)

    def _prune_conversation(self) -> None:
        """修剪对话历史，保持最大消息数"""
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "memory_count": len(self.memories),
            "conversation_count": len(self.conversation_history),
            "working_memory_keys": list(self.working_memory.keys()),
            "max_entries": self.max_entries,
            "max_history": self.max_history,
        }

    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"ShortTermMemory(memories={len(self.memories)}, "
            f"conversation={len(self.conversation_history)}, "
            f"working={len(self.working_memory)})"
        )


if __name__ == "__main__":
    # 测试短期记忆
    memory = ShortTermMemory(max_entries=5, max_history=3)

    # 添加记忆
    memory.add_memory("用户喜欢编程", importance=0.8, category="user_preference")
    memory.add_memory("用户需要帮助写代码", importance=0.6, category="task")
    memory.add_memory("今天是晴天", importance=0.3, category="context")

    # 添加对话
    memory.add_conversation("user", "你好，我需要帮助")
    memory.add_conversation("assistant", "你好！有什么可以帮助你的？")
    memory.add_conversation("user", "我想学习Python")

    # 设置工作记忆
    memory.set_working_memory("current_task", "学习Python")
    memory.set_working_memory("difficulty", "beginner")

    # 测试获取功能
    print("测试短期记忆模块:")
    print(f"记忆状态: {memory}")
    print(f"最近记忆: {[m.content for m in memory.get_recent_memories(2)]}")
    print(f"用户偏好记忆: {[m.content for m in memory.get_memories_by_category('user_preference')]}")
    print(f"相关记忆('编程'): {[m.content for m in memory.get_relevant_memories('编程', 2)]}")
    print(f"对话摘要: {memory.summarize_conversation()}")
    print(f"工作记忆: {memory.working_memory}")
    print(f"状态字典: {memory.to_dict()}")