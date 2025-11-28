"""
基于DeepAgent理念的PoC生成代理
将复杂的PoC生成任务分解为多个专业化子任务，提高成功率和可维护性
"""

import asyncio
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI, OpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.agents.base_agent import BaseAgent
from src.clients import get_llm_client
from src.models.poc_models import ToDoListResult, PocResult
from src.tools.sandbox_tools import POC_AGENT_TOOLS
from src.utils.logger import log


class TaskStage(Enum):
    """任务阶段枚举"""
    PLANNING = "planning"
    ANALYSIS = "analysis"
    CODING = "coding"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REVIEW = "review"


@dataclass
class TaskContext:
    """任务上下文，存储各阶段的结果"""
    stage: TaskStage
    vulnerability_info: ToDoListResult
    working_directory: str
    generated_files: List[str]
    analysis_result: Optional[str] = None
    code_result: Optional[str] = None
    test_result: Optional[str] = None
    doc_result: Optional[str] = None
    review_result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于传递给子代理"""
        return {
            "stage": self.stage.value,
            "vulnerability_info": self.vulnerability_info.model_dump(),
            "working_directory": self.working_directory,
            "generated_files": self.generated_files,
            "analysis_result": self.analysis_result,
            "code_result": self.code_result,
            "test_result": self.test_result,
            "doc_result": self.doc_result,
            "review_result": self.review_result
        }


class SubAgent:
    """子代理基类"""

    def __init__(self, name: str, model: ChatOpenAI | OpenAI, tools: List[BaseTool],
                 system_prompt: str, tools_prompt: str = ""):
        self.name = name
        self.model = model
        self.tools = tools
        self.system_prompt = system_prompt
        self.tools_prompt = tools_prompt

        # 创建LangChain代理
        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt + tools_prompt
        )

    async def execute(self, context: Dict[str, Any], task_description: str) -> str:
        """执行子代理任务"""
        try:
            # 构造用户输入
            user_input = f"""
任务描述: {task_description}

当前上下文:
{json.dumps(context, indent=2, ensure_ascii=False)}

请根据你的专业能力完成上述任务。返回详细的结果。
"""

            # 调用代理
            response = await self.agent.ainvoke({
                "messages": [{"role": "user", "content": user_input}]
            })

            # 提取回复内容
            ai_message = response["messages"][-1]
            return ai_message.content

        except Exception as e:
            log.error(f"子代理 {self.name} 执行失败: {str(e)}")
            return f"执行失败: {str(e)}"


class PlanningAgent(SubAgent):
    """规划阶段代理 - 分解复杂任务"""

    def __init__(self, model: ChatOpenAI | OpenAI, tools: List[BaseTool]):
        system_prompt = """
你是一个专业的PoC任务规划专家。你的职责是将复杂的漏洞验证任务分解为清晰、可执行的子任务列表。

你需要分析漏洞信息并制定详细的执行计划，包括：
1. 代码分析任务
2. PoC代码编写任务
3. 测试验证任务
4. 文档编写任务

输出格式应该是一个结构化的JSON，包含各阶段的具体任务。
"""
        tools_prompt = f"""
可用工具:
{chr(10).join([f"- {tool.name}: {tool.description}" for tool in tools])}

请使用这些工具来分析漏洞信息和环境。
"""
        super().__init__("PlanningAgent", model, tools, system_prompt, tools_prompt)


class AnalysisAgent(SubAgent):
    """分析阶段代理 - 深入分析漏洞"""

    def __init__(self, model: ChatOpenAI | OpenAI, tools: List[BaseTool]):
        system_prompt = """
你是一个资深的代码安全分析专家。你的职责是深入分析漏洞代码，理解漏洞原理，并确定PoC开发的技术方案。

你需要：
1. 分析漏洞代码的具体实现
2. 理解漏洞的触发条件和数据流
3. 确定PoC开发的技术路线
4. 识别需要模拟的依赖和环境

输出详细的技术分析报告，为后续的代码开发提供指导。
"""
        tools_prompt = f"""
可用工具:
{chr(10).join([f"- {tool.name}: {tool.description}" for tool in tools])}

请使用这些工具来读取和分析相关代码文件。
"""
        super().__init__("AnalysisAgent", model, tools, system_prompt, tools_prompt)


class CodingAgent(SubAgent):
    """编码阶段代理 - 生成PoC代码"""

    def __init__(self, model: ChatOpenAI | OpenAI, tools: List[BaseTool]):
        system_prompt = """
你是一个专业的PoC代码开发工程师。你的职责是根据漏洞分析结果，生成可独立运行的PoC验证代码。

你需要：
1. 根据分析结果编写完整的PoC代码
2. 确保代码可以独立编译和运行
3. 包含清晰的注释和关键节点标记
4. 实现有效的漏洞触发和验证逻辑

生成的代码应该：
- 完整可运行
- 包含必要的依赖模拟
- 有明显的验证效果
- 包含安全的使用说明
"""
        tools_prompt = f"""
可用工具:
{chr(10).join([f"- {tool.name}: {tool.description}" for tool in tools])}

