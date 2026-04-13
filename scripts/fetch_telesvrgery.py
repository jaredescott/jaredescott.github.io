#!/usr/bin/env python3
"""Download Telesvrgery HTML from Google Drive and wrap it for Jekyll 3 (Liquid {% raw %})."""
from __future__ import annotations

import pathlib
import re
import sys

# Served paths after fetch (same for local build and GitHub Pages with baseurl "").
VR_IMAGE_SITE_PATH = "/assets/telesvrgery/vr-view-1.png"
CYLINDER_IMAGE_SITE_PATH = "/assets/telesvrgery/vr-capsule-1.png"
OUTPUT_DEVICE_IMAGE_SITE_PATH = "/assets/telesvrgery/output-device-view.png"
VASCULAR_PHANTOM_IMAGE_SITE_PATH = "/assets/telesvrgery/vascular-phantom-view.png"


def rewrite_drive_asset_urls(html: str, file_id: str, site_path: str) -> str:
    """Replace Google Drive URLs for one file with a same-origin path (Drive blocks <img> hotlinking)."""
    if not file_id:
        return html
    needles = [
        f"https://drive.google.com/uc?export=view&id={file_id}",
        f"https://drive.google.com/uc?id={file_id}",
        f"https://drive.google.com/uc?export=download&id={file_id}",
    ]
    for n in needles:
        html = html.replace(n, site_path)
    html = re.sub(
        rf"https://drive\.google\.com/file/d/{re.escape(file_id)}/[^\s\"'<>]*",
        site_path,
        html,
        flags=re.I,
    )
    return html


# Injected before first </style>: VR screenshot sits in a narrow grid column (2.2fr 1fr); fixed
# width="800" overflows. Drive HTML may still include that attribute.
VR_PHOTO_CSS = """  /* telesvrgery build: responsive VR photo in .photo-slot */
  .photo-slot img {
    max-width: 100%;
    height: auto;
    display: block;
    margin-inline: auto;
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
  }
  .photo-slot:has(> img) {
    min-height: 0;
    align-items: center;
    justify-content: flex-start;
    padding: 12px;
    cursor: default;
  }
  .photo-slot:has(> img):hover {
    border-color: rgba(0, 150, 240, 0.35);
    background: var(--bg-card2);
  }
"""


def inject_vr_photo_css(html: str) -> str:
    if "</style>" not in html:
        return html
    return html.replace("</style>", VR_PHOTO_CSS + "\n</style>", 1)


def strip_fixed_width_on_poster_images(html: str) -> str:
    """Remove width=\"…\" from <img> tags (fixed px widths break the narrow grid column)."""
    return re.sub(r"\s+width=\"\d+\"", "", html)


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
    vr_view_id = img_m.group(1).strip() if img_m else ""
    cyl_m = re.search(r"^\s*telesvrgery_vr_cylinder_image_id:\s*\"([^\"]*)\"", text, re.MULTILINE)
    cylinder_id = cyl_m.group(1).strip() if cyl_m else ""
    out_m = re.search(r"^\s*telesvrgery_output_device_image_id:\s*\"([^\"]*)\"", text, re.MULTILINE)
    output_device_id = out_m.group(1).strip() if out_m else ""
    ph_m = re.search(r"^\s*telesvrgery_vascular_phantom_image_id:\s*\"([^\"]*)\"", text, re.MULTILINE)
    phantom_id = ph_m.group(1).strip() if ph_m else ""

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

    if vr_view_id:
        body = rewrite_drive_asset_urls(body, vr_view_id, VR_IMAGE_SITE_PATH)
    if cylinder_id:
        body = rewrite_drive_asset_urls(body, cylinder_id, CYLINDER_IMAGE_SITE_PATH)
    if output_device_id:
        body = rewrite_drive_asset_urls(body, output_device_id, OUTPUT_DEVICE_IMAGE_SITE_PATH)
    if phantom_id:
        body = rewrite_drive_asset_urls(body, phantom_id, VASCULAR_PHANTOM_IMAGE_SITE_PATH)

    body = inject_vr_photo_css(body)
    body = strip_fixed_width_on_poster_images(body)

    wrapped = (
        "---\nlayout: null\n---\n{% raw %}\n"
        + body
        + "\n{% endraw %}\n"
    )
    (out_dir / "index.html").write_text(wrapped, encoding="utf-8")
    print(f"Wrote {out_dir / 'index.html'}")

    assets_dir = root / "assets" / "telesvrgery"
    assets_dir.mkdir(parents=True, exist_ok=True)

    def download_asset(file_id: str, filename: str, label: str) -> None:
        out = assets_dir / filename
        gdown.download(f"https://drive.google.com/uc?id={file_id}", str(out), quiet=False)
        if not out.exists() or out.stat().st_size == 0:
            print(f"ERROR: {label} download failed or empty ({filename})", file=sys.stderr)
            sys.exit(1)
        print(f"Wrote {out}")

    if vr_view_id:
        download_asset(vr_view_id, "vr-view-1.png", "VR view image")
    if cylinder_id:
        download_asset(cylinder_id, "vr-capsule-1.png", "VR cylinder image")
    if output_device_id:
        download_asset(output_device_id, "output-device-view.png", "Output device view image")
    if phantom_id:
        download_asset(phantom_id, "vascular-phantom-view.png", "Vascular phantom image")


if __name__ == "__main__":
    main()
