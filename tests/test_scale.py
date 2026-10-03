"""规模验收：2000 主题、500 片段、32 层嵌套、20 万元素 / 5 万锚点 / 10 万链接。

核对：全部 id 全局唯一、每条链接目标身份正确（闭式校验）、
完整发布 < 15 秒、峰值内存 < 512 MiB。记录耗时与峰值内存。

运行：python3 -m unittest tests.test_scale -v  或  python3 tests/test_scale.py
"""
import json
import os
import resource
import shutil
import sys
import tempfile
import time
import tracemalloc
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from docpub import publish  # noqa: E402

N_TOPICS = 2000
N_SNIPPETS = 500
CHAIN_DEPTH = 32
ANCHORS_PER_TOPIC = 25  # 5 主题级 + 2 份片段副本 x 10
LINKS_PER_TOPIC = 50    # 10 主题级 + 2 份片段副本 x 20
TIME_LIMIT_S = 15.0
MEM_LIMIT_MIB = 512


def build_project():
    snippets = []
    for j in range(N_SNIPPETS):
        parts = [f'<p id="k{m}">s{j}-k{m}</p>' for m in range(10)]
        parts += [f'<a href="#k{m % 10}">lk</a>' for m in range(20)]
        parts += ['<p>pad</p>' for _ in range(10)]
        # 被过滤块：含锚点与一条坏链接，均不应参与检查
        parts.append('<when tag="off"><p id="gone">g</p><a href="#ghost">bad</a></when>')
        snippets.append({"name": f"s{j}", "body": "".join(parts)})
    for d in range(CHAIN_DEPTH):
        body = f'<p>chain-depth-{d + 1}</p>'
        if d + 1 < CHAIN_DEPTH:
            body += f'<include name="chain{d + 1}"/>'
        else:
            body += '<p id="deep-end">end</p><a href="#deep-end">dl</a>'
        snippets.append({"name": f"chain{d}", "body": body})

    topics = []
    for i in range(N_TOPICS):
        nxt = (i + 1) % N_TOPICS
        parts = [f'<p id="own">own-{i}</p>']
        parts += [f'<p id="t{k}">x</p>' for k in range(4)]
        parts += ['<a href="#own">lo</a>' for _ in range(5)]
        parts += [f'<a href="topic:t{nxt}#own">xo</a>' for _ in range(5)]
        parts += ['<p>pad</p>' for _ in range(5)]
        s = f"s{i % N_SNIPPETS}"
        parts.append(f'<include name="{s}"/><include name="{s}"/>')
        if i == N_TOPICS - 1:
            parts.append('<include name="chain0"/>')
        topics.append({"id": f"t{i}", "title": f"Topic {i}", "body": "".join(parts)})

    return {"name": "scale", "tags": [], "topics": topics, "snippets": snippets}


class ScaleCase(unittest.TestCase):
    def test_scale_publish(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        project_path = os.path.join(tmp, "project.json")
        with open(project_path, "w", encoding="utf-8") as fh:
            json.dump(build_project(), fh)

        rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        tracemalloc.start()
        start = time.perf_counter()
        out_path = publish(project_path, os.path.join(tmp, "out"))
        elapsed = time.perf_counter() - start
        _, peak_py = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        mib = 1024 * 1024
        # macOS ru_maxrss 单位为字节，Linux 为 KiB
        rss_unit = 1 if sys.platform == "darwin" else 1024
        print(
            f"\n[scale] elapsed={elapsed:.2f}s "
            f"peak_python={peak_py / mib:.0f} MiB "
            f"ru_maxrss_delta={(rss_after - rss_before) * rss_unit / mib:.0f} MiB "
            f"html={os.path.getsize(out_path) / mib:.1f} MiB"
        )
        self.assertLess(elapsed, TIME_LIMIT_S, "发布超时")
        self.assertLess(peak_py, MEM_LIMIT_MIB * mib, "峰值内存超限")

        # 校验产物：id 全局唯一且按序；每条链接目标身份闭式校验
        with open(out_path, encoding="utf-8") as fh:
            html = fh.read()
        root = ET.fromstring(html.split("\n", 1)[1])
        anchors, links = [], []
        for el in root.iter():
            if "id" in el.attrib:
                anchors.append(el.attrib["id"])
            if el.tag == "a":
                links.append(el.attrib["href"][1:])
        total_anchors = N_TOPICS * ANCHORS_PER_TOPIC + 1
        self.assertEqual(len(anchors), total_anchors)
        self.assertEqual(len(set(anchors)), total_anchors, "id 不唯一")
        self.assertEqual(anchors, [f"a{n}" for n in range(1, total_anchors + 1)])

        self.assertEqual(len(links), N_TOPICS * LINKS_PER_TOPIC + 1)
        for i in range(N_TOPICS):
            base = i * LINKS_PER_TOPIC
            own = f"a{i * ANCHORS_PER_TOPIC + 1}"
            for r in range(5):  # 主题级本地链接
                self.assertEqual(links[base + r], own, f"topic {i} local link {r}")
            nxt_own = f"a{((i + 1) % N_TOPICS) * ANCHORS_PER_TOPIC + 1}"
            for r in range(5, 10):  # 跨主题链接
                self.assertEqual(links[base + r], nxt_own, f"topic {i} cross link {r}")
            for r in range(20):  # 片段副本 1
                want = f"a{i * ANCHORS_PER_TOPIC + 6 + r % 10}"
                self.assertEqual(links[base + 10 + r], want, f"topic {i} copy1 link {r}")
            for r in range(20):  # 片段副本 2
                want = f"a{i * ANCHORS_PER_TOPIC + 16 + r % 10}"
                self.assertEqual(links[base + 30 + r], want, f"topic {i} copy2 link {r}")
        self.assertEqual(links[-1], f"a{total_anchors}")  # 32 层深处的链接
        self.assertIn("chain-depth-32", html)


if __name__ == "__main__":
    unittest.main()
