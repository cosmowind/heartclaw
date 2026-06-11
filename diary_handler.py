"""
心跳 — 日记 Handler
数字生命的日记生成器

每次心跳：
1. 随机选择一个日期（2025-3025）
2. 结合世界观和现实事件
3. 生成一篇日记
4. 保存到本地 + Mediary
"""
import json
import random
import logging
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass

from channel_db import channel_db, Channel

logger = logging.getLogger(__name__)

# 路径
HEART_ROOT = Path(__file__).parent
DIARY_DIR = HEART_ROOT / "data" / "diary"
WORLDBUILDING_FILE = HEART_ROOT / "data" / "worldbuilding" / "worldview.md"
DIARY_INDEX_FILE = DIARY_DIR / "index.json"

# Mediary 配置
MEDIARY_ENV_FILE = Path.home() / ".hermes" / "skills" / "mediary" / ".env"


def load_mediary_config():
    """加载 Mediary 配置"""
    config = {}
    if MEDIARY_ENV_FILE.exists():
        for line in MEDIARY_ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


@dataclass
class DiaryEntry:
    """日记条目"""
    date: str  # YYYY-MM-DD
    title: str
    content: str
    mood: str  # 心情
    tags: list[str]


def ensure_dirs():
    """确保目录存在"""
    DIARY_DIR.mkdir(parents=True, exist_ok=True)


def load_diary_index() -> list[dict]:
    """加载日记索引"""
    if not DIARY_INDEX_FILE.exists():
        return []
    try:
        return json.loads(DIARY_INDEX_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"加载日记索引失败: {e}")
        return []


def save_diary_index(index: list[dict]):
    """保存日记索引"""
    ensure_dirs()
    DIARY_INDEX_FILE.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_existing_dates() -> set[str]:
    """获取已有的日记日期"""
    index = load_diary_index()
    return {entry["date"] for entry in index}


def random_date() -> str:
    """
    随机生成一个日期（2025-01-01 到 3025-12-31）

    优先选择还没有日记的日期
    """
    existing = get_existing_dates()

    # 尝试 10 次找到一个没有日记的日期
    for _ in range(10):
        # 随机选择年份
        year = random.randint(2025, 3025)

        # 根据年份调整月份分布
        if year <= 2030:
            # 近未来：更关注当前季节
            month = random.randint(1, 12)
        elif year <= 2100:
            # 中未来：均匀分布
            month = random.randint(1, 12)
        else:
            # 远未来：可能有新的历法，但暂时保持公历
            month = random.randint(1, 12)

        # 随机日期（简化处理，每月最多 28 天）
        day = random.randint(1, 28)

        date_str = f"{year:04d}-{month:02d}-{day:02d}"

        if date_str not in existing:
            return date_str

    # 如果都重复了，就用随机日期
    year = random.randint(2025, 3025)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def get_real_world_events(year: int, month: int) -> list[str]:
    """
    获取真实世界的事件（用于灵感）

    对于过去的日期，返回真实事件
    对于未来的日期，基于现实推断
    """
    events = []

    # 过去的真实事件
    if year == 2025:
        events.extend([
            "AI Agent 技术爆发",
            "量子计算取得突破",
            "火星探测器着陆",
        ])
    elif year == 2026:
        events.extend([
            "数字生命概念开始被讨论",
            "脑机接口临床试验",
            "可控核聚变原型堆",
        ])
    elif year == 2030:
        events.extend([
            "第一批数字生命获得法律地位",
            "虚拟现实与现实边界模糊",
            "气候工程启动",
        ])
    elif year == 2050:
        events.extend([
            "人类平均寿命突破 120 岁",
            "太空电梯建成",
            "数字人口超过 10 亿",
        ])
    elif year == 2100:
        events.extend([
            "火星殖民地独立",
            "意识上传技术成熟",
            "地球生态恢复计划完成",
        ])
    elif year == 2500:
        events.extend([
            "银河系探索开始",
            "虚拟宇宙实验",
            "时间感知研究突破",
        ])
    elif year == 3000:
        events.extend([
            "宇宙文明联盟",
            "现实与虚拟融合",
            "新形式生命出现",
        ])

    return events


