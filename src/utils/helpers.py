"""
辅助工具模块
"""
import os
import sys
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from pathlib import Path
from datetime import datetime
import hashlib
import re
import logging

logger = logging.getLogger(__name__)


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建

    Args:
        path: 目录路径

    Returns:
        Path: Path对象
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    加载JSON文件

    Args:
        file_path: 文件路径

    Returns:
        Dict[str, Any]: JSON数据
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"文件不存在: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON格式错误: {e}")
        raise
    except Exception as e:
        logger.error(f"加载文件失败: {e}")
        raise


def save_json_file(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    保存数据到JSON文件

    Args:
        data: 要保存的数据
        file_path: 文件路径
    """
    try:
        ensure_directory(Path(file_path).parent)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        raise


def generate_hash(text: str) -> str:
    """
    生成文本的MD5哈希

    Args:
        text: 文本内容

    Returns:
        str: MD5哈希值
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """
    格式化时间戳

    Args:
        timestamp: 时间戳，默认为当前时间

    Returns:
        str: 格式化的时间字符串
    """
    if timestamp is None:
        timestamp = datetime.now()
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_text(text: str) -> str:
    """
    清理文本（移除多余空白和特殊字符）

    Args:
        text: 原始文本

    Returns:
        str: 清理后的文本
    """
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text.strip())
    # 移除控制字符
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return text


def extract_keywords(text: str, min_length: int = 3, max_keywords: int = 10) -> List[str]:
    """
    提取文本关键词

    Args:
        text: 输入文本
        min_length: 关键词最小长度
        max_keywords: 最大关键词数量

    Returns:
        List[str]: 关键词列表
    """
    # 简单的关键词提取（基于词频）
    words = re.findall(r'\b\w+\b', text.lower())
    word_freq = {}

    for word in words:
        if len(word) >= min_length and word.isalpha():
            word_freq[word] = word_freq.get(word, 0) + 1

    # 按频率排序并返回前N个关键词
    keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in keywords[:max_keywords]]


def validate_url(url: str) -> bool:
    """
    验证URL格式

    Args:
        url: URL字符串

    Returns:
        bool: 是否为有效URL
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名（移除或替换非法字符）

    Args:
        filename: 原始文件名

    Returns:
        str: 安全的文件名
    """
    # 移除或替换非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    filename = re.sub(illegal_chars, '_', filename)

    # 移除多余的空格和点
    filename = re.sub(r'\s+', '_', filename.strip())
    filename = re.sub(r'\.+', '.', filename)

    # 确保文件名不为空
    if not filename or filename == '.':
        filename = f"unnamed_{format_timestamp().replace(':', '')}"

    return filename


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        str: 格式化的文件大小
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数
        exceptions: 要重试的异常类型
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}, "
                            f"{current_delay:.1f}秒后重试"
                        )
                        asyncio.sleep(current_delay) if asyncio.iscoroutinefunction(func) else time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"函数 {func.__name__} 在 {max_retries + 1} 次尝试后仍然失败"
                        )

            raise last_exception
        return wrapper
    return decorator


async def async_retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    异步重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数
        exceptions: 要重试的异常类型
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"异步函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}, "
                            f"{current_delay:.1f}秒后重试"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"异步函数 {func.__name__} 在 {max_retries + 1} 次尝试后仍然失败"
                        )

            raise last_exception
        return wrapper
    return decorator


def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息

    Returns:
        Dict[str, Any]: 系统信息
    """
    import platform
    import psutil

    return {
        "platform": platform.platform(),
        "python_version": sys.version,
        "cpu_count": psutil.cpu_count(),
        "memory_total": format_file_size(psutil.virtual_memory().total),
        "memory_available": format_file_size(psutil.virtual_memory().available),
        "disk_usage": {
            "total": format_file_size(psutil.disk_usage('/').total),
            "free": format_file_size(psutil.disk_usage('/').free)
        }
    }


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    将文本分块

    Args:
        text: 输入文本
        chunk_size: 块大小
        overlap: 重叠大小

    Returns:
        List[str]: 文本块列表
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


class Timer:
    """计时器上下文管理器"""

    def __init__(self, description: str = "操作"):
        """
        初始化计时器

        Args:
            description: 描述信息
        """
        self.description = description
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """进入上下文"""
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        self.end_time = datetime.now()
        duration = self.duration
        logger.info(f"{self.description}完成，耗时: {duration:.2f}秒")

    @property
    def duration(self) -> float:
        """获取持续时间（秒）"""
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个字典

    Args:
        dict1: 第一个字典
        dict2: 第二个字典

    Returns:
        Dict[str, Any]: 合并后的字典
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if (key in result and
            isinstance(result[key], dict) and
            isinstance(value, dict)):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    扁平化字典

    Args:
        d: 输入字典
        parent_key: 父键名
        sep: 分隔符

    Returns:
        Dict[str, Any]: 扁平化后的字典
    """
    items = []

    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    return dict(items)