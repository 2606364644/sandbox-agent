import asyncio
import os
from datetime import datetime
from typing import List, Dict
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.middleware import FilesystemFileSearchMiddleware, SummarizationMiddleware
from langchain.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI

from src.agents.base_agent import BaseAgent
from src.clients.openai_client import OpenAIProvider
from src.models.poc_models import ToDoListResult, PocResult
from src.prompt.poc_prompt import SYSTEM_PROMPT, USER_PROMPT
from src.tools.sandbox_tools import POC_AGENT_TOOLS
from src.utils.logger import log
from src.tools.common.system_tools import save_conversation_history


class PocGenAgent(BaseAgent):

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
            tools=self.tools,
            system_prompt=self.system_prompt,
            # response_format=ToolStrategy(SandboxResult)
        )

        # user prompt
        self.user_prompt = ChatPromptTemplate.from_template(
            USER_PROMPT,
            template_format="jinja2"
        ).partial()

    async def achat(self, message: ToDoListResult) -> str:

        # 组装prompt
        formatted_prompt = self.user_prompt.invoke({
            "todolist": message.todolist,
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
    # 生成时间戳路径：年月日-时分秒
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    poc_path = os.path.join("./poc", timestamp)

    # 确保目录存在
    os.makedirs(poc_path, exist_ok=True)

    # 测试结果
    vuln_result = ToDoListResult(
        todolist="好的，作为资深的代码安全验证专家，我将根据您提供的漏洞信息，制定一份详细的PoC代码生成计划（ToDoList）。我的同事将依据此计划完成后续的代码编写和执行工作。\n\n---\n\n### **PoC代码生成计划 (ToDoList)**\n\n**目标**：生成一个独立的C++程序，用于动态验证 `tamperAdminView.cpp` 第1015行的格式化字符串漏洞。\n\n**漏洞核心**：用户控制的字符串 `(*it).c_str()` 被直接用作 `CString::Format` 函数的格式化字符串参数，最终传递给 `vsnprintf`，导致漏洞。\n\n---\n\n#### **步骤 1：项目初始化与头文件引入**\n\n- **任务**：创建一个新的C++源文件（例如 `poc_format_string.cpp`），并引入所有必要的标准库头文件。\n- **具体操作**：\n  - 包含 `<iostream>` 用于控制台输出。\n  - 包含 `<vector>` 用于模拟 `names` 容器。\n  - 包含 `<string>` 用于字符串操作。\n  - 包含 `<cstdio>` 和 `<cstdarg>` 用于实现 `CString::Format` 中的可变参数功能（`vsnprintf`, `va_list`）。\n\n#### **步骤 2：模拟核心依赖类与宏**\n\n- **任务**：为了使PoC独立可运行，需要模拟漏洞代码中依赖的关键类和宏。\n- **具体操作**：\n  - **模拟 `CString` 类**：\n    - 创建一个 `CString` 类。\n    - 在类中添加一个 `char*` 成员变量用于存储字符串数据。\n    - 实现构造函数、析构函数和赋值运算符，以管理内存。\n    - **核心**：实现 `void AFX_CDECL Format(LPCTSTR lpszFormat, ...)` 方法。该方法必须使用 `va_list`, `va_start`, `vsnprintf` 来完全复现漏洞代码中的逻辑，将 `lpszFormat` 直接作为格式化字符串传递给 `vsnprintf`。\n  - **定义 `ADD_ERR_MSG` 宏**：\n    - 按照漏洞代码中的定义，创建 `ADD_ERR_MSG` 宏。该宏需要调用一个全局的 `CString` 对象（模拟 `m_csBuf`）的 `Format` 方法，并将结果追加到另一个全局字符串（模拟 `m_ErrMsg`）中。\n\n#### **步骤 3：模拟漏洞触发逻辑**\n\n- **任务**：创建一个函数，用于模拟从HTTP请求接收数据到触发漏洞的完整业务逻辑流程。\n- **具体操作**：\n  - 定义一个函数，例如 `void SimulateVulnerableFunction(const std::string& userInput)`。\n  - 在函数内部：\n    - **[数据流入口]**：函数参数 `userInput` 代表来自HTTP请求 `json.name` 的用户输入。\n    - **[污点传播]**：\n      1. 创建一个 `std::vector<std::string> names`。\n      2. 将 `userInput`（污点数据）`push_back` 到 `names` 向量中。\n      3. 使用 `for` 循环遍历 `names`，获取迭代器 `it`。\n    - **[漏洞触发点]**：在循环内部，调用 `ADD_ERR_MSG(ID2STR(\"IDS_ERR_DELETE_DEPEND\"), (*it).c_str())`。注意，`ID2STR` 可以简单地用一个占位符字符串（如 `\"Error:\"`）代替，因为它不是污点来源。关键是第二个参数 `(*it).c_str()`，它直接携带了用户输入。\n\n#### **步骤 4：构造恶意Payload并实现主函数**\n\n- **任务**：在 `main` 函数中构造一个能够产生明显效果的Payload，并调用模拟函数进行验证。\n- **具体操作**：\n  - **构造Payload**：\n    - 定义一个 `std::string` 变量 `payload`。\n    - 为了产生**可观测的验证结果**，将 `payload` 设置为包含多个格式化说明符的字符串，例如 `\"%p%p%p%p\"`。这个Payload会尝试从栈上读取4个指针值并打印出来，效果非常明显。\n  - **实现 `main` 函数**：\n    - **[数据流入口]**：在 `main` 函数中，定义并初始化 `payload` 变量。\n    - 打印一条提示信息，说明即将发送的Payload。\n    - 调用 `SimulateVulnerableFunction(payload)`，将恶意Payload传入。\n    - 打印最终的错误消息（模拟 `m_ErrMsg` 的内容），以展示漏洞被成功触发后的结果（泄露的内存地址）。\n\n#### **步骤 5：添加关键节点注释**\n\n- **任务**：在生成的代码中，按照规则明确标记出数据流的关键节点。\n- **具体操作**：\n  - 在 `main` 函数中定义 `payload` 的地方，添加注释 `// [数据流入口]`。\n  - 在 `SimulateVulnerableFunction` 函数中，从参数传递到 `ADD_ERR_MSG` 的路径上，添加注释 `// [污点传播]`。\n  - 在 `CString::Format` 方法内部，调用 `vsnprintf` 的那一行，添加注释 `// [漏洞触发点]`。\n\n---\n\n这份ToDoList详细规划了生成独立、可执行且效果明显的PoC验证代码所需的所有步骤。请按照此列表进行开发。",
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
    model.with_structured_output(PocResult)

    agent = PocGenAgent(search_file_path=vuln_result.code_repo, model=model)

    # log.info(f"vuln_result: {vuln_result}")
    response = await agent.achat(vuln_result)
    log.info(f"res: {response}")

    # TODO 遍历结果


if __name__ == "__main__":
    log.info(f"Start...")
    asyncio.run(main())