"""
MCP服务器管理器
"""
import asyncio
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import json
import yaml
import logging

from .mcp_client import MCPClient
from .mcp_tool_adapter import MCPServerToolCollection

logger = logging.getLogger(__name__)


class MCPServerConfig:
    """MCP服务器配置"""

    def __init__(
        self,
        name: str,
        command: List[str],
        description: str = "",
        auto_start: bool = True,
        timeout: int = 30,
        retry_count: int = 3
    ):
        """
        初始化MCP服务器配置

        Args:
            name: 服务器名称
            command: 启动命令列表
            description: 服务器描述
            auto_start: 是否自动启动
            timeout: 启动超时时间（秒）
            retry_count: 重试次数
        """
        self.name = name
        self.command = command
        self.description = description
        self.auto_start = auto_start
        self.timeout = timeout
        self.retry_count = retry_count

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "command": self.command,
            "description": self.description,
            "auto_start": self.auto_start,
            "timeout": self.timeout,
            "retry_count": self.retry_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPServerConfig':
        """从字典创建配置"""
        return cls(**data)


class MCPServerManager:
    """MCP服务器管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化MCP服务器管理器

        Args:
            config_file: 配置文件路径
        """
        self.servers: Dict[str, MCPServerConfig] = {}
        self.clients: Dict[str, MCPClient] = {}
        self.tool_collections: Dict[str, MCPServerToolCollection] = {}
        self.config_file = config_file

        if config_file:
            self.load_config(config_file)

        # 加载默认配置
        self._load_default_servers()

    def _load_default_servers(self):
        """加载默认服务器配置"""
        # 示例：文件系统MCP服务器
        self.register_server(MCPServerConfig(
            name="filesystem",
            command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            description="文件系统访问",
            auto_start=False  # 默认不自动启动，需要用户明确启用
        ))

        # 示例：GitHub MCP服务器
        self.register_server(MCPServerConfig(
            name="github",
            command=["npx", "-y", "@modelcontextprotocol/server-github"],
            description="GitHub集成",
            auto_start=False
        ))

        # 示例：Google Drive MCP服务器
        self.register_server(MCPServerConfig(
            name="gdrive",
            command=["npx", "-y", "@modelcontextprotocol/server-gdrive"],
            description="Google Drive集成",
            auto_start=False
        ))

    def register_server(self, server_config: MCPServerConfig):
        """
        注册MCP服务器配置

        Args:
            server_config: 服务器配置
        """
        self.servers[server_config.name] = server_config
        logger.info(f"注册MCP服务器: {server_config.name}")

    def unregister_server(self, name: str):
        """
        注销MCP服务器

        Args:
            name: 服务器名称
        """
        if name in self.servers:
            del self.servers[name]
            # 如果服务器正在运行，先停止它
            if name in self.clients:
                asyncio.create_task(self.stop_server(name))
            logger.info(f"注销MCP服务器: {name}")

    def load_config(self, config_file: str):
        """
        从文件加载配置

        Args:
            config_file: 配置文件路径
        """
        config_path = Path(config_file)
        if not config_path.exists():
            logger.warning(f"MCP配置文件不存在: {config_file}")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            servers_data = data.get('servers', {})
            for server_name, server_data in servers_data.items():
                server_config = MCPServerConfig.from_dict(server_data)
                self.register_server(server_config)

            logger.info(f"从 {config_file} 加载了 {len(servers_data)} 个MCP服务器配置")

        except Exception as e:
            logger.error(f"加载MCP配置文件失败: {str(e)}")

    def save_config(self, config_file: str = None):
        """
        保存配置到文件

        Args:
            config_file: 配置文件路径
        """
        file_path = Path(config_file or self.config_file or "mcp_servers.json")
        if not file_path:
            raise ValueError("未指定配置文件路径")

        try:
            config_data = {
                "servers": {
                    name: server_config.to_dict()
                    for name, server_config in self.servers.items()
                }
            }

            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.safe_dump(config_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"MCP服务器配置已保存到: {file_path}")

        except Exception as e:
            logger.error(f"保存MCP配置文件失败: {str(e)}")

    async def start_server(self, name: str) -> bool:
        """
        启动MCP服务器

        Args:
            name: 服务器名称

        Returns:
            bool: 启动是否成功
        """
        if name not in self.servers:
            logger.error(f"未知的MCP服务器: {name}")
            return False

        if name in self.clients and self.clients[name].is_alive():
            logger.info(f"MCP服务器 {name} 已在运行")
            return True

        server_config = self.servers[name]

        try:
            # 创建客户端
            client = MCPClient(
                server_command=server_config.command,
                server_name=server_config.name
            )

            # 启动服务器（带重试）
            for attempt in range(server_config.retry_count):
                try:
                    success = await asyncio.wait_for(
                        client.start(),
                        timeout=server_config.timeout
                    )
                    if success:
                        self.clients[name] = client
                        # 创建工具集合
                        self.tool_collections[name] = MCPServerToolCollection(
                            mcp_client=client,
                            server_name=name
                        )
                        logger.info(f"MCP服务器 {name} 启动成功")
                        return True
                except asyncio.TimeoutError:
                    logger.warning(f"MCP服务器 {name} 启动超时，尝试 {attempt + 1}/{server_config.retry_count}")
                    if client:
                        await client.stop()
                except Exception as e:
                    logger.warning(f"MCP服务器 {name} 启动失败，尝试 {attempt + 1}/{server_config.retry_count}: {str(e)}")
                    if client:
                        await client.stop()

            logger.error(f"MCP服务器 {name} 启动失败，已达到最大重试次数")
            return False

        except Exception as e:
            logger.error(f"启动MCP服务器 {name} 时发生错误: {str(e)}")
            return False

    async def stop_server(self, name: str) -> bool:
        """
        停止MCP服务器

        Args:
            name: 服务器名称

        Returns:
            bool: 停止是否成功
        """
        if name not in self.clients:
            logger.warning(f"MCP服务器 {name} 未运行")
            return True

        try:
            await self.clients[name].stop()
            del self.clients[name]
            if name in self.tool_collections:
                del self.tool_collections[name]
            logger.info(f"MCP服务器 {name} 已停止")
            return True

        except Exception as e:
            logger.error(f"停止MCP服务器 {name} 失败: {str(e)}")
            return False

    async def restart_server(self, name: str) -> bool:
        """
        重启MCP服务器

        Args:
            name: 服务器名称

        Returns:
            bool: 重启是否成功
        """
        await self.stop_server(name)
        return await self.start_server(name)

    async def start_all_auto_servers(self) -> Dict[str, bool]:
        """
        启动所有自动启动的服务器

        Returns:
            Dict[str, bool]: 启动结果
        """
        results = {}
        for name, config in self.servers.items():
            if config.auto_start:
                results[name] = await self.start_server(name)
        return results

    async def stop_all_servers(self) -> Dict[str, bool]:
        """
        停止所有服务器

        Returns:
            Dict[str, bool]: 停止结果
        """
        results = {}
        for name in list(self.clients.keys()):
            results[name] = await self.stop_server(name)
        return results

    def get_client(self, name: str) -> Optional[MCPClient]:
        """
        获取MCP客户端

        Args:
            name: 服务器名称

        Returns:
            Optional[MCPClient]: MCP客户端
        """
        return self.clients.get(name)

    def get_tool_collection(self, name: str) -> Optional[MCPServerToolCollection]:
        """
        获取工具集合

        Args:
            name: 服务器名称

        Returns:
            Optional[MCPServerToolCollection]: 工具集合
        """
        return self.tool_collections.get(name)

    def list_servers(self) -> List[Dict[str, Any]]:
        """
        列出所有服务器

        Returns:
            List[Dict[str, Any]]: 服务器信息列表
        """
        servers_info = []
        for name, config in self.servers.items():
            info = config.to_dict()
            info['status'] = 'running' if name in self.clients and self.clients[name].is_alive() else 'stopped'
            info['tools_count'] = len(self.tool_collections[name].get_tools()) if name in self.tool_collections else 0
            servers_info.append(info)
        return servers_info

    def get_server_stats(self) -> Dict[str, Any]:
        """
        获取服务器统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_servers = len(self.servers)
        running_servers = sum(1 for name in self.clients if self.clients[name].is_alive())
        total_tools = sum(len(collection.get_tools()) for collection in self.tool_collections.values())

        return {
            "total_servers": total_servers,
            "running_servers": running_servers,
            "stopped_servers": total_servers - running_servers,
            "total_tools": total_tools,
            "servers": {
                name: {
                    "status": "running" if self.clients[name].is_alive() else "stopped",
                    "tools_count": len(self.tool_collections[name].get_tools()) if name in self.tool_collections else 0
                }
                for name in self.servers
            }
        }

    async def cleanup(self):
        """清理资源"""
        await self.stop_all_servers()


# 全局MCP服务器管理器实例
mcp_server_manager = MCPServerManager()