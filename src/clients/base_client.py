from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel


class BaseLLMProvider(ABC):
    """LLM供应商基类"""

    @abstractmethod
    def create_client(self) -> BaseChatModel:
        """创建LLM客户端"""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        pass