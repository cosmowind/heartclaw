"""
心跳 — FastAPI 服务
承载所有 HTTP 端点
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from channel_db import channel_db, Channel
from database import init_db
from channel_processor import ChannelProcessor

logger = logging.getLogger(__name__)

# ── 响应模型 ────────────────────────────────────────────


class ChannelResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    summary: str
    priority: int = 0
    created_at: float
    updated_at: float


class MessageResponse(BaseModel):
    id: int
    channel_id: str
    role: str
    content: str
    created_at: float


class CreateChannelRequest(BaseModel):
    name: str
    type: str = "generic"
    priority: int = 0


class UpdatePriorityRequest(BaseModel):
    priority: int


class AddMessageRequest(BaseModel):
    role: str
    content: str


class WakeResponse(BaseModel):
    triggered: bool
    channels_processed: int
    message: str


# ── 全局状态 ────────────────────────────────────────────

_processor: ChannelProcessor | None = None


def get_processor() -> ChannelProcessor:
    global _processor
    if _processor is None:
        _processor = ChannelProcessor()
    return _processor


# ── 生命周期 ───────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("✅ API 服务已启动")
    yield
    logger.info("🔻 API 服务关闭")


# ── 应用实例 ───────────────────────────────────────────

app = FastAPI(
    title="Heart API",
    description="心跳系统的 HTTP 接口",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Channel 路由 ────────────────────────────────────────


@app.get("/channels", response_model=list[ChannelResponse])
async def list_channels() -> list[ChannelResponse]:
    channels = await asyncio.to_thread(channel_db.list_channels)
    return [
        ChannelResponse(
            id=ch.id,
            name=ch.name,
            type=ch.type,
            status=ch.status,
            summary=ch.summary,
            priority=ch.priority,
            created_at=ch.created_at,
            updated_at=ch.updated_at,
        )
        for ch in channels
    ]


@app.post("/channels", response_model=ChannelResponse)
async def create_channel(req: CreateChannelRequest) -> ChannelResponse:
    channel = await asyncio.to_thread(channel_db.create_channel, req.name, req.type, req.priority)
    logger.info(f"📝 创建 Channel: {channel.name} ({channel.type}, priority={channel.priority})")
    return ChannelResponse(
        id=channel.id,
        name=channel.name,
        type=channel.type,
        status=channel.status,
        summary=channel.summary,
        priority=channel.priority,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@app.get("/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: str) -> ChannelResponse:
    channel = await asyncio.to_thread(channel_db.get_channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel 不存在")
    return ChannelResponse(
        id=channel.id,
        name=channel.name,
        type=channel.type,
        status=channel.status,
        summary=channel.summary,
        priority=channel.priority,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@app.put("/channels/{channel_id}/priority")
async def update_priority(channel_id: str, req: UpdatePriorityRequest) -> dict:
    channel = await asyncio.to_thread(channel_db.get_channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel 不存在")

    await asyncio.to_thread(channel_db.update_channel_priority, channel_id, req.priority)
    logger.info(f"📌 更新 Channel {channel.name} 优先级: {req.priority}")
    return {"ok": True, "channel_id": channel_id, "priority": req.priority}


@app.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str) -> dict:
    deleted = await asyncio.to_thread(channel_db.delete_channel, channel_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Channel 不存在")
    return {"ok": True, "deleted": channel_id}


# ── Message 路由 ────────────────────────────────────────


@app.get("/channels/{channel_id}/messages", response_model=list[MessageResponse])
async def get_messages(channel_id: str, limit: int = 50) -> list[MessageResponse]:
    channel = await asyncio.to_thread(channel_db.get_channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel 不存在")
    messages = await asyncio.to_thread(channel_db.get_messages, channel_id, limit)
    return [
        MessageResponse(
            id=m.id,
            channel_id=m.channel_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]


@app.post("/channels/{channel_id}/messages", response_model=MessageResponse)
async def add_message(channel_id: str, req: AddMessageRequest) -> MessageResponse:
    channel = await asyncio.to_thread(channel_db.get_channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel 不存在")

    message = await asyncio.to_thread(
        channel_db.add_message,
        channel_id,
        req.role,
        req.content,
    )
    await asyncio.to_thread(channel_db.touch_channel, channel_id)

    return MessageResponse(
        id=message.id,
        channel_id=message.channel_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


# ── Summarize 路由 ─────────────────────────────────────


@app.get("/channels/{channel_id}/summarize")
async def summarize_channel(channel_id: str) -> dict:
    from summarize import summarize_channel as do_summarize

    channel = await asyncio.to_thread(channel_db.get_channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel 不存在")

    messages = await asyncio.to_thread(channel_db.get_messages, channel_id, 20)
    msg_dicts = [{"role": m.role, "content": m.content} for m in messages]

    summary = await do_summarize(msg_dicts)
    await asyncio.to_thread(channel_db.update_channel_summary, channel_id, summary)

    return {"channel_id": channel_id, "summary": summary}


# ── Wake 路由 ──────────────────────────────────────────


@app.post("/wake", response_model=WakeResponse)
async def wake() -> WakeResponse:
    processor = get_processor()

    try:
        results = await processor.process_all()
        channels_processed = len(results)
        return WakeResponse(
            triggered=True,
            channels_processed=channels_processed,
            message=f"处理了 {channels_processed} 个 Channel",
        )
    except Exception as e:
        logger.error(f"Wake 处理失败: {e}")
        return WakeResponse(
            triggered=False,
            channels_processed=0,
            message=f"处理失败: {e}",
        )


# ── 健康检查 ────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:
    channels = await asyncio.to_thread(channel_db.list_channels)
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "channels_count": len(channels),
    }
