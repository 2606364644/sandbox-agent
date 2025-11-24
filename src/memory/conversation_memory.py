"""
对话记忆模块
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from langchain_core.memory import BaseMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel
import json
import logging

logger = logging.getLogger(__name__)


class ConversationMetadata(BaseModel):
    """对话元数据"""
    conversation_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    topic: Optional[str] = None
    participants: List[str] = []
    tags: List[str] = []


class ConversationMemory(BaseMemory):
    """增强版对话记忆"""

    def __init__(
        self,
        conversation_id: Optional[str] = None,
        max_messages: Optional[int] = None,
        enable_persistence: bool = False,
        storage_path: Optional[str] = None
    ):
        """
        初始化对话记忆

        Args:
            conversation_id: 对话ID
            max_messages: 最大消息数量
            enable_persistence: 是否启用持久化
            storage_path: 存储路径
        """
        self.conversation_id = conversation_id or f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.max_messages = max_messages
        self.enable_persistence = enable_persistence
        self.storage_path = storage_path

        self.messages: List[BaseMessage] = []
        self.metadata = ConversationMetadata(
            conversation_id=self.conversation_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            message_count=0,
            participants=["user", "assistant"]
        )

        # 记忆键
        self.memory_key = "chat_history"

        # 如果启用持久化，尝试加载现有记忆
        if self.enable_persistence and self.storage_path:
            self.load()

    @property
    def memory_variables(self) -> List[str]:
        """返回记忆变量列表"""
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """加载记忆变量"""
        return {self.memory_key: self.messages}

    def save_context(self, inputs: Dict[str, str], outputs: Dict[str, str]) -> None:
        """保存对话上下文"""
        # 提取输入消息
        input_text = inputs.get("input", "")
        if input_text:
            self.add_user_message(input_text)

        # 提取输出消息
        output_text = outputs.get("output", "") or outputs.get("text", "")
        if output_text:
            self.add_ai_message(output_text)

        # 更新元数据
        self.metadata.updated_at = datetime.now()
        self.metadata.message_count = len(self.messages)

        # 持久化
        if self.enable_persistence and self.storage_path:
            self.save()

    def add_user_message(self, message: str) -> None:
        """添加用户消息"""
        self.messages.append(HumanMessage(content=message))
        self._trim_if_needed()

    def add_ai_message(self, message: str) -> None:
        """添加AI消息"""
        self.messages.append(AIMessage(content=message))
        self._trim_if_needed()

    def add_message(self, message: BaseMessage) -> None:
        """添加通用消息"""
        self.messages.append(message)
        self._trim_if_needed()

    def _trim_if_needed(self) -> None:
        """如果需要，裁剪消息列表"""
        if self.max_messages and len(self.messages) > self.max_messages:
            # 保留最近的max_messages条消息
            self.messages = self.messages[-self.max_messages:]
            logger.info(f"记忆已裁剪，保留最近的 {self.max_messages} 条消息")

    def clear(self) -> None:
        """清空记忆"""
        self.messages.clear()
        self.metadata.updated_at = datetime.now()
        self.metadata.message_count = 0

        if self.enable_persistence and self.storage_path:
            self.save()

        logger.info("对话记忆已清空")

    def get_recent_messages(self, count: int = 5) -> List[BaseMessage]:
        """获取最近的消息"""
        return self.messages[-count:] if self.messages else []

    def search_messages(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索包含关键词的消息"""
        results = []
        for i, message in enumerate(self.messages):
            if keyword.lower() in message.content.lower():
                results.append({
                    "index": i,
                    "type": message.__class__.__name__,
                    "content": message.content,
                    "timestamp": self._get_message_timestamp(message)
                })
        return results

    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取对话摘要"""
        if not self.messages:
            return {
                "conversation_id": self.conversation_id,
                "message_count": 0,
                "duration": 0,
                "summary": "暂无对话记录"
            }

        # 计算对话持续时间（分钟）
        duration = (self.metadata.updated_at - self.metadata.created_at).total_seconds() / 60

        # 生成简单摘要
        user_messages = [msg for msg in self.messages if isinstance(msg, HumanMessage)]
        ai_messages = [msg for msg in self.messages if isinstance(msg, AIMessage)]

        return {
            "conversation_id": self.conversation_id,
            "message_count": len(self.messages),
            "user_message_count": len(user_messages),
            "ai_message_count": len(ai_messages),
            "duration_minutes": round(duration, 2),
            "created_at": self.metadata.created_at.isoformat(),
            "updated_at": self.metadata.updated_at.isoformat(),
            "topic": self.metadata.topic,
            "participants": self.metadata.participants,
            "tags": self.metadata.tags
        }

    def set_topic(self, topic: str) -> None:
        """设置对话主题"""
        self.metadata.topic = topic
        self.metadata.updated_at = datetime.now()
        if self.enable_persistence and self.storage_path:
            self.save()

    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag not in self.metadata.tags:
            self.metadata.tags.append(tag)
            self.metadata.updated_at = datetime.now()
            if self.enable_persistence and self.storage_path:
                self.save()

    def remove_tag(self, tag: str) -> None:
        """移除标签"""
        if tag in self.metadata.tags:
            self.metadata.tags.remove(tag)
            self.metadata.updated_at = datetime.now()
            if self.enable_persistence and self.storage_path:
                self.save()

    def export_conversation(self, file_path: str) -> None:
        """导出对话历史"""
        try:
            export_data = {
                "metadata": {
                    "conversation_id": self.metadata.conversation_id,
                    "created_at": self.metadata.created_at.isoformat(),
                    "updated_at": self.metadata.updated_at.isoformat(),
                    "topic": self.metadata.topic,
                    "participants": self.metadata.participants,
                    "tags": self.metadata.tags
                },
                "messages": [
                    {
                        "type": msg.__class__.__name__,
                        "content": msg.content,
                        "timestamp": self._get_message_timestamp(msg)
                    }
                    for msg in self.messages
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            logger.info(f"对话已导出到: {file_path}")

        except Exception as e:
            logger.error(f"导出对话时出错: {str(e)}")
            raise

    def import_conversation(self, file_path: str) -> None:
        """导入对话历史"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # 导入元数据
            metadata = import_data.get("metadata", {})
            self.metadata.topic = metadata.get("topic")
            self.metadata.participants = metadata.get("participants", ["user", "assistant"])
            self.metadata.tags = metadata.get("tags", [])

            # 导入消息
            self.messages.clear()
            for msg_data in import_data.get("messages", []):
                msg_type = msg_data.get("type")
                content = msg_data.get("content")

                if msg_type == "HumanMessage":
                    self.messages.append(HumanMessage(content=content))
                elif msg_type == "AIMessage":
                    self.messages.append(AIMessage(content=content))

            # 更新统计信息
            self.metadata.updated_at = datetime.now()
            self.metadata.message_count = len(self.messages)

            logger.info(f"对话已从 {file_path} 导入")

        except Exception as e:
            logger.error(f"导入对话时出错: {str(e)}")
            raise

    def save(self) -> None:
        """保存记忆到文件"""
        if not self.storage_path:
            return

        try:
            os.makedirs(self.storage_path, exist_ok=True)
            file_path = os.path.join(self.storage_path, f"{self.conversation_id}.json")

            data = {
                "metadata": self.metadata.dict(),
                "messages": [
                    {
                        "type": msg.__class__.__name__,
                        "content": msg.content
                    }
                    for msg in self.messages
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存记忆时出错: {str(e)}")

    def load(self) -> None:
        """从文件加载记忆"""
        if not self.storage_path:
            return

        try:
            file_path = os.path.join(self.storage_path, f"{self.conversation_id}.json")

            if not os.path.exists(file_path):
                logger.info(f"记忆文件不存在: {file_path}")
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载元数据
            metadata_data = data.get("metadata", {})
            self.metadata = ConversationMetadata(**metadata_data)

            # 加载消息
            self.messages.clear()
            for msg_data in data.get("messages", []):
                msg_type = msg_data.get("type")
                content = msg_data.get("content")

                if msg_type == "HumanMessage":
                    self.messages.append(HumanMessage(content=content))
                elif msg_type == "AIMessage":
                    self.messages.append(AIMessage(content=content))

            logger.info(f"记忆已从 {file_path} 加载")

        except Exception as e:
            logger.error(f"加载记忆时出错: {str(e)}")

    def _get_message_timestamp(self, message: BaseMessage) -> Optional[str]:
        """获取消息时间戳"""
        # 这里可以根据实际需求实现时间戳记录
        return None