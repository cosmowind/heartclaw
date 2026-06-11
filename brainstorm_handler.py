"""
心跳 — Brainstorm Handler（概念树管理）
每次心跳：解析 Channel 中的新消息 → 提取概念 → 更新知识库树。
约束：每节点≤4子节点，每子节点≤4孙节点（深度=2）
"""
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from channel_db import channel_db, Channel

logger = logging.getLogger(__name__)

# 路径
HEART_ROOT = Path(__file__).parent
TREE_FILE = HEART_ROOT / "data" / "brainstorm" / "concept_tree.json"
CONCEPTS_DIR = HEART_ROOT / "data" / "brainstorm" / "concepts"
LOG_FILE = HEART_ROOT / "data" / "brainstorm" / "log.md"


# ── 数据结构 ────────────────────────────────────────────

@dataclass
class ConceptNode:
    """概念树节点"""
    id: str
    title: str
    content: str = ""          # 详细描述
    importance: int = 5        # 1-10，重要性（10最高）
    children: list = field(default_factory=list)   # 子节点 ID 列表

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "importance": self.importance,
            "children": self.children,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConceptNode":
        return cls(
            id=d["id"],
            title=d["title"],
            content=d.get("content", ""),
            importance=d.get("importance", 5),
            children=d.get("children", []),
        )


