"""
代码分析工具集
包含: codebase_search, list_code_definitions 等工具
"""

import os
import re
import ast
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


def codebase_search_core(query: str, directory: Optional[str] = None,
                        file_types: Optional[List[str]] = None) -> str:
    """
    在代码库中搜索相关代码

    Args:
        query: 搜索查询
        directory: 搜索目录（默认为当前目录）
        file_types: 文件类型过滤列表

    Returns:
        搜索结果字符串
    """
    try:
        # 处理搜索目录
        if directory is None:
            search_path = Path.cwd()
        else:
            search_path = Path(directory)
            if not search_path.is_absolute():
                search_path = Path.cwd() / search_path

        if not search_path.exists():
            return f"错误: 搜索目录不存在 - {directory}"

        # 默认支持的文件类型
        if file_types is None:
            file_types = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
                         '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala']

        results = []
        files_searched = 0

        # 遍历文件
        for file_path in search_path.rglob('*'):
            if not file_path.is_file():
                continue

            # 文件类型过滤
            if file_path.suffix not in file_types:
                continue

            # 跳过二进制文件
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and (mime_type.startswith('application/') or mime_type.startswith('image/')):
                continue

            files_searched += 1

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 简单的搜索算法 - 可以根据需要改进
                relevance_score = _calculate_relevance(content, query, file_path.name)

                if relevance_score > 0:
                    # 提取相关代码片段
                    code_snippets = _extract_relevant_snippets(content, query, file_path.suffix)

                    relative_path = file_path.relative_to(search_path)
                    results.append({
                        'file': str(relative_path),
                        'score': relevance_score,
                        'snippets': code_snippets
                    })

            except Exception as e:
                # 忽略无法读取的文件
                continue

        # 按相关性排序
        results.sort(key=lambda x: x['score'], reverse=True)

        # 格式化结果
        if not results:
            return f"在代码库中未找到与 '{query}' 相关的代码。\n搜索了 {files_searched} 个代码文件。"

        result = f"代码库搜索结果 - 查询: {query}\n"
        result += f"搜索目录: {search_path}\n"
        result += f"搜索文件数: {files_searched}\n"
        result += f"匹配文件数: {len(results)}\n"
        result += "=" * 50 + "\n\n"

        for i, file_result in enumerate(results[:20]):  # 限制显示前20个结果
            result += f"{i+1}. 📄 {file_result['file']} (相关性: {file_result['score']:.2f})\n"

            for snippet in file_result['snippets'][:3]:  # 每个文件最多显示3个代码片段
                result += f"   行 {snippet['start']}-{snippet['end']}:\n"
                result += f"   ```{file_result['file'].split('.')[-1]}\n"
                for line in snippet['code']:
                    result += f"   {line}\n"
                result += "   ```\n\n"

        if len(results) > 20:
            result += f"... 还有 {len(results) - 20} 个结果未显示\n"

        return result

    except Exception as e:
        logger.error(f"代码库搜索时出错: {str(e)}")
        return f"错误: 代码库搜索失败 - {str(e)}"


