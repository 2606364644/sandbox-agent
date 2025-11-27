# -*- coding: utf-8 -*-
"""LLM客户端抽象层

根据模型名称自动路由到不同的客户端实现：
- qwq-32b: 使用 chat_openai_client.py (支持深度思考)
- 其他模型: 使用 basechat_openai_client.py
"""

from typing import Optional

from .basechat_openai_client import OpenAIProvider as BaseChatOpenAIProvider
from .chat_openai_client import OpenAIProvider as ChatOpenAIProvider
from .base_client import BaseLLMProvider
from src.config.settings import settings
from src.utils.logger import log


class LLMClientFactory:
    """LLM客户端工厂类"""

    @staticmethod
    def create_provider(model: Optional[str] = None, **kwargs) -> BaseLLMProvider:
        """
        根据模型名称创建对应的LLM客户端提供者

        Args:
            model: 模型名称，如果不提供则使用settings.MODEL_NAME
            **kwargs: 其他配置参数

        Returns:
            BaseLLMProvider: 对应的LLM客户端提供者实例
        """
        model_name = model or settings.MODEL_NAME

        if model_name == "qwq-32b":
            return ChatOpenAIProvider(model=model_name, **kwargs)

        else:
            return BaseChatOpenAIProvider(model=model_name, **kwargs)

    @staticmethod
    def create_client(model: Optional[str] = None, **kwargs):
        """
        创建LLM客户端实例

        Args:
            model: 模型名称，如果不提供则使用settings.MODEL_NAME
            **kwargs: 其他配置参数

        Returns:
            LLM客户端实例
        """
        provider = LLMClientFactory.create_provider(model, **kwargs)
        return provider.create_client()


# 便捷函数，供外部直接调用
def get_llm_client(model: Optional[str] = None, **kwargs):
    """获取LLM客户端的便捷函数"""
    return LLMClientFactory.create_client(model, **kwargs)


def get_llm_provider(model: Optional[str] = None, **kwargs) -> BaseLLMProvider:
    """获取LLM提供者的便捷函数"""
    return LLMClientFactory.create_provider(model, **kwargs)


# 导出主要接口 - 遵循最小暴露原则
__all__ = [
    'get_llm_client',      # 获取LLM客户端实例
    'get_llm_provider'     # 获取LLM提供者实例
]