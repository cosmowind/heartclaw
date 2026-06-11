"""
心跳 — 内容目录管理
每个 Channel type 对应一个本地目录，统一管理。
"""
import os
from pathlib import Path
from typing import Optional

# Heart 项目根目录
HEART_ROOT = Path(__file__).parent

# 内容根目录
DATA_ROOT = HEART_ROOT / "data"

# 各 Channel type 的目录配置
CHANNEL_DIRS: dict[str, str] = {
    "brainstorm": "brainstorm",
    "chat": "chat",
    "generic": "generic",
}


def get_channel_dir(channel_type: str) -> Path:
    """
    根据 channel_type 返回对应的内容目录。
    如果不存在则创建。
    """
    subdir = CHANNEL_DIRS.get(channel_type, "generic")
    path = DATA_ROOT / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_channel_dir(channel_type: str) -> Path:
    """确保目录存在，返回路径（与 get_channel_dir 相同但语义强调创建）"""
    return get_channel_dir(channel_type)


def list_channel_files(channel_type: str, pattern: str = "*") -> list[Path]:
    """列出某 Channel 目录下符合条件的文件"""
    d = get_channel_dir(channel_type)
    return sorted(d.glob(pattern))
