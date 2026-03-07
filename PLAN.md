# Niuma AI Agent - 项目实施计划

## 项目概述

**Niuma**（牛马）是一个具备认知能力、协作能力和自主执行能力的下一代 AI Agent 系统。

---

## 当前状态

**已完成阶段**: 第一阶段至第六阶段 (1-6) ✅

---

## 实施阶段

### ✅ 阶段一: 核心框架 (Week 1-2) - DONE

**目标**: 搭建项目基础架构，实现 Agent 运行时核心

| 任务 | 状态 | 交付文件 |
|------|------|----------|
| 1.1 项目脚手架 | ✅ | pyproject.toml, 目录结构 |
| 1.2 配置系统 | ✅ | niuma/config.py |
| 1.3 认知引擎核心 | ✅ | niuma/core/cognitive.py |
| 1.4 Agent 运行时 | ✅ | niuma/core/agent.py |
| 1.5 基础 CLI | ✅ | niuma/cli/main.py |
| 1.6 LLM 客户端 | ✅ | niuma/llm/client.py |
| 额外: 任务模型 | ✅ | niuma/core/task.py |
| 额外: 任务调度器 | ✅ | niuma/core/scheduler.py |

---

### ✅ 阶段二: 任务系统 (Week 3-4) - DONE

**目标**: 实现任务调度、并发控制与 Worktree 隔离

| 任务 | 状态 | 交付文件 |
|------|------|----------|
| 2.1 任务模型 | ✅ | niuma/core/task.py |
| 2.2 任务调度器 | ✅ | niuma/core/scheduler.py |
| 2.3 Worktree 隔离 | ✅ | niuma/isolation/worktree.py |
| 2.4 后台任务支持 | ✅ | niuma/core/background.py |

---

### ✅ 阶段三: 多智能体 (Week 5-6) - DONE

**目标**: 实现 Agent 工厂与团队协作机制

| 任务 | 状态 | 交付文件 |
|------|------|----------|
| 3.1 Agent 工厂 | ✅ | niuma/agents/factory.py |
| 3.2 专项 Agent | ✅ | research.py, code.py, test.py, review.py |
| 3.3 Orchestrator | ✅ | niuma/agents/orchestrator.py |
| 3.4 团队协议 | ✅ | niuma/protocol/team.py |
| 3.5 消息系统 | ✅ | niuma/core/messaging.py |

---

### ✅ 阶段四: 记忆系统 (Week 7-8) - DONE

**目标**: 实现短期/长期记忆与向量检索

| 任务 | 状态 | 交付文件 |
|------|------|----------|
| 4.1 短期记忆 | ✅ | niuma/memory/short_term.py |
| 4.2 长期记忆 | ✅ | niuma/memory/long_term.py |
| 4.3 向量存储 | ✅ | niuma/memory/vector_store.py |
| 4.4 记忆管理器 | ✅ | niuma/memory/manager.py |

---

### ✅ 阶段五: MCP 与技能 (Week 9-10) - DONE

**目标**: 集成 MCP 协议与可复用技能系统

| 任务 | 状态 | 交付文件 |
|------|------|----------|
| 5.1 工具注册中心 | ✅ | niuma/tools/registry.py |
| 5.2 内置工具 | ✅ | file.py, shell.py |
| 5.3 MCP 客户端 | ✅ | niuma/tools/mcp/client.py |
| 5.4 技能系统 | ✅ | niuma/skills/manager.py |

---

### ✅ 阶段六: 优化与扩展 (Week 11-12) - DONE

**目标**: Web API、性能优化与文档完善

