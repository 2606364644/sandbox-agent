import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 计算项目根目录的绝对路径
# __file__ -> D:\...\src\code_review_agent\settings.py
# os.path.dirname(__file__) -> D:\...\src\code_review_agent
# os.path.dirname(...) -> D:\...\src\code_review_agent
# os.path.dirname(...) -> D:\...\src
# os.path.dirname(...) -> D:\... (项目根目录)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    """
    应用配置类，使用Pydantic进行类型校验和自动加载。

    加载优先级:
    1. 环境变量
    2. .env 文件
    3. 模型中定义的默认值
    """
    # .env文件路径配置
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, '.env'),
        env_nested_delimiter="--",
        env_file_encoding='utf-8',
        # extra='ignore'  # 忽略.env文件中多余的字段
    )
    MAX_WORKERS: int = Field(description="并发分析的最大工作线程数", default=2)

    APP_NAME: str = Field(description="应用名称", default="CodeReviewAgent")
    OUTPUT_DIR: str = Field(description="输出目录", default=os.path.join(BASE_DIR, "outputs"))
    LOG_DIR: str = Field(description="日志目录", default=os.path.join(BASE_DIR, "outputs", "logs"))
    LOG_LEVEL: str = Field(description="日志级别", default="INFO")

    # 模型配置
    API_BASE: str = Field(description="API Base URL", default="https://oneapi.sangfor.com/v1")
    API_KEY: str = Field(description="API Key", default="...")
    MODEL_NAME: str = Field(description="模型名称", default="glm45")

    # LLM 超时配置
    LLM_TIMEOUT: int = Field(description="LLM API 请求超时时间（秒）", default=300)  # 5分钟

    # LLM 重试配置
    LLM_MAX_RETRIES: int = Field(description="LLM API 请求最大重试次数", default=3)
    LLM_RETRY_DELAY: float = Field(description="LLM API 请求重试延迟时间（秒）", default=1.0)
    LLM_RETRY_MAX_DELAY: float = Field(description="LLM API 请求重试最大延迟时间（秒）", default=30.0)
    LLM_RETRY_EXP_BASE: float = Field(description="LLM API 请求重试指数退避基础", default=2.0)
    LLM_RETRY_JITTER: float = Field(description="LLM API 请求重试抖动系数", default=0.1)

    # LLM 基础配置
    LLM_TEMPERATURE: float = Field(description="LLM 温度参数", default=0.0)
    LLM_MAX_TOKENS: Optional[int] = Field(description="LLM 最大输出token数", default=None)
    LLM_TOP_P: Optional[float] = Field(description="LLM top_p参数", default=None)


@lru_cache
def get_settings() -> Settings:
    """
    获取并缓存配置实例。
    使用lru_cache确保全局只有一个Settings实例，避免重复读取文件和环境变量。
    """
    return Settings()


# 创建一个全局可用的配置实例
settings = get_settings()


if __name__ == "__main__":
    # 确保日志和输出目录存在
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    # 此时不能直接使用 log，因为 log 依赖 settings
    # 可以临时创建一个 logger
    import logging
    temp_logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    temp_logger.info(f"Gemini API Key Loaded: {'*' * 10 if settings.GEMINI_API_KEY else 'Not Found'}")
    temp_logger.info(f"Output Directory: {settings.OUTPUT_DIR}")
    temp_logger.info(f"Log Directory: {settings.LOG_DIR}")
    temp_logger.info(f"Log Level: {settings.LOG_LEVEL}")
    temp_logger.info(f"Exclude Dirs: {settings.EXCLUDE_DIRS}")
    temp_logger.info(f"Exclude Files: {settings.EXCLUDE_FILES}")
