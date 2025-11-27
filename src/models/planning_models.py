from pydantic import BaseModel, Field


class VulnResult(BaseModel):
    code_repo: str = Field(..., description="代码仓库路径")
    poc_path: str = Field(..., description="PoC输出路径")
    type: str = Field(..., description="漏洞类型")
    description: str = Field(..., description="漏洞描述")
    filename: str = Field(..., description="漏洞触发点路径")
    code: str = Field(..., description="漏洞触发点")
    impact: str = Field(..., description="漏洞影响")
    result: str = Field(..., description="漏洞报告")


class PlanningResult(BaseModel):
    todolist: str = Field(description="你规划的todolist")