请使用这些工具来创建和管理代码文件。
"""
        super().__init__("CodingAgent", model, tools, system_prompt, tools_prompt)


class TestingAgent(SubAgent):
    """测试阶段代理 - 验证PoC效果"""

    def __init__(self, model: ChatOpenAI | OpenAI, tools: List[BaseTool]):
        system_prompt = """
你是一个专业的PoC测试验证工程师。你的职责是测试生成的PoC代码，验证其正确性和有效性。

你需要：
1. 检查代码的语法正确性
2. 验证代码的可编译性
3. 测试PoC的执行效果
4. 确认漏洞是否被成功触发
5. 提供测试结果和改进建议

如果发现问题，请详细报告并提供修复建议。
"""
        tools_prompt = f"""
可用工具:
{chr(10).join([f"- {tool.name}: {tool.description}" for tool in tools])}

请使用这些工具来编译、运行和测试代码。
"""
        super().__init__("TestingAgent", model, tools, system_prompt, tools_prompt)


class DocumentationAgent(SubAgent):
    """文档阶段代理 - 生成完整报告"""

    def __init__(self, model: ChatOpenAI | OpenAI, tools: List[BaseTool]):
        system_prompt = """
你是一个专业的安全文档编写专家。你的职责是根据所有阶段的结果，生成完整、专业的漏洞验证报告。

你需要：
1. 整合所有阶段的分析和测试结果
2. 编写详细的漏洞分析报告
3. 包含PoC使用说明和安全建议
4. 确保报告的完整性和专业性

生成的报告应该包含：
- 漏洞概述和影响分析
- 技术分析详情
- PoC代码和使用说明
- 测试结果和验证效果
- 修复建议和防护措施
"""
        tools_prompt = f"""
可用工具:
{chr(10).join([f"- {tool.name}: {tool.description}" for tool in tools])}

请使用这些工具来读取文件信息并生成报告文档。
"""
        super().__init__("DocumentationAgent", model, tools, system_prompt, tools_prompt)


class PoCGenDeepAgent:
    """
    基于DeepAgent理念的PoC生成代理

    核心特点:
    1. 任务分解: 将复杂任务分解为多个专业化子任务
    2. 专业化代理: 每个子任务由专门优化的代理处理
    3. 上下文保持: 通过TaskContext保持各阶段间的上下文信息
    4. 渐进式执行: 按阶段顺序执行，每阶段结果为下一阶段提供输入
    """

    def __init__(self, model: Optional[ChatOpenAI | OpenAI] = None):
        self.model = model or get_llm_client()
        self.chat_history: List = []

        # 初始化各个专业化代理
        self.planning_agent = PlanningAgent(self.model, POC_AGENT_TOOLS)
        self.analysis_agent = AnalysisAgent(self.model, POC_AGENT_TOOLS)
        self.coding_agent = CodingAgent(self.model, POC_AGENT_TOOLS)
        self.testing_agent = TestingAgent(self.model, POC_AGENT_TOOLS)
        self.documentation_agent = DocumentationAgent(self.model, POC_AGENT_TOOLS)

    def _create_working_directory(self, poc_path: str) -> str:
        """创建工作目录"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        working_dir = os.path.join(poc_path, f"deepagent_{timestamp}")
        os.makedirs(working_dir, exist_ok=True)
        return working_dir

    async def _execute_stage(self, agent: SubAgent, context: TaskContext,
                           task_description: str) -> str:
        """执行单个阶段"""
        log.info(f"开始执行阶段: {agent.name}")

        # 添加用户消息到历史记录
        self.chat_history.append(HumanMessage(
            content=f"[{agent.name}] {task_description}"
        ))

        # 执行代理任务
        result = await agent.execute(context.to_dict(), task_description)

        # 添加AI回复到历史记录
        self.chat_history.append(AIMessage(content=result))

        log.info(f"阶段 {agent.name} 执行完成")
        return result

    async def _planning_stage(self, context: TaskContext) -> str:
        """规划阶段"""
        task_description = """
请根据提供的漏洞信息，制定详细的PoC生成计划。分析漏洞类型、影响范围、技术难点，
并制定包含代码分析、PoC开发、测试验证、文档编写的完整执行计划。
"""
        return await self._execute_stage(self.planning_agent, context, task_description)

    async def _analysis_stage(self, context: TaskContext) -> str:
        """分析阶段"""
        task_description = """
请深入分析漏洞代码，理解漏洞的技术原理和触发机制。重点关注：
1. 漏洞代码的具体实现逻辑
2. 数据流和控制流分析
3. 漏洞触发的必要条件
4. PoC开发需要模拟的环境和依赖
"""
        return await self._execute_stage(self.analysis_agent, context, task_description)

    async def _coding_stage(self, context: TaskContext) -> str:
        """编码阶段"""
        task_description = """
请根据前面的分析结果，生成完整可运行的PoC验证代码。要求：
1. 代码必须可以独立编译和运行
2. 包含必要的依赖类和函数模拟
3. 实现有效的漏洞触发逻辑
4. 包含清晰的注释和关键节点标记
5. 提供明显的验证效果
"""
        return await self._execute_stage(self.coding_agent, context, task_description)

    async def _testing_stage(self, context: TaskContext) -> str:
        """测试阶段"""
        task_description = """
请测试生成的PoC代码，验证其正确性和有效性。包括：
1. 检查代码语法正确性
2. 验证代码可编译性
3. 测试PoC执行效果
4. 确认漏洞是否被成功触发
5. 提供详细的测试结果
"""
        return await self._execute_stage(self.testing_agent, context, task_description)

    async def _documentation_stage(self, context: TaskContext) -> str:
        """文档阶段"""
        task_description = """
请根据所有阶段的执行结果，生成完整的漏洞验证报告。报告应包含：
1. 漏洞概述和技术分析
2. PoC代码说明和使用指南
3. 测试结果和验证效果
4. 安全建议和修复方案
5. 完整的执行过程记录
"""
        return await self._execute_stage(self.documentation_agent, context, task_description)

    async def generate_poc(self, vulnerability_info: ToDoListResult) -> PocResult:
        """
        执行完整的PoC生成流程

        Args:
            vulnerability_info: 漏洞信息

        Returns:
            PocResult: 包含完整执行过程和结果的PoC结果
        """
        log.info("开始DeepAgent PoC生成流程")

        try:
            # 创建工作目录
            working_dir = self._create_working_directory(vulnerability_info.poc_path)

            # 初始化任务上下文
            context = TaskContext(
                stage=TaskStage.PLANNING,
                vulnerability_info=vulnerability_info,
                working_directory=working_dir,
                generated_files=[]
            )

            execution_log = []

            # 执行各个阶段
            stages = [
                (TaskStage.PLANNING, self._planning_stage),
                (TaskStage.ANALYSIS, self._analysis_stage),
                (TaskStage.CODING, self._coding_stage),
                (TaskStage.TESTING, self._testing_stage),
                (TaskStage.DOCUMENTATION, self._documentation_stage)
            ]

            for stage, stage_func in stages:
                context.stage = stage
                result = await stage_func(context)

                # 更新上下文
                if stage == TaskStage.PLANNING:
                    # 规划阶段结果不直接存储，但可以解析出任务列表
                    pass
                elif stage == TaskStage.ANALYSIS:
                    context.analysis_result = result
                elif stage == TaskStage.CODING:
                    context.code_result = result
                elif stage == TaskStage.TESTING:
                    context.test_result = result
                elif stage == TaskStage.DOCUMENTATION:
                    context.doc_result = result

                execution_log.append(f"=== {stage.value.upper()} 阶段 ===\n{result}\n")

            # 生成最终结果
            final_result = f"""
DeepAgent PoC生成执行报告

工作目录: {working_dir}
执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*60}
{chr(10).join(execution_log)}
{'='*60}

生成的文件:
{chr(10).join([f"- {f}" for f in context.generated_files]) if context.generated_files else "无"}

执行状态: 成功完成
"""

            log.info("DeepAgent PoC生成流程完成")
            return PocResult(result=final_result)

        except Exception as e:
            error_msg = f"DeepAgent执行过程中发生错误: {str(e)}"
            log.error(error_msg)
            return PocResult(result=error_msg)


