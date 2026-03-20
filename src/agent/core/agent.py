"""
Agent 核心类

实现感知-思考-执行循环，协调各个模块工作。
支持任务规划、反思和多Agent协作等高级功能。
"""

import json
import time
from typing import Any, Callable, Dict, List, Optional, Union

from .config import AgentConfig, get_config
from .state import StateManager
from ..llm import BaseLLM
from ..modules.coordination import AgentRole, CoordinationStrategy, MultiAgentCoordinator
from ..modules.memory import LongTermMemory, ShortTermMemory
from ..modules.reasoning import ReflectionEngine, TaskPlanner
from ..modules.reasoning.reflection import TaskExecutionRecord
from ..tools import BaseTool


class Agent:
    """AI Agent 主类"""

    def __init__(
        self,
        llm: BaseLLM,
        config: Optional[Union[AgentConfig, str]] = None,
        tools: Optional[List[BaseTool]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        enable_planning: Optional[bool] = None,
        enable_reflection: Optional[bool] = None,
        enable_multi_agent: bool = False,
    ):
        """
        初始化Agent

        Args:
            llm: LLM实例
            config: 配置对象或配置文件路径
            tools: 工具列表
            on_log: 日志回调
            enable_planning: 是否启用任务规划（覆盖配置）
            enable_reflection: 是否启用反思（覆盖配置）
            enable_multi_agent: 是否启用多Agent协作
        """
        # 配置管理
        if isinstance(config, str):
            self.config = get_config(config)
        elif config is None:
            self.config = get_config()
        else:
            self.config = config

        # 日志回调
        self.on_log = on_log

        # 核心组件
        self.llm = llm
        self.state_manager = StateManager()
        self.tools: Dict[str, BaseTool] = {}

        # 初始化记忆系统
        self.short_term_memory = ShortTermMemory(
            max_entries=self.config.memory.short_term.max_entries,
            max_history=self.config.memory.short_term.max_history
        )

        self.long_term_memory = LongTermMemory(
            persist_path=self.config.memory.long_term.persist_path,
            collection_name=self.config.memory.long_term.collection_name,
            embedding_model=self.config.memory.long_term.embedding_model
        )

        # 初始化工具
        if tools:
            for tool in tools:
                self.add_tool(tool)

        # 功能开关（参数优先，否则读配置）
        self.enable_planning = enable_planning if enable_planning is not None else self.config.enable_planning
        self.enable_reflection = enable_reflection if enable_reflection is not None else self.config.enable_reflection
        self.enable_multi_agent = enable_multi_agent

        # 高级模块（按需初始化）
        self.task_planner: Optional[TaskPlanner] = None
        self.reflection_engine: Optional[ReflectionEngine] = None
        self.multi_agent_coordinator: Optional[MultiAgentCoordinator] = None

        if self.enable_planning:
            self.task_planner = TaskPlanner(llm=llm)

        if self.enable_reflection:
            self.reflection_engine = ReflectionEngine(llm=llm, memory_system=self.long_term_memory)

        if self.enable_multi_agent:
            self.multi_agent_coordinator = MultiAgentCoordinator(strategy=CoordinationStrategy.HIERARCHICAL)

        # 任务执行历史
        self.task_history: List[Dict[str, Any]] = []
        self.current_task_record: Optional[Dict[str, Any]] = None

        # 系统提示词
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        tools_description = self._get_tools_description()

        return f"""你是一个AI助手，可以调用工具来帮助用户解决问题。

你可以使用的工具：
{tools_description}

请按照以下步骤工作：
1. 理解用户的需求
2. 如果需要使用工具，请明确说明要使用哪个工具以及输入参数
3. 如果不需要工具，直接回答用户的问题

工具调用格式：
```json
{{
    "tool": "工具名称",
    "input": "输入参数"
}}
```

请保持回答简洁明了。"""

    def _get_tools_description(self) -> str:
        """获取工具描述"""
        if not self.tools:
            return "暂无可用工具。"

        descriptions = []
        for tool_name, tool in self.tools.items():
            descriptions.append(f"- {tool_name}: {tool.description}")

        return "\n".join(descriptions)

    def _get_memory_context(self, user_input: str) -> str:
        """获取记忆上下文"""
        memory_context_parts = []

        # 从短期记忆中获取相关记忆
        if self.config.memory.short_term.enabled:
            short_term_memories = self.short_term_memory.get_relevant_memories(
                user_input, count=3
            )
            if short_term_memories:
                memory_context_parts.append("短期记忆:")
                for i, memory in enumerate(short_term_memories, 1):
                    memory_context_parts.append(f"{i}. {memory.content}")

        # 从长期记忆中获取相关记忆
        if self.config.memory.long_term.enabled and self.long_term_memory.is_available():
            long_term_memories = self.long_term_memory.retrieve_memories(
                user_input, n_results=2
            )
            if long_term_memories:
                memory_context_parts.append("长期记忆:")
                for i, memory in enumerate(long_term_memories, 1):
                    memory_context_parts.append(f"{i}. {memory.content}")

        # 获取工作记忆
        working_memory = self.short_term_memory.working_memory
        if working_memory:
            memory_context_parts.append("工作记忆:")
            for key, value in working_memory.items():
                memory_context_parts.append(f"- {key}: {value}")

        if memory_context_parts:
            return "基于以下记忆信息:\n" + "\n".join(memory_context_parts)
        else:
            return ""

    def _store_important_memories(self, user_input: str, response: str) -> None:
        """存储重要记忆"""
        # 存储到短期记忆
        if self.config.memory.short_term.enabled:
            # 存储用户输入（中等重要性）
            if user_input and len(user_input) > 10:  # 只存储较长的输入
                self.short_term_memory.add_memory(
                    content=f"用户说: {user_input}",
                    importance=0.6,
                    category="user_input"
                )

            # 存储Agent回复（中等重要性）
            if response and len(response) > 20:  # 只存储较长的回复
                self.short_term_memory.add_memory(
                    content=f"我回复: {response[:100]}...",  # 只存储前100字符
                    importance=0.5,
                    category="agent_response"
                )

        # 存储到长期记忆（如果启用）
        if self.config.memory.long_term.enabled and self.long_term_memory.is_available():
            # 判断是否应该存储到长期记忆（基于重要性）
            should_store = False
            importance = 0.5

            # 简单的启发式规则：如果对话涉及学习目标、用户偏好或重要任务
            important_keywords = ["学习", "目标", "偏好", "喜欢", "不喜欢", "重要", "记住", "备忘"]
            if any(keyword in user_input for keyword in important_keywords):
                should_store = True
                importance = 0.8

            # 如果涉及工具调用，可能也是重要的
            if "工具" in response or "调用" in response:
                should_store = True
                importance = 0.7

            if should_store:
                memory_id = self.long_term_memory.store_memory(
                    content=f"对话: 用户: {user_input[:50]}... | 助手: {response[:50]}...",
                    importance=importance,
                    category="conversation",
                    metadata={
                        "type": "dialogue",
                        "user_input": user_input[:100],
                        "agent_response": response[:100]
                    }
                )
                if memory_id and not memory_id.startswith("存储失败"):
                    self._log("记忆", f"已存储长期记忆: {memory_id}")

    def _update_conversation_history(self, role: str, content: str) -> None:
        """更新对话历史到短期记忆"""
        self.short_term_memory.add_conversation(role, content)

    def add_tool(self, tool: BaseTool) -> None:
        """添加工具"""
        self.tools[tool.name] = tool

        # 设置工具上下文（如果工具需要访问Agent）
        if hasattr(tool, 'context'):
            tool.context = {"agent": self}

        # 更新系统提示词以包含新工具
        self.system_prompt = self._build_system_prompt()

    def remove_tool(self, tool_name: str) -> None:
        """移除工具"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            self.system_prompt = self._build_system_prompt()

    def _perceive(self, user_input: str) -> List[Dict[str, str]]:
        """感知阶段：构建消息上下文"""
        messages = []

        # 添加系统提示
        messages.append({"role": "system", "content": self.system_prompt})

        # 添加记忆上下文（如果启用）
        memory_context = self._get_memory_context(user_input)
        if memory_context:
            messages.append({"role": "system", "content": memory_context})

        # 添加历史对话（只包含user/assistant/system角色，过滤内部日志）
        history = self.state_manager.state.get_conversation_history(
            max_messages=self.config.memory.short_term.max_history
        )
        messages.extend(
            msg for msg in history
            if msg["role"] in ("user", "assistant", "system")
        )

        # 添加当前用户输入
        if user_input:
            messages.append({"role": "user", "content": user_input})

        return messages

    def _log(self, phase: str, content: str) -> None:
        """记录运行日志，如果设置了回调则实时通知"""
        self.state_manager.state.add_log(phase, content)
        if self.on_log:
            self.on_log(phase, content)

    def _think(self, messages: List[Dict[str, str]]) -> str:
        """思考阶段：调用LLM生成回复"""
        self._log("思考", "正在调用LLM...")
        try:
            response = self.llm.generate(
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            self._log("思考", "LLM回复完成")
            return response
        except Exception as e:
            error = f"思考过程中出现错误: {str(e)}"
            self._log("思考", error)
            return error

    def _extract_tool_call(self, response: str) -> Optional[Dict[str, str]]:
        """从回复中提取工具调用"""
        import re

        # 查找JSON代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, response, re.DOTALL)

        if match:
            # 有代码块，使用捕获组内容
            json_str = match.group(1)
        else:
            # 尝试查找没有代码块的JSON
            # 使用非贪婪匹配，只匹配第一个完整的JSON对象
            json_pattern = r'\{[^{}]*\}'
            match = re.search(json_pattern, response)
            if match:
                # 没有代码块，使用整个匹配
                json_str = match.group(0)
            else:
                return None

        try:
            tool_call = json.loads(json_str)
            if "tool" in tool_call and "input" in tool_call:
                return tool_call
        except json.JSONDecodeError:
            pass

        return None

    def _execute_tool(self, tool_name: str, input_text: str) -> str:
        """执行工具"""
        if tool_name not in self.tools:
            return f"错误: 工具 '{tool_name}' 不存在。"

        tool = self.tools[tool_name]

        try:
            # 记录工具调用开始（使用内部角色，不会发送给API）
            self.state_manager.state.add_message("system_log", f"调用工具: {tool_name}")
            self.state_manager.state.add_message("system_log", f"工具输入: {input_text}")

            # 执行工具
            self._log("工具", f"执行 {tool_name}，输入: {input_text}")
            start_time = time.time()
            result = tool.execute(input_text)
            execution_time = time.time() - start_time
            self._log("工具", f"{tool_name} 完成 (耗时: {execution_time:.2f}s)，结果: {result[:200]}")

            # 记录工具调用结果
            self.state_manager.state.add_tool_call(
                tool_name=tool_name,
                input_text=input_text,
                output_text=result,
                success=True
            )

            self.state_manager.state.add_message("system_log", f"工具结果: {result} (耗时: {execution_time:.2f}s)")

            return result

        except Exception as e:
            error_msg = f"工具执行失败: {str(e)}"
            self.state_manager.state.add_tool_call(
                tool_name=tool_name,
                input_text=input_text,
                output_text=error_msg,
                success=False
            )
            self.state_manager.state.add_message("system_log", f"工具错误: {error_msg}")
            self.state_manager.record_error(error_msg)
            return error_msg

    def _act_with_tool(self, llm_response: str, tool_call: Dict[str, str]) -> str:
        """执行阶段：执行工具调用并将结果反馈给LLM"""
        # 执行工具（_execute_tool 内部会打印工具执行详情）
        tool_result = self._execute_tool(tool_call["tool"], tool_call["input"])

        # 将工具结果反馈给LLM进行下一步思考
        follow_up_messages = [
            {"role": "assistant", "content": llm_response},
            {"role": "user", "content": f"工具执行结果: {tool_result}"}
        ]

        self._log("执行", "将工具结果反馈给LLM...")
        final_response = self._think(follow_up_messages)
        return final_response

    def _run_loop(self, user_input: str, max_steps: Optional[int] = None) -> str:
        """核心感知-思考-执行循环"""
        if max_steps is None:
            max_steps = self.config.max_steps

        # 记录用户输入
        self.state_manager.state.add_message("user", user_input)
        self._update_conversation_history("user", user_input)

        self.state_manager.start()
        self.state_manager.clear_error()

        try:
            current_step = 0
            final_response = ""

            while current_step < max_steps:
                self._log("步骤", f"第 {current_step + 1}/{max_steps} 步")

                # 感知
                messages = self._perceive(user_input if current_step == 0 else "")
                self._log("感知", f"构建消息上下文，共 {len(messages)} 条消息")

                # 思考
                llm_response = self._think(messages)

                # 检查是否需要执行工具
                tool_call = self._extract_tool_call(llm_response)
                if not tool_call:
                    self._log("执行", "无工具调用，跳过执行阶段")
                    self.state_manager.state.add_message("assistant", llm_response)
                    self._update_conversation_history("assistant", llm_response)
                    self.state_manager.state.increment_step()
                    final_response = llm_response
                    break

                # 执行工具
                response = self._act_with_tool(llm_response, tool_call)

                # 记录助手回复
                self.state_manager.state.add_message("assistant", response)
                self._update_conversation_history("assistant", response)

                # 更新状态
                self.state_manager.state.increment_step()
                current_step += 1
                final_response = response

                # 检查执行后的回复是否还需要继续调用工具
                if not self._extract_tool_call(response):
                    break

                # 准备下一轮的用户输入（工具执行结果已包含在消息中）
                user_input = ""

            # 运行结束后存储重要记忆
            self._store_important_memories(user_input, final_response)

            return final_response

        except Exception as e:
            error_msg = f"Agent运行错误: {str(e)}"
            self.state_manager.record_error(error_msg)
            return error_msg

        finally:
            self.state_manager.stop()

    def run(self, user_input: str, max_steps: Optional[int] = None) -> str:
        """
        运行Agent

        Args:
            user_input: 用户输入
            max_steps: 最大执行步骤数，如果为None则使用配置中的值

        Returns:
            Agent的回复
        """
        if self.enable_planning and self.task_planner is not None:
            return self._run_with_planning(user_input, max_steps)

        if self.enable_reflection and self.reflection_engine is not None:
            return self._run_with_reflection(user_input, max_steps)

        return self._run_loop(user_input, max_steps)

    def _run_with_planning(self, user_input: str, max_steps: Optional[int] = None) -> str:
        """将输入分解为子任务后逐步执行"""
        self._log("规划", f"开始规划任务: {user_input[:80]}")
        available_tools = list(self.tools.keys())
        task_plan = self.task_planner.create_plan_from_llm(user_input, available_tools)
        self._log("规划", f"生成计划 {task_plan.task_id}，共 {len(task_plan.subtasks)} 个子任务")

        subtask_results: List[str] = []
        start_time = time.time()

        for subtask in task_plan.subtasks:
            # 检查依赖是否满足
            if subtask not in task_plan.get_ready_subtasks():
                self._log("规划", f"子任务 {subtask.id} 依赖未满足，跳过")
                task_plan.mark_subtask_failed(subtask.id, "依赖未满足")
                subtask_results.append(f"[{subtask.id}] 依赖未满足，已跳过")
                continue

            self._log("规划", f"执行子任务 {subtask.id}: {subtask.description}")
            task_plan.mark_subtask_started(subtask.id)

            result = self._run_loop(subtask.description, max_steps)

            task_plan.mark_subtask_completed(subtask.id, result)
            subtask_results.append(f"[{subtask.id}] {subtask.description}\n{result}")
            self._log("规划", f"子任务 {subtask.id} 完成")

        record = {
            "task_id": task_plan.task_id,
            "task_description": user_input,
            "subtask_count": len(task_plan.subtasks),
            "duration": time.time() - start_time,
            "status": task_plan.status.value,
        }
        self.task_history.append(record)
        self.current_task_record = record

        if self.enable_reflection and self.reflection_engine is not None:
            self._reflect_on_execution(record, subtask_results)

        summary = f"任务规划执行完成（{len(subtask_results)} 个子任务）：\n\n"
        summary += "\n\n---\n\n".join(subtask_results)
        return summary

    def _run_with_reflection(self, user_input: str, max_steps: Optional[int] = None) -> str:
        """执行并在完成后触发反思"""
        start_time = time.time()
        result = self._run_loop(user_input, max_steps)

        record = {
            "task_id": f"task_{int(start_time)}",
            "task_description": user_input,
            "subtask_count": 1,
            "duration": time.time() - start_time,
            "status": "completed",
        }
        self.task_history.append(record)
        self.current_task_record = record

        self._reflect_on_execution(record, [result])
        return result

    def _reflect_on_execution(self, record: Dict[str, Any], results: List[str]) -> None:
        """对本次执行进行反思"""
        exec_record = TaskExecutionRecord(
            task_id=record["task_id"],
            task_description=record["task_description"],
            start_time=time.time() - record["duration"],
            end_time=time.time(),
            steps_taken=record["subtask_count"],
            successful_steps=record["subtask_count"],
            tools_used=list(self.tools.keys()),
            final_result=results[-1] if results else ""
        )

        insights = self.reflection_engine.analyze_task_execution(exec_record)
        self._log("反思", f"生成 {len(insights)} 条反思见解")
        for insight in insights:
            self._log("反思", f"[{insight.reflection_type.value}] {insight.insight}")

    def run_with_coordination(self, user_input: str, other_agents: List[Dict[str, Any]] = None) -> str:
        """
        使用多Agent协作运行

        Args:
            user_input: 用户输入
            other_agents: 其他Agent信息列表

        Returns:
            协调执行结果
        """
        if not self.enable_multi_agent or self.multi_agent_coordinator is None:
            self._log("协作", "多Agent协作未启用，使用单Agent模式")
            return self.run(user_input)

        self._log("协作", f"开始多Agent协作任务: {user_input}")

        # 注册其他Agent（如果提供）
        if other_agents:
            for agent_info in other_agents:
                agent_id = agent_info.get("id", f"agent_{len(self.multi_agent_coordinator.agents)}")
                role = AgentRole(agent_info.get("role", "executor"))
                capabilities = agent_info.get("capabilities", [])
                self.multi_agent_coordinator.register_agent(agent_id, role, capabilities)

        # 注册自己
        self.multi_agent_coordinator.register_agent(
            agent_id="main_agent",
            role=AgentRole.COORDINATOR,
            capabilities=list(self.tools.keys())
        )

        # 创建任务分解
        if self.enable_planning and self.task_planner is not None:
            available_tools = list(self.tools.keys())
            task_plan = self.task_planner.create_plan_from_llm(user_input, available_tools)

            subtasks = [
                {
                    "task_id": task_plan.task_id,
                    "subtask_id": subtask.id,
                    "description": subtask.description,
                    "required_capabilities": subtask.required_tools,
                }
                for subtask in task_plan.subtasks
            ]

            result = self.multi_agent_coordinator.coordinate_complex_task(user_input, subtasks)

            final_response = "多Agent协作任务完成！\n\n"
            final_response += f"成功率: {result['success_rate']:.1%}\n"
            final_response += f"总子任务数: {result['total_subtasks']}\n"
            final_response += f"成功数: {result['successful_subtasks']}\n\n"

            for subtask_id, subtask_result in result['results'].items():
                status = "✅" if subtask_result['success'] else "❌"
                final_response += f"{status} {subtask_id}: {subtask_result.get('result', '无结果')[:100]}...\n"

            return final_response
        else:
            subtasks = [{
                "task_id": f"task_{int(time.time())}",
                "subtask_id": "subtask_1",
                "description": user_input,
                "required_capabilities": [],
            }]
            result = self.multi_agent_coordinator.coordinate_complex_task(user_input, subtasks)
            return f"协作任务完成: {result}"

    def drain_logs(self) -> list:
        """取出并清空运行日志"""
        return self.state_manager.state.drain_logs()

    def get_state(self) -> Dict[str, Any]:
        """获取当前状态信息"""
        state = {
            "config": self.config.model_dump(),
            "state": self.state_manager.state.to_dict(),
            "tools": list(self.tools.keys()),
            "system_prompt_length": len(self.system_prompt),
            "short_term_memory": self.short_term_memory.to_dict(),
            "long_term_memory": self.long_term_memory.get_statistics(),
            "enable_planning": self.enable_planning,
            "enable_reflection": self.enable_reflection,
            "enable_multi_agent": self.enable_multi_agent,
        }

        if self.multi_agent_coordinator:
            state["multi_agent_status"] = self.multi_agent_coordinator.get_system_status()

        return state

    def reset(self, clear_history: bool = False) -> None:
        """重置Agent状态"""
        self.state_manager.reset(clear_history=clear_history)
        if clear_history:
            self.short_term_memory.reset()
            self.task_history.clear()
            if self.reflection_engine:
                self.reflection_engine.reflection_history.clear()
            if self.multi_agent_coordinator:
                self.multi_agent_coordinator.reset()

        self.current_task_record = None

    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"Agent(name={self.config.name}, "
            f"tools={len(self.tools)}, "
            f"steps={self.state_manager.state.current_step}, "
            f"short_term_memories={len(self.short_term_memory.memories)})"
        )


class SimpleAgent(Agent):
    """简化版Agent，用于快速测试"""

    def __init__(self, llm: BaseLLM):
        """使用默认配置初始化简化版Agent"""
        super().__init__(llm=llm)

    def chat(self, message: str) -> str:
        """简化聊天接口"""
        return self.run(message)
