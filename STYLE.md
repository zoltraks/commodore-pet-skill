# Style Guide

## Purpose

> **Scope:** Formatting rules for all Commodore PET skill documents
> **Key items:** File structure, table alignment, code blocks, address notation, cross-references, adding new files

This document defines the formatting conventions for all files in the commodore-pet-skill.

Follow these rules when adding new files or editing existing ones to keep style uniform across the skill.

## File Header Structure

Every topic file follows this top-to-bottom layout:

1. H1 title -- plain topic name, no subtitle or suffix
2. `## Purpose` section with Purpose blockquote
3. Out-of-scope table -- directly after the blockquote, no heading
4. `## Contents` table -- only for files longer than roughly 200 lines
5. Main content sections (H2 and H3)

### Purpose Section

The Purpose section uses a two-line blockquote:

```markdown
## Purpose

> **Scope:** one-line description of what this file covers
> **Key items:** comma-separated list of key addresses, registers, or concepts
```

### Out-of-Scope Table

Every topic file includes a table directing readers to related files for topics outside its scope.

```markdown
| Out of scope   | See instead        |
|----------------|--------------------|
| Chip registers | `hardware/chip.md` |
| Memory map     | `system/memory.md` |
```

The table has exactly two columns named `Out of scope` and `See instead`.

Put it directly below the Purpose blockquote with no heading between them.

Use backtick code spans around the file path in the `See instead` column.

### Contents Table

Include a Contents table in files longer than roughly 200 lines.

```markdown
## Contents

| Section            | Line | What it covers                          |
|--------------------|------|-----------------------------------------|
| Overview           | 15   | Background and architecture description |
| Register Reference | 80   | Full register map with bit meanings     |
```

The table has exactly three columns: `Section`, `Line`, and `What it covers`.

`Line` is the approximate starting line number of the section.

Update line numbers when sections move significantly.

## Section Headings

Use Title Case for all headings.

Use H2 (`##`) for top-level sections within a file.

Use H3 (`###`) for subsections.

Do not use H4 or deeper.

Do not put qualifiers in parentheses inside headings.

Write qualifiers as plain sentences in the section body instead.

## Tables

Table formatting follows the rules in `/home/desktop/PROJECT/ROOT/ai-dev/docs/TABLE.md`.

The key rules are summarised here.

### Separators

Place the separator row immediately after the header row.

Use hyphens flush against the pipe characters -- no spaces between pipes and hyphens.

The number of hyphens in each separator cell equals the column width plus two (one for each side space).

```markdown
| Name   | Address | Description             |
|--------|---------|-------------------------|
| CHROUT | `$FFD2` | Output byte to channel  |
```

### Column Widths

Calculate column width as the maximum character width of any cell in that column, including the header.

Pad every cell with trailing spaces to match that width.

Remove any padding that exceeds the widest cell -- do not over-pad.

The minimum column width is three characters.

Include backticks, asterisks, and all other Markdown formatting characters in the width measurement.

### Addresses and Values in Tables

Wrap hex addresses and byte values in single backticks: `` `$E840` ``, `` `$FF` ``.

Always use the `$` prefix for hex values.

## Code Blocks

### Language Tag

Use the `asm` language tag on all assembly code blocks.

````markdown
```asm
        lda #$00
```
````

Do not leave a blank line as the first or last line inside a code block.

### Column Layout

Assembly source uses the column positions defined in `utility/dasm-assembler.md`.

| Element                         | Position             |
|---------------------------------|----------------------|
| Labels                          | Column 1 (no indent) |
| Instructions and directives     | 8-space indent       |
| Global equate `=`               | 8-space indent       |
| Zero-page equate `=`            | 16-space indent      |
| Inline comments on equates      | Column 25            |
| Inline comments on instructions | Column 33            |

### Equate Style

Define equates using `=` with enough padding to align the `=` at the correct column.

Do not use the `equ` keyword in documentation examples.

```asm
SCREEN  = $8000
GETIN   = $FFE4
CHROUT  = $FFD2
STATUS  = $0096
```

### Standalone Programs vs. Snippets

Complete standalone programs include `processor 6502` and `org $0401` at the top and the full BASIC stub.

Subroutine snippets omit these and show only the relevant code.

Always define all equates used in a snippet at the top of the same code block.

## Inline Formatting

### Addresses and Values

Wrap all hex addresses and byte values in single backticks in prose and table cells.

Examples: `` `$E840` ``, `` `$0096` ``, `` `$FF` ``

Always use the `$` prefix for hex.

### File Cross-References

Reference other skill files with backtick code spans that include the folder prefix.

Examples: `` `system/file.md` ``, `` `hardware/chip.md` ``, `` `example/general.md` ``

Use this format consistently in both prose and table cells.

### Register and Signal Names

Chip registers in prose: `PCR`, `ACR`, `IFR`, `PORT B`, `CRB`

6502 registers: `A`, `X`, `Y`, `SP`, `PC`

Bit positions: bit 7, bit 6 (not Bit7, BIT7, b7, or bit#7)

STATUS flag masks in prose: `$80`, `$40` (not 0x80 or %10000000)

## Prose Style

Write short sentences.

Use a single sentence per paragraph for technical descriptions.

Put one empty line before and after bullet lists.

Do not put blank lines between items in a short bullet list.

Use dashes (`-`) for bullet points.

Use numbered lists only for sequential steps.

Do not use typographic quotes (`""`). Use standard ASCII double quotes (`""`).

## Adding New Topic Files

### Register in SKILL.md

Every new file must be registered in `SKILL.md`:

1. Add a row to the appropriate topic table under the correct category heading.
2. Add one or more rows to the Common Task Routing table.
3. If the file exceeds roughly 500 lines, add it to the "Note on Large Reference Files" table.

### File Naming

Use a single lowercase word for single-concept files: `cpu.md`, `sound.md`, `memory.md`.

Use a hyphen for multi-word names: `dasm-assembler.md`.

### Folder Assignment

| Folder      | Contents                                        |
|-------------|-------------------------------------------------|
| `hardware/` | Chip registers, timing, hardware-level facts    |
| `system/`   | OS routines, memory layout, I/O protocols       |
| `code/`     | Implementation techniques, algorithmic patterns |
| `utility/`  | Tools, assembler, build system                  |
| `example/`  | Complete runnable programs and templates        |

### Required Sections

Every new topic file must include at minimum:

- H1 title
- `## Purpose` with `> **Scope:**` and `> **Key items:**` blockquote
- Out-of-scope table with at least one row pointing to a related skill file
- One or more main content sections

Files over roughly 200 lines must also include a `## Contents` table.
