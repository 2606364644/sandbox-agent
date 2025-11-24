from langchain.tools import tool
from tools.langchain_tools import (
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
    validate_path_security
)


@tool
def search(query: str) -> str:
    """A simple search tool placeholder."""
    return f"Search results for '{query}'"


@tool
def get_weather(location: str) -> str:
    """Get weather information for a location."""
    return f"Weather in {location}: Sunny, 72°F"


@tool
def get_file_info(file_path: str) -> str:
    """
    获取文件基本信息

    Args:
        file_path: 文件路径

    Returns:
        文件信息
    """
    return read_file_info(file_path)


@tool
def search_in_files(directory: str, pattern: str, file_pattern: str = None) -> str:
    """
    在文件中搜索内容

    Args:
        directory: 搜索目录
        pattern: 搜索模式
        file_pattern: 文件模式过滤

    Returns:
        搜索结果
    """
    return search_files(directory, pattern, file_pattern)


@tool
def get_system_information() -> str:
    """
    获取系统信息

    Returns:
        系统信息
    """
    return get_system_info()


@tool
def check_permissions(directory: str) -> str:
    """
    检查目录权限

    Args:
        directory: 目录路径

    Returns:
        权限检查结果
    """
    return check_directory_permissions(directory)


@tool
def validate_security(file_path: str, base_directory: str = None) -> str:
    """
    验证路径安全性

    Args:
        file_path: 要验证的文件路径
        base_directory: 基础目录

    Returns:
        安全验证结果
    """
    return validate_path_security(file_path, base_directory)


# 导出所有工具以便使用
__all__ = [
    'search',
    'get_weather',
    'read_file',
    'get_file_info',
    'list_files',
    'search_in_files',
    'search_and_replace',
    'codebase_search',
    'list_code_definitions',
    'execute_command',
    'get_system_information',
    'check_permissions',
    'validate_security'
]
