"""docpub 单元测试：命名空间、遮蔽、条件过滤与链接归属。"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from docpub import PublishError, publish  # noqa: E402
from docpub.expand import expand_project  # noqa: E402
from docpub.loader import load_project  # noqa: E402
from docpub.resolve import resolve_links  # noqa: E402


class PublishCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_publish(self, project):
        ppath = os.path.join(self.tmp, "project.json")
        with open(ppath, "w", encoding="utf-8") as fh:
            json.dump(project, fh)
        out = publish(ppath, os.path.join(self.tmp, "out"))
        with open(out, encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def parse(html):
        """返回 (anchors, links)：anchors={元素文本: id}，links=[(链接文本, 目标id)]。"""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(html.split("\n", 1)[1])  # 去掉 <!DOCTYPE html>
        anchors, links = {}, []
        for el in root.iter():
            text = (el.text or "").strip()
            if "id" in el.attrib:
                anchors[text] = el.attrib["id"]
            if el.tag == "a" and el.attrib.get("href", "").startswith("#"):
                links.append((text, el.attrib["href"][1:]))
        return anchors, links

    def test_repeated_snippet_independent_namespaces(self):
        """同一片段在同一主题插入两次：各自 #top 落到各自副本。"""
        html = self.run_publish({
            "name": "d", "tags": [],
            "topics": [{"id": "t", "title": "T", "body":
                '<include name="s"/><include name="s"/>'}],
            "snippets": [{"name": "s", "body":
                '<p id="top">S</p><a href="#top">up</a>'}],
        })
        anchors, links = self.parse(html)
        self.assertEqual(len(links), 2)
        # 两条链接分别指向两个不同的锚点实例，且按文档顺序落在各自副本上
        self.assertNotEqual(links[0][1], links[1][1])
        self.assertEqual(links[0][1], "a1")
        self.assertEqual(links[1][1], "a2")

    def test_nested_include_resolves_innermost(self):
        """嵌套插入：内层片段的同名声明遮蔽外层。"""
        html = self.run_publish({
            "name": "d", "tags": [],
            "topics": [{"id": "t", "title": "T", "body":
                '<p id="x">topic-x</p><include name="mid"/>'}],
            "snippets": [
                {"name": "mid", "body":
                    '<p id="x">mid-x</p><include name="leaf"/><a href="#x">m</a>'},
                {"name": "leaf", "body":
                    '<p id="x">leaf-x</p><a href="#x">l</a>'},
            ],
        })
        anchors, links = self.parse(html)
        # leaf 的链接指向 leaf 自己的 x；mid 的链接指向 mid 的 x
        by_text = dict(links)
        self.assertEqual(by_text["l"], anchors["leaf-x"])
        self.assertEqual(by_text["m"], anchors["mid-x"])

    def test_forward_reference_and_cross_topic(self):
        """前向引用 + 跨主题同名锚点：topic:T#x 落到 T 自身声明。"""
        html = self.run_publish({
            "name": "d", "tags": [],
            "topics": [
                {"id": "t1", "title": "T1", "body":
                    '<a href="#later">fwd</a><a href="topic:t2#x">cross</a>'
                    '<p id="later">L</p>'},
                {"id": "t2", "title": "T2", "body":
                    '<p id="x">t2-own</p><include name="s"/>'},
            ],
            "snippets": [{"name": "s", "body": '<p id="x">t2-snippet</p>'}],
        })
        anchors, links = self.parse(html)
        by_text = dict(links)
        self.assertEqual(by_text["fwd"], anchors["L"])
        self.assertEqual(by_text["cross"], anchors["t2-own"])

    def test_shadowed_filtered_target_fails(self):
        """内层同名目标被过滤：链接判失效，发布失败，且错误可定位。"""
        with self.assertRaises(PublishError) as ctx:
            self.run_publish({
                "name": "d", "tags": [],
                "topics": [{"id": "t1", "title": "T1", "body":
                    '<p id="x">outer</p><include name="s"/>'}],
                "snippets": [{"name": "s", "body":
                    '<when tag="mac"><p id="x">inner</p></when>'
                    '<a href="#x">go</a>'}],
            })
        msg = str(ctx.exception)
        self.assertIn("t1", msg)
        self.assertIn("s", msg)  # 片段插入位置

    def test_filtered_link_not_checked(self):
        """链接本身也被过滤：不参与检查，发布成功。"""
        html = self.run_publish({
            "name": "d", "tags": [],
            "topics": [{"id": "t1", "title": "T1", "body":
                '<p id="x">outer</p><include name="s"/>'}],
            "snippets": [{"name": "s", "body":
                '<when tag="mac"><p id="x">inner</p>'
                '<a href="#x">go</a></when>'}],
        })
        self.assertIn("outer", html)
        self.assertNotIn("go", html)

    def test_nested_conditions_all_required(self):
        """嵌套条件必须全部满足。"""
        html = self.run_publish({
            "name": "d", "tags": ["a"],
            "topics": [{"id": "t", "title": "T", "body":
                '<when tag="a"><when tag="b"><p>need-both</p></when>'
                '<p>need-a</p></when>'}],
            "snippets": [],
        })
        self.assertIn("need-a", html)
        self.assertNotIn("need-both", html)

    def test_all_ids_globally_unique(self):
        html = self.run_publish({
            "name": "d", "tags": [],
            "topics": [{"id": f"t{i}", "title": f"T{i}", "body":
                '<p id="x">a</p><include name="s"/>'} for i in range(5)],
            "snippets": [{"name": "s", "body": '<p id="x">b</p>'}],
        })
        ids = re.findall(r'id="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)))

    def test_declaration_order_irrelevant(self):
        """链接归属不受声明先后顺序影响（链接可在目标之前）。"""
        body_a = '<a href="#x">g</a><p id="x">target</p>'
        body_b = '<p id="x">target</p><a href="#x">g</a>'
        htmls = [self.run_publish({
            "name": "d", "tags": [],
            "topics": [{"id": "t", "title": "T", "body": body}],
            "snippets": [],
        }) for body in (body_a, body_b)]
        for html in htmls:
            anchors, links = self.parse(html)
            self.assertEqual(dict(links)["g"], anchors["target"])

    def test_broken_link_fails_and_writes_nothing(self):
        out_dir = os.path.join(self.tmp, "out")
        ppath = os.path.join(self.tmp, "project.json")
        with open(ppath, "w") as fh:
            json.dump({
                "name": "d", "tags": [],
                "topics": [{"id": "t", "title": "T",
                            "body": '<a href="#nope">x</a>'}],
                "snippets": [],
            }, fh)
        with self.assertRaises(PublishError):
            publish(ppath, out_dir)
        self.assertFalse(os.path.exists(os.path.join(out_dir, "index.html")))

    def test_loader_rejects_cycles_and_duplicates(self):
        def load(data):
            p = os.path.join(self.tmp, "p.json")
            with open(p, "w") as fh:
                json.dump(data, fh)
            return load_project(p)
        with self.assertRaises(PublishError):
            load({"topics": [], "snippets": [
                {"name": "a", "body": '<include name="b"/>'},
                {"name": "b", "body": '<include name="a"/>'}]})
        with self.assertRaises(PublishError):
            load({"topics": [{"id": "t", "body": ""},
                             {"id": "t", "body": ""}], "snippets": []})
        with self.assertRaises(PublishError):
            load({"topics": [], "snippets": [
                {"name": "s", "body": '<include name="ghost"/>'}]})


if __name__ == "__main__":
    unittest.main()
