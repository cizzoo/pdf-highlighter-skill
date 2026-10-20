#!/usr/bin/env python3
"""Extract a PDF into numbered text units (roughly sentences) with exact geometry.

Outputs:
  <out>/units.txt   one line per unit: "<page>.<n>|<text>"  (this is what Claude reads)
  <out>/units.json  geometry per unit id (line rectangles) used later by highlight.py

Usage:
  python extract.py input.pdf --out work/
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:
    try:
        import fitz
    except ImportError:
        sys.exit("PyMuPDF is not installed. Ask the user to run 'pip install pymupdf' or to start Claude Code inside an environment that has it.")

ABBREV = {"e.g.", "i.e.", "etc.", "fig.", "eq.", "vs.", "cf.", "al.", "no.", "dr.",
          "prof.", "sig.", "es.", "ecc.", "pag.", "cap.", "art.", "sez."}
LEADER = re.compile(r"^[.\u00b7\u2022\u2026_\-\u2013\u2014\s]+$")  # dot leaders, rules
MAX_WORDS = 45  # hard cap so one unit never becomes a giant paragraph


def ends_sentence(word: str) -> bool:
    w = word.strip().lower()
    if w in ABBREV:
        return False
    if re.fullmatch(r"\d+\.", w):  # list numbers such as "3."
        return False
    return bool(re.search(r"[.!?…]['\")\]]*$", w))


def merge_rects(words):
    """Union word boxes that share the same (block, line) -> one rect per visual line."""
    lines = {}
    for w in words:
        key = (w[5], w[6])
        r = lines.setdefault(key, [w[0], w[1], w[2], w[3]])
        r[0], r[1] = min(r[0], w[0]), min(r[1], w[1])
        r[2], r[3] = max(r[2], w[2]), max(r[3], w[3])
    return [[round(v, 2) for v in r] for r in lines.values()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default="work")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        doc = fitz.open(args.pdf)
    except Exception as e:
        sys.exit(f"cannot open PDF: {e}")
    if doc.needs_pass:
        sys.exit("PDF is password-protected: ask the user for a decrypted copy.")
    if len(doc) == 0:
        sys.exit("PDF has no pages.")

    geometry, text_lines, empty_pages = {}, [], []
    for pno, page in enumerate(doc, start=1):
        words = [w for w in page.get_text("words") if not LEADER.match(w[4])]
        if not words:
            empty_pages.append(pno)
            continue
        n, buf, last_block = 0, [], None

        def flush():
            nonlocal n, buf
            if not buf or not any(c.isalnum() for w in buf for c in w[4]):
                buf = []
                return
            n += 1
            uid = f"{pno}.{n}"
            geometry[uid] = {"page": pno, "rects": merge_rects(buf)}
            text_lines.append(f"{uid}|{' '.join(w[4] for w in buf)}")
            buf = []

        for w in words:
            if last_block is not None and w[5] != last_block:
                flush()  # new text block -> new unit
            buf.append(w)
            last_block = w[5]
            if ends_sentence(w[4]) or len(buf) >= MAX_WORDS:
                flush()
        flush()

    (out / "units.txt").write_text("\n".join(text_lines), encoding="utf-8")
    (out / "units.json").write_text(json.dumps(geometry), encoding="utf-8")

    chars = sum(len(l) for l in text_lines)
    print(f"pages={len(doc)} units={len(geometry)} chars={chars} (~{chars // 4} tokens to read)")
    if empty_pages:
        print(f"WARNING: no text layer on pages {empty_pages}. "
              "Run OCR first (e.g. ocrmypdf --force-ocr in.pdf ocr.pdf) and retry.")


if __name__ == "__main__":
    main()
