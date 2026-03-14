"""
DeepSeek LLM 实现

集成DeepSeek API，提供LLM功能。
"""

import os
import time
from typing import Any, Dict, List, Optional
import requests

from .base import BaseLLM, LLMConfigError, LLMRequestError, LLMResponseError


class DeepSeekLLM(BaseLLM):
    """DeepSeek LLM 实现"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        初始化DeepSeek LLM

        Args:
            api_key: API密钥，如果为None则从环境变量读取
            base_url: API基础URL
            model: 模型名称
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise LLMConfigError("未提供DeepSeek API密钥，请设置DEEPSEEK_API_KEY环境变量或传入api_key参数")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

        # 验证配置
        self._validate_config()

    def _validate_config(self) -> None:
        """验证配置"""
        if not self.api_key.startswith("sk-"):
            raise LLMConfigError(f"API密钥格式不正确: {self.api_key[:10]}...")

        if self.timeout <= 0:
            raise LLMConfigError(f"超时时间必须大于0: {self.timeout}")

        if self.max_retries < 0:
            raise LLMConfigError(f"重试次数不能为负数: {self.max_retries}")

    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            endpoint: API端点
            data: 请求数据

        Returns:
            响应数据
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.json()

                # 处理错误状态码
                error_msg = f"HTTP {response.status_code}: {response.text}"
                if response.status_code == 401:
                    raise LLMConfigError(f"认证失败: {error_msg}")
                elif response.status_code == 429:
                    raise LLMRequestError(f"请求过于频繁: {error_msg}")
                elif 500 <= response.status_code < 600:
                    # 服务器错误，可以重试
                    last_error = LLMRequestError(f"服务器错误: {error_msg}")
                    if attempt < self.max_retries:
                        time.sleep(1 * (attempt + 1))  # 指数退避
                        continue
                else:
                    raise LLMRequestError(f"请求失败: {error_msg}")

            except requests.exceptions.Timeout:
                last_error = LLMRequestError(f"请求超时: {self.timeout}秒")
                if attempt < self.max_retries:
                    time.sleep(1 * (attempt + 1))
                    continue
            except requests.exceptions.ConnectionError as e:
                last_error = LLMRequestError(f"连接错误: {str(e)}")
                if attempt < self.max_retries:
                    time.sleep(1 * (attempt + 1))
                    continue
            except Exception as e:
                last_error = LLMRequestError(f"未知错误: {str(e)}")
                break

        # 所有重试都失败
        if last_error:
            raise last_error
        else:
            raise LLMRequestError("请求失败，未知原因")

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
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        # 构建请求数据
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": max(0.0, min(2.0, temperature)),
            "max_tokens": max(1, min(4096, max_tokens)),
            "stream": False
        }

        # 添加可选参数
        if "top_p" in kwargs:
            data["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            data["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            data["presence_penalty"] = kwargs["presence_penalty"]

        try:
            # 发送请求
            response = self._make_request("/chat/completions", data)

            # 解析响应
            if "choices" not in response or len(response["choices"]) == 0:
                raise LLMResponseError("响应中没有choices字段")

            choice = response["choices"][0]
            if "message" not in choice or "content" not in choice["message"]:
                raise LLMResponseError("响应中没有content字段")

            return choice["message"]["content"].strip()

        except LLMRequestError:
            raise
        except Exception as e:
            raise LLMResponseError(f"解析响应失败: {str(e)}")

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
        messages = [{"role": "user", "content": message}]
        return self.generate(messages, temperature, max_tokens, **kwargs)

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "deepseek",
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            # 发送一个简单的测试请求
            test_messages = [{"role": "user", "content": "Hello"}]
            response = self.generate(test_messages, max_tokens=10)
            return bool(response and len(response) > 0)
        except Exception:
            return False


class DeepSeekLLMFactory:
    """DeepSeek LLM 工厂类"""

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> DeepSeekLLM:
        """
        从配置创建DeepSeek LLM实例

        Args:
            config: 配置字典

        Returns:
            DeepSeekLLM实例
        """
        return DeepSeekLLM(
            api_key=config.get("api_key"),
            base_url=config.get("base_url", "https://api.deepseek.com"),
            model=config.get("model", "deepseek-chat"),
            timeout=config.get("timeout", 30),
            max_retries=config.get("max_retries", 3)
        )

    @staticmethod
    def create_from_env() -> DeepSeekLLM:
        """
        从环境变量创建DeepSeek LLM实例

        Returns:
            DeepSeekLLM实例
        """
        return DeepSeekLLM(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "30")),
            max_retries=int(os.getenv("DEEPSEEK_MAX_RETRIES", "3"))
        )


if __name__ == "__main__":
    # 测试代码
    print("DeepSeek LLM测试")

    # 从环境变量创建（需要设置DEEPSEEK_API_KEY环境变量）
    try:
        llm = DeepSeekLLMFactory.create_from_env()
        print(f"创建LLM: {llm}")
        print(f"模型信息: {llm.get_model_info()}")

        # 测试连接
        print("测试连接...")
        if llm.test_connection():
            print("连接测试成功")
        else:
            print("连接测试失败")

        # 测试生成
        print("\n测试生成...")
        messages = [
            {"role": "system", "content": "你是一个有帮助的助手。"},
            {"role": "user", "content": "你好，请简单介绍一下自己。"}
        ]
        response = llm.generate(messages, max_tokens=100)
        print(f"回复: {response}")

    except LLMConfigError as e:
        print(f"配置错误: {e}")
        print("请设置DEEPSEEK_API_KEY环境变量")
    except LLMRequestError as e:
        print(f"请求错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")