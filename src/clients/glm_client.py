from typing import Optional

from langchain_openai import ChatOpenAI

from src.clients.base_client import BaseLLMProvider
from src.utils.logger import log
from src.utils.settings import settings


class GlmProvider(BaseLLMProvider):
    """适配公司本地大模型"""

    def __init__(self, model: Optional[str] = None, **kwargs):
        self.model = model or settings.MODEL_NAEM
        self.api_key = kwargs.get('api_key') or settings.API_KEY
        self.api_base = kwargs.get('api_base') or settings.API_BASE
        self.temperature = kwargs.get('temperature', settings.LLM_TEMPERATURE)
        self.max_tokens = kwargs.get('max_tokens', settings.LLM_MAX_TOKENS)
        self.timeout = kwargs.get('timeout', settings.LLM_TIMEOUT)

    def validate_config(self) -> bool:
        """验证GLM配置"""
        if not self.api_key:
            log.error("GLM API Key未设置")
            return False
        if not self.api_base:
            log.error("GLM API Base URL未设置")
            return False
        return True

    def create_client(self) -> ChatOpenAI:
        if not self.validate_config():
            raise ValueError("GLM配置验证失败")

        log.info(f"初始化GLM客户端，模型: {self.model}, API Base: {self.api_base}")
        return ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.api_base,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            max_retries=settings.LLM_MAX_RETRIES
        )