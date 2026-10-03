"""链接解析：按命名空间规则把每条保留 href 绑定到具体锚点实例。

- "#x"：从链接所在作用域向外找最近声明 x 的作用域，到主题根为止；
  最近声明若已被过滤（None），链接判为失效，不回退外层同名锚点。
- "topic:T#x"：只查主题 T 自身作用域，不进入 T 插入的片段。
- 被过滤的链接根本不存在于展开结果中，自然不参与检查。
"""
from __future__ import annotations

from .errors import PublishError, SourceLocation
from .expand import Expansion, Scope
from .model import Element

_MAX_ERRORS = 20


def _iter_elements(items: list):
    """遍历保留内容中的全部普通元素（不进入子作用域，由调用方递归）。"""
    for item in items:
        if isinstance(item, Scope):
            yield from _iter_elements(item.content)
        else:
            yield item
            yield from _iter_elements(item.children)


def _resolve_local(anchor: str, scope: Scope) -> "Element | None":
    """向外层逐级查找；返回目标元素，None 表示失效（未声明或已被过滤）。"""
    current: "Scope | None" = scope
    while current is not None:
        if anchor in current.anchors:
            return current.anchors[anchor]  # None 表示最近声明已被过滤：失效
        current = current.parent
    return None


def resolve_links(
    expansion: Expansion, topic_index: "dict[str, Scope]"
) -> "dict[int, Element]":
    """返回 {链接元素 id(): 目标锚点元素}。任一保留链接失效则抛 PublishError。"""
    targets: dict[int, Element] = {}
    errors: list[str] = []

    for topic_scope in expansion.topic_scopes:
        for el in _iter_elements(topic_scope.content):
            if el.tag != "a":
                continue
            href = el.attrs.get("href", "")
            if href.startswith("#"):
                anchor = href[1:]
                if not anchor:
                    errors.append(f"empty anchor in href '#' at {topic_scope.topic_id}")
                    continue
                link_scope = expansion.elem_scope[id(el)]
                target = _resolve_local(anchor, link_scope)
                location = link_scope.location
            elif href.startswith("topic:"):
                rest = href[len("topic:"):]
                tid, sep, anchor = rest.partition("#")
                if not sep or not tid or not anchor:
                    errors.append(
                        f"malformed href '{href}' at {topic_scope.topic_id}"
                    )
                    continue
                target_scope = topic_index.get(tid)
                if target_scope is None:
                    target = None
                else:
                    # 只查主题自身作用域，不进入其片段
                    target = target_scope.anchors.get(anchor)
                location = expansion.elem_scope[id(el)].location
            else:
                # 外部链接不参与内部引用检查
                continue

            if target is None:
                errors.append(
                    f"unresolved link '{href}' (missing or filtered target) "
                    f"at {location}"
                )
            else:
                targets[id(el)] = target

    if errors:
        shown = errors[:_MAX_ERRORS]
        more = f" ... and {len(errors) - _MAX_ERRORS} more" if len(errors) > _MAX_ERRORS else ""
        raise PublishError(
            f"publish failed: {len(errors)} broken link(s): "
            + "; ".join(shown) + more
        )
    return targets
