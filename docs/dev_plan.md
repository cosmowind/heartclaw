# Heart 项目开发计划

> **文档路径**: `/www/wwwroot/projects/heart/docs/dev_plan.md`
> **维护者**: wind / Hermes
> **更新日期**: 2026-05-09（第2次修订）
> **状态**: 进行中

---

## 项目概述

Heart（心跳）是"我本是龙虾"宇宙中的核心隐喻：**一个每 10 秒醒来查看请求队列的程序**。

本次迭代引入**多 Channel 架构**——本地数据库存储各 Channel 的对话历史，心跳苏醒时遍历所有 Channel，通过 Summarize API 了解各 Channel 当前状态，按需按序处理。

**运行模式**：内网测试模式。对话由 wind 和 Hermes 通过代码直接操作 Channel 数据库完成，不暴露公网前后端。

---

## 核心架构

### 整体架构

```
┌─────────────────────────────────────────────┐
│              SQLite 本地数据库               │
│                                             │
│  Channel: brainstorm  ←→  brainstorm/目录   │
│  Channel: chat       ←→  chat/目录           │
└──────────┬──────────────────┬────────────────┘
           │                 │
           ▼                 ▼
┌──────────────────┐  ┌─────────────────────┐
│  Summarize API   │  │   Channel 存储库     │
│  每 channel 一句话│  │   (CRUD + 历史)      │
└────────┬─────────┘  └─────────────────────┘
         │                    ▲
         ▼                    │
┌──────────────────────────────────────────┐
│           心跳苏醒（Beat Loop）            │
│                                          │
│  1. 获取所有 Channel                     │
│  2. 对每个 Channel 调用 Summarize API    │
│  3. 根据 Summary 决定处理顺序             │
│  4. 按序处理有需求的 Channel              │
│  5. 休眠                                  │
└──────────────────────────────────────────┘
```

### 核心概念

#### Channel（频道）

- 一个 Channel 代表一个**独立的对话上下文 + 内容存储目录**
- Channel 类型：
  - `brainstorm`：心跳项目头脑风暴，生成哲学知识库
  - `chat`：低优先级聊天测试
- 每个 Channel 有状态：`idle`、`needs_processing`、`processing`、`done`

#### Message（消息）

- 属于某个 Channel 的一条对话记录
- 字段：`id`, `channel_id`, `role`（user/assistant/system）, `content`, `created_at`

#### 内容目录

- 每个 Channel 对应一个本地目录：`data/<channel_name>/`
- 随运行生成文件（如知识库节点、聊天记录等）
- 所有 Channel 共享统一的 `data/` 根目录

#### Summary（总结）

- 每个 Channel 的当前状态被压缩成**一句话描述**
- 由 Summarize API 调用 LLM 生成

#### 处理顺序决定

- 遍历所有 Channel 的 Summary
- 策略：needs_processing > idle，相同状态按 updated_at 升序
- 形成处理队列，按序执行

---

## 当前开发范围（基座框架）

> **目标**：心跳苏醒后能调用 API 遍历所有 Channel，决定处理顺序。

### 阶段 1：数据库层

#### Channel 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT (PK) | UUID |
| name | TEXT | Channel 名称（唯一） |
| type | TEXT | brainstorm / chat |
| status | TEXT | idle / needs_processing / processing / done |
| summary | TEXT | 最近一次 Summarize 的结果 |
| created_at | FLOAT | 创建时间 |
| updated_at | FLOAT | 最后更新时间 |

#### Message 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER (PK) | 自增 ID |
| channel_id | TEXT (FK) | 所属 Channel |
| role | TEXT | user / assistant / system |
| content | TEXT | 消息内容 |
| created_at | FLOAT | 创建时间 |

### 阶段 2：内容目录管理

- `data/<channel_name>/` 目录结构
- 每个 Channel 类型有专属的目录管理模块

### 阶段 3：Channel 存储库

- `channel_db.py`: SQLite 操作封装
  - `create_channel(name, type) -> Channel`
  - `get_channel(channel_id) -> Channel`
  - `list_channels() -> list[Channel]`
  - `update_channel_status(channel_id, status)`
  - `update_channel_summary(channel_id, summary)`
  - `add_message(channel_id, role, content) -> Message`
  - `get_messages(channel_id, limit=50) -> list[Message]`

### 阶段 4：Summarize API

- `summarize_channel(messages) -> str`
- 输入：某 Channel 的最新 N 条消息（默认 20 条）
- 输出：一句话总结

### 阶段 5：心跳 → Channel 处理流程

见 `channel_processor.py` 实现。

### 阶段 6：基础 API 端点

| 端点 | 方法 | 说明 |
|---|---|---|
| `POST /channels` | 创建 Channel |  |
| `GET /channels` | 列表所有 Channel |  |
| `GET /channels/{id}` | 获取单个 Channel |  |
| `DELETE /channels/{id}` | 删除 Channel |  |
| `POST /channels/{id}/messages` | 添加消息 |  |
| `GET /channels/{id}/messages` | 获取消息历史 |  |
| `POST /channels/{id}/summarize` | 手动触发 Summarize |  |
| `POST /wake` | 唤醒心跳，立即执行一轮 |  |

