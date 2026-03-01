"""PDF parser using pypdfium2 for text extraction with heuristic heading detection."""

import logging
import re
from pathlib import Path

import pypdfium2 as pdfium

from config.settings import settings
from parsers.base import BaseParser, ParsedSection
from parsers.image_utils import resize_image, pil_to_base64

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Heading heuristic helpers
# ---------------------------------------------------------------------------

_CHAPTER_RE = re.compile(
    r"^(chapter|part|section|appendix)\s+(\d+|[IVXLCDM]+)",
    re.IGNORECASE,
)

_NUMBERED_HEADING_RE = re.compile(
    r"^\d+(\.\d+)*\.?\s+\S",  # e.g. "1.2 Introduction"
)


def _is_allcaps_heading(line: str) -> bool:
    """Return True if the line looks like an ALL-CAPS heading."""
    stripped = line.strip()
    if not stripped or len(stripped) < 3:
        return False
    # Must be predominantly alphabetical and uppercase
    alpha_chars = [c for c in stripped if c.isalpha()]
    if len(alpha_chars) < 3:
        return False
    return all(c.isupper() or not c.isalpha() for c in stripped) and len(stripped) <= 120


def _is_titlecase_heading(line: str) -> bool:
    """Return True if the line is a short Title Case line (likely a heading)."""
    stripped = line.strip()
    if not stripped or len(stripped) > 100 or len(stripped) < 3:
        return False
    words = stripped.split()
    if len(words) > 12:
        return False
    # Title Case: most words start with uppercase
    title_words = [w for w in words if w[0].isupper()]
    # At least 60% of words should be title-cased
    return len(title_words) / len(words) >= 0.6


def _detect_heading(line: str) -> tuple[bool, int]:
    """Detect whether a line is a heading and return (is_heading, level).

    Level guide:
        1 - Chapter / Part / ALL-CAPS major heading
        2 - Title-case heading or numbered heading (e.g. 1.2 Foo)
        3 - Other minor headings
    """
    stripped = line.strip()
    if not stripped:
        return False, 0

    if _CHAPTER_RE.match(stripped):
        return True, 1

    if _is_allcaps_heading(stripped):
        return True, 1

    if _NUMBERED_HEADING_RE.match(stripped):
        # Depth from dotted number: "1" -> level 1, "1.2" -> level 2, etc.
        num_part = stripped.split()[0].rstrip(".")
        depth = num_part.count(".") + 1
        level = min(depth, 4)
        return True, level

    if _is_titlecase_heading(stripped):
        return True, 2

    return False, 0


# ---------------------------------------------------------------------------
# PDFParser
# ---------------------------------------------------------------------------

