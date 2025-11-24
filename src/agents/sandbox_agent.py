from typing import List, Dict
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI

from src.clients.glm_client import GlmProvider
from src.models.sandbox_models import VulnResult, SandboxResult
from src.prompt.sandbox_prompt import SYSTEM_PROMPT, USER_PROMPT
from src.tools.sandbox_tools import SANDBOX_TOOLS
from src.utils.logger import log


class SandboxAgent:
    """沙箱执行Agent类"""

    def __init__(
            self,
            model: ChatOpenAI = None,
            tool: List[BaseTool] = SANDBOX_TOOLS,
    ):
        self.model = model
        self.tools = tool
        self.system_prompt = SYSTEM_PROMPT

        # 创建Agent
        self.agent = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.system_prompt,
            response_format=ToolStrategy(SandboxResult)
        )

        # 对话历史
        self.chat_history = []

        # user prompt
        self.user_prompt = ChatPromptTemplate.from_template(
            USER_PROMPT,
            template_format="jinja2"
        ).partial()

    # def chat(self, message: str) -> str:
    #     # 添加用户消息到历史记录
    #     self.chat_history.append(HumanMessage(content=message))
    #
    #     # 调用Agent
    #     response = self.agent.invoke({
    #         "messages": self.chat_history
    #     })
    #
    #     # 提取回复内容
    #     ai_message = response["messages"][-1]
    #     reply = ai_message.content
    #
    #     # 添加AI回复到历史记录
    #     self.chat_history.append(AIMessage(content=reply))
    #
    #     return reply

    # async def achat(self, message: str) -> str:
    #     # 添加用户消息到历史记录
    #     self.chat_history.append(HumanMessage(content=message))
    #
    #     # 异步调用Agent
    #     response = await self.agent.ainvoke({
    #         "messages": self.chat_history
    #     })
    #
    #     # 提取回复内容
    #     ai_message = response["messages"][-1]
    #     reply = ai_message.content
    #
    #     # 添加AI回复到历史记录
    #     self.chat_history.append(AIMessage(content=reply))
    #
    #     return reply

    async def achat(self, message: VulnResult) -> str:

        # 组装prompt
        formatted_prompt = self.user_prompt.invoke({
            "type": message.type,
            "description": message.description,
            "filename": message.filename,
            "code": message.code,
            "impact": message.impact,
            "result": message.result
        })

        # 添加用户消息到历史记录
        self.chat_history.append(HumanMessage(content=str(formatted_prompt)))

        # 异步调用Agent
        response = await self.agent.ainvoke({
            "messages": [{"role": "user", "content": str(formatted_prompt)}]
        })

        # 提取回复内容
        reply = response["structured_response"]

        # 添加AI回复到历史记录
        self.chat_history.append(AIMessage(content=reply))

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
if __name__ == "__main__":
    # 测试结果
    vuln_result = VulnResult(
        type="FORMAT_STRING_VULNERABILITY",
        description="代码第1387行使用output.Eval函数将未经转义的path.c_str()作为格式化字符串参数传递。若path的值包含格式化字符串特殊字符（如%n），可能触发内存写入漏洞。触发点函数为Eval，受污染变量为path，其来源为pGrp->pPath，而pGrp通过用户输入的nCrc获取，存在潜在用户控制路径。",
        filename="af/business/user_auth/cgi/AcOrg/AcOrgCgi.cpp",
        code="""1387 | output.Eval("json.data.path='%s'",path.c_str());
1388 | output.Eval("json.data.name='%s'", JSON::Escape(pGrp->pGrpName).c_str());
1389 | output.Eval("json.data.desc='%s'", JSON::Escape(pGrp->pDesc).c_str());
        """.strip(),
        impact="攻击者可通过构造特殊路径字符串读取或修改内存内容，可能导致信息泄露或程序崩溃。由于path的来源依赖内部组结构，影响范围受限。",
        result="""
# 安全漏洞分析报告（修订版）

## 1. 安全漏洞存在性
**存在**：存在格式化字符串漏洞，HTTP接口`/api/acorg/group`的`nCrc`参数可控制`output.Eval`的格式化字符串参数，且未进行过滤。

## 2. 漏洞利用条件及触发方式
- **利用条件**：
  - 攻击者需发送特制HTTP请求到`/api/acorg/group`接口
  - 需要`nCrc`参数值能映射到包含`%n`的`pPath`路径
- **触发方式**：
  构造`nCrc`参数使`pGrp->pPath`包含`%n`，在`output.Eval`调用时触发内存写入

## 3. 数据流分析
```mermaid
graph TD
    A["/api/acorg/group POST请求"] --> B["AcOrgCgi::HandleRequest解析nCrc"]
    B --> C["GetGroupByCrc生成pGrp"]
    C --> D["pGrp->pPath赋值用户控制路径"]
    D --> E["output.Eval(path.c_str())格式化字符串漏洞"]
```

## 4. 关键代码片段

**路由绑定位置**：
```cpp
// af/business/user_auth/cgi/AcOrg/AcOrgCgi.cpp
extern "C" void RegisterAcOrgCgi() {
    CgiRouter::GetInstance()->RegisterHandler(
        "/api/acorg/group", 
        HTTP_METHOD_POST, 
        AcOrgCgi::HandleRequest
    );
}
```

**用户输入来源**：
```cpp
// af/business/user_auth/cgi/AcOrg/AcOrgCgi.cpp
int AcOrgCgi::HandleRequest(HttpRequest* req) {
    int nCrc = req->GetPostParamInt("nCrc"); // 直接从POST参数获取
    ...
    pGrp = GetGroupByCrc(nCrc);
    ...
    output.Eval(pGrp->pPath.c_str()); // 漏洞调用点
}
```

**参数解析流程**：
```cpp
// af/framework/http/HttpRequest.cpp
int HttpRequest::GetPostParamInt(const std::string& key) {
    std::string value = GetPostParam(key);
    return std::stoi(value); // 无输入校验
}
```

**危险函数调用链**：
```cpp
// af/business/user_auth/cgi/AcOrg/AcOrgCgi.cpp
void output.Eval(const char* format, ...) {
    va_list args;
    va_start(args, format);
    vprintf(format, args); // 未校验format来源
    va_end(args);
}
```

## 5. 总结
**漏洞类型**：格式化字符串漏洞
**修复建议**：
1. 修改调用方式为固定格式字符串：
```cpp
output.Eval("%s", pGrp->pPath.c_str());
```
2. 实现输入校验函数：
```cpp
SanitizeFormatString(pGrp->pPath); // 移除%n等危险字符
```
3. 在`GetPostParamInt`增加参数长度和格式校验
4. 对`pGrp->pPath`赋值前进行路径规范化处理""".strip()
    )

    model = GlmProvider().create_client()
    agent = SandboxAgent(model=model)
    response = agent.achat(vuln_result)
    log.info(f"res: {response}")

    # TODO 遍历结果

    # # 简单对话
    # print("=== 简化版Agent演示 ===")
    # response = agent.chat("你好，我是用户！")
    # print(f"用户: 你好，我是用户！")
    # print(f"助手: {response}")
    #
    # # 使用工具
    # response = agent.chat("计算 15 + 8 * 3")
    # print(f"用户: 计算 15 + 8 * 3")
    # print(f"助手: {response}")
    #
    # response = agent.chat("北京的天气怎么样？")
    # print(f"用户: 北京的天气怎么样？")
    # print(f"助手: {response}")
    #
    # # 查看对话历史
    # print("\n=== 对话历史 ===")
    # for msg in agent.get_history():
    #     print(f"{msg['role']}: {msg['content']}")