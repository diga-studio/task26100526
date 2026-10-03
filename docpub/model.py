"""项目数据模型与元素树节点定义。"""
from __future__ import annotations

from dataclasses import dataclass, field


# 普通元素允许的标签
PLAIN_TAGS = frozenset({"p", "div", "span", "h1", "h2", "a"})
# 控制元素
TAG_WHEN = "when"
TAG_INCLUDE = "include"


@dataclass(slots=True)
class Element:
    """正文元素树节点。普通元素保留属性与文本语义。"""


    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    text: str = ""
    tail: str = ""
    children: list["Element"] = field(default_factory=list)


@dataclass
class Topic:
    """有序主题，具有唯一标识。"""

    id: str
    title: str
    body: Element  # 虚拟根节点，tag 为 ""


@dataclass
class Snippet:
    """命名片段，具有唯一名称。"""

    name: str
    body: Element


@dataclass
class Project:
    """项目快照：有序主题 + 命名片段 + 本次选中的条件标签集合。"""

    name: str
    tags: frozenset[str]
    topics: list[Topic]
    snippets: dict[str, Snippet]
