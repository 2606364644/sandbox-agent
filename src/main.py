"""
LangChain Agent 主入口文件
"""
import asyncio
import sys
from typing import List, Dict, Any, Optional
from src.agents.conversational_agent import ConversationalAgent
from src.models.llm_configs import LLMProvider
from src.tools.file_tools import ReadFileTool, WriteFileTool, ListDirectoryTool
from src.tools.web_tools import WebSearchTool, HttpRequestTool
from src.memory.memory_manager import MemoryManager
from src.utils.logger import get_logger, LogContext
from config.settings import get_settings

logger = get_logger(__name__)


class LangChainAgentFramework:
    """LangChain Agent框架主类"""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        enable_file_tools: bool = True,
        enable_web_tools: bool = True,
        memory_type: str = "buffer",
        verbose: bool = True
    ):
        """
        初始化Agent框架

        Args:
            llm_provider: LLM提供商
            model: 模型名称
            enable_file_tools: 是否启用文件工具
            enable_web_tools: 是否启用Web工具
            memory_type: 记忆类型
            verbose: 是否启用详细日志
        """
        self.settings = get_settings()
        self.llm_provider = llm_provider or LLMProvider(self.settings.default_llm_provider)
        self.model = model or self.settings.default_model

        # 初始化组件
        self.agent: Optional[ConversationalAgent] = None
        self.memory_manager = MemoryManager()
        self.tools: List = []

        # 配置工具
        if enable_file_tools:
            self._setup_file_tools()
        if enable_web_tools:
            self._setup_web_tools()

        # 创建Agent
        self._create_agent(memory_type, verbose)

        logger.info("LangChain Agent框架初始化完成")

    def _setup_file_tools(self):
        """设置文件工具"""
        from src.tools.base_tools import get_all_tools
        file_tools = [tool for tool in get_all_tools()
                     if hasattr(tool, 'name') and any(x in tool.name for x in ['file', 'directory', 'json'])]
        self.tools.extend(file_tools)
        logger.info(f"已加载 {len(file_tools)} 个文件工具")

    def _setup_web_tools(self):
        """设置Web工具"""
        from src.tools.base_tools import get_all_tools
        web_tools = [tool for tool in get_all_tools()
                    if hasattr(tool, 'name') and any(x in tool.name for x in ['web', 'http', 'wikipedia', 'url'])]
        self.tools.extend(web_tools)
        logger.info(f"已加载 {len(web_tools)} 个Web工具")

    def _create_agent(self, memory_type: str, verbose: bool):
        """创建Agent"""
        # 创建记忆组件
        memory = self.memory_manager.create_memory_from_config({
            "type": memory_type,
            "params": {}
        })

        # 创建Agent
        self.agent = ConversationalAgent(
            llm_provider=self.llm_provider,
            model=self.model,
            tools=self.tools,
            memory=memory,
            verbose=verbose
        )

    def run_interactive_mode(self):
        """运行交互模式"""
        print("=== LangChain Agent 交互模式 ===")
        print("输入 'help' 查看命令，输入 'quit' 退出")
        print(f"当前模型: {self.model}")
        print(f"可用工具数量: {len(self.tools)}")
        print("-" * 40)

        while True:
            try:
                user_input = input("\n您: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("再见！")
                    break

                if user_input.lower() == 'help':
                    self._show_help()
                    continue

                if user_input.lower() == 'tools':
                    self._show_tools()
                    continue

                if user_input.lower() == 'memory':
                    self._show_memory_info()
                    continue

                if user_input.lower() == 'clear':
                    self.agent.clear_memory()
                    print("记忆已清空")
                    continue

                if not user_input:
                    continue

                # 执行Agent
                with LogContext("main", f"处理用户输入: {user_input[:50]}..."):
                    result = self.agent.run(user_input)
                    print(f"\nAssistant: {result.get('output', '抱歉，我无法处理这个请求。')}")

            except KeyboardInterrupt:
                print("\n\n程序被用户中断")
                break
            except Exception as e:
                logger.error(f"处理用户输入时出错: {str(e)}")
                print(f"\n错误: {str(e)}")

    def _show_help(self):
        """显示帮助信息"""
        help_text = """
可用命令:
  help     - 显示此帮助信息
  tools    - 显示可用工具列表
  memory   - 显示记忆信息
  clear    - 清空对话记忆
  quit     - 退出程序

使用示例:
  - "帮我读取文件 /path/to/file.txt"
  - "搜索关于人工智能的信息"
  - "列出当前目录的内容"
  - "访问 https://example.com 获取内容"
        """
        print(help_text)

    def _show_tools(self):
        """显示工具信息"""
        tools_info = self.agent.list_tools()
        print(f"\n可用工具 ({len(tools_info)}个):")
        for i, tool in enumerate(tools_info, 1):
            print(f"{i}. {tool['name']}: {tool['description']}")

    def _show_memory_info(self):
        """显示记忆信息"""
        summary = self.agent.get_conversation_context()
        print(f"\n记忆信息:")
        print(f"消息数量: {summary['message_count']}")
        print(f"最近5条消息:")

        messages = summary['messages'][-5:]
        for msg in messages:
            msg_type = "用户" if msg['type'] == 'HumanMessage' else "AI"
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"  {msg_type}: {content}")

    def run_single_query(self, query: str) -> Dict[str, Any]:
        """
        运行单个查询

        Args:
            query: 查询文本

        Returns:
            Dict[str, Any]: 查询结果
        """
        with LogContext("main", f"执行查询: {query[:50]}..."):
            return self.agent.run(query)

    async def arun_single_query(self, query: str) -> Dict[str, Any]:
        """
        异步运行单个查询

        Args:
            query: 查询文本

        Returns:
            Dict[str, Any]: 查询结果
        """
        with LogContext("main", f"异步执行查询: {query[:50]}..."):
            return await self.agent.arun(query)

    def add_custom_tool(self, tool):
        """
        添加自定义工具

        Args:
            tool: 工具实例
        """
        self.agent.add_tool(tool)
        self.tools.append(tool)
        logger.info(f"已添加自定义工具: {tool.name}")

    def get_agent_stats(self) -> Dict[str, Any]:
        """获取Agent统计信息"""
        return {
            "agent_stats": self.agent.get_stats(),
            "memory_stats": self.memory_manager.get_memory_stats(self.agent.memory),
            "tools_count": len(self.tools),
            "framework_version": "1.0.0"
        }

    def save_conversation(self, file_path: str):
        """
        保存对话历史

        Args:
            file_path: 保存路径
        """
        self.agent.save_conversation(file_path)
        logger.info(f"对话历史已保存到: {file_path}")

    def load_conversation(self, file_path: str):
        """
        加载对话历史

        Args:
            file_path: 文件路径
        """
        self.agent.load_conversation(file_path)
        logger.info(f"对话历史已从 {file_path} 加载")


