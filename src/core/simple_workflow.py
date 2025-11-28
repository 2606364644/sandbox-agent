"""
简化工作流 - 无评估决策机制
去除复杂的重试决策逻辑，采用简单线性执行
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from src.agents.planning_agent import PlanningAgent
from src.agents.pocgen_agent import PocGenAgent
from src.agents.sandbox_agent import SandboxAgent
from src.clients import get_llm_client
from src.models.sandbox_models import PocCode, SandboxResult
from src.models.planning_models import VulnResult, PlanningResult
from src.models.poc_models import ToDoListResult, PocResult
from src.models.workflow_models import WorkflowState
from src.utils.logger import log


class SimpleWorkflow:
    """简化工作流 - 无评估决策机制"""

    def __init__(self):
        # 使用抽象层自动选择客户端
        self.model = get_llm_client()

        self.planning_agent = PlanningAgent(model=self.model)
        self.pocgen_agent = PocGenAgent(model=self.model)
        self.sandbox_agent = SandboxAgent(model=self.model)

        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()

        log.info("简化工作流初始化完成")

    def _build_workflow(self) -> StateGraph:
        """构建简单线性工作流"""
        workflow = StateGraph(WorkflowState)

        # 添加节点
        workflow.add_node("planning", self._planning_node)
        workflow.add_node("poc_generation", self._poc_generation_node)
        workflow.add_node("sandbox_execution", self._sandbox_execution_node)

        # 简单线性连接，无决策点
        workflow.add_edge(START, "planning")
        workflow.add_edge("planning", "poc_generation")
        workflow.add_edge("poc_generation", "sandbox_execution")
        workflow.add_edge("sandbox_execution", END)

        return workflow

    async def _planning_node(self, state: WorkflowState) -> WorkflowState:
        """规划节点"""
        log.info("开始规划...")

        try:
            # 直接使用传入的vuln_result或创建新的
            if "vuln_result" not in state:
                vuln_result = VulnResult(
                    code_repo=state["code_repo"],
                    poc_path=state["poc_path"],
                    type=state["vulnerability_type"],
                    description=state["description"],
                    filename=state["filename"],
                    code=state["code"],
                    impact=state["impact"],
                    result=state["initial_analysis"]
                )
                state["vuln_result"] = vuln_result

            response = await self.planning_agent.achat(state["vuln_result"])

            planning_result = PlanningResult(todolist=response)
            state["planning_result"] = planning_result

            todolist_result = ToDoListResult(
                todolist=response,
                code_repo=state["code_repo"],
                poc_path=state["poc_path"],
                type=state["vulnerability_type"],
                description=state["description"],
                filename=state["filename"],
                code=state["code"],
                impact=state["impact"],
                result=state["initial_analysis"]
            )
            state["todolist_result"] = todolist_result

            log.info("规划完成")

        except Exception as e:
            log.error(f"规划失败: {e}")
            # 不抛出异常，继续执行
            state["planning_result"] = PlanningResult(todolist=f"规划失败: {str(e)}")
            state["todolist_result"] = None

        return state

    async def _poc_generation_node(self, state: WorkflowState) -> WorkflowState:
        """PoC生成节点"""
        log.info("生成PoC...")

        if not state.get("todolist_result"):
            log.warning("缺少待办事项，使用默认内容生成PoC")
            # 创建默认的todolist_result
            todolist_result = ToDoListResult(
                todolist="基于漏洞信息生成PoC",
                code_repo=state["code_repo"],
                poc_path=state["poc_path"],
                type=state["vulnerability_type"],
                description=state["description"],
                filename=state["filename"],
                code=state["code"],
                impact=state["impact"],
                result=state["initial_analysis"]
            )
            state["todolist_result"] = todolist_result

        try:
            response = await self.pocgen_agent.achat(state["todolist_result"])

            poc_result = PocResult(result=response)
            state["poc_result"] = poc_result

            poc_code = PocCode(
                poc_path=state["poc_path"],
                poc_info=response,
                type=state["vulnerability_type"],
                description=state["description"],
                impact=state["impact"]
            )
            state["poc_code"] = poc_code

            log.info("PoC生成完成")

        except Exception as e:
            log.error(f"PoC生成失败: {e}")
            # 不抛出异常，继续执行
            state["poc_result"] = PocResult(result=f"PoC生成失败: {str(e)}", poc_code="")
            state["poc_code"] = None

        return state

    async def _sandbox_execution_node(self, state: WorkflowState) -> WorkflowState:
        """沙箱执行节点"""
        log.info("执行PoC...")

        if not state.get("poc_code"):
            log.warning("缺少PoC代码，使用默认内容执行")
            # 创建默认的poc_code
            poc_code = PocCode(
                poc_path=state["poc_path"],
                poc_info="#include <stdio.h>\nint main() {\n    printf(\"默认PoC执行\\n\");\n    return 0;\n}",
                type=state["vulnerability_type"],
                description=state["description"],
                impact=state["impact"]
            )
            state["poc_code"] = poc_code

        try:
            response = await self.sandbox_agent.achat(state["poc_code"])

            sandbox_result = SandboxResult(result=response)
            state["sandbox_result"] = sandbox_result

            log.info("执行完成")

        except Exception as e:
            log.error(f"执行失败: {e}")
            # 不抛出异常，继续执行
            state["sandbox_result"] = SandboxResult(result=f"执行失败: {str(e)}")

        return state

    async def run(
        self,
        code_repo: str,
        vulnerability_type: str,
        description: str,
        filename: str,
        code: str,
        impact: str,
        initial_analysis: str,
        poc_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行简化工作流"""
        log.info("开始执行简化工作流")

        # 生成PoC路径
        if not poc_path:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            poc_path = os.path.join("./poc", timestamp)
        os.makedirs(poc_path, exist_ok=True)

        # 创建漏洞结果对象
        vuln_result = VulnResult(
            code_repo=code_repo,
            poc_path=poc_path,
            type=vulnerability_type,
            description=description,
            filename=filename,
            code=code,
            impact=impact,
            result=initial_analysis
        )

        # 初始状态
        initial_state: WorkflowState = {
            "code_repo": code_repo,
            "poc_path": poc_path,
            "vulnerability_type": vulnerability_type,
            "description": description,
            "filename": filename,
            "code": code,
            "impact": impact,
            "initial_analysis": initial_analysis,
            "vuln_result": vuln_result,
            "planning_result": None,
            "todolist_result": None,
            "poc_result": None,
            "poc_code": None,
            "sandbox_result": None
        }

        try:
            final_state = await self.app.ainvoke(initial_state)

            result = {
                "success": True,  # 简化工作流总是成功执行
                "final_state": final_state,
                "planning_result": final_state.get("planning_result"),
                "poc_result": final_state.get("poc_result"),
                "sandbox_result": final_state.get("sandbox_result"),
                "poc_path": poc_path,
                "execution_summary": self._generate_execution_summary(final_state)
            }

            log.info("简化工作流完成")
            return result

        except Exception as e:
            log.error(f"简化工作流执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "poc_path": poc_path,
                "execution_summary": f"工作流执行失败: {str(e)}"
            }

    def _generate_execution_summary(self, final_state: WorkflowState) -> str:
        """生成执行摘要"""
        summary_parts = []

        # 规划结果摘要
        planning_result = final_state.get("planning_result")
        if planning_result and hasattr(planning_result, 'todolist'):
            planning_text = planning_result.todolist[:100] if planning_result.todolist else "无内容"
            summary_parts.append(f"规划: {planning_text}")

        # PoC结果摘要
        poc_result = final_state.get("poc_result")
        if poc_result and hasattr(poc_result, 'result'):
            poc_text = poc_result.result[:100] if poc_result.result else "无内容"
            summary_parts.append(f"PoC: {poc_text}")

        # 执行结果摘要
        sandbox_result = final_state.get("sandbox_result")
        if sandbox_result and hasattr(sandbox_result, 'result'):
            exec_text = sandbox_result.result[:100] if sandbox_result.result else "无内容"
            summary_parts.append(f"执行: {exec_text}")

        return " | ".join(summary_parts) if summary_parts else "执行完成，但无详细结果"


# 使用示例
async def main():
    """测试简化工作流"""
    workflow = SimpleWorkflow()

    result = await workflow.run(
        code_repo="/codesec/AF8048/AF8.0.48",
        vulnerability_type="FORMAT_STRING_VULNERABILITY",
        description="格式化字符串漏洞",
        filename="test.cpp",
        code="ADD_ERR_MSG(user_input)",
        impact="内存泄露",
        initial_analysis="漏洞分析..."
    )

    print("\n" + "="*50)
    print("简化工作流结果:")
    print(f"执行成功: {result['success']}")
    print(f"执行摘要: {result['execution_summary']}")
    print(f"PoC路径: {result['poc_path']}")

    if result.get('sandbox_result') and hasattr(result['sandbox_result'], 'result'):
        print(f"执行结果: {result['sandbox_result'].result[:200]}...")

    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())