| 任务 | 状态 | 交付文件 |
|------|------|----------|
| 6.1 Web API | ✅ | niuma/api/main.py, routes/*.py |
| 6.2 测试覆盖 | ✅ | tests/unit/*.py, tests/integration/*.py |
| 6.3 性能优化 | ⏭️ | (后续迭代) |
| 6.4 文档完善 | ✅ | PLAN.md 更新 |

---

## 项目结构

```
niuma/
├── niuma/
│   ├── __init__.py
│   ├── api/                    ✅ NEW
│   │   ├── __init__.py
│   │   ├── main.py            ✅ FastAPI app
│   │   └── routes/            ✅ API routes
│   │       ├── __init__.py
│   │       ├── agents.py      ✅ Agent endpoints
│   │       ├── tasks.py       ✅ Task endpoints
│   │       ├── memory.py      ✅ Memory endpoints
│   │       └── tools.py       ✅ Tool endpoints
│   ├── cli/
│   │   └── main.py            ✅ CLI 界面
│   ├── core/                  ✅ 核心组件
│   │   ├── agent.py           ✅ Agent 基类
│   │   ├── background.py      ✅ 后台任务
│   │   ├── cognitive.py       ✅ 认知引擎
│   │   ├── messaging.py       ✅ 消息通信
│   │   ├── scheduler.py       ✅ 任务调度
│   │   └── task.py            ✅ 任务模型
│   ├── agents/                ✅ Agent 实现
│   │   ├── factory.py         ✅ Agent 工厂
│   │   ├── orchestrator.py    ✅ 编排器
│   │   ├── research.py        ✅ 研究Agent
│   │   ├── code.py            ✅ 代码Agent
│   │   ├── test.py            ✅ 测试Agent
│   │   └── review.py          ✅ 审查Agent
│   ├── memory/                ✅ 记忆系统
│   │   ├── short_term.py      ✅ 短期记忆
│   │   ├── long_term.py       ✅ 长期记忆
│   │   ├── vector_store.py    ✅ 向量存储
│   │   └── manager.py         ✅ 记忆管理器
│   ├── tools/                 ✅ 工具系统
│   │   ├── registry.py        ✅ 工具注册
│   │   ├── builtin/           ✅ 内置工具
│   │   │   ├── file.py        ✅ 文件工具
│   │   │   └── shell.py       ✅ Shell工具
│   │   └── mcp/               ✅ MCP集成
│   │       └── client.py
│   ├── skills/                ✅ 技能系统
│   │   └── manager.py         ✅ 技能管理
│   ├── protocol/              ✅ 团队协议
│   │   └── team.py
│   ├── isolation/             ✅ 隔离系统
│   │   └── worktree.py
│   ├── llm/
│   │   └── client.py          ✅ LLM客户端
│   └── config.py              ✅ 配置管理
├── tests/                     ✅ 测试目录
│   ├── conftest.py            ✅ pytest 配置
│   ├── pytest.ini            ✅ pytest 配置
│   ├── unit/                  ✅ 单元测试
│   │   ├── test_config.py
│   │   ├── test_task.py
│   │   ├── test_agent_factory.py
│   │   └── test_memory.py
│   └── integration/           ✅ 集成测试
│       └── test_api.py
├── docs/
│   └── PRD.md
├── pyproject.toml             ✅ 项目配置
├── CLAUDE.md                  ✅ 开发指南
├── README.md                  ✅ 项目说明
└── PLAN.md                    ✅ 本文件
```

---

## 核心功能概览

### Agent 类型 (7种)
1. `research` - 信息收集和分析
2. `code` - 代码编写和重构
3. `test` - 测试编写和执行
4. `review` - 代码审查
5. `plan` - 架构和规划
6. `explore` - 代码库探索
7. `assistant` - 通用助手

### 记忆层次 (3层)
1. **短期记忆** - LRU 窗口, 重要性评分
2. **长期记忆** - SQLite 持久化, 分类标签
3. **语义记忆** - 向量存储, ChromaDB, OpenAI Embedding

### 工具系统 (MCP + 内置)
- MCP 客户端 (SSE/stdio 协议)
- FileTool (文件操作)
- ShellTool (命令执行)

### API 端点
- `/` - 根/健康检查
- `/agents` - Agent 管理
- `/tasks` - 任务执行
- `/memory` - 记忆操作
- `/tools` - 工具调用

---

## 使用方式

### CLI 使用
```bash
# 运行任务
uv run niuma run "Analyze this codebase"

# 交互模式
uv run niuma run -i

# 查看配置
uv run niuma config --show
```

### API 使用
```bash
# 启动 API 服务
uv run uvicorn niuma.api.main:app --reload

# 创建任务
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Hello", "agent_type": "assistant"}'
```

### 程序化使用
```python
from niuma.agents import Orchestrator

orch = Orchestrator()
await orch.initialize()
result = await orch.execute("Write a function", agent_type="code")
```

---

## 测试

```bash
# 运行测试
uv run pytest

# 运行特定测试
uv run pytest tests/unit/test_task.py -v
```

---

## 后续优化方向

1. **性能优化**
   - 连接池管理
   - 缓存策略优化
   - 异步批量处理

2. **功能扩展**
   - 更多 MCP 工具集成
   - 可视化监控界面
   - 工作流编排

3. **生产准备**
   - Docker 容器化
   - 认证与授权
   - 监控与日志

---

*最后更新: 2026-03-07*
*状态: 6/6 阶段完成 ✅*
