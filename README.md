# LangChain Agent框架

基于LangChain v1.0构建的智能Agent框架，支持多轮对话、工具调用和记忆管理。

## 🌟 特性

- **模块化设计**: 清晰的项目结构，易于扩展和维护
- **多LLM支持**: 支持OpenAI、Azure OpenAI、Anthropic、HuggingFace等
- **丰富工具集**: 内置文件操作、Web搜索、任务管理等工具
- **灵活记忆系统**: 支持缓冲记忆、滑动窗口、摘要记忆等多种记忆策略
- **异步支持**: 支持同步和异步执行模式
- **中文友好**: 全中文注释和文档，符合中文使用习惯
- **最佳实践**: 遵循LangChain v1.0最佳实践和设计模式

## 📁 项目结构

```
langchain-agent/
├── src/                     # 源代码目录
│   ├── agents/             # Agent模块
│   │   ├── __init__.py
│   │   ├── base_agent.py           # 基础Agent类
│   │   ├── conversational_agent.py # 对话式Agent
│   │   └── custom_agent.py         # 自定义Agent
│   ├── tools/              # 工具模块
│   │   ├── __init__.py
│   │   ├── base_tools.py           # 基础工具类
│   │   ├── file_tools.py           # 文件操作工具
│   │   └── web_tools.py            # Web工具
│   ├── memory/             # 记忆模块
│   │   ├── __init__.py
│   │   ├── memory_manager.py       # 记忆管理器
│   │   └── conversation_memory.py  # 对话记忆
│   ├── models/             # 模型配置
│   │   ├── __init__.py
│   │   └── llm_configs.py          # LLM配置
│   ├── utils/              # 工具模块
│   │   ├── __init__.py
│   │   ├── logger.py              # 日志工具
│   │   └── helpers.py             # 辅助工具
│   └── main.py             # 主入口文件
├── config/                 # 配置目录
│   ├── __init__.py
│   └── settings.py         # 配置管理
├── examples/               # 示例代码
│   ├── __init__.py
│   ├── basic_agent.py      # 基础Agent示例
│   └── advanced_agent.py   # 高级Agent示例
├── tests/                  # 测试代码
│   ├── __init__.py
│   ├── test_agents.py      # Agent测试
│   └── test_tools.py       # 工具测试
├── requirements.txt        # 依赖包列表
├── pyproject.toml         # 项目配置
├── .env.example           # 环境变量示例
└── README.md              # 项目说明
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量示例文件并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置你的API密钥：

```env
# OpenAI API密钥
OPENAI_API_KEY=your_openai_api_key_here

# 可选：其他LLM提供商
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. 运行基础示例

```bash
python examples/basic_agent.py
```

### 4. 运行高级示例

```bash
python examples/advanced_agent.py
```

## 📖 使用指南

### 创建Agent

```python
from src.main import LangChainAgentFramework
from src.models.llm_configs import LLMProvider

# 创建Agent框架
framework = LangChainAgentFramework(
    llm_provider=LLMProvider.OPENAI,
    model="gpt-3.5-turbo",
    enable_file_tools=True,
    enable_web_tools=True,
    memory_type="buffer"
)

# 运行查询
result = framework.run_single_query("你好，请介绍一下自己")
print(result['output'])
```

### 交互模式

```bash
python src/main.py
```

### 命令行参数

```bash
# 指定LLM提供商和模型
python src/main.py --provider openai --model gpt-4

# 禁用某些工具
python src/main.py --no-file-tools --no-web-tools

# 执行单个查询
python src/main.py --query "你好"

# 选择记忆类型
python src/main.py --memory-type window
```

## 🛠️ 自定义工具

创建自定义工具非常简单：

```python
from src.tools.base_tools import BaseCustomTool, register_tool
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    message: str = Field(description="输入消息")

class MyCustomTool(BaseCustomTool):
    name: str = "my_tool"
    description: str = "我的自定义工具"
    args_schema = MyToolInput

    def _setup(self):
        # 工具初始化设置
        pass

    def _execute(self, message: str) -> str:
        # 具体执行逻辑
        return f"处理消息: {message}"

# 注册工具
register_tool(MyCustomTool(), category="custom")

# 添加到Agent
framework.add_custom_tool(MyCustomTool())
```

