# 自动打包智能体 (AutoPackAgent) 使用指南

## 概述

AutoPackAgent 是一个智能的自动打包/编译工具，能够自动将微服务代码仓库打包成Docker容器。它支持多种编程语言和框架，具有智能重试机制和错误分析能力。

## 主要特性

### 1. 智能项目检测
- 自动检测项目类型（Python、Node.js、Java、Go、Rust等）
- 识别构建脚本和配置文件
- 分析项目依赖关系

### 2. Docker支持
- 自动生成Dockerfile（如果不存在）
- 支持多种项目类型的Docker模板
- 灵活的构建参数配置

### 3. 构建脚本集成
- 自动执行预构建脚本
- 支持Shell、Python、NPM、Maven等多种构建工具
- 智能识别和利用现有的构建流程

### 4. 智能重试机制
- 基于LangGraph的智能工作流
- LLM驱动的错误分析和解决方案生成
- 自适应重试策略，最多5次重试

### 5. 详细日志和报告
- 完整的打包过程记录
- 错误分析和修复建议
- 性能指标统计

## 安装依赖

```bash
# 安装Docker Python SDK
pip install docker langchain langchain-openai langgraph

# 确保Docker服务正在运行
# Windows: 启动Docker Desktop
# Linux: sudo systemctl start docker
# macOS: 启动Docker Desktop
```

## 基础使用

### 1. 简单打包

```python
import asyncio
from src.agents.autopack_agent import AutoPackAgent
from src.models.pack_models import PackRequest

async def basic_pack_example():
    # 创建打包请求
    pack_request = PackRequest(
        repo_path="/path/to/your/microservice",
        docker_image_name="my-service",
        docker_tag="v1.0.0",
        environment="production"
    )

    # 创建智能体并执行打包
    agent = AutoPackAgent()
    result = await agent.pack(pack_request)

    # 检查结果
    if result.success:
        print(f"打包成功! 镜像: {result.image_name}")
        print(f"执行时间: {result.execution_time:.2f}秒")
    else:
        print(f"打包失败: {result.error_message}")
        print(f"重试次数: {result.retry_count}")

asyncio.run(basic_pack_example())
```

### 2. 使用智能工作流

```python
import asyncio
from src.core.pack_workflow import PackWorkflow
from src.models.pack_models import PackRequest

async def workflow_pack_example():
    # 创建智能工作流
    workflow = PackWorkflow(max_retries=3)

    # 创建打包请求
    pack_request = PackRequest(
        repo_path="/path/to/your/microservice",
        docker_image_name="my-smart-service",
        docker_tag="latest",
        environment="staging",
        build_args={
            "HTTP_PROXY": "http://proxy:8080",
            "HTTPS_PROXY": "http://proxy:8080"
        }
    )

    # 执行智能打包
    result = await workflow.run(pack_request)

    print(f"工作流结果: {'成功' if result['success'] else '失败'}")
    print(f"重试次数: {result['retry_count']}")
    print(f"检测到的构建脚本: {len(result['build_scripts_found'])}")

    if result['pack_result']:
        pack_result = result['pack_result']
        print(f"镜像ID: {pack_result.image_id}")

asyncio.run(workflow_pack_example())
```

## 支持的项目类型

### 1. Python项目
- 检测文件: `requirements.txt`, `setup.py`, `pyproject.toml`, `Pipfile`
- 自动生成Flask/FastAPI等Web应用的Dockerfile
- 支持Gunicorn和uWSGI配置

### 2. Node.js项目
- 检测文件: `package.json`, `Gruntfile.js`, `Gulpfile.js`, `webpack.config.js`
- 支持Express、Koa等框架
- 自动处理npm/yarn依赖安装

### 3. Java项目
- 检测文件: `pom.xml`, `build.gradle`, `build.gradle.kts`
- 支持Maven和Gradle构建
- 多阶段构建优化

### 4. Go项目
- 检测文件: `go.mod`, `go.sum`
- 静态编译优化
- 最小化运行时镜像

### 5. Rust项目
- 检测文件: `Cargo.toml`, `Cargo.lock`
- 发布版本优化
- 最小化的Alpine镜像

## 高级配置

### 1. 自定义构建参数

```python
pack_request = PackRequest(
    repo_path="/path/to/project",
    docker_image_name="custom-service",
    build_args={
        "NODE_ENV": "production",
        "HTTP_PROXY": "http://proxy:8080",
        "CUSTOM_ARG": "custom_value"
    },
    build_context="./src",  # 自定义构建上下文
    dockerfile_path="Dockerfile.custom"  # 自定义Dockerfile路径
)
```

### 2. 构建脚本配置

AutoPackAgent会自动检测并执行以下构建脚本：

- Shell脚本: `build.sh`, `build`, `Makefile`
- Python脚本: `setup.py`, `requirements.txt`
- Node.js脚本: `package.json` (npm scripts)
- Java脚本: `pom.xml` (Maven), `build.gradle` (Gradle)

### 3. 环境配置

