# 能力清单

> **文档路径**: `/www/wwwroot/projects/heart/docs/features.md`
> **更新日期**: 2026-05-09

---

## 心跳核心

### 心跳循环

- **状态**: done
- **描述**: 每 10 秒（可配置）苏醒一次，检查请求队列
- **文件**: `heartbeat.py`

### 请求队列

- **状态**: done
- **描述**: 内存 FIFO 队列，支持 `add_request`、`get_nowait`
- **文件**: `request_queue.py`

---

## Channel 架构（本次迭代）

### SQLite 数据库层

- **状态**: done
- **描述**: channels + messages 表，带索引
- **文件**: `database.py`

### Channel CRUD

- **状态**: done
- **描述**: 创建/查询/更新/删除 Channel，添加/查询 Message
- **文件**: `channel_db.py`

### Summarize API

- **状态**: done
- **描述**: 将 Channel 最近 20 条消息压缩成一句话总结
- **文件**: `summarize.py`
- **备注**: OpenAI-compatible API，无 Key 时降级返回占位文本

### Channel 处理器

- **状态**: done
- **描述**: 心跳遍历所有 Channel → 生成 Summary → 决定处理顺序 → 依次处理
- **文件**: `channel_processor.py`

### Web API 层

- **状态**: done
- **描述**: FastAPI 路由：Channel CRUD、Message 读写、Summarize、Wake
- **文件**: `api_server.py`

---

## 后续开发计划

- F1: 实际 Channel 处理逻辑（Handler 匹配）
- F2: Channel 优先级策略
- F3: Channel 持久化与迁移
- F4: 多龙虾协作
- F5: 动态心跳频率
- F6: 嵌套 API 调用链（Decider 机制）
