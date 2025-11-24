"""
Agent框架核心类 - 使用LangChain v1.0最新API
"""
import asyncio
from typing import List, Dict, Any, Optional
from src.agents.conversational_agent import create_conversational_agent, ModernConversationalAgent
from src.models.llm_configs import LLMProvider, create_llm
from src.memory.memory_manager import MemoryManager
from src.framework.tool_manager import ToolManager
from src.framework.mcp_integration import MCPIntegration
from src.utils.logger import get_logger, LogContext

logger = get_logger(__name__)


class AgentFramework:
    """
    Agent框架核心类 - 提供统一的Agent创建和管理接口

    这是真正的框架主类，负责整合Agent、工具、记忆等所有组件
    使用LangChain v1.0最新API和最佳实践
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        memory_type: str = "buffer",
        verbose: bool = True,
        use_modern_agents: bool = True
    ):
        """
        初始化Agent框架

        Args:
            llm_provider: LLM提供商
            model: 模型名称
            memory_type: 记忆类型
            verbose: 是否启用详细日志
            use_modern_agents: 是否使用现代化Agent
        """
        self.llm_provider = llm_provider or LLMProvider.OPENAI
        self.model = model or "gpt-3.5-turbo"
        self.memory_type = memory_type
        self.verbose = verbose
        self.use_modern_agents = use_modern_agents

        # 初始化核心组件
        self.memory_manager = MemoryManager()
        self.tool_manager = ToolManager()
        self.mcp_integration = MCPIntegration()

        # 框架状态
        self._initialized = False
        self._agents: Dict[str, ModernConversationalAgent] = {}

        logger.info("Agent框架核心初始化完成")

    def create_agent(
        self,
        agent_id: str,
        tools: Optional[List] = None,
        enable_mcp: bool = False,
        mcp_servers: Optional[List[str]] = None,
        system_message: Optional[str] = None,
        agent_type: str = "openai-tools",
        **kwargs
    ) -> ModernConversationalAgent:
        """
        创建Agent实例（使用LangChain v1.0最新API）

        Args:
            agent_id: Agent唯一标识
            tools: 自定义工具列表
            enable_mcp: 是否启用MCP工具
            mcp_servers: 指定的MCP服务器
            system_message: 系统消息
            agent_type: Agent类型 ("openai-tools", "xml", "react")
            **kwargs: 其他参数

        Returns:
            ModernConversationalAgent: Agent实例
        """
        if agent_id in self._agents:
            logger.warning(f"Agent {agent_id} 已存在，将被覆盖")

        try:
            # 获取工具
            agent_tools = tools or []
            if enable_mcp:
                mcp_tools = self.mcp_integration.get_tools(mcp_servers)
                agent_tools.extend(mcp_tools)

            # 创建记忆
            memory = self.memory_manager.create_memory_from_config({
                "type": self.memory_type,
                "params": {}
            })

            # 使用现代化Agent创建方式
            if self.use_modern_agents:
                agent = ModernConversationalAgent(
                    llm_provider=self.llm_provider,
                    model=self.model,
                    tools=agent_tools,
                    memory=memory,
                    verbose=self.verbose,
                    system_message=system_message,
                    agent_type=agent_type,
                    **kwargs
                )
            else:
                # 使用便捷函数
                agent = create_conversational_agent(
                    llm_provider=self.llm_provider,
                    model=self.model,
                    tools=agent_tools,
                    system_message=system_message,
                    modern=False,
                    memory=memory,
                    verbose=self.verbose,
                    agent_type=agent_type,
                    **kwargs
                )

            self._agents[agent_id] = agent
            logger.info(f"Agent {agent_id} 创建成功，工具数: {len(agent_tools)}, 类型: {agent_type}")

            return agent

        except Exception as e:
            logger.error(f"创建Agent {agent_id} 失败: {str(e)}")
            raise

    def get_agent(self, agent_id: str) -> Optional[ModernConversationalAgent]:
        """
        获取Agent实例

        Args:
            agent_id: Agent标识

        Returns:
            Optional[ModernConversationalAgent]: Agent实例
        """
        return self._agents.get(agent_id)

    def remove_agent(self, agent_id: str) -> bool:
        """
        移除Agent实例

        Args:
            agent_id: Agent标识

        Returns:
            bool: 移除是否成功
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent {agent_id} 已移除")
            return True
        return False

    def list_agents(self) -> List[str]:
        """
        列出所有Agent标识

        Returns:
            List[str]: Agent标识列表
        """
        return list(self._agents.keys())

    async def initialize_mcp(self, servers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        初始化MCP集成

        Args:
            servers: 要初始化的服务器列表

        Returns:
            Dict[str, Any]: 初始化结果
        """
        return await self.mcp_integration.initialize(servers)

    async def cleanup(self):
        """清理框架资源"""
        # 清理MCP资源
        await self.mcp_integration.cleanup()

        # 清理Agent
        self._agents.clear()

        logger.info("Agent框架资源已清理")

    def get_framework_stats(self) -> Dict[str, Any]:
        """
        获取框架统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "agents_count": len(self._agents),
            "agents": {
                agent_id: agent.get_stats()
                for agent_id, agent in self._agents.items()
            },
            "tool_manager": self.tool_manager.get_tool_info(),
            "mcp_integration": self.mcp_integration.get_stats(),
            "llm_config": {
                "provider": self.llm_provider,
                "model": self.model
            },
            "memory_type": self.memory_type,
            "use_modern_agents": self.use_modern_agents,
            "langchain_version": "v1.0+"
        }

    async def create_conversation_session(
        self,
        agent_id: str,
        session_id: Optional[str] = None
    ) -> 'ConversationSession':
        """
        创建对话会话

        Args:
            agent_id: Agent标识
            session_id: 会话标识

        Returns:
            ConversationSession: 对话会话实例
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} 不存在")

        return ConversationSession(
            agent=agent,
            session_id=session_id or f"session_{len(self._agents)}_{agent_id}"
        )

    def create_agent_chain(self, *chain_steps) -> 'AgentChain':
        """
        创建Agent链

        Args:
            *chain_steps: 链步骤

        Returns:
            AgentChain: Agent链实例
        """
        return AgentChain(self, *chain_steps)


class ConversationSession:
    """
    对话会话类 - 管理单个对话会话的生命周期
    """

    def __init__(self, agent: ModernConversationalAgent, session_id: str):
        """
        初始化对话会话

        Args:
            agent: Agent实例
            session_id: 会话标识
        """
        self.agent = agent
        self.session_id = session_id
        self.message_count = 0
        self.start_time = None

    async def start(self):
        """启动会话"""
        import datetime
        self.start_time = datetime.datetime.now()
        logger.info(f"对话会话 {self.session_id} 已启动")

    async def message(self, input_text: str) -> Dict[str, Any]:
        """
        发送消息并获取回复

        Args:
            input_text: 输入文本

        Returns:
            Dict[str, Any]: 回复结果
        """
        if not self.start_time:
            await self.start()

        self.message_count += 1

        with LogContext("conversation_session", f"处理消息 {self.message_count}"):
            result = await self.agent.arun(input_text)
            return result

    async def end(self):
        """结束会话"""
        duration = None
        if self.start_time:
            import datetime
            duration = (datetime.datetime.now() - self.start_time).total_seconds()

        logger.info(f"对话会话 {self.session_id} 已结束，消息数: {self.message_count}, 时长: {duration}秒")

        return {
            "session_id": self.session_id,
            "message_count": self.message_count,
            "duration_seconds": duration
        }


class AgentChain:
    """
    Agent链 - 支持多个Agent协作
    """

    def __init__(self, framework: AgentFramework, *chain_steps):
        """
        初始化Agent链

        Args:
            framework: Agent框架实例
            *chain_steps: 链步骤配置
        """
        self.framework = framework
        self.chain_steps = chain_steps
        self.chain_agents = []

    def setup_chain(self):
        """设置Agent链"""
        for i, step in enumerate(self.chain_steps):
            agent_id = f"chain_agent_{i}"
            agent = self.framework.create_agent(
                agent_id=agent_id,
                **step
            )
            self.chain_agents.append(agent)
            logger.info(f"链步骤 {i} Agent {agent_id} 已创建")

    async def execute_chain(self, input_text: str) -> List[Dict[str, Any]]:
        """
        执行Agent链

        Args:
            input_text: 输入文本

        Returns:
            List[Dict[str, Any]]: 所有步骤的结果
        """
        if not self.chain_agents:
            self.setup_chain()

        results = []
        current_input = input_text

        for i, agent in enumerate(self.chain_agents):
            logger.info(f"执行链步骤 {i}")
            session = await self.framework.create_conversation_session(f"chain_agent_{i}")
            await session.start()

            try:
                result = await session.message(current_input)
                results.append({
                    "step": i,
                    "agent_id": f"chain_agent_{i}",
                    "input": current_input,
                    "output": result.get('output', ''),
                    "intermediate_steps": result.get('intermediate_steps', [])
                })

                # 将当前步骤的输出作为下一步的输入
                current_input = result.get('output', '')

            finally:
                await session.end()

        return results


def create_modern_framework(
    llm_provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
    **kwargs
) -> AgentFramework:
    """
    创建现代化框架实例的便捷函数

    Args:
        llm_provider: LLM提供商
        model: 模型名称
        **kwargs: 其他参数

    Returns:
        AgentFramework: 框架实例
    """
    return AgentFramework(
        llm_provider=llm_provider,
        model=model,
        use_modern_agents=True,
        **kwargs
    )