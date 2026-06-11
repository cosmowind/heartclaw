"""
心跳 — Chat Handler（低优先级聊天）
收到处理信号后打印"你好"，标记 Channel 为 done。
"""
import logging
from dataclasses import dataclass
from channel_db import channel_db, Channel

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    handled: bool
    action: str
    channel_id: str
    detail: str = ""


def handle(channel: Channel) -> ProcessingResult:
    """
    Chat Channel 的处理逻辑：
    - 读取最新一条 user 消息
    - 如果是"你好"类问候，回复"你好"
    - 标记 Channel 为 done

    Args:
        channel: 待处理的 Channel

    Returns:
        ProcessingResult
    """
    messages = channel_db.get_messages(channel.id, limit=5)
    if not messages:
        logger.info(f"[{channel.name}] Chat: 无消息，跳过")
        return ProcessingResult(
            handled=False,
            action="skipped",
            channel_id=channel.id,
            detail="无消息",
        )

    # 取最新一条 user 消息
    last_user_msg = None
    for m in reversed(messages):
        if m.role == "user":
            last_user_msg = m.content
            break

    if last_user_msg is None:
        logger.info(f"[{channel.name}] Chat: 无 user 消息，跳过")
        return ProcessingResult(
            handled=False,
            action="skipped",
            channel_id=channel.id,
            detail="无 user 消息",
        )

    logger.info(f"[{channel.name}] Chat: 收到消息 '{last_user_msg}'，回复'你好'")

    # 写入回复
    channel_db.add_message(channel.id, "assistant", "你好")
    channel_db.touch_channel(channel.id)
    channel_db.update_channel_status(channel.id, "done")

    return ProcessingResult(
        handled=True,
        action="greeted",
        channel_id=channel.id,
        detail="已回复：你好",
    )