---

## 测试案例

### 测试案例 A：Brainstorm Channel（心跳项目头脑风暴）

**目标**：通过对话驱动，构建心跳项目的哲学知识库（层级概念树）。

**Channel 配置**：
- `name`: brainstorm
- `type`: brainstorm
- 目录: `data/brainstorm/`

**概念树规范**：
- 每个知识单元 = 一个**节点**（概念 + 内容）
- 每个节点最多 **4 个子节点**
- 每个子节点最多 **4 个子子节点**（树深度 2）
- 新 idea 出现时，找到树中对应节点插入
- **定期维护**：重要性高的节点上浮到顶层，低的沉到底层
- 可按**关联性**重新架构

**运行方式**：
1. Hermes 和 wind 对话（我通过代码写入 Channel）
2. 每次心跳检查该 Channel
3. 对 Channel 做 Summarize
4. 有新的对话内容 → 解析 → 生成/更新概念树节点 → 写入 `data/brainstorm/` 目录
5. 结果通过 Channel 的 assistant 消息返回

**内容管理目录**：
```
data/brainstorm/
├── concept_tree.json    # 概念树本体（JSON）
├── concepts/            # 每个概念单独一个文件
│   ├── <concept_id>.json
│   └── ...
└── log.md               # 头脑风暴操作日志
```

### 测试案例 B：Chat Channel（低优先级聊天）

**目标**：测试重要性排序，发出"你好"即结束。

**Channel 配置**：
- `name`: chat
- `type`: chat
- 目录: `data/chat/`

**运行方式**：
1. 创建 chat Channel，写入初始化消息
2. 心跳触发处理
3. 处理结果：仅打印"已收到你好"，无后续操作
4. 状态标记为 done

**内容管理目录**：
```
data/chat/
└── log.md               # 聊天日志
```

---

## 后续开发计划（待实现）

以下内容**不在当前范围**，仅作记录。

### F1：实际 Channel 处理逻辑

- 根据 Summary 内容匹配到具体 Handler（客服、查询、任务执行等）
- Handler 处理完成后写回复到 Message
- 支持 Handler 的 Decider：判断是否需要继续处理

### F2：Channel 优先级策略

- 支持配置处理策略：FIFO、紧急优先、轮询、基于 Summary 内容匹配
- 可在 Channel 元数据中标记优先级

### F3：Channel 持久化与迁移

- 支持导出/导入 Channel 数据（JSON）
- 历史消息归档

### F4：多龙虾协作

- 多个心跳实例共享数据库
- 分布式锁防止重复处理

### F5：动态心跳频率

- 队列/待处理多时加快心跳
- 空闲时降低频率节能

---

## 技术方案

### 架构

```
heart/
├── SPEC.md                      # 项目总规范
├── docs/                        # WCS 基线文档
│   ├── dev_plan.md              # 本文件
│   ├── dev_log.md               # 实施记录
│   ├── project_status.md        # 当前状态
│   ├── features.md              # 能力清单
│   ├── structure.md            # 目录结构
│   ├── error_book.md            # 错误手册
│   └── CODING_STANDARDS.md      # 代码规范
├── heartbeat.py                  # 心跳核心
├── request_queue.py             # 请求队列
├── main.py                      # 入口
├── database.py                  # SQLite 连接与表初始化
├── channel_db.py               # Channel CRUD
├── summarize.py                  # Summarize API
├── channel_processor.py         # Channel 处理逻辑
├── api_server.py               # FastAPI 路由
│
└── data/                        # 【新增】Channel 内容目录
    ├── brainstorm/              # Brainstorm Channel 目录
    │   ├── concept_tree.json
    │   ├── concepts/
    │   └── log.md
    └── chat/                   # Chat Channel 目录
        └── log.md
```

### 技术选型

- **数据库**: SQLite（零依赖）
- **Web 框架**: FastAPI
- **LLM 调用**: OpenAI-compatible API（可配置 base_url + api_key）

### 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | （空） | LLM API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 地址 |
| `SUMMARIZE_MODEL` | `gpt-4o-mini` | Summarize 模型 |
| `HEART_DB_PATH` | `./heart.db` | 数据库路径 |

---

## 验收标准（当前阶段）

1. **数据库层** 能正确创建 Channel、写入 Message、查询历史
2. **Summarize API** 能对 Channel 生成一句话总结
3. **心跳 Beat** 能遍历所有 Channel 并生成 Summary
4. **处理顺序** 能根据 Summary 决定先后（空 Summary 排后）
5. **不破坏原有心跳功能** — 定时心跳 + 队列处理保持正常
6. **API 端点** 可调用，创建/查询 Channel 正常
7. **测试案例 A**：Brainstorm Channel 能通过对话生成概念树节点
8. **测试案例 B**：Chat Channel 能正确低优先级处理

---

## 风险与依赖

- **风险**: LLM API 调用耗时可能较长，需设置超时
- **依赖**: `fastapi`, `uvicorn`, `aiohttp`（`pip install fastapi uvicorn aiohttp`）

---

## 参考资料

- [心跳雏形 SPEC.md](../SPEC.md)
- [WCS 开发规范](../../../../.hermes/skills/wcs-cn/SKILL.md)
