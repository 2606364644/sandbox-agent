import os
import mimetypes
from pathlib import Path
from typing import Optional, Union, Dict, Any
import logging

logger = logging.getLogger(__name__)


def read_file_core(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """
    读取文件内容的核心函数

    Args:
        file_path: 文件路径（相对于当前工作目录或绝对路径）
        start_line: 起始行号（可选，从1开始）
        end_line: 结束行号（可选）

    Returns:
        文件内容字符串，包含行号

    Raises:
        FileNotFoundError: 文件不存在
        PermissionError: 没有读取权限
        ValueError: 行号参数无效
        UnicodeDecodeError: 文件编码问题
    """
    try:
        # 处理路径
        path = Path(file_path)
        if not path.is_absolute():
            # 如果是相对路径，相对于当前工作目录
            path = Path.cwd() / path

        # 检查文件是否存在
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检查是否为文件
        if not path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")

        # 检查文件权限
        if not os.access(path, os.R_OK):
            raise PermissionError(f"没有读取权限: {file_path}")

        # 检测文件类型
        mime_type, _ = mimetypes.guess_type(str(path))
        is_binary = mime_type and mime_type.startswith('application/') or mime_type and mime_type.startswith('image/')

        if is_binary:
            return f"二进制文件: {file_path} (类型: {mime_type})，内容不显示"

        # 验证行号参数
        if start_line is not None and start_line < 1:
            raise ValueError("起始行号必须大于0")

        if end_line is not None and end_line < 1:
            raise ValueError("结束行号必须大于0")

        if start_line is not None and end_line is not None and start_line > end_line:
            raise ValueError("起始行号不能大于结束行号")

        # 读取文件内容
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(path, 'r', encoding='gbk') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                try:
                    with open(path, 'r', encoding='latin-1') as f:
                        lines = f.readlines()
                except Exception as e:
                    return f"无法解码文件 {file_path}: {str(e)}"

        total_lines = len(lines)

        # 处理行范围
        if start_line is None and end_line is None:
            # 读取全部内容
            content_lines = lines
            line_start = 1
            line_end = total_lines
        else:
            # 读取指定行范围
            start = start_line - 1 if start_line is not None else 0  # 转换为0基索引
            end = end_line if end_line is not None else total_lines

            # 确保不超出文件范围
            start = max(0, start)
            end = min(total_lines, end)

            content_lines = lines[start:end]
            line_start = start + 1
            line_end = end

        # 添加行号并格式化输出
        if not content_lines:
            result = f"文件 {file_path} 为空"
        else:
            formatted_lines = []
            for i, line in enumerate(content_lines, start=line_start):
                formatted_lines.append(f"{i:>4}\t{line.rstrip()}")

            result = "\n".join(formatted_lines)

            # 添加文件信息头部
            header = f"文件: {file_path}"
            if start_line is not None or end_line is not None:
                header += f" (行 {line_start}-{line_end}, 共 {total_lines} 行)"
            else:
                header += f" (共 {total_lines} 行)"

            result = f"{header}\n{'=' * 50}\n{result}"

        return result

    except Exception as e:
        logger.error(f"读取文件 {file_path} 时出错: {str(e)}")
        return f"读取文件失败: {str(e)}"


def read_file_info_core(file_path: str) -> Dict[str, Any]:
    """
    获取文件基本信息的核心函数

    Args:
        file_path: 文件路径

    Returns:
        包含文件信息的字典
    """
    try:
        path = Path(file_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            return {"error": f"文件不存在: {file_path}"}

        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))

        return {
            "path": str(path),
            "name": path.name,
            "size": stat.st_size,
            "modified_time": stat.st_mtime,
            "mime_type": mime_type,
            "is_file": path.is_file(),
            "is_binary": mime_type and (mime_type.startswith('application/') or mime_type.startswith('image/'))
        }

    except Exception as e:
        logger.error(f"获取文件信息 {file_path} 时出错: {str(e)}")
        return {"error": f"获取文件信息失败: {str(e)}"}


# Langchain 工具版本在 sandbox_tools.py 中定义
