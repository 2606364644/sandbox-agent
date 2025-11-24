"""
对话式Agent模块
"""
from typing import List, Dict, Any, Optional
from langchain_core.agents import AgentExecutor
from langchain_core.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_functions_agent
from langchain_core.tools import BaseTool
from src.agents.base_agent import BaseAgent
from src.models.llm_configs import LLMProvider
import logging

logger = logging.getLogger(__name__)


class ConversationalAgent(BaseAgent):
    """对话式Agent - 支持多轮对话和工具调用"""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        system_message: Optional[str] = None,
        memory_key: str = "chat_history",
        input_key: str = "input",
        output_key: str = "output",
        **kwargs
    ):
        """
        初始化对话式Agent

        Args:
            llm_provider: LLM提供商
            model: 模型名称
            tools: 工具列表
            system_message: 系统消息
            memory_key: 记忆的键名
            input_key: 输入的键名
            output_key: 输出的键名
            **kwargs: 其他参数
        """
        self.system_message = system_message or self._get_default_system_message()
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key

        super().__init__(llm_provider, model, tools, **kwargs)

    def _get_default_system_message(self) -> str:
        """获取默认系统消息"""
        return """你是一个有帮助的AI助手，能够使用工具来回答问题和执行任务。

你有以下特点：
1. 你可以调用各种工具来获取信息或执行操作
2. 你会记住之前的对话内容，保持对话的连续性
3. 如果工具无法解决问题，你会根据自己的知识尽力回答
4. 你会以中文回答用户的问题
5. 你会礼貌、友好、专业地与用户交流

请在回答问题时尽可能详细和准确。"""

    def _setup_agent(self):
        """设置对话式Agent"""
        try:
            # 创建提示模板
            prompt = self._create_prompt_template()

            # 创建agent
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )

            # 创建执行器
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=self.memory,
                verbose=self.verbose,
                max_iterations=self.max_iterations,
                early_stopping_method=self.early_stopping_method,
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )

            logger.info("对话式Agent设置完成")

        except Exception as e:
            logger.error(f"设置对话式Agent时出错: {str(e)}")
            raise

    def _create_prompt_template(self):
        """创建提示模板"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_message),
            MessagesPlaceholder(variable_name=self.memory_key),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        return prompt

    def _create_default_memory(self) -> ConversationBufferMemory:
        """创建默认记忆组件"""
        return ConversationBufferMemory(
            memory_key=self.memory_key,
            return_messages=True
        )

    def set_system_message(self, message: str):
        """设置系统消息"""
        self.system_message = message
        # 重新设置agent以应用新的系统消息
        self._setup_agent()

    def get_conversation_context(self) -> Dict[str, Any]:
        """获取对话上下文"""
        if hasattr(self.memory, 'chat_memory'):
            messages = self.memory.chat_memory.messages
            return {
                "message_count": len(messages),
                "messages": [
                    {
                        "type": msg.__class__.__name__,
                        "content": msg.content
                    }
                    for msg in messages
                ]
            }
        return {"message_count": 0, "messages": []}

    def search_memory(self, keyword: str) -> List[Dict[str, str]]:
        """搜索记忆中的内容"""
        results = []
        if hasattr(self.memory, 'chat_memory'):
            messages = self.memory.chat_memory.messages
            for i, msg in enumerate(messages):
                if keyword.lower() in msg.content.lower():
                    results.append({
                        "index": i,
                        "type": msg.__class__.__name__,
                        "content": msg.content
                    })
        return results

    def summarize_conversation(self) -> str:
        """总结对话内容"""
        if not hasattr(self.memory, 'chat_memory') or not self.memory.chat_memory.messages:
            return "暂无对话记录"

        # 使用LLM来总结对话
        messages = self.memory.chat_memory.messages
        conversation_text = "\n".join([f"{msg.__class__.__name__}: {msg.content}" for msg in messages])

        summary_prompt = f"""
        请总结以下对话的主要内容：

        {conversation_text}

        请用中文简洁地总结对话的主题、关键信息和重要结论。
        """

        try:
            response = self.llm.invoke(summary_prompt)
            return response.content
        except Exception as e:
            logger.error(f"总结对话时出错: {str(e)}")
            return "无法生成对话摘要"