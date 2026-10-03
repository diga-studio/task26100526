"""发布语义测试：命名空间、遮蔽、条件过滤与链接归属。"""
import re

import pytest

from helpdoc import PublishError, load_project
from helpdoc.expand import expand_project
from helpdoc.render import render_document

IDS = re.compile(r'id="(a\d+)"')
HREFS = re.compile(r'href="#(a\d+)"')


def publish_html(project_dict, tags=()):
    project_dict = dict(project_dict)
    project_dict.setdefault("tags", list(tags))
    project = load_project(project_dict)
    return render_document(expand_project(project))


def ids_and_hrefs(html):
    return IDS.findall(html), HREFS.findall(html)


def test_repeated_and_nested_snippet_insertion():
    html = publish_html({
        "snippets": [
            {"name": "s", "body": '<p id="x">s</p><include name="i"/><a href="#x">ls</a>'},
            {"name": "i", "body": '<p id="x">i</p><a href="#x">li</a>'},
        ],
        "topics": [{"id": "T", "body": '<include name="s"/><include name="s"/>'}],
    })
    ids, hrefs = ids_and_hrefs(html)
    assert len(ids) == 4 and len(set(ids)) == 4
    # 每个副本的链接都落在自己副本的锚点上，不跨副本串联
    assert hrefs == [ids[1], ids[0], ids[3], ids[2]]


def test_forward_reference_within_topic():
    html = publish_html({
        "topics": [{"id": "T", "body": '<a href="#x">fwd</a><p id="x">later</p>'}],
    })
    ids, hrefs = ids_and_hrefs(html)
    assert hrefs == [ids[0]]


def test_cross_topic_same_name_anchors():
    html = publish_html({
        "topics": [
            {"id": "A", "body": '<p id="x">ax</p><a href="topic:B#x">to-b</a>'},
            {"id": "B", "body": '<p id="x">bx</p><a href="#x">self</a>'},
        ],
    })
    ids, hrefs = ids_and_hrefs(html)
    assert hrefs == [ids[1], ids[1]]


def test_topic_ref_skips_target_snippets():
    with pytest.raises(PublishError):
        publish_html({
            "snippets": [{"name": "s", "body": '<p id="x">in-snip</p>'}],
            "topics": [
                {"id": "T", "body": '<include name="s"/>'},
                {"id": "U", "body": '<a href="topic:T#x">bad</a>'},
            ],
        })


def test_child_declarations_not_visible_to_parent():
    with pytest.raises(PublishError):
        publish_html({
            "snippets": [{"name": "s", "body": '<p id="x">in-snip</p>'}],
            "topics": [{"id": "T", "body": '<include name="s"/><a href="#x">bad</a>'}],
        })


def test_shadowed_filtered_target_fails_without_fallback():
    project = {
        "tags": [],
        "snippets": [{
            "name": "s",
            "body": ('<when tag="off"><p id="x">gone</p></when>'
                     '<a href="#x">dangling</a>'),
        }],
        "topics": [{"id": "T", "body": '<p id="x">outer</p><include name="s"/>'}],
    }
    with pytest.raises(PublishError):
        publish_html(project)


def test_filtered_link_is_not_checked():
    html = publish_html({
        "tags": [],
        "snippets": [{
            "name": "s",
            "body": ('<when tag="off"><p id="x">gone</p>'
                     '<a href="#x">also-gone</a></when>'),
        }],
        "topics": [{"id": "T", "body": '<p id="x">outer</p><include name="s"/>'}],
    })
    ids, hrefs = ids_and_hrefs(html)
    assert ids == ["a0"] and hrefs == []


def test_unresolved_link_fails():
    with pytest.raises(PublishError):
        publish_html({
            "topics": [{"id": "T", "body": '<a href="#nope">bad</a>'}],
        })


def test_error_location_points_to_snippet_insertion():
    project = {
        "snippets": [
            {"name": "outer", "body": '<include name="inner"/>'},
            {"name": "inner", "body": '<a href="#missing">bad</a>'},
        ],
        "topics": [{"id": "T", "body": '<include name="outer"/>'}],
    }
    with pytest.raises(PublishError) as excinfo:
        publish_html(project)
    location = excinfo.value.location
    assert location.topic_id == "T"
    assert location.include_path == ("outer", "inner")


def test_declaration_order_does_not_change_link_target():
    body = ('<p id="x">first</p><a href="#x">mid</a><p id="y">second</p>'
            '<a href="#x">late</a><a href="#y">back</a>')
    html = publish_html({"topics": [{"id": "T", "body": body}]})
    ids, hrefs = ids_and_hrefs(html)
    assert hrefs == [ids[0], ids[0], ids[1]]
