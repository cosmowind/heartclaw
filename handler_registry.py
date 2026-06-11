"""
心跳 — Handler 注册中心
支持：
1. 基于 Channel type 的 Handler 匹配
2. 基于 Summary 内容的 Handler 匹配
3. Decider 机制（判断是否需要继续处理）
"""
import logging
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional
import re

logger = logging.getLogger(__name__)


@dataclass
class HandlerMatch:
    """Handler 匹配结果"""
    handler_name: str
    priority: int = 0  # 优先级，越高越优先
    confidence: float = 1.0  # 匹配置信度 0-1


@dataclass
class HandlerSpec:
    """Handler 规格"""
    name: str
    description: str
    handler_fn: Callable  # 处理函数
    type_match: Optional[str] = None  # 匹配的 Channel type
    keyword_patterns: list[str] = field(default_factory=list)  # 匹配 Summary 的关键词模式
    priority: int = 0  # 默认优先级
    decider_fn: Optional[Callable] = None  # Decider 函数，判断是否需要继续处理


class HandlerRegistry:
    """Handler 注册中心"""

    def __init__(self):
        self._handlers: dict[str, HandlerSpec] = {}
        self._type_handlers: dict[str, str] = {}  # type -> handler_name
        self._keyword_handlers: list[tuple[str, str, int]] = []  # (pattern, handler_name, priority)

    def register(self, spec: HandlerSpec):
        """注册 Handler"""
        self._handlers[spec.name] = spec

        # 注册 type 匹配
        if spec.type_match:
            self._type_handlers[spec.type_match] = spec.name
            logger.info(f"📌 注册 type Handler: {spec.type_match} -> {spec.name}")

        # 注册关键词匹配
        for pattern in spec.keyword_patterns:
            self._keyword_handlers.append((pattern, spec.name, spec.priority))
            logger.info(f"🔑 注册 keyword Handler: '{pattern}' -> {spec.name}")

    def find_handler(self, channel_type: str, summary: str) -> Optional[HandlerSpec]:
        """
        根据 Channel type 和 Summary 内容找到最匹配的 Handler

        匹配优先级：
        1. type 精确匹配（最高优先级）
        2. 关键词匹配（按 priority 排序）
        3. 默认 Handler（如果有的话）
        """
        # 1. type 精确匹配
        if channel_type in self._type_handlers:
            handler_name = self._type_handlers[channel_type]
            return self._handlers[handler_name]

        # 2. 关键词匹配
        if summary:
            summary_lower = summary.lower()
            matches = []
            for pattern, handler_name, priority in self._keyword_handlers:
                if re.search(pattern, summary_lower, re.IGNORECASE):
                    matches.append((priority, handler_name))

            if matches:
                # 选择优先级最高的
                matches.sort(key=lambda x: x[0], reverse=True)
                return self._handlers[matches[0][1]]

        # 3. 默认 Handler（name="default"）
        if "default" in self._handlers:
            return self._handlers["default"]

        return None

    def get_all_handlers(self) -> dict[str, HandlerSpec]:
        """获取所有注册的 Handler"""
        return self._handlers.copy()

    def should_continue(self, handler_name: str, result: dict) -> bool:
        """
        Decider 机制：判断是否需要继续处理

        Args:
            handler_name: Handler 名称
            result: Handler 处理结果

        Returns:
            True 表示需要继续处理，False 表示处理完成
        """
        spec = self._handlers.get(handler_name)
        if not spec or not spec.decider_fn:
            # 没有 Decider，默认处理完成
            return False

        try:
            return spec.decider_fn(result)
        except Exception as e:
            logger.error(f"Decider 执行失败: {e}")
            return False


# 全局单例
_registry: Optional[HandlerRegistry] = None


def get_registry() -> HandlerRegistry:
    """获取全局 Handler 注册中心"""
    global _registry
    if _registry is None:
        _registry = HandlerRegistry()
        _register_default_handlers()
    return _registry


def _register_default_handlers():
    """注册默认的 Handlers"""
    from brainstorm_handler import handle as brainstorm_handle
    from chat_handler import handle as chat_handle
    from diary_handler import handle as diary_handle

    # Brainstorm Handler
    def brainstorm_handler_fn(channel, summary):
        result = brainstorm_handle(channel)
        return {
            "handled": result.handled,
            "action": result.action,
            "channel_id": result.channel_id,
            "detail": result.detail,
            "concepts_added": result.concepts_added,
        }

    _registry.register(HandlerSpec(
        name="brainstorm",
        description="头脑风暴概念树管理",
        handler_fn=brainstorm_handler_fn,
        type_match="brainstorm",
        keyword_patterns=[r"概念", r"知识库", r"头脑风暴"],
        priority=10,
    ))

    # Chat Handler
    def chat_handler_fn(channel, summary):
        result = chat_handle(channel)
        return {
            "handled": result.handled,
            "action": result.action,
            "channel_id": result.channel_id,
            "detail": result.detail,
        }

    _registry.register(HandlerSpec(
        name="chat",
        description="简单聊天处理",
        handler_fn=chat_handler_fn,
        type_match="chat",
        keyword_patterns=[r"聊天", r"闲聊", r"你好"],
        priority=5,
    ))

    # Diary Handler（数字生命日记）
    def diary_handler_fn(channel, summary):
        result = diary_handle(channel)
        return {
            "handled": result.handled,
            "action": result.action,
            "channel_id": result.channel_id,
            "detail": result.detail,
        }

    _registry.register(HandlerSpec(
        name="diary",
        description="数字生命日记生成",
        handler_fn=diary_handler_fn,
        type_match="diary",
        keyword_patterns=[r"日记", r"日志", r"记录", r"diary"],
        priority=8,
    ))

    # Default Handler（兜底）
    def default_handler_fn(channel, summary):
        logger.info(f"[{channel.name}] 默认处理: {summary}")
        return {"handled": True, "channel_id": channel.id, "action": "logged"}

    _registry.register(HandlerSpec(
        name="default",
        description="默认处理（仅记录日志）",
        handler_fn=default_handler_fn,
        priority=-100,
    ))
