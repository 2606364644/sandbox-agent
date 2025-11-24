"""
基础Agent示例
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.main import LangChainAgentFramework
from src.models.llm_configs import LLMProvider
from src.utils.logger import get_logger, LogContext

logger = get_logger(__name__)


def main():
    """主函数 - 基础Agent示例"""
    print("=== LangChain Agent 基础示例 ===\n")

    try:
        # 创建Agent框架实例
        with LogContext("example", "创建Agent框架"):
            framework = LangChainAgentFramework(
                llm_provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
                enable_file_tools=True,
                enable_web_tools=False,  # 禁用Web工具以避免依赖
                memory_type="buffer",
                verbose=True
            )

        print("✓ Agent框架创建成功")
        print(f"✓ 已加载 {len(framework.tools)} 个工具")
        print(f"✓ 使用模型: {framework.model}\n")

        # 测试工具列表
        print("可用工具:")
        for i, tool_info in enumerate(framework.agent.list_tools(), 1):
            print(f"  {i}. {tool_info['name']}: {tool_info['description']}")
        print()

        # 示例对话
        test_queries = [
            "你好，请介绍一下你的功能",
            "帮我创建一个测试文件并写入一些内容",
            "列出当前目录的文件",
            "你能记住我之前说的话吗？"
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"--- 示例 {i} ---")
            print(f"用户: {query}")

            with LogContext("example", f"处理示例查询 {i}"):
                result = framework.run_single_query(query)
                response = result.get('output', '抱歉，无法处理这个请求。')
                print(f"Assistant: {response}\n")

        # 显示统计信息
        print("=== Agent 统计信息 ===")
        stats = framework.get_agent_stats()
        print(f"框架版本: {stats['framework_version']}")
        print(f"工具数量: {stats['tools_count']}")
        print(f"记忆类型: {stats['memory_stats']['memory_type']}")

        if 'message_count' in stats['memory_stats']:
            print(f"对话消息数: {stats['memory_stats']['message_count']}")

    except Exception as e:
        logger.error(f"运行示例时出错: {str(e)}")
        print(f"错误: {str(e)}")
        print("\n可能的原因:")
        print("1. 未设置OPENAI_API_KEY环境变量")
        print("2. 网络连接问题")
        print("3. 依赖包未正确安装")
        print("\n请检查配置后重试。")


if __name__ == "__main__":
    main()