import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

from src.config.settings import settings


# ANSI 颜色代码
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD_RED = '\033[1;91m'
    BOLD_GREEN = '\033[1;92m'
    BOLD_YELLOW = '\033[1;93m'
    BOLD_BLUE = '\033[1;94m'
    BOLD_MAGENTA = '\033[1;95m'
    BOLD_CYAN = '\033[1;96m'
    BOLD_WHITE = '\033[1;97m'

# 日志级别对应的颜色
LOG_COLORS = {
    logging.DEBUG: Colors.CYAN,
    logging.INFO: Colors.GREEN,
    logging.WARNING: Colors.YELLOW,
    logging.ERROR: Colors.RED,
    logging.CRITICAL: Colors.BOLD_RED,
}

class ColoredFormatter(logging.Formatter):
    """
    带颜色的日志格式化器
    """
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)

    def format(self, record):
        # 先使用父类的格式化方法
        formatted = super().format(record)

        # 为日志级别添加颜色
        color = LOG_COLORS.get(record.levelno, Colors.RESET)
        levelname = record.levelname
        colored_levelname = f"{color}{levelname}{Colors.RESET}"
        formatted = formatted.replace(f" - {levelname} - ", f" - {colored_levelname} - ")

        return formatted


def setuplogger():
    """
    配置并返回一个全局Logger。
    """
    # 确保日志目录存在
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    log_level = logging.getLevelName(settings.LOG_LEVEL.upper())

    # 创建 logger
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(log_level)

    # 防止重复添加 handler
    if logger.hasHandlers():
        return logger

    # 基础格式化器
    base_format = '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'

    # 控制台 Handler - 使用带颜色或符号的格式化器
    console_formatter = ColoredFormatter(base_format)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(console_formatter)
    logger.addHandler(stream_handler)

    # 文件 Handler (滚动) - 使用普通格式化器
    file_formatter = logging.Formatter(base_format)
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(settings.LOG_DIR, f"{settings.APP_NAME.lower()}_{timestamp}.log")
    # maxBytes=5MB, backupCount=5 (保留5个备份)
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


# 全局可用的logger实例
log = setuplogger()

# 使用示例
if __name__ == '__main__':
    log.debug("这是一条 debug 信息")
    log.info("应用启动成功")
    log.warning("这是一个警告")
    log.error("发生了一个错误", extra={"user_id": 123})
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("捕获到异常")