```python
# 开发环境
pack_request = PackRequest(
    repo_path="/path/to/project",
    environment="development",
    docker_tag="dev"
)

# 生产环境
pack_request = PackRequest(
    repo_path="/path/to/project",
    environment="production",
    docker_tag="prod",
    build_args={
        "NODE_ENV": "production",
        "DEBUG": "false"
    }
)
```

## 错误处理和重试

### 1. 智能错误分析

智能工作流使用LLM分析构建错误，提供针对性的解决方案：

```python
workflow = PackWorkflow(max_retries=5)

result = await workflow.run(pack_request)

# 查看错误分析
if not result['success'] and 'error_history' in result:
    print("错误历史:")
    for error in result['error_history']:
        print(f"- {error}")
```

### 2. 常见错误类型

- **依赖问题**: 缺少依赖包或版本冲突
- **配置错误**: Docker配置或环境变量错误
- **权限问题**: 文件权限或用户权限错误
- **网络问题**: 依赖下载或网络连接问题
- **空间问题**: 磁盘空间或内存不足

### 3. 重试策略

- 指数退避: 每次重试间隔递增
- 智能调整: 基于错误类型调整构建策略
- 最大重试: 默认5次，可配置

## 最佳实践

### 1. 项目结构

```
my-microservice/
├── src/
│   └── main.py
├── requirements.txt
├── Dockerfile          # 可选，会自动生成
├── build.sh           # 可选，自定义构建脚本
└── README.md
```

### 2. Dockerfile最佳实践

如果项目没有Dockerfile，AutoPackAgent会自动生成。建议遵循以下最佳实践：

```dockerfile
# 使用具体版本标签
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 使用非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
CMD ["python", "src/main.py"]
```

### 3. 性能优化

- 使用`.dockerignore`减少构建上下文
- 多阶段构建减少镜像大小
- 合理使用缓存层
- 选择合适的基础镜像

## 监控和日志

### 1. 打包结果分析

```python
result = await agent.pack(pack_request)

print(f"成功: {result.success}")
print(f"镜像: {result.image_name}")
print(f"镜像ID: {result.image_id}")
print(f"执行时间: {result.execution_time:.2f}秒")
print(f"重试次数: {result.retry_count}")
print(f"使用的Docker命令: {result.docker_commands_used}")
print(f"使用的构建脚本: {result.build_scripts_used}")
```

### 2. 日志配置

```python
import logging
from src.utils.logger import log

# 设置日志级别
logging.basicConfig(level=logging.INFO)

# 执行打包，会自动记录详细日志
result = await agent.pack(pack_request)
```

## 故障排除

### 1. Docker连接问题

```python
import docker

try:
    client = docker.from_env()
    client.ping()
    print("Docker连接正常")
except Exception as e:
    print(f"Docker连接失败: {e}")
    print("请检查Docker服务是否正在运行")
```

### 2. 权限问题

```bash
# Linux/Mac 确保用户在docker组中
sudo usermod -aG docker $USER

# Windows 确保Docker Desktop正在运行
```

### 3. 常见问题

**问题**: 构建超时
```python
# 增加超时时间
agent = AutoPackAgent()
agent.docker_timeout = 600  # 10分钟
```

**问题**: 内存不足
```python
# 限制构建内存
pack_request = PackRequest(
    repo_path="/path/to/project",
    build_args={
        "NODE_OPTIONS": "--max-old-space-size=4096"
    }
)
```

## 示例项目

完整的使用示例请参考 `test_autopack_agent.py` 文件，包含：

- Python Flask应用
- Node.js Express应用
- 自动生成Dockerfile的项目
- 带构建脚本项目
- 错误处理示例

## API参考

### PackRequest

```python
class PackRequest:
    repo_path: str                    # 微服务代码仓库路径
    docker_image_name: Optional[str]  # Docker镜像名称
    docker_tag: str = "latest"        # Docker标签
    build_context: str = "."          # 构建上下文路径
    dockerfile_path: str = "Dockerfile"  # Dockerfile路径
    build_args: Optional[Dict[str, str]]  # 构建参数
    environment: str = "development"  # 环境类型
```

### PackResult

```python
class PackResult:
    success: bool                      # 是否成功
    image_name: Optional[str]          # 生成的镜像名称
    image_id: Optional[str]            # 镜像ID
    build_output: str                  # 构建输出
    error_message: Optional[str]       # 错误信息
    execution_time: float              # 执行时间（秒）
    docker_commands_used: List[str]    # 使用的Docker命令
    build_scripts_used: List[str]      # 使用的构建脚本
    retry_count: int                   # 重试次数
```

### AutoPackAgent

```python
class AutoPackAgent:
    def __init__(model, max_retries=5, docker_client=None)
    async def pack(pack_request: PackRequest) -> PackResult
```

### PackWorkflow

```python
class PackWorkflow:
    def __init__(max_retries=5)
    async def run(pack_request: PackRequest, thread_id=None) -> Dict[str, Any]
```

## 贡献和反馈

如果您遇到问题或有改进建议，请：

1. 查看日志了解详细错误信息
2. 检查Docker服务状态
3. 确认项目结构和依赖
4. 提交issue或改进建议