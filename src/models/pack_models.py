from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PackRequest(BaseModel):
    """打包请求"""
    repo_path: str = Field(description="微服务代码仓库路径")
    docker_image_name: Optional[str] = Field(None, description="Docker镜像名称，默认为仓库名")
    docker_tag: Optional[str] = Field("latest", description="Docker标签")
    build_context: Optional[str] = Field(".", description="构建上下文路径")
    dockerfile_path: Optional[str] = Field("Dockerfile", description="Dockerfile路径")
    build_args: Optional[Dict[str, str]] = Field(None, description="构建参数")
    environment: Optional[str] = Field("development", description="环境类型：development, staging, production")


class BuildScript(BaseModel):
    """构建脚本信息"""
    script_path: str = Field(description="脚本路径")
    script_type: str = Field(description="脚本类型：shell, python, npm, maven, gradle等")
    description: Optional[str] = Field(None, description="脚本描述")
    priority: int = Field(1, description="优先级，数字越小优先级越高")


class PackResult(BaseModel):
    """打包结果"""
    success: bool = Field(description="是否成功")
    image_name: Optional[str] = Field(None, description="生成的镜像名称")
    image_id: Optional[str] = Field(None, description="镜像ID")
    build_output: str = Field(description="构建输出")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(description="执行时间（秒）")
    docker_commands_used: List[str] = Field(default_factory=list, description="使用的Docker命令")
    build_scripts_used: List[str] = Field(default_factory=list, description="使用的构建脚本")
    retry_count: int = Field(0, description="重试次数")


class PackWorkflowState(BaseModel):
    """打包工作流状态"""
    pack_request: PackRequest
    current_step: str = "initialization"
    build_scripts: List[BuildScript] = Field(default_factory=list)
    pack_result: Optional[PackResult] = None
    error_history: List[str] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 5
    success: bool = False
    error_analysis: Optional[Dict[str, Any]] = None