# Changelog

## 0.3.1 - 2026-10-21

- Corrected document formatting repo-wide: realigned 81 tables, replaced semicolons in table-cell prose, normalized typographic characters to ASCII, joined wrapped continuation lines to the logical-line convention, and fixed blank-line defects.
- Split the longest multi-sentence warning paragraphs in `system/kernal.md`, `system/file.md`, `example/file.md`, and `code/compression.md`.
- Documented in `STYLE.md` that Unicode glyphs are allowed when they are the subject matter, such as key-cap legends and character-set renderings.

## 0.3.0 - 2026-10-20

- Converted all `## Contents` tables to name-based `| Section | What it covers |` navigation, replacing drift-prone line numbers.
- Added missing Contents tables to `system/keyboard.md`, `hardware/chip.md`, `expansion/petay.md`, and `STYLE.md`.
- Restored the lost `## Reverse Video` section in `system/screen.md`.
- Added `script/check-contents.py` to verify Contents entries, coverage, and the SKILL.md large-file table.
- Added `AGENTS.md`, `.gitignore`, `CHANGELOG.md`, and `test/evals/evals.json`.
- Completed SKILL.md frontmatter: `name` now matches the directory name, plus `license`, `compatibility`, and `metadata.version`.
- Refreshed the README install commands and file tree.