def list_code_definitions_core(file_path: str) -> str:
    """
    列出文件中的代码定义（函数、类、变量等）

    Args:
        file_path: 文件路径

    Returns:
        代码定义列表字符串
    """
    try:
        # 处理路径
        path = Path(file_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            return f"错误: 文件不存在 - {file_path}"

        if not path.is_file():
            return f"错误: 路径不是文件 - {file_path}"

        # 根据文件扩展名选择解析器
        suffix = path.suffix.lower()

        if suffix == '.py':
            return _parse_python_definitions(path)
        elif suffix in ['.js', '.jsx', '.ts', '.tsx']:
            return _parse_javascript_definitions(path)
        elif suffix in ['.java']:
            return _parse_java_definitions(path)
        elif suffix in ['.cpp', '.c', '.h']:
            return _parse_cpp_definitions(path)
        else:
            return f"暂不支持解析 {suffix} 文件的代码定义"

    except Exception as e:
        logger.error(f"解析代码定义时出错: {str(e)}")
        return f"错误: 解析代码定义失败 - {str(e)}"


def _calculate_relevance(content: str, query: str, filename: str) -> float:
    """
    计算文件内容与查询的相关性分数
    """
    score = 0.0
    query_lower = query.lower()
    content_lower = content.lower()
    filename_lower = filename.lower()

    # 文件名匹配
    if query_lower in filename_lower:
        score += 2.0

    # 完整单词匹配
    words = query_lower.split()
    for word in words:
        # 在内容中的匹配次数
        matches = content_lower.count(word)
        score += matches * 0.5

        # 在函数/类名中的匹配
        # 简单的启发式方法
        if any(word in line.lower() for line in content.split('\n')
               if any(keyword in line for keyword in ['def ', 'class ', 'function ', 'const ', 'let ', 'var '])):
            score += 1.0

    # 考虑文件大小（避免太小的文件获得高分）
    if len(content) < 100:
        score *= 0.5
    elif len(content) > 50000:
        score *= 0.8

    return score


def _extract_relevant_snippets(content: str, query: str, file_type: str) -> List[Dict]:
    """
    提取相关的代码片段
    """
    lines = content.split('\n')
    query_lower = query.lower()
    snippets = []

    for i, line in enumerate(lines):
        if query_lower in line.lower():
            # 提取上下文（前后几行）
            start = max(0, i - 3)
            end = min(len(lines), i + 4)
            snippet_lines = lines[start:end]

            snippets.append({
                'start': start + 1,  # 转换为1基索引
                'end': end,
                'code': snippet_lines
            })

            # 限制片段数量
            if len(snippets) >= 5:
                break

    return snippets


def _parse_python_definitions(path: Path) -> str:
    """解析Python文件的代码定义"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        definitions = {
            'classes': [],
            'functions': [],
            'variables': [],
            'imports': []
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                definitions['classes'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
            elif isinstance(node, ast.FunctionDef):
                # 检查是否是类的方法
                is_method = False
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        line_numbers = [n.lineno for n in ast.walk(parent) if hasattr(n, 'lineno')]
                        if line_numbers and any(parent.lineno <= node.lineno <= max(line_numbers)):
                            is_method = True
                            break

                if not is_method:
                    definitions['functions'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args]
                    })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    definitions['imports'].append({
                        'name': alias.name,
                        'line': node.lineno,
                        'alias': alias.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    definitions['imports'].append({
                        'name': f"{module}.{alias.name}",
                        'line': node.lineno,
                        'alias': alias.asname
                    })

        # 查找全局变量（简单启发式）
        lines = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (re.match(r'^[A-Z_][A-Z0-9_]*\s*=', stripped) or
                re.match(r'^[a-z_][a-z0-9_]*\s*=', stripped)):
                # 排除函数和类定义行
                if not (stripped.startswith('def ') or stripped.startswith('class ')):
                    definitions['variables'].append({
                        'name': stripped.split('=')[0].strip(),
                        'line': i + 1
                    })

        return _format_definitions(path.name, definitions)

    except SyntaxError as e:
        return f"错误: Python语法错误 - {str(e)}"
    except Exception as e:
        return f"错误: 解析Python文件失败 - {str(e)}"


def _parse_javascript_definitions(path: Path) -> str:
    """解析JavaScript/TypeScript文件的代码定义"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        definitions = {
            'classes': [],
            'functions': [],
            'variables': [],
            'imports': []
        }

        lines = content.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 类定义
            if re.match(r'^(class|export\s+class)\s+\w+', stripped):
                class_name = re.search(r'(class|export\s+class)\s+(\w+)', stripped)
                if class_name:
                    definitions['classes'].append({
                        'name': class_name.group(2),
                        'line': i + 1
                    })

            # 函数定义
            elif re.match(r'^(function|export\s+function|const|let|var)\s+\w+\s*=', stripped):
                func_match = re.search(r'(function|export\s+function|(?:const|let|var))\s+(\w+)', stripped)
                if func_match:
                    definitions['functions'].append({
                        'name': func_match.group(2),
                        'line': i + 1
                    })

            # 箭头函数
            elif re.match(r'^\w+\s*=\s*\([^)]*\)\s*=>', stripped):
                func_name = stripped.split('=')[0].strip()
                definitions['functions'].append({
                    'name': func_name,
                    'line': i + 1
                })

            # 导入语句
            elif stripped.startswith('import ') or stripped.startswith('const ') and 'require' in stripped:
                if 'from' in stripped or 'require' in stripped:
                    definitions['imports'].append({
                        'name': stripped,
                        'line': i + 1
                    })

            # 变量定义
            elif re.match(r'^(const|let|var)\s+\w+', stripped) and '=' in stripped:
                var_name = stripped.split('=')[0].strip()
                if not any(keyword in var_name for keyword in ['import', 'function']):
                    definitions['variables'].append({
                        'name': var_name.replace('const ', '').replace('let ', '').replace('var ', '').strip(),
                        'line': i + 1
                    })

        return _format_definitions(path.name, definitions)

    except Exception as e:
        return f"错误: 解析JavaScript/TypeScript文件失败 - {str(e)}"


