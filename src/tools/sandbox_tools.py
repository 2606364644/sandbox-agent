"""
Langchain工具装饰器版本
提供与Langchain框架集成的工具
"""

from typing import Optional
from langchain.tools import tool

# 导入核心功能函数
from src.tools.common import (
    read_file_core,
    read_file_info_core,
    list_files_core,
    write_to_file_core,
    search_files_core,
    search_and_replace_core,
    codebase_search_core,
    list_code_definitions_core,
    execute_command_core,
)
from src.tools.common.system_tools import load_conversation_history, save_conversation_history


# 文件操作工具
@tool
def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """
    读取文件内容的工具

    Args:
        file_path: 文件路径（相对于当前工作目录或绝对路径）
        start_line: 起始行号（可选，从1开始）
        end_line: 结束行号（可选）

    Returns:
        文件内容字符串，包含行号
    """
    return read_file_core(file_path, start_line, end_line)


@tool
def read_file_info(file_path: str) -> str:
    """
    获取文件基本信息

    Args:
        file_path: 文件路径

    Returns:
        包含文件信息的字符串
    """
    info = read_file_info_core(file_path)
    if isinstance(info, dict):
        if "error" in info:
            return info["error"]

        result = f"📄 文件信息: {info['name']}\n"
        result += f"路径: {info['path']}\n"
        result += f"大小: {info['size']} 字节\n"
        result += f"类型: {info.get('mime_type', '未知')}\n"
        result += f"是否二进制: {'是' if info.get('is_binary', False) else '否'}\n"
        result += f"修改时间: {info.get('modified_time', '未知')}\n"
        return result
    return str(info)


@tool
def list_files(directory: str, recursive: bool = False, max_files: int = 200) -> str:
    """
    列出目录中的文件和子目录

    Args:
        directory: 目录路径（相对于当前工作目录或绝对路径）
        recursive: 是否递归搜索子目录
        max_files: 最大文件数量限制

    Returns:
        格式化的文件列表字符串
    """
    return list_files_core(directory, recursive, max_files)


@tool
def write_to_file(file_path: str, content: str, create_dirs: bool = True) -> str:
    """
    将内容写入文件

    Args:
        file_path: 文件路径（相对于当前工作目录或绝对路径）
        content: 要写入的内容
        create_dirs: 是否自动创建不存在的目录

    Returns:
        操作结果字符串
    """
    return write_to_file_core(file_path, content, create_dirs)


@tool
def search_files(directory: str, pattern: str, file_pattern: Optional[str] = None,
                 use_regex: bool = False, case_sensitive: bool = False) -> str:
    """
    在文件中搜索内容

    Args:
        directory: 搜索目录
        pattern: 搜索模式
        file_pattern: 文件名模式过滤
        use_regex: 是否使用正则表达式
        case_sensitive: 是否区分大小写

    Returns:
        搜索结果字符串
    """
    return search_files_core(directory, pattern, file_pattern, use_regex, case_sensitive)


