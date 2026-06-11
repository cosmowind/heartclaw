# 能力清单

> **更新日期**: 2026-06-11

---

## 核心能力

### 🫀 心跳循环
- 每 N 秒苏醒一次（默认 10 秒）
- 动态频率调节（5-60 秒）
- 队列有任务时加快，连续空闲时降频
- 优雅退出（SIGINT / SIGTERM）

### 📡 Channel 系统
- 创建 / 删除 / 列出 Channel
- 发送 / 获取消息
- 状态管理（idle → needs_processing → processing → done）
- 优先级排序
- LLM 自动生成 Summary

### 🔧 Handler 注册中心
- Type 匹配（Channel type → Handler）
- Keyword 匹配（Summary 内容 → Handler）
- Decider 机制（判断是否需要继续处理）
- 优先级排序

### 📖 日记生成器
- 随机选择虚拟日期（2025-3025）
- 基于世界观设定生成
- 参考已有日记避免重复
- LLM 生成完整日记
- 保存本地 + 发布到 Mediary

### 🧠 概念树管理器
- 从消息中提取概念
- 树结构管理（深度=2，每层≤4子节点）
- JSON 持久化
- 日志记录

### 💬 聊天回复
- 简单消息回复
- Channel 状态管理

---

## 基础设施

### 🗄️ 数据持久化
- SQLite 数据库（Channel + Message）
- 文件系统（日记、推文、状态文件）
- Mediary API（云端同步）

### 🌐 HTTP 接口
- FastAPI 自动文档（/docs）
- Channel CRUD
- Message CRUD
- Wake 触发
- Health 检查

### 📊 内容管理
- Channel type → 目录映射
- 日记索引（index.json）
- 推文元数据（meta.json）
