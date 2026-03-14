"""
LLM 抽象接口

定义LLM的标准接口，支持不同的LLM提供商。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLM(ABC):
    """LLM 抽象基类"""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        生成回复

        Args:
            messages: 消息列表，每个消息包含role和content
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        pass

    @abstractmethod
    def chat(
        self,
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        简化聊天接口

        Args:
            message: 用户消息
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Returns:
            LLM的回复
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass

    def __str__(self) -> str:
        """字符串表示"""
        info = self.get_model_info()
        return f"{self.__class__.__name__}(model={info.get('model', 'unknown')})"


class LLMError(Exception):
    """LLM相关错误"""
    pass


class LLMConfigError(LLMError):
    """配置错误"""
    pass


class LLMRequestError(LLMError):
    """请求错误"""
    pass


class LLMResponseError(LLMError):
    """响应错误"""
    pass