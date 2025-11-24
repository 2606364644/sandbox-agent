"""
文件系统操作工具集
包含:list_files, write_to_file 等工具
"""

import os
import re
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def list_files_core(directory: str, recursive: bool = False, max_files: int = 200) -> str:
    """
    列出目录中的文件和子目录

    Args:
        directory: 目录路径（相对于当前工作目录或绝对路径）
        recursive: 是否递归搜索子目录
        max_files: 最大文件数量限制

    Returns:
        格式化的文件列表字符串
    """
    try:
        # 处理路径
        path = Path(directory)
        if not path.is_absolute():
            path = Path.cwd() / path

        # 检查目录是否存在
        if not path.exists():
            return f"错误: 目录不存在 - {directory}"

        if not path.is_dir():
            return f"错误: 路径不是目录 - {directory}"

        # 收集文件和目录
        files = []
        dirs = []

        if recursive:
            # 递归遍历
            pattern = "**/*"
            try:
                for item in path.glob(pattern):
                    if item.is_file():
                        relative_path = item.relative_to(path)
                        files.append(str(relative_path))
                    elif item.is_dir() and item != path:  # 不包含根目录本身
                        relative_path = item.relative_to(path)
                        dirs.append(str(relative_path))
            except PermissionError as e:
                return f"错误: 没有权限访问目录 - {str(e)}"
        else:
            # 只列出当前目录
            try:
                for item in path.iterdir():
                    if item.is_file():
                        files.append(item.name)
                    elif item.is_dir():
                        dirs.append(item.name)
            except PermissionError as e:
                return f"错误: 没有权限访问目录 - {str(e)}"

        # 排序
        files.sort()
        dirs.sort()

        # 检查是否达到限制
        total_items = len(files) + len(dirs)
        if total_items > max_files:
            files = files[:max_files]
            dirs = dirs[:max_files - len(files)]

        # 格式化输出
        result = f"目录: {path}\n"
        result += f"总计: {total_items} 个项目"
        if total_items > max_files:
            result += f" (显示前 {max_files} 个)"
        result += "\n"
        result += "=" * 50 + "\n"

        if dirs:
            result += "📁 目录:\n"
            for dir_name in dirs:
                result += f"  {dir_name}/\n"
            result += "\n"

        if files:
            result += "📄 文件:\n"
            for file_name in files:
                file_path = path / file_name
                try:
                    size = file_path.stat().st_size
                    # 格式化文件大小
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size/1024:.1f}KB"
                    else:
                        size_str = f"{size/(1024*1024):.1f}MB"

                    result += f"  {file_name} ({size_str})\n"
                except:
                    result += f"  {file_name}\n"

        if not dirs and not files:
            result += "目录为空\n"

        return result

    except Exception as e:
        logger.error(f"列出目录内容时出错: {str(e)}")
        return f"错误: 列出目录内容失败 - {str(e)}"


