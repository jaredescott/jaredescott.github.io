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


POSTER_PDF_CSS = """  .poster-pdf-bar {
    margin-bottom: 20px;
    padding-bottom: 18px;
    border-bottom: 1px solid rgba(0, 100, 200, 0.22);
  }
  .poster-pdf-frame {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 10;
    max-height: min(72vh, 680px);
    min-height: 280px;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(0, 150, 240, 0.28);
    background: var(--bg-card2);
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.35);
  }
  .poster-pdf-frame iframe {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
  }
"""


def inject_printable_poster_pdf(html: str, pdf_id: str) -> str:
    """Embed overview PDF directly below .header (above Figure 1 row). Relocates if Drive HTML still has it on top."""
    if not pdf_id.strip():
        return html
    if ".poster-pdf-frame" not in html and "</style>" in html:
        html = html.replace("</style>", POSTER_PDF_CSS + "\n</style>", 1)

    block = f"""
  <section class="poster-pdf-bar" aria-label="Project poster PDF">
    <div class="sec-label">Printable poster — PDF</div>
    <div class="poster-pdf-frame">
      <iframe title="AWE XR Telesvrgery poster (PDF)" src="https://drive.google.com/file/d/{pdf_id}/preview" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
    </div>
  </section>

"""
    # Drop any existing bar so we can place once below header (handles old "PDF first" Drive copies).
    html = re.sub(
        r'\s*<!-- Printable PDF[^\n]*-->\s*\n\s*<section class="poster-pdf-bar"[\s\S]*?</section>\s*',
        "\n",
        html,
        count=1,
    )
    html = re.sub(
        r'\s*<section class="poster-pdf-bar"[\s\S]*?</section>\s*',
        "\n",
        html,
        count=1,
    )

    row1_full = "<!-- ═══════════════════════════════════════════════════════════ ROW 1: SYSTEM ARCHITECTURE -->"
    markers = (
        "  " + row1_full,
        "\n" + row1_full,
        row1_full,
        "  <!-- ═══════════════════════════════════════════════════════════ ROW 1:",
        "<!-- ═══════════════════════════════════════════════════════════ ROW 1:",
    )
    for marker in markers:
        if marker in html:
            html = html.replace(marker, block + "\n\n" + marker, 1)
            return html
    # Fallback: locate ROW 1 comment line regardless of leading whitespace
    m = re.search(
        r"^[\t ]*<!-- ═+ ROW 1:[^\n]+-->",
        html,
        re.MULTILINE,
    )
    if m:
        line = m.group(0)
        html = html.replace(line, block + "\n\n" + line, 1)
        return html
    if '<div class="poster">' in html:
        html = html.replace('<div class="poster">', '<div class="poster">\n\n' + block, 1)
    return html


def normalize_figure_caption_prefixes(html: str) -> str:
    """Remove legacy PHOTO — / SCREENSHOT — prefixes from figure captions."""
    for old, new in (
        ("PHOTO — VR OPERATOR VIEW", "VR OPERATING ROOM VIEW"),
        ("VR OPERATOR VIEW", "VR OPERATING ROOM VIEW"),
        ('alt="VR operator view"', 'alt="VR operating room view"'),
        ("SCREENSHOT — VIRTUAL CYLINDER", "VIRTUAL CYLINDER"),
        ("PHOTO — OUTPUT DEVICE", "OUTPUT DEVICE"),
        ("PHOTO — VASCULAR PHANTOM", "VASCULAR PHANTOM"),
    ):
        html = html.replace(old, new)
    return html


def ensure_vr_operating_room_caption(html: str) -> str:
    """Add VR OPERATING ROOM VIEW caption under first VR img if missing."""
    if 'margin-top:10px;">VR OPERATING ROOM VIEW</div>' in html:
        return html
    cap = '\n        <div class="ps-label" style="margin-top:10px;">VR OPERATING ROOM VIEW</div>'
    esc = re.escape(VR_IMAGE_SITE_PATH)
    pat = rf'(<img\s+[\s\S]*?src="{esc}"[\s\S]*?/>)\s*(\n\s*</div>)'
    nhtml, n = re.subn(pat, r"\1" + cap + r"\2", html, count=1, flags=re.I)
    if n:
        return nhtml
    # Before URL rewrite (e.g. local Drive copy): match by file id
    vid = "1cMX1lEvc3eMHahnLLKPM4LJd4Z0ACV9D"
    pat2 = rf'(<img\s+[\s\S]*?{re.escape(vid)}[\s\S]*?/>)\s*(\n\s*</div>)'
    nhtml, n = re.subn(pat2, r"\1" + cap + r"\2", html, count=1, flags=re.I)
    return nhtml if n else html


