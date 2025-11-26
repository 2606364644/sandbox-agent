from typing import List, Dict

from langchain.messages import HumanMessage, AIMessage


class BaseAgent:
    def __init__(self):
        # 对话历史
        self.chat_history = []

    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        history = []
        for msg in self.chat_history:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        return history

    def clear_history(self):
        """清空对话历史"""
        self.chat_history = []