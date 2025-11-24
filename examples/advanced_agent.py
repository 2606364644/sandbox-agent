"""
高级Agent示例 - 自定义工具和配置
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.main import LangChainAgentFramework
from src.models.llm_configs import LLMProvider
from src.tools.base_tools import BaseCustomTool, register_tool
from src.utils.logger import get_logger, LogContext
from pydantic import BaseModel, Field
from datetime import datetime
import json

logger = get_logger(__name__)


class CalculatorInput(BaseModel):
    """计算器输入模型"""
    expression: str = Field(description="要计算的数学表达式，例如: 2 + 3 * 4")


class CalculatorTool(BaseCustomTool):
    """自定义计算器工具"""

    name: str = "calculator"
    description: str = "执行基本的数学计算，支持加减乘除和括号"
    args_schema = CalculatorInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(self, expression: str) -> str:
        """执行计算"""
        try:
            # 使用eval进行计算（在生产环境中应该使用更安全的方法）
            # 这里仅作为示例，实际使用时应该考虑安全性
            result = eval(expression)
            return f"计算结果: {expression} = {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"


class WeatherInput(BaseModel):
    """天气查询输入模型"""
    city: str = Field(description="城市名称")
    date: str = Field(default="今天", description="查询日期，例如: 今天, 明天, 2024-12-25")


class WeatherTool(BaseCustomTool):
    """模拟天气查询工具"""

    name: str = "weather_query"
    description: str = "查询指定城市的天气信息"
    args_schema = WeatherInput

    def _setup(self):
        """工具初始化设置"""
        # 模拟天气数据
        self.mock_weather_data = {
            "北京": {"今天": "晴天，温度15-25°C", "明天": "多云，温度12-22°C"},
            "上海": {"今天": "小雨，温度18-23°C", "明天": "阴天，温度16-21°C"},
            "广州": {"今天": "晴天，温度22-30°C", "明天": "晴天，温度23-31°C"},
            "深圳": {"今天": "多云，温度23-29°C", "明天": "晴天，温度24-30°C"}
        }

    def _execute(self, city: str, date: str = "今天") -> str:
        """执行天气查询"""
        city_data = self.mock_weather_data.get(city)
        if not city_data:
            return f"抱歉，没有找到 {city} 的天气信息"

        weather = city_data.get(date, "暂无数据")
        return f"{city}{date}的天气: {weather}"


class TaskManagerInput(BaseModel):
    """任务管理输入模型"""
    action: str = Field(description="操作类型: add, list, complete")
    task: str = Field(default="", description="任务内容")


class TaskManagerTool(BaseCustomTool):
    """任务管理工具"""

    name: str = "task_manager"
    description: str = "管理待办事项，支持添加、列表和完成任务"
    args_schema = TaskManagerInput

    def _setup(self):
        """工具初始化设置"""
        self.tasks = []

    def _execute(self, action: str, task: str = "") -> str:
        """执行任务管理操作"""
        if action == "add":
            if task.strip():
                self.tasks.append({"task": task, "completed": False, "created_at": datetime.now().isoformat()})
                return f"✓ 已添加任务: {task}"
            else:
                return "错误: 任务内容不能为空"

        elif action == "list":
            if not self.tasks:
                return "暂无待办任务"

            result = "待办任务列表:\n"
            for i, task_info in enumerate(self.tasks, 1):
                status = "✓" if task_info["completed"] else "○"
                result += f"{i}. {status} {task_info['task']}\n"
            return result.strip()

        elif action == "complete":
            if not self.tasks:
                return "暂无任务可完成"

            # 完成第一个未完成的任务
            for task_info in self.tasks:
                if not task_info["completed"]:
                    task_info["completed"] = True
                    task_info["completed_at"] = datetime.now().isoformat()
                    return f"✓ 已完成任务: {task_info['task']}"

            return "所有任务都已完成"

        else:
            return f"不支持的操作: {action}，请使用 add, list, complete"


def main():
    """主函数 - 高级Agent示例"""
    print("=== LangChain Agent 高级示例 ===\n")

    try:
        # 创建Agent框架实例
        with LogContext("advanced_example", "创建高级Agent框架"):
            framework = LangChainAgentFramework(
                llm_provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
                enable_file_tools=True,
                enable_web_tools=False,
                memory_type="buffer",
                verbose=True
            )

        print("✓ Agent框架创建成功")

        # 注册自定义工具
        custom_tools = [
            CalculatorTool(),
            WeatherTool(),
            TaskManagerTool()
        ]

        for tool in custom_tools:
            framework.add_custom_tool(tool)
            print(f"✓ 已添加自定义工具: {tool.name}")

        print(f"\n总共可用工具: {len(framework.tools)} 个\n")

        # 高级示例对话
        advanced_examples = [
            {
                "query": "帮我计算 (15 + 8) * 3 - 10 的结果",
                "expected_tools": ["calculator"]
            },
            {
                "query": "查询北京今天的天气情况",
                "expected_tools": ["weather_query"]
            },
            {
                "query": "帮我添加一个任务：学习LangChain框架",
                "expected_tools": ["task_manager"]
            },
            {
                "query": "显示我的任务列表",
                "expected_tools": ["task_manager"]
            },
            {
                "query": "计算 100 / 5 + 10 的结果，然后查询上海明天的天气",
                "expected_tools": ["calculator", "weather_query"]
            },
            {
                "query": "帮我完成第一个任务，然后创建一个包含这个计算结果的文件",
                "expected_tools": ["task_manager", "write_file"]
            }
        ]

        for i, example in enumerate(advanced_examples, 1):
            print(f"--- 高级示例 {i} ---")
            print(f"用户: {example['query']}")
            print(f"预期使用工具: {', '.join(example['expected_tools'])}")

            with LogContext("advanced_example", f"处理高级示例 {i}"):
                result = framework.run_single_query(example['query'])
                response = result.get('output', '抱歉，无法处理这个请求。')

                # 显示结果
                print(f"Assistant: {response}")

                # 如果有中间步骤，显示工具调用
                if 'intermediate_steps' in result:
                    steps = result['intermediate_steps']
                    if steps:
                        print("\n工具调用详情:")
                        for j, (tool_call, tool_output) in enumerate(steps, 1):
                            tool_name = tool_call.tool if hasattr(tool_call, 'tool') else str(tool_call)
                            print(f"  {j}. {tool_name}: {truncate_text(str(tool_output), 100)}")

                print()

        # 显示最终统计
        print("=== 最终统计信息 ===")
        final_stats = framework.get_agent_stats()
        print(f"总对话轮数: {len(advanced_examples)}")
        print(f"记忆消息数: {final_stats['memory_stats'].get('message_count', 0)}")
        print(f"可用工具数: {final_stats['tools_count']}")

        # 保存对话历史
        conversation_file = "examples/conversation_history.json"
        framework.save_conversation(conversation_file)
        print(f"✓ 对话历史已保存到: {conversation_file}")

    except Exception as e:
        logger.error(f"运行高级示例时出错: {str(e)}")
        print(f"错误: {str(e)}")
        print("\n可能的原因:")
        print("1. 未设置OPENAI_API_KEY环境变量")
        print("2. 自定义工具注册失败")
        print("3. 网络连接问题")


def truncate_text(text: str, max_length: int = 80) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


if __name__ == "__main__":
    main()