"""渲染合并后的单页 HTML：全部 id 全局唯一，href 指向解析后的锚点实例。"""
from __future__ import annotations

from .expand import Scope
from .model import Element

_ESCAPES = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}


def _escape_text(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(s: str) -> str:
    return _escape_text(s).replace('"', "&quot;")


def _assign_ids(topic_scopes: "list[Scope]") -> "dict[int, str]":
    """按文档顺序为每个保留锚点元素分配全局唯一 id。"""
    new_ids: dict[int, str] = {}
    counter = 0

    def visit(items: list) -> None:
        nonlocal counter
        for item in items:
            if isinstance(item, Scope):
                visit(item.content)
            else:
                if "id" in item.attrs:
                    counter += 1
                    new_ids[id(item)] = f"a{counter}"
                visit(item.children)

    for scope in topic_scopes:
        visit(scope.content)
    return new_ids


def _render_items(
    items: list,
    new_ids: "dict[int, str]",
    link_targets: "dict[int, Element]",
    out: list,
) -> None:
    for item in items:
        if isinstance(item, Scope):
            _render_items(item.content, new_ids, link_targets, out)
            continue
        el = item
        attrs = []
        for key, value in el.attrs.items():
            if key == "id":
                value = new_ids[id(el)]
            elif key == "href" and el.tag == "a" and id(el) in link_targets:
                value = "#" + new_ids[id(link_targets[id(el)])]
            attrs.append(f'{key}="{_escape_attr(value)}"')
        attr_str = (" " + " ".join(attrs)) if attrs else ""
        out.append(f"<{el.tag}{attr_str}>")
        out.append(_escape_text(el.text))
        _render_items(el.children, new_ids, link_targets, out)
        out.append(f"</{el.tag}>")
        out.append(_escape_text(el.tail))


def render_html(
    project_name: str,
    topic_scopes: "list[Scope]",
    topic_titles: "dict[str, str]",
    link_targets: "dict[int, Element]",
) -> str:
    """生成最终单页 HTML 文本。"""
    new_ids = _assign_ids(topic_scopes)
    parts: list[str] = [
        "<!DOCTYPE html>",
        "<html><head>",
        f'<meta charset="utf-8"/><title>{_escape_text(project_name)}</title>',
        "</head><body>",
    ]
    for scope in topic_scopes:
        title = topic_titles.get(scope.topic_id, scope.topic_id)
        parts.append(f'<section data-topic="{_escape_attr(scope.topic_id)}">')
        parts.append(f"<h1>{_escape_text(title)}</h1>")
        _render_items(scope.content, new_ids, link_targets, parts)
        parts.append("</section>")
    parts.append("</body></html>")
    return "\n".join(parts)
