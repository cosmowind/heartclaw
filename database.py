"""
心跳 — SQLite 数据库层
负责表初始化与连接管理
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# 数据库文件路径
DB_PATH = Path(__file__).parent / "heart.db"


def get_db_path() -> Path:
    """返回数据库文件路径，可通过环境变量覆盖"""
    import os
    custom = os.environ.get("HEART_DB_PATH")
    if custom:
        return Path(custom)
    return DB_PATH


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    获取数据库连接的上下文管理器。
    自动处理提交和关闭。
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """
    初始化数据库表（幂等操作）。
    包含对已有数据库的字段迁移（type 列）。
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Channel 表（v2：新增 type 列，name 唯一约束）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL UNIQUE,
                type        TEXT NOT NULL DEFAULT 'generic',
                status      TEXT NOT NULL DEFAULT 'idle',
                summary     TEXT NOT NULL DEFAULT '',
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL
            )
        """)

        # 迁移旧数据：如果 type 列不存在（从 v1 升级），添加默认值
        try:
            cursor.execute("SELECT type FROM channels LIMIT 1")
        except sqlite3.OperationalError:
            # type 列不存在，添加它
            cursor.execute("ALTER TABLE channels ADD COLUMN type TEXT NOT NULL DEFAULT 'generic'")

        # Message 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  REAL NOT NULL,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            )
        """)

        # 索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_channel_id
            ON messages(channel_id, created_at DESC)
        """)

        conn.commit()

    print(f"✅ 数据库初始化完成: {get_db_path()}")


if __name__ == "__main__":
    init_db()
