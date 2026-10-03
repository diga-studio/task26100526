"""发布器：读入项目快照 JSON，把单页 HTML 写入本地目录。"""
from __future__ import annotations

from pathlib import Path

from .expand import expand_project
from .model import load_project
from .render import render_document

OUTPUT_NAME = "index.html"


def publish(project_source: str | Path | dict, out_dir: str | Path) -> Path:
    """执行完整发布，返回生成的 HTML 文件路径。失败抛 PublishError。"""
    project = load_project(project_source)
    expanded = expand_project(project)
    html = render_document(expanded)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    target = out_path / OUTPUT_NAME
    target.write_text(html, encoding="utf-8")
    return target