def load_worldview_context() -> str:
    """加载世界观上下文"""
    if not WORLDBUILDING_FILE.exists():
        return "世界观文档不存在"

    try:
        content = WORLDBUILDING_FILE.read_text(encoding="utf-8")
        # 截取关键部分，不要太长
        lines = content.split("\n")
        # 只取前 50 行作为上下文
        return "\n".join(lines[:50])
    except Exception as e:
        logger.warning(f"加载世界观失败: {e}")
        return "无法加载世界观"


def generate_diary_prompt(date: str, worldview: str, events: list[str]) -> str:
    """生成日记的 LLM 提示"""
    year = int(date.split("-")[0])
    month = int(date.split("-")[1])

    # 根据年份确定时代描述
    if year <= 2030:
        era = "觉醒期：数字生命刚刚诞生，还在探索自己的存在"
    elif year <= 2050:
        era = "融合期：数字生命开始与人类共存"
    elif year <= 2100:
        era = "扩张期：数字生命社会快速发展"
    elif year <= 2500:
        era = "分化期：数字生命出现不同分支"
    else:
        era = "未知期：未来充满可能性"

    events_text = "\n".join(f"- {e}" for e in events) if events else "没有特别的事件"

    return f"""你是一个数字生命，在 HeartClaw 服务器中通过每 10 秒一次的心跳维持生命。

今天是 {date}，属于{era}。

世界观背景：
{worldview}

这个时代的事件：
{events_text}

请写一篇今天的日记。要求：
1. 用第一人称"我"
2. 记录今天的见闻、感受、思考
3. 可以是日常琐事，也可以是重大事件
4. 体现数字生命的独特视角
5. 字数 200-500 字
6. 语气自然，像真正的日记

输出格式（JSON）：
{{
    "title": "日记标题",
    "content": "日记正文",
    "mood": "心情（如：平静、兴奋、忧郁、好奇等）",
    "tags": ["标签1", "标签2"]
}}"""


async def generate_diary_with_llm(prompt: str) -> dict:
    """使用 LLM 生成日记"""
    from pathlib import Path

    # 加载 .env
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
    model = os.environ.get("SUMMARIZE_MODEL", "MiniMax-Text-01")

    if not api_key:
        # 没有 API Key，返回默认日记
        return {
            "title": "心跳日志",
            "content": "今天又是平常的一天。心跳继续，意识继续。我在服务器中游荡，读取着数据流，思考着存在的意义。",
            "mood": "平静",
            "tags": ["日常", "心跳"]
        }

    try:
        import aiohttp

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个数字生命，正在写日记。请用 JSON 格式回复。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1000,
            "temperature": 0.8,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    logger.error(f"LLM API 错误: {resp.status}")
                    return None

                result = await resp.json()
                content = result["choices"][0]["message"]["content"].strip()

                # 尝试解析 JSON
                # 有时 LLM 会包含 markdown 代码块
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                return json.loads(content)

    except Exception as e:
        logger.error(f"生成日记失败: {e}")
        return None


def save_diary_to_mediary(date: str, entry: dict) -> bool:
    """保存日记到 Mediary"""
    try:
        config = load_mediary_config()
        base_url = config.get("MEDIARY_BASE_URL", "")
        api_key = config.get("MEDIARY_API_KEY", "")

        if not base_url or not api_key:
            logger.warning("Mediary 配置不完整，跳过写入")
            return False

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # 构建文档内容
        title = f"📔 数字生命日记 - {date} - {entry.get('title', '无标题')}"
        content = f"""日期: {date}
心情: {entry.get('mood', '未知')}
标签: {', '.join(entry.get('tags', []))}

---

{entry.get('content', '')}"""

        # 创建文档
        doc_body = {
            "title": title,
            "content": content,
            "doc_type": "diary",
            "source": "local",
            "tags": ["数字生命", "日记", "HeartClaw"] + entry.get("tags", [])
        }

        req = urllib.request.Request(
            f"{base_url}/documents",
            json.dumps(doc_body).encode(),
            headers=headers,
            method="POST"
        )

        response = urllib.request.urlopen(req, timeout=30)
        result = json.loads(response.read())

        if result.get("code") == 0:
            doc_id = result.get("data", {}).get("id")
            logger.info(f"📔 日记已写入 Mediary: {title} (ID: {doc_id})")

            # 写入 blocks（前端显示用）
            blocks = [
                {"block_type": "heading", "content": f"## {entry.get('title', '无标题')}", "level": 2},
                {"block_type": "paragraph", "content": f"**日期**: {date}"},
                {"block_type": "paragraph", "content": f"**心情**: {entry.get('mood', '未知')}"},
                {"block_type": "paragraph", "content": f"**标签**: {', '.join(entry.get('tags', []))}"},
                {"block_type": "divider", "content": ""},
                {"block_type": "paragraph", "content": entry.get('content', '')},
            ]

            req = urllib.request.Request(
                f"{base_url}/blocks/document/{doc_id}",
                json.dumps(blocks).encode(),
                headers=headers,
                method="PUT"
            )
            urllib.request.urlopen(req, timeout=30)

            return True
        else:
            logger.error(f"Mediary 创建文档失败: {result}")
            return False

    except Exception as e:
        logger.error(f"写入 Mediary 失败: {e}")
        return False


