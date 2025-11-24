"""
工具测试模块
"""
import sys
import os
import pytest
import tempfile
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tools.file_tools import (
    ReadFileTool, WriteFileTool, ListDirectoryTool,
    SearchFilesTool, JsonFileTool
)
from src.tools.base_tools import tool_registry


class TestFileTools:
    """文件工具测试类"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def sample_file(self, temp_dir):
        """创建示例文件"""
        file_path = Path(temp_dir) / "test.txt"
        file_path.write_text("这是一个测试文件", encoding='utf-8')
        return str(file_path)

    def test_read_file_tool(self, sample_file):
        """测试文件读取工具"""
        tool = ReadFileTool()

        result = tool._run(file_path=sample_file)
        assert "这是一个测试文件" in result
        assert "成功" in result or "内容" in result

    def test_read_nonexistent_file(self, temp_dir):
        """测试读取不存在的文件"""
        tool = ReadFileTool()
        nonexistent_file = os.path.join(temp_dir, "nonexistent.txt")

        result = tool._run(file_path=nonexistent_file)
        assert "不存在" in result or "错误" in result

    def test_write_file_tool(self, temp_dir):
        """测试文件写入工具"""
        tool = WriteFileTool()
        test_file = os.path.join(temp_dir, "write_test.txt")
        test_content = "这是写入测试内容"

        result = tool._run(
            file_path=test_file,
            content=test_content
        )
        assert "成功" in result

        # 验证文件是否真的被写入
        assert os.path.exists(test_file)
        with open(test_file, 'r', encoding='utf-8') as f:
            assert f.read() == test_content

    def test_list_directory_tool(self, temp_dir):
        """测试目录列表工具"""
        tool = ListDirectoryTool()

        # 在临时目录中创建一些文件
        Path(temp_dir).joinpath("file1.txt").touch()
        Path(temp_dir).joinpath("file2.txt").touch()
        Path(temp_dir).joinpath("subdir").mkdir()

        result = tool._run(directory_path=temp_dir)
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "subdir" in result

    def test_list_nonexistent_directory(self, temp_dir):
        """测试列出不存在的目录"""
        tool = ListDirectoryTool()
        nonexistent_dir = os.path.join(temp_dir, "nonexistent")

        result = tool._run(directory_path=nonexistent_dir)
        assert "不存在" in result or "错误" in result

    def test_search_files_tool(self, temp_dir):
        """测试文件搜索工具"""
        tool = SearchFilesTool()

        # 创建测试文件
        test_files = ["test1.txt", "test2.py", "other.txt"]
        for filename in test_files:
            Path(temp_dir).joinpath(filename).touch()

        result = tool._run(
            directory_path=temp_dir,
            pattern="*.txt"
        )
        assert "test1.txt" in result
        assert "other.txt" in result
        assert "test2.py" not in result

    def test_json_file_tool_read(self, temp_dir):
        """测试JSON文件读取"""
        tool = JsonFileTool()
        json_file = os.path.join(temp_dir, "test.json")
        test_data = {"name": "test", "value": 123}

        # 先创建JSON文件
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        result = tool._run(
            operation="read",
            file_path=json_file
        )
        assert "test" in result
        assert "123" in result

    def test_json_file_tool_write(self, temp_dir):
        """测试JSON文件写入"""
        tool = JsonFileTool()
        json_file = os.path.join(temp_dir, "write_test.json")
        test_data = {"message": "hello world"}

        result = tool._run(
            operation="write",
            file_path=json_file,
            data=json.dumps(test_data)
        )
        assert "成功" in result

        # 验证文件内容
        with open(json_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_json_file_tool_invalid_operation(self):
        """测试JSON文件无效操作"""
        tool = JsonFileTool()

        result = tool._run(
            operation="invalid",
            file_path="test.json"
        )
        assert "不支持" in result or "错误" in result


class TestToolRegistry:
    """工具注册器测试类"""

    def test_register_and_get_tool(self):
        """测试工具注册和获取"""
        tool = ReadFileTool()
        original_count = len(tool_registry.get_all_tools())

        tool_registry.register_tool(tool, category="test")

        assert len(tool_registry.get_all_tools()) == original_count + 1
        retrieved_tool = tool_registry.get_tool("read_file")
        assert retrieved_tool is not None
        assert retrieved_tool.name == "read_file"

    def test_unregister_tool(self):
        """测试工具注销"""
        tool = ReadFileTool()
        tool_registry.register_tool(tool, category="test")

        original_count = len(tool_registry.get_all_tools())
        tool_registry.unregister_tool("read_file")

        assert len(tool_registry.get_all_tools()) == original_count - 1
        assert tool_registry.get_tool("read_file") is None

    def test_get_tools_by_category(self):
        """测试按分类获取工具"""
        # 清理之前的注册
        tool_registry._tools.clear()
        tool_registry._categories.clear()

        file_tool = ReadFileTool()
        write_tool = WriteFileTool()

        tool_registry.register_tool(file_tool, category="file")
        tool_registry.register_tool(write_tool, category="file")

        file_tools = tool_registry.get_tools_by_category("file")
        assert len(file_tools) == 2
        assert all(tool.name in ["read_file", "write_file"] for tool in file_tools)

    def test_search_tools(self):
        """测试工具搜索"""
        # 清理之前的注册
        tool_registry._tools.clear()
        tool_registry._categories.clear()

        tool = ReadFileTool()
        tool_registry.register_tool(tool, category="test")

        # 搜索工具名称
        results = tool_registry.search_tools("read")
        assert len(results) == 1
        assert results[0].name == "read_file"

        # 搜索描述
        results = tool_registry.search_tools("文件")
        assert len(results) == 1

        # 搜索不存在的工具
        results = tool_registry.search_tools("nonexistent")
        assert len(results) == 0

    def test_list_tools(self):
        """测试列出工具"""
        # 清理之前的注册
        tool_registry._tools.clear()
        tool_registry._categories.clear()

        tool = ReadFileTool()
        tool_registry.register_tool(tool, category="test")

        tools_list = tool_registry.list_tools()
        assert isinstance(tools_list, dict)
        assert "read_file" in tools_list
        assert tools_list["read_file"]["name"] == "read_file"

    def test_get_stats(self):
        """测试获取统计信息"""
        # 清理之前的注册
        tool_registry._tools.clear()
        tool_registry._categories.clear()

        tool = ReadFileTool()
        tool_registry.register_tool(tool, category="test")

        stats = tool_registry.get_stats()
        assert isinstance(stats, dict)
        assert stats["total_tools"] == 1
        assert stats["total_categories"] == 1
        assert "test" in stats["categories"]


class TestToolInputValidation:
    """工具输入验证测试类"""

    def test_read_file_validation(self):
        """测试文件读取工具输入验证"""
        tool = ReadFileTool()

        # 有效输入
        valid_input = {"file_path": "test.txt"}
        assert tool.validate_input(valid_input) == True

        # 无效输入 - 缺少必需参数
        invalid_input = {"wrong_param": "test.txt"}
        assert tool.validate_input(invalid_input) == False

    def test_write_file_validation(self):
        """测试文件写入工具输入验证"""
        tool = WriteFileTool()

        # 有效输入
        valid_input = {
            "file_path": "test.txt",
            "content": "测试内容"
        }
        assert tool.validate_input(valid_input) == True

        # 无效输入 - 缺少content参数
        invalid_input = {"file_path": "test.txt"}
        assert tool.validate_input(invalid_input) == False

    def test_json_file_validation(self):
        """测试JSON文件工具输入验证"""
        tool = JsonFileTool()

        # 有效读取输入
        valid_read_input = {
            "operation": "read",
            "file_path": "test.json"
        }
        assert tool.validate_input(valid_read_input) == True

        # 有效写入输入
        valid_write_input = {
            "operation": "write",
            "file_path": "test.json",
            "data": '{"key": "value"}'
        }
        assert tool.validate_input(valid_write_input) == True

        # 无效输入 - 缺少operation
        invalid_input = {"file_path": "test.json"}
        assert tool.validate_input(invalid_input) == False


@pytest.mark.integration
class TestToolIntegration:
    """工具集成测试类"""

    def test_file_workflow(self):
        """测试文件操作工作流程"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建文件
            write_tool = WriteFileTool()
            test_file = os.path.join(temp_dir, "integration_test.txt")
            test_content = "这是一个集成测试"

            write_result = write_tool._run(
                file_path=test_file,
                content=test_content
            )
            assert "成功" in write_result

            # 读取文件
            read_tool = ReadFileTool()
            read_result = read_tool._run(file_path=test_file)
            assert test_content in read_result

            # 列出目录（应该能看到刚创建的文件）
            list_tool = ListDirectoryTool()
            list_result = list_tool._run(directory_path=temp_dir)
            assert "integration_test.txt" in list_result

    def test_json_workflow(self):
        """测试JSON操作工作流程"""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_tool = JsonFileTool()
            json_file = os.path.join(temp_dir, "workflow_test.json")
            original_data = {"message": "hello", "numbers": [1, 2, 3]}

            # 写入JSON
            write_result = json_tool._run(
                operation="write",
                file_path=json_file,
                data=json.dumps(original_data)
            )
            assert "成功" in write_result

            # 读取JSON
            read_result = json_tool._run(
                operation="read",
                file_path=json_file
            )
            assert "hello" in read_result
            assert "1, 2, 3" in read_result


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])