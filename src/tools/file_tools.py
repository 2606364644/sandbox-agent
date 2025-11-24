"""
文件操作工具模块
"""
import os
import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from src.tools.base_tools import BaseCustomTool, register_tool
import logging

logger = logging.getLogger(__name__)


class ReadFileInput(BaseModel):
    """读取文件输入模型"""
    file_path: str = Field(description="要读取的文件路径")
    encoding: str = Field(default="utf-8", description="文件编码格式")


class WriteFileInput(BaseModel):
    """写入文件输入模型"""
    file_path: str = Field(description="要写入的文件路径")
    content: str = Field(description="要写入的内容")
    encoding: str = Field(default="utf-8", description="文件编码格式")
    mode: str = Field(default="w", description="写入模式")


class ListDirectoryInput(BaseModel):
    """列出目录内容输入模型"""
    directory_path: str = Field(description="目录路径")
    show_hidden: bool = Field(default=False, description="是否显示隐藏文件")


class SearchFilesInput(BaseModel):
    """搜索文件输入模型"""
    directory_path: str = Field(description="搜索目录路径")
    pattern: str = Field(description="搜索模式（支持通配符）")
    recursive: bool = Field(default=True, description="是否递归搜索")


class ReadFileTool(BaseCustomTool):
    """文件读取工具"""

    name: str = "read_file"
    description: str = "读取指定文件的内容"
    args_schema = ReadFileInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(self, file_path: str, encoding: str = "utf-8") -> str:
        """执行文件读取"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"错误：文件 {file_path} 不存在"

            if not path.is_file():
                return f"错误：{file_path} 不是一个文件"

            # 检查文件大小，避免读取过大的文件
            if path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                return f"错误：文件 {file_path} 过大（超过10MB）"

            with open(path, 'r', encoding=encoding) as f:
                content = f.read()

            return f"文件 {file_path} 内容：\n\n{content}"

        except UnicodeDecodeError:
            return f"错误：无法使用编码 {encoding} 读取文件 {file_path}"
        except PermissionError:
            return f"错误：没有权限读取文件 {file_path}"
        except Exception as e:
            return f"读取文件时发生错误：{str(e)}"


class WriteFileTool(BaseCustomTool):
    """文件写入工具"""

    name: str = "write_file"
    description: str = "将内容写入指定文件"
    args_schema = WriteFileInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(self, file_path: str, content: str, encoding: str = "utf-8", mode: str = "w") -> str:
        """执行文件写入"""
        try:
            path = Path(file_path)

            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, mode, encoding=encoding) as f:
                f.write(content)

            return f"成功将内容写入文件 {file_path}"

        except PermissionError:
            return f"错误：没有权限写入文件 {file_path}"
        except Exception as e:
            return f"写入文件时发生错误：{str(e)}"


class ListDirectoryTool(BaseCustomTool):
    """目录列表工具"""

    name: str = "list_directory"
    description: str = "列出指定目录的内容"
    args_schema = ListDirectoryInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(self, directory_path: str, show_hidden: bool = False) -> str:
        """执行目录列表"""
        try:
            path = Path(directory_path)
            if not path.exists():
                return f"错误：目录 {directory_path} 不存在"

            if not path.is_dir():
                return f"错误：{directory_path} 不是一个目录"

            items = []
            for item in path.iterdir():
                if not show_hidden and item.name.startswith('.'):
                    continue

                item_type = "目录" if item.is_dir() else "文件"
                items.append(f"  {item_type}: {item.name}")

            if not items:
                return f"目录 {directory_path} 为空"

            result = f"目录 {directory_path} 的内容：\n\n" + "\n".join(items)
            return result

        except PermissionError:
            return f"错误：没有权限访问目录 {directory_path}"
        except Exception as e:
            return f"列出目录时发生错误：{str(e)}"


class SearchFilesTool(BaseCustomTool):
    """文件搜索工具"""

    name: str = "search_files"
    description: str = "在指定目录中搜索匹配模式的文件"
    args_schema = SearchFilesInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(self, directory_path: str, pattern: str, recursive: bool = True) -> str:
        """执行文件搜索"""
        try:
            path = Path(directory_path)
            if not path.exists():
                return f"错误：目录 {directory_path} 不存在"

            if not path.is_dir():
                return f"错误：{directory_path} 不是一个目录"

            if recursive:
                files = list(path.rglob(pattern))
            else:
                files = list(path.glob(pattern))

            if not files:
                return f"在目录 {directory_path} 中未找到匹配模式 '{pattern}' 的文件"

            result = f"在目录 {directory_path} 中找到 {len(files)} 个匹配文件：\n\n"
            for file in files:
                file_type = "目录" if file.is_dir() else "文件"
                relative_path = file.relative_to(path)
                result += f"  {file_type}: {relative_path}\n"

            return result

        except PermissionError:
            return f"错误：没有权限搜索目录 {directory_path}"
        except Exception as e:
            return f"搜索文件时发生错误：{str(e)}"


class JsonFileTool(BaseCustomTool):
    """JSON文件操作工具"""

    name: str = "json_file_operations"
    description: str = "读取或写入JSON文件"

    class JsonFileInput(BaseModel):
        operation: str = Field(description="操作类型：'read' 或 'write'")
        file_path: str = Field(description="JSON文件路径")
        data: Optional[str] = Field(default=None, description="要写入的JSON数据（字符串格式）")

    args_schema = JsonFileInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(self, operation: str, file_path: str, data: Optional[str] = None) -> str:
        """执行JSON文件操作"""
        try:
            path = Path(file_path)

            if operation == "read":
                if not path.exists():
                    return f"错误：文件 {file_path} 不存在"

                with open(path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                return f"JSON文件内容：\n{json.dumps(json_data, ensure_ascii=False, indent=2)}"

            elif operation == "write":
                if data is None:
                    return "错误：写入操作需要提供data参数"

                json_data = json.loads(data)
                path.parent.mkdir(parents=True, exist_ok=True)

                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)

                return f"成功将数据写入JSON文件 {file_path}"

            else:
                return f"错误：不支持的操作类型 '{operation}'"

        except json.JSONDecodeError as e:
            return f"JSON格式错误：{str(e)}"
        except Exception as e:
            return f"JSON文件操作时发生错误：{str(e)}"


# 注册所有文件工具
register_tool(ReadFileTool(), category="file")
register_tool(WriteFileTool(), category="file")
register_tool(ListDirectoryTool(), category="file")
register_tool(SearchFilesTool(), category="file")
register_tool(JsonFileTool(), category="file")