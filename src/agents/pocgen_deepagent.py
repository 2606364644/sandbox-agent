import asyncio
import os
from datetime import datetime
from typing import List, Dict
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.middleware import FilesystemFileSearchMiddleware, SummarizationMiddleware
from langchain.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI, OpenAI

from src.models.planning_models import VulnResult
from src.agents.base_agent import BaseAgent
from src.clients import get_llm_client, get_llm_provider
from src.models.poc_models import ToDoListResult, PocResult
from src.prompt.pocgen_deepagent_prompt import SYSTEM_PROMPT, USER_PROMPT
from src.tools.sandbox_tools import POC_AGENT_TOOLS
from src.utils.logger import log
from src.tools.common.system_tools import save_conversation_history


class PocGenDeepAgent(BaseAgent):

    def __init__(
            self,
            search_file_path: str = None,
            model: ChatOpenAI | OpenAI = None,
            tool: List[BaseTool] = POC_AGENT_TOOLS,
    ):
        super().__init__()

        self.model = model
        self.tools = tool
        self.system_prompt = SYSTEM_PROMPT

        # 创建Agent
        self.agent = create_deep_agent(
            model=self.model,
            system_prompt=self.system_prompt,
            # backend=FilesystemBackend(root_dir="/codesec", virtual_mode=True),
            backend=FilesystemBackend(root_dir="/codesec"),
        )

        # user prompt
        self.user_prompt = PromptTemplate.from_template(
            USER_PROMPT,
            template_format="jinja2"
        ).partial()

    async def achat(self, message: ToDoListResult) -> str:

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

    async def stream_multiple_achat(self, message: ToDoListResult):
        formatted_prompt = self.user_prompt.invoke(message.model_dump())
        self.chat_history.append(HumanMessage(content=str(formatted_prompt)))
        for stream_mode, chunk in self.agent.stream(
                {"messages": [{"role": "user", "content": str(formatted_prompt)}]},
                stream_mode=["updates", "custom"],
                # stream_mode=["messages", "updates", "custom"]
        ):
            log.info(f"stream_mode: {stream_mode}")
            log.info(f"content: {chunk}")
            log.info("\n")


async def run_vulnerability_analysis(code_repo, vuln_type, description, filename, code, impact, result, todolist, mode="stream_multiple"):
    """统一的漏洞分析函数

    Args:
        code_repo: 代码仓库路径
        vuln_type: 漏洞类型
        description: 漏洞描述
        filename: 文件名
        code: 代码片段
        impact: 漏洞影响
        result: 分析结果
        todolist: 待办事项列表
        mode: 分析模式，可选 "achat", "stream_multiple"
    """
    # 创建时间戳路径和POC目录：年月日-时分秒
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    poc_path = os.path.join(os.getcwd(), "poc", timestamp)

    # 确保目录存在
    os.makedirs(poc_path, exist_ok=True)

    vuln_result = VulnResult(
        code_repo=code_repo,
        poc_path=poc_path,
        type=vuln_type,
        description=description,
        filename=filename,
        code=code.strip(),
        impact=impact,
        result=result.strip()
    )

    # 初始化模型和代理
    model = get_llm_client(stream_usage=True)
    model.with_structured_output(PocResult)

    agent = PocGenDeepAgent(search_file_path=code_repo, model=model)

    # 执行代理分析
    if mode == "achat":
        # response = await agent.achat(todo_list_result)
        response = await agent.achat(vuln_result)
        return response
    elif mode == "stream_multiple":
        # await agent.stream_multiple_achat(todo_list_result)
        await agent.stream_multiple_achat(vuln_result)
    else:
        raise ValueError(f"不支持的模式: {mode}")


