#!/usr/bin/env python3
"""
交互式 Agent 运行脚本
"""

import os
import readline  # noqa: F401 - 启用终端行编辑支持
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent.core.agent import Agent
from src.agent.llm.deepseek import DeepSeekLLM
from src.agent.tools.file_tools import FileToolsFactory


def print_log(phase: str, content: str) -> None:
    """实时打印 Agent 运行日志"""
    print(f"  [{phase}] {content}")


def main():
    # 创建 LLM
    llm = DeepSeekLLM()

    # 创建文件工具
    tools = FileToolsFactory.create_basic_tools(
        allowed_directories=[os.getcwd()],
    )

    # 创建 Agent，传入日志回调
    agent = Agent(llm=llm, tools=tools, on_log=print_log)
    print(f"Agent 已启动 ({agent.config.name})")
    print(f"可用工具: {list(agent.tools.keys())}")
    print("输入 'quit' 或 'exit' 退出\n")

    while True:
        try:
            user_input = input("你: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("再见！")
            break

        response = agent.run(user_input)
        print(f"Agent: {response}\n")


if __name__ == "__main__":
    main()