def main():
    """主函数"""
    try:
        # 解析命令行参数
        import argparse
        parser = argparse.ArgumentParser(description="LangChain Agent框架")
        parser.add_argument("--provider", choices=["openai", "azure_openai", "anthropic", "huggingface"],
                          help="LLM提供商")
        parser.add_argument("--model", help="模型名称")
        parser.add_argument("--no-file-tools", action="store_true", help="禁用文件工具")
        parser.add_argument("--no-web-tools", action="store_true", help="禁用Web工具")
        parser.add_argument("--memory-type", choices=["buffer", "window", "summary"],
                          default="buffer", help="记忆类型")
        parser.add_argument("--quiet", action="store_true", help="静默模式")
        parser.add_argument("--query", help="执行单个查询")
        args = parser.parse_args()

        # 创建框架实例
        framework = LangChainAgentFramework(
            llm_provider=LLMProvider(args.provider) if args.provider else None,
            model=args.model,
            enable_file_tools=not args.no_file_tools,
            enable_web_tools=not args.no_web_tools,
            memory_type=args.memory_type,
            verbose=not args.quiet
        )

        if args.query:
            # 执行单个查询
            result = framework.run_single_query(args.query)
            print(result.get('output', ''))
        else:
            # 运行交互模式
            framework.run_interactive_mode()

    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()