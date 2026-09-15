# Document Style

## Purpose

This document defines the formatting and prose style for every Markdown document that is part of this Agent Skill.

It compiles rules from the [Agent Skills specification](https://agentskills.io/specification), the `skill-creator` skill, and general Markdown formatting best practices.

Every document created or modified as part of this skill must follow the rules below.

## Document Structure

Use a consistent top-to-bottom layout for every document.

1. **H1 title** - plain, descriptive title, no subtitle or suffix.
2. **Purpose** - one paragraph or blockquote stating what the document covers.
3. **Main sections** - H2 (`##`) for major topics, H3 (`###`) for subtopics.

Do not use H4 or deeper headings.

### Purpose Section Format

The Purpose section may use a blockquote format to summarize scope and key items:

```markdown
## Purpose

> **Scope:** one-line description of what this file covers
> **Key items:** comma-separated list of key concepts or references
```

This format is recommended for reference files and topic documents.

### Out-of-Scope Table

When a document covers a focused topic within a larger skill, include an out-of-scope table directing readers to related files.

```markdown
| Out of scope   | See instead        |
|----------------|--------------------|
| Chip registers | `hardware/chip.md` |
| Memory map     | `system/memory.md` |
```

The table has exactly two columns named `Out of scope` and `See instead`.

Put it directly below the Purpose section with no heading between them.

Use backtick code spans around the file path in the `See instead` column.

### Contents Table

Include a Contents table in files longer than 300 lines.

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

## Paragraph and Sentence Structure

Write short sentences.

Use one sentence per paragraph for technical descriptions.

This keeps the text readable in plain text editors, terminal viewers, and diff output.

Separate every sentence with an empty line.

A sentence may contain multiple related clauses if they express a single thought.

Do not pack unrelated ideas into one long paragraph.

## Word Wrap and Line Breaks

Do not hard-wrap text at a fixed column width.

Let each sentence occupy one logical line.

A sentence may be long when the thought is long, the editor or renderer will soft-wrap the display.

Hard-wrap only when the source itself needs a forced line break, such as inside a code block or a diagram.

## Headings

Use Title Case for all English section and chapter names.

Use sentence case for Polish section and chapter names.

Use H2 (`##`) for top-level sections.

Use H3 (`###`) for subsections.

Keep section names short.

Do not put descriptive qualifiers in section names using parentheses.

Put qualifiers like "mandatory" or "do not repeat" in the section body instead.

Parenthetical content in headings is allowed for compact technical identifiers only, such as address ranges, register numbers, or standard disambiguators.

Avoid headings with trailing punctuation.

## Lists

Use dashes (`-`) for bullet points.

Use numbered lists only for sequential steps.

Put one empty line before and after every list.

Do not put blank lines between short list items.

Use blank lines between list items when the items are long or contain multiple sentences.

Put one blank line between a parent list item and its nested sublist.

For nested lists, indent the sublist to the parent item.

## Empty Lines and Spacing

Use one blank line between paragraphs.

Put one blank line before and after a list.

Put one blank line before and after a code block.

Do not stack multiple blank lines.

Do not use trailing spaces at the end of lines.

## Code Blocks

Use a language tag on every fenced code block that contains code in a programming, markup, or data language.

Do not use a language tag on fenced blocks that contain ASCII art, directory trees, diagrams, or plain text.

Leave those blocks as plain fenced blocks with no tag.

Do not leave a blank line as the first or last line inside the block.

Keep code blocks compact and relevant.

Use backticks for inline code, file names, commands, and values.

## Inline Formatting

Prefer standard ASCII characters for normal text.

Use standard ASCII double quotes (`"`) instead of typographic quotes.

Use standard ASCII apostrophes (`'`) instead of typographic apostrophes.

Use bold text for key term definitions: **Term**: definition.

Use italics sparingly.

Do not overuse emphasis.

## Semicolons

Do not use the semicolon character in prose.

Join two closely related clauses with a comma instead.

Split the clauses into separate sentences when they express separate thoughts.

This rule does not apply to code blocks, inline code, or file paths.

## Tables

Tables must remain readable as plain text.

Column alignment and consistent padding are the primary goals.

### Delimiters

Use pipe characters (`|`) to delimit columns.

Place one space after the leading pipe and one space before the trailing pipe.

Do not add extra spaces around the pipes beyond the single required space.

### Header Separator

Place a separator line immediately after the header row.

The separator line contains only hyphens and pipe characters.

The hyphens in the separator row are contiguous with the pipe characters.

Do not add spaces between the pipes and the hyphens in the separator row.

The separator width for each column must match the header and content cell width between the pipes.

This means the separator contains the calculated column width plus two hyphens.

The extra hyphens account for the single space before and after each cell value.

The minimum width of any column is three characters.

### Cell Padding

Pad every cell with trailing spaces so it matches the column width.

Empty cells must also be padded to the column width.

Do not pad beyond the column width.

Never truncate cell contents.

Use left alignment for all cells.

### Column Widths

Calculate the column width as the maximum character width of all cells in that column, including the header cell.

Measure the width as the length of the cell string between the cell delimiters.

The width is the **source text** character count, not the rendered character count.

This is the most important rule in this section.

Count every character that appears in the plain-text Markdown source, including all formatting markers.

Do not strip, interpret, or collapse any characters before measuring.

Do not measure the width of what the cell would look like after a Markdown renderer processes it.

A Markdown renderer hides backticks, asterisks, and other formatting markers from the reader, but those markers are still present in the source text and must be counted.

The table is formatted for plain-text readability first, and a Markdown renderer second.

In plain-text view, every character is visible, so every character must be counted.

**Characters That Must Be Counted**

The following characters are part of the cell content and must be included in the width measurement.

- Backticks around inline code (e.g., the cell `` `some.value` `` has 13 characters, not 11).
- Double backticks around code containing backticks (e.g., the cell `` `` `00` `` `` has 8 characters, not 4).
- Asterisks for emphasis (e.g., the cell `*italic*` has 9 characters, not 7).
- Double asterisks for bold (e.g., the cell `**bold**` has 10 characters, not 4).
- Underscores for emphasis (e.g., the cell `_under_` has 8 characters, not 5).
- Triple backticks, pipe characters inside code spans, and any other literal characters.
- Spaces, punctuation, and all other visible characters.

**Common Mistake**

The most common formatting mistake is measuring the **rendered** width instead of the **source** width.

For example, the cell `` `config.settings.json` `` contains 22 characters in the source text, including the two backticks.

A Markdown renderer displays only `config.settings.json`, which is 20 characters.

If the formatter uses 20 instead of 22, the column will be too narrow and the pipes will not align in plain text.

Always count the source text, never the rendered text.

### Compacting

Compact the table after calculating column widths.

Remove any padding that exceeds the widest cell in each column.

Recalculate the separator line and all cell padding after compacting.

A compacted table has the minimum column widths needed to display all cells correctly.

The compacted version is the correct version.

### Reformat After Editing

Editing any cell can change a column's width, so reformat the whole table after every edit.

Recompute each column's width, re-pad every data cell, and replace every separator cell with the correct number of hyphens.

A table is only correctly edited when every cell in a column has the same width and every separator cell matches that width plus two.

### Multi-Line Cells

Avoid multi-line cells.

If a cell must wrap, apply the same formatting rules to every row in the table.

## Special Characters

Box-drawing characters are allowed inside code blocks for diagrams.

Do not replace box-drawing characters with `+`, `-`, or other ASCII approximations.

Do not use emojis unless explicitly requested.

## Language

Write documentation in the language used by the project.

For English, use Title Case in section names.

For Polish, use sentence case in section names.

For Polish content examples, use "Przykład zawartości" instead of "Content Example".

## File References

When referencing other files in the skill, use relative paths from the skill root.

Keep file references one level deep from `SKILL.md`.

Avoid deeply nested reference chains.

Reference files clearly from `SKILL.md` with guidance on when to read them.

Use backtick code spans around file paths in both prose and table cells.

Examples: `system/memory.md`, `hardware/chip.md`, `process/workflow.md`.

## Skill Document Requirements

Documents that are part of an Agent Skill must follow additional rules from the [Agent Skills specification](https://agentskills.io/specification) and the `skill-creator` skill.

### SKILL.md Frontmatter

The `SKILL.md` file must contain YAML frontmatter followed by Markdown content.

Required frontmatter fields:

- **`name`** - 1-64 characters, lowercase letters and hyphens only, must not start or end with a hyphen, must not contain consecutive hyphens, must match the parent directory name.
- **`description`** - 1-1024 characters, non-empty, describes what the skill does and when to use it, should include specific trigger keywords.

Optional frontmatter fields:

- **`license`** - License name or reference to a bundled license file.
- **`compatibility`** - 1-500 characters, environment requirements.
- **`metadata`** - Map from string keys to string values for additional properties.
- **`allowed-tools`** - Space-separated string of pre-approved tools.

### Progressive Disclosure

Skills use a three-level loading system.

1. **Metadata** - The `name` and `description` fields are loaded at startup for all skills.
2. **Instructions** - The full `SKILL.md` body is loaded when the skill is activated.
3. **Resources** - Files in `scripts/`, `references/`, `assets/`, or other directories are loaded only when required.

Keep `SKILL.md` under 500 lines.

Move detailed reference material to separate files.

For large reference files over 300 lines, include a table of contents.

### Writing Style for Skill Instructions

Prefer the imperative form in instructions.

Explain why things are important instead of using heavy-handed directives.

Use theory of mind and make the skill general, not narrow to specific examples.

Start by writing a draft and then review it with fresh eyes to improve it.

### Directory Structure

A skill is a directory containing, at minimum, a `SKILL.md` file.

Optional directories:

- `scripts/` - Executable code for deterministic or repetitive tasks.
- `references/` - Documentation loaded into context as needed.
- `assets/` - Files used in output such as templates, icons, and fonts.

When a skill supports multiple domains or frameworks, organize by variant and let the agent read only the relevant reference file.

## Adding New Files

### Register in SKILL.md

Every new file must be registered in `SKILL.md`.

Add a reference to the appropriate section or table in `SKILL.md` with guidance on when to read the file.

### File Naming

Use a single lowercase word for single-concept files: `cpu.md`, `sound.md`, `memory.md`.

Use hyphens for multi-word names: `dasm-assembler.md`, `risk-register.md`.

### Required Sections

Every new topic file must include at minimum:

- H1 title
- `## Purpose` section
- One or more main content sections

Files over 300 lines must also include a `## Contents` table.

## File Maintenance

Maintain the existing line break style and encoding of any document you edit.

Create new files in UTF-8 by default.
