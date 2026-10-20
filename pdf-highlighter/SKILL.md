---
name: pdf-highlighter
description: Highlight a PDF in different colors by meaning (key points, definitions, evidence, risks, actions, examples, or custom categories) and return the annotated PDF, not a summary. Use when asked to highlight, annotate, mark up or color-code a PDF, or to change the legend. Not for summarizing or editing PDFs.
---

# PDF highlighter

Goal: read the whole PDF, decide what matters, and deliver the **original PDF with colored highlights**. No summary, no rewriting: the original wording stays intact and the only output tokens spent are compact unit IDs.

## Requirements

- Python 3 with PyMuPDF (`pip install pymupdf`, or run Claude Code inside an environment that has it). Checked in Step 0a.
- Optional: `ocrmypdf` for scanned PDFs.
- All `scripts/...` paths below are relative to this skill's folder (`~/.claude/skills/pdf-highlighter`). Run them as `$PY <skill-dir>/scripts/...` (`$PY` from Step 0a) from any directory, and keep `work/` in a scratch directory, not in the skill folder.

## Files

- `legend.md`: the legend. Defines categories (code, label, hex color, when to highlight) and a `status` in its frontmatter. Single source of truth: `highlight.py` reads it.
- `scripts/legend.py`: parses and validates `legend.md` (`$PY scripts/legend.py` prints status and categories as JSON, exit code 2 on errors).
- `scripts/extract.py`: PDF -> numbered units + geometry.
- `scripts/highlight.py`: annotation files + geometry -> highlighted PDF.

## Step 0a: check PyMuPDF (every run, before anything else)

Find a Python that can import PyMuPDF: try `python3 -c "import pymupdf"` (or `import fitz`), then the pipx venv `~/.local/share/pipx/venvs/pymupdf/bin/python`. Use the first interpreter that works (call it `$PY`) for every script below. If none works, **stop**: do not install anything yourself. Tell the user to install it (`pip install pymupdf` in a venv, or `pipx install pymupdf`) or restart Claude Code inside an environment that already has PyMuPDF, then wait.

## Step 0: check the legend (every run, before anything else)

Run `$PY scripts/legend.py` and look at `status` and `comments` (`comments` says whether Claude writes notes on highlights; see "Comments" below).

| status | Meaning | What to do |
|---|---|---|
| `default` | Factory legend, user never asked | **Offer customization once** (below), then continue |
| `default-confirmed` | User chose to keep the factory legend | Continue, do not ask |
| `custom` | User's own legend | Continue, do not ask |

If the command fails, the legend is broken: fix `legend.md` (or restore the factory table) before continuing.

### First-run offer (status = `default`)

Ask with a single AskUserQuestion call containing two questions:

1. Legend, two options:
   - "Use the default legend (Recommended)": keep the six factory categories (key point, definition, evidence, risk, action, example).
   - "Set up my own": define custom categories.
2. Comments on highlights, two options:
   - "No comments (Recommended)": colors only, fewest tokens.
   - "Add short comments": Claude writes a brief observation on the most valuable highlights, shown as a popup note in the PDF viewer. Costs extra output tokens.

Show the current categories briefly (code, label, color) in the question text so the choice is informed. If the user is not present (unattended or scheduled run), skip the questions, use the defaults (no comments) and mention in the final reply that the legend and comments can be customized.

Save the comments answer in the frontmatter of `legend.md` (`comments: on` or `comments: off`).

**If they keep the default:** set `status: default-confirmed` in the frontmatter of `legend.md` (Edit), then continue with the task.

**If they want their own**, help them build it, keeping it short:

1. Ask what they use these PDFs for (e.g. papers, contracts, study material, meeting notes, reports). One question, free text allowed.
2. Propose a starting set of 4-7 categories tailored to that use, each with a one-letter code, a label and a "when to highlight" rule. Examples:
   - Contracts: obligations, deadlines, penalties/liability, definitions, unusual clauses.
   - Papers: contribution, method, results, limitations, related work.
   - Study material: definitions, formulas/theorems, examples, likely exam points.
3. Let the user add, remove or rename. Offer a color for each. Rules for colors: pick clearly distinguishable hues, avoid dark colors (text must stay readable under a 45% opacity highlight), avoid two similar yellows/greens.
4. Write the result into the table of `legend.md` with `status: custom`, keeping the explanatory text of the file. Codes must be unique single letters A-Z, colors `#RRGGBB`.
5. Run `$PY scripts/legend.py` to validate. Show the final legend as a short table and continue with the task.

The user can also ask later to change the legend or the comments setting ("change the colors", "add a category", "turn comments on", "reset to default"). Edit `legend.md` the same way. "Reset" means restoring the six factory rows and setting `status: default-confirmed`.

Per-run override: `highlight.py --legend other.md` uses a different legend file for one run without touching `legend.md`.

## Workflow

