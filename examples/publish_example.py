"""最小调用示例：构造项目 JSON，调用 docpub.publish 生成单页 HTML。

运行：python3 examples/publish_example.py [输出目录]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from docpub import PublishError, publish

PROJECT = {
    "name": "示例帮助文档",
    "tags": ["windows"],  # 本次选中的条件标签
    "topics": [
        {
            "id": "intro",
            "title": "入门",
            "body": (
                '<p id="overview">入门概览。</p>'
                '<include name="install-steps"/>'
                '<p>进阶内容见 <a href="topic:advanced#overview">进阶概览</a>。</p>'
            ),
        },
        {
            "id": "advanced",
            "title": "进阶",
            "body": (
                '<p id="overview">进阶概览。</p>'
                '<include name="install-steps"/>'
            ),
        },
    ],
    "snippets": [
        {
            "name": "install-steps",
            "body": (
                '<h2 id="install">安装步骤</h2>'
                '<p>第一步……</p>'
                '<when tag="windows"><p>Windows 特有步骤。</p></when>'
                '<when tag="mac"><p>macOS 特有步骤。</p></when>'
                '<p>回到 <a href="#install">安装步骤</a> 开头。</p>'
            ),
        },
    ],
}


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "build"
    project_path = os.path.join(out_dir, "project.json")
    os.makedirs(out_dir, exist_ok=True)
    with open(project_path, "w", encoding="utf-8") as fh:
        json.dump(PROJECT, fh, ensure_ascii=False, indent=2)
    try:
        html_path = publish(project_path, out_dir)
    except PublishError as exc:
        print(f"发布失败：{exc}", file=sys.stderr)
        sys.exit(1)
    print(f"发布成功：{html_path}")


if __name__ == "__main__":
    main()
