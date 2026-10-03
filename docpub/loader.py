"""从本地 JSON 加载项目快照。"""
from __future__ import annotations

import json

from .errors import PublishError
from .model import TAG_INCLUDE, Element, Project, Snippet, Topic
from .parser import parse_body

_FORMAT = """{
  "name": "项目名",
  "tags": ["选中的条件标签", ...],
  "topics": [{"id": "t1", "title": "标题", "body": "<p>...</p>"}, ...],
  "snippets": [{"name": "s1", "body": "<p>...</p>"}, ...]
}"""


def _iter_includes(el: Element):
    for child in el.children:
        if child.tag == TAG_INCLUDE:
            yield child.attrs.get("name", "")
        yield from _iter_includes(child)


def _check_acyclic(snippets: dict[str, Snippet]) -> None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in snippets}

    def visit(name: str, stack: list[str]) -> None:
        color[name] = GRAY
        stack.append(name)
        for dep in _iter_includes(snippets[name].body):
            if dep not in snippets:
                raise PublishError(
                    f"snippet '{name}' includes unknown snippet '{dep}'"
                )
            if color[dep] == GRAY:
                cycle = " -> ".join(stack + [dep])
                raise PublishError(f"cyclic snippet include detected: {cycle}")
            if color[dep] == WHITE:
                visit(dep, stack)
        stack.pop()
        color[name] = BLACK

    for name in snippets:
        if color[name] == WHITE:
            visit(name, [])


def load_project(path: str) -> Project:
    """加载项目 JSON，校验主题 id / 片段名唯一性及片段引用无环。"""
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise PublishError(f"invalid project JSON in {path}: {exc}") from exc

    topics: list[Topic] = []
    seen_topics: set[str] = set()
    for entry in data.get("topics", []):
        tid = entry["id"]
        if tid in seen_topics:
            raise PublishError(f"duplicate topic id '{tid}'")
        seen_topics.add(tid)
        topics.append(
            Topic(
                id=tid,
                title=entry.get("title", tid),
                body=parse_body(entry.get("body", ""), f"topic '{tid}'"),
            )
        )

    snippets: dict[str, Snippet] = {}
    for entry in data.get("snippets", []):
        name = entry["name"]
        if name in snippets:
            raise PublishError(f"duplicate snippet name '{name}'")
        snippets[name] = Snippet(
            name=name,
            body=parse_body(entry.get("body", ""), f"snippet '{name}'"),
        )

    _check_acyclic(snippets)

    for topic in topics:
        for dep in _iter_includes(topic.body):
            if dep not in snippets:
                raise PublishError(
                    f"topic '{topic.id}' includes unknown snippet '{dep}'"
                )

    return Project(
        name=data.get("name", "document"),
        tags=frozenset(data.get("tags", [])),
        topics=topics,
        snippets=snippets,
    )
