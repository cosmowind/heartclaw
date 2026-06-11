# 目录结构

> **文档路径**: `/www/wwwroot/projects/heart/docs/structure.md`
> **更新日期**: 2026-05-09

---

```
heart/
├── SPEC.md                      # 项目总规范（龙虾心跳隐喻）
├── main.py                      # 入口（demo/api 双模式）
├── heartbeat.py                  # 心跳控制器（Heartbeat + Lobster，含 Channel 处理器注入点）
├── request_queue.py             # FIFO 请求队列（Request + RequestQueue）
├── database.py                   # SQLite 连接与表初始化
├── channel_db.py                # Channel/Message CRUD
├── summarize.py                  # LLM Summarize API
├── channel_processor.py         # 心跳遍历 Channel → Summary → 排序 → 处理
├── api_server.py                # FastAPI 路由
│
├── docs/                        # WCS 基线文档
│   ├── dev_plan.md              # 开发计划
│   ├── dev_log.md               # 实施记录
│   ├── project_status.md        # 当前状态
│   ├── features.md              # 能力清单
│   ├── structure.md             # 本文件
│   ├── error_book.md            # 错误手册
│   └── CODING_STANDARDS.md      # 代码规范
│
└── heart.db                     # SQLite 数据库文件（运行时生成）
```

---

## 模块职责

| 文件 | 职责 | 状态 |
|---|---|---|
| `heartbeat.py` | 心跳循环、唤醒、休眠控制，支持 Channel 处理器注入 | 已完成 |
| `request_queue.py` | FIFO 队列、请求数据模型 | 已完成 |
| `main.py` | 入口、演示、心跳启动，双模式 | 已完成 |
| `database.py` | SQLite 连接、表初始化（channels + messages） | 已完成 |
| `channel_db.py` | Channel/Message CRUD，同步函数 | 已完成 |
| `summarize.py` | LLM Summarize，OpenAI-compatible | 已完成 |
| `channel_processor.py` | Channel 遍历、Summary、排序、处理 | 已完成 |
| `api_server.py` | FastAPI 路由（Channel/Message/Wake/Health） | 已完成 |