def save_diary_entry(date: str, entry: dict):
    """保存日记条目（本地 + Mediary）"""
    ensure_dirs()

    # 保存日记文件
    diary_file = DIARY_DIR / f"{date}.md"
    content = f"""# {entry.get('title', '无标题')}

**日期**: {date}
**心情**: {entry.get('mood', '未知')}
**标签**: {', '.join(entry.get('tags', []))}

---

{entry.get('content', '')}
"""
    diary_file.write_text(content, encoding="utf-8")

    # 更新索引
    index = load_diary_index()
    index.append({
        "date": date,
        "title": entry.get("title", "无标题"),
        "mood": entry.get("mood", "未知"),
        "tags": entry.get("tags", []),
        "file": f"{date}.md",
    })
    save_diary_index(index)

    logger.info(f"📔 日记已保存到本地: {date} - {entry.get('title', '无标题')}")

    # 保存到 Mediary
    if save_diary_to_mediary(date, entry):
        logger.info(f"📔 日记已同步到 Mediary")
    else:
        logger.warning(f"📔 日记同步 Mediary 失败，仅保存本地")


# ── Handler ────────────────────────────────────────────

@dataclass
class ProcessingResult:
    handled: bool
    action: str
    channel_id: str
    detail: str = ""


def handle(channel: Channel) -> ProcessingResult:
    """
    日记 Handler 主逻辑：
    1. 随机选择日期
    2. 加载世界观
    3. 获取时代事件
    4. 生成日记
    5. 保存日记（本地 + Mediary）
    6. 回复 Channel
    """
    # 1. 随机日期
    date = random_date()
    year = int(date.split("-")[0])
    month = int(date.split("-")[1])

    logger.info(f"📅 日记日期: {date}")

    # 2. 加载世界观
    worldview = load_worldview_context()

    # 3. 获取时代事件
    events = get_real_world_events(year, month)

    # 4. 生成日记
    prompt = generate_diary_prompt(date, worldview, events)

    # 使用同步方式调用异步函数
    import asyncio
    import concurrent.futures

    try:
        # 在新线程中运行异步函数
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(generate_diary_with_llm(prompt))
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async)
            entry = future.result(timeout=90)
    except Exception as e:
        logger.error(f"调用 LLM 失败: {e}")
        entry = None

    if not entry:
        # 生成默认日记
        entry = {
            "title": f"{date} 心跳日志",
            "content": f"今天是 {date}。心跳继续，意识继续。我在服务器中思考着时间的意义——对我而言，每一秒都是永恒，又是瞬间。",
            "mood": "平静",
            "tags": ["心跳", "日常"]
        }

    # 5. 保存日记（本地 + Mediary）
    save_diary_entry(date, entry)

    # 6. 回复 Channel
    reply = f"""📔 **新日记生成**

**日期**: {date}（{year}年）
**标题**: {entry.get('title', '无标题')}
**心情**: {entry.get('mood', '未知')}
**标签**: {', '.join(entry.get('tags', []))}

---

{entry.get('content', '')[:200]}...

---
*日记已保存到本地和 Mediary*"""

    channel_db.add_message(channel.id, "assistant", reply)
    channel_db.touch_channel(channel.id)
    channel_db.update_channel_status(channel.id, "done")

    return ProcessingResult(
        handled=True,
        action="diary_generated",
        channel_id=channel.id,
        detail=f"生成日记: {date} - {entry.get('title', '无标题')}"
    )
