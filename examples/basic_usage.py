"""
基础使用示例

展示如何使用Agent框架的基本功能。
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.core.agent import Agent, SimpleAgent
from src.agent.llm.deepseek import DeepSeekLLMFactory
from src.agent.tools.file_tools import FileToolsFactory


def example_1_basic_agent():
    """示例1: 基础Agent使用"""
    print("=" * 60)
    print("示例1: 基础Agent使用")
    print("=" * 60)

    # 检查API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("⚠️  警告: 未设置DeepSeek API密钥")
        print("请设置环境变量 DEEPSEEK_API_KEY 或编辑 .env 文件")
        print("跳过此示例...")
        print()
        return

    # 创建DeepSeek LLM
    llm = DeepSeekLLMFactory.create_default()

    # 创建简单Agent
    agent = SimpleAgent(llm=llm)

    # 进行对话
    response = agent.chat("你好，请介绍一下自己")
    print(f"用户: 你好，请介绍一下自己")
    print(f"Agent: {response}")
    print()

    # 查看状态
    state = agent.get_state()
    print(f"Agent状态: {state['state']}")
    print()


def example_2_agent_with_tools():
    """示例2: 带工具的Agent"""
    print("=" * 60)
    print("示例2: 带工具的Agent")
    print("=" * 60)

    # 检查API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("⚠️  警告: 未设置DeepSeek API密钥")
        print("请设置环境变量 DEEPSEEK_API_KEY 或编辑 .env 文件")
        print("跳过此示例...")
        print()
        return

    # 创建DeepSeek LLM
    llm = DeepSeekLLMFactory.create_default()

    # 创建文件工具（限制在当前目录）
    current_dir = os.getcwd()
    tools = FileToolsFactory.create_basic_tools(
        allowed_directories=[current_dir],
        timeout=10,
        safe_mode=True
    )

    # 创建Agent
    agent = Agent(llm=llm, tools=tools)

    # 测试1: 列出当前目录
    print("测试1: 列出当前目录")
    response = agent.run("请列出当前目录的内容")
    print(f"用户: 请列出当前目录的内容")
    print(f"Agent: {response[:200]}...")  # 只显示前200字符
    print()

    # 测试2: 创建测试文件
    print("测试2: 创建测试文件")
    test_file = os.path.join(current_dir, "test_example.txt")
    input_text = f"{test_file}\n这是一个测试文件，由Agent示例创建。"
    response = agent.run(f"请创建文件: {test_file}")
    print(f"用户: 请创建文件: {test_file}")
    print(f"Agent: {response}")
    print()

    # 测试3: 读取测试文件
    print("测试3: 读取测试文件")
    response = agent.run(f"请读取文件: {test_file}")
    print(f"用户: 请读取文件: {test_file}")
    print(f"Agent: {response[:200]}...")
    print()

    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"已清理测试文件: {test_file}")
    print()


def example_3_agent_state_management():
    """示例3: Agent状态管理"""
    print("=" * 60)
    print("示例3: Agent状态管理")
    print("=" * 60)

    # 检查API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("⚠️  警告: 未设置DeepSeek API密钥")
        print("请设置环境变量 DEEPSEEK_API_KEY 或编辑 .env 文件")
        print("跳过此示例...")
        print()
        return

    # 创建DeepSeek LLM
    llm = DeepSeekLLMFactory.create_default()

    # 创建Agent
    agent = Agent(llm=llm)

    # 进行多次对话
    print("进行多次对话:")
    for i in range(3):
        response = agent.run(f"消息 {i+1}")
        print(f"用户: 消息 {i+1}")
        print(f"Agent: {response}")

    # 查看详细状态
    print("\n当前状态详情:")
    state = agent.get_state()
    print(f"会话ID: {state['state']['session_id']}")
    print(f"当前步骤: {state['state']['current_step']}")
    print(f"消息数量: {state['state']['message_count']}")
    print(f"开始时间: {state['state']['start_time']}")

    # 重置Agent（保留历史）
    print("\n重置Agent（保留历史）...")
    agent.reset(clear_history=False)
    state = agent.get_state()
    print(f"重置后步骤: {state['state']['current_step']}")
    print(f"重置后消息数量: {state['state']['message_count']}")

    # 重置Agent（清空历史）
    print("\n重置Agent（清空历史）...")
    agent.reset(clear_history=True)
    state = agent.get_state()
    print(f"重置后步骤: {state['state']['current_step']}")
    print(f"重置后消息数量: {state['state']['message_count']}")
    print()


def example_4_custom_configuration():
    """示例4: 自定义配置"""
    print("=" * 60)
    print("示例4: 自定义配置")
    print("=" * 60)

    from src.agent.core.config import AgentConfig

    # 创建自定义配置
    config = AgentConfig(
        name="CustomAgent",
        max_steps=5,
        temperature=0.9,
        enable_reflection=False,
        enable_planning=False
    )

    # 检查API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("⚠️  警告: 未设置DeepSeek API密钥")
        print("请设置环境变量 DEEPSEEK_API_KEY 或编辑 .env 文件")
        print("跳过此示例...")
        print()
        return

    # 创建DeepSeek LLM
    llm = DeepSeekLLMFactory.create_default()

    # 使用自定义配置创建Agent
    agent = Agent(llm=llm, config=config)

    print(f"Agent名称: {agent.config.name}")
    print(f"最大步骤: {agent.config.max_steps}")
    print(f"温度参数: {agent.config.temperature}")
    print(f"启用反思: {agent.config.enable_reflection}")
    print(f"启用规划: {agent.config.enable_planning}")
    print()

    # 测试运行
    response = agent.run("测试自定义配置")
    print(f"测试运行: {response}")
    print()


def example_5_error_handling():
    """示例5: 错误处理"""
    print("=" * 60)
    print("示例5: 错误处理")
    print("=" * 60)

    # 检查API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("⚠️  警告: 未设置DeepSeek API密钥")
        print("请设置环境变量 DEEPSEEK_API_KEY 或编辑 .env 文件")
        print("跳过此示例...")
        print()
        return

    # 创建DeepSeek LLM
    llm = DeepSeekLLMFactory.create_default()

    # 创建Agent
    agent = Agent(llm=llm)

    # 测试网络错误处理（通过设置无效的API密钥）
    print("测试网络错误处理...")
    original_key = os.environ.get("DEEPSEEK_API_KEY")
    os.environ["DEEPSEEK_API_KEY"] = "invalid_key"

    try:
        # 重新创建LLM以使用无效密钥
        llm_invalid = DeepSeekLLMFactory.create_default()
        agent_invalid = Agent(llm=llm_invalid)
        response = agent_invalid.run("测试错误处理")
        print(f"响应: {response}")
    except Exception as e:
        print(f"捕获到预期错误: {type(e).__name__}: {str(e)[:100]}...")
    finally:
        # 恢复原始API密钥
        if original_key:
            os.environ["DEEPSEEK_API_KEY"] = original_key
        else:
            del os.environ["DEEPSEEK_API_KEY"]

    print()


def main():
    """主函数"""
    print("AI Agent 框架使用示例")
    print("=" * 60)

    try:
        # 运行所有示例
        example_1_basic_agent()
        example_2_agent_with_tools()
        example_3_agent_state_management()
        example_4_custom_configuration()
        example_5_error_handling()

        print("所有示例执行完成！")
        print("\n下一步建议:")
        print("1. 设置DeepSeek API密钥（编辑.env文件）")
        print("2. 运行测试: python -m pytest tests/ -v")
        print("3. 查看文档: docs/ 目录")
        print("4. 尝试创建自己的工具")

    except Exception as e:
        print(f"示例执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()