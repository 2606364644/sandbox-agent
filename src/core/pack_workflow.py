"""
自动打包工作流 - 基于langgraph的智能重试工作流
用于将微服务自动打包成Docker容器，具有智能错误分析和重试策略
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.autopack_agent import AutoPackAgent
from src.clients import get_llm_client
from src.models.pack_models import PackRequest, PackResult, PackWorkflowState
from src.utils.logger import log


class PackWorkflow:
    """智能打包工作流 - 使用langgraph实现智能重试和错误分析"""

    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries
        self.model = get_llm_client()
        self.pack_agent = AutoPackAgent(model=self.model, max_retries=1)  # 单次尝试，工作流控制重试

        # 构建工作流
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile(checkpointer=MemorySaver())

        log.info("智能打包工作流初始化完成")

    def _build_workflow(self) -> StateGraph:
        """构建打包工作流"""
        workflow = StateGraph(PackWorkflowState)

        # 添加节点
        workflow.add_node("analyze_project", self._analyze_project_node)
        workflow.add_node("attempt_pack", self._attempt_pack_node)
        workflow.add_node("analyze_error", self._analyze_error_node)
        workflow.add_node("adjust_strategy", self._adjust_strategy_node)

        # 定义流程
        workflow.add_edge(START, "analyze_project")
        workflow.add_edge("analyze_project", "attempt_pack")
        workflow.add_edge("attempt_pack", "analyze_error")

        # 条件边：根据错误分析结果决定下一步
        workflow.add_conditional_edges(
            "analyze_error",
            self._decide_next_action,
            {
                "success": END,
                "retry": "adjust_strategy",
                "abort": END
            }
        )

        workflow.add_edge("adjust_strategy", "attempt_pack")

        return workflow

    async def _analyze_project_node(self, state: PackWorkflowState) -> PackWorkflowState:
        """分析项目节点 - 分析项目结构和构建需求"""
        log.info("开始分析项目...")

        try:
            from pathlib import Path

            repo_path = Path(state.pack_request.repo_path)
            if not repo_path.exists():
                state.error_history.append(f"项目路径不存在: {repo_path}")
                return state

            # 检测项目类型和构建脚本
            build_scripts = await self.pack_agent._detect_build_scripts(repo_path)
            state.build_scripts = build_scripts

            # 分析项目特性
            project_type = self.pack_agent._analyze_project_type(build_scripts)
            log.info(f"项目类型: {project_type}")

            # 生成初始策略
            strategy = {
                "project_type": project_type,
                "detected_scripts": [script.script_path for script in build_scripts],
                "strategy": "standard",
                "reasoning": "使用标准打包策略"
            }

            state.current_step = "project_analyzed"
            log.info(f"项目分析完成，检测到 {len(build_scripts)} 个构建脚本")

        except Exception as e:
            log.error(f"项目分析失败: {e}")
            state.error_history.append(f"项目分析异常: {e}")

        return state

    async def _attempt_pack_node(self, state: PackWorkflowState) -> PackWorkflowState:
        """尝试打包节点 - 执行单次打包尝试"""
        log.info(f"第 {state.retry_count + 1} 次尝试打包...")

        try:
            # 执行打包
            pack_result = await self.pack_agent._attempt_pack(
                state.pack_request,
                state.retry_count
            )

            state.pack_result = pack_result
            state.current_step = "pack_attempted"

            if pack_result.success:
                log.info("打包成功！")
                state.success = True
            else:
                log.warning(f"打包失败: {pack_result.error_message}")
                state.error_history.append(f"尝试 {state.retry_count + 1} 失败: {pack_result.error_message}")

        except Exception as e:
            log.error(f"打包尝试异常: {e}")
            state.error_history.append(f"尝试 {state.retry_count + 1} 异常: {e}")

            # 创建失败结果
            state.pack_result = PackResult(
                success=False,
                error_message=str(e),
                build_output="",
                retry_count=state.retry_count
            )

        return state

    async def _analyze_error_node(self, state: PackWorkflowState) -> PackWorkflowState:
        """错误分析节点 - 使用LLM分析失败原因并生成解决方案"""
        if state.success:
            return state

        log.info("开始分析打包失败原因...")

        try:
            # 准备错误分析提示
            error_analysis_prompt = self._create_error_analysis_prompt(state)

            # 使用LLM分析错误
            response = await self.model.ainvoke([
                {"role": "system", "content": "你是一个资深的DevOps工程师，擅长分析Docker构建错误并提供解决方案。"},
                {"role": "user", "content": error_analysis_prompt}
            ])

            # 解析LLM响应
            analysis = self._parse_error_analysis(response.content)

            # 将分析结果存储在状态中
            state.error_analysis = analysis
            state.current_step = "error_analyzed"

            log.info(f"错误分析完成: {analysis['category']} - {analysis['suggested_action']}")

        except Exception as e:
            log.error(f"错误分析失败: {e}")
            state.error_history.append(f"错误分析异常: {e}")

            # 提供默认分析
            state.error_analysis = {
                "category": "unknown",
                "root_cause": "无法分析错误原因",
                "suggested_action": "standard_retry",
                "confidence": 0.1
            }

        return state

    def _create_error_analysis_prompt(self, state: PackWorkflowState) -> str:
        """创建错误分析提示"""
        pack_result = state.pack_result
        build_scripts_info = "\n".join([
            f"- {script.script_path} ({script.script_type})"
            for script in state.build_scripts
        ])

        prompt = f"""
