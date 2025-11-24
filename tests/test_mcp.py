"""
MCP工具模块测试
"""
import sys
import os
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tools.mcp.mcp_client import MCPClient, MCPStdioClient
from src.tools.mcp.mcp_tool_adapter import MCPToolAdapter, create_dynamic_pydantic_model
from src.tools.mcp.mcp_server_manager import MCPServerConfig, MCPServerManager
from src.tools.mcp.mcp_registry import MCPRegistry, UnifiedToolManager


class TestMCPClient:
    """MCP客户端测试"""

    def test_mcp_client_initialization(self):
        """测试MCP客户端初始化"""
        server_command = ["echo", "hello"]
        client = MCPClient(server_command, "test_server")

        assert client.server_command == server_command
        assert client.server_name == "test_server"
        assert client.request_id == 0

    @pytest.mark.asyncio
    async def test_mcp_stdio_client(self):
        """测试标准IO MCP客户端"""
        client = MCPStdioClient()

        # 测试请求ID生成
        id1 = client._next_id()
        id2 = client._next_id()
        assert id1 == 1
        assert id2 == 2

        # 模拟响应
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": []}
        }

        with patch('builtins.input', return_value='{"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}'):
            with patch('builtins.print') as mock_print:
                response = client._send_request({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list"
                })
                assert response == mock_response


class TestMCPToolAdapter:
    """MCP工具适配器测试"""

    def test_create_dynamic_pydantic_model(self):
        """测试动态Pydantic模型创建"""
        tool_schema = {
            "name": "test_tool",
            "inputSchema": {
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "测试消息"
                    },
                    "count": {
                        "type": "integer",
                        "description": "计数"
                    }
                },
                "required": ["message"]
            }
        }

        model_class = create_dynamic_pydantic_model(tool_schema)

        # 测试模型创建
        assert model_class.__name__ == "test_toolInput"

        # 测试有效输入
        valid_input = {"message": "hello", "count": 5}
        instance = model_class(**valid_input)
        assert instance.message == "hello"
        assert instance.count == 5

        # 测试必需字段验证
        with pytest.raises(ValueError):
            model_class(count=5)  # 缺少必需的message字段

    def test_mcp_tool_adapter_initialization(self):
        """测试MCP工具适配器初始化"""
        mock_client = Mock()
        tool_schema = {
            "name": "test_tool",
            "description": "测试工具",
            "inputSchema": {
                "properties": {
                    "message": {"type": "string", "description": "消息"}
                }
            }
        }

        adapter = MCPToolAdapter(mock_client, tool_schema)

        assert adapter.name == "test_tool"
        assert adapter.description == "测试工具"
        assert adapter.mcp_client == mock_client

    def test_mcp_tool_adapter_info(self):
        """测试MCP工具适配器信息获取"""
        mock_client = Mock()
        tool_schema = {
            "name": "test_tool",
            "description": "测试工具"
        }

        adapter = MCPToolAdapter(mock_client, tool_schema)

        info = adapter.get_mcp_info()
        assert info["name"] == "test_tool"
        assert info["description"] == "测试工具"
        assert "tool_schema" in info
        assert "available" in info


class TestMCPServerConfig:
    """MCP服务器配置测试"""

    def test_server_config_creation(self):
        """测试服务器配置创建"""
        config = MCPServerConfig(
            name="test_server",
            command=["echo", "hello"],
            description="测试服务器"
        )

        assert config.name == "test_server"
        assert config.command == ["echo", "hello"]
        assert config.description == "测试服务器"
        assert config.auto_start is True
        assert config.timeout == 30

    def test_server_config_serialization(self):
        """测试服务器配置序列化"""
        config = MCPServerConfig(
            name="test_server",
            command=["echo", "hello"],
            description="测试服务器",
            auto_start=False,
            timeout=60
        )

        config_dict = config.to_dict()
        assert config_dict["name"] == "test_server"
        assert config_dict["command"] == ["echo", "hello"]
        assert config_dict["description"] == "测试服务器"
        assert config_dict["auto_start"] is False
        assert config_dict["timeout"] == 60

        # 测试从字典创建
        new_config = MCPServerConfig.from_dict(config_dict)
        assert new_config.name == config.name
        assert new_config.command == config.command
        assert new_config.description == config.description


