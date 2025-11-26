import asyncio
import os
from datetime import datetime
from typing import List, Dict
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.middleware import (
    ShellToolMiddleware,
    HostExecutionPolicy,
)
from langchain.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI

from src.agents.base_agent import BaseAgent
from src.clients.openai_client import OpenAIProvider
from src.models.sandbox_models import PocCode, SandboxResult
from src.prompt.sandbox_prompt import SYSTEM_PROMPT, USER_PROMPT
from src.tools.sandbox_tools import SANDBOX_TOOLS
from src.utils.logger import log


class SandboxAgent(BaseAgent):
    """沙箱执行Agent类"""

    def __init__(
            self,
            workspace_root: str = None,
            model: ChatOpenAI = None,
            tool: List[BaseTool] = SANDBOX_TOOLS,
    ):
        super().__init__()

        self.model = model
        self.tools = tool
        self.system_prompt = SYSTEM_PROMPT

        # 创建Agent
        self.agent = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.system_prompt,
            middleware=[
                ShellToolMiddleware(
                    workspace_root=workspace_root,
                    execution_policy=HostExecutionPolicy(),
                ),
            ],
            # response_format=ToolStrategy(SandboxResult),
        )

        # 对话历史
        self.chat_history = []

        # user prompt
        self.user_prompt = ChatPromptTemplate.from_template(
            USER_PROMPT,
            template_format="jinja2"
        ).partial()

    async def achat(self, message: PocCode) -> str:

        # 组装prompt
        formatted_prompt = self.user_prompt.invoke(message.model_dump())

        # 添加用户消息到历史记录
        self.chat_history.append(HumanMessage(content=str(formatted_prompt)))

        # 异步调用Agent
        response = await self.agent.ainvoke({
            "messages": [{"role": "user", "content": str(formatted_prompt)}]
        })

        # 提取回复内容
        ai_message = response["messages"][-1]
        reply = ai_message.content

        # 添加AI回复到历史记录
        self.chat_history.append(ai_message)

        return reply

    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        history = []
        for msg in self.chat_history:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        return history

    def clear_history(self):
        """清空对话历史"""
        self.chat_history = []


# 使用示例
async def main():
    # 测试结果
    poc_path = ""
    poc = PocCode(
        poc_path="/codesec/gjy/sandbox-agent/poc/20251125-090908",
        poc_info="我已经成功根据ToDoList生成了完整的格式化字符串漏洞验证代码。以下是生成的文件和功能说明：\n\n### 📁 生成的文件\n\n1. **`poc_format_string.cpp`** - 主要的PoC验证代码\n2. **`test_payloads.cpp`** - 多种Payload测试程序\n3. **`compile_and_run.sh`** - 编译运行脚本\n4. **`Makefile`** - 构建配置文件\n5. **`README.md`** - 详细说明文档\n\n### 🎯 核心验证逻辑\n\n**完整数据流模拟**：\n- **[数据流入口]**: `main()`函数中的`payload`变量（模拟HTTP请求参数`json.name`）\n- **[污点传播]**: `userInput` → `names.push_back()` → `(*it).c_str()` → `ADD_ERR_MSG`宏\n- **[漏洞触发点]**: `CString::Format()`中的`vsnprintf(line, allocated - 1, lpszFormat, apbak)`\n\n**可观测的验证结果**：\n- 使用`\"%p%p%p%p%p%p%p%p\"`Payload泄露栈内存地址\n- 程序会输出类似`Error: 0x7ff...0x7ff...0x7ff...`的内存地址\n- 自动检测是否成功泄露内存地址并给出验证结果\n\n### ✅ 独立可执行性\n\n- 包含所有必要的头文件：`<iostream>`, `<vector>`, `<string>`, `<cstdio>`, `<cstdarg>`, `<cstring>`\n- 完整的`CString`类模拟，包含内存管理和`Format`方法\n- 模拟了`ADD_ERR_MSG`宏和`ID2STR`宏\n- 包含`main()`函数入口，可直接编译运行\n\n### 🚀 运行方法\n\n```bash\n# 方法1: 使用脚本\nchmod +x compile_and_run.sh\n./compile_and_run.sh\n\n# 方法2: 使用Makefile\nmake run\n\n# 方法3: 手动编译\ng++ -o poc_format_string poc_format_string.cpp -std=c++11\n./poc_format_string\n```\n\n### 🔍 预期验证结果\n\n程序运行后将显示：\n1. 构造的恶意Payload信息\n2. 漏洞触发过程\n3. 包含泄露内存地址的错误消息\n4. 自动验证结果分析\n5. 漏洞原理说明\n\n当看到输出中包含`0x`开头的内存地址时，证明格式化字符串漏洞被成功触发，验证了`tamperAdminView.cpp`第1015行的安全漏洞。\n\nPoC代码已准备就绪，可以交给下一个同事执行验证。",
        type="FORMAT_STRING_VULNERABILITY",
        description="在第1015行，ADD_ERR_MSG函数的第二个参数直接使用了来自用户输入的字符串(*it).c_str()，该字符串可能包含格式化说明符(如%s、%n等)，导致格式化字符串漏洞。当用户输入包含特殊格式化字符时，可能被利用读取或写入内存，造成信息泄露或潜在代码执行。",
        impact="攻击者可以通过构造包含格式化说明符的输入，导致程序读取或写入任意内存地址，可能造成敏感信息泄露或拒绝服务攻击。",
    )

    model = OpenAIProvider().create_client()
    model.with_structured_output(SandboxResult)

    agent = SandboxAgent(workspace_root=poc_path, model=model)

    # log.info(f"vuln_result: {vuln_result}")
    response = await agent.achat(poc)
    log.info(f"res: {response}")

    # TODO 遍历结果


if __name__ == "__main__":
    log.info(f"Start...")
    asyncio.run(main())