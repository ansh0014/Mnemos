"""Book Ingestion Parser wrapping ``neuralloop_books.chapters`` plus Markdown/text extraction."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mnemos_services.common import bootstrap_services

bootstrap_services()

from neuralloop_books import chapters as nl_chapters  # noqa: E402

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
_CODE_BLOCK_RE = re.compile(r"```([A-Za-z0-9_+-]*)\n(.*?)```", re.DOTALL)


@dataclass
class ParsedChapter:
    n: int
    title: str
    markdown: str
    sections: list[dict[str, str]] = field(default_factory=list)
    code_blocks: list[dict[str, str]] = field(default_factory=list)
    estimated_read_minutes: int = 1


def extract_sections_and_code(markdown: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Split a chapter's Markdown into clean section objects and fenced code snippets."""
    matches = list(_HEADING_RE.finditer(markdown))
    sections: list[dict[str, str]] = []
    if not matches:
        stripped = markdown.strip()
        if stripped:
            sections.append({"heading": "Overview", "body": stripped})
    else:
        for idx, match in enumerate(matches):
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
            sections.append(
                {
                    "heading": match.group(2).strip(),
                    "level": str(len(match.group(1))),
                    "body": markdown[start:end].strip(),
                }
            )

    code_blocks = [
        {"language": (m.group(1) or "text").strip(), "code": m.group(2).strip()}
        for m in _CODE_BLOCK_RE.finditer(markdown)
    ]
    return sections, code_blocks


def parse_markdown_book(markdown_text: str, book_title: str = "Untitled Book") -> dict[str, Any]:
    """Parse a raw Markdown document into chapters by top-level headings."""
    chapter_splits = list(re.finditer(r"^#\s+(.+?)\s*$", markdown_text, re.MULTILINE))
    parsed_chapters: list[ParsedChapter] = []

    if not chapter_splits:
        sections, code_blocks = extract_sections_and_code(markdown_text)
        words = max(1, len(markdown_text.split()))
        parsed_chapters.append(
            ParsedChapter(
                n=1,
                title=book_title,
                markdown=markdown_text.strip(),
                sections=sections,
                code_blocks=code_blocks,
                estimated_read_minutes=max(1, round(words / 220)),
            )
        )
    else:
        for idx, match in enumerate(chapter_splits):
            start = match.start()
            end = chapter_splits[idx + 1].start() if idx + 1 < len(chapter_splits) else len(markdown_text)
            chunk = markdown_text[start:end].strip()
            sections, code_blocks = extract_sections_and_code(chunk)
            words = max(1, len(chunk.split()))
            parsed_chapters.append(
                ParsedChapter(
                    n=idx + 1,
                    title=match.group(1).strip(),
                    markdown=chunk,
                    sections=sections,
                    code_blocks=code_blocks,
                    estimated_read_minutes=max(1, round(words / 220)),
                )
            )

    return {
        "book_title": book_title,
        "chapter_count": len(parsed_chapters),
        "chapters": [
            {
                "n": ch.n,
                "title": ch.title,
                "markdown": ch.markdown,
                "sections": ch.sections,
                "code_blocks": ch.code_blocks,
                "estimated_read_minutes": ch.estimated_read_minutes,
            }
            for ch in parsed_chapters
        ],
    }


def ingest_book_file(book_path: str | Path, out_dir: str | Path | None = None) -> dict[str, Any]:
    """Ingest a PDF, EPUB, or Markdown book using ``neuralloop_books.chapters.split_book``."""
    path = Path(book_path)
    if path.suffix.lower() in {".md", ".txt"}:
        return parse_markdown_book(path.read_text(encoding="utf-8"), book_title=path.stem)

    if out_dir is None:
        with tempfile.TemporaryDirectory(prefix="mnemos_ingest_") as tmp:
            return _ingest_via_pipeline(path, Path(tmp))
    return _ingest_via_pipeline(path, Path(out_dir))


def _ingest_via_pipeline(path: Path, target_dir: Path) -> dict[str, Any]:
    records = nl_chapters.split_book(path, target_dir)
    enriched: list[dict[str, Any]] = []
    for rec in records:
        chapter_file = target_dir / rec["file"]
        text = chapter_file.read_text(encoding="utf-8") if chapter_file.exists() else ""
        sections, code_blocks = extract_sections_and_code(text)
        enriched.append(
            {
                "n": rec["n"],
                "title": rec["title"],
                "file": rec["file"],
                "markdown": text,
                "sections": sections,
                "code_blocks": code_blocks,
                "estimated_read_minutes": max(1, round(max(1, len(text.split())) / 220)),
            }
        )
    return {"book_title": path.stem, "chapter_count": len(enriched), "chapters": enriched}
