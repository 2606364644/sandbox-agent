"""
现代化Agent使用示例 - 展示LangChain v1.0最新特性
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.framework import create_modern_framework, AgentFramework
from src.models.llm_configs import LLMProvider
from src.utils.logger import get_logger, LogContext

logger = get_logger(__name__)


async def demonstrate_modern_agent():
    """演示现代化Agent功能"""
    print("=== 现代化Agent演示 ===\n")

    try:
        # 创建现代化框架
        framework = create_modern_framework(
            llm_provider=LLMProvider.OPENAI,
            model="gpt-3.5-turbo",
            verbose=True
        )

        print("✓ 现代化框架创建完成")

        # 创建现代化Agent
        agent = framework.create_agent(
            agent_id="modern_demo",
            enable_mcp=False,  # 为了演示简单，暂时不使用MCP
            system_message="你是一个现代化的AI助手，使用LangChain v1.0最新API。",
            agent_type="openai-tools"
        )

        print("✓ 现代化Agent创建完成")
        print(f"✓ Agent类型: {agent.get_agent_info()}")

        # 创建会话
        session = await framework.create_conversation_session("modern_demo")
        await session.start()

        # 演示查询
        demo_queries = [
            "你好，请介绍一下LangChain v1.0的新特性",
            "你能处理哪些类型的工具？",
            "请用结构化的方式回答这个问题"
        ]

        for i, query in enumerate(demo_queries, 1):
            print(f"\n--- 现代化演示 {i} ---")
            print(f"用户: {query}")

            with LogContext("modern_demo", f"现代化查询 {i}"):
                result = await session.message(query)
                response = result.get('output', '抱歉，无法处理这个请求。')
                print(f"Assistant: {response}")

                # 显示中间步骤（如果有的话）
                if 'intermediate_steps' in result and result['intermediate_steps']:
                    print("中间步骤:")
                    for j, (action, observation) in enumerate(result['intermediate_steps'], 1):
                        print(f"  {j}. 动作: {action}")
                        print(f"     结果: {str(observation)[:100]}...")

        # 结束会话
        summary = await session.end()
        print(f"\n✓ 会话结束: {summary}")

        # 显示框架统计
        stats = framework.get_framework_stats()
        print(f"\n=== 框架统计信息 ===")
        print(f"Agent数量: {stats['agents_count']}")
        print(f"LangChain版本: {stats['langchain_version']}")
        print(f"使用现代化Agent: {stats['use_modern_agents']}")
        print(f"LLM配置: {stats['llm_config']}")

    except Exception as e:
        logger.error(f"现代化Agent演示失败: {str(e)}")
        print(f"错误: {str(e)}")


async def demonstrate_agent_chain():
    """演示Agent链功能"""
    print("\n=== Agent链演示 ===\n")

    try:
        # 创建框架
        framework = create_modern_framework(
            llm_provider=LLMProvider.OPENAI,
            model="gpt-3.5-turbo"
        )

        # 创建Agent链
        chain = framework.create_agent_chain(
            # 第一步：分析Agent
            {
                "system_message": "你是一个问题分析专家，负责分析用户问题的类型和复杂度。",
                "agent_type": "openai-tools"
            },
            # 第二步：解决方案Agent
            {
                "system_message": "你是一个解决方案专家，负责为分析后的问题提供具体解决方案。",
                "agent_type": "openai-tools"
            },
            # 第三步：总结Agent
            {
                "system_message": "你是一个总结专家，负责总结前面的分析和解决方案，并提供最终答案。",
                "agent_type": "openai-tools"
            }
        )

        # 执行链
        test_query = "如何构建一个支持多Agent协作的智能系统？"
        print(f"测试查询: {test_query}")

        results = await chain.execute_chain(test_query)

        print("\n=== Agent链执行结果 ===")
        for i, result in enumerate(results, 1):
            print(f"\n步骤 {i}:")
            print(f"Agent: {result['agent_id']}")
            print(f"输入: {result['input']}")
            print(f"输出: {result['output']}")
            print(f"中间步骤数: {len(result['intermediate_steps'])}")

    except Exception as e:
        logger.error(f"Agent链演示失败: {str(e)}")
        print(f"错误: {str(e)}")


async def demonstrate_different_agent_types():
    """演示不同类型的Agent"""
    print("\n=== 不同Agent类型演示 ===\n")

    try:
        framework = AgentFramework(use_modern_agents=True)

        # 创建不同类型的Agent
        agent_types = ["openai-tools", "xml", "react"]

        for agent_type in agent_types:
            try:
                agent = framework.create_agent(
                    agent_id=f"demo_{agent_type}",
                    agent_type=agent_type,
                    system_message=f"你是一个使用{agent_type}类型的Agent，请展示你的能力。"
                )

                print(f"✓ 创建 {agent_type} Agent 成功")

                # 简单测试
                session = await framework.create_conversation_session(f"demo_{agent_type}")
                await session.start()

                result = await session.message("请简单介绍一下你的工作方式")
                print(f"  {agent_type} 回复: {result['output'][:100]}...")

                await session.end()

            except Exception as e:
                print(f"✗ 创建 {agent_type} Agent 失败: {str(e)}")

    except Exception as e:
        logger.error(f"Agent类型演示失败: {str(e)}")
        print(f"错误: {str(e)}")


async def main():
    """主函数"""
    print("=== LangChain v1.0 现代化Agent演示 ===\n")

    # 检查环境
    if not os.getenv("OPENAI_API_KEY"):
        print("警告: 未设置OPENAI_API_KEY环境变量")
        print("某些功能可能无法正常工作\n")

    try:
        # 演示现代化Agent
        await demonstrate_modern_agent()

        # 演示Agent链
        await demonstrate_agent_chain()

        # 演示不同Agent类型
        await demonstrate_different_agent_types()

        print("\n=== 演示完成 ===")
        print("✅ 所有现代化Agent功能演示完成")

    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"演示程序运行出错: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())