"""项目快照的数据模型与 JSON 载入。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .errors import PublishError


@dataclass
class Topic:
    id: str
    title: str
    body: str


@dataclass
class Snippet:
    name: str
    body: str


@dataclass
class Project:
    topics: list[Topic] = field(default_factory=list)
    snippets: dict[str, Snippet] = field(default_factory=dict)
    tags: frozenset[str] = frozenset()


def load_project(source: str | Path | dict) -> Project:
    """从 JSON 文件路径或已解析的 dict 载入项目快照。"""
    if isinstance(source, (str, Path)):
        with open(source, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        data = source
    if not isinstance(data, dict):
        raise PublishError("project snapshot must be a JSON object")

    topics: list[Topic] = []
    seen_ids: set[str] = set()
    for entry in data.get("topics", []):
        topic = Topic(id=str(entry["id"]), title=str(entry.get("title", "")),
                      body=str(entry.get("body", "")))
        if topic.id in seen_ids:
            raise PublishError(f"duplicate topic id '{topic.id}'")
        seen_ids.add(topic.id)
        topics.append(topic)

    snippets: dict[str, Snippet] = {}
    for entry in data.get("snippets", []):
        snippet = Snippet(name=str(entry["name"]), body=str(entry.get("body", "")))
        if snippet.name in snippets:
            raise PublishError(f"duplicate snippet name '{snippet.name}'")
        snippets[snippet.name] = snippet

    return Project(topics=topics, snippets=snippets,
                   tags=frozenset(str(t) for t in data.get("tags", [])))
