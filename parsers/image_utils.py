"""Image processing utilities for document parsers."""
import base64
from io import BytesIO
from typing import Optional
from PIL import Image

# Optimal max edge for Claude/GPT-4o Vision
DEFAULT_MAX_EDGE = 1568

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}

EXTENSION_TO_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".bmp": "image/bmp", ".tiff": "image/tiff",
    ".webp": "image/webp",
}


def resize_image(img: Image.Image, max_edge: int = DEFAULT_MAX_EDGE) -> Image.Image:
    """Resize image so longest edge <= max_edge, preserving aspect ratio."""
    w, h = img.size
    if max(w, h) <= max_edge:
        return img
    scale = max_edge / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    return img.resize((new_w, new_h), Image.LANCZOS)


def pil_to_base64(img: Image.Image, fmt: str = "PNG") -> tuple[str, str]:
    """Convert PIL Image to (base64_string, media_type)."""
    if img.mode == "RGBA" and fmt.upper() == "JPEG":
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    media_type = f"image/{fmt.lower()}"
    if fmt.upper() == "JPEG":
        media_type = "image/jpeg"
    return b64, media_type


def bytes_to_base64_image(image_bytes: bytes, ext: str, max_edge: int = DEFAULT_MAX_EDGE) -> tuple[str, str]:
    """Convert raw image bytes to resized (base64_string, media_type)."""
    img = Image.open(BytesIO(image_bytes))
    img = resize_image(img, max_edge)
    # Choose format based on extension
    ext_lower = ext.lower().lstrip(".")
    fmt = "JPEG" if ext_lower in ("jpg", "jpeg") else "PNG"
    return pil_to_base64(img, fmt)