# 使用示例
async def main():
    # 生成时间戳路径：年月日-时分秒
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    poc_path = os.path.join(os.getcwd(), "poc", timestamp)

    # 确保目录存在
    os.makedirs(poc_path, exist_ok=True)

    # 测试结果
    vuln_result = ToDoListResult(
        todolist="好的，我将根据您提供的漏洞信息，进入规划阶段，为您生成一份详细的 ToDoList，以指导后续的 PoC 代码编写工作。\n\n```xml\n<ToDoList>\n    <project_name>FORMAT_STRING_VULNERABILITY_PoC</project_name>\n    <description>针对 BlobLogRowWriter::log_debug_firewall 函数中格式化字符串漏洞的验证代码生成计划。</description>\n    \n    <steps>\n        <step id=\"1\">\n            <title>项目环境与结构搭建</title>\n            <description>创建 PoC 项目所需的目录、文件和基础配置，确保项目结构清晰、可独立编译和运行。</description>\n            <details>\n                <item>1.1. 在指定输出路径 `./poc/20251127-120357` 下创建项目根目录。</item>\n                <item>1.2. 创建主源码文件 `poc.cpp`。</item>\n                <item>1.3. 创建 `Makefile` 用于定义编译规则。</item>\n                <item>1.4. 创建编译脚本 `build.sh`，内容为执行 `make` 命令。</item>\n                <item>1.5. 创建 `README.md` 文档，用于说明 PoC 的功能、编译、运行方法及预期结果。</item>\n            </details>\n        </step>\n\n        <step id=\"2\">\n            <title>定义核心数据结构</title>\n            <description>根据漏洞分析报告，定义并实现 PoC 所需的最小化数据结构，模拟漏洞触发环境。</description>\n            <details>\n                <item>2.1. 在 `poc.cpp` 中，定义 `union nf_inet_addr` 结构体，用于模拟 IP 地址。内部可包含一个 `struct in_addr ip;`。</item>\n                <item>2.2. 定义 `action` 结构体，包含 `char in_ifname[IFNAMSIZ];` 字段（`IFNAMSIZ` 通常为16，可根据实际情况调整，确保能容纳测试payload）和 `union nf_inet_addr nHstIp, nDstIp;`。</item>\n                <item>2.3. 定义 `FIREWALL` 结构体，包含 `char szDepict[256];` 和 `struct action action;` 字段。数组大小需足够大以容纳恶意payload。</item>\n            </details>\n        </step>\n\n        <step id=\"3\">\n            <title>模拟辅助函数</title>\n            <description>实现漏洞函数调用链中依赖的辅助函数，确保 PoC 的完整性和可编译性。</description>\n            <details>\n                <item>3.1. 实现 `SyslogGetAddr` 函数。该函数接收 `union nf_inet_addr*` 和 `unsigned int order` 参数，返回一个静态的 IP 地址字符串，如 `\"192.168.1.1\"`。此函数非漏洞点，简化实现即可。</item>\n                <item>3.2. 实现 `tsklog_dp_debug` 函数。此函数是**漏洞触发点**。它应接收一个格式化字符串和可变参数，并直接调用 `vprintf` 或 `printf` 将其输出到标准错误或标准输出。**关键：不能对格式化字符串进行任何处理。**</item>\n            </details>\n        </step>\n\n        <step id=\"4\">\n            <title>实现漏洞函数逻辑</title>\n            <description>精确复现漏洞函数 `BlobLogRowWriter::log_debug_firewall` 的核心逻辑，完成污点数据的传播。</description>\n            <details>\n                <item>4.1. 在 `poc.cpp` 中，创建 `BlobLogRowWriter` 类（或直接使用命名空间），并实现 `log_debug_firewall(FIREWALL *pkt)` 方法。</item>\n                <item>4.2. 在该方法内部，**标记污点传播**：直接使用 `pkt->szDepict` 和 `pkt->action.in_ifname` 作为参数。</item>\n                <item>4.3. 调用 `tsklog_dp_debug` 函数，并传入包含 `%s` 占位符的格式化字符串以及 `pkt` 中的污点数据，完整复现危险函数调用。例如：`tsklog_dp_debug(\"应用控制日志 ==> szDepict:%s, in_ifname:%s, src_ip:%s, dst_ip:%s\", pkt->szt->action.nHstIp), 0), SyslogGetAddr(&(pkt->action.nDstIp), 1));`</item>\n            </details>\n        </step>\n\n        <step id=\"5\">\n            <title>构造主函数与数据流入口</title>\n            <description>在 `main` 函数中构造恶意输入，模拟外部数据源，并调用漏洞函数，形成完整的数据流。</description>\n            <details>\n                <item>5.1. 在 `main` 函数中，实例化一个 `FIREWALL` 结构体变量 `pkt`。</item>\n                <item>5.2. **标记数据流入口**：使用 `strcpy` 或 `sprintf` 将恶意的格式化字符串 payload 写入 `pkt.szDepict` 和 `pkt.action.in_ifname`。Payload 应设计为能泄露栈上信息，例如 `\"%p %p %p %p\"` 或 `\"%x.%x.%x.%x\"`。</item>\n                <item>5.3. 调用 `log_debug_firewall(&pkt)`，触发漏洞。</item>\n                <item>5.4. 在 `main` 函数中添加打印信息，说明 PoC 的目的和正在执行的操作。</item>\n            </details>\n        </step>\n\n        <step id=\"6\">\n            <title>完善编译与文档</title>\n            <description>配置编译选项，并完善 README 文档，确保 PoC 易于使用和验证。</description>\n            <details>\n                <item>6.1. 编写 `Makefile`，设置编译器（如 `g++`），添加编译标志（如 `-g` 用于调试，`-Wall` 显示所有警告），并指定生成可执行文件（如 `poc`）。</item>\n                <item>6.2. 编写 `README.md`，内容包括：\n                    - 漏洞简介。\n                    - PoC 文件结构说明。\n                    - 编译命令 (`./build.sh` 或 `make`)。\n                    - 运行命令 (`./poc`)。\n                    - **预期结果**：明确指出成功运行后，控制台将打印出多个十六进制的内存地址，证明格式化字符串漏洞被成功利用，泄露了栈信息。</item>\n            </details>\n        </step>\n    </steps>\n</ToDoList>\n```\n",
        code_repo="/codesec/AF8048/AF8.0.48",
        poc_path=poc_path,
        type="FORMAT_STRING_VULNERABILITY",
        description="在第1896行，使用strcpy函数将r.eth的内容复制到固定大小的if_name数组中，而r.eth是从外部输入获取的（第1830行），如果r.eth的长度超过24字节（包括终止符），就会导致缓冲区溢出。",
        filename="af/datacenter/daemon/fwlog/BlobLogRowWriter.cpp",
        code="""
2883 |          "test_d:%s,"
2912 |          "session_start_time:%s",
2922 |          pkt->szDepict,
2939 |          pkt->action.in_ifname,
2944 |+         SyslogGetAddr(&(pkt->action.nHstIp), 0),
2945 |+         SyslogGetAddr(&(pkt->action.nDstIp), 1));
        """.strip(),
        impact="攻击者可通过构造恶意输入注入格式化字符串指令（如%n），导致内存写入或信息泄露，进而可能实现任意代码执行或敏感数据窃取。",
        result="""
# 安全漏洞分析报告

## 1. 安全漏洞存在性
**存在**：存在格式化字符串漏洞，函数`BlobLogRowWriter::log_debug_firewall`中的`pkt->szDepict`、`pkt->action.in_ifname`参数未过滤`%`字符，可能导致格式化字符串攻击。

## 2. 漏洞利用条件及触发方式
- **利用条件**：
  - 攻击者需能控制`pkt->szDepict`和`pkt->action.in_ifname`的值（如通过构造恶意网络数据包）
  - 需要`tsklog_DBG1`实现直接使用格式字符串（如`vprintf`）
- **触发方式**：
  构造包含`%n`的字符串作为`szDepict`或`in_ifname`值，触发内存写入或信息泄露

## 3. 数据流分析
```mermaid
graph TD
    A["用户构造恶意输入"] --> |网络数据包 szDepict/in_ifname| B["pkt结构体赋值"]
    B --> |未过滤参数| C["BlobLogRowWriter::log_debug_firewall"]
    C --> |格式化字符串参数| D["tsklog_dp_debug"]
    D --> |潜在格式化处理| E["内存写入/信息泄露"]
```

## 4. 关键代码片段

**危险函数调用**：
```cpp
// af/datacenter/daemon/fwlog/BlobLogRowWriter.cpp
void BlobLogRowWriter::log_debug_firewall(FIREWALL *pkt) {
    tsklog_dp_debug("应用控制日志 ==> szDepict:%s, in_ifname:%s, ...", 
        pkt->szDepict, pkt->action.in_ifname, ...);
}
```

**用户输入来源**：
```cpp
// af/datacenter/daemon/fwlog/BlobLogRowWriter.cpp
APPEND_STR_VALUE(FIREWALL_DEPICT, pkt->szDepict, strlen(pkt->szDepict));
APPEND_STR_VALUE(FIREWALL_IN_IFNAME, pkt->action.in_ifname, strlen(pkt->action.in_ifname));
```

**SyslogGetAddr实现**：
```cpp
// af/datacenter/daemon/fwlog/BlobLogRowWriter.cpp
char *BlobLogRowWriter::SyslogGetAddr(union nf_inet_addr* ip, unsigned int order) {
    // IP地址转换为字符串，通常不包含%字符
    return inet_ntoa(ip->ip);
}
```

## 5. 总结
**漏洞类型**：格式化字符串漏洞  
**修复建议**：
1. 对`szDepict`和`in_ifname`进行过滤，移除`%`字符：
   ```cpp
   std::string sanitize(const std::string& input) {
       std::string result;
       for (char c : input) {
           if (c != '%') result += c;
       }
       return result;
   }
   ```
2. 使用安全的日志函数（如`snprintf`）替代`tsklog_dp_debug`：
   ```cpp
   char buffer[1024];
   snprintf(buffer, sizeof(buffer), "日志模板: %s", sanitized_input.c_str());
   tsklog_dp_debug("%s", buffer);
   ```
3. 对`tsklog_DBG1`实现进行审查，确保其使用固定格式字符串而非用户输入。
        """.strip()
    )
    # 使用抽象层自动选择客户端
    model = get_llm_client(stream_usage=True)
    model.with_structured_output(PocResult)

    agent = PocGenDeepAgent(search_file_path=vuln_result.code_repo, model=model)

    # log.info(f"vuln_result: {vuln_result}")
    # response = await agent.achat(vuln_result)
    # log.info(f"res: {response}")

    await agent.stream_multiple_achat(vuln_result)


