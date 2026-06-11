"""
心跳 — Summarize API
将 Channel 的消息历史压缩成一句话总结
支持 MiniMax API（OpenAI 兼容格式）
"""
import asyncio
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 尝试从 .env 文件加载配置
def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

load_env()

# LLM 配置（从环境变量读取）
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("SUMMARIZE_MODEL", "MiniMax-Text-01")
SUMMARIZE_TIMEOUT = float(os.environ.get("SUMMARIZE_TIMEOUT", "30"))


async def summarize_channel(messages: list[dict]) -> str:
    """
    将消息列表压缩成一句话总结。

    Args:
        messages: [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮你的？"},
            ...
        ]

    Returns:
        一句话总结，如 "用户询问了订单状态，需要查询后回复"
        如果没有消息，返回空字符串 ""
    """
    if not messages:
        return ""

    # 构建 prompt
    message_lines = []
    for msg in messages:
        role_label = {"user": "用户", "assistant": "助手", "system": "系统"}.get(
            msg.get("role", "user"), "用户"
        )
        content = msg.get("content", "")
        # 截断过长消息
        if len(content) > 200:
            content = content[:200] + "..."
        message_lines.append(f"{role_label}：{content}")

    dialogue_text = "\n".join(message_lines)

    prompt = f"""你是一个对话总结助手。请将以下对话历史压缩成**一句话总结**。

要求：
- 不超过 50 个字
- 说明用户的需求或问题是什么
- 如果没有明确需求，说明当前状态

对话历史：
{dialogue_text}

一句话总结："""

    # 如果没有配置 API Key，返回占位总结（开发/测试用）
    if not OPENAI_API_KEY:
        logger.warning("SUMMARIZE_API_KEY 未配置，返回占位总结")
        return f"[无 API Key] 用户发了 {len(messages)} 条消息，最后一条: {messages[-1].get('content', '')[:30]}..."

    try:
        import aiohttp

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "你是一个简洁的对话总结助手。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 100,
            "temperature": 0.3,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=SUMMARIZE_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Summarize API 错误 {resp.status}: {text}")
                    return f"[API 错误 {resp.status}]"

                result = await resp.json()
                summary = result["choices"][0]["message"]["content"].strip()
                logger.info(f"Summarize 结果: {summary}")
                return summary

    except asyncio.TimeoutError:
        logger.error("Summarize API 调用超时")
        return "[Summarize 超时]"
    except Exception as e:
        logger.error(f"Summarize API 调用失败: {e}")
        return f"[Summarize 失败: {e}]"
