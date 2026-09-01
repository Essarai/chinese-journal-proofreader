#!/usr/bin/env python3
"""Add native Word comments anchored to exact text ranges in a DOCX.

Ledger format:
[
  {
    "anchor": "unique text identifying the paragraph or table cell",
    "target": "smallest exact text span to highlight",
    "comment": "【文字】Actionable review comment.",
    "occurrence": 1,
    "anchor_occurrence": 1
  }
]
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import zipfile
from pathlib import Path

from lxml import etree


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W, "pr": PKG_REL, "ct": CT}


def qn(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def xml_bytes(root: etree._Element) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")


def paragraph_text(paragraph: etree._Element) -> str:
    return "".join(paragraph.xpath(".//w:t/text() | .//w:delText/text()", namespaces=NS))


def text_nodes(paragraph: etree._Element) -> list[etree._Element]:
    return paragraph.xpath(".//w:t | .//w:delText", namespaces=NS)


def ancestor_run(node: etree._Element) -> etree._Element:
    current = node
    while current is not None and current.tag != qn(W, "r"):
        current = current.getparent()
    if current is None:
        raise RuntimeError("Text node is not inside a Word run")
    return current


def set_text(node: etree._Element, value: str) -> None:
    node.text = value
    if value.startswith(" ") or value.endswith(" "):
        node.set(qn(XML, "space"), "preserve")
    else:
        node.attrib.pop(qn(XML, "space"), None)


def split_run_at_node(run: etree._Element, node: etree._Element, offset: int) -> None:
    """Split a run at an offset inside a direct w:t/w:delText child."""
    if node.getparent() is not run:
        raise RuntimeError("Precise comment boundary falls inside a complex nested run")
    value = node.text or ""
    if offset <= 0 or offset >= len(value):
        return

    payload = [child for child in run if child.tag != qn(W, "rPr")]
    if len(payload) != 1 or payload[0] is not node:
        raise RuntimeError(
            "Precise comment boundary falls inside a compound run; use a smaller target "
            "or normalize that paragraph before adding comments"
        )
    left = copy.deepcopy(run)
    right = copy.deepcopy(run)
    left_nodes = left.xpath("./w:t | ./w:delText", namespaces=NS)
    if not left_nodes:
        raise RuntimeError("Could not preserve the left side of a split run")
    set_text(left_nodes[0], value[:offset])
    right_nodes = right.xpath("./w:t | ./w:delText", namespaces=NS)
    if not right_nodes:
        raise RuntimeError("Could not preserve the right side of a split run")
    set_text(right_nodes[0], value[offset:])

    parent = run.getparent()
    position = parent.index(run)
    parent.remove(run)
    parent.insert(position, left)
    parent.insert(position + 1, right)


def split_at(paragraph: etree._Element, position: int) -> None:
    if position <= 0 or position >= len(paragraph_text(paragraph)):
        return
    cursor = 0
    for node in text_nodes(paragraph):
        value = node.text or ""
        next_cursor = cursor + len(value)
        if cursor < position < next_cursor:
            split_run_at_node(ancestor_run(node), node, position - cursor)
            return
        cursor = next_cursor


def run_at_character(paragraph: etree._Element, position: int) -> etree._Element:
    cursor = 0
    for node in text_nodes(paragraph):
        value = node.text or ""
        if cursor <= position < cursor + len(value):
            return ancestor_run(node)
        cursor += len(value)
    raise RuntimeError(f"No run found at character position {position}")


def ensure_comments_root(existing: bytes | None) -> etree._Element:
    if existing is not None:
        return etree.fromstring(existing)
    return etree.Element(qn(W, "comments"), nsmap={"w": W})


def next_comment_id(comments: etree._Element, document: etree._Element) -> int:
    used: set[int] = set()
    for node in comments.xpath(".//w:comment", namespaces=NS) + document.xpath(
        ".//w:commentRangeStart | .//w:commentRangeEnd | .//w:commentReference",
        namespaces=NS,
    ):
        try:
            used.add(int(node.get(qn(W, "id"))))
        except (TypeError, ValueError):
            pass
    candidate = 0
    while candidate in used:
        candidate += 1
    return candidate


def ensure_package_wiring(content_types: etree._Element, rels: etree._Element) -> None:
    if not content_types.xpath(
        "//*[local-name()='Override' and @PartName='/word/comments.xml']"
    ):
        override = etree.SubElement(content_types, qn(CT, "Override"))
        override.set("PartName", "/word/comments.xml")
        override.set(
            "ContentType",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
        )

    rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
    if any(rel.get("Type") == rel_type for rel in rels.xpath(".//pr:Relationship", namespaces=NS)):
        return
    ids = []
    for rel in rels.xpath(".//pr:Relationship", namespaces=NS):
        match = re.fullmatch(r"rId(\d+)", rel.get("Id", ""))
        if match:
            ids.append(int(match.group(1)))
    relation = etree.SubElement(rels, qn(PKG_REL, "Relationship"))
    relation.set("Id", f"rId{max(ids, default=0) + 1}")
    relation.set("Type", rel_type)
    relation.set("Target", "comments.xml")


def nth_start(text: str, target: str, occurrence: int) -> int:
    if occurrence < 1:
        raise ValueError("occurrence must be at least 1")
    start = -1
    cursor = 0
    for _ in range(occurrence):
        start = text.find(target, cursor)
        if start < 0:
            return -1
        cursor = start + len(target)
    return start


def add_comment(
    document: etree._Element,
    comments: etree._Element,
    item: dict,
    author: str,
) -> tuple[int, str]:
    anchor = item["anchor"]
    target = item["target"]
    comment_text = item["comment"]
    anchor_occurrence = int(item.get("anchor_occurrence", 1))
    target_occurrence = int(item.get("occurrence", 1))

    matches = [p for p in document.xpath(".//w:p", namespaces=NS) if anchor in paragraph_text(p)]
    if len(matches) < anchor_occurrence:
        raise RuntimeError(
            f"Anchor not found at occurrence {anchor_occurrence}: {anchor!r} (matches={len(matches)})"
        )
    paragraph = matches[anchor_occurrence - 1]
    full_text = paragraph_text(paragraph)
    start = nth_start(full_text, target, target_occurrence)
    if start < 0:
        raise RuntimeError(
            f"Target not found at occurrence {target_occurrence}: {target!r} within anchor {anchor!r}"
        )
    end = start + len(target)

    # Split from right to left so the first boundary's character position stays stable.
    split_at(paragraph, end)
    split_at(paragraph, start)
    start_run = run_at_character(paragraph, start)
    end_run = run_at_character(paragraph, end - 1)
    start_parent = start_run.getparent()
    end_parent = end_run.getparent()

    comment_id = next_comment_id(comments, document)
    range_start = etree.Element(qn(W, "commentRangeStart"))
    range_start.set(qn(W, "id"), str(comment_id))
    start_parent.insert(start_parent.index(start_run), range_start)

    range_end = etree.Element(qn(W, "commentRangeEnd"))
    range_end.set(qn(W, "id"), str(comment_id))
    end_parent.insert(end_parent.index(end_run) + 1, range_end)
    reference_run = etree.Element(qn(W, "r"))
    reference = etree.SubElement(reference_run, qn(W, "commentReference"))
    reference.set(qn(W, "id"), str(comment_id))
    end_parent.insert(end_parent.index(range_end) + 1, reference_run)

    comment = etree.SubElement(comments, qn(W, "comment"))
    comment.set(qn(W, "id"), str(comment_id))
    comment.set(qn(W, "author"), author)
    comment.set(qn(W, "date"), dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    p = etree.SubElement(comment, qn(W, "p"))
    r = etree.SubElement(p, qn(W, "r"))
    t = etree.SubElement(r, qn(W, "t"))
    set_text(t, comment_text)
    return comment_id, target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--author", default="Codex审校")
    args = parser.parse_args()

    items = json.loads(args.ledger.read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise SystemExit("Ledger must be a non-empty JSON list")

    with zipfile.ZipFile(args.input) as source:
        document = etree.fromstring(source.read("word/document.xml"))
        comments = ensure_comments_root(
            source.read("word/comments.xml") if "word/comments.xml" in source.namelist() else None
        )
        content_types = etree.fromstring(source.read("[Content_Types].xml"))
        rels_name = "word/_rels/document.xml.rels"
        rels = etree.fromstring(source.read(rels_name))
        ensure_package_wiring(content_types, rels)

        applied = []
        for item in items:
            if not all(key in item and str(item[key]) for key in ("anchor", "target", "comment")):
                raise RuntimeError(f"Ledger item lacks anchor, target, or comment: {item!r}")
            applied.append(add_comment(document, comments, item, args.author))

        overrides = {
            "word/document.xml": xml_bytes(document),
            "word/comments.xml": xml_bytes(comments),
            "[Content_Types].xml": xml_bytes(content_types),
            rels_name: xml_bytes(rels),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as output:
            for info in source.infolist():
                if info.filename in overrides:
                    output.writestr(info, overrides[info.filename])
                else:
                    output.writestr(info, source.read(info.filename))
            if "word/comments.xml" not in source.namelist():
                output.writestr("word/comments.xml", overrides["word/comments.xml"])

    print(f"PASS: added {len(applied)} precise comments to {args.out}")
    for comment_id, target in applied:
        print(f"  id={comment_id} target={target!r}")


if __name__ == "__main__":
    main()
