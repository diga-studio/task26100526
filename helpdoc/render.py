"""把展开后的元素树序列化为 HTML。"""
from __future__ import annotations

from html import escape
from xml.etree.ElementTree import Element

from .model import Topic


def render_document(topics: list[tuple[Topic, Element]]) -> str:
    """把各主题输出树按序合并为单页 HTML 字符串。"""
    parts = [
        "<!DOCTYPE html>",
        '<html><head><meta charset="utf-8"><title>Help</title></head><body>',
    ]
    for topic, root in topics:
        parts.append(f'<section data-topic="{escape(topic.id, quote=True)}">')
        if topic.title:
            parts.append(f"<h1>{escape(topic.title)}</h1>")
        parts.append(_serialize_children(root))
        parts.append("</section>")
    parts.append("</body></html>")
    return "".join(parts)


def _serialize_children(elem: Element) -> str:
    parts: list[str] = []
    if elem.text:
        parts.append(escape(elem.text))
    for child in elem:
        _serialize(child, parts)
    return "".join(parts)


def _serialize(elem: Element, parts: list[str]) -> None:
    attrs = "".join(
        f' {name}="{escape(value, quote=True)}"'
        for name, value in elem.attrib.items())
    parts.append(f"<{elem.tag}{attrs}>")
    parts.append(_serialize_children(elem))
    parts.append(f"</{elem.tag}>")
    if elem.tail:
        parts.append(escape(elem.tail))