async def format_string_poc_main():
    """格式化字符串漏洞PoC生成示例"""
    log.info(f"Start format_string_poc_main ...")

    # 使用统一函数运行格式化字符串漏洞PoC生成
    await run_vulnerability_analysis(
        code_repo="/codesec/AF8048/AF8.0.48",
        vuln_type="FORMAT_STRING_VULNERABILITY",
        description="在第1896行，使用strcpy函数将r.eth的内容复制到固定大小的if_name数组中，而r.eth是从外部输入获取的（第1830行），如果r.eth的长度超过24字节（包括终止符），就会导致缓冲区溢出。",
        filename="af/datacenter/daemon/fwlog/BlobLogRowWriter.cpp",
        code="""
2883 |         "test_d:%s,"
2912 |         "session_start_time:%s",
2922 |         pkt->szDepict,
2939 |         pkt->action.in_ifname,
2944 |+         SyslogGetAddr(&(pkt->action.nHstIp), 0),
2945 |+         SyslogGetAddr(&(pkt->action.nDstIp), 1));
        """.strip(),
        impact="攻击者可通过构造恶意输入注入格式化字符串指令（如%n），导致内存写入或信息泄露，进而可能实现任意代码执行或敏感数据窃取。",
        result="""
# 安全漏洞分析报告

## 1. 安全漏洞存在性
**存在**：存在格式化字符串漏洞，函数`BlobLogRowWriter::log_debug_firewall`中的`pkt->szDepict`、`pkt->action.in_ifname`参数未过滤`%`字符，可能导致格式化字符串攻击。

## 2. 漏洞利用条件及触发方式
- **利用条件**：
  - 攻击者需能控制`pkt->szDepict`和`pkt->action.in_ifname`的值（如通过构造恶意网络数据包）
  - 需要`tsklog_DBG1`实现直接使用格式字符串（如`vprintf`）
- **触发方式**：
  构造包含`%n`的字符串作为`szDepict`或`in_ifname`值，触发内存写入或信息泄露

## 3. 数据流分析
```mermaid
graph TD
    A["用户构造恶意输入"] --> |网络数据包 szDepict/in_ifname| B["pkt结构体赋值"]
    B --> |未过滤参数| C["BlobLogRowWriter::log_debug_firewall"]
    C --> |格式化字符串参数| D["tsklog_dp_debug"]
    D --> |潜在格式化处理| E["内存写入/信息泄露"]
```

## 4. 关键代码片段

**危险函数调用**：
```cpp
// af/datacenter/daemon/fwlog/BlobLogRowWriter.cpp
void BlobLogRowWriter::log_debug_firewall(FIREWALL *pkt) {
    tsklog_dp_debug("应用控制日志 ==> szDepict:%s, in_ifname:%s, ...",
        pkt->szDepict, pkt->action.in_ifname, ...);
}
```

**用户输入来源**：
```cpp
// af/datacenter/daemon/fwlog/BlobLogRowWriter.cpp
APPEND_STR_VALUE(FIREWALL_DEPICT, pkt->szDepict, strlen(pkt->szDepict));
APPEND_STR_VALUE(FIREWALL_IN_IFNAME, pkt->action.in_ifname, strlen(pkt->action.in_ifname));
```

**SyslogGetAddr实现**：
```cpp
// af/datacenter/daemon/fwlog/BlobLogRowWriter.cpp
char *BlobLogRowWriter::SyslogGetAddr(union nf_inet_addr* ip, unsigned int order) {
    // IP地址转换为字符串，通常不包含%字符
    return inet_ntoa(ip->ip);
}
```

## 5. 总结
**漏洞类型**：格式化字符串漏洞
**修复建议**：
1. 对`szDepict`和`in_ifname`进行过滤，移除`%`字符：
   ```cpp
   std::string sanitize(const std::string& input) {
       std::string result;
       for (char c : input) {
           if (c != '%') result += c;
       }
       return result;
   }
   ```
2. 使用安全的日志函数（如`snprintf`）替代`tsklog_dp_debug`：
   ```cpp
   char buffer[1024];
   snprintf(buffer, sizeof(buffer), "日志模板: %s", sanitized_input.c_str());
   tsklog_dp_debug("%s", buffer);
   ```
3. 对`tsklog_DBG1`实现进行审查，确保其使用固定格式字符串而非用户输入。
        """.strip(),
        todolist="""
好的，我将根据您提供的漏洞信息，进入规划阶段，为您生成一份详细的 ToDoList，以指导后续的 PoC 代码编写工作。

```xml
<ToDoList>
    <project_name>FORMAT_STRING_VULNERABILITY_PoC</project_name>
    <description>针对 BlobLogRowWriter::log_debug_firewall 函数中格式化字符串漏洞的验证代码生成计划。</description>
    
    <steps>
        <step id="1">
            <title>项目环境与结构搭建</title>
            <description>创建 PoC 项目所需的目录、文件和基础配置，确保项目结构清晰、可独立编译和运行。</description>
            <details>
                <item>1.1. 在指定输出路径 `./poc/20251127-120357` 下创建项目根目录。</item>
                <item>1.2. 创建主源码文件 `poc.cpp`。</item>
                <item>1.3. 创建 `Makefile` 用于定义编译规则。</item>
                <item>1.4. 创建编译脚本 `build.sh`，内容为执行 `make` 命令。</item>
                <item>1.5. 创建 `README.md` 文档，用于说明 PoC 的功能、编译、运行方法及预期结果。</item>
            </details>
        </step>

        <step id="2">
            <title>定义核心数据结构</title>
            <description>根据漏洞分析报告，定义并实现 PoC 所需的最小化数据结构，模拟漏洞触发环境。</description>
            <details>
                <item>2.1. 在 `poc.cpp` 中，定义 `union nf_inet_addr` 结构体，用于模拟 IP 地址。内部可包含一个 `struct in_addr ip;`。</item>
                <item>2.2. 定义 `action` 结构体，包含 `char in_ifname[IFNAMSIZ];` 字段（`IFNAMSIZ` 通常为16，可根据实际情况调整，确保能容纳测试payload）和 `union nf_inet_addr nHstIp, nDstIp;`。</item>
                <item>2.3. 定义 `FIREWALL` 结构体，包含 `char szDepict[256];` 和 `struct action action;` 字段。数组大小需足够大以容纳恶意payload。</item>
            </details>
        </step>

        <step id="3">
            <title>模拟辅助函数</title>
            <description>实现漏洞函数调用链中依赖的辅助函数，确保 PoC 的完整性和可编译性。</description>
            <details>
                <item>3.1. 实现 `SyslogGetAddr` 函数。该函数接收 `union nf_inet_addr*` 和 `unsigned int order` 参数，返回一个静态的 IP 地址字符串，如 `"192.168.1.1"`。此函数非漏洞点，简化实现即可。</item>
                <item>3.2. 实现 `tsklog_dp_debug` 函数。此函数是**漏洞触发点**。它应接收一个格式化字符串和可变参数，并直接调用 `vprintf` 或 `printf` 将其输出到标准错误或标准输出。**关键：不能对格式化字符串进行任何处理。**</item>
            </details>
        </step>

        <step id="4">
            <title>实现漏洞函数逻辑</title>
            <description>精确复现漏洞函数 `BlobLogRowWriter::log_debug_firewall` 的核心逻辑，完成污点数据的传播。</description>
            <details>
                <item>4.1. 在 `poc.cpp` 中，创建 `BlobLogRowWriter` 类（或直接使用命名空间），并实现 `log_debug_firewall(FIREWALL *pkt)` 方法。</item>
                <item>4.2. 在该方法内部，**标记污点传播**：直接使用 `pkt->szDepict` 和 `pkt->action.in_ifname` 作为参数。</item>
                <item>4.3. 调用 `tsklog_dp_debug` 函数，并传入包含 `%s` 占位符的格式化字符串以及 `pkt` 中的污点数据，完整复现危险函数调用。例如：`tsklog_dp_debug("应用控制日志 ==> szDepict:%s, in_ifname:%s, src_ip:%s, dst_ip:%s", pkt->szt->action.nHstIp), 0), SyslogGetAddr(&(pkt->action.nDstIp), 1));`</item>
            </details>
        </step>

        <step id="5">
            <title>构造主函数与数据流入口</title>
            <description>在 `main` 函数中构造恶意输入，模拟外部数据源，并调用漏洞函数，形成完整的数据流。</description>
            <details>
                <item>5.1. 在 `main` 函数中，实例化一个 `FIREWALL` 结构体变量 `pkt`。</item>
                <item>5.2. **标记数据流入口**：使用 `strcpy` 或 `sprintf` 将恶意的格式化字符串 payload 写入 `pkt.szDepict` 和 `pkt.action.in_ifname`。Payload 应设计为能泄露栈上信息，例如 `"%p %p %p %p"` 或 `"%x.%x.%x.%x"`。</item>
                <item>5.3. 调用 `log_debug_firewall(&pkt)`，触发漏洞。</item>
                <item>5.4. 在 `main` 函数中添加打印信息，说明 PoC 的目的和正在执行的操作。</item>
            </details>
        </step>

        <step id="6">
            <title>完善编译与文档</title>
            <description>配置编译选项，并完善 README 文档，确保 PoC 易于使用和验证。</description>
            <details>
                <item>6.1. 编写 `Makefile`，设置编译器（如 `g++`），添加编译标志（如 `-g` 用于调试，`-Wall` 显示所有警告），并指定生成可执行文件（如 `poc`）。</item>
                <item>6.2. 编写 `README.md`，内容包括：
                    - 漏洞简介。
                    - PoC 文件结构说明。
                    - 编译命令 (`./build.sh` 或 `make`)。
                    - 运行命令 (`./poc`)。
                    - **预期结果**：明确指出成功运行后，控制台将打印出多个十六进制的内存地址，证明格式化字符串漏洞被成功利用，泄露了栈信息。</item>
            </details>
        </step>
    </steps>
</ToDoList>
```
        """.strip()
    )


if __name__ == "__main__":
    log.info(f"Start...")
    asyncio.run(main())