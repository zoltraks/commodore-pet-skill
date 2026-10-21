#!/usr/bin/env python3
"""Check Contents navigation tables in skill documents.

Verifies the navigation-table rules in STYLE.md:

- every Markdown file over 300 lines carries a `## Contents` table
- every row in a `## Contents` table names an existing ## or ### heading
  in the same file
- the large-file table in SKILL.md lists every topic file over 300 lines
  with its approximate size
- table cells are padded to the column width and the separator row
  matches the column width plus two hyphens

Usage:

    python3 script/check-contents.py [PATH]
    python3 script/check-contents.py --fix [PATH]

PATH defaults to the repository root containing this script.
Without --fix the tool is read-only: it reports issues and exits 1 when
any are found. With --fix it repairs what is mechanical - legacy `Line`
columns are dropped from Contents tables, large-file counts and rows are
refreshed, tables are re-padded - then reports the remaining issues for
manual repair. It never invents sections, rows, or headings.

Exit status: 0 when no issues remain, 1 otherwise.
"""

import os
import re
import sys
from pathlib import Path

HEADING_RE = re.compile(r"^(#{2,3})\s+(\S.*?)\s*$")
FENCE_RE = re.compile(r"^\s*```")
SEPARATOR_CELL_RE = re.compile(r"^-+$")
LARGE_FILE_LIMIT = 300
SKIP_DIRS = {"work", "node_modules", "__pycache__"}
LARGE_FILE_HEADING = "Note on Large Reference Files"


def find_root():
    return Path(__file__).resolve().parent.parent


def iter_markdown(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS
        )
        for name in sorted(filenames):
            if name.endswith(".md"):
                yield Path(dirpath) / name


def body_lines(path):
    """Return (lines, fence_flags): fence_flags[i] is True for lines inside a code fence."""
    lines = path.read_text(encoding="utf-8").splitlines()
    flags = []
    in_fence = False
    for line in lines:
        if FENCE_RE.match(line):
            flags.append(True)
            in_fence = not in_fence
            continue
        flags.append(in_fence)
    return lines, flags


def heading_map(lines, flags):
    """Map heading text -> 1-based line number for ## and ### headings outside fences."""
    out = {}
    contents_at = None
    for i, (line, fenced) in enumerate(zip(lines, flags)):
        if fenced:
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        name = m.group(2).strip()
        out.setdefault(name, i + 1)
        if m.group(1) == "##" and name == "Contents" and contents_at is None:
            contents_at = i
    return out, contents_at


def table_block(lines, flags, start):
    """Return (start, end) line indexes of the first table block after `start`, or None.

    Scans forward past prose and blank lines, stopping at the next heading.
    """
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if not fenced(flags, i) and line.lstrip().startswith("|"):
            break
        if not fenced(flags, i) and HEADING_RE.match(line):
            return None
        i += 1
    if i >= len(lines):
        return None
    end = i
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    if any(flags[i:end]):
        return None
    return (i, end)


def fenced(flags, i):
    return flags[i]


def parse_cells(row):
    cells = row.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def is_separator(cells):
    return all(SEPARATOR_CELL_RE.match(c) for c in cells)


def format_table(header, data_rows):
    ncols = len(header)
    widths = [len(h) for h in header]
    for row in data_rows:
        for c in range(ncols):
            widths[c] = max(widths[c], len(row[c]) if c < len(row) else 0)

    def fmt(row):
        return "| " + " | ".join(
            (row[c] if c < len(row) else "").ljust(widths[c]) for c in range(ncols)
        ) + " |"

    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    return [fmt(header), sep] + [fmt(r) for r in data_rows]


def round10(n):
    return int(round(n / 10.0)) * 10


