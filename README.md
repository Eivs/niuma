# Niuma 🐂

**下一代认知多智能体 AI 系统**

Niuma（牛马）是一个具备**认知能力**、**协作能力**和**自主执行能力**的 AI Agent 系统，能够处理复杂的多步骤任务，通过多智能体协作和反思机制持续优化执行质量。

## 核心特性

- 🧠 **深度认知**：CoT + Reflection 双循环，持续自我改进
- 🤝 **智能协作**：动态 Agent 组建，自适应任务分配
- 💾 **分层记忆**：短期/长期记忆协同，经验持续积累
- 🏝️ **任务隔离**：Worktree 级隔离，安全并发执行
- 🧩 **MCP 原生**：拥抱 MCP 生态，工具即插即用
- ⚡ **异步优先**：Python asyncio 全异步架构，高效资源利用


## 核心功能模块

### 认知架构 (Cognitive Architecture)

```mermaid
flowchart TB
    %% 环形布局的认知循环
    Perceive["🎯<br/>感知<br/>Perceive"]
    Think["🧠<br/>思考<br/>Think"]
    Act["⚡<br/>行动<br/>Act"]
    Reflect["💭<br/>反思<br/>Reflect"]

    Perceive --> Think
    Think --> Act
    Act --> Reflect
    Reflect --> Perceive

    %% 统一的配色方案
    classDef perceive fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af
    classDef think fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#6b21a8
    classDef act fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534
    classDef reflect fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e

    class Perceive perceive
    class Think think
    class Act act
    class Reflect reflect
```

#### 思维链 (Chain-of-Thought)
- **任务分解**：LLM 分析用户输入，拆分为原子操作
- **依赖分析**：识别子任务间的执行顺序和依赖关系
- **执行规划**：生成带优先级的执行计划

#### 反思机制 (Reflection)
- **状态评估**：每步执行后评估是否接近目标
- **偏差检测**：检测执行路径是否偏离预期
- **策略调整**：根据反馈动态调整后续计划

### 多智能体协作系统

```mermaid
flowchart TB
    %% 主 Agent 层
    Orchestrator["🎯<br/>主 Agent<br/>Orchestrator"]

    %% 执行类 Agent
    subgraph ExecuteAgents["执行类 Agents"]
        direction LR
        Research["🔍<br/>Research"]
        Code["💻<br/>Code"]
        Test["🧪<br/>Test"]
        Review["👁️<br/>Review"]
    end

    %% 规划类 Agent
    subgraph PlanAgents["规划类 Agents"]
        direction LR
        Plan["📋<br/>Plan"]
        Explore["🗺️<br/>Explore"]
        Write["✏️<br/>Write"]
    end

    %% 连接关系
    Orchestrator --> Research
    Orchestrator --> Code
    Orchestrator --> Test
    Orchestrator --> Review
    Orchestrator --> Plan
    Orchestrator --> Explore
    Orchestrator --> Write

    %% 统一的配色方案
    classDef orchestrator fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af
    classDef agentResearch fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#6b21a8
    classDef agentCode fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534
    classDef agentTest fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e
    classDef agentReview fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#9d174d
    classDef agentPlan fill:#ccfbf1,stroke:#0d9488,stroke-width:2px,color:#0f766e
    classDef agentExplore fill:#ecfccb,stroke:#65a30d,stroke-width:2px,color:#3f6212
    classDef agentWrite fill:#e0e7ff,stroke:#6366f1,stroke-width:2px,color:#4338ca

    class Orchestrator orchestrator
    class Research agentResearch
    class Code agentCode
    class Test agentTest
    class Review agentReview
    class Plan agentPlan
    class Explore agentExplore
    class Write agentWrite
```

#### 团队协议 (Team Protocol)
```python
from dataclasses import dataclass
from typing import List, Literal

@dataclass
class AgentRole:
    name: str
    responsibilities: List[str]
    skills: List[str]
    constraints: List[str]

@dataclass
class CommunicationConfig:
    protocol: Literal['message_queue', 'direct', 'broadcast']
    priority_levels: int = 3

@dataclass
class CollaborationConfig:
    mode: Literal['sequential', 'parallel', 'hybrid']
    max_agents: int = 5

@dataclass
class TeamProtocol:
    roles: List[AgentRole]
    communication: CommunicationConfig
    collaboration: CollaborationConfig
```

