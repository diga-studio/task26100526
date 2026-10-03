"""解析 XML 良构的 HTML 子集正文为元素树。"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from .errors import PublishError
from .model import PLAIN_TAGS, TAG_INCLUDE, TAG_WHEN, Element

_ALLOWED = PLAIN_TAGS | {TAG_WHEN, TAG_INCLUDE}


def _convert(node: ET.Element, source: str) -> Element:
    tag = node.tag
    if not isinstance(tag, str) or tag not in _ALLOWED:
        raise PublishError(f"unsupported element <{tag}> in {source}")
    el = Element(
        tag=tag,
        attrs={k: v for k, v in node.attrib.items()},
        text=node.text or "",
    )
    for child in node:
        conv = _convert(child, source)
        conv.tail = child.tail or ""
        el.children.append(conv)
    return el


def parse_body(xml_text: str, source: str) -> Element:
    """把正文字符串解析为以虚拟根（tag 为 ""）包裹的元素树。"""
    try:
        root = ET.fromstring(f"<root>{xml_text}</root>")
    except ET.ParseError as exc:
        raise PublishError(f"malformed XML body in {source}: {exc}") from exc
    body = Element(tag="", text=root.text or "")
    for child in root:
        conv = _convert(child, source)
        conv.tail = child.tail or ""
        body.children.append(conv)
    return body