请分析以下Docker构建失败情况，并提供解决方案：

**项目信息：**
- 项目路径: {state.pack_request.repo_path}
- 镜像名称: {state.pack_request.docker_image_name}
- 环境类型: {state.pack_request.environment}

**检测到的构建脚本：**
{build_scripts_info}

**构建错误信息：**
{pack_result.error_message}

**构建输出：**
{pack_result.build_output[-2000:] if len(pack_result.build_output) > 2000 else pack_result.build_output}

**历史重试情况：**
- 当前重试次数: {state.retry_count}/{state.max_retries}
- 历史错误: {'; '.join(state.error_history[-3:])}

请分析：
1. 错误类型（如：依赖问题、配置错误、权限问题、网络问题等）
2. 根本原因
3. 建议的解决方案（如：修改Dockerfile、更新依赖、调整配置等）
4. 成功解决的概率评估
5. 是否应该继续重试

请以JSON格式返回分析结果：
{{
    "category": "错误类型",
    "root_cause": "根本原因分析",
    "suggested_action": "建议行动",
    "specific_fixes": ["具体修复建议1", "具体修复建议2"],
    "confidence": 0.8,
    "should_retry": true,
    "reasoning": "详细分析过程"
}}
"""
        return prompt

    def _parse_error_analysis(self, response: str) -> Dict[str, Any]:
        """解析LLM的错误分析响应"""
        try:
            # 尝试解析JSON
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass

        # JSON解析失败，返回默认分析
        return {
            "category": "analysis_failed",
            "root_cause": "无法解析错误分析结果",
            "suggested_action": "standard_retry",
            "specific_fixes": [],
            "confidence": 0.3,
            "should_retry": True,
            "reasoning": "基于LLM响应的文本分析：检查构建输出中的常见错误模式"
        }

    def _decide_next_action(self, state: PackWorkflowState) -> str:
        """决定下一步行动"""
        # 如果已经成功，直接结束
        if state.success:
            return "success"

        # 检查是否超过最大重试次数
        if state.retry_count >= state.max_retries:
            log.warning(f"达到最大重试次数 {state.max_retries}，中止")
            return "abort"

        # 基于错误分析决定是否继续
        error_analysis = getattr(state, 'error_analysis', {})

        if error_analysis.get('should_retry', False) and error_analysis.get('confidence', 0) > 0.3:
            log.info(f"根据错误分析，继续重试 (置信度: {error_analysis.get('confidence', 0)})")
            return "retry"
        else:
            log.warning("错误分析建议中止重试")
            return "abort"

    async def _adjust_strategy_node(self, state: PackWorkflowState) -> PackWorkflowState:
        """调整策略节点 - 根据错误分析调整打包策略"""
        log.info("根据错误分析调整打包策略...")

        try:
            error_analysis = getattr(state, 'error_analysis', {})
            suggested_action = error_analysis.get('suggested_action', 'standard_retry')
            specific_fixes = error_analysis.get('specific_fixes', [])

            # 根据建议调整打包请求
            if suggested_action == 'modify_dockerfile':
                state.pack_request = self._adjust_dockerfile_strategy(state.pack_request, specific_fixes)
            elif suggested_action == 'update_dependencies':
                state.pack_request = self._adjust_dependencies_strategy(state.pack_request, specific_fixes)
            elif suggested_action == 'change_build_context':
                state.pack_request = self._adjust_build_context_strategy(state.pack_request, specific_fixes)
            elif suggested_action == 'modify_build_args':
                state.pack_request = self._adjust_build_args_strategy(state.pack_request, specific_fixes)

            # 增加重试次数
            state.retry_count += 1
            state.current_step = "strategy_adjusted"

            log.info(f"策略调整完成，准备第 {state.retry_count + 1} 次尝试")

        except Exception as e:
            log.error(f"策略调整失败: {e}")
            state.error_history.append(f"策略调整异常: {e}")
            state.retry_count += 1

        return state

    def _adjust_dockerfile_strategy(self, pack_request: PackRequest, fixes: list) -> PackRequest:
        """调整Dockerfile策略"""
        # 这里可以实现更复杂的Dockerfile修改逻辑
        # 暂时返回调整后的请求
        adjusted_request = pack_request.model_copy(deep=True)
        adjusted_request.dockerfile_path = "Dockerfile.modified"
        return adjusted_request

    def _adjust_dependencies_strategy(self, pack_request: PackRequest, fixes: list) -> PackRequest:
        """调整依赖策略"""
        adjusted_request = pack_request.model_copy(deep=True)

        # 添加构建参数来处理依赖问题
        if not adjusted_request.build_args:
            adjusted_request.build_args = {}

        adjusted_request.build_args.update({
            "NODE_OPTIONS": "--max-old-space-size=4096",
            "PIP_NO_CACHE_DIR": "1"
        })

        return adjusted_request

    def _adjust_build_context_strategy(self, pack_request: PackRequest, fixes: list) -> PackRequest:
        """调整构建上下文策略"""
        adjusted_request = pack_request.model_copy(deep=True)
        adjusted_request.build_context = "."
        return adjusted_request

    def _adjust_build_args_strategy(self, pack_request: PackRequest, fixes: list) -> PackRequest:
        """调整构建参数策略"""
        adjusted_request = pack_request.model_copy(deep=True)

        if not adjusted_request.build_args:
            adjusted_request.build_args = {}

        # 根据修复建议添加构建参数
        for fix in fixes:
            if "http_proxy" in fix.lower():
                adjusted_request.build_args["http_proxy"] = "http://proxy:8080"
            elif "https_proxy" in fix.lower():
                adjusted_request.build_args["https_proxy"] = "http://proxy:8080"

        return adjusted_request

    async def run(self, pack_request: PackRequest, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """运行智能打包工作流"""
        log.info("开始执行智能打包工作流")

        # 创建初始状态
        initial_state = PackWorkflowState(
            pack_request=pack_request,
            current_step="initialization",
            build_scripts=[],
            pack_result=None,
            error_history=[],
            retry_count=0,
            max_retries=self.max_retries,
            success=False
        )

        # 配置工作流执行参数
        config = {"configurable": {"thread_id": thread_id or datetime.now().isoformat()}}

        try:
            # 执行工作流
            final_state = await self.app.ainvoke(initial_state, config=config)

            # 准备返回结果
            result = {
                "success": final_state.success,
                "pack_result": final_state.pack_result,
                "retry_count": final_state.retry_count,
                "error_history": final_state.error_history,
                "build_scripts_found": [script.dict() for script in final_state.build_scripts],
                "thread_id": config["configurable"]["thread_id"],
                "execution_steps": self._extract_execution_steps(final_state)
            }

            log.info(f"工作流完成: {'成功' if result['success'] else '失败'}")
            return result

        except Exception as e:
            log.error(f"工作流执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "retry_count": initial_state.retry_count,
                "error_history": initial_state.error_history
            }

    def _extract_execution_steps(self, state: PackWorkflowState) -> List[str]:
        """提取执行步骤"""
        steps = []

        if hasattr(state, 'current_step'):
            steps.append(f"final_state: {state.current_step}")

        if state.build_scripts:
            steps.append(f"detected_scripts: {len(state.build_scripts)}")

        if hasattr(state, 'error_analysis'):
            steps.append(f"error_category: {state.error_analysis.get('category', 'unknown')}")

        return steps


# 使用示例
async def main():
    """测试智能打包工作流"""
    workflow = PackWorkflow(max_retries=3)

    pack_request = PackRequest(
        repo_path="/path/to/your/microservice",
        docker_image_name="my-smart-service",
        docker_tag="v1.0.0",
        environment="production"
    )

    result = await workflow.run(pack_request)

    print("\n" + "="*60)
    print("智能打包工作流结果:")
    print(f"成功: {result['success']}")
    print(f"重试次数: {result['retry_count']}")
    print(f"检测到的构建脚本: {len(result['build_scripts_found'])}")
    print(f"执行步骤: {result['execution_steps']}")

    if result['pack_result']:
        pack_result = result['pack_result']
        print(f"镜像名称: {pack_result.image_name}")
        print(f"执行时间: {pack_result.execution_time:.2f}秒")

    if result['error_history']:
        print("错误历史:")
        for i, error in enumerate(result['error_history'], 1):
            print(f"  {i}. {error}")

    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())