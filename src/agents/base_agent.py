"""
基础Agent类模块
"""
from typing import List, Dict, Any, Optional, Union, Callable
from abc import ABC, abstractmethod
from langchain_core.agents import AgentExecutor
from langchain_core.memory import BaseMemory
from langchain_core.tools import BaseTool
from langchain_core.messages import BaseMessage
from src.models.llm_configs import create_llm, LLMProvider
from src.memory.memory_manager import MemoryManager
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """基础Agent抽象类"""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        memory: Optional[BaseMemory] = None,
        verbose: bool = True,
        max_iterations: int = 10,
        early_stopping_method: str = "generate",
        **llm_kwargs
    ):
        """
        初始化基础Agent

        Args:
            llm_provider: LLM提供商
            model: 模型名称
            tools: 工具列表
            memory: 记忆组件
            verbose: 是否启用详细日志
            max_iterations: 最大迭代次数
            early_stopping_method: 早期停止方法
            **llm_kwargs: LLM参数
        """
        self.llm = create_llm(llm_provider, model, **llm_kwargs)
        self.tools = tools or []
        self.memory = memory or self._create_default_memory()
        self.verbose = verbose
        self.max_iterations = max_iterations
        self.early_stopping_method = early_stopping_method

        # Agent执行器
        self.agent_executor: Optional[AgentExecutor] = None
        self._setup_agent()

    @abstractmethod
    def _setup_agent(self):
        """设置Agent - 子类必须实现"""
        pass

    @abstractmethod
    def _create_default_memory(self) -> BaseMemory:
        """创建默认记忆组件 - 子类必须实现"""
        pass

    def add_tool(self, tool: BaseTool) -> None:
        """添加工具"""
        self.tools.append(tool)
        if self.agent_executor:
            self.agent_executor.tools = self.tools

    def remove_tool(self, tool_name: str) -> None:
        """移除工具"""
        self.tools = [tool for tool in self.tools if tool.name != tool_name]
        if self.agent_executor:
            self.agent_executor.tools = self.tools

    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有工具"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "type": tool.__class__.__name__
            }
            for tool in self.tools
        ]

    def run(
        self,
        input_text: str,
        callbacks: Optional[List[Callable]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        运行Agent

        Args:
            input_text: 输入文本
            callbacks: 回调函数列表
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"开始执行Agent，输入: {input_text}")

            if not self.agent_executor:
                raise ValueError("Agent执行器未初始化")

            result = self.agent_executor.invoke(
                {
                    "input": input_text,
                    "chat_history": self.memory.chat_memory.messages if hasattr(self.memory, 'chat_memory') else []
                },
                callbacks=callbacks,
                **kwargs
            )

            logger.info(f"Agent执行完成，结果: {result}")
            return result

        except Exception as e:
            logger.error(f"Agent执行出错: {str(e)}")
            raise

    async def arun(
        self,
        input_text: str,
        callbacks: Optional[List[Callable]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        异步运行Agent

        Args:
            input_text: 输入文本
            callbacks: 回调函数列表
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"开始异步执行Agent，输入: {input_text}")

            if not self.agent_executor:
                raise ValueError("Agent执行器未初始化")

            result = await self.agent_executor.ainvoke(
                {
                    "input": input_text,
                    "chat_history": self.memory.chat_memory.messages if hasattr(self.memory, 'chat_memory') else []
                },
                callbacks=callbacks,
                **kwargs
            )

            logger.info(f"Agent异步执行完成，结果: {result}")
            return result

        except Exception as e:
            logger.error(f"Agent异步执行出错: {str(e)}")
            raise

    def clear_memory(self) -> None:
        """清空记忆"""
        if hasattr(self.memory, 'clear'):
            self.memory.clear()
        logger.info("Agent记忆已清空")

    def get_memory_summary(self) -> Dict[str, Any]:
        """获取记忆摘要"""
        if hasattr(self.memory, 'chat_memory'):
            return {
                "message_count": len(self.memory.chat_memory.messages),
                "last_message": self.memory.chat_memory.messages[-1].content if self.memory.chat_memory.messages else None
            }
        return {"message_count": 0, "last_message": None}

    def save_conversation(self, file_path: str) -> None:
        """保存对话历史"""
        if hasattr(self.memory, 'chat_memory'):
            import json
            conversation = [
                {
                    "type": msg.__class__.__name__,
                    "content": msg.content
                }
                for msg in self.memory.chat_memory.messages
            ]

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, ensure_ascii=False, indent=2)

            logger.info(f"对话历史已保存到: {file_path}")

    def load_conversation(self, file_path: str) -> None:
        """加载对话历史"""
        if hasattr(self.memory, 'chat_memory'):
            import json
            from langchain_core.messages import HumanMessage, AIMessage

            with open(file_path, 'r', encoding='utf-8') as f:
                conversation = json.load(f)

            for msg in conversation:
                if msg['type'] == 'HumanMessage':
                    self.memory.chat_memory.add_user_message(msg['content'])
                elif msg['type'] == 'AIMessage':
                    self.memory.chat_memory.add_ai_message(msg['content'])

            logger.info(f"对话历史已从 {file_path} 加载")

    def get_stats(self) -> Dict[str, Any]:
        """获取Agent统计信息"""
        return {
            "llm_provider": self.llm.__class__.__name__,
            "tool_count": len(self.tools),
            "memory_type": self.memory.__class__.__name__,
            "max_iterations": self.max_iterations,
            "verbose": self.verbose
        }