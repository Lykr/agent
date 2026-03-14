"""
记忆工具

提供Agent与记忆系统交互的工具。
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..tools.base import BaseTool
from ..modules.memory import ShortTermMemoryEntry, LongTermMemoryEntry


class RememberTool(BaseTool):
    """记住重要信息工具"""

    @property
    def name(self) -> str:
        return "remember"

    @property
    def description(self) -> str:
        return """记住重要信息到长期记忆。

        输入格式: JSON字符串
        {
            "content": "要记住的内容",
            "importance": 0.8,  # 可选，重要性评分 0-1，默认0.7
            "category": "user_preference",  # 可选，记忆类别
            "metadata": {"key": "value"}  # 可选，元数据
        }

        示例: {"content": "用户喜欢Python编程", "importance": 0.8, "category": "user_preference"}
        """

    def _execute_impl(self, input_text: str) -> str:
        try:
            # 解析输入
            data = json.loads(input_text)
            content = data.get("content", "").strip()

            if not content:
                return "错误: 内容不能为空"

            # 获取参数
            importance = float(data.get("importance", 0.7))
            category = data.get("category", "general")
            metadata = data.get("metadata", {})

            # 检查重要性范围
            if not 0 <= importance <= 1:
                return f"错误: 重要性评分必须在0-1之间，当前值: {importance}"

            # 需要从Agent获取long_term_memory实例
            # 这里假设工具被添加到Agent后，Agent会设置context
            agent = self.context.get("agent")
            if not agent:
                return "错误: 无法访问Agent记忆系统"

            if not agent.long_term_memory.is_available():
                return "错误: 长期记忆不可用"

            # 存储到长期记忆
            memory_id = agent.long_term_memory.store_memory(
                content=content,
                importance=importance,
                category=category,
                metadata=metadata
            )

            if memory_id.startswith("存储失败"):
                return f"存储失败: {memory_id}"

            # 同时存储到短期记忆
            agent.short_term_memory.add_memory(
                content=f"记住了: {content[:50]}...",
                importance=0.6,
                category="memory_operation"
            )

            return f"已记住信息 (ID: {memory_id}): {content[:100]}..."

        except json.JSONDecodeError:
            return "错误: 输入必须是有效的JSON格式"
        except Exception as e:
            return f"记住信息时出错: {str(e)}"


class RecallTool(BaseTool):
    """回忆信息工具"""

    @property
    def name(self) -> str:
        return "recall"

    @property
    def description(self) -> str:
        return """从记忆中回忆相关信息。

        输入格式: JSON字符串
        {
            "query": "要回忆的内容关键词",
            "source": "short_term|long_term|both",  # 可选，记忆来源，默认both
            "count": 5,  # 可选，返回数量，默认3
            "category": "general"  # 可选，按类别过滤
        }

        示例: {"query": "编程", "source": "both", "count": 3}
        """

    def _execute_impl(self, input_text: str) -> str:
        try:
            # 解析输入
            data = json.loads(input_text)
            query = data.get("query", "").strip()

            if not query:
                return "错误: 查询内容不能为空"

            # 获取参数
            source = data.get("source", "both")
            count = int(data.get("count", 3))
            category = data.get("category")

            # 需要从Agent获取记忆实例
            agent = self.context.get("agent")
            if not agent:
                return "错误: 无法访问Agent记忆系统"

            results = []

            # 从短期记忆回忆
            if source in ["short_term", "both"]:
                short_term_results = agent.short_term_memory.get_relevant_memories(
                    query, count=count
                )
                for i, memory in enumerate(short_term_results, 1):
                    results.append(f"短期记忆 {i}: {memory.content} (重要性: {memory.importance:.2f})")

            # 从长期记忆回忆
            if source in ["long_term", "both"] and agent.long_term_memory.is_available():
                long_term_results = agent.long_term_memory.retrieve_memories(
                    query, n_results=count, category_filter=category
                )
                for i, memory in enumerate(long_term_results, 1):
                    results.append(f"长期记忆 {i}: {memory.content} (重要性: {memory.importance:.2f})")

            if not results:
                return f"没有找到与 '{query}' 相关的记忆"

            return "回忆结果:\n" + "\n".join(results)

        except json.JSONDecodeError:
            return "错误: 输入必须是有效的JSON格式"
        except Exception as e:
            return f"回忆信息时出错: {str(e)}"


class ListMemoriesTool(BaseTool):
    """列出记忆工具"""

    @property
    def name(self) -> str:
        return "list_memories"

    @property
    def description(self) -> str:
        return """列出记忆系统中的记忆。

        输入格式: JSON字符串
        {
            "source": "short_term|long_term",  # 记忆来源
            "limit": 10,  # 可选，限制数量
            "sort_by": "recent|importance"  # 可选，排序方式
        }

        示例: {"source": "short_term", "limit": 5, "sort_by": "recent"}
        """

    def _execute_impl(self, input_text: str) -> str:
        try:
            # 解析输入
            data = json.loads(input_text)
            source = data.get("source", "short_term")
            limit = int(data.get("limit", 10))
            sort_by = data.get("sort_by", "recent")

            # 需要从Agent获取记忆实例
            agent = self.context.get("agent")
            if not agent:
                return "错误: 无法访问Agent记忆系统"

            memories_info = []

            if source == "short_term":
                memories = agent.short_term_memory.memories

                # 排序
                if sort_by == "importance":
                    memories = sorted(memories, key=lambda m: m.importance, reverse=True)
                else:  # recent
                    memories = sorted(memories, key=lambda m: m.timestamp, reverse=True)

                # 限制数量
                memories = memories[:limit]

                for i, memory in enumerate(memories, 1):
                    time_str = memory.timestamp.strftime("%H:%M:%S")
                    memories_info.append(
                        f"{i}. [{time_str}] {memory.content[:60]}... "
                        f"(重要性: {memory.importance:.2f}, 类别: {memory.category})"
                    )

                total = len(agent.short_term_memory.memories)
                header = f"短期记忆 (显示 {len(memories)}/{total}):"

            elif source == "long_term":
                if not agent.long_term_memory.is_available():
                    return "错误: 长期记忆不可用"

                memories = agent.long_term_memory.get_all_memories(limit=limit)

                for i, memory in enumerate(memories, 1):
                    time_str = memory.timestamp.strftime("%Y-%m-%d %H:%M")
                    memories_info.append(
                        f"{i}. [{time_str}] {memory.content[:60]}... "
                        f"(重要性: {memory.importance:.2f}, 类别: {memory.category}, "
                        f"访问: {memory.access_count})"
                    )

                stats = agent.long_term_memory.get_statistics()
                total = stats.get("total_memories", 0)
                header = f"长期记忆 (显示 {len(memories)}/{total}):"

            else:
                return f"错误: 不支持的记忆来源: {source}"

            if not memories_info:
                return f"{header}\n暂无记忆"

            return header + "\n" + "\n".join(memories_info)

        except json.JSONDecodeError:
            return "错误: 输入必须是有效的JSON格式"
        except Exception as e:
            return f"列出记忆时出错: {str(e)}"


class ForgetTool(BaseTool):
    """忘记记忆工具"""

    @property
    def name(self) -> str:
        return "forget"

    @property
    def description(self) -> str:
        return """忘记指定的记忆。

        输入格式: JSON字符串
        {
            "memory_id": "记忆ID",  # 长期记忆需要
            "source": "short_term|long_term",  # 记忆来源
            "content": "要忘记的内容关键词"  # 短期记忆需要
        }

        示例1 (长期记忆): {"memory_id": "123", "source": "long_term"}
        示例2 (短期记忆): {"content": "测试", "source": "short_term"}
        """

    def _execute_impl(self, input_text: str) -> str:
        try:
            # 解析输入
            data = json.loads(input_text)
            source = data.get("source", "short_term")

            # 需要从Agent获取记忆实例
            agent = self.context.get("agent")
            if not agent:
                return "错误: 无法访问Agent记忆系统"

            if source == "short_term":
                content_filter = data.get("content", "").strip()
                if not content_filter:
                    return "错误: 短期记忆需要指定要忘记的内容关键词"

                # 查找匹配的记忆
                memories_to_remove = []
                for memory in agent.short_term_memory.memories:
                    if content_filter.lower() in memory.content.lower():
                        memories_to_remove.append(memory)

                if not memories_to_remove:
                    return f"没有找到包含 '{content_filter}' 的短期记忆"

                # 移除记忆
                for memory in memories_to_remove:
                    agent.short_term_memory.memories.remove(memory)

                return f"已忘记 {len(memories_to_remove)} 条包含 '{content_filter}' 的短期记忆"

            elif source == "long_term":
                memory_id = data.get("memory_id", "").strip()
                if not memory_id:
                    return "错误: 长期记忆需要指定记忆ID"

                if not agent.long_term_memory.is_available():
                    return "错误: 长期记忆不可用"

                # 删除记忆
                success = agent.long_term_memory.delete_memory(memory_id)
                if success:
                    return f"已忘记长期记忆 (ID: {memory_id})"
                else:
                    return f"忘记长期记忆失败 (ID: {memory_id})"

            else:
                return f"错误: 不支持的记忆来源: {source}"

        except json.JSONDecodeError:
            return "错误: 输入必须是有效的JSON格式"
        except Exception as e:
            return f"忘记记忆时出错: {str(e)}"


class MemoryStatsTool(BaseTool):
    """记忆统计工具"""

    @property
    def name(self) -> str:
        return "memory_stats"

    @property
    def description(self) -> str:
        return """获取记忆系统的统计信息。

        输入: 任意文本（会被忽略）
        输出: 记忆系统的统计信息
        """

    def _execute_impl(self, input_text: str) -> str:
        try:
            # 需要从Agent获取记忆实例
            agent = self.context.get("agent")
            if not agent:
                return "错误: 无法访问Agent记忆系统"

            stats = []

            # 短期记忆统计
            short_term_stats = agent.short_term_memory.to_dict()
            stats.append("=== 短期记忆 ===")
            stats.append(f"记忆条目: {short_term_stats['memory_count']}")
            stats.append(f"对话记录: {short_term_stats['conversation_count']}")
            stats.append(f"工作记忆键: {', '.join(short_term_stats['working_memory_keys']) or '无'}")
            stats.append(f"最大条目: {short_term_stats['max_entries']}")
            stats.append(f"最大历史: {short_term_stats['max_history']}")

            # 长期记忆统计
            long_term_stats = agent.long_term_memory.get_statistics()
            stats.append("\n=== 长期记忆 ===")
            if long_term_stats.get("available", False):
                stats.append(f"状态: 可用")
                stats.append(f"记忆总数: {long_term_stats.get('total_memories', 0)}")
                stats.append(f"存储路径: {long_term_stats.get('persist_path', '未知')}")
                stats.append(f"集合名称: {long_term_stats.get('collection_name', '未知')}")
            else:
                stats.append(f"状态: 不可用")
                if "error" in long_term_stats:
                    stats.append(f"错误: {long_term_stats['error']}")

            return "\n".join(stats)

        except Exception as e:
            return f"获取记忆统计时出错: {str(e)}"


# 工具列表
MEMORY_TOOLS = [
    RememberTool(),
    RecallTool(),
    ListMemoriesTool(),
    ForgetTool(),
    MemoryStatsTool(),
]


if __name__ == "__main__":
    # 测试记忆工具
    print("测试记忆工具...")

    # 创建模拟的Agent上下文
    class MockAgent:
        def __init__(self):
            from ..modules.memory import ShortTermMemory, LongTermMemory
            self.short_term_memory = ShortTermMemory(max_entries=5, max_history=3)
            self.long_term_memory = LongTermMemory(persist_path="./test_memory_tools")

            # 添加一些测试记忆
            self.short_term_memory.add_memory("测试记忆1", importance=0.8)
            self.short_term_memory.add_memory("测试记忆2", importance=0.6)

    mock_agent = MockAgent()

    # 测试RememberTool
    print("\n1. 测试RememberTool:")
    remember_tool = RememberTool()
    remember_tool.context = {"agent": mock_agent}

    test_input = json.dumps({
        "content": "这是一个测试记忆",
        "importance": 0.9,
        "category": "test",
        "metadata": {"test": "true"}
    })
    result = remember_tool.execute(test_input)
    print(f"   结果: {result}")

    # 测试RecallTool
    print("\n2. 测试RecallTool:")
    recall_tool = RecallTool()
    recall_tool.context = {"agent": mock_agent}

    test_input = json.dumps({
        "query": "测试",
        "source": "short_term",
        "count": 2
    })
    result = recall_tool.execute(test_input)
    print(f"   结果: {result}")

    # 测试ListMemoriesTool
    print("\n3. 测试ListMemoriesTool:")
    list_tool = ListMemoriesTool()
    list_tool.context = {"agent": mock_agent}

    test_input = json.dumps({
        "source": "short_term",
        "limit": 3,
        "sort_by": "recent"
    })
    result = list_tool.execute(test_input)
    print(f"   结果: {result}")

    # 测试MemoryStatsTool
    print("\n4. 测试MemoryStatsTool:")
    stats_tool = MemoryStatsTool()
    stats_tool.context = {"agent": mock_agent}

    result = stats_tool.execute("")
    print(f"   结果: {result}")

    print("\n测试完成!")