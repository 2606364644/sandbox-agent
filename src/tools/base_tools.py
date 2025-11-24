"""
基础工具模块
"""
from typing import Dict, Any, Optional, Type, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ToolInput(BaseModel):
    """工具输入基类"""
    pass


class BaseCustomTool(BaseTool, ABC):
    """自定义工具基类"""

    name: str
    description: str
    args_schema: Type[BaseModel] = ToolInput

    def __init__(self, **kwargs):
        """初始化工具"""
        super().__init__(**kwargs)
        self._setup()

    @abstractmethod
    def _setup(self):
        """工具初始化设置 - 子类必须实现"""
        pass

    def _run(self, **kwargs) -> str:
        """
        同步执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            str: 执行结果
        """
        try:
            return self._execute(**kwargs)
        except Exception as e:
            error_msg = f"工具 {self.name} 执行出错: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def _arun(self, **kwargs) -> str:
        """
        异步执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            str: 执行结果
        """
        try:
            return await self._execute_async(**kwargs)
        except Exception as e:
            error_msg = f"工具 {self.name} 异步执行出错: {str(e)}"
            logger.error(error_msg)
            return error_msg

    @abstractmethod
    def _execute(self, **kwargs) -> str:
        """具体执行逻辑 - 子类必须实现"""
        pass

    async def _execute_async(self, **kwargs) -> str:
        """
        异步执行逻辑 - 子类可以重写此方法

        默认行为是调用同步方法
        """
        return self._execute(**kwargs)

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        验证输入数据

        Args:
            input_data: 输入数据

        Returns:
            bool: 验证结果
        """
        try:
            self.args_schema(**input_data)
            return True
        except Exception as e:
            logger.warning(f"输入验证失败: {str(e)}")
            return False

    def get_tool_info(self) -> Dict[str, Any]:
        """
        获取工具信息

        Returns:
            Dict[str, Any]: 工具信息
        """
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": self.args_schema.__name__,
            "type": self.__class__.__name__
        }


class ToolRegistry:
    """工具注册器 - 管理工具的注册和发现"""

    def __init__(self):
        """初始化工具注册器"""
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}

    def register_tool(self, tool: BaseTool, category: str = "general") -> None:
        """
        注册工具

        Args:
            tool: 工具实例
            category: 工具分类
        """
        if tool.name in self._tools:
            logger.warning(f"工具 {tool.name} 已存在，将被覆盖")

        self._tools[tool.name] = tool

        if category not in self._categories:
            self._categories[category] = []
        if tool.name not in self._categories[category]:
            self._categories[category].append(tool.name)

        logger.info(f"工具 {tool.name} 已注册到分类 {category}")

    def unregister_tool(self, tool_name: str) -> None:
        """
        注销工具

        Args:
            tool_name: 工具名称
        """
        if tool_name in self._tools:
            del self._tools[tool_name]

            # 从分类中移除
            for category, tools in self._categories.items():
                if tool_name in tools:
                    tools.remove(tool_name)

            logger.info(f"工具 {tool_name} 已注销")

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具实例

        Args:
            tool_name: 工具名称

        Returns:
            Optional[BaseTool]: 工具实例
        """
        return self._tools.get(tool_name)

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """
        根据分类获取工具

        Args:
            category: 分类名称

        Returns:
            List[BaseTool]: 工具列表
        """
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_all_tools(self) -> List[BaseTool]:
        """
        获取所有工具

        Returns:
            List[BaseTool]: 所有工具列表
        """
        return list(self._tools.values())

    def list_tools(self) -> Dict[str, Dict[str, str]]:
        """
        列出所有工具

        Returns:
            Dict[str, Dict[str, str]]: 工具信息字典
        """
        tools_info = {}
        for name, tool in self._tools.items():
            tools_info[name] = {
                "name": tool.name,
                "description": tool.description,
                "type": tool.__class__.__name__
            }
        return tools_info

    def list_categories(self) -> Dict[str, List[str]]:
        """
        列出所有分类及其工具

        Returns:
            Dict[str, List[str]]: 分类字典
        """
        return {category: tools[:] for category, tools in self._categories.items()}

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

        for tool in self._tools.values():
            if (keyword in tool.name.lower() or
                keyword in tool.description.lower()):
                matched_tools.append(tool)

        return matched_tools

    def get_stats(self) -> Dict[str, Any]:
        """
        获取注册器统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_tools": len(self._tools),
            "total_categories": len(self._categories),
            "categories": {
                category: len(tools)
                for category, tools in self._categories.items()
            }
        }


# 全局工具注册器实例
tool_registry = ToolRegistry()


def register_tool(tool: BaseTool, category: str = "general") -> None:
    """
    注册工具的便捷函数

    Args:
        tool: 工具实例
        category: 工具分类
    """
    tool_registry.register_tool(tool, category)


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """
    获取工具的便捷函数

    Args:
        tool_name: 工具名称

    Returns:
        Optional[BaseTool]: 工具实例
    """
    return tool_registry.get_tool(tool_name)


def get_all_tools() -> List[BaseTool]:
    """
    获取所有工具的便捷函数

    Returns:
        List[BaseTool]: 所有工具列表
    """
    return tool_registry.get_all_tools()