def _parse_java_definitions(path: Path) -> str:
    """解析Java文件的代码定义"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        definitions = {
            'classes': [],
            'functions': [],
            'variables': [],
            'imports': []
        }

        lines = content.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 类定义
            if re.match(r'^(public\s+|private\s+|protected\s+)?(class|interface|enum)\s+\w+', stripped):
                class_match = re.search(r'(class|interface|enum)\s+(\w+)', stripped)
                if class_match:
                    definitions['classes'].append({
                        'name': class_match.group(2),
                        'line': i + 1
                    })

            # 方法定义
            if re.match(r'^(public\s+|private\s+|protected\s+|static\s+)*(\w+)\s+\w+\s*\([^)]*\)', stripped):
                if not any(keyword in stripped for keyword in ['class', 'interface', 'enum']):
                    method_match = re.search(r'\s+(\w+)\s*\(', stripped)
                    if method_match:
                        definitions['functions'].append({
                            'name': method_match.group(1),
                            'line': i + 1
                        })

            # 导入语句
            if stripped.startswith('import '):
                definitions['imports'].append({
                    'name': stripped,
                    'line': i + 1
                })

        return _format_definitions(path.name, definitions)

    except Exception as e:
        return f"错误: 解析Java文件失败 - {str(e)}"


def _parse_cpp_definitions(path: Path) -> str:
    """解析C/C++文件的代码定义"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        definitions = {
            'classes': [],
            'functions': [],
            'variables': [],
            'includes': []
        }

        lines = content.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 类/结构体定义
            if re.match(r'^(class|struct)\s+\w+', stripped):
                class_match = re.search(r'(class|struct)\s+(\w+)', stripped)
                if class_match:
                    definitions['classes'].append({
                        'name': class_match.group(2),
                        'line': i + 1
                    })

            # 函数定义
            if re.match(r'^[\w\s\*]+\s+\w+\s*\([^)]*\)', stripped):
                if not any(keyword in stripped for keyword in ['class', 'struct', '#include']):
                    func_match = re.search(r'\s+(\w+)\s*\(', stripped)
                    if func_match and func_match.group(1) not in ['if', 'while', 'for', 'switch']:
                        definitions['functions'].append({
                            'name': func_match.group(1),
                            'line': i + 1
                        })

            # 包含语句
            if stripped.startswith('#include'):
                definitions['includes'].append({
                    'name': stripped,
                    'line': i + 1
                })

        return _format_definitions(path.name, definitions)

    except Exception as e:
        return f"错误: 解析C/C++文件失败 - {str(e)}"


def _format_definitions(filename: str, definitions: Dict) -> str:
    """格式化代码定义输出"""
    result = f"📄 {filename} 代码定义\n"
    result += "=" * 50 + "\n\n"

    if definitions.get('imports'):
        result += "📥 导入/包含:\n"
        for item in definitions['imports']:
            name = item.get('name', '')
            alias = item.get('alias', '')
            line = item['line']
            if alias:
                result += f"  {line:>4}: {name} as {alias}\n"
            else:
                result += f"  {line:>4}: {name}\n"
        result += "\n"

    if definitions.get('classes'):
        result += "🏗️  类/接口/结构体:\n"
        for item in definitions['classes']:
            name = item['name']
            line = item['line']
            methods = item.get('methods', [])
            result += f"  {line:>4}: {name}\n"
            if methods:
                for method in methods[:5]:  # 限制显示前5个方法
                    result += f"       - {method}()\n"
                if len(methods) > 5:
                    result += f"       ... 还有 {len(methods) - 5} 个方法\n"
        result += "\n"

    if definitions.get('functions'):
        result += "⚡ 函数:\n"
        for item in definitions['functions']:
            name = item['name']
            line = item['line']
            args = item.get('args', [])
            if args:
                args_str = ', '.join(args[:3])  # 限制显示前3个参数
                if len(args) > 3:
                    args_str += f', ... ({len(args)-3} more)'
                result += f"  {line:>4}: {name}({args_str})\n"
            else:
                result += f"  {line:>4}: {name}()\n"
        result += "\n"

    if definitions.get('variables'):
        result += "📦 变量:\n"
        for item in definitions['variables']:
            name = item['name']
            line = item['line']
            result += f"  {line:>4}: {name}\n"
        result += "\n"

    if not any(definitions.values()):
        result += "未找到代码定义\n"

    return result