"""
MCP注册表和统一工具管理
"""
import asyncio
from typing import Dict, Any, List, Optional, Union, Set
from langchain.tools import BaseTool
import logging

from .mcp_server_manager import mcp_server_manager, MCPServerManager
from .mcp_tool_adapter import MCPServerToolCollection, MCPToolAdapter

logger = logging.getLogger(__name__)


class MCPRegistry:
    """MCP工具注册表 - 管理所有MCP工具"""

    def __init__(self, server_manager: MCPServerManager = None):
        """
        初始化MCP注册表

        Args:
            server_manager: MCP服务器管理器
        """
        self.server_manager = server_manager or mcp_server_manager
        self._mcp_tools: Dict[str, MCPToolAdapter] = {}
        self._mcp_tools_by_server: Dict[str, List[str]] = {}
        self._loaded_servers: Set[str] = set()
        self._auto_load_enabled = True

    async def load_server_tools(self, server_name: str) -> List[MCPToolAdapter]:
        """
        加载指定服务器的MCP工具

        Args:
            server_name: 服务器名称

        Returns:
            List[MCPToolAdapter]: 工具适配器列表
        """
        if not self.server_manager:
            logger.error("MCP服务器管理器未初始化")
            return []

        # 确保服务器正在运行
        client = self.server_manager.get_client(server_name)
        if not client or not client.is_alive():
            if not await self.server_manager.start_server(server_name):
                logger.error(f"无法启动MCP服务器: {server_name}")
                return []

        try:
            # 获取工具集合
            tool_collection = self.server_manager.get_tool_collection(server_name)
            if not tool_collection:
                logger.error(f"未找到服务器的工具集合: {server_name}")
                return []

            # 加载工具
            tools = await tool_collection.load_tools()

            # 注册工具
            server_tools = []
            for tool in tools:
                await self._register_mcp_tool(tool, server_name)
                server_tools.append(tool)

            self._loaded_servers.add(server_name)
            logger.info(f"从服务器 {server_name} 加载了 {len(tools)} 个MCP工具")
            return server_tools

        except Exception as e:
            logger.error(f"加载服务器 {server_name} 的MCP工具失败: {str(e)}")
            return []

    async def _register_mcp_tool(self, tool: MCPToolAdapter, server_name: str):
        """
        注册单个MCP工具

        Args:
            tool: 工具适配器
            server_name: 服务器名称
        """
        # 检查工具名冲突
        if tool.name in self._mcp_tools:
            original_tool = self._mcp_tools[tool.name]
            original_server = self._get_tool_server(tool.name)
            logger.warning(
                f"MCP工具名冲突: {tool.name} "
                f"(服务器: {server_name} vs {original_server})"
            )
            # 重命名工具以避免冲突
            tool.name = f"{server_name}_{tool.name}"

        self._mcp_tools[tool.name] = tool

        if server_name not in self._mcp_tools_by_server:
            self._mcp_tools_by_server[server_name] = []
        self._mcp_tools_by_server[server_name].append(tool.name)

        logger.debug(f"注册MCP工具: {tool.name} (服务器: {server_name})")

    def _get_tool_server(self, tool_name: str) -> Optional[str]:
        """
        获取工具所属的服务器

        Args:
            tool_name: 工具名称

        Returns:
            Optional[str]: 服务器名称
        """
        for server_name, tool_names in self._mcp_tools_by_server.items():
            if tool_name in tool_names:
                return server_name
        return None

    async def unload_server_tools(self, server_name: str) -> int:
        """
        卸载指定服务器的MCP工具

        Args:
            server_name: 服务器名称

        Returns:
            int: 卸载的工具数量
        """
        if server_name not in self._mcp_tools_by_server:
            return 0

        tool_names = self._mcp_tools_by_server[server_name]
        count = len(tool_names)

        # 移除工具
        for tool_name in tool_names:
            if tool_name in self._mcp_tools:
                del self._mcp_tools[tool_name]

        # 清理服务器记录
        del self._mcp_tools_by_server[server_name]
        self._loaded_servers.discard(server_name)

        logger.info(f"卸载服务器 {server_name} 的 {count} 个MCP工具")
        return count

    async def load_all_tools(self) -> Dict[str, int]:
        """
        加载所有服务器的MCP工具

        Returns:
            Dict[str, int]: 各服务器加载的工具数量
        """
        if not self.server_manager:
            logger.error("MCP服务器管理器未初始化")
            return {}

        results = {}

        # 启动所有自动启动的服务器
        await self.server_manager.start_all_auto_servers()

        # 加载所有运行中服务器的工具
        for server_name in self.server_manager.list_servers():
            server_info = next(
                (s for s in self.server_manager.list_servers() if s['name'] == server_name),
                None
            )
            if server_info and server_info['status'] == 'running':
                tools = await self.load_server_tools(server_name)
                results[server_name] = len(tools)

        return results

    async def reload_tools(self) -> Dict[str, int]:
        """
        重新加载所有MCP工具

        Returns:
            Dict[str, int]: 各服务器加载的工具数量
        """
        # 清理现有工具
        await self.unload_all_tools()

        # 重新加载
        return await self.load_all_tools()

    async def unload_all_tools(self):
        """卸载所有MCP工具"""
        server_names = list(self._mcp_tools_by_server.keys())
        for server_name in server_names:
            await self.unload_server_tools(server_name)

    def get_tool(self, name: str) -> Optional[MCPToolAdapter]:
        """
        根据名称获取MCP工具

        Args:
            name: 工具名称

        Returns:
            Optional[MCPToolAdapter]: MCP工具适配器
        """
        return self._mcp_tools.get(name)

    def get_all_tools(self) -> List[MCPToolAdapter]:
        """
        获取所有MCP工具

        Returns:
            List[MCPToolAdapter]: MCP工具适配器列表
        """
        return list(self._mcp_tools.values())

    def get_tools_by_server(self, server_name: str) -> List[MCPToolAdapter]:
        """
        根据服务器获取MCP工具

        Args:
            server_name: 服务器名称

        Returns:
            List[MCPToolAdapter]: MCP工具适配器列表
        """
        tool_names = self._mcp_tools_by_server.get(server_name, [])
        return [self._mcp_tools[name] for name in tool_names if name in self._mcp_tools]

    def search_tools(self, keyword: str) -> List[MCPToolAdapter]:
        """
        搜索MCP工具

        Args:
            keyword: 搜索关键词

        Returns:
            List[MCPToolAdapter]: 匹配的工具列表
        """
        keyword = keyword.lower()
        matched_tools = []

        for tool in self._mcp_tools.values():
            if (keyword in tool.name.lower() or
                keyword in tool.description.lower()):
                matched_tools.append(tool)

        return matched_tools

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有MCP工具信息

        Returns:
            Dict[str, Dict[str, Any]]: 工具信息字典
        """
        tools_info = {}
        for name, tool in self._mcp_tools.items():
            tools_info[name] = {
                "name": tool.name,
                "description": tool.description,
                "server": self._get_tool_server(name),
                "type": "MCP",
                "available": tool.is_available() if hasattr(tool, 'is_available') else True
            }
        return tools_info

    def get_loaded_servers(self) -> List[str]:
        """
        获取已加载工具的服务器列表

        Returns:
            List[str]: 服务器名称列表
        """
        return list(self._loaded_servers)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取MCP注册表统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_tools = len(self._mcp_tools)
        loaded_servers = len(self._loaded_servers)
        available_tools = sum(
            1 for tool in self._mcp_tools.values()
            if tool.is_available() if hasattr(tool, 'is_available') else True
        )

        server_stats = {}
        for server_name, tool_names in self._mcp_tools_by_server.items():
            server_tools = [
                self._mcp_tools[name] for name in tool_names
                if name in self._mcp_tools
            ]
            server_stats[server_name] = {
                "total_tools": len(server_tools),
                "available_tools": sum(
                    1 for tool in server_tools
                    if tool.is_available() if hasattr(tool, 'is_available') else True
                )
            }

        return {
            "total_tools": total_tools,
            "available_tools": available_tools,
            "unavailable_tools": total_tools - available_tools,
            "loaded_servers": loaded_servers,
            "servers": server_stats
        }

    def set_auto_load(self, enabled: bool):
        """
        设置是否自动加载工具

        Args:
            enabled: 是否启用自动加载
        """
        self._auto_load_enabled = enabled
        logger.info(f"MCP工具自动加载已{'启用' if enabled else '禁用'}")

    def is_auto_load_enabled(self) -> bool:
        """
        检查是否启用自动加载

        Returns:
            bool: 是否启用自动加载
        """
        return self._auto_load_enabled


# 全局MCP注册表实例
mcp_registry = MCPRegistry()


class UnifiedToolManager:
    """统一工具管理器 - 同时支持LangChain和MCP工具"""

    def __init__(self):
        """初始化统一工具管理器"""
        self.mcp_registry = mcp_registry
        self.langchain_tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}

    def register_langchain_tool(self, tool: BaseTool, category: str = "langchain"):
        """
        注册LangChain工具

        Args:
            tool: LangChain工具
            category: 工具分类
        """
        if tool.name in self.langchain_tools:
            logger.warning(f"LangChain工具 {tool.name} 已存在，将被覆盖")

        self.langchain_tools[tool.name] = tool

        if category not in self._categories:
            self._categories[category] = []
        if tool.name not in self._categories[category]:
            self._categories[category].append(tool.name)

        logger.info(f"注册LangChain工具: {tool.name} (分类: {category})")

    async def load_mcp_tools(self, server_name: str = None) -> Dict[str, int]:
        """
        加载MCP工具

        Args:
            server_name: 服务器名称，None表示加载所有服务器

        Returns:
            Dict[str, int]: 加载结果
        """
        if server_name:
            tools = await self.mcp_registry.load_server_tools(server_name)
            return {server_name: len(tools)}
        else:
            return await self.mcp_registry.load_all_tools()

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        根据名称获取工具（优先返回LangChain工具）

        Args:
            name: 工具名称

        Returns:
            Optional[BaseTool]: 工具实例
        """
        # 优先返回LangChain工具
        if name in self.langchain_tools:
            return self.langchain_tools[name]

        # 然后查找MCP工具
        return self.mcp_registry.get_tool(name)

    def get_all_tools(self) -> List[BaseTool]:
        """
        获取所有工具

        Returns:
            List[BaseTool]: 所有工具列表
        """
        tools = []

        # 添加LangChain工具
        tools.extend(self.langchain_tools.values())

        # 添加MCP工具
        mcp_tools = self.mcp_registry.get_all_tools()
        tools.extend(mcp_tools)

        return tools

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """
        根据分类获取工具

        Args:
            category: 分类名称

        Returns:
            List[BaseTool]: 工具列表
        """
        tools = []

        # 获取分类下的LangChain工具
        tool_names = self._categories.get(category, [])
        for name in tool_names:
            if name in self.langchain_tools:
                tools.append(self.langchain_tools[name])

        # 添加MCP工具（MCP工具按服务器分组）
        if category.startswith("mcp_"):
            server_name = category[4:]  # 移除"mcp_"前缀
            tools.extend(self.mcp_registry.get_tools_by_server(server_name))

        return tools

    def search_tools(self, keyword: str) -> List[BaseTool]:
        """
        搜索工具

        Args:
            keyword: 搜索关键词

        Returns:
            List[BaseTool]: 匹配的工具列表
        """
        keyword = keyword.lower()
        matched_tools = []

        # 搜索LangChain工具
        for tool in self.langchain_tools.values():
            if (keyword in tool.name.lower() or
                keyword in tool.description.lower()):
                matched_tools.append(tool)

        # 搜索MCP工具
        mcp_tools = self.mcp_registry.search_tools(keyword)
        matched_tools.extend(mcp_tools)

        return matched_tools

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有工具信息

        Returns:
            Dict[str, Dict[str, Any]]: 工具信息字典
        """
        tools_info = {}

        # LangChain工具信息
        for name, tool in self.langchain_tools.items():
            tools_info[name] = {
                "name": tool.name,
                "description": tool.description,
                "type": "LangChain",
                "category": self._get_tool_category(name)
            }

        # MCP工具信息
        mcp_tools_info = self.mcp_registry.list_tools()
        tools_info.update(mcp_tools_info)

        return tools_info

    def _get_tool_category(self, tool_name: str) -> str:
        """
        获取工具的分类

        Args:
            tool_name: 工具名称

        Returns:
            str: 分类名称
        """
        for category, tool_names in self._categories.items():
            if tool_name in tool_names:
                return category
        return "uncategorized"

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统一工具管理器统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        langchain_stats = {
            "total_tools": len(self.langchain_tools),
            "categories": {
                category: len(tools)
                for category, tools in self._categories.items()
            }
        }

        mcp_stats = self.mcp_registry.get_stats()

        return {
            "langchain_tools": langchain_stats,
            "mcp_tools": mcp_stats,
            "total_tools": langchain_stats["total_tools"] + mcp_stats["total_tools"]
        }

    async def cleanup(self):
        """清理资源"""
        await self.mcp_registry.unload_all_tools()


# 全局统一工具管理器实例
unified_tool_manager = UnifiedToolManager()