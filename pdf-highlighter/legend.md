---
status: default
comments: off
---

# Highlight legend

This file defines the categories used by the highlighter. `scripts/highlight.py` reads the table below, so editing it changes the colors and codes with no code changes.

`status` (in the frontmatter above) tracks setup:

- `default`: factory legend, the user was never asked. Claude must offer customization on first use.
- `default-confirmed`: the user was asked and chose to keep the factory legend. Do not ask again.
- `custom`: the user's own legend. Do not ask again.

`comments` (also in the frontmatter) is `off` or `on`. With `off` (default) highlights carry no popup text and Claude writes no notes, which saves output tokens. With `on`, Claude adds a short observation to the most valuable highlights.

Table rules: one row per category; `Code` is a single letter A-Z (unique); `Color` is a hex value like `#FFEB3B`; `When to highlight` is the instruction Claude follows while reading.

| Code | Label              | Color   | When to highlight                                     |
|------|--------------------|---------|-------------------------------------------------------|
| T    | Key point / thesis | #FFEB3B | Main claims, conclusions, central ideas               |
| D    | Definition         | #73D973 | Terms being defined, formal statements, key concepts  |
| E    | Evidence / data    | #66BFFF | Numbers, results, citations, measurements             |
| R    | Risk / caveat      | #FF7373 | Limitations, warnings, assumptions, exceptions        |
| A    | Action / decision  | #FFA633 | Requirements, deadlines, todo items, recommendations  |
| X    | Example            | #BF8CF2 | Worked examples, case studies, illustrations          |
