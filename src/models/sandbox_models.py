from pydantic import BaseModel, Field


class VulnResult(BaseModel):
    type: str = Field(..., description="漏洞类型")
    description: str = Field(..., description="漏洞描述")
    filename: str = Field(..., description="漏洞触发点路径")
    code: str = Field(..., description="漏洞触发点")
    impact: str = Field(..., description="漏洞影响")
    result: str = Field(..., description="漏洞报告")


class SandboxResult(BaseModel):
    result: str = Field(..., description="沙箱执行结果")
