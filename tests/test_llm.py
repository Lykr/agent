"""
LLM模块测试
"""

import os
from unittest.mock import Mock, patch
import pytest

from src.agent.llm.base import BaseLLM, LLMConfigError, LLMRequestError
from src.agent.llm.deepseek import DeepSeekLLM, DeepSeekLLMFactory


class TestBaseLLM:
    """BaseLLM 测试"""

    def test_abstract_methods(self):
        """测试抽象方法"""
        # 应该不能直接实例化抽象类
        with pytest.raises(TypeError):
            llm = BaseLLM()  # type: ignore

    def test_concrete_implementation(self):
        """测试具体实现"""
        class ConcreteLLM(BaseLLM):
            def generate(self, messages, **kwargs):
                return "Test response"

            def chat(self, message, **kwargs):
                return f"Echo: {message}"

            def get_model_info(self):
                return {"model": "test"}

        llm = ConcreteLLM()
        assert llm.generate([]) == "Test response"
        assert llm.chat("Hello") == "Echo: Hello"
        assert llm.get_model_info()["model"] == "test"




class TestDeepSeekLLM:
    """DeepSeekLLM 测试（模拟）"""

    def test_deepseek_creation_without_api_key(self):
        """测试没有API密钥的创建"""
        # 清理环境变量
        if "DEEPSEEK_API_KEY" in os.environ:
            del os.environ["DEEPSEEK_API_KEY"]

        with pytest.raises(LLMConfigError, match="未提供DeepSeek API密钥"):
            DeepSeekLLM()

    def test_deepseek_creation_with_env_key(self):
        """测试使用环境变量API密钥"""
        os.environ["DEEPSEEK_API_KEY"] = "sk-test123"

        try:
            llm = DeepSeekLLM()
            assert llm.api_key == "sk-test123"
            assert llm.base_url == "https://api.deepseek.com"
            assert llm.model == "deepseek-chat"
        finally:
            del os.environ["DEEPSEEK_API_KEY"]

    def test_deepseek_creation_with_parameter(self):
        """测试使用参数API密钥"""
        llm = DeepSeekLLM(api_key="sk-param123")
        assert llm.api_key == "sk-param123"

    def test_deepseek_config_validation(self):
        """测试配置验证"""
        # 无效的API密钥格式
        with pytest.raises(LLMConfigError, match="API密钥格式不正确"):
            DeepSeekLLM(api_key="invalid-key")

        # 无效的超时时间
        with pytest.raises(LLMConfigError, match="超时时间必须大于0"):
            DeepSeekLLM(api_key="sk-test123", timeout=0)

        # 无效的重试次数
        with pytest.raises(LLMConfigError, match="重试次数不能为负数"):
            DeepSeekLLM(api_key="sk-test123", max_retries=-1)

    @patch('src.agent.llm.deepseek.requests.post')
    def test_deepseek_generate_success(self, mock_post):
        """测试成功生成（模拟）"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Test response from DeepSeek"
                }
            }]
        }
        mock_post.return_value = mock_response

        llm = DeepSeekLLM(api_key="sk-test123")
        response = llm.generate([
            {"role": "user", "content": "Hello"}
        ])

        assert response == "Test response from DeepSeek"
        mock_post.assert_called_once()

    @patch('src.agent.llm.deepseek.requests.post')
    def test_deepseek_generate_error(self, mock_post):
        """测试生成错误（模拟）"""
        # 模拟错误响应
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        llm = DeepSeekLLM(api_key="sk-test123")

        with pytest.raises(LLMRequestError, match="请求失败"):
            llm.generate([{"role": "user", "content": "Hello"}])

    @patch('src.agent.llm.deepseek.requests.post')
    def test_deepseek_chat(self, mock_post):
        """测试聊天接口（模拟）"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Chat response"
                }
            }]
        }
        mock_post.return_value = mock_response

        llm = DeepSeekLLM(api_key="sk-test123")
        response = llm.chat("Hello")

        assert response == "Chat response"

    def test_deepseek_get_model_info(self):
        """测试获取模型信息"""
        llm = DeepSeekLLM(
            api_key="sk-test123",
            base_url="https://test.api.com",
            model="test-model",
            timeout=60,
            max_retries=5
        )

        info = llm.get_model_info()
        assert info["provider"] == "deepseek"
        assert info["model"] == "test-model"
        assert info["base_url"] == "https://test.api.com"
        assert info["timeout"] == 60
        assert info["max_retries"] == 5

    @patch('src.agent.llm.deepseek.requests.post')
    def test_deepseek_test_connection(self, mock_post):
        """测试连接测试"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Test"
                }
            }]
        }
        mock_post.return_value = mock_response

        llm = DeepSeekLLM(api_key="sk-test123")
        assert llm.test_connection() is True

        # 测试连接失败
        mock_response.status_code = 401
        assert llm.test_connection() is False


class TestDeepSeekLLMFactory:
    """DeepSeekLLMFactory 测试"""

    def test_create_from_config(self):
        """测试从配置创建"""
        config = {
            "api_key": "sk-config123",
            "base_url": "https://config.api.com",
            "model": "config-model",
            "timeout": 90,
            "max_retries": 7
        }

        llm = DeepSeekLLMFactory.create_from_config(config)
        assert llm.api_key == "sk-config123"
        assert llm.base_url == "https://config.api.com"
        assert llm.model == "config-model"
        assert llm.timeout == 90
        assert llm.max_retries == 7

    def test_create_from_env(self):
        """测试从环境变量创建"""
        # 设置环境变量
        os.environ["DEEPSEEK_API_KEY"] = "sk-env123"
        os.environ["DEEPSEEK_BASE_URL"] = "https://env.api.com"
        os.environ["DEEPSEEK_MODEL"] = "env-model"
        os.environ["DEEPSEEK_TIMEOUT"] = "120"
        os.environ["DEEPSEEK_MAX_RETRIES"] = "9"

        try:
            llm = DeepSeekLLMFactory.create_from_env()
            assert llm.api_key == "sk-env123"
            assert llm.base_url == "https://env.api.com"
            assert llm.model == "env-model"
            assert llm.timeout == 120
            assert llm.max_retries == 9
        finally:
            # 清理环境变量
            for key in ["DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
                       "DEEPSEEK_TIMEOUT", "DEEPSEEK_MAX_RETRIES"]:
                if key in os.environ:
                    del os.environ[key]


if __name__ == "__main__":
    # 运行测试
    import pytest
    pytest.main([__file__, "-v"])