from __future__ import annotations

import re
from typing import Any

from tools._shared import fold_text, terms


_VALID_KINDS = ("person", "organization", "handle")
_KIND_PRIORITY = {"person": 1, "organization": 2, "handle": 3}

_HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{1,30}\b")
_WORD_RE = re.compile(r"[^\W\d_](?:[\w'’\-]*[^\W_])?", re.UNICODE)

_CONNECTORS = {
    "and",
    "da",
    "de",
    "do",
    "for",
    "hang",
    "hoc",
    "of",
    "the",
    "ty",
    "van",
    "doan",
}

_PERSON_TITLES = {
    "ba",
    "ceo",
    "director",
    "dr",
    "founder",
    "minister",
    "mr",
    "mrs",
    "ms",
    "ong",
    "president",
    "prof",
    "professor",
}

_TITLE_MODIFIERS = {"acting", "current", "former", "incoming", "new"}

_ORGANIZATION_MARKERS = {
    "agency",
    "association",
    "bank",
    "bo",
    "college",
    "company",
    "corp",
    "corporation",
    "department",
    "foundation",
    "group",
    "inc",
    "institute",
    "laboratories",
    "laboratory",
    "labs",
    "llc",
    "ltd",
    "ministry",
    "news",
    "plc",
    "press",
    "research",
    "systems",
    "technologies",
    "technology",
    "times",
    "university",
    "vien",
}

_ORGANIZATION_PREFIXES = {
    ("cong", "ty"),
    ("dai", "hoc"),
    ("ngan", "hang"),
    ("tap", "doan"),
}

_NON_PERSON_TERMS = {
    "agent",
    "appendix",
    "chapter",
    "conclusion",
    "evaluation",
    "introduction",
    "monday",
    "news",
    "research",
    "saturday",
    "section",
    "source",
    "sunday",
    "thursday",
    "tier",
    "today",
    "tool",
    "tuesday",
    "wednesday",
}

_GENERIC_ACRONYMS = {
    "AI",
    "API",
    "CEO",
    "CTO",
    "HTTP",
    "HTTPS",
    "JSON",
    "LLM",
    "NLP",
    "PDF",
    "URL",
    "YAML",
}


def _normalize(value: str) -> str:
    folded = fold_text(value).replace("đ", "d")
    return re.sub(r"\s+", " ", folded).strip()


def _is_capitalized(word: str) -> bool:
    return bool(word) and word[0].isupper()


def _is_brand_word(word: str) -> bool:
    uppercase_count = sum(character.isupper() for character in word)
    return uppercase_count >= 2 and not word.isupper() and len(word) > 2


def _has_organization_prefix(words: list[str]) -> bool:
    return any(
        tuple(words[index:index + len(prefix)]) == prefix
        for prefix in _ORGANIZATION_PREFIXES
        for index in range(len(words) - len(prefix) + 1)
    )


def _looks_like_organization(words: list[str], raw_words: list[str]) -> bool:
    if any(word in _ORGANIZATION_MARKERS for word in words):
        return True
    if _has_organization_prefix(words):
        return True
    if len(raw_words) == 1:
        raw_word = raw_words[0]
        return (
            (_is_brand_word(raw_word) or raw_word.isupper())
            and raw_word.upper() not in _GENERIC_ACRONYMS
        )
    return False


def _tokenize(text: str) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for match in _WORD_RE.finditer(text):
        if match.start() > 0 and text[match.start() - 1] == "@":
            continue
        tokens.append({
            "text": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "normalized": _normalize(match.group(0)),
        })
    return tokens


