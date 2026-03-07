# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Niuma 是一个具备**认知能力**、**协作能力**和**自主执行能力**的下一代 AI Agent 系统。

### 核心价值
- **智能分解**：自动将复杂任务拆分为可执行的子任务
- **持续优化**：通过反思机制不断修正执行路径
- **高效协作**：多 Agent 并行处理，提升整体效率
- **安全隔离**：任务级隔离确保环境安全和可恢复性

## 技术栈

- **语言**：Python 3.11+
- **Web 框架**：FastAPI
- **CLI 框架**：Typer
- **配置管理**：Pydantic Settings
- **LLM**：OpenAI, Anthropic, LangChain
- **向量存储**：ChromaDB / Qdrant
- **异步框架**：asyncio + anyio
- **持久化**：SQLite / PostgreSQL (SQLAlchemy)
- **MCP**：MCP Python SDK

## 开发命令

```bash
# 初始化项目（首次）
uv sync --all-extras

# 安装依赖
uv sync

# 运行 CLI
uv run niuma --help

# 运行测试
uv run pytest
uv run pytest -xvs tests/test_specific.py

# 代码检查
uv run ruff check niuma/
uv run ruff format niuma/
uv run mypy niuma/

# 运行 Web API
uv run uvicorn niuma.api.main:app --reload

# 添加新依赖
uv add <package>
uv add --dev <package>  # 开发依赖
uv add --optional web <package>  # 可选依赖
```

## 核心架构

### 1. 认知循环 (Cognitive Loop)

```
Perceive → Think → Act → Reflect → (loop)
```

- **思维链 (CoT)**：任务分解、依赖分析、执行规划
- **反思机制**：状态评估、偏差检测、策略调整

### 2. 多智能体协作

- **主 Agent (Orchestrator)**：负责任务分解与协调
- **子 Agent 类型**：
  - `ResearchAgent`：信息收集、搜索、文档阅读
  - `PlanAgent`：任务规划、架构设计
  - `CodeAgent`：代码编写、重构
  - `TestAgent`：测试执行、验证
  - `ReviewAgent`：代码审查、质量检查
  - `ExploreAgent`：代码库探索、理解

### 3. 任务系统

**任务状态流转**：
```
PENDING → IN_PROGRESS → COMPLETED
   ↓           ↓
BLOCKED     FAILED → RETRY
```

**并发控制**：
- 支持后台长时间运行的异步任务
- 每个任务在独立的 Worktree 中执行
- 通过 `max_concurrency` 限制并发 Agent 数量

### 4. 记忆系统

**短期记忆 (STM)**：
- 滑动窗口维护最近 N 轮对话/操作
- 智能压缩使用 LLM 总结历史上下文

**长期记忆 (LTM)**：
- 向量存储支持语义检索 (ChromaDB)
- 结构化存储项目知识、代码模式
- 经验库存储成功/失败执行模式

### 5. 工具系统

**MCP 集成**：
- 动态发现并加载 MCP 服务器
- 每个工具声明输入/输出能力
- 安全沙箱限制执行权限

**Skill 系统**：
- 封装常用操作序列为可复用技能
- 支持技能版本管理和迭代更新

## 项目结构

