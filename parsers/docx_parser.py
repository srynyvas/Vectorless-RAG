"""DOCX parser using python-docx to extract sections by heading styles."""

import logging
import os
import re
import zipfile
from pathlib import Path

from docx import Document

from config.settings import settings
from parsers.base import BaseParser, ParsedSection
from parsers.image_utils import bytes_to_base64_image, SUPPORTED_IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)

# Map Word built-in style names to heading levels.
# "Title" is treated as level 0 (document title).
_STYLE_LEVEL_MAP: dict[str, int] = {
    "Title": 0,
    "Heading 1": 1,
    "Heading 2": 2,
    "Heading 3": 3,
    "Heading 4": 4,
    "Heading 5": 5,
    "Heading 6": 6,
    "Heading 7": 7,
    "Heading 8": 8,
    "Heading 9": 9,
}

# Regex fallback for style names that contain "heading" with a digit
_HEADING_STYLE_RE = re.compile(r"[Hh]eading\s*(\d+)")

# XML namespaces used in OOXML documents
_NSMAP = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _style_to_level(style_name: str | None) -> int | None:
    """Convert a paragraph style name to a heading level, or None."""
    if style_name is None:
        return None

    # Direct lookup first
    level = _STYLE_LEVEL_MAP.get(style_name)
    if level is not None:
        return level

    # Regex fallback for variations like "heading 1", "Heading1"
    match = _HEADING_STYLE_RE.search(style_name)
    if match:
        return int(match.group(1))

    return None


def _paragraph_has_images(para) -> bool:
    """Check if a paragraph contains any inline or floating images."""
    try:
        drawings = para._element.findall(".//w:drawing", _NSMAP)
        if drawings:
            return True
        # Also check for legacy VML picture elements
        picts = para._element.findall(".//w:pict", _NSMAP)
        if picts:
            return True
    except Exception:
        pass
    return False


def _get_paragraph_image_rids(para) -> list[str]:
    """Extract relationship IDs for images referenced in a paragraph.

    Looks for <a:blip r:embed="rIdXX"> elements inside drawing elements.
    Returns a list of rId strings.
    """
    rids: list[str] = []
    try:
        blips = para._element.findall(
            ".//a:blip",
            _NSMAP,
        )
        for blip in blips:
            r_embed = blip.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
            )
            if r_embed:
                rids.append(r_embed)
    except Exception:
        pass
    return rids


def _extract_all_media(file_path: str) -> dict[str, dict]:
    """Extract all images from the DOCX zip's word/media/ folder.

    Returns:
        Dict mapping media filename (e.g. "word/media/image1.png") to
        {"data": base64_str, "media_type": str, "caption": str}
    """
    if not settings.EXTRACT_IMAGES:
        return {}
    images: dict[str, dict] = {}
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            for name in z.namelist():
                if name.startswith("word/media/"):
                    ext = os.path.splitext(name)[1].lower()
                    if ext in SUPPORTED_IMAGE_EXTENSIONS:
                        try:
                            raw = z.read(name)
                            b64, media_type = bytes_to_base64_image(
                                raw, ext, settings.IMAGE_MAX_EDGE
                            )
                            images[name] = {
                                "data": b64,
                                "media_type": media_type,
                                "caption": os.path.basename(name),
                            }
                        except Exception as e:
                            logger.debug(
                                "Failed to extract image %s: %s", name, e
                            )
                            continue
    except Exception as e:
        logger.warning("Failed to read media from DOCX zip: %s", e)
    return images


def _build_rid_to_media_map(file_path: str) -> dict[str, str]:
    """Parse word/_rels/document.xml.rels to build rId -> media filename mapping.

    Returns:
        Dict mapping relationship ID (e.g. "rId5") to media path (e.g. "word/media/image1.png").
    """
    rid_map: dict[str, str] = {}
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            rels_path = "word/_rels/document.xml.rels"
            if rels_path not in z.namelist():
                return rid_map
            from lxml import etree

            rels_xml = z.read(rels_path)
            root = etree.fromstring(rels_xml)
            ns = "http://schemas.openxmlformats.org/package/2006/relationships"
            for rel in root.findall(f"{{{ns}}}Relationship"):
                target = rel.get("Target", "")
                rid = rel.get("Id", "")
                if target.startswith("media/"):
                    # Targets are relative to word/ directory
                    rid_map[rid] = "word/" + target
                elif target.startswith("word/media/"):
                    rid_map[rid] = target
    except Exception as e:
        logger.debug("Failed to parse document.xml.rels: %s", e)
    return rid_map


class DocxParser(BaseParser):
    """Parse .docx files by splitting on heading paragraph styles."""

    def supported_extensions(self) -> list[str]:
        return [".docx"]

    def parse(self, file_path: str) -> list[ParsedSection]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"DOCX file not found: {file_path}")
        if path.suffix.lower() != ".docx":
            raise ValueError(f"Not a DOCX file: {file_path}")

        try:
            doc = Document(str(path))
        except Exception as exc:
            raise RuntimeError(f"Failed to open DOCX '{file_path}': {exc}") from exc

        # ----- Extract all media images and build rId mapping -----
        all_media = _extract_all_media(str(path))
        rid_to_media = _build_rid_to_media_map(str(path))

        sections: list[ParsedSection] = []
        current_title: str | None = None
        current_level: int = 0
        body_parts: list[str] = []
        current_images: list[dict] = []

        def _flush() -> None:
            nonlocal current_title, current_level, body_parts, current_images
            text = "\n".join(body_parts).strip()
            # Cap images per section
            section_images = current_images[: settings.MAX_IMAGES_PER_SECTION]
            if current_title is not None:
                sections.append(ParsedSection(
                    title=current_title,
                    text=text,
                    level=current_level,
                    images=section_images,
                ))
            elif text:
                sections.append(ParsedSection(
                    title="Preamble",
                    text=text,
                    level=0,
                    images=section_images,
                ))
            body_parts = []
            current_images = []

        for para in doc.paragraphs:
            style_name = para.style.name if para.style else None
            level = _style_to_level(style_name)

            if level is not None:
                _flush()
                current_title = para.text.strip() or "(Untitled)"
                current_level = level
            else:
                para_text = para.text.strip()
                if para_text:
                    body_parts.append(para_text)

            # Check for images in this paragraph and associate with current section
            if settings.EXTRACT_IMAGES and all_media:
                rids = _get_paragraph_image_rids(para)
                for rid in rids:
                    media_path = rid_to_media.get(rid)
                    if media_path and media_path in all_media:
                        if len(current_images) < settings.MAX_IMAGES_PER_SECTION:
                            current_images.append(all_media[media_path])

        # Flush the last accumulated section
        _flush()

        # ----- Distribute unattached images if none were matched via rIds -----
        # If rId mapping failed to match any images to sections but we have
        # media files, distribute them across sections as a fallback.
        total_attached = sum(len(s.images) for s in sections)
        if total_attached == 0 and all_media and sections:
            media_list = list(all_media.values())
            # Distribute images evenly: assign to sections round-robin
            for idx, img_dict in enumerate(media_list):
                target_section = sections[idx % len(sections)]
                if len(target_section.images) < settings.MAX_IMAGES_PER_SECTION:
                    target_section.images.append(img_dict)

        return sections
