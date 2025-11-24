"""
工具管理器 - 统一管理LangChain和MCP工具
"""
from typing import List, Dict, Any, Optional
from src.tools.base_tools import unified_tool_manager, register_tool
from src.tools.file_tools import ReadFileTool, WriteFileTool, ListDirectoryTool, SearchFilesTool, JsonFileTool
from src.tools.web_tools import WebSearchTool, HttpRequestTool, WikipediaSearchTool, UrlExtractorTool
import logging

logger = logging.getLogger(__name__)


class ToolManager:
    """
    工具管理器 - 负责管理和提供各种工具
    """

    def __init__(self):
        """初始化工具管理器"""
        self._default_tools_loaded = False
        self._load_default_tools()

    def _load_default_tools(self):
        """加载默认工具"""
        if self._default_tools_loaded:
            return

        try:
            # 注册文件工具
            register_tool(ReadFileTool(), category="file")
            register_tool(WriteFileTool(), category="file")
            register_tool(ListDirectoryTool(), category="file")
            register_tool(SearchFilesTool(), category="file")
            register_tool(JsonFileTool(), category="file")

            # 注册Web工具
            register_tool(WebSearchTool(), category="web")
            register_tool(HttpRequestTool(), category="web")
            register_tool(WikipediaSearchTool(), category="web")
            register_tool(UrlExtractorTool(), category="web")

            self._default_tools_loaded = True
            logger.info("默认工具加载完成")

        except Exception as e:
            logger.error(f"加载默认工具失败: {str(e)}")

    def get_tools(
        self,
        categories: Optional[List[str]] = None,
        include_langchain: bool = True,
        include_mcp: bool = False,
        mcp_servers: Optional[List[str]] = None
    ) -> List:
        """
        获取工具列表

        Args:
            categories: 工具分类
            include_langchain: 是否包含LangChain工具
            include_mcp: 是否包含MCP工具
            mcp_servers: 指定的MCP服务器

        Returns:
            List: 工具列表
        """
        tools = []

        # 获取LangChain工具
        if include_langchain:
            if categories:
                for category in categories:
                    tools.extend(unified_tool_manager.get_tools_by_category(category))
            else:
                # 获取所有已注册的LangChain工具
                langchain_tools = list(unified_tool_manager.langchain_tools.values())
                tools.extend(langchain_tools)

        # 获取MCP工具
        if include_mcp:
            if mcp_servers:
                for server_name in mcp_servers:
                    tools.extend(unified_tool_manager.mcp_registry.get_tools_by_server(server_name))
            else:
                # 获取所有MCP工具
                tools.extend(unified_tool_manager.mcp_registry.get_all_tools())

        return tools

    def get_tools_by_category(self, category: str) -> List:
        """
        根据分类获取工具

        Args:
            category: 分类名称

        Returns:
            List: 工具列表
        """
        return unified_tool_manager.get_tools_by_category(category)

    def search_tools(self, keyword: str) -> List:
        """
        搜索工具

        Args:
            keyword: 搜索关键词

        Returns:
            List: 匹配的工具列表
        """
        return unified_tool_manager.search_tools(keyword)

    def register_custom_tool(self, tool, category: str = "custom"):
        """
        注册自定义工具

        Args:
            tool: 工具实例
            category: 工具分类
        """
        register_tool(tool, category)
        logger.info(f"注册自定义工具: {tool.name} (分类: {category})")

    def get_tool_info(self) -> Dict[str, Any]:
        """
        获取工具信息

        Returns:
            Dict[str, Any]: 工具信息
        """
        return unified_tool_manager.get_stats()

    def list_available_categories(self) -> List[str]:
        """
        列出可用的工具分类

        Returns:
            List[str]: 分类列表
        """
        langchain_categories = list(unified_tool_manager._categories.keys())
        mcp_servers = list(unified_tool_manager.mcp_registry._mcp_tools_by_server.keys())

        return langchain_categories + [f"mcp_{server}" for server in mcp_servers]