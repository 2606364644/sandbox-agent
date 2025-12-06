#!/usr/bin/env python3
"""
自动打包智能体命令行工具
Usage: python autopack_cli.py /path/to/project [image_name]
"""

import asyncio
import sys
import argparse
from pathlib import Path

from src.agents.autopack_agent import AutoPackAgent
from src.core.pack_workflow import PackWorkflow
from src.models.pack_models import PackRequest
from src.utils.logger import log


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="自动打包微服务成Docker容器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python autopack_cli.py /path/to/my-service
  python autopack_cli.py /path/to/my-service my-service-image
  python autopack_cli.py /path/to/my-service --workflow --max-retries 3
        """
    )

    parser.add_argument(
        "repo_path",
        help="微服务代码仓库路径"
    )

    parser.add_argument(
        "image_name",
        nargs="?",
        help="Docker镜像名称（可选，默认为目录名）"
    )

    parser.add_argument(
        "--tag", "-t",
        default="latest",
        help="Docker标签（默认: latest）"
    )

    parser.add_argument(
        "--workflow", "-w",
        action="store_true",
        help="使用智能工作流（包含错误分析和重试策略）"
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="最大重试次数（默认: 5）"
    )

    parser.add_argument(
        "--environment", "-e",
        choices=["development", "staging", "production"],
        default="development",
        help="环境类型（默认: development）"
    )

    parser.add_argument(
        "--build-arg",
        action="append",
        help="构建参数（可多次使用）格式: KEY=VALUE"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )

    return parser.parse_args()


def parse_build_args(build_arg_list):
    """解析构建参数"""
    if not build_arg_list:
        return None

    build_args = {}
    for arg in build_arg_list:
        if "=" in arg:
            key, value = arg.split("=", 1)
            build_args[key] = value
        else:
            log.warning(f"忽略格式错误的构建参数: {arg}")

    return build_args


async def main():
    """主函数"""
    args = parse_args()

    # 设置日志级别
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # 验证项目路径
    repo_path = Path(args.repo_path)
    if not repo_path.exists():
        log.error(f"项目路径不存在: {repo_path}")
        sys.exit(1)

    if not repo_path.is_dir():
        log.error(f"项目路径不是目录: {repo_path}")
        sys.exit(1)

    # 创建打包请求
    pack_request = PackRequest(
        repo_path=str(repo_path.absolute()),
        docker_image_name=args.image_name,
        docker_tag=args.tag,
        environment=args.environment,
        build_args=parse_build_args(args.build_arg)
    )

    log.info(f"开始打包项目: {repo_path}")
    log.info(f"镜像名称: {args.image_name or repo_path.name}:{args.tag}")
    log.info(f"使用模式: {'智能工作流' if args.workflow else '基础打包'}")
    log.info(f"最大重试次数: {args.max_retries}")

    try:
        if args.workflow:
            # 使用智能工作流
            workflow = PackWorkflow(max_retries=args.max_retries)
            result = await workflow.run(pack_request)

            if result['success']:
                log.info("✅ 打包成功!")
                if result['pack_result']:
                    pack_result = result['pack_result']
                    print(f"\n📦 镜像信息:")
                    print(f"   名称: {pack_result.image_name}")
                    print(f"   ID: {pack_result.image_id}")
                    print(f"   执行时间: {pack_result.execution_time:.2f}秒")
                    print(f"   重试次数: {result['retry_count']}")
                    print(f"   检测到构建脚本: {len(result['build_scripts_found'])}")

                    print(f"\n🔧 使用的构建脚本:")
                    for script in result['build_scripts_found']:
                        print(f"   - {script['script_path']} ({script['script_type']})")

            else:
                log.error("❌ 打包失败")
                print(f"\n❌ 错误信息:")
                if result.get('error_history'):
                    for error in result['error_history']:
                        print(f"   - {error}")

        else:
            # 使用基础打包
            agent = AutoPackAgent(max_retries=args.max_retries)
            result = await agent.pack(pack_request)

            if result.success:
                log.info("✅ 打包成功!")
                print(f"\n📦 镜像信息:")
                print(f"   名称: {result.image_name}")
                print(f"   ID: {result.image_id}")
                print(f"   执行时间: {result.execution_time:.2f}秒")
                print(f"   重试次数: {result.retry_count}")

                print(f"\n🔧 使用的构建脚本:")
                for script in result.build_scripts_used:
                    print(f"   - {script}")

            else:
                log.error("❌ 打包失败")
                print(f"\n❌ 错误信息: {result.error_message}")

        return 0 if (result['success'] if args.workflow else result.success) else 1

    except KeyboardInterrupt:
        log.info("用户中断操作")
        return 130
    except Exception as e:
        log.error(f"打包过程中发生异常: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    # 确保Docker服务运行
    try:
        import docker
        docker_client = docker.from_env()
        docker_client.ping()
        print("Docker服务连接正常 ✓")
    except Exception as e:
        print(f"❌ Docker连接失败: {e}")
        print("请确保Docker服务正在运行")
        sys.exit(1)

    # 运行主程序
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(130)