def ensure_standard_image_captions(html: str) -> str:
    """Add short figure labels (no PHOTO/SCREENSHOT prefix) when img exists but caption is missing."""
    if 'margin-top:10px;">VIRTUAL CYLINDER</div>' not in html and "vr-capsule-1.png" in html:
        esc = re.escape(CYLINDER_IMAGE_SITE_PATH)
        pat = rf'(<img\s+[\s\S]*?src="{esc}"[\s\S]*?/>)\s*(\n\s*</div>)'
        cap = '\n        <div class="ps-label" style="margin-top:10px;">VIRTUAL CYLINDER</div>'
        html, _ = re.subn(pat, r"\1" + cap + r"\2", html, count=1, flags=re.I)
    if 'margin-top:10px;">OUTPUT DEVICE</div>' not in html and "output-device-view.png" in html:
        esc = re.escape(OUTPUT_DEVICE_IMAGE_SITE_PATH)
        pat = rf'(<img\s+[\s\S]*?src="{esc}"[\s\S]*?/>)\s*(\n\s*</div>)'
        cap = '\n        <div class="ps-label" style="margin-top:10px;">OUTPUT DEVICE</div>'
        html, _ = re.subn(pat, r"\1" + cap + r"\2", html, count=1, flags=re.I)
    if 'margin-top:10px;">VASCULAR PHANTOM</div>' not in html and "vascular-phantom-view.png" in html:
        esc = re.escape(VASCULAR_PHANTOM_IMAGE_SITE_PATH)
        pat = rf'(<img\s+[\s\S]*?src="{esc}"[\s\S]*?/>)\s*(\n\s*</div>)'
        cap = '\n        <div class="ps-label" style="margin-top:10px;">VASCULAR PHANTOM</div>'
        html, _ = re.subn(pat, r"\1" + cap + r"\2", html, count=1, flags=re.I)
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
    vr_view_id = img_m.group(1).strip() if img_m else ""
    cyl_m = re.search(r"^\s*telesvrgery_vr_cylinder_image_id:\s*\"([^\"]*)\"", text, re.MULTILINE)
    cylinder_id = cyl_m.group(1).strip() if cyl_m else ""
    out_m = re.search(r"^\s*telesvrgery_output_device_image_id:\s*\"([^\"]*)\"", text, re.MULTILINE)
    output_device_id = out_m.group(1).strip() if out_m else ""
    ph_m = re.search(r"^\s*telesvrgery_vascular_phantom_image_id:\s*\"([^\"]*)\"", text, re.MULTILINE)
    phantom_id = ph_m.group(1).strip() if ph_m else ""
    pdf_m = re.search(r"^\s*telesvrgery_poster_pdf_id:\s*\"([^\"]*)\"", text, re.MULTILINE)
    poster_pdf_id = pdf_m.group(1).strip() if pdf_m else ""

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

    body = inject_printable_poster_pdf(body, poster_pdf_id)

    if vr_view_id:
        body = rewrite_drive_asset_urls(body, vr_view_id, VR_IMAGE_SITE_PATH)
    if cylinder_id:
        body = rewrite_drive_asset_urls(body, cylinder_id, CYLINDER_IMAGE_SITE_PATH)
    if output_device_id:
        body = rewrite_drive_asset_urls(body, output_device_id, OUTPUT_DEVICE_IMAGE_SITE_PATH)
    if phantom_id:
        body = rewrite_drive_asset_urls(body, phantom_id, VASCULAR_PHANTOM_IMAGE_SITE_PATH)

    body = normalize_figure_caption_prefixes(body)

    body = ensure_vr_operating_room_caption(body)
    body = ensure_standard_image_captions(body)

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
