"""Text sanitization for ingestion.

Operates on raw strings from the submission form (product / audience / colors
descriptions) rather than markdown files: strips zero-width unicode, removes
URLs, and normalizes whitespace so downstream LLM payloads stay clean.
"""

import re
from typing import Any

_ZERO_WIDTH_RE = re.compile(r"[​‌‍﻿]")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(https?://[^\s)]+\)")
_NAKED_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def process_text(raw_text: str) -> dict[str, Any]:
    """Sanitize a single description string and return cleaned text + metrics."""
    clean_text = raw_text.strip().replace("\r\n", "\n").replace("\r", "\n")
    clean_text = _ZERO_WIDTH_RE.sub("", clean_text)

    # Drop URLs but keep markdown link labels.
    clean_text = _MARKDOWN_LINK_RE.sub(r"\1", clean_text)
    clean_text = _NAKED_URL_RE.sub("", clean_text)

    # Collapse runs of 3+ blank lines; preserve intra-line spacing.
    clean_text = _BLANK_LINES_RE.sub("\n\n", clean_text).strip()

    return {
        "status": "success",
        "metrics": {
            "word_count": len(clean_text.split()),
            "char_length": len(clean_text),
        },
        "content": clean_text,
    }
