#!/usr/bin/env python3
"""Read and validate legend.md (the category table used by the highlighter).

CLI:
  python legend.py [path/to/legend.md]   -> prints JSON {status, categories}, exit 2 on errors
"""
import json
import re
import sys
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "legend.md"
STATUSES = {"default", "default-confirmed", "custom"}


def load_comments(path=None):
    """True if legend.md has `comments: on` in its frontmatter (default off)."""
    path = Path(path) if path else DEFAULT_PATH
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", path.read_text(encoding="utf-8"), re.S)
    for line in (fm.group(1).splitlines() if fm else []):
        k, _, v = line.partition(":")
        if k.strip() == "comments":
            v = v.strip().lower()
            if v not in ("on", "off"):
                raise ValueError(f"comments must be on or off, got {v!r}")
            return v == "on"
    return False


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def load(path=None):
    """Return (status, {code: (label, description, rgb01, hex)}). Raises ValueError."""
    path = Path(path) if path else DEFAULT_PATH
    text = path.read_text(encoding="utf-8")

    status = "default"
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if fm:
        for line in fm.group(1).splitlines():
            k, _, v = line.partition(":")
            if k.strip() == "status":
                status = v.strip()
    if status not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}, got {status!r}")

    cats, errors = {}, []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() == "code" or set(cells[0]) <= set("-: "):
            continue
        code, label, color, desc = cells[0].upper(), cells[1], cells[2], cells[3]
        m = re.search(r"#[0-9a-fA-F]{6}\b", color)
        if not re.fullmatch(r"[A-Z]", code):
            errors.append(f"code must be a single letter A-Z: {cells[0]!r}")
        elif code in cats:
            errors.append(f"duplicate code {code!r}")
        elif not m:
            errors.append(f"{code}: color must be hex like #FFEB3B, got {color!r}")
        elif not label:
            errors.append(f"{code}: empty label")
        else:
            cats[code] = (label, desc, hex_to_rgb(m.group(0)), m.group(0).upper())
    if not cats and not errors:
        errors.append("no categories found in the table")
    if errors:
        raise ValueError("; ".join(errors))
    return status, cats


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        status, cats = load(path)
        comments = load_comments(path)
    except (ValueError, OSError) as e:
        print(f"legend error: {e}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps({
        "status": status,
        "comments": comments,
        "categories": [{"code": c, "label": v[0], "color": v[3], "when": v[1]} for c, v in cats.items()],
    }, indent=2))


if __name__ == "__main__":
    main()
