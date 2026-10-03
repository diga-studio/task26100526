# helpdoc

单页帮助文档发布库。项目快照保存在本地 JSON，生成的单页 HTML 写入本地目录。

## 用法

```python
from helpdoc import publish

target = publish("project.json", "out/")  # 返回 out/index.html 路径
```

项目快照格式：

```json
{
  "tags": ["windows"],
  "snippets": [{"name": "s", "body": "<p id=\"x\">...</p>"}],
  "topics": [{"id": "t1", "title": "标题", "body": "<include name=\"s\"/>..."}]
}
```

- `<when tag="x">`：仅在选中标签 `x` 时保留，控制元素不输出。
- `<include name="s"/>`：在该位置插入片段 `s`，可嵌套（保证无环）。
- 每个主题与每次片段插入是独立锚点命名空间；`#x` 向外找最近声明，
  `topic:T#x` 只引用主题 T 自身声明。被条件过滤的最近声明判链接失效。
- 任一保留链接无对应声明或目标被过滤，整次发布失败并抛 `PublishError`
  （`error.location` 定位到来源主题与片段插入路径）。

运行示例与测试：

```sh
PYTHONPATH=. python3 examples/example.py
python3 -m pytest tests/ -q
```
