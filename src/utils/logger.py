"""
日志工具模块
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from config.settings import get_settings


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }

    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}"
                f"{self.COLORS['RESET']}"
            )

        # 格式化消息
        formatted = super().format(record)

        # 重置颜色，防止后续输出被影响
        if hasattr(record, 'levelname') and record.levelname in self.COLORS.values():
            formatted += self.COLORS['RESET']

        return formatted


def setup_logger(
    name: str = "langchain_agent",
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    console_output: bool = True,
    colored_output: bool = True
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        console_output: 是否输出到控制台
        colored_output: 是否使用彩色输出

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 获取设置
    settings = get_settings()
    log_level = level or settings.log_level
    log_file_path = log_file or settings.log_file

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 清除现有的处理器
    logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))

        if colored_output and sys.stdout.isatty():
            # 使用彩色格式化器
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    # 文件处理器
    if log_file_path:
        # 确保日志目录存在
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件处理器
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 防止日志传播到根日志记录器
    logger.propagate = False

    return logger


def get_logger(name: str = "langchain_agent") -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 日志记录器
    """
    return logging.getLogger(name)


class LoggerManager:
    """日志管理器"""

    def __init__(self):
        """初始化日志管理器"""
        self.loggers = {}
        self.default_logger = None

    def create_logger(
        self,
        name: str,
        level: Optional[str] = None,
        log_file: Optional[str] = None,
        **kwargs
    ) -> logging.Logger:
        """
        创建日志记录器

        Args:
            name: 日志记录器名称
            level: 日志级别
            log_file: 日志文件路径
            **kwargs: 其他参数

        Returns:
            logging.Logger: 日志记录器
        """
        logger = setup_logger(name, level, log_file, **kwargs)
        self.loggers[name] = logger

        if self.default_logger is None:
            self.default_logger = logger

        return logger

    def get_logger(self, name: str) -> Optional[logging.Logger]:
        """
        获取日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            Optional[logging.Logger]: 日志记录器
        """
        return self.loggers.get(name)

    def list_loggers(self) -> list:
        """
        列出所有日志记录器

        Returns:
            list: 日志记录器名称列表
        """
        return list(self.loggers.keys())

    def set_default_logger(self, name: str) -> bool:
        """
        设置默认日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            bool: 设置是否成功
        """
        if name in self.loggers:
            self.default_logger = self.loggers[name]
            return True
        return False

    def log_agent_activity(self, agent_name: str, activity: str, level: str = "INFO"):
        """
        记录Agent活动

        Args:
            agent_name: Agent名称
            activity: 活动描述
            level: 日志级别
        """
        message = f"[{agent_name}] {activity}"
        if self.default_logger:
            getattr(self.default_logger, level.lower())(message)

    def create_agent_logger(self, agent_name: str) -> logging.Logger:
        """
        为Agent创建专用日志记录器

        Args:
            agent_name: Agent名称

        Returns:
            logging.Logger: Agent专用日志记录器
        """
        logger_name = f"agent.{agent_name}"
        return self.create_logger(logger_name)


# 全局日志管理器实例
logger_manager = LoggerManager()


def init_logging():
    """初始化日志系统"""
    settings = get_settings()

    # 创建默认日志记录器
    default_logger = logger_manager.create_logger(
        "langchain_agent",
        level=settings.log_level,
        log_file=settings.log_file
    )

    # 设置根日志记录器级别
    logging.getLogger().setLevel(logging.WARNING)

    default_logger.info("日志系统已初始化")
    return default_logger


# 日志装饰器
def log_execution(logger_name: str = None, level: str = "INFO"):
    """
    日志装饰器 - 记录函数执行

    Args:
        logger_name: 日志记录器名称
        level: 日志级别
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 获取日志记录器
            if logger_name:
                logger = logger_manager.get_logger(logger_name) or get_logger()
            else:
                logger = get_logger()

            # 记录函数开始执行
            logger.log(
                getattr(logging, level.upper()),
                f"开始执行函数: {func.__name__}"
            )

            try:
                # 执行函数
                result = func(*args, **kwargs)

                # 记录函数执行成功
                logger.log(
                    getattr(logging, level.upper()),
                    f"函数 {func.__name__} 执行成功"
                )

                return result

            except Exception as e:
                # 记录函数执行失败
                logger.error(f"函数 {func.__name__} 执行失败: {str(e)}")
                raise

        return wrapper
    return decorator


# 日志上下文管理器
class LogContext:
    """日志上下文管理器"""

    def __init__(self, logger_name: str, operation: str, level: str = "INFO"):
        """
        初始化日志上下文

        Args:
            logger_name: 日志记录器名称
            operation: 操作描述
            level: 日志级别
        """
        self.logger = logger_manager.get_logger(logger_name) or get_logger()
        self.operation = operation
        self.level = getattr(logging, level.upper())
        self.start_time = None

    def __enter__(self):
        """进入上下文"""
        self.start_time = datetime.now()
        self.logger.log(self.level, f"开始 {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.log(
                self.level,
                f"完成 {self.operation} (耗时: {duration:.2f}秒)"
            )
        else:
            self.logger.error(
                f"{self.operation} 失败 (耗时: {duration:.2f}秒): {exc_val}"
            )

        return False  # 不抑制异常


# 初始化日志系统
init_logging()