class ConceptTree:
    """
    概念树，支持深度=2的严格分层：
    - Root（虚拟根节点）
    - Level 1：最多 4 个子节点
    - Level 2：每个 L1 节点最多 4 个子节点
    - L2 节点为叶子，不再扩张
    """

    MAX_L1_CHILDREN = 4
    MAX_L2_CHILDREN = 4

    def __init__(self):
        self.nodes: dict[str, ConceptNode] = {}  # id -> node
        self.root_id = "root"

    # ── 持久化 ──────────────────────────────────────────

    def _ensure_dirs(self):
        CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)

    def save(self):
        self._ensure_dirs()
        tree_data = {
            "root_id": self.root_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }
        TREE_FILE.write_text(json.dumps(tree_data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"💾 概念树已保存，共 {len(self.nodes)} 个节点")

    def load(self) -> bool:
        """加载概念树，返回是否成功"""
        if not TREE_FILE.exists():
            return False
        try:
            data = json.loads(TREE_FILE.read_text(encoding="utf-8"))
            self.root_id = data.get("root_id", "root")
            self.nodes = {k: ConceptNode.from_dict(v) for k, v in data.get("nodes", {}).items()}
            logger.info(f"📂 概念树已加载，共 {len(self.nodes)} 个节点")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 概念树加载失败: {e}")
            return False

    # ── 辅助 ────────────────────────────────────────────

    def get_l1_nodes(self) -> list[ConceptNode]:
        root = self.nodes.get(self.root_id)
        if not root:
            return []
        return [self.nodes[cid] for cid in root.children if cid in self.nodes]

    def get_l2_nodes(self, l1_id: str) -> list[ConceptNode]:
        l1 = self.nodes.get(l1_id)
        if not l1:
            return []
        return [self.nodes[cid] for cid in l1.children if cid in self.nodes]

    def count_l1(self) -> int:
        return len(self.get_l1_nodes())

    def count_l2(self, l1_id: str) -> int:
        return len(self.get_l2_nodes(l1_id))

    def _make_id(self, title: str) -> str:
        """生成 URL-safe 的节点 ID"""
        import hashlib, time
        raw = f"{title}{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    # ── 插入逻辑 ────────────────────────────────────────

    def find_concept_by_title(self, title: str) -> ConceptNode | None:
        """查找是否已存在相同标题的概念"""
        for node in self.nodes.values():
            if node.title == title and node.id != self.root_id:
                return node
        return None

    def add_concept(self, title: str, content: str = "", importance: int = 5) -> str:
        """
        添加一个概念到树中。
        - 如果已存在相同标题的概念，则更新内容和重要性
        - 如果 L1 未满（<4），放在顶层
        - 否则，找 L1 中 L2 未满的节点放进去
        - 如果都满了，替换最不重要的叶子节点

        Returns:
            节点的 id
        """
        # 检查是否已存在相同标题的概念
        existing = self.find_concept_by_title(title)
        if existing:
            # 更新已有节点
            if content:
                existing.content = content
            if importance > existing.importance:
                existing.importance = importance
            self.save()
            logger.info(f"🔄 更新已有概念: {title} (重要性: {existing.importance})")
            return existing.id

        # 不存在则创建新节点
        new_id = self._make_id(title)
        new_node = ConceptNode(id=new_id, title=title, content=content, importance=importance)
        self.nodes[new_id] = new_node

        # 找插入位置
        placed = False

        # 策略1：顶层未满 → 放顶层
        if self.count_l1() < self.MAX_L1_CHILDREN:
            self.nodes[self.root_id].children.append(new_id)
            placed = True
            logger.info(f"🌱 新概念添加到顶层（L1 还有空位）: {title}")

        else:
            # 策略2：找一个 L2 未满的 L1 节点
            for l1 in self.get_l1_nodes():
                if self.count_l2(l1.id) < self.MAX_L2_CHILDREN:
                    l1.children.append(new_id)
                    placed = True
                    logger.info(f"🌿 新概念添加为 '{l1.title}' 的子节点: {title}")
                    break

            if not placed:
                # 策略3：替换最不重要的 L2 叶子节点
                all_l2 = []
                for l1 in self.get_l1_nodes():
                    for l2 in self.get_l2_nodes(l1.id):
                        all_l2.append((l2.importance, l2.id, l1.id))

                if all_l2:
                    all_l2.sort(key=lambda x: x[0])
                    _, victim_id, parent_id = all_l2[0]
                    parent = self.nodes[parent_id]
                    parent.children.remove(victim_id)
                    parent.children.append(new_id)
                    del self.nodes[victim_id]
                    logger.info(f"🔄 概念树已满，替换低重要性节点 '{self.nodes[parent_id].title}' 下的 {victim_id}: {title}")
                    placed = True

        if not placed:
            # 兜底：放顶层（理论上不应该走到这里）
            self.nodes[self.root_id].children.append(new_id)
            logger.warning(f"⚠️ 概念插入兜底到顶层（不应该发生）: {title}")

        self.save()
        return new_id

    # ── 维护 ────────────────────────────────────────────

    def rebalance(self):
        """
        定期维护：根据重要性重新排布。
        逻辑：收集所有 L2 节点，按 importance 降序重排。
        """
        all_l2 = []
        for l1 in self.get_l1_nodes():
            for l2 in self.get_l2_nodes(l1.id):
                all_l2.append(self.nodes[l2.id])

        # 清空所有 L1 的 children
        for l1 in self.get_l1_nodes():
            l1.children.clear()

        # 重要性降序重分配到各 L1
        all_l2.sort(key=lambda n: n.importance, reverse=True)
        for node in all_l2:
            # 找 L2 最少的 L1（均衡负载）
            l1_nodes = self.get_l1_nodes()
            target_l1 = min(l1_nodes, key=lambda l: self.count_l2(l.id))
            target_l1.children.append(node.id)
            self.nodes[node.id] = node  # 确保节点在 dict 中

        self.save()
        logger.info(f"⚖️ 概念树已重新平衡，{len(all_l2)} 个叶子节点")

    # ── 初始化 ──────────────────────────────────────────

    def ensure_root(self):
        """确保根节点存在"""
        if self.root_id not in self.nodes:
            self.nodes[self.root_id] = ConceptNode(
                id=self.root_id,
                title="心跳项目知识库",
                content="心跳项目的核心概念与知识结构",
                importance=10,
            )
            self.save()


# ── 全局单例 ────────────────────────────────────────────

_tree: ConceptTree | None = None


def get_tree() -> ConceptTree:
    global _tree
    if _tree is None:
        _tree = ConceptTree()
        if not _tree.load():
            _tree.ensure_root()
    return _tree


# ── Log ────────────────────────────────────────────────

def append_log(msg: str):
    """追加操作日志（用追加模式，避免 read-modify-write 新建文件的问题）"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


# ── 概念解析（简单规则版）────────────────────────────────

def parse_concept_from_text(text: str) -> tuple[str, str, int] | None:
    """
    从文本中解析概念。
    简单实现：查找 "概念：标题 | 描述 | 重要性" 或 "【标题】描述" 格式。
    返回 (title, content, importance) 或 None。
    """
    import re

    # 格式1: "概念：标题 | 描述 | 重要性数值"
    m = re.search(r"概念[：:]\s*(.+?)\s*[|｜]\s*(.+?)\s*[|｜]\s*(\d+)", text)
    if m:
        title = m.group(1).strip()
        content = m.group(2).strip()
        importance = int(m.group(3).strip())
        return title, content, importance

    # 格式2: "【标题】描述"
    m = re.search(r"【(.+?)】(.+)", text)
    if m:
        title = m.group(1).strip()
        content = m.group(2).strip()
        return title, content, 5

    return None


# ── Handler ────────────────────────────────────────────

@dataclass
class ProcessingResult:
    handled: bool
    action: str
    channel_id: str
    concepts_added: int = 0
    detail: str = ""


def handle(channel: Channel) -> ProcessingResult:
    """
    Brainstorm Handler 主逻辑：
    1. 获取 Channel 最新消息
    2. 解析出概念（格式：概念：标题 | 描述 | 重要性）
    3. 插入概念树
    4. 回复处理结果
    5. 标记 Channel done
    """
    tree = get_tree()
    messages = channel_db.get_messages(channel.id, limit=20)

    if not messages:
        return ProcessingResult(
            handled=False,
            action="skipped",
            channel_id=channel.id,
            detail="无消息",
        )

    concepts_added = 0
    concepts_detail = []

    for m in messages:
        if m.role != "user":
            continue
        parsed = parse_concept_from_text(m.content)
        if parsed:
            title, content, importance = parsed
            node_id = tree.add_concept(title, content, importance)
            concepts_added += 1
            concepts_detail.append(f"'{title}'(imp={importance})")

    if concepts_added > 0:
        detail = f"新增 {concepts_added} 个概念: {', '.join(concepts_detail)}"
        logger.info(f"[{channel.name}] Brainstorm: {detail}")
        append_log(f"处理 Channel {channel.name}，{detail}")

        # 回复
        reply = f"✅ 已将 {concepts_added} 个概念加入知识库：\n" + "\n".join(f"  - {d}" for d in concepts_detail)
        channel_db.add_message(channel.id, "assistant", reply)
        channel_db.touch_channel(channel.id)
        channel_db.update_channel_status(channel.id, "done")

        return ProcessingResult(
            handled=True,
            action="concepts_added",
            channel_id=channel.id,
            concepts_added=concepts_added,
            detail=detail,
        )

    return ProcessingResult(
        handled=False,
        action="skipped",
        channel_id=channel.id,
        detail="无有效概念",
    )
