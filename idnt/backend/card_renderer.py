# =============================================================================
# IDNT Digital ID Card Renderer
# =============================================================================
# Install: pip install Pillow qrcode[pil] numpy
# Usage:
#   from card_renderer import render_id_card
#   card_png = render_id_card(photo_bytes, employee_data)
#
# Standalone test:
#   python card_renderer.py  (generates sample_card.png)
# =============================================================================

from __future__ import annotations

import io
import json
import math
import random
from typing import Optional, Tuple

import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CARD_W = 1012
CARD_H = 638
CORNER_RADIUS = 20

COLOR_BG_TOP_LEFT = (0x1A, 0x1A, 0x1A)
COLOR_BG_BOTTOM_RIGHT = (0x0D, 0x0D, 0x0D)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (0x8E, 0x8E, 0x93)
COLOR_LIGHT_GRAY = (0x63, 0x63, 0x66)
COLOR_BORDER = (0x33, 0x33, 0x33)

# ---------------------------------------------------------------------------
# Font helpers — fall back gracefully across platforms
# ---------------------------------------------------------------------------

_FONT_CACHE: dict[str, ImageFont.FreeTypeFont] = {}


def _load_font(style: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType font with fallback chain.

    *style* is one of ``"bold"``, ``"regular"``, ``"mono"``.
    """
    key = f"{style}_{size}"
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates: dict[str, list[str]] = {
        "bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ],
        "regular": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ],
        "mono": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/System/Library/Fonts/Courier.dfont",
        ],
    }

    for path in candidates.get(style, candidates["regular"]):
        try:
            font = ImageFont.truetype(path, size)
            _FONT_CACHE[key] = font
            return font
        except (OSError, IOError):
            continue

    # Ultimate fallback — Pillow built-in bitmap font (no sizing control)
    font = ImageFont.load_default()  # type: ignore[assignment]
    _FONT_CACHE[key] = font
    return font


# ---------------------------------------------------------------------------
# Background & texture
# ---------------------------------------------------------------------------

def _make_gradient(width: int, height: int) -> Image.Image:
    """Create a diagonal linear gradient from top-left to bottom-right."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    r1, g1, b1 = COLOR_BG_TOP_LEFT
    r2, g2, b2 = COLOR_BG_BOTTOM_RIGHT
    for y in range(height):
        for x in range(width):
            t = (x / width + y / height) / 2.0
            arr[y, x] = (
                int(r1 + (r2 - r1) * t),
                int(g1 + (g2 - g1) * t),
                int(b1 + (b2 - b1) * t),
            )
    return Image.fromarray(arr, "RGB")


def add_metal_texture(image: Image.Image, intensity: float = 0.03) -> Image.Image:
    """Add subtle noise texture for metal feel.

    *intensity* controls the amplitude of the noise (0.0 -- 1.0).
    """
    arr = np.array(image, dtype=np.int16)
    noise = np.random.default_rng(42).integers(
        -int(255 * intensity), int(255 * intensity) + 1, arr.shape, dtype=np.int16
    )
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, image.mode)


def _round_rect_mask(width: int, height: int, radius: int) -> Image.Image:
    """Return an anti-aliased rounded-rectangle alpha mask."""
    scale = 4  # supersample for smooth edges
    big = Image.new("L", (width * scale, height * scale), 0)
    draw = ImageDraw.Draw(big)
    draw.rounded_rectangle(
        [0, 0, width * scale - 1, height * scale - 1],
        radius=radius * scale,
        fill=255,
    )
    return big.resize((width, height), Image.LANCZOS)


def _make_card_base() -> Image.Image:
    """Create the card background with gradient, texture, and rounded border."""
    gradient = _make_gradient(CARD_W, CARD_H)
    gradient = add_metal_texture(gradient, intensity=0.03)

    # Apply rounded corners via alpha channel
    mask = _round_rect_mask(CARD_W, CARD_H, CORNER_RADIUS)
    card = gradient.convert("RGBA")
    card.putalpha(mask)

    # Draw 1px rounded rectangle border
    border_overlay = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(border_overlay)
    draw.rounded_rectangle(
        [0, 0, CARD_W - 1, CARD_H - 1],
        radius=CORNER_RADIUS,
        outline=(*COLOR_BORDER, 255),
        width=1,
    )
    card = Image.alpha_composite(card, border_overlay)
    return card


