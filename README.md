# docpub — 单页帮助文档发布库

把"有序主题 + 可复用片段 + 条件标签"的项目快照（本地 JSON）合并发布为单页 HTML，
写入本地目录。发布器保持作者原本引用的对象：锚点命名空间隔离、同名遮蔽语义
不因条件过滤而改变、任一保留链接失效则整次发布失败。

## 快速开始

```python
from docpub import publish, PublishError

try:
    html_path = publish("project.json", "build/")   # 生成 build/index.html
except PublishError as exc:
    print("发布失败：", exc)   # 错误定位到来源主题及片段插入路径
```

可运行示例：`python3 examples/publish_example.py /tmp/docpub-demo`

## 项目 JSON 格式

```json
{
  "name": "文档名",
  "tags": ["windows"],
  "topics":   [{"id": "intro", "title": "入门", "body": "<p id=\"a\">…</p><include name=\"s\"/>"}],
  "snippets": [{"name": "s", "body": "<p id=\"a\">…</p><when tag=\"windows\"><p>…</p></when>"}]
}
```

- `body` 为 XML 良构的 HTML 子集；普通元素支持 `p/div/span/h1/h2/a`，保留属性与文本。
- `<when tag="x">`：仅在选中标签 `x` 时保留，控制元素不输出；嵌套条件须全部满足。
- `<include name="s"/>`：在该位置插入片段 `s`（引用保证无环，嵌套深度 ≤ 32）。

## 链接与锚点规则

- 每个主题和每次片段插入是独立的锚点命名空间；普通元素与 `when` 不产生新命名空间。
- `#x`：从链接所在命名空间向外找最近声明 `x` 的命名空间，到所属主题为止。
- `topic:T#x`：只引用主题 `T` 自身声明的锚点，不进入 `T` 插入的片段。
- 同名遮蔽不因条件过滤而改变：最近同名声明被过滤后链接判失效，不回退外层。
- 被过滤的链接不参与检查；任一保留链接失效则整次发布失败，不交付带坏链接的产物。
- 产物中所有 `id` 全局唯一（重写为 `a1…aN`），每条 `href` 指向解析后的具体锚点实例。

## 测试

```bash
python3 -m unittest discover -s tests        # 单元测试 + 规模验收
python3 -m unittest tests.test_scale -v      # 仅规模验收（记录耗时与峰值内存）
```

规模验收：2000 主题、500 片段、32 层嵌套，展开后 20 万元素 / 5 万锚点 / 10 万链接，
闭式校验全部 id 唯一与链接目标身份。本机实测约 3 秒、Python 峰值内存约 144 MiB
（限 15 秒 / 512 MiB）。
