"""
测试PoC生成DeepAgent
对比传统单次调用与DeepAgent分阶段处理的区别
"""

import asyncio
import os
from datetime import datetime

from src.agents.pocgen_deepagent import PoCGenDeepAgent
from src.models.poc_models import ToDoListResult, PocResult
from src.utils.logger import log


async def test_deepagent():
    """测试DeepAgent的PoC生成能力"""

    # 生成时间戳路径
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    poc_path = os.path.join("./poc", timestamp)

    # 确保目录存在
    os.makedirs(poc_path, exist_ok=True)

    # 创建测试用的漏洞信息
    vuln_result = ToDoListResult(
        todolist="""
基于DeepAgent方法生成一个完整的PoC验证程序，用于验证C++程序中的格式化字符串漏洞。

任务要求：
1. 深入分析格式化字符串漏洞的原理和触发机制
2. 生成一个独立可运行的C++ PoC程序
3. 模拟漏洞代码中的关键依赖类和函数
4. 实现有效的漏洞触发逻辑，能够产生明显的验证效果
5. 编写完整的测试验证过程
6. 生成详细的漏洞分析报告和安全建议

漏洞核心：用户控制的字符串被直接用作CString::Format函数的格式化字符串参数，
最终传递给vsnprintf，导致格式化字符串漏洞。
        """.strip(),
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

**危险函数实现**：
```cpp
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
1. 使用硬编码的格式化字符串，将用户输入作为参数传递
2. 对用户输入进行过滤，移除或转义格式化说明符
3. 实现输入验证，限制用户输入的字符集
4. 使用安全的字符串格式化函数，确保格式化字符串来自可信源
        """.strip()
    )

    # 使用DeepAgent生成PoC
    log.info("=== 开始测试PoC生成DeepAgent ===")
    deep_agent = PoCGenDeepAgent()

    try:
        # 执行完整的PoC生成流程
        result = await deep_agent.generate_poc(vuln_result)

        # 输出结果
        log.info("=== DeepAgent执行完成 ===")
        log.info(f"执行结果:\n{result.result}")

        # 保存结果到文件
        result_file = os.path.join(poc_path, "deepagent_result.txt")
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(result.result)

        log.info(f"完整结果已保存到: {result_file}")

        return result

    except Exception as e:
        error_msg = f"DeepAgent测试失败: {str(e)}"
        log.error(error_msg)
        return PocResult(result=error_msg)


async def main():
    """主测试函数"""
    try:
        # 执行DeepAgent测试
        result = await test_deepagent()

        log.info("\n=== 测试完成 ===")
        if "执行状态: 成功完成" in result.result:
            log.info("✅ DeepAgent PoC生成测试成功")
        else:
            log.info("❌ DeepAgent PoC生成测试存在问题")

    except Exception as e:
        log.error(f"测试过程中发生错误: {str(e)}")


if __name__ == "__main__":
    log.info("启动DeepAgent测试...")
    asyncio.run(main())