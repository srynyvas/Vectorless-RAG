"""Parser registry: maps file extensions to parser instances."""

from parsers.base import BaseParser
from parsers.pdf_parser import PDFParser
from parsers.markdown_parser import MarkdownParser
from parsers.docx_parser import DocxParser
from parsers.pptx_parser import PptxParser
from parsers.txt_parser import TxtParser

# ---------------------------------------------------------------------------
# Internal mapping -- built once at import time.
# Each extension (including the leading dot) maps to a singleton parser.
# ---------------------------------------------------------------------------

_pdf_parser = PDFParser()
_md_parser = MarkdownParser()
_docx_parser = DocxParser()
_pptx_parser = PptxParser()
_txt_parser = TxtParser()

_EXTENSION_MAP: dict[str, BaseParser] = {
    ".pdf": _pdf_parser,
    ".md": _md_parser,
    ".markdown": _md_parser,
    ".docx": _docx_parser,
    ".pptx": _pptx_parser,
    ".txt": _txt_parser,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_parser(file_extension: str) -> BaseParser:
    """Return the parser instance for the given file extension.

    Parameters
    ----------
    file_extension : str
        A file extension **with** the leading dot, e.g. ``".pdf"``.
        Case-insensitive.

    Returns
    -------
    BaseParser
        The parser capable of handling files with that extension.

    Raises
    ------
    ValueError
        If no parser is registered for the given extension.
    """
    ext = file_extension.lower().strip()
    if not ext.startswith("."):
        ext = f".{ext}"

    parser = _EXTENSION_MAP.get(ext)
    if parser is None:
        supported = ", ".join(sorted(_EXTENSION_MAP.keys()))
        raise ValueError(
            f"Unsupported file extension '{file_extension}'. "
            f"Supported extensions: {supported}"
        )
    return parser


def supported_extensions() -> list[str]:
    """Return a sorted list of all supported file extensions."""
    return sorted(_EXTENSION_MAP.keys())