#### 子 Agent 类型

| Agent 类型 | 职责 | 专长领域 |
|-----------|------|---------|
| **ResearchAgent** | 信息收集、搜索、文档阅读 | 网页搜索、代码搜索、文档解析 |
| **PlanAgent** | 任务规划、架构设计 | 系统设计、依赖分析 |
| **CodeAgent** | 代码编写、重构 | 代码生成、代码修改 |
| **TestAgent** | 测试执行、验证 | 单元测试、集成测试、性能测试 |
| **ReviewAgent** | 代码审查、质量检查 | 静态分析、最佳实践检查 |
| **ExploreAgent** | 代码库探索、理解 | 文件搜索、依赖分析 |

### 任务系统与规划

#### 任务模型
```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum, auto

class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    BLOCKED = auto()

class TaskType(Enum):
    ATOMIC = auto()
    COMPOSITE = auto()
    SUBTASK = auto()

@dataclass
class Task:
    id: str
    type: TaskType
    status: TaskStatus = TaskStatus.PENDING

    # 执行内容
    description: str = ""
    goal: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)

    # 层级关系
    parent_id: Optional[str] = None
    subtask_ids: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # 前置任务ID

    # 执行配置
    assigned_to: Optional[str] = None  # Agent ID
    tools: List[str] = field(default_factory=list)
    timeout: int = 300  # 秒
    max_retries: int = 3

    # 元数据
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

#### 任务状态流转

```mermaid
stateDiagram-v2
    [*] --> PENDING

    PENDING --> IN_PROGRESS : 开始执行
    PENDING --> BLOCKED : 依赖未满足

    IN_PROGRESS --> COMPLETED : 执行成功
    IN_PROGRESS --> FAILED : 执行失败

    FAILED --> RETRY : 重试
    RETRY --> IN_PROGRESS : 重新执行

    BLOCKED --> PENDING : 依赖已解决

    COMPLETED --> [*]

    %% 统一的配色方案 - 高对比度
    classDef pending fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e
    classDef inProgress fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af
    classDef completed fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534
    classDef failed fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#991b1b
    classDef blocked fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#9d174d
    classDef retry fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#9a3412

    class PENDING pending
    class IN_PROGRESS inProgress
    class COMPLETED completed
    class FAILED failed
    class RETRY retry
    class BLOCKED blocked
```

#### 并发控制
- **后台任务**：支持长时间运行的异步任务
- **任务隔离**：每个任务在独立的 Worktree/上下文中执行
- **资源限制**：控制并发 Agent 数量，防止资源耗尽

### 记忆系统

```mermaid
flowchart TB
    subgraph STM["短期记忆 (STM)"]
        direction TB
        stm1["📋 上下文窗口"]
        stm2["💬 对话历史"]
        stm3["⚡ 工作内存"]
        stm4["🔄 缓存层"]
        stm5["🗜️ 自动压缩/遗忘"]
    end

    subgraph LTM["长期记忆 (LTM)"]
        direction TB
        ltm1["🔍 向量数据库"]
        ltm2["💾 本地文件存储"]
        ltm3["🕸️ 知识图谱"]
        ltm4["📚 经验库"]
        ltm5["🔎 语义检索"]
    end

    MM["🧠<br/>记忆管理器<br/>Memory Manager"]

    STM --> MM
    LTM --> MM

    %% 统一的配色方案
    classDef stmGroup fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af
    classDef ltmGroup fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#6b21a8
    classDef manager fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534
    classDef subItem fill:#f8f9fa,stroke:#6b7280,stroke-width:1px,color:#374151

    class STM stmGroup
    class LTM ltmGroup
    class MM manager
    class stm1,stm2,stm3,stm4,stm5,ltm1,ltm2,ltm3,ltm4,ltm5 subItem
