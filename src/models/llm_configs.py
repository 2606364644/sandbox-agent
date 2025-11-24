"""
LLM配置模块
"""
from typing import Optional, Dict, Any, List
from enum import Enum
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_community.llms import HuggingFaceHub
from config.settings import get_settings


class LLMProvider(str, Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"


class LLMConfig:
    """LLM配置管理类"""

    def __init__(self, provider: LLMProvider = None, model: str = None, **kwargs):
        self.settings = get_settings()
        self.provider = provider or LLMProvider(self.settings.default_llm_provider)
        self.model = model or self.settings.default_model
        self.kwargs = kwargs

    def create_llm(self) -> BaseLanguageModel:
        """创建LLM实例"""
        if self.provider == LLMProvider.OPENAI:
            return self._create_openai_llm()
        elif self.provider == LLMProvider.AZURE_OPENAI:
            return self._create_azure_openai_llm()
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._create_anthropic_llm()
        elif self.provider == LLMProvider.HUGGINGFACE:
            return self._create_huggingface_llm()
        else:
            raise ValueError(f"不支持的LLM提供商: {self.provider}")

    def _create_openai_llm(self) -> ChatOpenAI:
        """创建OpenAI LLM实例"""
        if not self.settings.openai_api_key:
            raise ValueError("未设置OpenAI API密钥")

        default_kwargs = {
            "openai_api_key": self.settings.openai_api_key,
            "model": self.model,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }

        default_kwargs.update(self.kwargs)
        return ChatOpenAI(**default_kwargs)

    def _create_azure_openai_llm(self) -> AzureChatOpenAI:
        """创建Azure OpenAI LLM实例"""
        if not self.settings.azure_openai_api_key:
            raise ValueError("未设置Azure OpenAI API密钥")

        default_kwargs = {
            "openai_api_key": self.settings.azure_openai_api_key,
            "azure_endpoint": self.settings.azure_openai_endpoint,
            "deployment_name": self.settings.azure_openai_deployment_name,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }

        default_kwargs.update(self.kwargs)
        return AzureChatOpenAI(**default_kwargs)

    def _create_anthropic_llm(self):
        """创建Anthropic LLM实例"""
        # 由于LangChain中Anthropic的实现可能不同，这里需要导入相应的类
        from langchain_community.llms import Anthropic

        if not self.settings.anthropic_api_key:
            raise ValueError("未设置Anthropic API密钥")

        default_kwargs = {
            "anthropic_api_key": self.settings.anthropic_api_key,
            "model": self.model,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }

        default_kwargs.update(self.kwargs)
        return Anthropic(**default_kwargs)

    def _create_huggingface_llm(self) -> HuggingFaceHub:
        """创建HuggingFace LLM实例"""
        from config.settings import get_settings

        default_kwargs = {
            "repo_id": self.model,
            "model_kwargs": {
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens,
            }
        }

        default_kwargs.update(self.kwargs)
        return HuggingFaceHub(**default_kwargs)


def create_llm(
    provider: LLMProvider = None,
    model: str = None,
    **kwargs
) -> BaseLanguageModel:
    """
    创建LLM实例的便捷函数

    Args:
        provider: LLM提供商
        model: 模型名称
        **kwargs: 其他参数

    Returns:
        BaseLanguageModel: LLM实例
    """
    config = LLMConfig(provider, model, **kwargs)
    return config.create_llm()


def get_available_models(provider: LLMProvider) -> List[str]:
    """获取指定提供商的可用模型列表"""
    models_map = {
        LLMProvider.OPENAI: [
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ],
        LLMProvider.AZURE_OPENAI: [
            "gpt-4",
            "gpt-35-turbo"
        ],
        LLMProvider.ANTHROPIC: [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ],
        LLMProvider.HUGGINGFACE: [
            "google/flan-t5-base",
            "google/flan-t5-large",
            "microsoft/DialoGPT-medium",
            "microsoft/DialoGPT-large"
        ]
    }

    return models_map.get(provider, [])