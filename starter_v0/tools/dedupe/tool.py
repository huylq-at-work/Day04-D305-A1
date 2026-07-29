from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _normalize_url(value: Any) -> str:
    raw_url = str(value or "").strip()
    if not raw_url:
        return ""

    parts = urlsplit(raw_url)
    query = urlencode(sorted([
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if not name.casefold().startswith("utm_")
    ]))
    path = parts.path
    if path not in {"", "/"}:
        path = path.rstrip("/")

    return urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            path,
            query,
            "",
        )
    )


def _normalize_title(value: Any) -> str:
    title = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"\s+", " ", title).strip()


def dedupe_items(
    items: list[dict[str, Any]] | None = None,
    key: str = "url",
) -> dict[str, Any]:
    """Keep the first item for each normalized URL or title."""
    try:
        if key not in {"url", "title"}:
            return {
                "tool": "dedupe",
                "error": "invalid_key",
                "message": "key must be either 'url' or 'title'",
                "key": key,
            }

        if items is None:
            items = []
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            return {
                "tool": "dedupe",
                "error": "invalid_items",
                "message": "items must be a list of objects",
                "key": key,
            }

        normalize = _normalize_url if key == "url" else _normalize_title
        seen: set[str] = set()
        kept: list[dict[str, Any]] = []
        duplicate_indexes: list[int] = []

        for index, item in enumerate(items):
            marker = normalize(item.get(key))
            # Missing comparison fields are not evidence that two items are equal.
            if marker and marker in seen:
                duplicate_indexes.append(index)
                continue
            if marker:
                seen.add(marker)
            kept.append(item)

        return {
            "tool": "dedupe",
            "items": kept,
            "kept": kept,
            "input_count": len(items),
            "item_count": len(kept),
            "removed": len(duplicate_indexes),
            "duplicate_indexes": duplicate_indexes,
            "key": key,
            "error": None,
        }
    except Exception as exc:
        return {
            "tool": "dedupe",
            "error": type(exc).__name__,
            "message": str(exc),
            "key": key,
        }
