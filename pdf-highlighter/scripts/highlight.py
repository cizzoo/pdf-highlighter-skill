#!/usr/bin/env python3
"""Apply semantic highlights to a PDF from compact annotation files.

Annotation file format (one rule per line, '#' starts a comment):
    T: 1.2, 1.5-1.7, 3.10-4.2
    R: 2.4
Optional comment lines attach a short note to a highlighted unit (shown as the
annotation popup in PDF viewers):
    @3.12: why this matters, one short sentence
Each token is a unit id from units.txt ("<page>.<n>") or an inclusive range
"<start>-<end>" in document order (ranges may cross pages).

Usage:
  python highlight.py input.pdf --units work/units.json \
      --ann work/ann_*.txt --out input_highlighted.pdf
"""
import argparse
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import legend as legend_mod  # noqa: E402

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        sys.exit("PyMuPDF is not installed. Ask the user to run 'pip install pymupdf' or to start Claude Code inside an environment that has it.")



def parse_annotations(paths, order, index, cats):
    """Return {code: [unit ids]} and a list of problems."""
    result, problems, notes = {}, [], {}
    for path in paths:
        for ln, raw in enumerate(open(path, encoding="utf-8"), start=1):
            stripped = raw.strip()
            if stripped.startswith("@"):  # note line: keep '#' characters as text
                nm = re.match(r"^@\s*(\d+\.\d+)\s*:\s*(.+)$", stripped)
                if not nm:
                    problems.append(f"{path}:{ln} bad note line: {stripped[:40]!r}")
                elif nm.group(1) not in index:
                    problems.append(f"{path}:{ln} note on unknown unit {nm.group(1)!r}")
                else:
                    notes[nm.group(1)] = nm.group(2).strip()
                continue
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            m = re.match(r"^([A-Za-z])\s*:\s*(.+)$", line)
            if not m:
                problems.append(f"{path}:{ln} unparsable line: {line!r}")
                continue
            code = m.group(1).upper()
            if code not in cats:
                problems.append(f"{path}:{ln} unknown category {code!r}")
                continue
            for tok in re.split(r"[,\s]+", m.group(2).strip()):
                if not tok:
                    continue
                if "-" in tok:
                    a, b = tok.split("-", 1)
                    # shorthand "3.10-14" means 3.10-3.14
                    if "." not in b:
                        b = f"{a.split('.')[0]}.{b}"
                    if a not in index or b not in index or index[a] > index[b]:
                        problems.append(f"{path}:{ln} bad range {tok!r}")
                        continue
                    ids = order[index[a]: index[b] + 1]
                else:
                    if tok not in index:
                        problems.append(f"{path}:{ln} unknown unit {tok!r}")
                        continue
                    ids = [tok]
                result.setdefault(code, []).extend(ids)
    return result, problems, notes


def _font(text):
    """Built-in font able to render text: Latin by default, CJK fallback."""
    return "helv" if all(ord(c) < 256 for c in text) else "japan"


def add_legend(doc, used, cats):
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 70), "Highlight legend", fontsize=18)
    y = 110
    for code, (label, desc, rgb, _hex) in cats.items():
        if code not in used:
            continue
        page.draw_rect(fitz.Rect(50, y - 11, 74, y + 5), color=None, fill=rgb)
        page.insert_text((84, y), f"{label}  ({used[code]} units)", fontsize=12, fontname=_font(label))
        page.insert_text((84, y + 14), desc, fontsize=9, color=(0.35, 0.35, 0.35), fontname=_font(desc))
        y += 40


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--units", required=True, help="units.json from extract.py")
    ap.add_argument("--ann", nargs="+", required=True, help="annotation files (globs ok)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--legend", default=None, help="legend.md path (default: skill legend.md)")
    ap.add_argument("--no-comments", action="store_true", help="ignore @notes, write no popup text")
    ap.add_argument("--no-legend", action="store_true", help="do not append the legend page")
    ap.add_argument("--opacity", type=float, default=0.45)
    args = ap.parse_args()

    try:
        _status, cats = legend_mod.load(args.legend)
    except (ValueError, OSError) as e:
        sys.exit(f"legend error: {e}")

    geometry = json.load(open(args.units, encoding="utf-8"))
    order = list(geometry.keys())
    index = {u: i for i, u in enumerate(order)}

    paths = sorted({p for pat in args.ann for p in glob.glob(pat)})
    if not paths:
        sys.exit("No annotation files matched.")
    rules, problems, notes = parse_annotations(paths, order, index, cats)
    if args.no_comments:
        notes = {}

    try:
        doc = fitz.open(args.pdf)
    except Exception as e:
        sys.exit(f"cannot open PDF: {e}")
    used, covered = Counter(), set()
    for code, ids in rules.items():
        label, _, rgb, _hex = cats[code]
        for uid in dict.fromkeys(ids):  # dedupe, keep order
            g = geometry[uid]
            page = doc[g["page"] - 1]
            quads = [fitz.Rect(*r).quad for r in g["rects"]]
            annot = page.add_highlight_annot(quads=quads)
            annot.set_colors(stroke=rgb)
            annot.set_opacity(args.opacity)
            note = notes.get(uid)
            if note:  # popup comment only when a note exists; otherwise no text at all
                annot.set_info(title=label, content=note)
            annot.update()
            used[code] += 1
            covered.add(uid)

    orphan = [u for u in notes if u not in covered]
    for u in orphan:
        problems.append(f"note on unit {u} which is not highlighted (ignored)")
    n_notes = len(notes) - len(orphan)

    if not args.no_legend and used:
        add_legend(doc, used, cats)
    doc.save(args.out, garbage=3, deflate=True)

    pct = 100 * len(covered) / max(len(order), 1)
    print(f"saved {args.out}: {sum(used.values())} highlights on {len(order)} units ({pct:.0f}% covered)")
    if n_notes:
        print(f"comments: {n_notes}")
    print("by category: " + ", ".join(f"{c}={n}" for c, n in sorted(used.items())))
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems[:20]:
            print("  " + p)
        sys.exit(2)


if __name__ == "__main__":
    main()
