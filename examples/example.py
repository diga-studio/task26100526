"""最小调用示例：构造项目快照 JSON，发布为单页 HTML。"""
import json
import tempfile
from pathlib import Path

from helpdoc import publish

project = {
    "tags": ["windows"],
    "snippets": [
        {
            "name": "open-settings",
            "body": (
                '<p id="step-open">打开<when tag="windows">Windows </when>设置。</p>'
            ),
        }
    ],
    "topics": [
        {
            "id": "install",
            "title": "安装",
            "body": (
                '<h2 id="prepare">准备</h2>'
                '<include name="open-settings"/>'
                '<p>详见<a href="#prepare">准备</a>一节。</p>'
            ),
        },
        {
            "id": "faq",
            "title": "常见问题",
            "body": '<p>回到<a href="topic:install#prepare">安装准备</a>。</p>',
        },
    ],
}

out_dir = Path(tempfile.mkdtemp(prefix="helpdoc-example-"))
snapshot = out_dir / "project.json"
snapshot.write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")

target = publish(snapshot, out_dir)
print(f"published: {target}")
print(target.read_text(encoding="utf-8"))
