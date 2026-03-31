#!/usr/bin/env python3
"""Download Telesvrgery HTML from Google Drive and wrap it for Jekyll 3 (Liquid {% raw %})."""
from __future__ import annotations

import pathlib
import re
import sys


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    config_path = root / "_config.yml"
    text = config_path.read_text(encoding="utf-8")
    m = re.search(r"^\s*telesvrgery_drive_file_id:\s*\"([^\"]*)\"", text, re.MULTILINE)
    if not m:
        print("ERROR: telesvrgery_drive_file_id not found in _config.yml", file=sys.stderr)
        sys.exit(1)
    file_id = m.group(1).strip()
    if not file_id:
        print("ERROR: telesvrgery_drive_file_id is empty in _config.yml", file=sys.stderr)
        sys.exit(1)

    try:
        import gdown
    except ImportError:
        print("ERROR: pip install -r scripts/requirements-telesvrgery.txt", file=sys.stderr)
        sys.exit(1)

    out_dir = root / "telesvrgery"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "index.html.raw"

    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, str(raw_path), quiet=False, fuzzy=True)

    body = raw_path.read_text(encoding="utf-8")
    if body.startswith("\ufeff"):
        body = body[1:]
    if raw_path.exists():
        raw_path.unlink()

    wrapped = (
        "---\nlayout: null\n---\n{% raw %}\n"
        + body
        + "\n{% endraw %}\n"
    )
    (out_dir / "index.html").write_text(wrapped, encoding="utf-8")
    print(f"Wrote {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