@tool
def search_and_replace(file_path: str, search: str, replace: str,
                       use_regex: bool = False, case_sensitive: bool = False,
                       start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """
    在文件中搜索并替换内容

    Args:
        file_path: 文件路径
        search: 搜索内容
        replace: 替换内容
        use_regex: 是否使用正则表达式
        case_sensitive: 是否区分大小写
        start_line: 起始行号
        end_line: 结束行号

    Returns:
        操作结果字符串
    """
    return search_and_replace_core(file_path, search, replace, use_regex, case_sensitive, start_line, end_line)


# 代码分析工具
@tool
def codebase_search(query: str, directory: Optional[str] = None,
                    file_types: Optional[str] = None) -> str:
    """
    在代码库中搜索相关代码

    Args:
        query: 搜索查询
        directory: 搜索目录（默认为当前目录）
        file_types: 文件类型过滤，用逗号分隔，如 ".py,.js,.ts"

    Returns:
        搜索结果字符串
    """
    file_types_list = None
    if file_types:
        file_types_list = [ext.strip() for ext in file_types.split(',')]

    return codebase_search_core(query, directory, file_types_list)


@tool
def list_code_definitions(file_path: str) -> str:
    """
    列出文件中的代码定义（函数、类、变量等）

    Args:
        file_path: 文件路径

    Returns:
        代码定义列表字符串
    """
    return list_code_definitions_core(file_path)


# 系统工具
@tool
def execute_command(command: str, cwd: Optional[str] = None,
                    timeout: int = 300, max_output: int = 10000) -> str:
    """
    执行系统命令

    Args:
        command: 要执行的命令
        cwd: 工作目录（默认为当前目录）
        timeout: 超时时间（秒）
        max_output: 最大输出字符数

    Returns:
        命令执行结果字符串
    """
    return execute_command_core(command, cwd, timeout, max_output)


@tool
def get_system_info() -> str:
    """
    获取系统信息

    Returns:
        系统信息字符串
    """
    # 调用核心函数，避免递归
    from src.tools.common import get_system_info as get_system_info_core
    return get_system_info_core()


@tool
def check_directory_permissions(directory: str) -> str:
    """
    检查目录权限

    Args:
        directory: 要检查的目录路径

    Returns:
        目录权限信息字符串
    """
    from src.tools.common import check_directory_permissions as check_directory_permissions_core
    return check_directory_permissions_core(directory)


@tool
def validate_path_security(file_path: str, base_directory: Optional[str] = None) -> str:
    """
    验证路径安全性，防止路径遍历攻击

    Args:
        file_path: 要验证的文件路径
        base_directory: 基础目录（默认为当前目录）

    Returns:
        路径安全检查结果字符串
    """
    from src.tools.common import validate_path_security as validate_path_security_core
    return validate_path_security_core(file_path, base_directory)

@tool
def calculate(expression: str) -> str:
    """
    计算数学表达式

    Args:
        expression: 数学表达式，如 "2 + 3 * 4"

    Returns:
        计算结果
    """
    try:
        # 注意：在实际应用中，应该使用更安全的eval替代方案
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {str(e)}"


@tool
def get_weather(city: str) -> str:
    """
    获取城市天气（模拟）

    Args:
        city: 城市名称

    Returns:
        天气信息
    """
    return f"{city}的天气是晴朗，温度25°C。"


# 对话历史工具
@tool
def save_conversation(conversation_data: str, log_file: Optional[str] = None) -> str:
    """
    保存对话历史到日志文件

    Args:
        conversation_data: 对话数据（JSON格式的字符串）
        log_file: 日志文件路径（可选，默认为 conversation_history.jsonl）

    Returns:
        操作结果字符串
    """
    try:
        import json
        conversation = json.loads(conversation_data)
        return save_conversation_history(conversation, log_file)
    except json.JSONDecodeError:
        return "错误：对话数据格式无效，请提供有效的JSON格式字符串"
    except Exception as e:
        return f"保存对话历史时发生错误：{str(e)}"


@tool
def load_conversation(log_file: Optional[str] = None, limit: int = 10) -> str:
    """
    加载最近的对话历史

    Args:
        log_file: 日志文件路径（可选，默认为 conversation_history.jsonl）
        limit: 加载的条目数量（默认为10）

    Returns:
        对话历史内容字符串
    """
    return load_conversation_history(log_file, limit)


# 工具列表，便于注册到agent中
TOOLS = [
    read_file,
    read_file_info,
    list_files,
    write_to_file,
    search_files,
    search_and_replace,
    codebase_search,
    list_code_definitions,
    execute_command,
    get_system_info,
    check_directory_permissions,
    validate_path_security,
    save_conversation,
    load_conversation
]


# Poc工具列表
POC_AGENT_TOOLS = [
    read_file,
    list_files,
    write_to_file,
    search_files,
]


# 沙箱工具列表
SANDBOX_TOOLS = [
    read_file,
    list_files,
    execute_command,
]

