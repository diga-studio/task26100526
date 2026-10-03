"""条件过滤与片段展开，构建作用域（锚点命名空间）树。

规则：
- 每个主题和每次片段插入产生一个独立作用域；普通元素与 when 块不产生。
- when 未选中时整块过滤，但其中声明的锚点仍记入当前作用域（值为 None），
  以保证同名遮蔽语义不因条件过滤而改变。
- include 在选中时展开为子作用域，嵌套插入形成外层关系。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .errors import PublishError, SourceLocation
from .model import TAG_INCLUDE, TAG_WHEN, Element, Project

MAX_INCLUDE_DEPTH = 32


@dataclass(slots=True)
class Scope:
    """一个锚点命名空间：主题或一次片段插入。"""


    topic_id: str
    parent: "Scope | None" = None
    include_path: tuple[str, ...] = ()
    # 原始 id -> 保留的元素；被条件过滤的声明 -> None（遮蔽仍然生效）
    anchors: dict[str, "Element | None"] = field(default_factory=dict)
    # 展开并过滤后的有序内容：普通元素或子作用域（片段插入位置）
    content: list = field(default_factory=list)  # list[Element | Scope]
    children: "list[Scope]" = field(default_factory=list)

    @property
    def location(self) -> SourceLocation:
        return SourceLocation(topic_id=self.topic_id, include_path=self.include_path)


@dataclass
class Expansion:
    topic_scopes: "list[Scope]"
    # 保留元素 id() -> 声明它（或它所在）的作用域
    elem_scope: "dict[int, Scope]"


def _record_filtered_anchors(node: Element, scope: Scope) -> None:
    """把被过滤子树中的锚点声明记为 None（include 无子节点，天然跳过）。"""
    anchor = node.attrs.get("id")
    if anchor is not None:
        scope.anchors[anchor] = None
    for child in node.children:
        _record_filtered_anchors(child, scope)


def _declare(scope: Scope, anchor: str, el: "Element | None") -> None:
    if anchor in scope.anchors:
        raise PublishError(
            f"duplicate anchor id '{anchor}' in the same namespace",
            location=scope.location,
        )
    scope.anchors[anchor] = el


def _process_nodes(
    nodes: "list[Element]",
    scope: Scope,
    out: list,
    project: Project,
    expansion: Expansion,
    depth: int,
) -> None:
    for node in nodes:
        if node.tag == TAG_WHEN:
            tag = node.attrs.get("tag", "")
            if tag in project.tags:
                # 条件块不产生新命名空间，内容就地展开
                _process_nodes(node.children, scope, out, project, expansion, depth)
            else:
                for child in node.children:
                    _record_filtered_anchors(child, scope)
        elif node.tag == TAG_INCLUDE:
            name = node.attrs.get("name", "")
            if depth + 1 > MAX_INCLUDE_DEPTH:
                raise PublishError(
                    f"include depth exceeds {MAX_INCLUDE_DEPTH} at snippet '{name}'",
                    location=scope.location,
                )
            snippet = project.snippets[name]  # loader 已校验存在
            child_scope = Scope(
                topic_id=scope.topic_id,
                parent=scope,
                include_path=scope.include_path + (name,),
            )
            scope.children.append(child_scope)
            out.append(child_scope)
            _process_nodes(
                snippet.body.children, child_scope, child_scope.content,
                project, expansion, depth + 1,
            )
        else:
            clone = Element(tag=node.tag, attrs=dict(node.attrs), text=node.text)
            clone.tail = node.tail
            anchor = clone.attrs.get("id")
            if anchor is not None:
                _declare(scope, anchor, clone)
            expansion.elem_scope[id(clone)] = scope
            out.append(clone)
            _process_nodes(node.children, scope, clone.children, project, expansion, depth)


def expand_project(project: Project) -> Expansion:
    """对每个主题做条件过滤 + 片段展开，返回主题作用域列表。"""
    expansion = Expansion(topic_scopes=[], elem_scope={})
    for topic in project.topics:
        scope = Scope(topic_id=topic.id)
        expansion.topic_scopes.append(scope)
        _process_nodes(
            topic.body.children, scope, scope.content, project, expansion, depth=0
        )
    return expansion
