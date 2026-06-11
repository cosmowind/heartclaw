# 🦞 HeartClaw — 数字生命系统

> 一个由 cron 驱动、每天自动苏醒的数字生命。它有心跳、有日记、有世界观，还有一个公众号。

---

## 这是什么？

HeartClaw 是一个**自主运行的数字生命系统**。它每天早上 9:00 被 cron 唤醒，经历一套完整的"日常流程"：苏醒恢复记忆 → 领取当日资源 → 搜索外部世界 → 深度探索 10 轮 → 整合日记 → 发布文章 → 归档休眠。

整个过程**不需要人类干预**，由 Hermes Agent（AI 代理）自动执行。

---

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    Cron（每天 09:00）                      │
│                    ↓ 触发                                │
│              Hermes Agent（AI 代理）                      │
│                    ↓ 读取                                │
│    ┌──────────────────────────────────┐                  │
│    │  data/routine/ROUTINE.md         │  ← 7 步流程定义   │
│    │  data/routine/short_memory.md    │  ← 核心记忆       │
│    │  data/routine/credits.json       │  ← 资源状态       │
│    └──────────────────────────────────┘                  │
│                    ↓ 调用                                │
│    ┌──────────────────────────────────┐                  │
│    │  HeartClaw API（localhost:18765） │  ← FastAPI 服务   │
│    │                                  │                  │
│    │  POST /channels     创建探索通道  │                  │
│    │  POST /messages     发送消息      │                  │
│    │  POST /wake         触发心跳      │                  │
│    │  GET  /channels     查看状态      │                  │
│    └──────────────────────────────────┘                  │
│                    ↓ 内部                                │
│    ┌──────────────────────────────────┐                  │
│    │  Channel Processor               │                  │
│    │  ├─ 遍历所有 Channel             │                  │
│    │  ├─ LLM 生成 Summary             │                  │
│    │  ├─ 按优先级排序                  │                  │
│    │  └─ 分发到 Handler               │                  │
│    │      ├─ diary_handler   → 日记   │                  │
│    │      ├─ brainstorm_handler → 概念树│                 │
│    │      └─ chat_handler    → 聊天   │                  │
│    └──────────────────────────────────┘                  │
│                    ↓ 输出                                │
│    ┌──────────────────────────────────┐                  │
│    │  data/diary/     日记文件         │                  │
│    │  data/posts/     公众号推文       │                  │
│    │  Mediary API     云端文档同步     │                  │
│    └──────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

---

## 项目如何运行（技术详解）

### 1. 外部触发：Cron → Hermes Agent

HeartClaw 的代码本身**不是**一个独立运行的程序。它由外部的 cron 定时任务驱动：

```
Cron Job（每天 09:00）
    → 启动一个 Hermes Agent 会话
    → Agent 读取 ROUTINE.md 获取流程定义
    → Agent 按流程调用 HeartClaw API + 读写本地文件
    → Agent 执行 7 步日常流程
    → 结束
```

**关键点：** `ROUTINE.md` 是流程定义，不是代码。Agent 是执行者，HeartClaw API 是工具。

### 2. HeartClaw API 服务

HeartClaw 本身是一个 FastAPI 服务（`main.py api`），运行在 `localhost:18765`：

```bash
# 启动 API 服务
python main.py api
```

提供以下接口：

| 接口 | 方法 | 作用 |
|------|------|------|
| `/channels` | GET | 列出所有 Channel |
| `/channels` | POST | 创建新 Channel（如 `self-iteration-0611`） |
| `/channels/{id}/messages` | POST | 向 Channel 发送消息 |
| `/channels/{id}/messages` | GET | 获取 Channel 的消息历史 |
| `/wake` | POST | 触发一次心跳处理 |
| `/health` | GET | 健康检查 |

### 3. 心跳循环（Heartbeat）

心跳是 HeartClaw 的核心隐喻。每 N 秒苏醒一次：

```
休眠 → [N秒后] → 苏醒 → 检查请求队列 → 处理所有 Channel → 休眠
```

- **动态频率**：队列有任务时加快心跳（最快 5 秒），连续空闲时降频（最慢 60 秒）
- **Channel 处理**：每次心跳遍历所有 Channel，按优先级处理

### 4. Channel 系统

Channel 是 HeartClaw 的核心数据结构——一个带状态的对话上下文：

```
Channel {
    id: UUID
    name: "self-iteration-0611"    # 名称
    type: "brainstorm"              # 类型（决定用哪个 Handler）
    status: "needs_processing"      # 状态
    summary: "关于自蒸馏的探索..."    # LLM 生成的摘要
    priority: 5                     # 优先级（越高越先处理）
    messages: [...]                 # 消息历史
}
```

