"""
龙虾心跳 — 请求队列模块
模拟一个简单的 FIFO 任务队列
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Request:
    """请求任务"""
    id: int
    type: str
    data: str
    added_at: float = field(default_factory=time.time)


class RequestQueue:
    """请求队列管理器"""

    def __init__(self):
        self._queue: asyncio.Queue[Request] = asyncio.Queue()
        self._counter = 0

    async def add_request(self, req_type: str, data: str) -> Request:
        """添加一个新请求到队列"""
        self._counter += 1
        request = Request(
            id=self._counter,
            type=req_type,
            data=data,
        )
        await self._queue.put(request)
        return request

    async def get_request(self) -> Request:
        """从队列获取一个请求（阻塞等待）"""
        return await self._queue.get()

    def get_nowait(self) -> Optional[Request]:
        """尝试立即获取一个请求，不阻塞"""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    @property
    def size(self) -> int:
        """返回队列当前长度"""
        return self._queue.qsize()

    @property
    def queue(self) -> asyncio.Queue:
        """返回底层队列对象"""
        return self._queue
