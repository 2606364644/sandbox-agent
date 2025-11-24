"""
MCP Agent示例 - 展示MCP工具的使用
"""
import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.main import LangChainAgentFramework
from src.models.llm_configs import LLMProvider
from src.tools.mcp import MCPToolLoader, mcp_server_manager
from src.tools.base_tools import initialize_tools, tool_collector
from src.utils.logger import get_logger, LogContext

logger = get_logger(__name__)


async def main():
    """主函数 - MCP Agent示例"""
    print("=== LangChain Agent MCP示例 ===\n")

    try:
        # 显示MCP服务器信息
        print("可用的MCP服务器:")
        servers = MCPToolLoader.list_mcp_servers()
        for i, server in enumerate(servers, 1):
            status = "运行中" if server['status'] == 'running' else "已停止"
            print(f"  {i}. {server['name']}: {server['description']} ({status})")
        print()

        # 选择要启动的MCP服务器
        selected_servers = ["filesystem"]  # 默认启动文件系统服务器
        print(f"将启动MCP服务器: {', '.join(selected_servers)}")

        # 启动选定的MCP服务器
        started_servers = {}
        for server_name in selected_servers:
            success = await MCPToolLoader.start_server(server_name)
            started_servers[server_name] = success
            if success:
                print(f"✓ MCP服务器 {server_name} 启动成功")
            else:
                print(f"✗ MCP服务器 {server_name} 启动失败")

        if not any(started_servers.values()):
            print("没有MCP服务器启动成功，将仅使用LangChain工具")
            enable_mcp = False
        else:
            enable_mcp = True

        print()

        # 初始化工具系统
        print("正在初始化工具系统...")
        with LogContext("mcp_example", "初始化工具系统"):
            init_result = await initialize_tools(enable_mcp=enable_mcp)

        print(f"✓ 工具系统初始化完成")
        print(f"  - LangChain工具: {init_result['langchain_tools']} 个")
        print(f"  - MCP工具: {init_result['mcp_tools']} 个")

        if init_result.get('mcp_servers'):
            for server, count in init_result['mcp_servers'].items():
                print(f"  - {server}: {count} 个工具")

        print()

        # 创建Agent框架
        print("创建Agent框架...")
        framework = LangChainAgentFramework(
            llm_provider=LLMProvider.OPENAI,
            model="gpt-3.5-turbo",
            enable_file_tools=True,
            enable_web_tools=False,  # 禁用Web工具以专注于MCP
            memory_type="buffer",
            verbose=True
        )

        # 获取包含MCP工具的工具列表
        print("正在加载MCP工具到Agent...")
        mcp_tools = []
        if enable_mcp:
            for server_name in selected_servers:
                if started_servers.get(server_name):
                    server_tools = await tool_collector.get_tools(
                        include_langchain=False,
                        include_mcp=True,
                        mcp_servers=[server_name]
                    )
                    mcp_tools.extend(server_tools)
                    print(f"  - {server_name}: {len(server_tools)} 个工具")

        # 添加MCP工具到Agent
        for tool in mcp_tools:
            framework.add_custom_tool(tool)

        print(f"✓ Agent创建完成，总共 {len(framework.tools)} 个工具")

        # 显示工具信息
        print("\n可用工具:")
        for i, tool_info in enumerate(framework.agent.list_tools(), 1):
            tool_type = "MCP" if "MCP" in tool_info.get('type', '') else "LangChain"
            print(f"  {i}. {tool_info['name']}: {tool_info['description']} ({tool_type})")

        print()

        # MCP功能演示
        if enable_mcp and mcp_tools:
            print("=== MCP工具演示 ===\n")

            demo_queries = [
                "帮我列出当前目录的文件和文件夹",  # 文件系统MCP工具
                "请帮我读取一个README文件的内容",
                "创建一个测试文件并写入一些内容"
            ]

            for i, query in enumerate(demo_queries, 1):
                print(f"--- 演示 {i} ---")
                print(f"用户: {query}")

                with LogContext("mcp_demo", f"执行演示查询 {i}"):
                    result = framework.run_single_query(query)
                    response = result.get('output', '抱歉，无法处理这个请求。')
                    print(f"Assistant: {response}\n")

        else:
            print("没有可用的MCP工具，跳过MCP演示\n")

        # 显示统计信息
        print("=== 统计信息 ===")
        framework_stats = framework.get_agent_stats()
        print(f"框架版本: {framework_stats['framework_version']}")
        print(f"总工具数: {framework_stats['tools_count']}")

        # MCP统计信息
        if enable_mcp:
            mcp_stats = MCPToolLoader.get_mcp_stats()
            print(f"MCP服务器: {len(mcp_stats.get('servers', {}))}")
            print(f"MCP工具总数: {mcp_stats.get('total_tools', 0)}")
            print(f"可用MCP工具: {mcp_stats.get('available_tools', 0)}")

        # 显示服务器状态
        print("\n=== MCP服务器状态 ===")
        for server_name in selected_servers:
            if started_servers.get(server_name):
                status = "运行中" if mcp_server_manager.get_client(server_name) and mcp_server_manager.get_client(server_name).is_alive() else "已停止"
                tool_count = len(mcp_server_manager.get_tool_collection(server_name).get_tools()) if mcp_server_manager.get_tool_collection(server_name) else 0
                print(f"{server_name}: {status} (工具数: {tool_count})")

        # 清理资源
        print("\n正在清理资源...")
        for server_name in selected_servers:
            await MCPToolLoader.stop_server(server_name)
            print(f"✓ MCP服务器 {server_name} 已停止")

        print("✓ 资源清理完成")

    except Exception as e:
        logger.error(f"运行MCP示例时出错: {str(e)}")
        print(f"错误: {str(e)}")
        print("\n可能的原因:")
        print("1. 未安装Node.js或npx")
        print("2. 未安装MCP服务器包")
        print("3. 网络连接问题")
        print("4. 权限问题")
        print("\n请检查环境配置后重试。")


