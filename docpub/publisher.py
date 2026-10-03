"""发布入口：读取项目 JSON，生成单页 HTML 写入本地目录。"""
from __future__ import annotations

import os

from .expand import expand_project
from .loader import load_project
from .render import render_html
from .resolve import resolve_links

OUTPUT_NAME = "index.html"


def publish(project_path: str, out_dir: str) -> str:
    """完整发布流程，返回生成的 HTML 文件路径。

    任一保留链接失效时抛 PublishError，且不写出任何产物。
    """
    project = load_project(project_path)
    expansion = expand_project(project)
    topic_index = {scope.topic_id: scope for scope in expansion.topic_scopes}
    link_targets = resolve_links(expansion, topic_index)
    titles = {topic.id: topic.title for topic in project.topics}
    html = render_html(project.name, expansion.topic_scopes, titles, link_targets)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, OUTPUT_NAME)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return out_path