## 🧠 记忆系统

框架支持多种记忆类型：

### 缓冲记忆（Buffer Memory）
- 保存所有对话历史
- 适用于短对话

### 滑动窗口记忆（Window Memory）
- 只保留最近的N条消息
- 适用于长对话

### 摘要记忆（Summary Memory）
- 保存对话摘要
- 适用于需要长期记忆的场景

```python
from src.memory.memory_manager import MemoryManager

memory_manager = MemoryManager()

# 创建缓冲记忆
buffer_memory = memory_manager.create_buffer_memory()

# 创建滑动窗口记忆
window_memory = memory_manager.create_window_memory(window_size=10)

# 创建摘要记忆
summary_memory = memory_manager.create_summary_memory()
```

## 🧪 测试

运行所有测试：

```bash
pytest tests/ -v
```

运行特定测试：

```bash
pytest tests/test_agents.py -v
pytest tests/test_tools.py -v
```

## 📊 配置选项

### LLM配置

```python
from src.models.llm_configs import LLMProvider, create_llm

# OpenAI
llm = create_llm(LLMProvider.OPENAI, model="gpt-3.5-turbo")

# Azure OpenAI
llm = create_llm(LLMProvider.AZURE_OPENAI, model="gpt-4")

# Anthropic
llm = create_llm(LLMProvider.ANTHROPIC, model="claude-3-sonnet")
```

### 工具配置

```python
# 启用/禁用特定工具
framework = LangChainAgentFramework(
    enable_file_tools=True,
    enable_web_tools=False
)
```

### 记忆配置

```python
# 配置记忆类型和参数
framework = LangChainAgentFramework(
    memory_type="window",  # buffer, window, summary
)
```

## 🔧 扩展开发

### 添加新的Agent类型

```python
from src.agents.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    def _setup_agent(self):
        # 设置Agent逻辑
        pass

    def _create_default_memory(self):
        # 创建默认记忆
        pass
```

### 添加新的记忆类型

```python
from src.memory.memory_manager import MemoryManager

class MyCustomMemory(BaseMemory):
    # 实现自定义记忆逻辑
    pass

memory_manager.create_custom_memory = MyCustomMemory
```

## 🐛 故障排除

### 常见问题

1. **API密钥错误**
   - 确保正确设置环境变量
   - 检查API密钥是否有效

2. **依赖安装失败**
   - 升级pip: `pip install --upgrade pip`
   - 使用虚拟环境

3. **工具调用失败**
   - 检查工具输入格式
   - 查看日志获取详细错误信息

4. **内存问题**
   - 调整记忆类型
   - 限制最大消息数量

### 调试模式

```python
# 启用详细日志
framework = LangChainAgentFramework(verbose=True)

# 查看Agent执行步骤
result = framework.run_single_query("测试查询")
print(result.get('intermediate_steps', []))
```

## 📚 API参考

### 主要类

- `LangChainAgentFramework`: 主框架类
- `ConversationalAgent`: 对话式Agent
- `MemoryManager`: 记忆管理器
- `BaseCustomTool`: 自定义工具基类
- `ToolRegistry`: 工具注册器

### 主要方法

```python
# Agent方法
agent.run(query)                    # 同步运行
agent.arun(query)                   # 异步运行
agent.add_tool(tool)                # 添加工具
agent.clear_memory()                # 清空记忆

# 记忆方法
memory.save_context(inputs, outputs) # 保存上下文
memory.load_memory_variables(inputs) # 加载记忆变量
memory.clear()                      # 清空记忆
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 发起Pull Request

## 📄 许可证

MIT License

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain): 核心框架
- [OpenAI](https://openai.com/): LLM支持
- 所有贡献者和用户

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交Issue: [GitHub Issues](https://github.com/your-repo/issues)
- 邮箱: your-email@example.com

---

**注意**: 这是一个基于LangChain v1.0的示例框架，用于学习和参考。在生产环境中使用前，请确保进行充分测试和安全评估。