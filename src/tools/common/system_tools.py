"""
系统操作工具集
包含: execute_command 等工具
"""

import os
import subprocess
import shlex
import time
import signal
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def execute_command_core(command: str, cwd: Optional[str] = None,
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
    try:
        # 处理工作目录
        working_dir = None
        if cwd:
            path = Path(cwd)
            if not path.is_absolute():
                path = Path.cwd() / path
            working_dir = str(path)

            if not path.exists():
                return f"错误: 工作目录不存在 - {cwd}"
            if not path.is_dir():
                return f"错误: 指定路径不是目录 - {cwd}"
        else:
            working_dir = str(Path.cwd())

        # 安全检查 - 防止危险命令
        dangerous_commands = [
            'rm -rf', 'sudo rm', 'format', 'del /f', 'rmdir /s',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'mkfs', 'fdisk', 'format'
        ]

        command_lower = command.lower()
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return f"❌ 安全警告: 检测到潜在危险命令，拒绝执行"

        # 记录命令执行
        start_time = time.time()
        logger.info(f"执行命令: {command} 在目录: {working_dir}")

        result = {
            'command': command,
            'working_directory': working_dir,
            'start_time': start_time,
            'timeout': timeout
        }

        # 执行命令
        try:
            # 在Windows上使用shell=True，在Unix上使用默认设置
            use_shell = True

            process = subprocess.Popen(
                command,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
                universal_newlines=True,
                bufsize=1
            )

            # 收集输出
            stdout_lines = []
            stderr_lines = []

            try:
                stdout, stderr = process.communicate(timeout=timeout)

                # Windows下的echo命令可能立即完成，不需要等待超时
                if process.returncode == 0 and stdout.strip():
                    timeout = False  # 标记为非超时完成

                # 限制输出长度
                if len(stdout) > max_output:
                    stdout = stdout[:max_output] + f"\n... (输出被截断，超过 {max_output} 字符限制)"

                if len(stderr) > max_output:
                    stderr = stderr[:max_output] + f"\n... (错误输出被截断，超过 {max_output} 字符限制)"

                exit_code = process.returncode
                execution_time = time.time() - start_time

                result.update({
                    'exit_code': exit_code,
                    'stdout': stdout,
                    'stderr': stderr,
                    'execution_time': execution_time,
                    'success': exit_code == 0
                })

                return _format_command_result(result)

            except subprocess.TimeoutExpired:
                # 超时处理
                process.kill()
                process.wait()

                execution_time = time.time() - start_time
                result.update({
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': f'命令执行超时 ({timeout}秒)',
                    'execution_time': execution_time,
                    'success': False,
                    'timeout': True
                })

                return _format_command_result(result)

        except FileNotFoundError:
            return f"错误: 命令或程序未找到 - {command.split()[0]}"
        except PermissionError:
            return f"错误: 没有执行权限 - {command}"
        except Exception as e:
            return f"错误: 执行命令时发生异常 - {str(e)}"

    except Exception as e:
        logger.error(f"执行命令时出错: {str(e)}")
        return f"错误: 执行命令失败 - {str(e)}"


def _format_command_result(result: Dict) -> str:
    """格式化命令执行结果"""
    output = []

    output.append("🔧 命令执行结果")
    output.append("=" * 50)
    output.append(f"命令: {result['command']}")
    output.append(f"工作目录: {result['working_directory']}")
    output.append(f"执行时间: {result['execution_time']:.2f} 秒")

    if result.get('timeout'):
        output.append(f"⏰ 状态: 超时终止 ({result['timeout']}秒)")
        output.append(f"退出代码: -1")
    else:
        output.append(f"退出代码: {result['exit_code']}")
        if result['success']:
            output.append("✅ 状态: 执行成功")
        else:
            output.append("❌ 状态: 执行失败")

    output.append("")

    # 标准输出
    if result['stdout']:
        output.append("📤 标准输出:")
        output.append("-" * 30)
        stdout_lines = result['stdout'].split('\n')
        for line in stdout_lines:
            if line.strip():
                output.append(f"  {line}")
            else:
                output.append("")
        output.append("")

    # 错误输出
    if result['stderr']:
        output.append("❗ 错误输出:")
        output.append("-" * 30)
        stderr_lines = result['stderr'].split('\n')
        for line in stderr_lines:
            if line.strip():
                output.append(f"  {line}")
            else:
                output.append("")
        output.append("")

    return "\n".join(output)


def get_system_info() -> str:
    """获取系统信息"""
    try:
        import platform
        import psutil

        info = []
        info.append("💻 系统信息")
        info.append("=" * 50)

        # 基本系统信息
        info.append(f"操作系统: {platform.system()} {platform.release()}")
        info.append(f"架构: {platform.machine()}")
        info.append(f"Python版本: {platform.python_version()}")

        # CPU信息
        info.append(f"CPU核心数: {psutil.cpu_count(logical=False)} 物理核心, {psutil.cpu_count()} 逻辑核心")
        info.append(f"CPU使用率: {psutil.cpu_percent(interval=1):.1f}%")

        # 内存信息
        memory = psutil.virtual_memory()
        info.append(f"内存总量: {memory.total / (1024**3):.1f} GB")
        info.append(f"可用内存: {memory.available / (1024**3):.1f} GB")
        info.append(f"内存使用率: {memory.percent:.1f}%")

        # 磁盘信息
        disk = psutil.disk_usage('/')
        info.append(f"磁盘总量: {disk.total / (1024**3):.1f} GB")
        info.append(f"可用磁盘: {disk.free / (1024**3):.1f} GB")
        info.append(f"磁盘使用率: {(disk.used / disk.total) * 100:.1f}%")

        # 当前工作目录信息
        cwd = Path.cwd()
        info.append(f"当前工作目录: {cwd}")

        return "\n".join(info)

    except ImportError:
        # 如果psutil不可用，返回基本信息
        try:
            import platform
            info = []
            info.append("💻 系统信息")
            info.append("=" * 50)
            info.append(f"操作系统: {platform.system()} {platform.release()}")
            info.append(f"架构: {platform.machine()}")
            info.append(f"Python版本: {platform.python_version()}")
            info.append(f"当前工作目录: {Path.cwd()}")
            return "\n".join(info)
        except Exception as e:
            return f"获取系统信息失败: {str(e)}"
    except Exception as e:
        return f"获取系统信息失败: {str(e)}"


def check_directory_permissions(directory: str) -> str:
    """检查目录权限"""
    try:
        path = Path(directory)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            return f"错误: 目录不存在 - {directory}"

        if not path.is_dir():
            return f"错误: 路径不是目录 - {directory}"

        permissions = []

        # 检查读权限
        if os.access(path, os.R_OK):
            permissions.append("✅ 读取")
        else:
            permissions.append("❌ 读取")

        # 检查写权限
        if os.access(path, os.W_OK):
            permissions.append("✅ 写入")
        else:
            permissions.append("❌ 写入")

        # 检查执行权限（对于目录意味着可以进入）
        if os.access(path, os.X_OK):
            permissions.append("✅ 进入")
        else:
            permissions.append("❌ 进入")

        # 获取目录信息
        stat = path.stat()

        result = []
        result.append(f"📁 目录权限检查: {directory}")
        result.append("=" * 50)
        result.append(f"完整路径: {path.absolute()}")
        result.append(f"权限: {' | '.join(permissions)}")
        result.append(f"所有者: {stat.st_uid}")
        result.append(f"组: {stat.st_gid}")
        result.append(f"模式: {oct(stat.st_mode)[-3:]}")

        # 检查目录内容
        try:
            items = list(path.iterdir())
            result.append(f"目录项数量: {len(items)}")
        except PermissionError:
            result.append("目录项数量: 无法访问（权限不足）")

        return "\n".join(result)

    except Exception as e:
        return f"检查目录权限失败: {str(e)}"


def validate_path_security(file_path: str, base_directory: Optional[str] = None) -> str:
    """
    验证路径安全性，防止路径遍历攻击
    """
    try:
        if base_directory is None:
            base_directory = str(Path.cwd())

        base_path = Path(base_directory).resolve()
        target_path = Path(file_path)

        # 如果是相对路径，相对于基础目录解析
        if not target_path.is_absolute():
            target_path = (base_path / target_path).resolve()
        else:
            target_path = target_path.resolve()

        # 检查路径是否在基础目录内
        try:
            target_path.relative_to(base_path)
            is_safe = True
            risk_level = "安全"
        except ValueError:
            is_safe = False
            risk_level = "危险"

        result = []
        result.append("🔒 路径安全检查")
        result.append("=" * 50)
        result.append(f"基础目录: {base_path}")
        result.append(f"目标路径: {target_path}")
        result.append(f"安全状态: {'✅' if is_safe else '❌'} {risk_level}")

        if is_safe:
            result.append("✅ 路径在允许的目录范围内")
        else:
            result.append("⚠️  警告: 路径可能访问允许目录外的文件")
            result.append("   这可能导致安全问题或意外修改系统文件")

        # 检查路径中是否包含可疑模式
        suspicious_patterns = ['..', '~', '$', '%', 'system32', 'windows', 'etc']
        path_str = str(target_path).lower()
        found_patterns = [pattern for pattern in suspicious_patterns if pattern in path_str]

        if found_patterns:
            result.append(f"⚠️  发现可疑模式: {', '.join(found_patterns)}")

        return "\n".join(result)

    except Exception as e:
        return f"路径安全检查失败: {str(e)}"