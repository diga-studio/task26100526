"""规模验收：2000 主题、500 片段、32 层嵌套、20 万元素、5 万锚点、10 万链接。

核对产物全部 id 唯一、链接目标身份正确，并记录耗时与峰值内存。
"""
import json
import re
import resource
import time

from helpdoc import publish

N_TOPICS = 2000
N_CYCLE_SNIPPETS = 468
CHAIN_DEPTH = 32
ANCHORS_PER_TOPIC = 25   # 20 主题自身 + 5 片段
LINKS_PER_TOPIC = 50     # 45 主题自身 + 5 片段
TIME_LIMIT_S = 15
MEM_LIMIT_BYTES = 512 * 1024 * 1024

IDS = re.compile(r'id="(a\d+)"')
HREFS = re.compile(r'href="#(a\d+)"')


def build_project():
    snippets = []
    for n in range(N_CYCLE_SNIPPETS):
        parts = [f'<a href="#s{n}_{k}">sl{k}</a>' for k in range(5)]
        parts += [f'<span id="s{n}_{k}">sa{k}</span>' for k in range(5)]
        snippets.append({"name": f"c{n}", "body": "".join(parts)})
    for d in range(CHAIN_DEPTH):
        nxt = f'<include name="chain{d + 1}"/>' if d + 1 < CHAIN_DEPTH else ""
        snippets.append({"name": f"chain{d}", "body": f"<div>d{d}</div>{nxt}"})

    topics = []
    expected_hrefs = []
    for t in range(N_TOPICS):
        parts = []
        for i in range(45):  # 链接全部在锚点声明之前（前向引用）
            j = (i * 7 + 3) % 20
            parts.append(f'<a href="#x{t}_{j}">l{i}</a>')
            expected_hrefs.append(f"a{t * ANCHORS_PER_TOPIC + j}")
        for j in range(20):
            parts.append(f'<p id="x{t}_{j}">a{j}</p>')
        for k in range(20):
            parts.append(f"<div>plain{k}</div>")
        parts.append('<when tag="on"><span>kept</span></when>')
        parts.append('<when tag="off"><div>dropped</div></when>')
        parts.append(f'<include name="c{t % N_CYCLE_SNIPPETS}"/>')
        for k in range(5):
            expected_hrefs.append(f"a{t * ANCHORS_PER_TOPIC + 20 + k}")
        if t == 0:
            parts.insert(0, '<include name="chain0"/>')
        topics.append({"id": f"t{t}", "title": f"Topic {t}",
                       "body": "".join(parts)})

    return {"tags": ["on"], "topics": topics, "snippets": snippets}, expected_hrefs


def test_publish_at_scale(tmp_path, capsys):
    project, expected_hrefs = build_project()
    snapshot = tmp_path / "project.json"
    snapshot.write_text(json.dumps(project), encoding="utf-8")

    start = time.perf_counter()
    target = publish(snapshot, tmp_path / "out")
    elapsed = time.perf_counter() - start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # macOS: bytes

    html = target.read_text(encoding="utf-8")
    ids = IDS.findall(html)
    hrefs = HREFS.findall(html)

    with capsys.disabled():
        print(f"\n[scale] elements~200k anchors={len(ids)} links={len(hrefs)}")
        print(f"[scale] elapsed={elapsed:.2f}s peak_rss={peak / 1024 / 1024:.0f} MiB")

    assert len(ids) == N_TOPICS * ANCHORS_PER_TOPIC == 50_000
    assert len(set(ids)) == len(ids), "output ids must be globally unique"
    assert ids == [f"a{i}" for i in range(len(ids))]
    assert len(hrefs) == N_TOPICS * LINKS_PER_TOPIC == 100_000
    assert hrefs == expected_hrefs, "every link must land on its expected anchor"
    assert elapsed < TIME_LIMIT_S
    assert peak < MEM_LIMIT_BYTES