# ---------------------------------------------------------------------------
# Photo helpers
# ---------------------------------------------------------------------------

def create_circular_photo(photo_bytes: bytes, size: int = 180) -> Image.Image:
    """Crop photo to circle with anti-aliased mask and white border + glow.

    Returns an RGBA image of *size* x *size* pixels (plus border padding).
    """
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")

    # Centre-crop to square
    min_dim = min(img.width, img.height)
    left = (img.width - min_dim) // 2
    top = (img.height - min_dim) // 2
    img = img.crop((left, top, left + min_dim, top + min_dim))
    img = img.resize((size, size), Image.LANCZOS)

    # Anti-aliased circular mask (supersample)
    scale = 4
    big_mask = Image.new("L", (size * scale, size * scale), 0)
    draw = ImageDraw.Draw(big_mask)
    draw.ellipse([0, 0, size * scale - 1, size * scale - 1], fill=255)
    circle_mask = big_mask.resize((size, size), Image.LANCZOS)

    img.putalpha(circle_mask)

    # Build output with border and glow
    border_w = 2
    glow_r = 6
    total = size + (border_w + glow_r) * 2
    out = Image.new("RGBA", (total, total), (0, 0, 0, 0))

    # Glow: white ellipse blurred
    glow_layer = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    pad = glow_r
    gd.ellipse(
        [pad, pad, total - pad - 1, total - pad - 1],
        fill=(255, 255, 255, 40),
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_r))
    out = Image.alpha_composite(out, glow_layer)

    # White border ring
    ring_layer = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring_layer)
    offset = glow_r
    rd.ellipse(
        [offset, offset, total - offset - 1, total - offset - 1],
        fill=(255, 255, 255, 200),
    )
    inner_offset = offset + border_w
    rd.ellipse(
        [inner_offset, inner_offset, total - inner_offset - 1, total - inner_offset - 1],
        fill=(0, 0, 0, 0),
    )
    out = Image.alpha_composite(out, ring_layer)

    # Paste photo centred
    paste_offset = border_w + glow_r
    out.paste(img, (paste_offset, paste_offset), img)
    return out


# ---------------------------------------------------------------------------
# QR code
# ---------------------------------------------------------------------------

