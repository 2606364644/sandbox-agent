"""
MCP集成模块 - 管理MCP相关功能
"""
from typing import List, Dict, Any, Optional
from src.tools.mcp import mcp_registry, mcp_server_manager, MCPToolLoader
import logging

logger = logging.getLogger(__name__)


class MCPIntegration:
    """
    MCP集成类 - 封装MCP相关功能
    """

    def __init__(self):
        """初始化MCP集成"""
        self._initialized = False
        self._active_servers: List[str] = []

    async def initialize(self, servers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        初始化MCP集成

        Args:
            servers: 要初始化的服务器列表

        Returns:
            Dict[str, Any]: 初始化结果
        """
        if self._initialized:
            return {"status": "already_initialized"}

        try:
            # 启动自动启动的服务器
            await mcp_server_manager.start_all_auto_servers()

            # 加载工具
            if servers:
                # 启动指定服务器
                results = {}
                for server_name in servers:
                    success = await mcp_server_manager.start_server(server_name)
                    if success:
                        tools = await mcp_registry.load_server_tools(server_name)
                        results[server_name] = len(tools)
                        self._active_servers.append(server_name)
            else:
                # 加载所有可用服务器的工具
                results = await mcp_registry.load_all_tools()
                self._active_servers = list(results.keys())

            self._initialized = True
            logger.info(f"MCP集成初始化完成，激活服务器: {self._active_servers}")

            return {
                "status": "success",
                "active_servers": self._active_servers,
                "tool_counts": results
            }

        except Exception as e:
            logger.error(f"MCP集成初始化失败: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def get_tools(self, servers: Optional[List[str]] = None) -> List:
        """
        获取MCP工具

        Args:
            servers: 指定的服务器列表

        Returns:
            List: 工具列表
        """
        if servers:
            tools = []
            for server_name in servers:
                tools.extend(mcp_registry.get_tools_by_server(server_name))
            return tools
        else:
            return mcp_registry.get_all_tools()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取MCP统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "initialized": self._initialized,
            "active_servers": self._active_servers.copy(),
            "registry_stats": mcp_registry.get_stats(),
            "server_manager_stats": mcp_server_manager.get_server_stats()
        }

    async def start_server(self, server_name: str) -> bool:
        """
        启动MCP服务器

        Args:
            server_name: 服务器名称

        Returns:
            bool: 启动是否成功
        """
        success = await mcp_server_manager.start_server(server_name)
        if success and server_name not in self._active_servers:
            self._active_servers.append(server_name)
        return success

    async def stop_server(self, server_name: str) -> bool:
        """
        停止MCP服务器

        Args:
            server_name: 服务器名称

        Returns:
            bool: 停止是否成功
        """
        success = await mcp_server_manager.stop_server(server_name)
        if success and server_name in self._active_servers:
            self._active_servers.remove(server_name)
        return success

    def list_available_servers(self) -> List[Dict[str, Any]]:
        """
        列出可用的MCP服务器

        Returns:
            List[Dict[str, Any]]: 服务器信息列表
        """
        return mcp_server_manager.list_servers()

    def get_server_tools(self, server_name: str) -> List:
        """
        获取指定服务器的工具

        Args:
            server_name: 服务器名称

        Returns:
            List: 工具列表
        """
        return mcp_registry.get_tools_by_server(server_name)

    async def cleanup(self):
        """清理MCP资源"""
        # 停止所有服务器
        await mcp_server_manager.stop_all_servers()

        # 清理注册表
        await mcp_registry.unload_all_tools()

        self._active_servers.clear()
        self._initialized = False

        logger.info("MCP集成资源已清理")