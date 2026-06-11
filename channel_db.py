"""
心跳 — Channel 存储库
封装 Channel 和 Message 的 CRUD 操作

所有方法均为同步（供 FastAPI 路由在线程池中调用）。
如需异步接口，请使用 asyncio.to_thread(channel_db.method, ...)。
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from database import get_connection


@dataclass
class Channel:
    """Channel 数据模型"""
    id: str
    name: str
    type: str          # brainstorm / chat / generic
    status: str        # idle / needs_processing / processing / done
    summary: str
    priority: int = 0  # 优先级，越高越优先处理
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class Message:
    """Message 数据模型"""
    id: int
    channel_id: str
    role: str  # user / assistant / system
    content: str
    created_at: float


class ChannelDB:
    """
    Channel 存储库。

    提供 Channel 和 Message 的 CRUD 操作。
    """

    # ── Channel 操作 ───────────────────────────────────────

    def create_channel(self, name: str, channel_type: str = "generic", priority: int = 0) -> Channel:
        """创建新 Channel"""
        channel_id = str(uuid.uuid4())
        now = time.time()

        with get_connection() as conn:
            cursor = conn.cursor()
            # 检查是否有 priority 列
            cursor.execute("PRAGMA table_info(channels)")
            columns = [r[1] for r in cursor.fetchall()]
            has_priority = 'priority' in columns

            if has_priority:
                cursor.execute(
                    """
                    INSERT INTO channels (id, name, type, status, summary, priority, created_at, updated_at)
                    VALUES (?, ?, ?, 'idle', ?, ?, ?, ?)
                    """,
                    (channel_id, name, channel_type, '', priority, now, now),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO channels (id, name, type, status, summary, created_at, updated_at)
                    VALUES (?, ?, ?, 'idle', '', ?, ?)
                    """,
                    (channel_id, name, channel_type, now, now),
                )

        return Channel(
            id=channel_id,
            name=name,
            type=channel_type,
            status='idle',
            summary='',
            priority=priority,
            created_at=now,
            updated_at=now,
        )

    def get_channel(self, channel_id: str) -> Optional[Channel]:
        """根据 ID 获取 Channel"""
        # 获取 columns 信息（兼容迁移前的数据库）
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(channels)")
            columns = [r[1] for r in cursor.fetchall()]
            has_type = 'type' in columns
            has_priority = 'priority' in columns

            cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
            row = cursor.fetchone()

        if row is None:
            return None

        row_dict = dict(row)
        row_type = row_dict.get('type', 'generic') if has_type else 'generic'
        row_priority = row_dict.get('priority', 0) if has_priority else 0
        return Channel(
            id=row_dict['id'],
            name=row_dict['name'],
            type=row_type,
            status=row_dict['status'],
            summary=row_dict['summary'],
            priority=row_priority,
            created_at=row_dict['created_at'],
            updated_at=row_dict['updated_at'],
        )

    def list_channels(self) -> list[Channel]:
        """列出所有 Channel（按 updated_at 升序）"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(channels)")
            columns = [r[1] for r in cursor.fetchall()]
            has_type = 'type' in columns
            has_priority = 'priority' in columns

            cursor.execute(
                'SELECT * FROM channels ORDER BY updated_at ASC'
            )
            rows = cursor.fetchall()

        result = []
        for row in rows:
            row_dict = dict(row)
            row_type = row_dict.get('type', 'generic') if has_type else 'generic'
            row_priority = row_dict.get('priority', 0) if has_priority else 0
            result.append(Channel(
                id=row_dict['id'],
                name=row_dict['name'],
                type=row_type,
                status=row_dict['status'],
                summary=row_dict['summary'],
                priority=row_priority,
                created_at=row_dict['created_at'],
                updated_at=row_dict['updated_at'],
            ))
        return result

    def update_channel_status(self, channel_id: str, status: str) -> None:
        """更新 Channel 状态"""
        now = time.time()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE channels SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, channel_id),
            )

    def update_channel_summary(self, channel_id: str, summary: str) -> None:
        """更新 Channel 的 summary"""
        now = time.time()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE channels SET summary = ?, updated_at = ? WHERE id = ?",
                (summary, now, channel_id),
            )

    def update_channel_priority(self, channel_id: str, priority: int) -> None:
        """更新 Channel 的优先级"""
        now = time.time()
        with get_connection() as conn:
            cursor = conn.cursor()
            # 检查是否有 priority 列
            cursor.execute("PRAGMA table_info(channels)")
            columns = [r[1] for r in cursor.fetchall()]
            has_priority = 'priority' in columns

            if not has_priority:
                # 如果没有 priority 列，添加它
                cursor.execute("ALTER TABLE channels ADD COLUMN priority INTEGER DEFAULT 0")

            cursor.execute(
                "UPDATE channels SET priority = ?, updated_at = ? WHERE id = ?",
                (priority, now, channel_id),
            )

    def touch_channel(self, channel_id: str) -> None:
        """更新 Channel 的 updated_at（不改变其他字段）"""
        now = time.time()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE channels SET updated_at = ? WHERE id = ?",
                (now, channel_id),
            )

    def delete_channel(self, channel_id: str) -> bool:
        """删除 Channel（级联删除消息）"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM channels WHERE id = ?",
                (channel_id,),
            )
            return cursor.rowcount > 0

    # ── Message 操作 ───────────────────────────────────────

    def add_message(
        self,
        channel_id: str,
        role: str,
        content: str,
    ) -> Message:
        """添加一条消息到 Channel"""
        now = time.time()

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (channel_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (channel_id, role, content, now),
            )
            msg_id = cursor.lastrowid

        return Message(
            id=msg_id,
            channel_id=channel_id,
            role=role,
            content=content,
            created_at=now,
        )

    def get_messages(
        self,
        channel_id: str,
        limit: int = 50,
    ) -> list[Message]:
        """获取 Channel 的最近 N 条消息（倒序）"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM messages
                WHERE channel_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (channel_id, limit),
            )
            rows = cursor.fetchall()

        # 倒序返回（按时间正序）
        messages = [
            Message(
                id=row['id'],
                channel_id=row['channel_id'],
                role=row['role'],
                content=row['content'],
                created_at=row['created_at'],
            )
            for row in rows
        ]
        return list(reversed(messages))

    def get_message_count(self, channel_id: str) -> int:
        """获取 Channel 的消息总数"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE channel_id = ?",
                (channel_id,),
            )
            row = cursor.fetchone()
        return row['cnt'] if row else 0


# 全局单例
channel_db = ChannelDB()