```
niuma/
├── niuma/                     # 核心包
│   ├── cli/                   # CLI 界面 (Typer)
│   │   └── main.py            # CLI 主入口
│   ├── api/                   # Web API (FastAPI)
│   │   ├── main.py            # FastAPI 应用
│   │   └── routes/            # API 路由
│   │       ├── agents.py      # Agent 管理端点
│   │       ├── tasks.py       # 任务管理端点
│   │       ├── memory.py      # 记忆操作端点
│   │       └── tools.py       # 工具调用端点
│   ├── core/                  # 核心组件
│   │   ├── agent.py           # Agent 基类
│   │   ├── cognitive.py       # 认知引擎 (CoT + Reflection)
│   │   ├── task.py            # 任务模型
│   │   ├── scheduler.py       # 任务调度器
│   │   ├── messaging.py       # 消息通信
│   │   └── background.py      # 后台任务管理
│   ├── agents/                # Agent 实现
│   │   ├── factory.py         # Agent 工厂
│   │   ├── orchestrator.py    # 主 Agent
│   │   ├── research.py        # 研究 Agent
│   │   ├── code.py            # 代码 Agent
│   │   ├── test.py            # 测试 Agent
│   │   ├── review.py          # 审查 Agent
│   │   └── plan.py            # 规划 Agent (集成在 factory)
│   ├── memory/                # 记忆系统
│   │   ├── short_term.py      # 短期记忆 (LRU)
│   │   ├── long_term.py       # 长期记忆 (SQLite)
│   │   ├── vector_store.py    # 向量存储 (ChromaDB)
│   │   └── manager.py         # 记忆管理器
│   ├── tools/                 # 工具系统
│   │   ├── registry.py        # 工具注册中心
│   │   ├── mcp/               # MCP 工具
│   │   │   └── client.py      # MCP 客户端 (SSE/stdio)
│   │   └── builtin/           # 内置工具
│   │       ├── file.py        # 文件操作工具
│   │       └── shell.py       # Shell 执行工具
│   ├── skills/                # 技能系统
│   │   └── manager.py         # 技能管理器
│   ├── protocol/              # 团队协议
│   │   └── team.py            # 团队协作协议
│   ├── isolation/             # Worktree 隔离
│   │   └── worktree.py        # Git worktree 管理
│   ├── llm/                   # LLM 客户端
│   │   └── client.py          # OpenAI/Anthropic 统一客户端
│   └── config.py              # 配置管理 (Pydantic Settings)
├── tests/                     # pytest 测试
│   ├── conftest.py            # pytest 配置
│   ├── unit/                  # 单元测试
│   └── integration/           # 集成测试
├── docs/                      # 文档
│   └── PRD.md                 # 产品需求文档
├── .env.example               # 环境变量示例
├── CLAUDE.md                  # 本文件
├── PLAN.md                    # 实施计划
├── pyproject.toml             # 项目配置
└── README.md                  # 项目说明
```

## 配置说明

配置采用扁平化结构，所有环境变量直接作用于主 `Settings` 类：

```bash
# LLM 配置
LLM_PROVIDER=openai                    # openai 或 anthropic
OPENAI_API_KEY=sk-xxx                   # OpenAI API Key
OPENAI_MODEL=gpt-4o                     # 模型名称
OPENAI_BASE_URL=https://api.openai.com # 可选：自定义 base URL
ANTHROPIC_API_KEY=xxx                   # Anthropic API Key
LLM_TEMPERATURE=0.7                     # 温度参数
LLM_TIMEOUT=60                          # 超时时间

# 记忆系统配置
MEMORY_VECTOR_STORE_PATH=.niuma/vector_store
MEMORY_SQLITE_PATH=.niuma/memory.db
MEMORY_STM_WINDOW_SIZE=10

# Agent 配置
AGENT_MAX_CONCURRENCY=5
AGENT_DEFAULT_TIMEOUT=300

# Worktree 配置
WORKTREE_BASE_PATH=.niuma/worktrees
WORKTREE_MAX_WORKTREES=10
```

详见 `.env.example` 完整配置列表。

## 实现阶段

- ✅ **阶段一 (Week 1-2)**：核心框架 - 项目脚手架、Agent 运行时、认知引擎、基础 CLI
- ✅ **阶段二 (Week 3-4)**：任务系统 - 任务调度器、子任务分解、并发执行、Worktree 隔离
- ✅ **阶段三 (Week 5-6)**：多智能体 - Agent 工厂、团队协议、消息通信
- ✅ **阶段四 (Week 7-8)**：记忆系统 - 短期/长期记忆、向量检索
- ✅ **阶段五 (Week 9-10)**：MCP 与技能 - MCP 客户端、工具动态发现
- ✅ **阶段六 (Week 11-12)**：优化与扩展 - Web API、测试覆盖、文档完善

## 关键依赖

```toml
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "anyio>=4.0",
    "typer>=0.9",
    "rich>=13.0",
    "openai>=1.0",
    "anthropic>=0.20",
    "chromadb>=0.4",
    "sqlalchemy>=2.0",
    "mcp>=1.0",
    "GitPython>=3.1",
]
```

## 参考文档

- 详细设计见 `docs/PRD.md`
