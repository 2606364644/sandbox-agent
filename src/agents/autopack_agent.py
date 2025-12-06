import asyncio
import os
import subprocess
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import docker
from langchain_openai import ChatOpenAI

from src.agents.base_agent import BaseAgent
from src.clients import get_llm_client
from src.models.pack_models import PackRequest, PackResult, BuildScript, PackWorkflowState
from src.utils.logger import log


class AutoPackAgent(BaseAgent):
    """自动打包/编译智能体 - 自动将微服务打包成Docker容器"""

    def __init__(
        self,
        model: Optional[ChatOpenAI] = None,
        max_retries: int = 5,
        docker_client: Optional[docker.DockerClient] = None
    ):
        super().__init__()

        self.model = model or get_llm_client()
        self.max_retries = max_retries

        # 初始化Docker客户端，增加错误处理
        try:
            self.docker_client = docker_client or docker.from_env()
            # 测试Docker连接
            self.docker_client.ping()
            log.info("Docker客户端连接成功")
        except Exception as e:
            log.error(f"Docker客户端初始化失败: {e}")
            raise RuntimeError(f"无法连接到Docker服务: {e}。请确保Docker服务正在运行。")

        # 常见构建脚本模式
        self.build_script_patterns = {
            'shell': ['build.sh', 'build', 'Makefile', 'build.bat', 'build.cmd'],
            'python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
            'node': ['package.json', 'Gruntfile.js', 'Gulpfile.js', 'webpack.config.js'],
            'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
            'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
            'rust': ['Cargo.toml'],
            'go': ['go.mod', 'go.sum'],
        }

    async def pack(self, pack_request: PackRequest) -> PackResult:
        """执行打包操作"""
        log.info(f"开始打包项目: {pack_request.repo_path}")

        start_time = time.time()
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                result = await self._attempt_pack(pack_request, retry_count)

                execution_time = time.time() - start_time
                result.execution_time = execution_time
                result.retry_count = retry_count

                if result.success:
                    log.info(f"打包成功! 镜像: {result.image_name}, 耗时: {execution_time:.2f}秒")
                    return result
                else:
                    log.warning(f"第{retry_count + 1}次打包失败: {result.error_message}")
                    retry_count += 1

            except Exception as e:
                log.error(f"第{retry_count + 1}次打包异常: {e}")
                retry_count += 1

                if retry_count >= self.max_retries:
                    break

                # 等待一段时间后重试
                await asyncio.sleep(2 ** retry_count)  # 指数退避

        # 所有重试都失败了
        execution_time = time.time() - start_time
        return PackResult(
            success=False,
            error_message=f"经过{retry_count}次重试后仍然失败",
            build_output="",
            execution_time=execution_time,
            retry_count=retry_count
        )

    async def _attempt_pack(self, pack_request: PackRequest, retry_count: int) -> PackResult:
        """尝试打包（单次）"""
        repo_path = Path(pack_request.repo_path)

        if not repo_path.exists():
            return PackResult(
                success=False,
                error_message=f"项目路径不存在: {pack_request.repo_path}",
                build_output=""
            )

        # 1. 检测构建脚本
        build_scripts = await self._detect_build_scripts(repo_path)
        log.info(f"检测到 {len(build_scripts)} 个构建脚本")

        # 2. 生成Dockerfile（如果不存在）
        dockerfile_path = await self._ensure_dockerfile(repo_path, build_scripts, pack_request)

        # 3. 执行预构建脚本
        pre_build_output = await self._run_pre_build_scripts(repo_path, build_scripts)

        # 4. 构建Docker镜像
        return await self._build_docker_image(repo_path, dockerfile_path, pack_request, pre_build_output)

    async def _detect_build_scripts(self, repo_path: Path) -> List[BuildScript]:
        """检测项目中的构建脚本"""
        build_scripts = []

        for script_type, patterns in self.build_script_patterns.items():
            for pattern in patterns:
                # 在根目录和常见子目录中查找
                search_paths = [repo_path] + [repo_path / d for d in ['scripts', 'build', '.github', 'ci']]

                for search_path in search_paths:
                    file_path = search_path / pattern
                    if file_path.exists():
                        script = BuildScript(
                            script_path=str(file_path.relative_to(repo_path)),
                            script_type=script_type,
                            description=f"检测到{script_type}构建文件: {pattern}",
                            priority=1 if pattern == 'Dockerfile' else 2
                        )
                        build_scripts.append(script)
                        log.info(f"发现构建脚本: {script.script_path} (类型: {script_type})")

        # 按优先级排序
        build_scripts.sort(key=lambda x: x.priority)
        return build_scripts

    async def _ensure_dockerfile(self, repo_path: Path, build_scripts: List[BuildScript], pack_request: PackRequest) -> str:
        """确保Dockerfile存在，如果不存在则生成"""
        dockerfile_path = repo_path / pack_request.dockerfile_path

        if dockerfile_path.exists():
            log.info(f"使用现有Dockerfile: {dockerfile_path}")
            return str(dockerfile_path.relative_to(repo_path))

        log.info("未找到Dockerfile，尝试自动生成...")
        generated_dockerfile = await self._generate_dockerfile(repo_path, build_scripts, pack_request)

        if generated_dockerfile:
            dockerfile_path.write_text(generated_dockerfile, encoding='utf-8')
            log.info(f"生成Dockerfile成功: {dockerfile_path}")
            return str(dockerfile_path.relative_to(repo_path))
        else:
            log.warning("无法生成Dockerfile，尝试使用通用模板")
            generic_dockerfile = await self._create_generic_dockerfile(repo_path, pack_request)
            dockerfile_path.write_text(generic_dockerfile, encoding='utf-8')
            return str(dockerfile_path.relative_to(repo_path))

    async def _generate_dockerfile(self, repo_path: Path, build_scripts: List[BuildScript], pack_request: PackRequest) -> Optional[str]:
        """基于项目结构生成Dockerfile"""

        # 分析项目类型
        project_type = self._analyze_project_type(build_scripts)

        # 基于项目类型生成Dockerfile
        dockerfile_templates = {
            'python': self._get_python_dockerfile(),
            'node': self._get_node_dockerfile(),
            'java': self._get_java_dockerfile(),
            'go': self._get_go_dockerfile(),
            'rust': self._get_rust_dockerfile(),
            'generic': self._get_generic_dockerfile()
        }

        template = dockerfile_templates.get(project_type, dockerfile_templates['generic'])

        # 检测端口
        exposed_port = await self._detect_exposed_port(repo_path)
        if exposed_port:
            template = template.replace("EXPOSE 8080", f"EXPOSE {exposed_port}")

        return template

    def _analyze_project_type(self, build_scripts: List[BuildScript]) -> str:
        """分析项目类型"""
        script_types = [script.script_type for script in build_scripts]

        if 'python' in script_types:
            return 'python'
        elif 'node' in script_types:
            return 'node'
        elif 'java' in script_types:
            return 'java'
        elif 'go' in script_types:
            return 'go'
        elif 'rust' in script_types:
            return 'rust'
        else:
            return 'generic'

    async def _detect_exposed_port(self, repo_path: Path) -> Optional[int]:
        """尝试检测应用监听的端口"""
        # 搜索常见端口配置模式
        port_patterns = [
            r'port[\'"\s]*[:=][\'"\s]*(\d+)',
            r'PORT[\'"\s]*[:=][\'"\s]*(\d+)',
            r'listen[\'"\s]*[:=][\'"\s]*(\d+)',
            r'bind[\'"\s]*[:=][\'"\s]*(\d+)',
        ]

        common_ports = [3000, 8000, 8080, 5000, 9000, 4000, 7000]

        # 简单返回常见端口
        return 8080

    async def _run_pre_build_scripts(self, repo_path: Path, build_scripts: List[BuildScript]) -> str:
        """运行预构建脚本"""
        output = ""

        for script in build_scripts:
            if script.script_type == 'shell':
                try:
                    log.info(f"执行构建脚本: {script.script_path}")

                    # 根据操作系统和脚本类型选择合适的执行方式
                    if os.name == 'nt':  # Windows
                        if script.script_path.endswith('.sh'):
                            log.warning(f"Windows系统跳过shell脚本: {script.script_path}")
                            continue
                        elif script.script_path.endswith(('.bat', '.cmd')):
                            cmd = ['cmd', '/c', script.script_path]
                        else:
                            log.warning(f"未知的Windows脚本类型: {script.script_path}")
                            continue
                    else:  # Unix/Linux/macOS
                        if script.script_path.endswith(('.bat', '.cmd')):
                            log.warning(f"Unix系统跳过Windows脚本: {script.script_path}")
                            continue
                        elif script.script_path.endswith('.sh'):
                            cmd = ['bash', script.script_path]
                        else:
                            # 尝试直接执行
                            cmd = [script.script_path]

                    result = subprocess.run(
                        cmd,
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟超时
                    )

                    output += f"--- 执行 {script.script_path} ---\n"
                    output += f"stdout: {result.stdout}\n"
                    if result.stderr:
                        output += f"stderr: {result.stderr}\n"
                    output += f"返回码: {result.returncode}\n\n"

                    if result.returncode != 0:
                        log.warning(f"构建脚本执行失败: {script.script_path}")

                except subprocess.TimeoutExpired:
                    log.error(f"构建脚本执行超时: {script.script_path}")
                    output += f"--- {script.script_path} 执行超时 ---\n"
                except Exception as e:
                    log.error(f"执行构建脚本异常: {script.script_path}, {e}")
                    output += f"--- {script.script_path} 执行异常: {e} ---\n"

        return output

    async def _build_docker_image(self, repo_path: Path, dockerfile_path: str, pack_request: PackRequest, pre_build_output: str) -> PackResult:
        """构建Docker镜像"""
        try:
            # 确定镜像名称
            image_name = pack_request.docker_image_name or repo_path.name.lower().replace(' ', '-')
            full_image_name = f"{image_name}:{pack_request.docker_tag}"

            log.info(f"开始构建Docker镜像: {full_image_name}")

            # 准备构建参数
            build_args = pack_request.build_args or {}

            # 执行Docker构建
            image, build_logs = self.docker_client.images.build(
                path=str(repo_path),
                dockerfile=dockerfile_path,
                tag=full_image_name,
                buildargs=build_args,
                rm=True,  # 删除中间容器
                forcerm=True  # 强制删除中间容器
            )

            # 收集构建日志
            build_output = "--- 预构建输出 ---\n" + pre_build_output + "\n"
            build_output += "--- Docker构建日志 ---\n"
            for log_entry in build_logs:
                if isinstance(log_entry, dict) and 'stream' in log_entry:
                    build_output += log_entry['stream']
                else:
                    build_output += str(log_entry)

            log.info(f"Docker镜像构建成功: {full_image_name}")

            return PackResult(
                success=True,
                image_name=full_image_name,
                image_id=image.id,
                build_output=build_output,
                docker_commands_used=[f"docker build -t {full_image_name} -f {dockerfile_path} {repo_path}"],
                build_scripts_used=[dockerfile_path]
            )

        except docker.errors.BuildError as e:
            error_msg = f"Docker构建失败: {e}"
            log.error(error_msg)

            build_output = "--- 预构建输出 ---\n" + pre_build_output + "\n"
            build_output += "--- Docker构建错误 ---\n" + str(e)

            return PackResult(
                success=False,
                error_message=error_msg,
                build_output=build_output
            )

        except Exception as e:
            error_msg = f"构建过程中发生异常: {e}"
            log.error(error_msg)

            return PackResult(
                success=False,
                error_message=error_msg,
                build_output=pre_build_output
            )

    def _get_python_dockerfile(self) -> str:
        return """# Python应用Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "app.py"]
"""

    def _get_node_dockerfile(self) -> str:
        return """# Node.js应用Dockerfile
FROM node:18-alpine

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["npm", "start"]
"""

    def _get_java_dockerfile(self) -> str:
        return """# Java应用Dockerfile
FROM maven:3.8-openjdk-11

WORKDIR /app

# 复制pom文件
COPY pom.xml .

# 下载依赖
RUN mvn dependency:go-offline

# 复制源代码
COPY src ./src

# 构建应用
RUN mvn clean package -DskipTests

# 运行时镜像
FROM openjdk:11-jre-slim
WORKDIR /app
COPY --from=0 /app/target/*.jar app.jar

EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
"""

    def _get_go_dockerfile(self) -> str:
        return """# Go应用Dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 复制go mod文件
COPY go.mod go.sum ./

# 下载依赖
RUN go mod download

# 复制源代码
COPY . .

# 构建应用
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# 运行时镜像
FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .

EXPOSE 8080
CMD ["./main"]
"""

    def _get_rust_dockerfile(self) -> str:
        return """# Rust应用Dockerfile
FROM rust:1.70 as builder

WORKDIR /app

# 复制Cargo文件
COPY Cargo.toml Cargo.lock ./

# 创建空的main.rs来预构建依赖
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release && rm -rf src

# 复制源代码
COPY src ./src

# 构建应用
RUN cargo build --release

# 运行时镜像
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/target/release/app .

EXPOSE 8080
CMD ["./app"]
"""

    def _get_generic_dockerfile(self) -> str:
        return """# 通用应用Dockerfile
FROM alpine:latest

WORKDIR /app

# 复制应用代码
COPY . .

# 安装基础工具
RUN apk add --no-cache ca-certificates

# 暴露端口
EXPOSE 8080

# 启动命令（需要根据实际情况调整）
CMD ["./start.sh"]
"""

    async def _create_generic_dockerfile(self, repo_path: Path, pack_request: PackRequest) -> str:
        """创建通用Dockerfile"""
        return self._get_generic_dockerfile()


# 使用示例
async def main():
    """测试AutoPackAgent"""
    agent = AutoPackAgent()

    pack_request = PackRequest(
        repo_path="/path/to/your/microservice",
        docker_image_name="my-service",
        docker_tag="v1.0.0",
        environment="production"
    )

    result = await agent.pack(pack_request)

    print("\n" + "="*50)
    print("打包结果:")
    print(f"成功: {result.success}")
    print(f"镜像名称: {result.image_name}")
    print(f"镜像ID: {result.image_id}")
    print(f"执行时间: {result.execution_time:.2f}秒")
    print(f"重试次数: {result.retry_count}")

    if result.error_message:
        print(f"错误信息: {result.error_message}")

    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())