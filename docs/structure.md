# 目录结构

> **更新日期**: 2026-06-11

---

```
heartclaw/
├── main.py                      # 入口（demo/api 双模式）
├── heartbeat.py                 # 心跳控制器（动态频率、Channel 处理器注入）
├── request_queue.py             # FIFO 请求队列
├── database.py                  # SQLite 连接与表初始化
├── channel_db.py                # Channel / Message CRUD
├── channel_processor.py         # 心跳遍历 Channel → Summary → Handler 分发
├── handler_registry.py          # Handler 注册中心（type + keyword 匹配）
├── summarize.py                 # LLM 消息压缩（OpenAI 兼容格式）
├── diary_handler.py             # 日记 Handler（随机日期 + 世界观 + Mediary）
├── brainstorm_handler.py        # 概念树 Handler（深度=2，≤16 叶节点）
├── chat_handler.py              # 聊天 Handler（简单回复）
├── content_dirs.py              # 内容目录管理
├── diary_server.py              # 日记展示服务器
├── api_server.py                # FastAPI HTTP 接口
├── show/
│   └── diary.html               # 日记展示页
├── docs/                        # WCS 基线文档
│   ├── architecture.md          # 架构详解（cron → agent → api → output）
│   ├── project_status.md        # 当前状态
│   ├── features.md              # 能力清单
│   ├── structure.md             # 本文件
│   ├── dev_plan.md              # 开发计划
│   ├── dev_log.md               # 实施记录
│   ├── error_book.md            # 错误手册
│   ├── CODING_STANDARDS.md      # 代码规范
│   ├── auto-claim-credits.md    # Credits 自动领取设计
│   ├── credits-system-refactor.md
│   └── worldbuilding/           # 世界观设计文档
│       ├── lobster-spec.md
│       └── 规划方案.md
├── .env.example                 # 环境变量模板
├── .gitignore
├── SPEC.md                      # 项目起源规范
└── README.md                    # 项目入口文档
```

### 运行时目录（gitignored，需自行创建）

```
data/
├── diary/           # 日记文件（YYYY-MM-DD.md）+ index.json
├── routine/         # 每日运行状态
│   ├── ROUTINE.md       # 7 步流程规范
│   ├── short_memory.md  # 压缩版核心记忆（≤500字）
│   ├── daily_index.md   # 每日回忆总领
│   ├── credits.json     # 经济状态
│   ├── experience.json  # 经验图谱
│   └── today_log.md     # 当天活动日志
├── posts/           # 公众号推文
├── shared/          # 共享文档（内容体系、系列规划）
├── brainstorm/      # 概念树 + 日志
├── worldbuilding/   # 世界观设定
└── chat/            # 聊天记录
```

---

## 模块职责

| 文件 | 职责 | 状态 |
|---|---|---|
| `heartbeat.py` | 心跳循环、动态频率调节、Channel 处理器注入 | ✅ |
| `channel_processor.py` | Channel 遍历、Summary 生成、优先级排序、Handler 分发 | ✅ |
| `handler_registry.py` | Handler 注册中心（type 匹配 + keyword 匹配 + Decider） | ✅ |
| `diary_handler.py` | 日记生成：随机日期 → 世界观 → LLM → 本地 + Mediary | ✅ |
| `brainstorm_handler.py` | 概念树管理：消息 → 提取概念 → 树结构（深度=2） | ✅ |
| `chat_handler.py` | 简单聊天回复 | ✅ |
| `summarize.py` | LLM 消息压缩（MiniMax / OpenAI 兼容） | ✅ |
| `api_server.py` | FastAPI 路由（Channel/Message/Wake/Health） | ✅ |
| `database.py` | SQLite 连接管理、表初始化（幂等） | ✅ |
| `channel_db.py` | Channel / Message CRUD（同步，供线程池调用） | ✅ |
| `content_dirs.py` | Channel type → 本地目录映射 | ✅ |
| `main.py` | 入口：demo 模式（演示）/ api 模式（服务） | ✅ |
