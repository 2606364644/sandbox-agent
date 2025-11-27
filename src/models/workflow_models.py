"""
工作流相关的数据模型定义
"""

from typing import Dict, Any, List, Optional, Literal, TypedDict
from pydantic import BaseModel, Field

from src.models.planning_models import PlanningResult
from src.models.poc_models import ToDoListResult, PocResult
from src.models.planning_models import VulnResult
from src.models.sandbox_models import PocCode, SandboxResult


class WorkflowState(TypedDict):
    """统一工作流状态 - TypedDict版本，专为LangGraph设计"""
    # 输入参数
    code_repo: str
    poc_path: str
    vulnerability_type: str
    description: str
    filename: str
    code: str
    impact: str
    initial_analysis: str

    # 流程状态
    vuln_result: VulnResult
    planning_result: Optional[PlanningResult]
    todolist_result: Optional[ToDoListResult]
    poc_result: Optional[PocResult]
    poc_code: Optional[PocCode]
    sandbox_result: Optional[SandboxResult]

    # 控制参数
    retry_count: int
    max_retries: int


class WorkflowInput(BaseModel):
    """通用工作流输入，支持不同步骤的数据传递"""
    execution_history: List[Dict[str, Any]] = Field(default_factory=list, description="执行历史")
    retry_count: int = Field(default=0, description="当前重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")
    failure_reason: Optional[str] = Field(None, description="失败原因")
