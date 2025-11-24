# Python 工具集

这是从 TypeScript Roo-Code 项目重构而来的 Python 工具集，提供了丰富的文件操作、代码分析和系统操作功能。

## 工具分类

### 📁 文件系统工具 (`file_system_tools.py`)

| 工具函数 | 功能描述 | 主要参数 |
|---------|---------|---------|
| `list_files_core()` | 列出目录文件和子目录 | `directory`, `recursive`, `max_files` |
| `write_to_file_core()` | 写入内容到文件 | `file_path`, `content`, `create_dirs` |
| `search_files_core()` | 在文件中搜索内容 | `directory`, `pattern`, `file_pattern` |
| `search_and_replace_core()` | 搜索并替换文件内容 | `file_path`, `search`, `replace` |

### 🔍 代码分析工具 (`code_analysis_tools.py`)

| 工具函数 | 功能描述 | 主要参数 |
|---------|---------|---------|
| `codebase_search_core()` | 在代码库中搜索相关代码 | `query`, `directory`, `file_types` |
| `list_code_definitions_core()` | 列出文件中的代码定义 | `file_path` |

### 🖥️ 系统工具 (`system_tools.py`)

| 工具函数 | 功能描述 | 主要参数 |
|---------|---------|---------|
| `execute_command_core()` | 执行系统命令 | `command`, `cwd`, `timeout` |
| `get_system_info()` | 获取系统信息 | 无 |
| `check_directory_permissions()` | 检查目录权限 | `directory` |
| `validate_path_security()` | 验证路径安全性 | `file_path`, `base_directory` |

### 📄 文件操作工具 (`file_tools.py`)

| 工具函数 | 功能描述 | 主要参数 |
|---------|---------|---------|
| `read_file_core()` | 读取文件内容 | `file_path`, `start_line`, `end_line` |
| `read_file_info_core()` | 获取文件基本信息 | `file_path` |

## 使用方式

### 1. 直接使用核心函数

```python
from src.tools.common import (
    read_file_core,
    list_files_core,
    write_to_file_core,
    codebase_search_core,
    execute_command_core
)

# 读取文件
content = read_file_core("example.py", start_line=1, end_line=20)

# 列出目录文件
files = list_files_core("./src", recursive=True)

# 写入文件
result = write_to_file_core("new_file.txt", "Hello World!")

# 搜索代码库
search_result = codebase_search_core("function", directory="./src")

# 执行命令
cmd_result = execute_command_core("ls -la")
```

### 2. 使用 Langchain 工具版本

```python
from src.tools.sandbox_tools import (
    read_file,
    list_files,
    write_to_file,
    codebase_search,
    execute_command
)

# 这些工具已经用 @tool 装饰器包装
# 可以直接注册到 Langchain Agent 中使用

# 示例：在 Agent 中使用
tools = [read_file, list_files, write_to_file, codebase_search, execute_command]
```

## 功能特性

### 🔒 安全特性
- **路径验证**: 防止路径遍历攻击
- **命令过滤**: 检测并阻止危险系统命令
- **权限检查**: 自动验证文件和目录访问权限
- **编码处理**: 自动处理不同文件编码

### 📊 智能分析
- **代码解析**: 支持 Python、JavaScript、Java、C/C++ 等多种语言
- **相关性评分**: 智能计算搜索结果相关性
- **上下文提取**: 提取代码片段的上下文信息
- **结构化输出**: 格式化显示分析结果

### ⚡ 性能优化
- **输出限制**: 防止输出过大造成性能问题
- **超时控制**: 命令执行超时保护
- **缓存机制**: 减少重复操作
- **资源管理**: 自动清理临时资源

## 示例用法

### 示例 1: 代码库分析

```python
# 搜索特定函数在代码库中的使用情况
result = codebase_search_core(
    query="read_file",
    directory="./src",
    file_types=['.py']
)
print(result)
```

### 示例 2: 批量文件操作

```python
# 列出所有 Python 文件
files = list_files_core(".", recursive=True)
for file_info in files.split('\n'):
    if file_info.endswith('.py)'):
        filename = file_info.split('(')[0].strip()
        print(f"分析文件: {filename}")
        definitions = list_code_definitions_core(filename)
        print(definitions)
```

### 示例 3: 安全的文件搜索和替换

```python
# 首先验证路径安全性
security_check = validate_path_security("config/settings.py")
if "安全" in security_check:
    # 执行搜索替换
    result = search_and_replace_core(
        file_path="config/settings.py",
        search="DEBUG = False",
        replace="DEBUG = True",
        case_sensitive=True
    )
    print(result)
```

## 测试

运行测试脚本验证所有工具功能：

```bash
python test_all_tools.py
```

## 依赖要求

- Python 3.7+
- 标准库模块：`pathlib`, `re`, `ast`, `mimetypes`, `subprocess`, `logging`
- 可选依赖：`psutil` (用于系统信息获取)
- Langchain (如果使用装饰器版本)：`langchain`

## 注意事项

1. **安全第一**: 在使用 `execute_command_core` 时要谨慎，避免执行危险命令
2. **权限检查**: 所有文件操作都会自动检查权限
3. **编码处理**: 工具会自动尝试多种编码方式读取文件
4. **错误处理**: 所有工具都包含完善的错误处理机制

## 扩展开发

如需添加新工具：

1. 在相应模块中添加核心函数
2. 在 `__init__.py` 中导出
3. 在 `langchain_tools.py` 中添加装饰器版本
4. 更新测试文件和文档

遵循现有的命名规范和错误处理模式。