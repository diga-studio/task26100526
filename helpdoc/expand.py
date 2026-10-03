"""条件过滤、片段展开、锚点命名空间与链接解析。"""
from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree.ElementTree import Element

from .errors import PublishError, SourceLocation
from .model import Project, Topic
from .parser import parse_fragment

MAX_INCLUDE_DEPTH = 64


@dataclass
class Anchor:
    raw_id: str
    out_id: str
    location: SourceLocation


@dataclass
class Namespace:
    """一个主题或一次片段插入对应的锚点命名空间。"""

    location: SourceLocation
    parent: "Namespace | None" = None
    declared: dict[str, Anchor | None] = field(default_factory=dict)


@dataclass
class _Link:
    elem: Element
    href: str
    ns: Namespace
    location: SourceLocation


def expand_project(project: Project) -> list[tuple[Topic, Element]]:
    """过滤条件、展开片段并解析全部链接，返回每主题的输出元素树。"""
    expander = _Expander(project)
    return expander.run()


class _Expander:
    def __init__(self, project: Project) -> None:
        self.project = project
        self.tags = project.tags
        self.snippet_trees: dict[str, Element] = {}
        self.links: list[_Link] = []
        self.topic_namespaces: dict[str, Namespace] = {}
        self.anchor_count = 0

    def run(self) -> list[tuple[Topic, Element]]:
        for name, snippet in self.project.snippets.items():
            self.snippet_trees[name] = parse_fragment(
                snippet.body, SourceLocation("<snippets>", (name,)))
        out: list[tuple[Topic, Element]] = []
        for topic in self.project.topics:
            out.append((topic, self._expand_topic(topic)))
        self._resolve_links()
        return out

    def _expand_topic(self, topic: Topic) -> Element:
        location = SourceLocation(topic.id)
        root = parse_fragment(topic.body, location)
        ns = Namespace(location=location)
        self.topic_namespaces[topic.id] = ns
        self._prescan(root, ns)
        out_root = Element("section", {"data-topic": topic.id})
        _append_text(out_root, root.text)
        self._process_children(root, ns, out_root, location, 0)
        return out_root

    # ---- 命名空间声明预扫描：不看条件，遇 include 边界停止 ----
    def _prescan(self, src_parent: Element, ns: Namespace) -> None:
        for child in src_parent:
            if child.tag == "include":
                continue
            if child.tag != "when":
                raw = child.get("id")
                if raw and raw not in ns.declared:
                    ns.declared[raw] = None
            self._prescan(child, ns)

    # ---- 条件过滤 + 片段展开 ----
    def _process_children(self, src_parent: Element, ns: Namespace,
                          out_parent: Element, location: SourceLocation,
                          depth: int) -> None:
        if depth > MAX_INCLUDE_DEPTH:
            raise PublishError("include nesting too deep (cycle?)", location)
        for child in src_parent:
            tag = child.tag
            if tag == "when":
                if child.get("tag") in self.tags:
                    _append_text(out_parent, child.text)
                    self._process_children(child, ns, out_parent, location, depth)
                _append_text(out_parent, child.tail)
                continue
            if tag == "include":
                name = child.get("name", "")
                snippet_root = self.snippet_trees.get(name)
                if snippet_root is None:
                    raise PublishError(f"unknown snippet '{name}'", location)
                child_location = SourceLocation(
                    location.topic_id, location.include_path + (name,))
                child_ns = Namespace(location=child_location, parent=ns)
                self._prescan(snippet_root, child_ns)
                _append_text(out_parent, child.text)
                self._process_children(snippet_root, child_ns, out_parent,
                                       child_location, depth + 1)
                _append_text(out_parent, child.tail)
                continue
            out = Element(tag, dict(child.attrib))
            raw_id = child.get("id")
            if raw_id:
                out_id = f"a{self.anchor_count}"
                self.anchor_count += 1
                ns.declared[raw_id] = Anchor(raw_id, out_id, location)
                out.set("id", out_id)
            if tag == "a":
                href = child.get("href")
                if href and (href.startswith("#") or href.startswith("topic:")):
                    self.links.append(_Link(out, href, ns, location))
            out.text = child.text
            self._process_children(child, ns, out, location, depth)
            out.tail = child.tail
            out_parent.append(out)

    # ---- 链接解析 ----
    def _resolve_links(self) -> None:
        for link in self.links:
            href = link.href
            if href.startswith("#"):
                raw = href[1:]
                anchor = self._resolve_local(link.ns, raw)
                if anchor is None:
                    raise PublishError(
                        f"unresolved link '#{raw}'", link.location)
            else:
                target_topic, _, raw = href[len("topic:"):].partition("#")
                topic_ns = self.topic_namespaces.get(target_topic)
                if topic_ns is None:
                    raise PublishError(
                        f"link targets unknown topic '{target_topic}'",
                        link.location)
                anchor = topic_ns.declared.get(raw)
                if anchor is None:
                    raise PublishError(
                        f"unresolved link 'topic:{target_topic}#{raw}'",
                        link.location)
            link.elem.set("href", f"#{anchor.out_id}")

    @staticmethod
    def _resolve_local(ns: Namespace, raw: str) -> Anchor | None:
        """从链接所在命名空间向外找最近声明；被过滤的最近声明判失效。"""
        current: Namespace | None = ns
        while current is not None:
            if raw in current.declared:
                return current.declared[raw]
            current = current.parent
        return None


def _append_text(out_parent: Element, text: str | None) -> None:
    if not text:
        return
    if len(out_parent):
        last = out_parent[-1]
        last.tail = (last.tail or "") + text
    else:
        out_parent.text = (out_parent.text or "") + text
