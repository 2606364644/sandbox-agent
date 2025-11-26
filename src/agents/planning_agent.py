import asyncio
import os
from datetime import datetime
from typing import List, Dict, Union
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
from langchain.agents.middleware import FilesystemFileSearchMiddleware, SummarizationMiddleware
from langchain.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI

from src.agents.base_agent import BaseAgent
from src.clients.openai_client import OpenAIProvider
from src.models.planning_models import PlanningResult
from src.models.sandbox_models import VulnResult
from src.prompt.planning_prompt import SYSTEM_PROMPT, USER_PROMPT
from src.tools.sandbox_tools import POC_AGENT_TOOLS
from src.utils.logger import log
from src.tools.common.system_tools import save_conversation_history


class PlanningAgent(BaseAgent):
    """沙箱执行Agent类"""

    def __init__(
            self,
            search_file_path: str = None,
            model: ChatOpenAI = None,
            tool: List[BaseTool] = POC_AGENT_TOOLS,
    ):
        super().__init__()

        self.model = model
        self.tools = tool
        self.system_prompt = SYSTEM_PROMPT

        # 创建Agent
        self.agent = create_agent(
            model=self.model,
            system_prompt=self.system_prompt,
            # response_format=PlanningResult,
            # response_format=ToolStrategy(
            #     PlanningResult,
            # ),
            # response_format=Union[
            #     ToolStrategy[PlanningResult],
            #     type[PlanningResult],
            # ]
        )

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
            "code_repo": message.code_repo,
            "poc_path": message.poc_path,
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
        # reply = response["structured_response"]
        # reply = response["messages"][-1].text
        ai_message = response["messages"][-1]
        reply = ai_message.content

        # 添加AI回复到历史记录
        # self.chat_history.append(AIMessage(content=str(reply)))
        self.chat_history.append(ai_message)

        return reply


