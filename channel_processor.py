"""
心跳 — Channel 处理器
心跳苏醒时遍历所有 Channel，决定处理顺序，按 type 和 Summary 内容分发到对应 handler，按序处理
支持 Handler 注册中心和 Decider 机制
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Awaitable

from channel_db import channel_db, Channel
from summarize import summarize_channel
from handler_registry import get_registry

logger = logging.getLogger(__name__)

# 处理结果类型
ProcessResult = dict


# 处理函数类型：输入 Channel 和它的 Summary，返回处理结果
ChannelHandler = Callable[[Channel, str], Awaitable[ProcessResult]]


# ── Type → Handler 注册表（向后兼容）────────────────────────

def _build_dispatch() -> dict[str, ChannelHandler]:
    """延迟导入，避免循环依赖"""
    from brainstorm_handler import handle as brainstorm_handle
    from chat_handler import handle as chat_handle

    # 同步 handler 需要包装为 async（ChannelProcessor 内部是 async）
    async def async_brainstorm(ch: Channel, summary: str) -> ProcessResult:
        import threading
        result_holder = [None]
        def sync_call():
            result_holder[0] = brainstorm_handle(ch)
        t = threading.Thread(target=sync_call)
        t.start()
        t.join()
        r = result_holder[0]
        return {
            "handled": r.handled,
            "action": r.action,
            "channel_id": r.channel_id,
            "detail": r.detail,
            "concepts_added": r.concepts_added,
        }

    async def async_chat(ch: Channel, summary: str) -> ProcessResult:
        import threading
        result_holder = [None]
        def sync_call():
            result_holder[0] = chat_handle(ch)
        t = threading.Thread(target=sync_call)
        t.start()
        t.join()
        r = result_holder[0]
        return {
            "handled": r.handled,
            "action": r.action,
            "channel_id": r.channel_id,
            "detail": r.detail,
        }

    return {
        "brainstorm": async_brainstorm,
        "chat": async_chat,
    }


@dataclass
class ProcessOrder:
    """处理顺序项"""
    channel: Channel
    summary: str
    order_key: tuple  # 用于排序


class ChannelProcessor:
    """
    Channel 处理器。

    心跳苏醒时：
    1. 获取所有 Channel
    2. 对每个 Channel 调用 Summarize
    3. 按策略排序（默认：auto）
    4. 根据 Channel.type 和 Summary 内容分发到对应 handler
    5. 依次处理有需求的 Channel（Summary 非空）
    6. 支持 Decider 机制（判断是否需要继续处理）
    """

    def __init__(self, sort_strategy: str = "auto"):
        """
        初始化 ChannelProcessor

        Args:
            sort_strategy: 排序策略，可选值：
                - "fifo": 按 updated_at 升序
                - "priority": 按 priority 降序
                - "urgent": 非空 summary 优先，再按 priority 降序
                - "auto"（默认）: 综合排序
        """
        self._dispatch: dict[str, ChannelHandler] = _build_dispatch()
        self._registry = get_registry()
        self._sort_strategy = sort_strategy

    async def _get_handler(self, channel: Channel, summary: str) -> ChannelHandler:
        """
        根据 Channel.type 和 Summary 内容找到对应 handler

        优先使用 HandlerRegistry 进行匹配，如果找不到则回退到 _dispatch
        """
        # 1. 尝试使用 HandlerRegistry
        spec = self._registry.find_handler(channel.type, summary)
        if spec:
            # 包装为 async
            async def async_handler(ch: Channel, summary: str) -> ProcessResult:
                import threading
                result_holder = [None]
                def sync_call():
                    result_holder[0] = spec.handler_fn(ch, summary)
                t = threading.Thread(target=sync_call)
                t.start()
                t.join()
                return result_holder[0]
            return async_handler

        # 2. 回退到 _dispatch
        if channel.type in self._dispatch:
            return self._dispatch[channel.type]

        # 3. 默认处理
        return self._default_handler

    async def _default_handler(self, channel: Channel, summary: str) -> ProcessResult:
        """默认处理函数（仅记录日志）"""
        logger.info(f"[{channel.name}] 默认处理（type={channel.type}）: {summary}")
        return {"handled": True, "channel_id": channel.id, "action": "logged"}

    async def _summarize_single(self, channel: Channel) -> tuple[Channel, str]:
        """
        对单个 Channel 生成总结。
        返回 (channel, summary)。
        """
        messages = channel_db.get_messages(channel.id, limit=20)
        msg_dicts = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        try:
            summary = await summarize_channel(msg_dicts)
        except Exception as e:
            logger.error(f"Channel {channel.id} Summarize 失败: {e}")
            summary = f"[Summarize 失败] {e}"

        # 更新数据库中的 summary
        if summary != channel.summary:
            channel_db.update_channel_summary(channel.id, summary)

        return channel, summary

    def _decide_order(self, items: list[tuple[Channel, str]], strategy: str = "auto") -> list[ProcessOrder]:
        """
        决定处理顺序。

        排序策略：
        - "fifo": 按 updated_at 升序（早的先处理）
        - "priority": 按 priority 降序（高优先级先处理）
        - "urgent": 非空 summary 优先，再按 priority 降序
        - "auto"（默认）: 综合排序（priority + summary + updated_at）

        Returns:
            ProcessOrder 列表（已排序）
        """
        result = []
        for channel, summary in items:
            # 关键程度：非空 summary 优先
            has_summary = 1 if (summary and not summary.startswith("[")) else 0

            if strategy == "fifo":
                order_key = (channel.updated_at,)
            elif strategy == "priority":
                order_key = (-channel.priority,)  # 负号实现降序
            elif strategy == "urgent":
                order_key = (-has_summary, -channel.priority)
            else:  # auto
                order_key = (-has_summary, -channel.priority, channel.updated_at)

            result.append(ProcessOrder(
                channel=channel,
                summary=summary,
                order_key=order_key,
            ))

        # 排序
        result.sort(key=lambda x: x.order_key)
        return result

    async def process_all(self) -> list[ProcessResult]:
        """
        遍历所有 Channel，生成总结，决定顺序，依次处理。

        Returns:
            每个 Channel 的处理结果列表
        """
        logger.info("🔔 ChannelProcessor: 开始处理所有 Channel")

        # 1. 获取所有 Channel
        channels = channel_db.list_channels()
        if not channels:
            logger.info("  └─ 没有 Channel，无需处理")
            return []

        logger.info(f"  └─ 共 {len(channels)} 个 Channel，开始生成 Summary...")

        # 2. 对每个 Channel 并发生成 Summary
        summarize_tasks = [self._summarize_single(ch) for ch in channels]
        summarized = await asyncio.gather(*summarize_tasks, return_exceptions=True)

        # 过滤失败
        valid_items = []
        for item in summarized:
            if isinstance(item, Exception):
                logger.error(f"  └─ Summarize 异常: {item}")
            else:
                valid_items.append(item)

        # 3. 决定顺序
        ordered = self._decide_order(valid_items, self._sort_strategy)

        logger.info(f"  └─ 处理顺序已确定，共 {len(ordered)} 项")
        for i, po in enumerate(ordered):
            flag = "📌" if po.summary and not po.summary.startswith("[") else "・"
            logger.info(f"  └─ {i+1}. {flag} [{po.channel.name}] {po.summary or '(空)' }")

        # 4. 按序处理有需求的 Channel
        # 跳过策略：
        # - 需要 LLM summary 的 generic 类型：空 summary 或失败占位符 → 跳过
        # - 有本地 handler 的类型（brainstorm/chat）：不依赖 LLM summary，直接处理
        results = []
        for po in ordered:
            summary_failed = (
                not po.summary
                or po.summary.startswith("[Summarize 失败]")
            )
            # generic 类型依赖 LLM summary，没有就跳过
            if po.channel.type == "generic" and summary_failed:
                logger.info(f"  └─ [{po.channel.name}] 跳过（Summary 为空或失败，且 type=generic）")
                continue
            # brainstorm/chat 有本地 handler，无需 LLM summary
            if po.channel.type in ("brainstorm", "chat") and summary_failed:
                logger.info(f"  └─ [{po.channel.name}] type={po.channel.type}，即使无 LLM Summary 也继续处理")

            try:
                logger.info(f"  └─ ▶ 处理 [{po.channel.name}] (type={po.channel.type})...")
                handler = await self._get_handler(po.channel, po.summary)
                result = await handler(po.channel, po.summary)
                results.append(result)
                logger.info(f"  └─ ✓ [{po.channel.name}] 处理完成")

                # Decider 机制：判断是否需要继续处理
                spec = self._registry.find_handler(po.channel.type, po.summary)
                if spec and self._registry.should_continue(spec.name, result):
                    logger.info(f"  └─ 🔄 [{po.channel.name}] Decider: 需要继续处理")
                    # TODO: 实现继续处理逻辑（如重新加入队列）

            except Exception as e:
                logger.error(f"  └─ ✗ [{po.channel.name}] 处理异常: {e}")
                results.append({
                    "handled": False,
                    "channel_id": po.channel.id,
                    "error": str(e),
                })

        logger.info(f"✅ ChannelProcessor: 处理完成，共处理 {len(results)} 个 Channel")
        return results
