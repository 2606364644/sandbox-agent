from pydantic import BaseModel, Field


class PocCode(BaseModel):
    poc_path: str = Field(..., description="poc路径")
    poc_info: str = Field(..., description="poc代码详细介绍")
    type: str = Field(..., description="漏洞类型")
    description: str = Field(..., description="漏洞描述")
    impact: str = Field(..., description="漏洞影响")


class SandboxResult(BaseModel):
    result: str = Field(..., description="PoC的执行结果，以及你对结果的分析过程和结论")
