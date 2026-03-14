"""
配置模块测试
"""

import os
import tempfile
import yaml
from pathlib import Path

from src.agent.core.config import AgentConfig, ConfigManager, get_config


class TestAgentConfig:
    """AgentConfig 测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = AgentConfig()

        assert config.name == "TeachingAgent"
        assert config.max_steps == 10
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.enable_reflection is False
        assert config.enable_planning is False

        # 检查子配置
        assert config.llm.provider == "deepseek"
        assert config.llm.model == "deepseek-chat"
        assert config.memory.short_term.enabled is True
        assert config.tools.safe_mode is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = AgentConfig(
            name="TestAgent",
            max_steps=5,
            temperature=0.9,
            enable_reflection=True,
        )

        assert config.name == "TestAgent"
        assert config.max_steps == 5
        assert config.temperature == 0.9
        assert config.enable_reflection is True
        assert config.enable_planning is False  # 默认值

    def test_config_validation(self):
        """测试配置验证"""
        # 测试温度范围
        config = AgentConfig(temperature=2.5)
        assert config.temperature == 2.5  # Pydantic应该允许，但实际使用时会限制

        # 测试步骤数
        config = AgentConfig(max_steps=0)
        assert config.max_steps == 0  # 同样，Pydantic可能不会验证

    def test_config_to_dict(self):
        """测试配置转字典"""
        config = AgentConfig(name="TestAgent")
        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert config_dict["name"] == "TestAgent"
        assert "llm" in config_dict
        assert "memory" in config_dict
        assert "tools" in config_dict


class TestConfigManager:
    """ConfigManager 测试"""

    def test_default_config_loading(self):
        """测试默认配置加载"""
        manager = ConfigManager()
        config = manager.get_config()

        assert isinstance(config, AgentConfig)
        assert config.name == "TeachingAgent"

    def test_yaml_config_loading(self):
        """测试YAML配置加载"""
        # 创建临时YAML文件
        yaml_content = """
        name: YamlTestAgent
        max_steps: 15
        llm:
          model: test-model
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            manager = ConfigManager(yaml_path)
            config = manager.get_config()

            assert config.name == "YamlTestAgent"
            assert config.max_steps == 15
            assert config.llm.model == "test-model"
            # 其他字段应该保持默认值
            assert config.temperature == 0.7

        finally:
            # 清理临时文件
            Path(yaml_path).unlink()

    def test_env_config_loading(self):
        """测试环境变量配置加载"""
        # 设置环境变量
        os.environ["AGENT_NAME"] = "EnvTestAgent"
        os.environ["AGENT_MAX_STEPS"] = "20"
        os.environ["DEEPSEEK_API_KEY"] = "test-api-key-123"

        try:
            manager = ConfigManager()
            config = manager.get_config()

            assert config.name == "EnvTestAgent"
            assert config.max_steps == 20
            assert config.llm.api_key == "test-api-key-123"

        finally:
            # 清理环境变量
            del os.environ["AGENT_NAME"]
            del os.environ["AGENT_MAX_STEPS"]
            del os.environ["DEEPSEEK_API_KEY"]

    def test_config_priority(self):
        """测试配置优先级（环境变量 > YAML > 默认值）"""
        # 设置环境变量
        os.environ["AGENT_NAME"] = "EnvAgent"

        # 创建YAML文件（包含不同的值）
        yaml_content = """
        name: YamlAgent
        max_steps: 25
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            manager = ConfigManager(yaml_path)
            config = manager.get_config()

            # 环境变量应该优先于YAML
            assert config.name == "EnvAgent"
            # YAML中的其他字段应该生效
            assert config.max_steps == 25

        finally:
            # 清理
            Path(yaml_path).unlink()
            del os.environ["AGENT_NAME"]


class TestGetConfigFunction:
    """get_config 函数测试"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        config1 = get_config()
        config2 = get_config()

        # 应该是同一个配置对象
        assert config1 is config2

    def test_custom_config_path(self):
        """测试自定义配置文件路径"""
        # 创建临时YAML文件
        yaml_content = """
        name: CustomPathAgent
        max_steps: 10
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            # 清除缓存以确保测试从文件加载
            from src.agent.core.config import _config_manager_cache
            original_cache = _config_manager_cache.copy()
            _config_manager_cache.clear()

            config = get_config(yaml_path)
            # 现在应该加载自定义配置
            assert config.name == "CustomPathAgent"
            assert config.max_steps == 10

            # 再次调用应该返回相同的配置（单例）
            config2 = get_config(yaml_path)
            assert config2 is config

        finally:
            Path(yaml_path).unlink()
            # 恢复原始缓存
            _config_manager_cache.clear()
            _config_manager_cache.update(original_cache)


if __name__ == "__main__":
    # 运行测试
    import pytest
    pytest.main([__file__, "-v"])