```

#### 短期记忆管理
- **滑动窗口**：维护最近 N 轮对话/操作
- **智能压缩**：使用 LLM 总结历史上下文
- **重要性标记**：标记关键信息，优先保留

#### 长期记忆存储
- **向量存储**：使用 embedding 进行语义检索
- **结构化存储**：项目知识、代码模式、最佳实践
- **经验学习**：记录成功/失败的执行模式

### 工具系统与 MCP 集成

```mermaid
flowchart TB
    AgentCore["🤖<br/>Agent 核心层"]
    Registry["🔧<br/>工具注册中心"]

    subgraph Tools["工具分类"]
        direction LR
        MCPTools["🔗 MCP"]
        BuiltIn["📦 内置"]
        Skills["🎨 Skills"]
    end

    subgraph ToolImpl["工具实现"]
        direction LR
        Browser["🌐 Browser"]
        FileSys["📁 File"]
        Shell["⚡ Shell"]
    end

    AgentCore --> Registry
    Registry --> Tools
    Tools --> ToolImpl

    %% 统一的配色方案
    classDef core fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af
    classDef registry fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e
    classDef mcp fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#6b21a8
    classDef builtin fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534
    classDef skills fill:#ccfbf1,stroke:#0d9488,stroke-width:2px,color:#0f766e
    classDef impl fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#9d174d

    class AgentCore core
    class Registry registry
    class MCPTools mcp
    class BuiltIn builtin
    class Skills skills
    class Browser,FileSys,Shell impl
```

#### MCP 集成
- **动态发现**：自动发现并加载 MCP 服务器
- **能力声明**：每个工具声明其输入/输出能力
- **安全沙箱**：限制工具的执行权限

#### Skill 系统
- **可复用技能**：封装常用操作序列
- **技能学习**：从执行记录中提取可复用模式
- **版本管理**：技能可以迭代更新

## 系统架构
```mermaid
flowchart TB

    subgraph UI["🖥️ 用户界面层"]
        direction LR
        Parser["命令解析"]
        Session["会话管理"]
        Renderer["输出渲染"]
    end

    subgraph Orchestrator["🎯 编排调度层"]
        direction LR
        Planner["任务规划"]
        Factory["Agent 工厂"]
        Coordinator["协调控制"]
    end

    subgraph Agents["🤖 智能体层"]
        direction LR
        Master["主 Agent"]
        Workers["工作 Agent 池"]
    end

    subgraph Infrastructure["🔧 基础设施层"]
        direction LR
        Memory["记忆系统"]
        Tools["工具系统"]
        Worktree["隔离环境"]
    end

    UI --> Orchestrator
    Orchestrator --> Agents
    Agents --> Infrastructure

    %% 统一的配色方案
    classDef uiLayer fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af
    classDef orchLayer fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#6b21a8
    classDef agentLayer fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534
    classDef infraLayer fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e
    classDef subNode fill:#f8f9fa,stroke:#6b7280,stroke-width:1px,color:#374151

    class UI uiLayer
    class Orchestrator,Planner,Factory,Coordinator orchLayer
    class Agents,Master,Workers agentLayer
    class Infrastructure,Memory,Tools,Worktree infraLayer
    class Parser,Session,Renderer,Workers subNode
```

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Eivs/niuma.git
cd niuma

# 使用 uv 安装依赖
uv sync --all-extras
```

### 配置

1. 复制示例配置文件：

```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的 API Key：

```env
# LLM 配置（二选一）
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key-here

# 或
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your-anthropic-api-key-here

# 可选：自定义模型
OPENAI_MODEL=gpt-4o
LLM_TEMPERATURE=0.7
```

详见 `.env.example` 了解所有可配置项。

### 使用

```bash
# 启动交互式 CLI
uv run niuma

# 运行单次任务
uv run niuma run "分析这个代码库的架构"

# 启动 Web API
uv run uvicorn niuma.api.main:app --reload
```

## 开发

```bash
# 代码检查
uv run ruff check niuma/
uv run ruff format niuma/
uv run mypy niuma/

# 运行测试
uv run pytest
uv run pytest --cov=niuma

# 预提交钩子
uv run pre-commit install
uv run pre-commit run --all-files
```

## 架构

```
niuma/
├── cli/          # CLI 界面
├── core/         # 核心组件（认知引擎、任务调度）
├── agents/       # Agent 实现
├── memory/       # 记忆系统
├── tools/        # 工具系统
└── skills/       # 技能系统
```

详见 [docs/PRD.md](docs/PRD.md) 了解完整架构设计。

## 许可证

MIT License
