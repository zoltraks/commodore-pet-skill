# Agent Instructions

## Purpose

> **Scope:** Agent-facing entry point for authoring and maintaining this skill repository.
> **Key items:** governing documents, boundaries, local workspace, validation, improvement.

This repository is the Commodore PET skill, an Agent Skills package for Commodore PET 3032 6502 assembly programming, hardware reference, and DASM code examples.

`SKILL.md` is the runtime router read by agents that use the skill.

This file is the entry point for agents that modify the skill.

## Governing Documents

| Document   | Owns                                                            |
|------------|-----------------------------------------------------------------|
| `STYLE.md` | Prose, tables, headings, and encoding for the skill's documents |

Keep each rule in its owning document and link to it instead of duplicating it.

## Boundaries

- Keep `SKILL.md` lean: it routes to topic files and stays below 500 lines.
- Register every new or renamed file in `SKILL.md` (topic table plus routing row) and mirror it in the `README.md` tree.
- Directory names use a single lowercase word in singular form: `system/`, `code/`, `script/`, `test/`.
- File names use one lowercase word or kebab-case: `cpu.md`, `dasm-assembler.md`.
- Follow `STYLE.md` for every document: one sentence per paragraph, tables aligned by source width, the required Purpose section, and a Contents table in files over 300 lines.
- Topic files follow the four-layer structure: quick-lookup table, reference tables, working code examples, deep reference notes.
- Hardware facts stay PET 3032 specific - never substitute C64 addresses or conventions.
- Bump `metadata.version` in `SKILL.md` by one patch with every change set, at most once between commits.
- Do not claim validation that did not run.
- Never commit automatically - propose a one-sentence commit message.

## Local Workspace

Scratch and throwaway artifacts live in the gitignored `work/` directory.

Shipped files never depend on workspace content.

## Validation

Run the maintenance checks before proposing a change:

    python3 script/check-contents.py .
    git diff --check

`check-contents.py` verifies that every Contents entry resolves to a heading, every file over 300 lines carries the table, and the SKILL.md large-file table matches reality. Run it with `--fix` to repair counts and table padding.

Changes that alter skill behavior also exercise the regression prompts in `test/evals/evals.json`.

## Skill Improvement

Improvements to this skill follow the boundaries above: analysis and proposals first, files change on an explicit, confirmed instruction.
