"""
记忆管理器模块
"""
from typing import Dict, Any, Optional, List
from langchain_core.memory import BaseMemory
from langchain_core.memory import (
    ConversationBufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryMemory,
    VectorStoreRetrieverMemory
)
from src.models.llm_configs import create_llm
import logging

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器 - 负责创建和管理不同类型的记忆组件"""

    def __init__(self, llm=None):
        """
        初始化记忆管理器

        Args:
            llm: 语言模型实例，用于需要LLM的记忆类型
        """
        self.llm = llm or create_llm()

    def create_buffer_memory(
        self,
        memory_key: str = "chat_history",
        return_messages: bool = True,
        input_key: str = "input",
        output_key: str = "output"
    ) -> ConversationBufferMemory:
        """
        创建对话缓冲记忆

        Args:
            memory_key: 记忆的键名
            return_messages: 是否返回消息对象
            input_key: 输入的键名
            output_key: 输出的键名

        Returns:
            ConversationBufferMemory: 对话缓冲记忆实例
        """
        memory = ConversationBufferMemory(
            memory_key=memory_key,
            return_messages=return_messages,
            input_key=input_key,
            output_key=output_key
        )
        logger.info("创建对话缓冲记忆")
        return memory

    def create_window_memory(
        self,
        window_size: int = 5,
        memory_key: str = "chat_history",
        return_messages: bool = True,
        input_key: str = "input",
        output_key: str = "output"
    ) -> ConversationBufferWindowMemory:
        """
        创建滑动窗口记忆

        Args:
            window_size: 窗口大小（保留最近的消息数量）
            memory_key: 记忆的键名
            return_messages: 是否返回消息对象
            input_key: 输入的键名
            output_key: 输出的键名

        Returns:
            ConversationBufferWindowMemory: 滑动窗口记忆实例
        """
        memory = ConversationBufferWindowMemory(
            k=window_size,
            memory_key=memory_key,
            return_messages=return_messages,
            input_key=input_key,
            output_key=output_key
        )
        logger.info(f"创建滑动窗口记忆，窗口大小: {window_size}")
        return memory

    def create_summary_memory(
        self,
        memory_key: str = "chat_history",
        return_messages: bool = True,
        input_key: str = "input",
        output_key: str = "output",
        prompt: Optional[str] = None
    ) -> ConversationSummaryMemory:
        """
        创建对话摘要记忆

        Args:
            memory_key: 记忆的键名
            return_messages: 是否返回消息对象
            input_key: 输入的键名
            output_key: 输出的键名
            prompt: 自定义摘要提示

        Returns:
            ConversationSummaryMemory: 对话摘要记忆实例
        """
        if prompt is None:
            prompt = """
            请总结以下对话内容，包括主要话题、关键信息和重要结论。
            请用中文简洁地总结对话。

            对话内容:
            {chat_history}

            新的对话:
            {input}

            请提供更新后的对话摘要：
            """

        memory = ConversationSummaryMemory(
            llm=self.llm,
            memory_key=memory_key,
            return_messages=return_messages,
            input_key=input_key,
            output_key=output_key,
            prompt=prompt
        )
        logger.info("创建对话摘要记忆")
        return memory

    def create_vector_memory(
        self,
        vector_store,
        retrieval_query: str = "",
        memory_key: str = "chat_history",
        input_key: str = "input",
        output_key: str = "output",
        k: int = 3
    ) -> VectorStoreRetrieverMemory:
        """
        创建向量检索记忆

        Args:
            vector_store: 向量存储实例
            retrieval_query: 检索查询模板
            memory_key: 记忆的键名
            input_key: 输入的键名
            output_key: 输出的键名
            k: 检索返回的相关记忆数量

        Returns:
            VectorStoreRetrieverMemory: 向量检索记忆实例
        """
        if retrieval_query == "":
            retrieval_query = """
            请检索与以下对话内容最相关的历史记忆：
            {input}
            """

        # 创建检索器
        retriever = vector_store.as_retriever(search_kwargs={"k": k})

        memory = VectorStoreRetrieverMemory(
            retriever=retriever,
            memory_key=memory_key,
            input_key=input_key,
            output_key=output_key,
            return_messages=True
        )
        logger.info(f"创建向量检索记忆，检索数量: {k}")
        return memory

    def get_memory_stats(self, memory: BaseMemory) -> Dict[str, Any]:
        """
        获取记忆统计信息

        Args:
            memory: 记忆实例

        Returns:
            Dict[str, Any]: 记忆统计信息
        """
        stats = {
            "memory_type": memory.__class__.__name__,
            "memory_keys": getattr(memory, 'memory_keys', []),
        }

        # 根据记忆类型添加特定统计
        if isinstance(memory, (ConversationBufferMemory, ConversationBufferWindowMemory)):
            if hasattr(memory, 'chat_memory') and memory.chat_memory:
                stats.update({
                    "message_count": len(memory.chat_memory.messages),
                    "has_messages": bool(memory.chat_memory.messages)
                })
            elif hasattr(memory, 'buffer'):
                stats.update({
                    "buffer_length": len(memory.buffer) if memory.buffer else 0,
                    "has_buffer": bool(memory.buffer)
                })

        elif isinstance(memory, ConversationBufferWindowMemory):
            stats["window_size"] = memory.k

        elif isinstance(memory, ConversationSummaryMemory):
            stats["has_summary"] = bool(memory.buffer)

        elif isinstance(memory, VectorStoreRetrieverMemory):
            stats.update({
                "retriever_type": memory.retriever.__class__.__name__,
                "search_kwargs": memory.retriever.search_kwargs
            })

        return stats

    def export_memory(self, memory: BaseMemory, file_path: str) -> None:
        """
        导出记忆到文件

        Args:
            memory: 记忆实例
            file_path: 导出文件路径
        """
        try:
            import json

            memory_data = {
                "memory_type": memory.__class__.__name__,
                "stats": self.get_memory_stats(memory),
                "content": {}
            }

            # 根据记忆类型导出内容
            if hasattr(memory, 'chat_memory') and memory.chat_memory:
                memory_data["content"]["messages"] = [
                    {
                        "type": msg.__class__.__name__,
                        "content": msg.content
                    }
                    for msg in memory.chat_memory.messages
                ]

            elif hasattr(memory, 'buffer'):
                memory_data["content"]["buffer"] = memory.buffer

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, ensure_ascii=False, indent=2)

            logger.info(f"记忆已导出到: {file_path}")

        except Exception as e:
            logger.error(f"导出记忆时出错: {str(e)}")
            raise

    def create_memory_from_config(self, config: Dict[str, Any]) -> BaseMemory:
        """
        根据配置创建记忆实例

        Args:
            config: 记忆配置

        Returns:
            BaseMemory: 记忆实例
        """
        memory_type = config.get("type", "buffer").lower()

        if memory_type == "buffer":
            return self.create_buffer_memory(**config.get("params", {}))
        elif memory_type == "window":
            return self.create_window_memory(**config.get("params", {}))
        elif memory_type == "summary":
            return self.create_summary_memory(**config.get("params", {}))
        elif memory_type == "vector":
            # 向量记忆需要额外的向量存储配置
            vector_store = config.get("vector_store")
            if not vector_store:
                raise ValueError("向量记忆需要提供vector_store配置")
            return self.create_vector_memory(
                vector_store=vector_store,
                **config.get("params", {})
            )
        else:
            raise ValueError(f"不支持的记忆类型: {memory_type}")