# 使用示例
async def main():
    # 生成时间戳路径：年月日-时分秒
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    poc_path = os.path.join("./poc", timestamp)

    # 确保目录存在
    os.makedirs(poc_path, exist_ok=True)

    # 测试结果
    vuln_result = VulnResult(
        code_repo="/codesec/AF8048/AF8.0.48",
        poc_path=poc_path,
        type="FORMAT_STRING_VULNERABILITY",
        description="在第1015行，ADD_ERR_MSG函数的第二个参数直接使用了来自用户输入的字符串(*it).c_str()，该字符串可能包含格式化说明符(如%s、%n等)，导致格式化字符串漏洞。当用户输入包含特殊格式化字符时，可能被利用读取或写入内存，造成信息泄露或潜在代码执行。",
        filename="webui/cgi/server/tamper_admin/tamperAdminView.cpp",
        code="""
1011 |+ 	for (vector<string>::iterator it = names.begin(); it != names.end(); it++) {
1012 |+ 		string out_name;
1013 |+ 		ret = CheckDeleteDepend(*it, out_name);
1014 |+ 		if (ret) {
1015 |+ 			ADD_ERR_MSG(ID2STR("IDS_ERR_DELETE_DEPEND"), (*it).c_str());
1016 |+ 			ShowErrMsg();
        """.strip(),
        impact="攻击者可以通过构造包含格式化说明符的输入，导致程序读取或写入任意内存地址，可能造成敏感信息泄露或拒绝服务攻击。",
        result="""
# 安全漏洞分析报告

## 1. 安全漏洞存在性
**存在**：存在格式化字符串漏洞，函数`CString::Format`直接将用户输入作为格式化字符串参数使用，未对输入中的格式化说明符进行过滤或转义。

## 2. 漏洞利用条件及触发方式
- **利用条件**：
  - 攻击者需能控制HTTP请求中的`json.name`参数
  - 需要存在可触发`/tamper_admin/tamperAdminView`接口的权限
- **触发方式**：
  通过构造包含格式化说明符的恶意`json.name`参数（如`%s%p%x%d`），在调用`ADD_ERR_MSG`宏时触发格式化字符串漏洞，可能导致内存信息泄露或程序崩溃。

## 3. 数据流分析
```mermaid
graph TD
    A["/tamper_admin/tamperAdminView HTTP接口"] --> |HTTP请求参数 json.name| B["CTAdminView::ProcessRequest"]
    B --> |污点变量 json.name| C["JSON::GetString"]
    C --> |污点变量 strName| D["names.push_back"]
    D --> |污点变量 (*it).c_str()| E["ADD_ERR_MSG宏"]
    E --> |污点变量 fmt| F["CString::Format"]
    F --> G["格式化字符串漏洞"]
```

## 4. 关键代码片段

**路由绑定位置**：
```cpp
// webui/cgi/server/tamper_admin/tamperAdminView.cpp
void CTAdminView::ProcessRequest(CHttpRequest &req, CHttpResponse &resp)
{
    // HTTP请求处理入口
}
```

**用户输入来源**：
```cpp
// webui/cgi/server/tamper_admin/tamperAdminView.cpp
JSON::GetString(json, "name", strName);  // 从HTTP请求获取json.name参数
names.push_back(strName);  // 将用户输入存入vector

for(vector<CString>::iterator it = names.begin(); it != names.end(); it++)
{
    ADD_ERR_MSG((*it).c_str(), 0);  // 直接将用户输入作为格式化字符串
}
```

**ADD_ERR_MSG宏定义**：
```cpp
// webui/cgi/server/tamper_admin/tamperAdminView.cpp
#define ADD_ERR_MSG(fmt, ...) \
    do { \
        m_csBuf.Format(fmt, ##__VA_ARGS__); \
        m_ErrMsg += m_csBuf; \
        m_ErrMsg += "\n"; \
    } while(0)
```

**危险函数实现**：
```cpp
// shared/lib/cstring.cpp
void AFX_CDECL CString::Format(LPCTSTR lpszFormat, ...)
{
    char *line;
    int allocated = 2048, result = allocated;
    va_list ap, apbak;
    va_start(ap, lpszFormat);  // lpszFormat直接来自用户输入
    line = (char*)malloc(allocated);
    while (line)
    {
        va_copy(apbak,ap);
        result = vsnprintf(line, allocated - 1, lpszFormat, apbak);  // 直接使用用户输入作为格式化字符串
        va_end(apbak);
        if (result < allocated - 1)
        {
            line[result] = '\0';
            break;
        }
        allocated += result;
        line = (char*)realloc(line, allocated);
    }
    if (line)
    {
        operator=(line);
    }
    else
        operator=("");
    if (line)
        free(line);
}
```

## 5. 总结
**漏洞类型**：格式化字符串漏洞
**漏洞原理**：`CString::Format`方法直接将用户输入的字符串作为格式化字符串参数传递给`vsnprintf`函数，当用户输入包含格式化说明符（如`%s`、`%p`、`%x`、`%d`、`%n`等）时，会导致：
1. **信息泄露**：通过`%p`、`%x`等说明符读取栈内存中的敏感信息
2. **拒绝服务**：通过构造特殊格式化字符串导致程序崩溃
3. **潜在代码执行**：在某些环境下，通过`%n`说明符可能实现任意内存写入

**修复建议**：
1. 使用硬编码的格式化字符串，将用户输入作为参数传递：
   ```cpp
   #define ADD_ERR_MSG(fmt, ...) \
       do { \
           m_csBuf.Format("%s", fmt); \
           m_ErrMsg += m_csBuf; \
           m_ErrMsg += "\n"; \
       } while(0)
   ```
2. 对用户输入进行过滤，移除或转义格式化说明符：
   ```cpp
   CString SafeFormatString(const CString& input) {
       CString safe = input;
       safe.Replace("%", "%%");
       return safe;
   }
   ```
3. 实现输入验证，限制用户输入的字符集
4. 使用安全的字符串格式化函数，确保格式化字符串来自可信源
        """.strip()
    )

    model = OpenAIProvider().create_client()
    model.with_structured_output(PlanningResult)

    agent = PlanningAgent(search_file_path=vuln_result.code_repo, model=model)

    # log.info(f"vuln_result: {vuln_result}")
    response = await agent.achat(vuln_result)
    log.info(f"res: {response}")

    # TODO 遍历结果


if __name__ == "__main__":
    log.info(f"Start...")
    asyncio.run(main())
