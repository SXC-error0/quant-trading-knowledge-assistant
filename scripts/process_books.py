#!/usr/bin/env python3
"""Convert PDF or TXT books into JSONL knowledge chunks ready for import.

Usage:
    python scripts/process_books.py book.pdf \\
        --domain trading_books \\
        --title "量化交易" \\
        --chunk-size 450 \\
        --overlap 60 \\
        --output data/quant_trading_chunks.jsonl

Supports:
    - PDF  (requires:  pip install pypdf)
    - TXT  (UTF-8, no extra dependency)

The output JSONL is directly compatible with:
    python scripts/import_chunks.py <output.jsonl>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

_PAGE_TAG = re.compile(r"\[P(\d+)\]")


def _read_pdf(path: Path) -> list[tuple[int, str]]:
    """Return list of (page_number, text) from a PDF."""
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf is required for PDF processing. Run: pip install pypdf")

    reader = PdfReader(path)
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append((i, text))
    return pages


def _read_txt(path: Path, start_after: str | None = None) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    if start_after:
        import re as _re
        # Interpret common escape sequences typed on the command line (\\n → newline)
        pattern = start_after.replace("\\n", "\n").replace("\\t", "\t")
        m = _re.search(pattern, text, _re.MULTILINE)
        if m:
            text = text[m.start():]
        else:
            print(f"[warn] --start-after pattern not found; processing full file.", file=sys.stderr)
    return [(0, text)]


# ---------------------------------------------------------------------------
# Section / chapter detection
# ---------------------------------------------------------------------------

_CHAPTER_RE = re.compile(
    r"^(?:"
    r"第\s*[一二三四五六七八九十百零千\d]+\s*[章节篇部]"  # 第X章 / 第X节
    r"|(?:译者序|绪言|前言|后记|附录)[^\n]{0,30}"          # 译者序/绪言/前言
    r"|Chapter\s+\d+"                                      # Chapter N
    r"|\d{1,2}\.\d+\s+\S"                                  # 1.1 Title
    r"|[一二三四五六七八九十]+、\S"                         # 一、标题
    r")",
    re.MULTILINE,
)


def _split_sections(pages: list[tuple[int, str]]) -> list[dict]:
    """Group page text into sections detected by chapter headings.

    Returns list of dicts: {heading, content, page_start, page_end}.
    """
    # Flatten pages, keeping page boundary markers
    flat_lines: list[tuple[int, str]] = []
    for page_no, text in pages:
        for line in text.splitlines():
            flat_lines.append((page_no, line))

    sections: list[dict] = []
    current_heading = "前言"
    current_lines: list[str] = []
    current_page_start = pages[0][0] if pages else 1
    current_page = current_page_start

    def _flush():
        content = "\n".join(current_lines).strip()
        if len(content) >= 30:
            sections.append(
                {
                    "heading": current_heading,
                    "content": content,
                    "page_start": current_page_start,
                    "page_end": current_page,
                }
            )

    for page_no, line in flat_lines:
        current_page = page_no
        stripped = line.strip()
        if _CHAPTER_RE.match(stripped) and len(stripped) < 80:
            _flush()
            current_heading = stripped
            current_lines = []
            current_page_start = page_no
        else:
            current_lines.append(line)

    _flush()
    return sections if sections else [{"heading": "正文", "content": "\n".join(l for _, l in flat_lines), "page_start": 1, "page_end": pages[-1][0] if pages else 1}]


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_SENTENCE_END = re.compile(r"[。！？\n]")


def _split_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if len(text) >= 20 else []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        at_end = end >= len(text)
        if not at_end:
            # Prefer breaking at a sentence boundary in the latter half
            m = None
            for m in _SENTENCE_END.finditer(text, start + chunk_size // 2, end):
                pass
            if m:
                end = m.end()
        chunk = text[start:end].strip()
        if len(chunk) >= 20:
            chunks.append(chunk)
        if at_end:
            break
        start = end - overlap

    return chunks


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

_CHINESE_WORD = re.compile(r"[一-鿿]{2,8}")
_ENGLISH_WORD = re.compile(r"\b[A-Za-z]{3,}\b")

_STOPWORDS = {
    "的", "了", "和", "是", "在", "有", "与", "或", "但", "而", "则", "对",
    "为", "于", "由", "被", "将", "其", "该", "此", "那", "这", "可以",
    "the", "and", "for", "that", "this", "are", "with", "from",
}


def _extract_keywords(text: str, top_n: int = 8) -> list[str]:
    chinese = [w for w in _CHINESE_WORD.findall(text) if w not in _STOPWORDS]
    english = [w.lower() for w in _ENGLISH_WORD.findall(text) if w.lower() not in _STOPWORDS]
    counts = Counter(chinese + english)
    return [term for term, _ in counts.most_common(top_n)]


# ---------------------------------------------------------------------------
# Chunk ID
# ---------------------------------------------------------------------------

def _make_chunk_id(title: str, heading: str, index: int) -> str:
    raw = f"{title}\x00{heading}\x00{index}"
    digest = hashlib.sha1(raw.encode()).hexdigest()[:10]
    return f"book_{digest}_{index:04d}"


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_book(
    path: Path,
    domain: str,
    title: str,
    chunk_size: int,
    overlap: int,
    copyright_status: str,
    start_after: str | None = None,
) -> list[dict]:
    if path.suffix.lower() == ".pdf":
        pages = _read_pdf(path)
    else:
        pages = _read_txt(path, start_after=start_after)

    if not pages:
        print(f"[warn] No text extracted from {path}", file=sys.stderr)
        return []

    sections = _split_sections(pages)
    records: list[dict] = []
    global_index = 0

    for section in sections:
        for chunk_text in _split_chunks(section["content"], chunk_size, overlap):
            records.append(
                {
                    "chunk_id": _make_chunk_id(title, section["heading"], global_index),
                    "knowledge_domain": domain,
                    "document_title": title,
                    "chapter": section["heading"],
                    "section": None,
                    "page_start": section["page_start"],
                    "page_end": section["page_end"],
                    "content": chunk_text,
                    "keywords": _extract_keywords(chunk_text),
                    "source_type": "book",
                    "copyright_status": copyright_status,
                }
            )
            global_index += 1

    return records


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a PDF or TXT book into JSONL knowledge chunks.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_file", type=Path, help="Path to PDF or TXT file.")
    parser.add_argument(
        "--domain",
        choices=["trading_books", "product_manual", "signal_rules"],
        default="trading_books",
    )
    parser.add_argument("--title", required=True, help="Document title stored in metadata.")
    parser.add_argument("--chunk-size", type=int, default=450, help="Max characters per chunk.")
    parser.add_argument("--overlap", type=int, default=60, help="Overlap characters between chunks.")
    parser.add_argument("--copyright-status", default="authorized")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path. Defaults to <input_stem>_chunks.jsonl.",
    )
    parser.add_argument("--append", action="store_true", help="Append to existing output file.")
    parser.add_argument(
        "--start-after",
        default=None,
        metavar="PATTERN",
        help="Regex pattern; skip all text before the first match (useful to skip TOC/header).",
    )
    args = parser.parse_args()

    if not args.input_file.exists():
        sys.exit(f"File not found: {args.input_file}")

    output: Path = args.output or args.input_file.parent / f"{args.input_file.stem}_chunks.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)

    records = process_book(
        args.input_file,
        args.domain,
        args.title,
        args.chunk_size,
        args.overlap,
        args.copyright_status,
        start_after=args.start_after,
    )

    mode = "a" if args.append else "w"
    with output.open(mode, encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"生成 {len(records)} 个知识块 → {output}")


if __name__ == "__main__":
    main()
