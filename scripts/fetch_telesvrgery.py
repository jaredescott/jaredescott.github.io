#!/usr/bin/env python3
"""Download Telesvrgery HTML from Google Drive and wrap it for Jekyll 3 (Liquid {% raw %})."""
from __future__ import annotations

import pathlib
import re
import sys

# Served path after fetch (same for local build and GitHub Pages with baseurl "").
VR_IMAGE_SITE_PATH = "/assets/telesvrgery/vr-view-1.png"


def rewrite_drive_vr_image_urls(html: str, image_id: str) -> str:
    """Replace Google Drive URLs for the VR image with a same-origin path (Drive blocks <img> hotlinking)."""
    if not image_id:
        return html
    needles = [
        f"https://drive.google.com/uc?export=view&id={image_id}",
        f"https://drive.google.com/uc?id={image_id}",
        "https://drive.google.com/uc?export=download&id=" + image_id,
    ]
    for n in needles:
        html = html.replace(n, VR_IMAGE_SITE_PATH)
    # Pasted "open in browser" links
    html = re.sub(
        rf"https://drive\.google\.com/file/d/{re.escape(image_id)}/[^\s\"'<>]*",
        VR_IMAGE_SITE_PATH,
        html,
        flags=re.I,
    )
    return html


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

    img_m = re.search(r"^\s*telesvrgery_vr_view_image_id:\s*\"([^\"]*)\"", text, re.MULTILINE)
    image_id = img_m.group(1).strip() if img_m else ""

    try:
        import gdown
    except ImportError:
        print("ERROR: pip install -r scripts/requirements-telesvrgery.txt", file=sys.stderr)
        sys.exit(1)

    out_dir = root / "telesvrgery"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "index.html.raw"

    url = f"https://drive.google.com/uc?id={file_id}"
    # gdown 6.x removed the `fuzzy` kwarg; direct uc?id= URLs do not need it.
    gdown.download(url, str(raw_path), quiet=False)

    body = raw_path.read_text(encoding="utf-8")
    if body.startswith("\ufeff"):
        body = body[1:]
    if raw_path.exists():
        raw_path.unlink()

    if image_id:
        body = rewrite_drive_vr_image_urls(body, image_id)

    wrapped = (
        "---\nlayout: null\n---\n{% raw %}\n"
        + body
        + "\n{% endraw %}\n"
    )
    (out_dir / "index.html").write_text(wrapped, encoding="utf-8")
    print(f"Wrote {out_dir / 'index.html'}")

    if image_id:
        assets_dir = root / "assets" / "telesvrgery"
        assets_dir.mkdir(parents=True, exist_ok=True)
        img_out = assets_dir / "vr-view-1.png"
        img_url = f"https://drive.google.com/uc?id={image_id}"
        gdown.download(img_url, str(img_out), quiet=False)
        if not img_out.exists() or img_out.stat().st_size == 0:
            print("ERROR: VR image download failed or empty", file=sys.stderr)
            sys.exit(1)
        print(f"Wrote {img_out} (poster HTML can use src=\"{VR_IMAGE_SITE_PATH}\")")


if __name__ == "__main__":
    main()
