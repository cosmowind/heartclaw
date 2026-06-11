"""
龙虾心跳 — 主程序入口
支持两种运行模式：
  1. demo 模式：演示心跳 + Channel 遍历（默认）
  2. api 模式：启动 FastAPI 服务
"""
import argparse
import asyncio
import logging
import random
import signal
import sys

from heartbeat import Heartbeat, Lobster
from channel_processor import ChannelProcessor
from database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# 全局停止标志
shutdown = False


def signal_handler(sig, frame):
    global shutdown
    print("\n收到终止信号...")
    shutdown = True


async def demo_task_adder(lobster: Lobster):
    """模拟随机向队列添加任务"""
    types = ["analysis", "coding", "review", "testing"]
    data_pool = [
        "分析今天的日志",
        "写一个冒泡排序",
        "审查代码质量",
        "运行性能测试",
        "整理项目文档",
        "优化查询速度",
    ]

    for i in range(8):
        wait = random.uniform(5, 15)
        await asyncio.sleep(wait)

        if shutdown:
            break

        task_type = random.choice(types)
        data = random.choice(data_pool)
        await lobster.add_task(task_type, data)


async def run_demo():
    """演示模式：心跳 + ChannelProcessor"""
    global shutdown

    print("=" * 50)
    print("  🦞 我本是龙虾 — 心跳演示")
    print("  每 10 秒醒来一次，遍历所有 Channel")
    print("=" * 50)
    print()

    # 初始化数据库
    init_db()

    # 预先创建 brainstorm + chat 两个测试 Channel（同名则删除重建）
    from channel_db import channel_db

    # 删除旧的同名 Channel
    for name in ("brainstorm", "chat"):
        existing = [ch for ch in channel_db.list_channels() if ch.name == name]
        for ch in existing:
            channel_db.delete_channel(ch.id)
            print(f"  🗑️ 删除旧 Channel: {name}")

    # brainstorm channel
    ch_brainstorm = channel_db.create_channel("brainstorm", "brainstorm")
    channel_db.add_message(ch_brainstorm.id, "user", "概念：心跳项目 | 一个每10秒苏醒的后端服务 | 8")
    channel_db.add_message(ch_brainstorm.id, "user", "概念：Channel | 对话上下文+内容存储目录 | 7")
    channel_db.add_message(ch_brainstorm.id, "user", "概念：Summarize | 将对话历史压缩成一句话 | 6")

    # chat channel
    ch_chat = channel_db.create_channel("chat", "chat")
    channel_db.add_message(ch_chat.id, "user", "你好")

    print(f"✅ 测试 Channel 已创建：")
    print(f"   - brainstorm (type=brainstorm): {ch_brainstorm.id}")
    print(f"   - chat (type=chat): {ch_chat.id}")
    print()

    # 创建 ChannelProcessor
    processor = ChannelProcessor()

    # 创建龙虾（带 ChannelProcessor）
    lobster = Lobster(
        heartbeat_interval=10.0,
        channel_processor=processor.process_all,
    )
    lobster.start()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 运行 60 秒
    try:
        for i in range(6):
            if shutdown:
                break
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass

    shutdown = True
    lobster.stop()

    print("\n🦞 程序结束")
    print(f"   总心跳次数: {lobster.heartbeat.count}")


def run_api():
    """API 模式：启动 FastAPI 服务"""
    import uvicorn

    print("=" * 50)
    print("  🦞 心跳 API 服务")
    print("  访问 http://localhost:18765/docs 查看 API 文档")
    print("=" * 50)
    print()

    # 初始化数据库
    init_db()

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=18765,
        log_level="info",
        reload=False,
    )


def main():
    parser = argparse.ArgumentParser(description="龙虾心跳")
    parser.add_argument(
        "mode",
        choices=["demo", "api"],
        nargs="?",
        default="demo",
        help="运行模式：demo（默认）或 api",
    )
    args = parser.parse_args()

    if args.mode == "api":
        run_api()
    else:
        asyncio.run(run_demo())


if __name__ == "__main__":
    main()