# 使用示例
async def main():
    """主函数示例"""
    import os

    # 生成时间戳路径
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    poc_path = os.path.join("./poc", timestamp)

    # 确保目录存在
    os.makedirs(poc_path, exist_ok=True)

    # 测试数据 - 格式化字符串漏洞示例
    vuln_result = ToDoListResult(
        todolist="基于DeepAgent方法生成格式化字符串漏洞的PoC验证代码",
        code_repo="/codesec/AF8048/AF8.0.48",
        poc_path=poc_path,
        type="FORMAT_STRING_VULNERABILITY",
        description="在第1015行，ADD_ERR_MSG函数的第二个参数直接使用了来自用户输入的字符串(*it).c_str()，该字符串可能包含格式化说明符(如%s、%n等)，导致格式化字符串漏洞。",
        filename="webui/cgi/server/tamper_admin/tamperAdminView.cpp",
        code="""
1011 |+ 	for (vector<string>::iterator it = names.begin(); it != names.end(); it++) {
1012 |+ 		string out_name;
1013 |+ 		ret = CheckDeleteDepend(*it, out_name);
1014 |+ 		if (ret) {
1015 |+ 			ADD_ERR_MSG(ID2STR("IDS_ERR_DELETE_DEPEND"), (*it).c_str());
1016 |+ 			ShowErrMsg();
        """.strip(),
        impact="攻击者可以通过构造包含格式化说明符的输入，导致程序读取或写入任意内存地址，可能造成敏感信息泄露或拒绝服务攻击。",
        result="安全漏洞分析报告..."  # 简化的结果字符串
    )

    # 使用DeepAgent生成PoC
    deep_agent = PoCGenDeepAgent()

    try:
        result = await deep_agent.generate_poc(vuln_result)
        log.info(f"DeepAgent执行结果:\n{result.result}")

    except Exception as e:
        log.error(f"DeepAgent执行失败: {str(e)}")


if __name__ == "__main__":
    log.info("启动PoC生成DeepAgent...")
    asyncio.run(main())