def write_to_file_core(file_path: str, content: str, create_dirs: bool = True) -> str:
    """
    将内容写入文件

    Args:
        file_path: 文件路径（相对于当前工作目录或绝对路径）
        content: 要写入的内容
        create_dirs: 是否自动创建不存在的目录

    Returns:
        操作结果字符串
    """
    try:
        # 处理路径
        path = Path(file_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        # 检查文件是否已存在
        file_exists = path.exists()

        # 检查父目录是否存在
        parent_dir = path.parent
        if not parent_dir.exists():
            if create_dirs:
                parent_dir.mkdir(parents=True, exist_ok=True)
            else:
                return f"错误: 父目录不存在 - {parent_dir}"

        # 检查是否有写入权限
        if file_exists and not os.access(path, os.W_OK):
            return f"错误: 没有写入权限 - {file_path}"

        if not file_exists and not os.access(parent_dir, os.W_OK):
            return f"错误: 没有在目录中创建文件的权限 - {parent_dir}"

        # 预处理内容（移除可能的代码块标记）
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if len(lines) > 1:
                content = "\n".join(lines[1:])
        if content.endswith("```"):
            lines = content.split("\n")
            if len(lines) > 1:
                content = "\n".join(lines[:-1])

        # 写入文件
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 返回结果
        action = "更新" if file_exists else "创建"
        lines_count = len(content.split('\n'))
        file_size = path.stat().st_size

        result = f"✅ 成功{action}文件: {file_path}\n"
        result += f"📊 文件信息:\n"
        result += f"   - 行数: {lines_count}\n"
        result += f"   - 大小: {file_size} 字节\n"

        if file_size < 1024:
            size_str = f"{file_size}B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size/1024:.1f}KB"
        else:
            size_str = f"{file_size/(1024*1024):.1f}MB"
        result += f"   - 格式化大小: {size_str}\n"

        return result

    except PermissionError as e:
        return f"错误: 没有写入权限 - {str(e)}"
    except Exception as e:
        logger.error(f"写入文件时出错: {str(e)}")
        return f"错误: 写入文件失败 - {str(e)}"


def search_files_core(directory: str, pattern: str, file_pattern: Optional[str] = None,
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
    try:
        # 处理路径
        path = Path(directory)
        if not path.is_absolute():
            path = Path.cwd() / path

        # 检查目录是否存在
        if not path.exists():
            return f"错误: 目录不存在 - {directory}"

        if not path.is_dir():
            return f"错误: 路径不是目录 - {directory}"

        # 准备搜索模式
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                search_regex = re.compile(pattern, flags)
            except re.error as e:
                return f"错误: 无效的正则表达式 - {str(e)}"
        else:
            search_term = pattern if case_sensitive else pattern.lower()

        # 准备文件模式过滤
        file_regex = None
        if file_pattern:
            try:
                file_regex = re.compile(file_pattern, re.IGNORECASE)
            except re.error:
                # 如果不是正则表达式，当作通配符处理
                import fnmatch
                file_pattern_simple = file_pattern

        results = []
        files_searched = 0

        # 遍历文件
        for file_path in path.rglob('*'):
            if not file_path.is_file():
                continue

            files_searched += 1

            # 应用文件名过滤
            if file_regex:
                if not file_regex.search(file_path.name):
                    continue
            elif file_pattern:
                try:
                    if not fnmatch.fnmatch(file_path.name.lower(), file_pattern.lower()):
                        continue
                except:
                    if not fnmatch.fnmatch(file_path.name, file_pattern):
                        continue

            # 跳过二进制文件
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and (mime_type.startswith('application/') or mime_type.startswith('image/')):
                continue

            try:
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                matches = []
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    search_content = line if case_sensitive else line.lower()

                    if use_regex:
                        if search_regex.search(line):
                            matches.append((line_num, line.strip()))
                    else:
                        if search_term in search_content:
                            matches.append((line_num, line.strip()))

                if matches:
                    relative_path = file_path.relative_to(path)
                    results.append({
                        'file': str(relative_path),
                        'matches': matches
                    })

            except Exception as e:
                # 忽略无法读取的文件
                continue

        # 格式化结果
        if not results:
            return f"在目录 '{directory}' 中未找到匹配项。\n搜索了 {files_searched} 个文件。"

        result = f"搜索结果 - 目录: {directory}\n"
        result += f"搜索模式: {pattern}\n"
        if file_pattern:
            result += f"文件过滤: {file_pattern}\n"
        result += f"搜索文件数: {files_searched}\n"
        result += f"匹配文件数: {len(results)}\n"
        result += "=" * 50 + "\n\n"

        for file_result in results:
            result += f"📄 {file_result['file']}:\n"
            for line_num, line_content in file_result['matches'][:10]:  # 限制每个文件最多显示10个匹配
                result += f"  {line_num:>4}: {line_content}\n"

            if len(file_result['matches']) > 10:
                result += f"  ... 还有 {len(file_result['matches']) - 10} 个匹配项\n"

            result += "\n"

        return result

    except Exception as e:
        logger.error(f"搜索文件时出错: {str(e)}")
        return f"错误: 搜索文件失败 - {str(e)}"


def search_and_replace_core(file_path: str, search: str, replace: str,
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
    try:
        # 处理路径
        path = Path(file_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        # 检查文件是否存在
        if not path.exists():
            return f"错误: 文件不存在 - {file_path}"

        if not path.is_file():
            return f"错误: 路径不是文件 - {file_path}"

        # 检查读取权限
        if not os.access(path, os.R_OK):
            return f"错误: 没有读取权限 - {file_path}"

        # 检查写入权限
        if not os.access(path, os.W_OK):
            return f"错误: 没有写入权限 - {file_path}"

        # 读取文件内容
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')

        # 准备搜索模式
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                search_regex = re.compile(search, flags)
            except re.error as e:
                return f"错误: 无效的正则表达式 - {str(e)}"
        else:
            search_term = search if case_sensitive else search.lower()

        # 执行替换
        replacement_count = 0

        if start_line is not None or end_line is not None:
            # 行范围替换
            start = max((start_line or 1) - 1, 0)
            end = min((end_line or len(lines)) - 1, len(lines) - 1)

            for i in range(start, end + 1):
                line = lines[i]
                if use_regex:
                    new_line, count = search_regex.subn(replace, line)
                    if count > 0:
                        lines[i] = new_line
                        replacement_count += count
                else:
                    search_content = line if case_sensitive else line.lower()
                    if search_term in search_content:
                        if case_sensitive:
                            lines[i] = line.replace(search, replace)
                            replacement_count += line.count(search)
                        else:
                            # 大小写不敏感的替换比较复杂，需要逐个匹配
                            local_pattern = re.compile(re.escape(search_term), re.IGNORECASE)
                            lines[i] = local_pattern.sub(replace, line)
                            replacement_count += len(local_pattern.findall(line))

            new_content = '\n'.join(lines)
        else:
            # 全文替换
            if use_regex:
                new_content, replacement_count = search_regex.subn(replace, content)
            else:
                if case_sensitive:
                    new_content = content.replace(search, replace)
                    replacement_count = content.count(search)
                else:
                    # 大小写不敏感的替换
                    pattern = re.compile(re.escape(search_term), re.IGNORECASE)
                    new_content = pattern.sub(replace, content)
                    replacement_count += len(pattern.findall(content))

        # 检查是否有变化
        if new_content == original_content:
            return f"文件 '{file_path}' 中没有找到匹配的内容，无需替换。"

        # 写入新内容
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # 生成结果报告
        result = f"✅ 成功替换文件: {file_path}\n"
        result += f"🔄 替换统计:\n"
        result += f"   - 搜索模式: {search}\n"
        result += f"   - 替换内容: {replace}\n"
        result += f"   - 替换次数: {replacement_count}\n"
        result += f"   - 使用正则: {'是' if use_regex else '否'}\n"
        result += f"   - 区分大小写: {'是' if case_sensitive else '否'}\n"

        if start_line is not None or end_line is not None:
            result += f"   - 行范围: {start_line or 1}-{end_line or len(lines)}\n"

        return result

    except Exception as e:
        logger.error(f"搜索替换时出错: {str(e)}")
        return f"错误: 搜索替换失败 - {str(e)}"