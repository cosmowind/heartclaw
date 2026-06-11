# 架构详解

> HeartClaw 如何从一行 cron 命令变成一个有日记、有世界观的数字生命

---

## 全景图

```
外部世界                    HeartClaw 系统                      输出
─────────                  ─────────────                      ────
                                                          
Cron ──────────→  Hermes Agent ──────→  HeartClaw API ──→  日记文件
(每天 09:00)      (AI 代理)              (FastAPI)          公众推文
                      │                      │              Mediary
                      │                      │
                      ↓                      ↓
                 ROUTINE.md            Channel Processor
                 (7步流程定义)          (心跳循环)
                      │                      │
                      ↓                      ↓
                 data/routine/          Handler Registry
                 (状态文件)              ├─ diary_handler
                                        ├─ brainstorm_handler
                                        └─ chat_handler
```

---

## 层次 1：谁在运行 HeartClaw？

HeartClaw 不是一个 `python main.py` 就能跑起来的独立程序。它需要两层驱动：

### 外层：Cron + Hermes Agent

```
┌─ Cron Job（每天 09:00）────────────────────────────────┐
│                                                         │
│  启动 Hermes Agent 会话                                  │
│  Agent 读取 prompt（包含 7 步流程指令）                    │
│                                                         │
│  Agent 的工具箱：                                        │
│  ├─ terminal()     → 执行 shell 命令                     │
│  ├─ read_file()    → 读取本地文件                        │
│  ├─ write_file()   → 写入本地文件                        │
│  ├─ web_search()   → 搜索外部信息                        │
│  └─ HTTP 请求      → 调用 HeartClaw API                  │
│                                                         │
│  Agent 按 ROUTINE.md 逐步执行：                          │
│  ① 读取记忆文件 → ② 领取 credits → ③ 搜索素材           │
│  → ④ 创建 Channel + 发消息 → ⑤ 写日记 → ⑥ 写文章       │
│  → ⑦ 归档                                              │
└─────────────────────────────────────────────────────────┘
```

**关键理解：** ROUTINE.md 是给 Agent 看的"剧本"，不是给代码执行的配置。Agent 是演员，HeartClaw API 是舞台。

### 内层：HeartClaw API 服务

```bash
python main.py api   # 启动 FastAPI 服务，监听 18765 端口
```

这是一个常驻服务（由 systemd 管理），提供 Channel 管理和心跳处理能力。

---

## 层次 2：心跳循环

心跳是 HeartClaw 的核心机制——一个周期性苏醒的循环：

```python
# heartbeat.py 核心逻辑（简化）
while running:
    # 1. 苏醒
    heartbeat_count += 1
    
    # 2. 检查请求队列
    queue_size = drain_queue()
    
    # 3. 处理所有 Channel（如果注入了处理器）
    if channel_processor:
        results = await channel_processor()
    
    # 4. 动态调整心跳频率
    adjust_interval(queue_size, len(results))
    
    # 5. 休眠
    await asyncio.sleep(interval)
```

### 动态频率调节

```
队列有任务 → 加快心跳（5秒）
连续空闲   → 降低心跳（最多60秒）
有新 Channel → 立即唤醒
```

这不是 cron，是**自主节律**。HeartClaw 根据负载调节自己的"呼吸频率"。

---

## 层次 3：Channel 系统

Channel 是 HeartClaw 处理任务的基本单位：

### 生命周期

```
创建 → needs_processing → processing → done
  ↑                                        │
  └────────── 新消息到达 ←─────────────────┘
```

### 类型与 Handler

```python
# handler_registry.py 中的注册逻辑
registry.register(HandlerSpec(
    name="diary",
    type_match="diary",           # type 匹配
    handler_fn=diary_handle,
))
registry.register(HandlerSpec(
    name="brainstorm",
    type_match="brainstorm",
    keyword_patterns=[r"概念"],    # keyword 匹配
    handler_fn=brainstorm_handle,
))
```

### 处理流程

