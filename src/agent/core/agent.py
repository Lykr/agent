"""
Agent 核心类

实现感知-思考-执行循环，协调各个模块工作。
"""

import json
import time
from typing import Any, Callable, Dict, List, Optional, Union

from .config import get_config, AgentConfig
from .state import StateManager
from ..llm import BaseLLM
from ..tools import BaseTool


class Agent:
    """AI Agent 主类"""

    def __init__(
        self,
        llm: BaseLLM,
        config: Optional[Union[AgentConfig, str]] = None,
        tools: Optional[List[BaseTool]] = None,
        on_log: Optional[Callable[[str, str], None]] = None
    ):
        """
        初始化Agent

        Args:
            llm: LLM实例
            config: 配置对象或配置文件路径
            tools: 工具列表
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

        # 初始化工具
        if tools:
            for tool in tools:
                self.add_tool(tool)

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

    def add_tool(self, tool: BaseTool) -> None:
        """添加工具"""
        self.tools[tool.name] = tool
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
        # 简单的JSON提取逻辑
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

    def run(self, user_input: str, max_steps: Optional[int] = None) -> str:
        """
        运行Agent

        Args:
            user_input: 用户输入
            max_steps: 最大执行步骤数，如果为None则使用配置中的值

        Returns:
            Agent的回复
        """
        if max_steps is None:
            max_steps = self.config.max_steps

        # 记录用户输入
        self.state_manager.state.add_message("user", user_input)

        # 开始运行
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
                    # 没有工具调用，直接返回思考结果
                    self._log("执行", "无工具调用，跳过执行阶段")
                    self.state_manager.state.add_message("assistant", llm_response)
                    self.state_manager.state.increment_step()
                    final_response = llm_response
                    break

                # 执行工具
                response = self._act_with_tool(llm_response, tool_call)

                # 记录助手回复
                self.state_manager.state.add_message("assistant", response)

                # 更新状态
                self.state_manager.state.increment_step()
                current_step += 1
                final_response = response

                # 检查执行后的回复是否还需要继续调用工具
                if not self._extract_tool_call(response):
                    break

                # 准备下一轮的用户输入（工具执行结果已包含在消息中）
                user_input = ""

            return final_response

        except Exception as e:
            error_msg = f"Agent运行错误: {str(e)}"
            self.state_manager.record_error(error_msg)
            return error_msg

        finally:
            # 停止运行
            self.state_manager.stop()

    def drain_logs(self) -> list:
        """取出并清空运行日志"""
        return self.state_manager.state.drain_logs()

    def get_state(self) -> Dict[str, Any]:
        """获取当前状态信息"""
        return {
            "config": self.config.model_dump(),
            "state": self.state_manager.state.to_dict(),
            "tools": list(self.tools.keys()),
            "system_prompt_length": len(self.system_prompt),
        }

    def reset(self, clear_history: bool = False) -> None:
        """重置Agent状态"""
        self.state_manager.reset(clear_history=clear_history)

    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"Agent(name={self.config.name}, "
            f"tools={len(self.tools)}, "
            f"steps={self.state_manager.state.current_step})"
        )


class SimpleAgent(Agent):
    """简化版Agent，用于快速测试"""

    def __init__(self, llm: BaseLLM):
        """使用默认配置初始化简化版Agent"""
        super().__init__(llm=llm)

    def chat(self, message: str) -> str:
        """简化聊天接口"""
        return self.run(message)


if __name__ == "__main__":
    # 测试代码
    print("Agent核心类测试")

    # 创建测试LLM
    class TestLLM(BaseLLM):
        def generate(self, messages, **kwargs):
            return "这是一个测试回复。"

        def chat(self, message, **kwargs):
            return f"收到: {message}"

        def get_model_info(self):
            return {"model": "test"}

    # 创建测试工具
    class TestTool(BaseTool):
        @property
        def name(self):
            return "test_tool"

        @property
        def description(self):
            return "测试工具，用于测试"

        def execute(self, input_text):
            return f"测试工具执行结果: {input_text}"

    # 测试Agent
    llm = TestLLM()
    tool = TestTool()
    agent = Agent(llm=llm, tools=[tool])

    print(f"创建Agent: {agent}")
    print(f"Agent状态: {agent.get_state()}")

    # 测试运行
    response = agent.run("你好，测试一下")
    print(f"Agent回复: {response}")
    print(f"运行后状态: {agent.get_state()}")