async def interactive_mcp_demo():
    """交互式MCP演示"""
    print("=== 交互式MCP演示 ===\n")

    try:
        # 启动文件系统MCP服务器
        print("启动文件系统MCP服务器...")
        success = await MCPToolLoader.start_server("filesystem")

        if not success:
            print("无法启动文件系统MCP服务器")
            return

        print("✓ 文件系统MCP服务器启动成功\n")

        # 加载MCP工具
        tools = await MCPToolLoader.load_server_tools("filesystem")
        print(f"✓ 加载了 {len(tools)} 个MCP工具")

        # 显示可用工具
        print("\n可用的MCP工具:")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool.name}: {tool.description}")

        print("\n输入 'quit' 退出交互模式")
        print("-" * 40)

        # 创建简单的Agent（仅用于演示工具调用）
        while True:
            try:
                user_input = input("\n您: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("再见！")
                    break

                if not user_input:
                    continue

                # 查找相关工具
                matched_tools = []
                for tool in tools:
                    if any(keyword in user_input.lower() for keyword in tool.name.lower().split('_')):
                        matched_tools.append(tool)

                if not matched_tools:
                    print("未找到相关的MCP工具")
                    continue

                print(f"找到相关工具: {[tool.name for tool in matched_tools]}")

                # 尝试调用第一个匹配的工具
                tool = matched_tools[0]
                print(f"调用工具: {tool.name}")

                try:
                    result = await tool._arun()
                    print(f"工具结果: {result}")
                except Exception as e:
                    print(f"工具调用失败: {str(e)}")

            except KeyboardInterrupt:
                print("\n\n程序被用户中断")
                break
            except Exception as e:
                print(f"\n错误: {str(e)}")

        # 停止服务器
        await MCPToolLoader.stop_server("filesystem")
        print("✓ 文件系统MCP服务器已停止")

    except Exception as e:
        logger.error(f"交互式MCP演示失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Agent示例")
    parser.add_argument("--interactive", action="store_true", help="运行交互式演示")
    args = parser.parse_args()

    if args.interactive:
        asyncio.run(interactive_mcp_demo())
    else:
        asyncio.run(main())