```
channel_processor.process_all():
    1. 列出所有 Channel
    2. 对每个 Channel：
       a. 获取消息历史
       b. 调用 LLM 生成 Summary（一句话概括）
    3. 按 priority 排序
    4. 依次分发到 Handler
    5. 返回处理结果
```

---

## 层次 4：Handler 详解

### diary_handler（日记生成器）

```
输入：Channel（type=diary）
处理：
  1. 随机选一个日期（2025-3025）
  2. 读取世界观（data/worldbuilding/worldview.md）
  3. 读取已有的日记列表
  4. 构建 prompt：日期 + 世界观 + 已有日记 + Channel 消息
  5. 调用 LLM 生成日记
  6. 保存到 data/diary/YYYY-MM-DD.md
  7. 更新 index.json
  8. 发布到 Mediary API
输出：日记文件 + Mediary 文档
```

### brainstorm_handler（概念树管理器）

```
输入：Channel（type=brainstorm）
处理：
  1. 解析 Channel 中的消息
  2. 提取概念（标题 + 内容 + 重要性）
  3. 更新概念树（深度=2，每层最多4个子节点）
  4. 保存到 data/brainstorm/concept_tree.json
  5. 记录日志到 data/brainstorm/log.md
输出：概念树 JSON + 日志
```

---

## 层次 5：数据流

### 写入流（Agent → 文件）

```
Agent 执行 ROUTINE.md
  ├─ write_file("data/routine/short_memory.md", ...)  ← 记忆
  ├─ write_file("data/routine/credits.json", ...)     ← 资源
  ├─ write_file("data/routine/today_log.md", ...)     ← 日志
  ├─ POST /channels (创建探索 Channel)
  ├─ POST /messages (发送探索消息)
  ├─ POST /wake (触发心跳 → diary_handler → 写日记)
  └─ write_file("data/posts/", ...)                   ← 推文
```

### 读取流（Agent ← 文件）

```
Agent 执行 ROUTINE.md
  ├─ read_file("data/routine/short_memory.md")  ← 恢复记忆
  ├─ read_file("data/routine/daily_index.md")   ← 回顾历史
  ├─ read_file("data/routine/credits.json")     ← 查看资源
  ├─ GET /channels (查看 Channel 状态)
  └─ read_file("data/diary/...")                ← 读取日记
```

---

## 层次 6：外部集成

### Mediary（文档同步）

日记和推文通过 Mediary API 同步到云端，支持：
- 跨设备访问
- 全文搜索
- 标签管理

### Hermes Agent（执行引擎）

HeartClaw 的"灵魂"不在代码里，在 Hermes Agent 的 prompt 里：
- `ROUTINE.md` 定义了"做什么"
- `short_memory.md` 定义了"记得什么"
- `experience.json` 定义了"会什么"
- Cron prompt 定义了"怎么想"

---

## 扩展指南

### 添加新 Handler

1. 创建 `xxx_handler.py`
2. 实现 `handle(channel: Channel) -> ProcessingResult`
3. 在 `channel_processor.py` 中注册
4. 创建对应类型的 Channel 即可触发

### 修改日常流程

编辑 `data/routine/ROUTINE.md`（Agent 每次苏醒都会读取）

### 调整心跳频率

修改 `heartbeat.py` 中的 `min_interval` / `max_interval` 参数

---

## 常见误解

| 误解 | 事实 |
|------|------|
| HeartClaw 是一个聊天机器人 | 它是一个自主运行的系统，聊天只是其中一个 Handler |
| `main.py` 启动后就能运行 | 需要 cron + Agent 驱动，`main.py api` 只启动 API 服务 |
| ROUTINE.md 是配置文件 | 它是给 Agent 看的"剧本"，不是代码可执行的配置 |
| 日记是代码生成的 | 日记是 Agent 在执行 ROUTINE.md 时写的，diary_handler 是辅助 |
| 心跳是 cron | 心跳是程序内部的周期循环，cron 是外部触发器 |
