"""
MCP工具适配器 - 将MCP工具适配为LangChain工具
"""
import asyncio
from typing import Dict, Any, Optional, List, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import logging

from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


def create_dynamic_pydantic_model(tool_schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    根据MCP工具模式动态创建Pydantic模型

    Args:
        tool_schema: MCP工具模式

    Returns:
        Type[BaseModel]: 动态创建的Pydantic模型
    """
    properties = tool_schema.get("inputSchema", {}).get("properties", {})
    required_fields = tool_schema.get("inputSchema", {}).get("required", [])

    # 创建字段字典
    fields = {}
    for field_name, field_info in properties.items():
        field_type = str
        field_description = field_info.get("description", "")
        default_value = field_info.get("default", Field(... if field_name in required_fields else None))

        # 处理不同的数据类型
        json_type = field_info.get("type", "string")
        if json_type == "string":
            field_type = str
        elif json_type == "number":
            field_type = float
        elif json_type == "integer":
            field_type = int
        elif json_type == "boolean":
            field_type = bool
        elif json_type == "array":
            field_type = List
        elif json_type == "object":
            field_type = Dict[str, Any]

        # 创建字段
        if field_name in required_fields:
            fields[field_name] = (field_type, Field(..., description=field_description))
        else:
            fields[field_name] = (field_type, Field(default_value, description=field_description))

    # 动态创建模型类
    model_name = f"{tool_schema.get('name', 'Tool')}Input"
    return type(model_name, (BaseModel,), fields)


class MCPToolAdapter(BaseTool):
    """MCP工具适配器 - 将MCP工具包装为LangChain工具"""

    def __init__(
        self,
        mcp_client: MCPClient,
        tool_schema: Dict[str, Any],
        **kwargs
    ):
        """
        初始化MCP工具适配器

        Args:
            mcp_client: MCP客户端实例
            tool_schema: MCP工具模式
            **kwargs: 其他参数
        """
        self.mcp_client = mcp_client
        self.tool_schema = tool_schema

        # 设置工具基本信息
        name = tool_schema.get("name", "mcp_tool")
        description = tool_schema.get("description", "MCP工具")

        # 创建动态参数模式
        try:
            self.args_schema = create_dynamic_pydantic_model(tool_schema)
        except Exception as e:
            logger.warning(f"创建参数模式失败，使用默认模式: {str(e)}")
            self.args_schema = BaseModel

        # 初始化LangChain工具
        super().__init__(
            name=name,
            description=description,
            args_schema=self.args_schema,
            **kwargs
        )

    def _run(self, **kwargs) -> str:
        """
        同步执行MCP工具

        Args:
            **kwargs: 工具参数

        Returns:
            str: 执行结果
        """
        # 转换为异步执行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._arun(**kwargs))
        finally:
            loop.close()

    async def _arun(self, **kwargs) -> str:
        """
        异步执行MCP工具

        Args:
            **kwargs: 工具参数

        Returns:
            str: 执行结果
        """
        try:
            # 检查MCP客户端是否存活
            if not self.mcp_client.is_alive():
                raise ConnectionError("MCP客户端未连接")

            # 调用MCP工具
            result = await self.mcp_client.call_tool(
                name=self.name,
                arguments=kwargs
            )

            # 处理结果
            if "content" in result:
                content_list = result["content"]
                if isinstance(content_list, list) and content_list:
                    # 合并多个内容块
                    content_parts = []
                    for content_item in content_list:
                        if isinstance(content_item, dict) and "text" in content_item:
                            content_parts.append(content_item["text"])
                        elif isinstance(content_item, str):
                            content_parts.append(content_item)
                    return "\n".join(content_parts)
                elif isinstance(content_list, dict) and "text" in content_list:
                    return content_list["text"]
                elif isinstance(content_list, str):
                    return content_list

            return "工具执行完成，但未返回内容"

        except Exception as e:
            error_msg = f"MCP工具 {self.name} 执行失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def get_tool_schema(self) -> Dict[str, Any]:
        """
        获取原始MCP工具模式

        Returns:
            Dict[str, Any]: MCP工具模式
        """
        return self.tool_schema.copy()

    def is_available(self) -> bool:
        """
        检查工具是否可用

        Returns:
            bool: 是否可用
        """
        return self.mcp_client.is_alive()

    def get_mcp_info(self) -> Dict[str, Any]:
        """
        获取MCP工具信息

        Returns:
            Dict[str, Any]: MCP工具信息
        """
        return {
            "name": self.name,
            "description": self.description,
            "mcp_server": getattr(self.mcp_client, 'server_name', 'unknown'),
            "tool_schema": self.tool_schema,
            "available": self.is_available()
        }


class MCPServerToolCollection:
    """MCP服务器工具集合"""

    def __init__(self, mcp_client: MCPClient, server_name: str = None):
        """
        初始化MCP服务器工具集合

        Args:
            mcp_client: MCP客户端实例
            server_name: 服务器名称
        """
        self.mcp_client = mcp_client
        self.server_name = server_name or "unknown"
        self._tools_cache: Optional[List[MCPToolAdapter]] = None
        self._tools_dict: Dict[str, MCPToolAdapter] = {}

    async def load_tools(self) -> List[MCPToolAdapter]:
        """
        加载MCP服务器上的所有工具

        Returns:
            List[MCPToolAdapter]: 工具适配器列表
        """
        if self._tools_cache is not None:
            return self._tools_cache

        try:
            # 获取工具列表
            tool_schemas = await self.mcp_client.list_tools()

            # 创建工具适配器
            tools = []
            for tool_schema in tool_schemas:
                try:
                    adapter = MCPToolAdapter(
                        mcp_client=self.mcp_client,
                        tool_schema=tool_schema
                    )
                    tools.append(adapter)
                    self._tools_dict[adapter.name] = adapter
                    logger.info(f"加载MCP工具: {adapter.name}")
                except Exception as e:
                    logger.error(f"加载MCP工具失败 {tool_schema.get('name', 'unknown')}: {str(e)}")

            self._tools_cache = tools
            logger.info(f"从MCP服务器 {self.server_name} 加载了 {len(tools)} 个工具")
            return tools

        except Exception as e:
            logger.error(f"加载MCP服务器 {self.server_name} 工具失败: {str(e)}")
            return []

    def get_tools(self) -> List[MCPToolAdapter]:
        """
        获取工具列表

        Returns:
            List[MCPToolAdapter]: 工具适配器列表
        """
        return self._tools_cache or []

    def get_tool(self, name: str) -> Optional[MCPToolAdapter]:
        """
        根据名称获取工具

        Args:
            name: 工具名称

        Returns:
            Optional[MCPToolAdapter]: 工具适配器
        """
        return self._tools_dict.get(name)

    def reload_tools(self) -> List[MCPToolAdapter]:
        """
        重新加载工具

        Returns:
            List[MCPToolAdapter]: 工具适配器列表
        """
        self._tools_cache = None
        self._tools_dict.clear()
        # 这里需要在异步上下文中调用
        return []

    def get_server_info(self) -> Dict[str, Any]:
        """
        获取服务器信息

        Returns:
            Dict[str, Any]: 服务器信息
        """
        return {
            "server_name": self.server_name,
            "tool_count": len(self._tools_cache) if self._tools_cache else 0,
            "is_alive": self.mcp_client.is_alive() if hasattr(self.mcp_client, 'is_alive') else True,
            "available_tools": [tool.name for tool in (self._tools_cache or [])]
        }