class PDFParser(BaseParser):
    """Parse PDF files using pypdfium2 with heuristic heading detection."""

    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    # ------------------------------------------------------------------
    # Image extraction helpers
    # ------------------------------------------------------------------

    def _get_image_pages(self, pdf) -> set[int]:
        """Return set of 1-based page numbers that contain image objects."""
        image_pages: set[int] = set()
        if not settings.EXTRACT_IMAGES:
            return image_pages
        for page_idx in range(len(pdf)):
            try:
                page = pdf[page_idx]
                for obj in page.get_objects():
                    if obj.type == pdfium.raw.FPDF_PAGEOBJ_IMAGE:
                        image_pages.add(page_idx + 1)  # 1-based
                        break  # one image object is enough to flag the page
            except Exception:
                pass
        return image_pages

    def _render_page_image(self, pdf, page_idx: int) -> dict | None:
        """Render a page to a base64 image dict."""
        try:
            page = pdf[page_idx]
            bitmap = page.render(scale=2)
            pil_img = bitmap.to_pil()
            pil_img = resize_image(pil_img, settings.IMAGE_MAX_EDGE)
            b64, media_type = pil_to_base64(pil_img, "PNG")
            return {
                "data": b64,
                "media_type": media_type,
                "caption": f"Page {page_idx + 1} visual content",
            }
        except Exception as e:
            logger.warning("Failed to render page %d image: %s", page_idx + 1, e)
            return None

    # ------------------------------------------------------------------
    # Main parse
    # ------------------------------------------------------------------

    def parse(self, file_path: str) -> list[ParsedSection]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {file_path}")

        try:
            pdf = pdfium.PdfDocument(str(path))
        except Exception as exc:
            raise RuntimeError(f"Failed to open PDF '{file_path}': {exc}") from exc

        try:
            # ----- Extract text per page -----
            page_texts: list[tuple[int, str]] = []
            for page_idx in range(len(pdf)):
                page = pdf[page_idx]
                try:
                    text = page.get_textpage().get_text_range()
                except Exception:
                    text = ""
                page_texts.append((page_idx + 1, text))  # 1-based page numbers

            # ----- Detect pages with images (before closing pdf) -----
            image_pages = self._get_image_pages(pdf)

            # ----- Render image pages to base64 (before closing pdf) -----
            # Map: 1-based page_num -> image dict
            rendered_images: dict[int, dict] = {}
            if image_pages:
                for page_num in image_pages:
                    img_dict = self._render_page_image(pdf, page_num - 1)
                    if img_dict is not None:
                        rendered_images[page_num] = img_dict
        finally:
            pdf.close()

        # ----- First pass: detect headings across all pages -----
        heading_entries: list[dict] = []  # {title, level, page, line_idx_in_page}
        all_lines_by_page: list[list[str]] = []

        for page_num, text in page_texts:
            lines = text.split("\n")
            all_lines_by_page.append(lines)
            for line_idx, line in enumerate(lines):
                is_heading, level = _detect_heading(line)
                if is_heading:
                    heading_entries.append({
                        "title": line.strip(),
                        "level": level,
                        "page": page_num,
                        "page_list_idx": page_num - 1,
                        "line_idx": line_idx,
                    })

        # ----- Fallback: chunk by page if fewer than 2 headings -----
        if len(heading_entries) < 2:
            sections = self._chunk_by_page(page_texts)
            self._attach_images_to_sections(sections, rendered_images)
            return sections

        # ----- Build sections from headings -----
        sections: list[ParsedSection] = []

        # Collect text before the first heading as a preamble (if any)
        first = heading_entries[0]
        preamble_lines: list[str] = []
        for pi in range(first["page_list_idx"]):
            preamble_lines.extend(all_lines_by_page[pi])
        preamble_lines.extend(all_lines_by_page[first["page_list_idx"]][:first["line_idx"]])
        preamble_text = "\n".join(preamble_lines).strip()
        if preamble_text:
            sections.append(ParsedSection(
                title="Preamble",
                text=preamble_text,
                level=0,
                page_number=1,
            ))

        # For each heading, collect text until the next heading
        for i, entry in enumerate(heading_entries):
            if i + 1 < len(heading_entries):
                next_entry = heading_entries[i + 1]
            else:
                next_entry = None

            body_lines: list[str] = []

            start_page_idx = entry["page_list_idx"]
            start_line = entry["line_idx"] + 1  # skip the heading line itself

            if next_entry is None:
                # Collect until end of document
                for pi in range(start_page_idx, len(all_lines_by_page)):
                    sl = start_line if pi == start_page_idx else 0
                    body_lines.extend(all_lines_by_page[pi][sl:])
            else:
                end_page_idx = next_entry["page_list_idx"]
                end_line = next_entry["line_idx"]

                if start_page_idx == end_page_idx:
                    body_lines.extend(
                        all_lines_by_page[start_page_idx][start_line:end_line]
                    )
                else:
                    # Rest of start page
                    body_lines.extend(all_lines_by_page[start_page_idx][start_line:])
                    # Full intermediate pages
                    for pi in range(start_page_idx + 1, end_page_idx):
                        body_lines.extend(all_lines_by_page[pi])
                    # Beginning of end page up to next heading
                    body_lines.extend(all_lines_by_page[end_page_idx][:end_line])

            body_text = "\n".join(body_lines).strip()
            sections.append(ParsedSection(
                title=entry["title"],
                text=body_text,
                level=entry["level"],
                page_number=entry["page"],
            ))

        # ----- Attach rendered images to sections -----
        self._attach_images_to_sections(sections, rendered_images)

        return sections

    # ------------------------------------------------------------------
    # Image-to-section attachment
    # ------------------------------------------------------------------

    @staticmethod
    def _attach_images_to_sections(
        sections: list[ParsedSection],
        rendered_images: dict[int, dict],
    ) -> None:
        """Attach rendered page images to sections that span those pages."""
        if not rendered_images:
            return

        for section in sections:
            if section.page_number is None:
                continue
            # A section starts at section.page_number.  We attach an image
            # if that page was rendered.
            page_num = section.page_number
            if page_num in rendered_images:
                if len(section.images) < settings.MAX_IMAGES_PER_SECTION:
                    section.images.append(rendered_images[page_num])

        # Also handle multi-page sections: walk through remaining rendered
        # images and attach to the last section whose page_number <= image page.
        # Build a sorted list of sections with page numbers for lookup.
        if not sections:
            return

        sorted_sections = sorted(
            [(s.page_number or 0, s) for s in sections],
            key=lambda x: x[0],
        )

        for img_page, img_dict in sorted_images_items(rendered_images):
            # Find the section that owns this page (last section with page <= img_page)
            target_section = None
            for sec_page, sec in sorted_sections:
                if sec_page <= img_page:
                    target_section = sec
                else:
                    break
            if target_section is not None:
                # Only add if not already attached and under cap
                if (img_dict not in target_section.images
                        and len(target_section.images) < settings.MAX_IMAGES_PER_SECTION):
                    target_section.images.append(img_dict)

    # ------------------------------------------------------------------
    @staticmethod
    def _chunk_by_page(page_texts: list[tuple[int, str]]) -> list[ParsedSection]:
        """Fallback: one section per page."""
        sections: list[ParsedSection] = []
        for page_num, text in page_texts:
            text = text.strip()
            if text:
                sections.append(ParsedSection(
                    title=f"Page {page_num}",
                    text=text,
                    level=1,
                    page_number=page_num,
                ))
        return sections


def sorted_images_items(rendered_images: dict[int, dict]) -> list[tuple[int, dict]]:
    """Return rendered_images items sorted by page number."""
    return sorted(rendered_images.items(), key=lambda x: x[0])
