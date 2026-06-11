"""
龙虾心跳 — 心跳模块
每 10 秒醒来一次，查看请求队列 + 处理所有 Channel
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional, Callable, Awaitable

from request_queue import RequestQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class Heartbeat:
    """
    龙虾心跳控制器

    核心行为：
    - 每隔 interval 秒执行一次心跳
    - 心跳时检查请求队列
    - 处理队列中的所有任务
    - （可选）处理所有 Channel
    - 支持动态心跳频率（F5）
    """

    def __init__(
        self,
        interval: float = 10.0,
        min_interval: float = 5.0,
        max_interval: float = 60.0,
        channel_processor: Optional[Callable[[], Awaitable[list]]] = None,
    ):
        self.base_interval = interval  # 基础心跳间隔
        self.interval = interval  # 当前心跳间隔
        self.min_interval = min_interval  # 最小心跳间隔
        self.max_interval = max_interval  # 最大心跳间隔
        self.count = 0
        self.running = False
        self._idle_count = 0  # 连续空闲次数
        self._busy_count = 0  # 连续忙碌次数
        # Channel 处理器（可选）
        self._channel_processor = channel_processor

    def set_channel_processor(self, processor: Callable[[], Awaitable[list]]) -> None:
        """设置 Channel 处理器"""
        self._channel_processor = processor

    def _adjust_interval(self, queue_size: int, channels_processed: int) -> None:
        """
        动态调整心跳间隔（F5）

        策略：
        - 队列有任务 → 加快心跳（缩短间隔）
        - 连续空闲 → 降低心跳频率（延长间隔）
        """
        is_busy = queue_size > 0

        if is_busy:
            # 忙碌时：加快心跳
            self._busy_count += 1
            self._idle_count = 0

            # 连续忙碌 3 次以上，进一步加快
            if self._busy_count >= 3:
                self.interval = max(self.min_interval, self.base_interval * 0.5)
            else:
                self.interval = max(self.min_interval, self.base_interval * 0.8)

            logger.debug(f"💓 心跳加快: {self.interval:.1f}秒 (连续忙碌 {self._busy_count} 次)")
        else:
            # 空闲时：降低心跳频率
            self._idle_count += 1
            self._busy_count = 0

            # 连续空闲 3 次以上，开始降频
            if self._idle_count >= 3:
                # 每多空闲 2 次，间隔增加 10 秒，最多到 max_interval
                extra = (self._idle_count - 2) * 10
                self.interval = min(self.max_interval, self.base_interval + extra)

                logger.debug(f"💤 心跳降频: {self.interval:.1f}秒 (连续空闲 {self._idle_count} 次)")
            else:
                self.interval = self.base_interval

    async def beat(self, request_queue: RequestQueue) -> None:
        """执行一次心跳"""
        self.count += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        queue_size = request_queue.size

        logger.info(
            f"♥ [{self.count}] 心跳 @ {now} | 队列任务: {queue_size} | 间隔: {self.interval:.1f}秒"
        )

        # ── 处理队列（原有逻辑）───────────────────────
        processed = 0
        while True:
            req = request_queue.get_nowait()
            if req is None:
                break

            logger.info(
                f"   └─ 处理 #{req.id} [{req.type}]: {req.data}"
            )
            # 模拟任务处理耗时
            await asyncio.sleep(0.3)
            processed += 1

        if processed > 0:
            logger.info(f"   └─ 本次处理 {processed} 个队列任务")
        else:
            logger.info(f"   └─ 队列空闲")

        # ── 处理 Channel（新增）───────────────────────
        channels_processed = 0
        if self._channel_processor is not None:
            try:
                results = await self._channel_processor()
                channels_processed = len(results)
                logger.info(f"   └─ Channel 处理完成: {channels_processed} 个 Channel")
            except Exception as e:
                logger.error(f"   └─ Channel 处理异常: {e}")
        else:
            logger.info(f"   └─ 无 Channel 处理器，跳过")

        # ── 动态调整心跳间隔 ────────────────────────
        self._adjust_interval(queue_size, channels_processed)

    async def _run(self, request_queue: RequestQueue) -> None:
        """心跳循环"""
        self.running = True
        logger.info(f"🦞 龙虾启动，心跳间隔: {self.base_interval}秒 (动态范围: {self.min_interval}-{self.max_interval}秒)")

        while self.running:
            await self.beat(request_queue)
            await asyncio.sleep(self.interval)

    def start(self, request_queue: RequestQueue) -> asyncio.Task:
        """启动心跳循环，返回 Task"""
        self.running = True
        task = asyncio.create_task(self._run(request_queue))
        return task

    def stop(self) -> None:
        """停止心跳"""
        self.running = False
        logger.info(f"🦞 龙虾休眠，共执行 {self.count} 次心跳")


class Lobster:
    """
    龙虾本体 — 心跳 + 队列的组合
    """

    def __init__(
        self,
        heartbeat_interval: float = 10.0,
        min_interval: float = 5.0,
        max_interval: float = 60.0,
        channel_processor: Optional[Callable[[], Awaitable[list]]] = None,
    ):
        self.request_queue = RequestQueue()
        self.heartbeat = Heartbeat(
            interval=heartbeat_interval,
            min_interval=min_interval,
            max_interval=max_interval,
            channel_processor=channel_processor,
        )
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """启动龙虾（后台运行）"""
        self._task = self.heartbeat.start(self.request_queue)

    async def add_task(self, task_type: str, data: str) -> None:
        """外部添加任务"""
        req = await self.request_queue.add_request(task_type, data)
        logger.info(f"📥 任务入队: #{req.id} [{task_type}] {data}")

    def stop(self) -> None:
        """停止龙虾"""
        self.heartbeat.stop()
        if self._task:
            self._task.cancel()

    @property
    def is_running(self) -> bool:
        return self.heartbeat.running
