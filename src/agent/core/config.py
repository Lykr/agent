"""
Agent 配置管理模块

提供配置加载、验证和管理功能。
支持从环境变量、YAML文件和默认值加载配置。
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = Field(default="deepseek", description="LLM提供商")
    model: str = Field(default="deepseek-chat", description="模型名称")
    base_url: str = Field(default="https://api.deepseek.com", description="API基础URL")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    timeout: int = Field(default=30, description="请求超时时间（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=2000, description="最大生成token数")


class MemoryConfig(BaseModel):
    """记忆系统配置"""

    class ShortTermConfig(BaseModel):
        """短期记忆配置"""
        enabled: bool = Field(default=True, description="是否启用短期记忆")
        max_entries: int = Field(default=20, description="最大记忆条目数")
        max_history: int = Field(default=10, description="最大历史记录数")

    class LongTermConfig(BaseModel):
        """长期记忆配置"""
        enabled: bool = Field(default=False, description="是否启用长期记忆")
        vector_db_provider: str = Field(default="chroma", description="向量数据库提供商")
        persist_path: str = Field(default="./data/memory", description="持久化路径")
        collection_name: str = Field(default="agent_memories", description="集合名称")
        embedding_model: str = Field(default="all-MiniLM-L6-v2", description="嵌入模型")
        retrieval_threshold: float = Field(default=0.7, description="检索阈值")

    short_term: ShortTermConfig = Field(default_factory=ShortTermConfig)
    long_term: LongTermConfig = Field(default_factory=LongTermConfig)


class ToolsConfig(BaseModel):
    """工具系统配置"""
    timeout: int = Field(default=30, description="工具执行超时时间（秒）")
    safe_mode: bool = Field(default=True, description="安全模式")
    allowed_directories: list[str] = Field(
        default_factory=lambda: ["./data", "./examples"],
        description="允许访问的目录"
    )


class AgentConfig(BaseModel):
    """Agent 主配置"""

    # 基础配置
    name: str = Field(default="TeachingAgent", description="Agent名称")
    max_steps: int = Field(default=10, description="最大执行步骤数")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=2000, description="最大生成token数")

    # 功能开关
    enable_reflection: bool = Field(default=False, description="是否启用反思")
    enable_planning: bool = Field(default=False, description="是否启用规划")

    # 子配置
    llm: LLMConfig = Field(default_factory=LLMConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> AgentConfig:
        """加载配置"""
        config_data = self._get_default_config()

        # 从YAML文件加载配置
        if self.config_path and Path(self.config_path).exists():
            yaml_config = self._load_yaml_config(self.config_path)
            config_data.update(yaml_config)

        # 从环境变量加载配置
        env_config = self._load_env_config()
        config_data.update(env_config)

        return AgentConfig(**config_data)

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "name": "TeachingAgent",
            "max_steps": 10,
            "temperature": 0.7,
            "max_tokens": 2000,
            "enable_reflection": False,
            "enable_planning": False,
        }

    def _load_yaml_config(self, path: str) -> Dict[str, Any]:
        """从YAML文件加载配置"""
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            print("警告: 未安装PyYAML，跳过YAML配置加载")
            return {}
        except Exception as e:
            print(f"警告: 加载YAML配置失败: {e}")
            return {}

    def _load_env_config(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        config = {}

        # Agent基础配置
        if env_name := os.getenv("AGENT_NAME"):
            config["name"] = env_name
        if env_steps := os.getenv("AGENT_MAX_STEPS"):
            config["max_steps"] = int(env_steps)

        # LLM配置
        llm_config = {}
        if api_key := os.getenv("DEEPSEEK_API_KEY"):
            llm_config["api_key"] = api_key
        if base_url := os.getenv("DEEPSEEK_BASE_URL"):
            llm_config["base_url"] = base_url

        if llm_config:
            config["llm"] = llm_config

        return config

    def get_config(self) -> AgentConfig:
        """获取当前配置"""
        return self.config


# 配置管理器缓存，按路径缓存
_config_manager_cache: Dict[Optional[str], ConfigManager] = {}


def get_config(config_path: Optional[str] = None) -> AgentConfig:
    """
    获取配置

    Args:
        config_path: 配置文件路径

    Returns:
        AgentConfig: 配置对象
    """
    global _config_manager_cache

    if config_path not in _config_manager_cache:
        _config_manager_cache[config_path] = ConfigManager(config_path)

    return _config_manager_cache[config_path].get_config()


if __name__ == "__main__":
    # 测试配置加载
    config = get_config()
    print("当前配置:")
    print(config.model_dump_json(indent=2))