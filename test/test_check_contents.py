#!/usr/bin/env python3
"""Unit tests for script/check-contents.py using synthetic fixture trees."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_contents",
    Path(__file__).resolve().parent.parent / "script" / "check-contents.py",
)
cc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cc)


def make_doc(sections, lines=400, with_contents=True):
    """Build a document body with a Purpose, a Contents table, and H2 sections."""
    doc = ["# Doc", "", "## Purpose", "", "Scope.", ""]
    if with_contents:
        doc += ["## Contents", ""]
        doc += cc.format_table(
            ["Section", "What it covers"], [[s, "x"] for s in sections]
        )
        doc += [""]
    for s in sections:
        doc += [f"## {s}", "", "Body.", ""]
    while len(doc) < lines:
        doc.append("pad")
    return doc


class TempTree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, lines):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_clean_tree_passes(self):
        self.write("system/doc.md", make_doc(["Alpha", "Beta"]))
        self.assertEqual(cc.main([str(self.root)]), 0)

    def test_missing_contents_flagged(self):
        self.write("system/doc.md", make_doc(["Alpha"], with_contents=False))
        self.assertEqual(cc.main([str(self.root)]), 1)

    def test_dangling_entry_flagged(self):
        doc = make_doc(["Alpha"])
        i = next(k for k, l in enumerate(doc) if l.startswith("| Alpha"))
        doc.insert(i + 1, "| Ghost   | x              |")
        self.write("system/doc.md", doc)
        self.assertEqual(cc.main([str(self.root)]), 1)

    def test_legacy_three_column_fixed(self):
        doc = make_doc(["Alpha"])
        for i, l in enumerate(doc):
            if l.startswith("| Section"):
                doc[i] = "| Section   | Line | What it covers |"
                doc[i + 1] = "|-----------|------|----------------|"
            elif l.startswith("| Alpha"):
                doc[i] = "| Alpha     | 40   | x              |"
        path = self.write("system/doc.md", doc)
        self.assertEqual(cc.main(["--fix", str(self.root)]), 1)
        text = path.read_text()
        self.assertIn("| Section ", text)
        self.assertNotIn("| Line ", text)
        self.assertEqual(cc.main([str(self.root)]), 0)

    def test_large_file_table_refresh(self):
        self.write("system/big.md", make_doc(["Alpha"], lines=400))
        skill = ["---", "name: x", "---", "", "# X", "",
                 "## " + cc.LARGE_FILE_HEADING, "", "Note.", "",
                 "| File | Lines |", "|------|-------|", ""]
        path = self.write("SKILL.md", skill)
        cc.main(["--fix", str(self.root)])
        text = path.read_text()
        self.assertIn("`system/big.md`", text)
        self.assertIn("~400", text)


if __name__ == "__main__":
    unittest.main()