def check_contents_table(rel, lines, flags, contents_at, headings, fix):
    issues = []
    block = table_block(lines, flags, contents_at)
    if block is None:
        return [f"{rel}: '## Contents' section has no table"], None
    start, end = block
    rows = [parse_cells(l) for l in lines[start:end]]
    if len(rows) < 2 or not is_separator(rows[1]):
        return [f"{rel}:{start + 1}: Contents table has no separator row"], None
    header, data = rows[0], rows[2:]
    legacy = len(header) == 3 and header[1] == "Line"
    if header not in (["Section", "What it covers"], ["Section", "Line", "What it covers"]):
        return [f"{rel}:{start + 1}: unexpected Contents table header"], None
    for row in data:
        if row and row[0] not in headings:
            issues.append(
                f"{rel}:{start + 1}: Contents row '{row[0]}' resolves to no ## or ### heading"
            )
    if legacy:
        issues.append(f"{rel}:{start + 1}: legacy three-column Contents table")
    new_header = ["Section", "What it covers"]
    new_data = [[r[0], r[2] if legacy and len(r) > 2 else (r[1] if len(r) > 1 else "")] for r in data]
    rebuilt = format_table(new_header, new_data)
    if lines[start:end] != rebuilt:
        issues.append(f"{rel}:{start + 1}: Contents table needs reformatting")
        if fix:
            lines[start:end] = rebuilt
    return issues, (start, end)


def large_file_rows(root):
    """Expected rows for the SKILL.md large-file table: topic files over the limit."""
    rows = []
    for path in iter_markdown(root):
        if path.parent == root:
            continue
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > LARGE_FILE_LIMIT:
            rel = path.relative_to(root).as_posix()
            rows.append((rel, count))
    rows.sort(key=lambda r: -r[1])
    return rows


def check_large_file_table(root, lines, flags, fix):
    issues = []
    idx = None
    for i, (line, fenced) in enumerate(zip(lines, flags)):
        if not fenced and HEADING_RE.match(line) and HEADING_RE.match(line).group(2).strip() == LARGE_FILE_HEADING:
            idx = i
            break
    if idx is None:
        return ["SKILL.md: no 'Note on Large Reference Files' section"], None
    block = table_block(lines, flags, idx)
    if block is None:
        return ["SKILL.md: large-file section has no table"], None
    start, end = block
    rows = [parse_cells(l) for l in lines[start:end]]
    if len(rows) < 2 or rows[0] != ["File", "Lines"]:
        issues.append("SKILL.md: unexpected large-file table header")
    data = rows[2:]
    expected = large_file_rows(root)
    have = {r[0].strip("`"): r for r in data}
    for rel, count in expected:
        row = have.get(rel)
        if row is None:
            issues.append(f"SKILL.md: large-file table missing row for `{rel}`")
        elif row[1] != f"~{round10(count)}":
            issues.append(
                f"SKILL.md: `{rel}` count {row[1]} should be ~{round10(count)}"
            )
    expected_names = [rel for rel, _ in expected]
    for r in data:
        if r[0].strip("`") not in expected_names:
            issues.append(f"SKILL.md: large-file row `{r[0].strip('`')}` lists a file under the limit")
    rebuilt = format_table(
        ["File", "Lines"], [[f"`{rel}`", f"~{round10(c)}"] for rel, c in expected]
    )
    if lines[start:end] != rebuilt:
        if not any("large-file" in i for i in issues):
            issues.append("SKILL.md: large-file table needs reformatting")
        if fix:
            lines[start:end] = rebuilt
    return issues, (start, end)


def main(argv):
    fix = "--fix" in argv
    args = [a for a in argv if not a.startswith("--")]
    root = Path(args[0]).resolve() if args else find_root()
    issues = []
    for path in sorted(iter_markdown(root)):
        rel = path.relative_to(root).as_posix()
        lines, flags = body_lines(path)
        headings, contents_at = heading_map(lines, flags)
        if len(lines) > LARGE_FILE_LIMIT and contents_at is None:
            issues.append(f"{rel}: {len(lines)} lines and no ## Contents table")
        if contents_at is not None:
            found, _ = check_contents_table(rel, lines, flags, contents_at, headings, fix)
            issues.extend(found)
        if path.name == "SKILL.md":
            found, _ = check_large_file_table(root, lines, flags, fix)
            issues.extend(found)
        if fix:
            new_text = "\n".join(lines) + "\n"
            if new_text != path.read_text(encoding="utf-8"):
                path.write_text(new_text, encoding="utf-8")
                print(f"fixed {rel}")
    for i in issues:
        print(i)
    print(f"{len(issues)} issue(s) found")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