```bash
# Step 1: extract (prints units count and an estimate of tokens to read)
$PY scripts/extract.py "<input.pdf>" --out work/

# Step 2: read work/units.txt fully, in chunks (see below), writing annotation files

# Step 3: render (uses legend.md automatically)
$PY scripts/highlight.py "<input.pdf>" --units work/units.json \
    --ann "work/ann_*.txt" --out "<input>_highlighted.pdf"
```

If `extract.py` reports an encrypted or unreadable PDF, stop and tell the user (ask for a decrypted copy); do not guess.

### Reading in chunks

- Read `work/units.txt` with the Read tool using `offset`/`limit`, about 400 lines per chunk.
- Before reading, take the categories and their "when to highlight" rules from `$PY scripts/legend.py` output. The category codes in annotation files must come from the legend.
- After each chunk, immediately write `work/ann_01.txt`, `work/ann_02.txt`, ... with Write. Do not wait until the end: it keeps context small and survives interruptions.
- Never skip a chunk. The whole document must be read.
- For very large PDFs (over ~150k tokens of units), delegate chunks to parallel subagents, giving each the legend, each writing its own `ann_XX.txt`, then run step 3 once.

### Annotation format

One rule per line, IDs only:

```text
T: 1.2, 1.5-1.7, 3.10-4.2
D: 2.1
E: 2.4, 2.9-2.11
R: 5.3
```

- The letter is a category `Code` from `legend.md`.
- `page.n` is a unit ID exactly as shown in `units.txt`.
- `a-b` is an inclusive range in document order and may cross pages. Shorthand `3.10-14` means `3.10-3.14`.
- `#` starts a comment (ignored by the script). Do not write explanations, quotes or prose in these files.
- Note lines, **only when comments are enabled** (see below): `@3.12: short observation`. The unit must also be highlighted by a category line, otherwise the note is reported as a problem and ignored.

### Selection rules (what makes a good highlight)

- Be selective: aim for roughly 10-25% of units highlighted. If more than ~35% is marked, the highlights stopped meaning anything; remove the weakest.
- One category per unit. If a unit fits two, pick the more actionable one.
- Prefer the unit that carries the claim over its introduction or transition sentences.
- Skip boilerplate: headers, footers, page numbers, tables of contents, bibliography entries (unless the user asks otherwise).
- Figure labels, table cells and axis ticks show up as short junk units: ignore them.
- Highlight consecutive units as one range to keep the file short.
- Work in the document's language; category codes are language-independent.

## Comments (optional, off by default)

Highlights carry **no popup text** unless comments are enabled. This is deliberate: colors already tell the category, and notes cost output tokens.

Comments are enabled when either:
- `legend.md` has `comments: on` (the legend output shows `"comments": true`), or
- the user asks for comments in the current request ("with comments", "add notes"): use them for this run only, without changing the file, unless they ask to make it permanent.

If the user asks for no comments in the current request while the file says `on`, write none.

When enabled, apply these rules while reading each chunk:
- Add a note only where it says something the color does not: why it matters, an implication, a tension with another passage, a caveat on a number. Never restate the sentence or name the category.
- Not every highlight needs one. Target roughly one note per 3-4 highlights, on the most valuable ones.
- Maximum 20 words per note, one sentence, in the document's language (or the user's, if they said so).
- Put notes in the same `ann_XX.txt` as the chunk, as `@page.n: text` lines, after the category lines.
- When comments are disabled, write no `@` lines at all and pass nothing special to the script (`--no-comments` exists to force-strip notes if some slipped in).

## Output and final reply

- Deliver the highlighted PDF with SendUserFile, named `<input>_highlighted.pdf`. If that tool is unavailable, save the file next to the input and give its full path.
- The user explicitly asked for a PDF here, so a PDF is the right deliverable for this skill.
- Final reply: one or two lines with the stats printed by `highlight.py` (highlights per category, % of text covered, and number of comments if any). Do **not** add a summary of the document unless asked.
- The script appends a legend page at the end of the PDF (`--no-legend` to skip), built from `legend.md`.

## Troubleshooting

- `legend error: ...`: `legend.md` is malformed (duplicate or multi-letter code, color not `#RRGGBB`, bad status). Fix the reported row.
- `WARNING: no text layer on pages [...]`: the PDF is scanned. Run `ocrmypdf --force-ocr in.pdf ocr.pdf` (install with pip or apt if needed), then restart from step 1 on `ocr.pdf`.
- `highlight.py` exits with code 2 and lists problems (unknown IDs or categories, bad ranges): fix those lines in the annotation files and re-run. It is idempotent because it always starts from the original PDF.
- Two-column layouts: `extract.py` keeps the PDF's native block order (no geometric sorting), which follows the reading order for typical LaTeX/Word papers (tested on a two-column IEEE paper). If a PDF's internal order is scrambled, highlights are still positioned correctly, only the reading order in `units.txt` is off.
- Highlights are standard PDF annotations: they can be removed or recolored in any PDF viewer. A highlight shows a popup only if Claude wrote a note for it.
- `note on unit X which is not highlighted`: add X to a category line or remove the `@` line.
- If the skill folder is read-only in the current environment, keep the custom legend in the working folder and pass it with `--legend`.
