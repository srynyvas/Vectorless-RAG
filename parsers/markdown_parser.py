"""Markdown parser that splits content into sections by ATX headings (# style)."""

import re
from pathlib import Path

from parsers.base import BaseParser, ParsedSection

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)")


class MarkdownParser(BaseParser):
    """Parse Markdown files by splitting on ATX-style headings."""

    def supported_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def parse(self, file_path: str) -> list[ParsedSection]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")
        if path.suffix.lower() not in self.supported_extensions():
            raise ValueError(f"Not a Markdown file: {file_path}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Retry with latin-1 as a broad fallback
            content = path.read_text(encoding="latin-1")

        lines = content.split("\n")
        sections: list[ParsedSection] = []

        # Track the current heading and body lines being accumulated
        current_title: str | None = None
        current_level: int = 0
        body_lines: list[str] = []

        def _flush() -> None:
            """Flush accumulated body lines into a ParsedSection."""
            nonlocal current_title, current_level, body_lines
            text = "\n".join(body_lines).strip()
            if current_title is not None:
                sections.append(ParsedSection(
                    title=current_title,
                    text=text,
                    level=current_level,
                ))
            elif text:
                # Text before the first heading becomes a preamble section.
                sections.append(ParsedSection(
                    title="Preamble",
                    text=text,
                    level=0,
                ))
            body_lines = []

        for line in lines:
            match = _HEADING_RE.match(line)
            if match:
                _flush()
                hashes = match.group(1)
                title = match.group(2).strip()
                current_title = title
                current_level = len(hashes)
            else:
                body_lines.append(line)

        # Flush the last section
        _flush()

        return sections
