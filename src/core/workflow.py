"""
统一简化版工作流
整合simplified_evaluator_optimizer.py和workflow.py，以简单流程为主
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


class Workflow:
    """统一简化工作流 - 整合两个版本，保持简单"""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        # 使用抽象层自动选择客户端
        self.model = get_llm_client()

        self.planning_agent = PlanningAgent(model=self.model)
        self.pocgen_agent = PocGenAgent(model=self.model)
        self.sandbox_agent = SandboxAgent(model=self.model)

        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()

        log.info("统一简化工作流初始化完成")

    def _build_workflow(self) -> StateGraph:
        """构建简单线性工作流"""
        workflow = StateGraph(WorkflowState)

        workflow.add_node("planning", self._planning_node)
        workflow.add_node("poc_generation", self._poc_generation_node)
        workflow.add_node("sandbox_execution", self._sandbox_execution_node)

        workflow.add_edge(START, "planning")
        workflow.add_edge("planning", "poc_generation")
        workflow.add_edge("poc_generation", "sandbox_execution")

        workflow.add_conditional_edges(
            "sandbox_execution",
            self._should_continue_or_retry,
            {
                "success": END,
                "retry_planning": "planning",
                "retry_poc": "poc_generation",
                "abort": END
            }
        )

        return workflow

    async def _planning_node(self, state: WorkflowState) -> WorkflowState:
        """规划节点"""
        log.info("开始规划...")

        try:
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
            raise

        return state

    async def _poc_generation_node(self, state: WorkflowState) -> WorkflowState:
        """PoC生成节点"""
        log.info("生成PoC...")

        if not state["todolist_result"]:
            log.error("缺少待办事项，无法生成PoC")
            raise ValueError("缺少待办事项，无法生成PoC")

        try:
            response = await self.pocgen_agent.achat(state["todolist_result"])

            poc_result = PocResult(result=response, poc_code=response)
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
            raise

        return state

    async def _sandbox_execution_node(self, state: WorkflowState) -> WorkflowState:
        """沙箱执行节点"""
        log.info("执行PoC...")

        if not state["poc_code"]:
            log.error("缺少PoC代码，无法执行")
            raise ValueError("缺少PoC代码，无法执行")

        try:
            response = await self.sandbox_agent.achat(state["poc_code"])

            sandbox_result = SandboxResult(result=response)
            state["sandbox_result"] = sandbox_result

            log.info("执行完成")

        except Exception as e:
            log.error(f"执行失败: {e}")
            raise

        return state

    def _should_continue_or_retry(self, state: WorkflowState) -> str:
        """决策：继续还是重试"""
        retry_count = state.get("retry_count", 0)

        if retry_count >= state["max_retries"]:
            log.warning(f"达到最大重试次数 {state['max_retries']}，中止")
            return "abort"

        sandbox_result = state.get("sandbox_result")
        if not sandbox_result:
            return "retry_planning"

        result_text = sandbox_result.result.lower()

        success_keywords = [
            "漏洞验证成功", "vulnerability confirmed", "内存地址",
            "0x", "leaked", "格式化字符串", "exploit", "payload"
        ]

        failure_keywords = [
            "编译错误", "compile error", "syntax error",
            "runtime error", "segmentation fault"
        ]

        if any(keyword in result_text for keyword in success_keywords):
            log.info("验证成功！")
            return "success"

        state["retry_count"] = retry_count + 1

        if any(keyword in result_text for keyword in failure_keywords):
            log.info(f"第{state['retry_count']}次重试: 代码问题，重新生成PoC")
            return "retry_poc"
        else:
            log.info(f"第{state['retry_count']}次重试: 重新规划")
            return "retry_planning"

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
        """运行统一工作流"""
        log.info("开始执行统一简化工作流")

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
            "sandbox_result": None,
            "retry_count": 0,
            "max_retries": self.max_retries
        }

        try:
            final_state = await self.app.ainvoke(initial_state)

            result = {
                "success": final_state.get("retry_count", 0) < self.max_retries and
                          final_state.get("sandbox_result") is not None,
                "final_state": final_state,
                "retry_count": final_state.get("retry_count", 0),
                "planning_result": final_state.get("planning_result"),
                "poc_result": final_state.get("poc_result"),
                "sandbox_result": final_state.get("sandbox_result"),
                "poc_path": poc_path
            }

            log.info(f"工作流完成: {'成功' if result['success'] else '部分成功'}")
            return result

        except Exception as e:
            log.error(f"工作流执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "retry_count": initial_state.get("retry_count", 0),
                "poc_path": poc_path
            }


# 使用示例
async def main():
    """测试统一工作流"""
    workflow = Workflow(max_retries=2)

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
    print("统一简化工作流结果:")
    print(f"成功: {result['success']}")
    print(f"重试次数: {result['retry_count']}")
    if result.get("sandbox_result"):
        print(f"执行结果: {result['sandbox_result'].result[:100]}...")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())