"""
Agent测试模块
"""
import sys
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.agents.conversational_agent import ConversationalAgent
from src.models.llm_configs import LLMProvider
from src.memory.memory_manager import MemoryManager
from src.tools.base_tools import BaseCustomTool, register_tool
from pydantic import BaseModel, Field


class MockToolInput(BaseModel):
    """模拟工具输入"""
    message: str = Field(description="输入消息")


class MockTool(BaseCustomTool):
    """模拟工具"""

    name: str = "mock_tool"
    description: str = "这是一个模拟工具"
    args_schema = MockToolInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(self, message: str) -> str:
        """执行工具"""
        return f"处理消息: {message}"


class TestConversationalAgent:
    """对话式Agent测试类"""

    @pytest.fixture
    def mock_llm(self):
        """模拟LLM"""
        llm_mock = Mock()
        llm_mock.invoke.return_value.content = "这是一个测试回复"
        return llm_mock

    @pytest.fixture
    def sample_tools(self):
        """示例工具"""
        return [MockTool()]

    @pytest.fixture
    def agent(self, mock_llm, sample_tools):
        """创建测试Agent"""
        with patch('src.agents.conversational_agent.create_llm', return_value=mock_llm):
            with patch('src.agents.conversational_agent.create_openai_functions_agent'):
                with patch('src.agents.conversational_agent.AgentExecutor'):
                    agent = ConversationalAgent(
                        llm_provider=LLMProvider.OPENAI,
                        tools=sample_tools,
                        verbose=False
                    )
                    return agent

    def test_agent_initialization(self, agent):
        """测试Agent初始化"""
        assert agent is not None
        assert len(agent.tools) > 0
        assert agent.memory is not None

    def test_add_tool(self, agent):
        """测试添加工具"""
        new_tool = MockTool()
        original_count = len(agent.tools)

        agent.add_tool(new_tool)

        assert len(agent.tools) == original_count + 1
        assert new_tool in agent.tools

    def test_remove_tool(self, agent):
        """测试移除工具"""
        tool_name = agent.tools[0].name
        original_count = len(agent.tools)

        agent.remove_tool(tool_name)

        assert len(agent.tools) == original_count - 1
        assert not any(tool.name == tool_name for tool in agent.tools)

    def test_list_tools(self, agent):
        """测试列出工具"""
        tools_info = agent.list_tools()
        assert isinstance(tools_info, list)
        assert len(tools_info) > 0

        for tool_info in tools_info:
            assert 'name' in tool_info
            assert 'description' in tool_info
            assert 'type' in tool_info

    def test_get_conversation_context(self, agent):
        """测试获取对话上下文"""
        context = agent.get_conversation_context()
        assert isinstance(context, dict)
        assert 'message_count' in context
        assert 'messages' in context

    def test_search_memory(self, agent):
        """测试搜索记忆"""
        # 添加一些测试消息
        agent.memory.chat_memory.add_user_message("测试消息1")
        agent.memory.chat_memory.add_ai_message("测试回复1")

        results = agent.search_memory("测试")
        assert isinstance(results, list)

    def test_set_system_message(self, agent):
        """测试设置系统消息"""
        new_message = "新的系统消息"
        agent.set_system_message(new_message)
        assert agent.system_message == new_message

    def test_get_stats(self, agent):
        """测试获取统计信息"""
        stats = agent.get_stats()
        assert isinstance(stats, dict)
        assert 'llm_provider' in stats
        assert 'tool_count' in stats
        assert 'memory_type' in stats


class TestMemoryManager:
    """记忆管理器测试类"""

    @pytest.fixture
    def memory_manager(self):
        """创建记忆管理器"""
        mock_llm = Mock()
        return MemoryManager(mock_llm)

    def test_create_buffer_memory(self, memory_manager):
        """测试创建对话缓冲记忆"""
        memory = memory_manager.create_buffer_memory()
        assert memory is not None

    def test_create_window_memory(self, memory_manager):
        """测试创建滑动窗口记忆"""
        memory = memory_manager.create_window_memory(window_size=5)
        assert memory is not None

    def test_get_memory_stats(self, memory_manager):
        """测试获取记忆统计信息"""
        memory = memory_manager.create_buffer_memory()
        stats = memory_manager.get_memory_stats(memory)
        assert isinstance(stats, dict)
        assert 'memory_type' in stats

    def test_create_memory_from_config(self, memory_manager):
        """测试根据配置创建记忆"""
        config = {
            "type": "buffer",
            "params": {
                "memory_key": "chat_history"
            }
        }
        memory = memory_manager.create_memory_from_config(config)
        assert memory is not None


class TestCustomTools:
    """自定义工具测试类"""

    def test_tool_registration(self):
        """测试工具注册"""
        tool = MockTool()
        register_tool(tool, category="test")

        from src.tools.base_tools import tool_registry
        registered_tool = tool_registry.get_tool("mock_tool")
        assert registered_tool is not None
        assert registered_tool.name == "mock_tool"

    def test_tool_execution(self):
        """测试工具执行"""
        tool = MockTool()
        result = tool._run(message="测试消息")
        assert "处理消息: 测试消息" in result

    def test_tool_validation(self):
        """测试工具输入验证"""
        tool = MockTool()
        valid_input = {"message": "测试消息"}
        invalid_input = {"wrong_field": "测试"}

        assert tool.validate_input(valid_input) == True
        assert tool.validate_input(invalid_input) == False

    def test_tool_info(self):
        """测试获取工具信息"""
        tool = MockTool()
        info = tool.get_tool_info()
        assert isinstance(info, dict)
        assert info['name'] == "mock_tool"
        assert info['description'] == "这是一个模拟工具"


@pytest.mark.asyncio
class TestAsyncAgent:
    """异步Agent测试类"""

    @pytest.fixture
    def mock_async_llm(self):
        """模拟异步LLM"""
        llm_mock = AsyncMock()
        response_mock = Mock()
        response_mock.content = "这是一个异步测试回复"
        llm_mock.invoke.return_value = response_mock
        return llm_mock

    @pytest.fixture
    async def async_agent(self, mock_async_llm):
        """创建异步测试Agent"""
        with patch('src.agents.conversational_agent.create_llm', return_value=mock_async_llm):
            with patch('src.agents.conversational_agent.create_openai_functions_agent'):
                with patch('src.agents.conversational_agent.AgentExecutor'):
                    agent = ConversationalAgent(
                        llm_provider=LLMProvider.OPENAI,
                        verbose=False
                    )
                    return agent

    async def test_async_run(self, async_agent):
        """测试异步运行"""
        # 由于使用了mock，这里主要测试异步调用不会出错
        with patch.object(async_agent.agent_executor, 'ainvoke') as mock_invoke:
            mock_invoke.return_value = {"output": "测试回复"}

            result = await async_agent.arun("测试输入")
            assert isinstance(result, dict)


class TestIntegration:
    """集成测试类"""

    @pytest.mark.integration
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 这个测试需要真实的LLM配置，标记为integration测试
        # 在CI/CD环境中可能需要跳过或使用mock
        pass

    @pytest.mark.integration
    def test_agent_with_custom_tools(self):
        """测试Agent与自定义工具的集成"""
        # 集成测试，验证自定义工具能正常工作
        pass


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])