"""XML 良构 HTML 子集片段的解析。"""
from __future__ import annotations

from xml.etree.ElementTree import Element, ParseError, fromstring

from .errors import PublishError, SourceLocation

ALLOWED_ELEMENTS = frozenset({"p", "div", "span", "h1", "h2", "a", "when", "include"})

_ROOT = "helpdoc-root"


def parse_fragment(body: str, location: SourceLocation | None = None) -> Element:
    """把正文片段解析为以占位根元素包裹的元素树。"""
    try:
        root = fromstring(f"<{_ROOT}>{body}</{_ROOT}>")
    except ParseError as exc:
        raise PublishError(f"malformed XML body: {exc}", location) from exc
    _validate(root, location)
    return root


def _validate(elem: Element, location: SourceLocation | None) -> None:
    for child in elem:
        tag = child.tag
        if tag not in ALLOWED_ELEMENTS:
            raise PublishError(f"unsupported element <{tag}>", location)
        if tag == "when" and not child.get("tag"):
            raise PublishError("<when> requires a 'tag' attribute", location)
        if tag == "include":
            if not child.get("name"):
                raise PublishError("<include> requires a 'name' attribute", location)
            if len(child) or (child.text and child.text.strip()):
                raise PublishError("<include> must be empty", location)
        _validate(child, location)