def generate_qr_code(data: str, size: int = 120, opacity: float = 0.5) -> Image.Image:
    """Generate semi-transparent white QR code on transparent background."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="white", back_color="black").convert("RGBA")
    qr_img = qr_img.resize((size, size), Image.LANCZOS)

    # Make black pixels fully transparent; white pixels at *opacity*
    arr = np.array(qr_img)
    # Where the pixel is white-ish
    white_mask = arr[:, :, 0] > 128
    alpha = np.where(white_mask, int(255 * opacity), 0).astype(np.uint8)
    # Set RGB to white everywhere visible
    arr[:, :, 0] = np.where(white_mask, 255, 0)
    arr[:, :, 1] = np.where(white_mask, 255, 0)
    arr[:, :, 2] = np.where(white_mask, 255, 0)
    arr[:, :, 3] = alpha
    return Image.fromarray(arr, "RGBA")


# ---------------------------------------------------------------------------
# Text effects
# ---------------------------------------------------------------------------

def add_embossed_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    position: Tuple[int, int],
    font: ImageFont.FreeTypeFont,
    color: Tuple[int, ...] = COLOR_WHITE,
    shadow_offset: Tuple[int, int] = (2, 2),
) -> None:
    """Draw text with a subtle shadow to simulate laser-engraved / embossed effect."""
    sx, sy = shadow_offset
    x, y = position
    # Dark shadow underneath
    shadow_color = (0, 0, 0, 180)
    draw.text((x + sx, y + sy), text, font=font, fill=shadow_color)
    # Main text on top
    draw.text(position, text, font=font, fill=color)


# ---------------------------------------------------------------------------
# Contactless / NFC icon (card back)
# ---------------------------------------------------------------------------

def _draw_nfc_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 60) -> None:
    """Draw a simplified contactless payment / NFC symbol."""
    # Three concentric arcs + small circle
    for i, radius in enumerate([size, size * 0.66, size * 0.33]):
        r = int(radius)
        bbox = [cx - r, cy - r, cx + r, cy + r]
        draw.arc(bbox, start=-45, end=45, fill=(*COLOR_GRAY, 200), width=3)
    # Centre dot
    dot_r = 4
    draw.ellipse(
        [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
        fill=(*COLOR_GRAY, 255),
    )


# ---------------------------------------------------------------------------
# Barcode (Code128-style drawn manually — avoids extra dependency)
# ---------------------------------------------------------------------------

def _draw_barcode(
    image: Image.Image,
    data: str,
    x: int,
    y: int,
    width: int = 300,
    height: int = 60,
) -> None:
    """Draw a Code128-like barcode.

    This generates a visually convincing barcode pattern derived from *data*.
    For production scanning accuracy you would use ``python-barcode``, but this
    avoids the extra dependency.
    """
    draw = ImageDraw.Draw(image)
    # Seed from data for deterministic pattern
    rng = random.Random(data)
    bar_x = x
    while bar_x < x + width:
        bar_w = rng.choice([1, 2, 3])
        is_bar = rng.choice([True, False])
        if is_bar:
            draw.rectangle(
                [bar_x, y, bar_x + bar_w - 1, y + height],
                fill=(200, 200, 200, 200),
            )
        bar_x += bar_w

    # Text below barcode
    font = _load_font("mono", 12)
    text_w = draw.textlength(data, font=font)
    draw.text(
        (x + (width - text_w) / 2, y + height + 6),
        data,
        font=font,
        fill=(*COLOR_LIGHT_GRAY, 255),
    )


# ---------------------------------------------------------------------------
# Card front
# ---------------------------------------------------------------------------

def _render_front(
    photo_bytes: Optional[bytes],
    employee_data: dict,
) -> Image.Image:
    """Render the front of the ID card."""
    card = _make_card_base()
    draw = ImageDraw.Draw(card)

    name: str = employee_data.get("name", "Unknown")
    department: str = employee_data.get("department", "")
    position: str = employee_data.get("position", "")
    employee_number: str = employee_data.get("employee_number", "EMP-0000-000000")
    company_name: str = employee_data.get("company_name", "IDNT")
    valid_thru: str = employee_data.get("valid_thru", "03/27")

    # 1. Logo — top-left
    font_logo = _load_font("bold", 32)
    add_embossed_text(draw, "IDNT", (60, 40), font_logo, COLOR_WHITE, (2, 2))

    # 2. Employee photo
    if photo_bytes:
        photo = create_circular_photo(photo_bytes, size=180)
        # Centre of circle at (160, 320)
        px = 160 - photo.width // 2
        py = 320 - photo.height // 2
        card.paste(photo, (px, py), photo)

    # 3. Employee name
    font_name = _load_font("bold", 36)
    add_embossed_text(draw, name, (300, 260), font_name, COLOR_WHITE, (2, 2))

    # 4. Department | Position
    dept_pos = " | ".join(filter(None, [department, position]))
    if dept_pos:
        font_dept = _load_font("regular", 18)
        draw.text((300, 310), dept_pos, font=font_dept, fill=(*COLOR_GRAY, 255))

    # 5. Employee ID number
    font_id = _load_font("mono", 14)
    draw.text((300, 360), employee_number, font=font_id, fill=(*COLOR_LIGHT_GRAY, 255))

    # 6. QR code — bottom-right
    qr_data = json.dumps(
        {
            "name": name,
            "department": department,
            "position": position,
            "id": employee_number,
        },
        ensure_ascii=False,
    )
    qr_img = generate_qr_code(qr_data, size=120, opacity=0.5)
    qr_x = 860 - qr_img.width // 2
    qr_y = 490 - qr_img.height // 2
    card.paste(qr_img, (qr_x, qr_y), qr_img)

    # 7. Expiry / VALID THRU
    font_label = _load_font("regular", 10)
    font_date = _load_font("regular", 16)
    draw.text((60, 568), "VALID THRU", font=font_label, fill=(*COLOR_GRAY, 255))
    draw.text((60, 584), valid_thru, font=font_date, fill=(*COLOR_WHITE, 255))

    return card


# ---------------------------------------------------------------------------
# Card back
# ---------------------------------------------------------------------------

def _render_back(employee_data: dict) -> Image.Image:
    """Render the back of the ID card."""
    card = _make_card_base()
    draw = ImageDraw.Draw(card)

    employee_number: str = employee_data.get("employee_number", "EMP-0000-000000")
    company_name: str = employee_data.get("company_name", "IDNT")

    # 1. NFC icon — top-centre
    _draw_nfc_icon(draw, cx=CARD_W // 2, cy=100, size=50)

    # 2. Barcode — centre
    barcode_w = 320
    barcode_x = (CARD_W - barcode_w) // 2
    _draw_barcode(card, employee_number, barcode_x, 260, width=barcode_w, height=70)

    # 3. "IDNT Digital Identity"
    font_brand = _load_font("regular", 16)
    brand_text = "IDNT Digital Identity"
    brand_w = draw.textlength(brand_text, font=font_brand)
    draw.text(
        ((CARD_W - brand_w) / 2, 510),
        brand_text,
        font=font_brand,
        fill=(*COLOR_GRAY, 255),
    )

    # 4. Company info line
    font_info = _load_font("regular", 11)
    info_text = f"{company_name}  \u00b7  Authorized Digital Identification  \u00b7  idnt.io"
    info_w = draw.textlength(info_text, font=font_info)
    draw.text(
        ((CARD_W - info_w) / 2, 545),
        info_text,
        font=font_info,
        fill=(*COLOR_LIGHT_GRAY, 255),
    )

    return card


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def render_id_card(
    photo_bytes: Optional[bytes],
    employee_data: dict,
    card_type: str = "front",
) -> bytes:
    """Render an ID card and return PNG bytes.

    This function is async-compatible for use with FastAPI. The actual
    rendering is CPU-bound and runs synchronously, but the async signature
    allows seamless integration with the async pipeline in main.py.

    Parameters
    ----------
    photo_bytes:
        Raw image bytes for the employee photo (JPEG / PNG).
        May be ``None`` when rendering the back of the card.
    employee_data:
        Dictionary containing at minimum:
        ``name``, ``department``, ``position``, ``employee_number``,
        ``company_name``.  Optional: ``valid_thru`` (e.g. ``"03/27"``)
        or ``expires_at`` (datetime / ISO string, auto-converted to MM/YY).
    card_type:
        ``"front"`` or ``"back"``.

    Returns
    -------
    bytes
        PNG-encoded image of the card.
    """
    # Auto-convert expires_at to valid_thru if not explicitly provided
    if "valid_thru" not in employee_data and "expires_at" in employee_data:
        from datetime import datetime as _dt
        exp = employee_data["expires_at"]
        if isinstance(exp, _dt):
            employee_data = {**employee_data, "valid_thru": exp.strftime("%m/%y")}
        elif isinstance(exp, str):
            try:
                employee_data = {**employee_data, "valid_thru": _dt.fromisoformat(exp).strftime("%m/%y")}
            except ValueError:
                pass

    if card_type == "back":
        card = _render_back(employee_data)
    else:
        card = _render_front(photo_bytes, employee_data)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Standalone demo
# ---------------------------------------------------------------------------

def _generate_placeholder_photo(initials: str = "KD", size: int = 400) -> bytes:
    """Create a simple coloured circle with initials as a placeholder photo."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Teal circle
    draw.ellipse([0, 0, size - 1, size - 1], fill=(0, 122, 255, 255))
    font = _load_font("bold", size // 3)
    tw = draw.textlength(initials, font=font)
    bbox = font.getbbox(initials)
    th = bbox[3] - bbox[1]
    draw.text(
        ((size - tw) / 2, (size - th) / 2 - bbox[1]),
        initials,
        font=font,
        fill=COLOR_WHITE,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    sample_data = {
        "name": "김도윤",
        "department": "Engineering",
        "position": "Senior Developer",
        "employee_number": "EMP-2024-001234",
        "company_name": "IDNT Corp.",
        "valid_thru": "03/27",
    }

    photo = _generate_placeholder_photo("KD")

    front_png = render_id_card(photo, sample_data, card_type="front")
    with open("sample_card_front.png", "wb") as f:
        f.write(front_png)
    print(f"Saved sample_card_front.png ({len(front_png):,} bytes)")

    back_png = render_id_card(None, sample_data, card_type="back")
    with open("sample_card_back.png", "wb") as f:
        f.write(back_png)
    print(f"Saved sample_card_back.png ({len(back_png):,} bytes)")