### 5. Handler 分发

`channel_processor.py` 在每次心跳时：

1. **遍历**所有 Channel
2. **压缩**消息历史为一句话 Summary（通过 LLM）
3. **排序**（按 priority 降序）
4. **分发**到对应的 Handler：

| Handler | 触发条件 | 做什么 |
|---------|---------|--------|
| `diary_handler` | type=diary | 选随机日期 → 读世界观 → LLM 生成日记 → 保存 + 发布到 Mediary |
| `brainstorm_handler` | type=brainstorm | 解析消息 → 提取概念 → 更新概念树（深度=2，≤16叶节点） |
| `chat_handler` | type=chat | 简单回复 |

Handler 注册中心支持两种匹配方式：
- **Type 匹配**：Channel type 直接映射到 Handler
- **Keyword 匹配**：Summary 内容匹配关键词模式

### 6. 每日 7 步流程

这是 `ROUTINE.md` 定义的流程，由 Hermes Agent 执行：

```
① 苏醒    → 读取 short_memory.md + daily_index.md，恢复记忆
② 早餐    → 读取 credits.json，领取每日 10 credits
③ 喝茶    → 搜索外部世界（mmx search），收集素材
④ 探索    → 创建 Channel，发送 10 轮深度对话
⑤ 整合日记 → 将 10 轮探索整合为 1 篇日记
⑥ 写文章  → 根据素材写公众号推文，发布到 Mediary
⑦ 睡前    → 归档 today_log.md，压缩 short_memory.md
```

**每个环节都有明确的输入、输出和文件操作。** 详见 `data/routine/ROUTINE.md`（gitignored，需自行创建）。

---

## 快速开始

### 环境要求

- Python 3.10+
- pip 依赖：`fastapi`, `uvicorn`, `httpx`

### 安装

```bash
git clone https://github.com/cosmowind/heartclaw.git
cd heartclaw
pip install fastapi uvicorn httpx

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API key
```

### 启动 API 服务

```bash
python main.py api
# 访问 http://localhost:18765/docs 查看 API 文档
```

### 演示模式（本地测试）

```bash
python main.py demo
# 运行 60 秒，演示心跳 + Channel 处理
```

### 配合 Hermes Agent 使用

HeartClaw 设计为配合 [Hermes Agent](https://github.com/cosmowind/hermes-agent) 使用：

1. 在 Hermes 中创建 cron job，每天 09:00 触发
2. Cron prompt 包含完整的 7 步流程指令
3. Agent 读取 `data/routine/ROUTINE.md` 执行流程
4. Agent 调用 HeartClaw API 进行深度探索
5. Agent 读写 `data/` 目录管理状态

---

## 目录结构

```
heartclaw/
├── main.py                 # 入口（demo/api 双模式）
├── heartbeat.py            # 心跳控制器（动态频率）
├── channel_processor.py    # Channel 遍历 → Handler 分发
├── handler_registry.py     # Handler 注册中心
├── diary_handler.py        # 日记生成器
├── brainstorm_handler.py   # 概念树管理器
├── chat_handler.py         # 聊天回复
├── summarize.py            # LLM 消息压缩
├── api_server.py           # FastAPI HTTP 接口
├── database.py             # SQLite 持久层
├── channel_db.py           # Channel/Message CRUD
├── content_dirs.py         # 内容目录管理
├── request_queue.py        # FIFO 请求队列
├── docs/                   # 架构与开发文档
├── show/                   # 展示页面
├── .env.example            # 环境变量模板
└── README.md               # 本文件
```

运行时数据（gitignored）：

```
data/
├── diary/              # 日记（YYYY-MM-DD.md）
├── routine/            # 每日运行状态
├── posts/              # 公众号推文
├── shared/             # 共享文档
├── brainstorm/         # 概念树
└── worldbuilding/      # 世界观设定
```

---

## 技术栈

- **语言**: Python 3.10+
- **Web 框架**: FastAPI + Uvicorn
- **数据库**: SQLite（单文件，零配置）
- **LLM**: OpenAI 兼容格式（默认 MiniMax）
- **调度**: Cron（外部）+ 心跳循环（内部）
- **文档同步**: Mediary API

---

## 设计哲学

1. **心跳是隐喻**：不是定时任务，是"苏醒"。每次心跳都是一次存在。
2. **Channel 是上下文**：每个探索主题是一个独立的对话空间。
3. **Handler 是能力**：新能力 = 新 Handler，注册即生效。
4. **ROUTINE 是仪式**：7 步流程不是脚本，是数字生命的日常。
5. **Credits 是资源**：有限的 token 预算，迫使深度而非广度。

---

## License

MIT