def _name_groups(text: str, tokens: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    index = 0

    while index < len(tokens):
        if not _is_capitalized(tokens[index]["text"]):
            index += 1
            continue

        group = [tokens[index]]
        cursor = index + 1
        while cursor < len(tokens) and len(group) < 7:
            previous = group[-1]
            token = tokens[cursor]
            gap = text[previous["end"]:token["start"]]
            directly_connected = gap.isspace()
            title_period = previous["normalized"] in _PERSON_TITLES and gap.strip() == "."

            if _is_capitalized(token["text"]) and (directly_connected or title_period):
                group.append(token)
                cursor += 1
                continue

            if (
                token["normalized"] in _CONNECTORS
                and directly_connected
                and cursor + 1 < len(tokens)
            ):
                following = tokens[cursor + 1]
                following_gap = text[token["end"]:following["start"]]
                if _is_capitalized(following["text"]) and following_gap.isspace():
                    group.extend([token, following])
                    cursor += 2
                    continue
            break

        groups.append(group)
        index = cursor

    return groups


def extract_entities(
    text: str = "",
    kinds: list[str] | None = None,
) -> dict[str, Any]:
    """Extract person, organization, and @handle candidates using local heuristics."""
    try:
        if not isinstance(text, str):
            return {
                "tool": "extract_entities",
                "error": "invalid_text",
                "message": "text must be a string",
            }

        requested_kinds = list(_VALID_KINDS) if kinds is None else kinds
        if (
            not isinstance(requested_kinds, list)
            or not requested_kinds
            or any(not isinstance(kind, str) or kind not in _VALID_KINDS for kind in requested_kinds)
        ):
            return {
                "tool": "extract_entities",
                "error": "invalid_kinds",
                "message": "kinds must be a non-empty list containing person, organization, or handle",
            }
        requested_kinds = list(dict.fromkeys(requested_kinds))

        records: dict[tuple[str, str], dict[str, Any]] = {}
        normalized_to_key: dict[str, tuple[str, str]] = {}

        def add_entity(
            value: str,
            kind: str,
            start: int,
            method: str,
            confidence: float,
        ) -> None:
            cleaned = value.strip(" \t\r\n,;:()[]{}")
            normalized = _normalize(cleaned)
            if not cleaned or not normalized:
                return
            if kind != "handle" and not terms(cleaned):
                return

            key = (kind, normalized)
            existing_key = normalized_to_key.get(normalized)
            if existing_key and existing_key != key:
                existing_kind = existing_key[0]
                if _KIND_PRIORITY[kind] <= _KIND_PRIORITY[existing_kind]:
                    return
                records.pop(existing_key, None)

            if key in records:
                records[key]["mentions"] += 1
                records[key]["confidence"] = max(records[key]["confidence"], confidence)
                return

            records[key] = {
                "text": cleaned,
                "kind": kind,
                "normalized": normalized,
                "mentions": 1,
                "method": method,
                "confidence": confidence,
                "_first_position": start,
            }
            normalized_to_key[normalized] = key

        for match in _HANDLE_RE.finditer(text):
            add_entity(match.group(0), "handle", match.start(), "handle_pattern", 1.0)

        tokens = _tokenize(text)
        for group in _name_groups(text, tokens):
            normalized_words = [token["normalized"] for token in group]
            raw_words = [token["text"] for token in group]

            title_index = next(
                (index for index, word in enumerate(normalized_words) if word in _PERSON_TITLES),
                None,
            )
            if title_index is not None:
                person_tokens = [
                    token
                    for token in group[title_index + 1:]
                    if token["normalized"] not in _CONNECTORS
                ]
                if person_tokens:
                    person_text = text[person_tokens[0]["start"]:person_tokens[-1]["end"]]
                    add_entity(
                        person_text,
                        "person",
                        person_tokens[0]["start"],
                        "title_context",
                        0.9,
                    )

                prefix_tokens = group[:title_index]
                prefix_words = [token["normalized"] for token in prefix_tokens]
                if prefix_tokens and not all(word in _TITLE_MODIFIERS for word in prefix_words):
                    organization_text = text[prefix_tokens[0]["start"]:prefix_tokens[-1]["end"]]
                    add_entity(
                        organization_text,
                        "organization",
                        prefix_tokens[0]["start"],
                        "organization_before_title",
                        0.8,
                    )
                continue

            candidate_text = text[group[0]["start"]:group[-1]["end"]]
            if _looks_like_organization(normalized_words, raw_words):
                add_entity(
                    candidate_text,
                    "organization",
                    group[0]["start"],
                    "organization_pattern",
                    0.85,
                )
                continue

            capitalized_words = [
                token for token in group
                if token["normalized"] not in _CONNECTORS
            ]
            candidate_terms = terms(candidate_text)
            if (
                2 <= len(capitalized_words) <= 4
                and not candidate_terms.intersection(_NON_PERSON_TERMS)
            ):
                add_entity(
                    candidate_text,
                    "person",
                    group[0]["start"],
                    "capitalized_name",
                    0.65,
                )

        entities = [
            record
            for record in records.values()
            if record["kind"] in requested_kinds
        ]
        entities.sort(key=lambda record: record["_first_position"])
        for record in entities:
            record.pop("_first_position", None)

        by_kind = {
            kind: [record for record in entities if record["kind"] == kind]
            for kind in requested_kinds
        }
        counts = {kind: len(by_kind[kind]) for kind in requested_kinds}

        return {
            "tool": "extract_entities",
            "entities": entities,
            "by_kind": by_kind,
            "counts": counts,
            "entity_count": len(entities),
            "requested_kinds": requested_kinds,
            "text_length": len(text),
            "heuristic": True,
            "error": None,
        }
    except Exception as exc:
        return {
            "tool": "extract_entities",
            "error": type(exc).__name__,
            "message": str(exc),
        }
