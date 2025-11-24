"""
项目配置管理模块
"""
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings(BaseSettings):
    """项目配置类"""

    # API密钥配置
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")

    # Azure OpenAI配置
    azure_openai_api_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment_name: Optional[str] = Field(default=None, env="AZURE_OPENAI_DEPLOYMENT_NAME")

    # LangChain追踪配置
    langchain_tracing: bool = Field(default=False, env="LANGCHAIN_TRACING_V2")
    langchain_api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="langchain-agent", env="LANGCHAIN_PROJECT")

    # 默认LLM配置
    default_llm_provider: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")
    default_model: str = Field(default="gpt-3.5-turbo", env="DEFAULT_MODEL")
    temperature: float = Field(default=0.0, env="DEFAULT_TEMPERATURE")
    max_tokens: int = Field(default=2000, env="DEFAULT_MAX_TOKENS")

    # 向量数据库配置
    chroma_host: str = Field(default="localhost", env="CHROMA_SERVER_HOST")
    chroma_port: int = Field(default=8000, env="CHROMA_SERVER_HTTP_PORT")

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def update_settings(**kwargs) -> None:
    """更新配置"""
    global settings
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
        else:
            raise ValueError(f"未知的配置项: {key}")