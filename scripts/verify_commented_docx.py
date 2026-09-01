#!/usr/bin/env python3
"""Verify that a comment-only DOCX review preserved manuscript content."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from lxml import etree


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"w": W, "pr": PR}


def w(tag: str) -> str:
    return f"{{{W}}}{tag}"


def read_xml(path: Path, member: str) -> etree._Element | None:
    with ZipFile(path) as archive:
        if member not in archive.namelist():
            return None
        return etree.fromstring(archive.read(member))


def visible_text(root: etree._Element | None) -> str:
    if root is None:
        return ""
    return "".join(root.xpath(".//w:t/text() | .//w:delText/text()", namespaces=NS))


def scrub_comment_markup(root: etree._Element) -> bytes:
    cleaned = copy.deepcopy(root)
    for node in cleaned.xpath(".//w:commentRangeStart | .//w:commentRangeEnd", namespaces=NS):
        node.getparent().remove(node)
    for ref in cleaned.xpath(".//w:commentReference", namespaces=NS):
        run = ref.getparent()
        run.remove(ref)
        if len(run) == 0 and not (run.text or "").strip():
            run.getparent().remove(run)
    merge_adjacent_equivalent_text_runs(cleaned)
    return etree.tostring(cleaned, method="c14n")


def run_signature(run: etree._Element) -> tuple[bytes, str] | None:
    payload = [child for child in run if child.tag != w("rPr")]
    if len(payload) != 1 or payload[0].tag not in (w("t"), w("delText")):
        return None
    rpr = run.find("w:rPr", namespaces=NS)
    signature = b"" if rpr is None else etree.tostring(rpr, method="c14n")
    return signature, payload[0].tag


def merge_adjacent_equivalent_text_runs(root: etree._Element) -> None:
    for parent in root.iter():
        index = 0
        while index + 1 < len(parent):
            left = parent[index]
            right = parent[index + 1]
            if left.tag != w("r") or right.tag != w("r"):
                index += 1
                continue
            left_sig = run_signature(left)
            right_sig = run_signature(right)
            if left_sig is None or left_sig != right_sig:
                index += 1
                continue
            left_text = next(child for child in left if child.tag != w("rPr"))
            right_text = next(child for child in right if child.tag != w("rPr"))
            left_text.text = (left_text.text or "") + (right_text.text or "")
            if (left_text.text or "").startswith(" ") or (left_text.text or "").endswith(" "):
                left_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            else:
                left_text.attrib.pop("{http://www.w3.org/XML/1998/namespace}space", None)
            parent.remove(right)


def anchored_text_by_id(document: etree._Element) -> dict[str, str]:
    active: list[str] = []
    captured: dict[str, list[str]] = {}
    for node in document.iter():
        if node.tag == w("commentRangeStart"):
            comment_id = node.get(w("id"))
            if comment_id is not None:
                active.append(comment_id)
                captured.setdefault(comment_id, [])
        elif node.tag in (w("t"), w("delText")):
            for comment_id in active:
                captured.setdefault(comment_id, []).append(node.text or "")
        elif node.tag == w("commentRangeEnd"):
            comment_id = node.get(w("id"))
            if comment_id in active:
                active.remove(comment_id)
    return {comment_id: "".join(parts) for comment_id, parts in captured.items()}


def count_comments(path: Path) -> int:
    root = read_xml(path, "word/comments.xml")
    return 0 if root is None else len(root.xpath(".//w:comment", namespaces=NS))


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("reviewed", type=Path)
    parser.add_argument("--expected-new-comments", type=int)
    parser.add_argument("--ledger", type=Path, help="JSON ledger used to verify exact anchored ranges")
    args = parser.parse_args()

    try:
        with ZipFile(args.source) as archive:
            bad = archive.testzip()
            if bad:
                fail(f"source ZIP member is corrupt: {bad}")
        with ZipFile(args.reviewed) as archive:
            bad = archive.testzip()
            if bad:
                fail(f"reviewed ZIP member is corrupt: {bad}")
    except (BadZipFile, FileNotFoundError) as exc:
        fail(str(exc))

    source_doc = read_xml(args.source, "word/document.xml")
    reviewed_doc = read_xml(args.reviewed, "word/document.xml")
    if source_doc is None or reviewed_doc is None:
        fail("word/document.xml is missing")

    if visible_text(source_doc) != visible_text(reviewed_doc):
        fail("visible main-document text changed")
    if scrub_comment_markup(source_doc) != scrub_comment_markup(reviewed_doc):
        fail("document structure changed beyond native comment markup")

    for member in (
        "word/footnotes.xml",
        "word/endnotes.xml",
        "word/header1.xml",
        "word/footer1.xml",
    ):
        if visible_text(read_xml(args.source, member)) != visible_text(read_xml(args.reviewed, member)):
            fail(f"visible text changed in {member}")

    source_changes = Counter(
        {
            "ins": len(source_doc.xpath(".//w:ins", namespaces=NS)),
            "del": len(source_doc.xpath(".//w:del", namespaces=NS)),
        }
    )
    reviewed_changes = Counter(
        {
            "ins": len(reviewed_doc.xpath(".//w:ins", namespaces=NS)),
            "del": len(reviewed_doc.xpath(".//w:del", namespaces=NS)),
        }
    )
    if source_changes != reviewed_changes:
        fail("tracked-change count changed")

    comments = read_xml(args.reviewed, "word/comments.xml")
    if comments is None:
        fail("word/comments.xml is missing")

    comment_ids = [node.get(w("id")) for node in comments.xpath(".//w:comment", namespaces=NS)]
    start_ids = [node.get(w("id")) for node in reviewed_doc.xpath(".//w:commentRangeStart", namespaces=NS)]
    end_ids = [node.get(w("id")) for node in reviewed_doc.xpath(".//w:commentRangeEnd", namespaces=NS)]
    ref_ids = [node.get(w("id")) for node in reviewed_doc.xpath(".//w:commentReference", namespaces=NS)]
    if Counter(comment_ids) != Counter(start_ids) or Counter(comment_ids) != Counter(end_ids) or Counter(comment_ids) != Counter(ref_ids):
        fail("comment IDs do not have matching start, end, and reference elements")

    source_comment_count = count_comments(args.source)
    new_comment_count = len(comment_ids) - source_comment_count
    if args.expected_new_comments is not None and new_comment_count != args.expected_new_comments:
        fail(
            f"expected {args.expected_new_comments} new comments, found {new_comment_count} "
            f"(source={source_comment_count}, reviewed={len(comment_ids)})"
        )

    if args.ledger is not None:
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        source_comments = read_xml(args.source, "word/comments.xml")
        source_ids = set()
        if source_comments is not None:
            source_ids = {
                node.get(w("id"))
                for node in source_comments.xpath(".//w:comment", namespaces=NS)
            }
        new_ids = [comment_id for comment_id in comment_ids if comment_id not in source_ids]
        if len(new_ids) != len(ledger):
            fail(f"ledger has {len(ledger)} items but reviewed file has {len(new_ids)} new comments")
        anchored = anchored_text_by_id(reviewed_doc)
        for index, (comment_id, item) in enumerate(zip(new_ids, ledger), start=1):
            expected_target = item["target"]
            actual_target = anchored.get(comment_id, "")
            if actual_target != expected_target:
                fail(
                    f"comment {index} (id={comment_id}) anchors {actual_target!r}; "
                    f"expected exact target {expected_target!r}"
                )

    rels = read_xml(args.reviewed, "word/_rels/document.xml.rels")
    if rels is None or not any(
        rel.get("Type", "").endswith("/comments") and rel.get("Target") == "comments.xml"
        for rel in rels.xpath(".//pr:Relationship", namespaces=NS)
    ):
        fail("comments relationship is missing")

    print("PASS: DOCX package integrity verified")
    print("PASS: visible text and non-comment document structure preserved")
    print(f"PASS: comments are structurally complete (source={source_comment_count}, new={new_comment_count}, total={len(comment_ids)})")
    if args.ledger is not None:
        print(f"PASS: all {len(ledger)} comment ranges equal their ledger targets")
    print(f"PASS: tracked changes preserved (insertions={source_changes['ins']}, deletions={source_changes['del']})")


if __name__ == "__main__":
    main()
