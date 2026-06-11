# 项目状态

> **文档路径**: `/www/wwwroot/projects/heart/docs/project_status.md`
> **更新日期**: 2026-05-09

---

## 技术栈

- **语言**: Python 3.10+
- **异步框架**: asyncio（原生）
- **Web 框架**: FastAPI（计划引入）
- **依赖**: fastapi, uvicorn（待安装）

---

## 当前能力

### 已实现

- ✅ 心跳循环（每 10 秒苏醒）
- ✅ 内存请求队列（FIFO）
- ✅ 任务处理（模拟）
- ✅ 优雅退出（SIGINT / SIGTERM）

### 计划中

- 🔄 嵌套 API 调用链（本次迭代）
- ⬜ Web API 层（FastAPI）
- ⬜ Redis 持久化队列
- ⬜ 多龙虾协作
- ⬜ 动态心跳频率

---

## 目录结构

```
heart/
├── SPEC.md               # 项目总规范
├── docs/                 # 文档目录
│   ├── dev_plan.md       # 开发计划
│   ├── dev_log.md        # 实施记录
│   ├── project_status.md # 本文件
│   ├── features.md        # 能力清单
│   ├── structure.md       # 目录结构
│   ├── error_book.md      # 错误手册
│   └── CODING_STANDARDS.md # 代码规范
├── heartbeat.py          # 心跳核心
├── request_queue.py      # 请求队列
└── main.py               # 入口
```

---

## 运行状态

- **启动命令**: `python main.py`
- **默认心跳间隔**: 10 秒
- **测试状态**: 正常运行

---

## 已知限制

- 队列仅内存存储，程序重启后丢失
- 无持久化能力
- 无 Web API 接口
