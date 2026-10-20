# pdf-highlighter-skill

A Claude Code skill that highlights a PDF in different colors by meaning (key points, definitions, evidence, risks, actions, examples, or your own categories) and returns the annotated PDF instead of a summary. The original text is untouched; highlights are standard PDF annotations.

## Requirements

- Python 3 with [PyMuPDF](https://pymupdf.readthedocs.io/) (`pip install pymupdf` in a venv, or `pipx install pymupdf`)
- Optional: `ocrmypdf` for scanned PDFs

The skill checks for PyMuPDF on every run and stops with install instructions if it is missing. It looks for `python3` first, then the pipx venv at `~/.local/share/pipx/venvs/pymupdf`.

## Install

### Claude Code

Download `pdf-highlighter.zip` from the [latest release](https://github.com/cizzoo/pdf-highlighter-skill/releases/latest) and unzip it into `~/.claude/skills/`.

Or from source: the skill lives in the `pdf-highlighter/` folder of this repo. Clone the repo anywhere, then copy that folder into your Claude Code skills directory (the folder name must match the skill name):

```bash
git clone https://github.com/cizzoo/pdf-highlighter-skill.git
cp -r pdf-highlighter-skill/pdf-highlighter ~/.claude/skills/
```

To keep it in sync with the repo, symlink it instead of copying:

```bash
ln -s "$(pwd)/pdf-highlighter-skill/pdf-highlighter" ~/.claude/skills/pdf-highlighter
```

For a single project, use `<project>/.claude/skills/` instead of `~/.claude/skills/`.

### Claude.ai

Download the skill as a zip from the [Releases page](https://github.com/cizzoo/pdf-highlighter-skill/releases/latest).

## Usage

In Claude Code, give it a PDF:

> Highlight ~/Downloads/paper.pdf

On first use it asks whether to keep the default legend and whether to add short popup comments. Both choices are saved in `legend.md`. You can change them later ("add a category", "turn comments on", "reset to default").

Output: `<input>_highlighted.pdf`, with a legend page appended.

## How it works

1. `scripts/extract.py` splits the PDF into numbered units (about one sentence each) with geometry.
2. Claude reads the units in chunks and writes compact annotation files (`T: 1.2, 1.5-1.7`), IDs only.
3. `scripts/highlight.py` turns those into highlight annotations, using the legend in `legend.md`.

## Default legend

| Code | Category | Color |
|------|----------|-------|
| T | Key point / thesis | #FFEB3B |
| D | Definition | #73D973 |
| E | Evidence / data | #66BFFF |
| R | Risk / caveat | #FF7373 |
| A | Action / decision | #FFA633 |
| X | Example | #BF8CF2 |