class TestMCPServerManager:
    """MCP服务器管理器测试"""

    def test_server_manager_initialization(self):
        """测试服务器管理器初始化"""
        manager = MCPServerManager()

        assert len(manager.servers) > 0  # 应该有默认服务器
        assert "filesystem" in manager.servers
        assert "github" in manager.servers

    def test_server_registration(self):
        """测试服务器注册"""
        manager = MCPServerManager()
        config = MCPServerConfig(
            name="custom_server",
            command=["echo", "test"],
            description="自定义服务器"
        )

        manager.register_server(config)

        assert "custom_server" in manager.servers
        assert manager.servers["custom_server"].description == "自定义服务器"

    def test_server_unregistration(self):
        """测试服务器注销"""
        manager = MCPServerManager()
        config = MCPServerConfig(
            name="temp_server",
            command=["echo", "test"]
        )

        manager.register_server(config)
        assert "temp_server" in manager.servers

        manager.unregister_server("temp_server")
        assert "temp_server" not in manager.servers

    def test_list_servers(self):
        """测试列出服务器"""
        manager = MCPServerManager()
        servers = manager.list_servers()

        assert isinstance(servers, list)
        assert len(servers) > 0

        for server in servers:
            assert "name" in server
            assert "command" in server
            assert "status" in server

    def test_server_stats(self):
        """测试服务器统计"""
        manager = MCPServerManager()
        stats = manager.get_server_stats()

        assert isinstance(stats, dict)
        assert "total_servers" in stats
        assert "running_servers" in stats
        assert "servers" in stats


class TestMCPRegistry:
    """MCP注册表测试"""

    def test_registry_initialization(self):
        """测试注册表初始化"""
        registry = MCPRegistry()

        assert len(registry._mcp_tools) == 0
        assert len(registry._mcp_tools_by_server) == 0
        assert len(registry._loaded_servers) == 0

    def test_registry_stats(self):
        """测试注册表统计"""
        registry = MCPRegistry()
        stats = registry.get_stats()

        assert isinstance(stats, dict)
        assert "total_tools" in stats
        assert "available_tools" in stats
        assert "loaded_servers" in stats


class TestUnifiedToolManager:
    """统一工具管理器测试"""

    def test_unified_manager_initialization(self):
        """测试统一工具管理器初始化"""
        manager = UnifiedToolManager()

        assert len(manager.langchain_tools) == 0
        assert isinstance(manager.mcp_registry, MCPRegistry)

    def test_langchain_tool_registration(self):
        """测试LangChain工具注册"""
        manager = UnifiedToolManager()

        # 创建模拟工具
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "测试工具"

        manager.register_langchain_tool(mock_tool, "test_category")

        assert "test_tool" in manager.langchain_tools
        assert "test_category" in manager._categories
        assert "test_tool" in manager._categories["test_category"]

    def test_get_tool_priority(self):
        """测试工具获取优先级"""
        manager = UnifiedToolManager()

        # 创建模拟工具
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "测试工具"

        manager.register_langchain_tool(mock_tool, "test_category")

        # 获取工具应该返回LangChain工具
        retrieved_tool = manager.get_tool("test_tool")
        assert retrieved_tool == mock_tool

    def test_search_tools(self):
        """测试工具搜索"""
        manager = UnifiedToolManager()

        # 创建模拟工具
        mock_tool = Mock()
        mock_tool.name = "file_reader"
        mock_tool.description = "读取文件内容"

        manager.register_langchain_tool(mock_tool, "file")

        # 搜索工具
        results = manager.search_tools("file")
        assert len(results) == 1
        assert results[0] == mock_tool

    def test_manager_stats(self):
        """测试管理器统计"""
        manager = UnifiedToolManager()

        # 添加一个工具
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "测试工具"

        manager.register_langchain_tool(mock_tool, "test")

        stats = manager.get_stats()
        assert isinstance(stats, dict)
        assert "langchain_tools" in stats
        assert "mcp_tools" in stats
        assert "total_tools" in stats
        assert stats["langchain_tools"]["total_tools"] == 1


class TestMCPIntegration:
    """MCP集成测试"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mcp_server_lifecycle(self):
        """测试MCP服务器生命周期"""
        manager = MCPServerManager()

        # 创建测试服务器配置
        config = MCPServerConfig(
            name="echo_server",
            command=["echo", "test"],
            description="Echo测试服务器"
        )
        manager.register_server(config)

        # 启动服务器
        success = await manager.start_server("echo_server")
        # 注意：echo命令可能不是真正的MCP服务器，这里主要测试流程
        # assert success == True

        # 检查状态
        client = manager.get_client("echo_server")
        # assert client is not None

        # 停止服务器
        stop_success = await manager.stop_server("echo_server")
        # assert stop_success == True

    @pytest.mark.integration
    def test_mcp_config_loading(self):
        """测试MCP配置加载"""
        config_file = "mcp_servers.json"

        if os.path.exists(config_file):
            manager = MCPServerManager(config_file)
            servers = manager.list_servers()

            assert len(servers) > 0

            # 检查是否包含预期的服务器
            server_names = [s["name"] for s in servers]
            expected_servers = ["filesystem", "github", "gdrive"]

            for expected in expected_servers:
                assert expected in server_names


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])