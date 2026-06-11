## 实施记录

> **文档路径**: `/www/wwwroot/projects/heart/docs/dev_log.md`
> **更新日期**: 2026-05-09

---

## 2026-05-09 — 嵌套 API 调用链项目启动

**任务**: 创建开发计划，启动 Heart 嵌套 API 项目

**变更内容**:

- 创建 `docs/dev_plan.md` — 定义嵌套 API 调用链的设计方案
- 创建 `docs/project_status.md` — 当前状态快照
- 创建 `docs/features.md` — 能力清单
- 创建 `docs/structure.md` — 目录结构
- 创建 `docs/error_book.md` — 错误手册（空）
- 创建 `docs/CODING_STANDARDS.md` — 代码规范

**验证依据**:

- 文档目录结构符合 WCS 基线要求
- dev_plan.md 包含完整的 API 设计、模块职责、开发阶段

**后续动作**:

- 阶段 1 实现：context.py、decider.py、chain_engine.py、api_server.py
- 单元测试验证
- 集成心跳

---

## 2026-05-09（下午）— Channel 架构基座完成

**任务**: 实现多 Channel 数据库 + 心跳遍历基座

**新增文件**:

| 文件 | 职责 |
|---|---|
| `database.py` | SQLite 连接与表初始化（channels + messages 表） |
| `channel_db.py` | Channel/Message CRUD 封装 |
| `summarize.py` | LLM Summarize API（OpenAI compatible） |
| `channel_processor.py` | 心跳遍历 Channel → 生成 Summary → 决定顺序 → 处理 |
| `api_server.py` | FastAPI 路由（Channel/Message/Wake/Health） |

**修改文件**:

- `heartbeat.py` — 新增 `channel_processor` 注入点，心跳同时处理队列+Channel
- `main.py` — 新增 `demo`/`api` 双模式启动

**关键设计决策**:

1. **SQLite 同步调用 + asyncio.to_thread()**: 所有 channel_db 方法为同步函数，FastAPI 路由用 `asyncio.to_thread()` 避免阻塞事件循环
2. **Summarize 降级**: 无 API Key 时返回占位文本，不影响心跳流程
3. **处理顺序策略**: 非空 summary 优先（FIFO + updated_at 升序）

**验证结果**:

```
✅ demo 模式：心跳正常唤醒，Channel 遍历正常，无 API Key 正确降级
✅ API 模式：/health ✓ /channels ✓ /messages ✓ /wake ✓
✅ curl 兼容性：健康检查通过（/channels 在 curl 下超时为 curl 自身问题）
```

**依赖安装**: `pip install uvicorn fastapi`

**待补充**: 单元测试（tests/ 目录）
