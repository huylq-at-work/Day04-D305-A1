from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from tools._shared import domain


POLICY_PATH = "company_policy/source-citation-policy.md"

_SOCIAL_OR_FORUM_DOMAINS = {
    "discord.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "medium.com",
    "news.ycombinator.com",
    "quora.com",
    "reddit.com",
    "stackoverflow.com",
    "t.me",
    "threads.net",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "youtube.com",
}

_PRIMARY_SOURCE_DOMAINS = {
    "arxiv.org",
    "congress.gov",
    "data.gov",
    "doi.org",
    "github.com",
    "gitlab.com",
    "regulations.gov",
    "sec.gov",
}

_REPORTING_DOMAINS = {
    "apnews.com",
    "bbc.co.uk",
    "bbc.com",
    "bloomberg.com",
    "cnn.com",
    "ft.com",
    "npr.org",
    "nytimes.com",
    "reuters.com",
    "techcrunch.com",
    "theguardian.com",
    "theverge.com",
    "washingtonpost.com",
    "wired.com",
    "wsj.com",
}

_PRIMARY_SOURCE_TYPES = {
    "dataset",
    "documentation",
    "official",
    "official_blog",
    "paper",
    "primary",
    "primary_source",
    "regulatory_filing",
}

_WEAK_SOURCE_TYPES = {
    "anonymous_claim",
    "forum",
    "screenshot",
    "social",
    "social_post",
    "unverified",
    "unverified_summary",
}


def _matches_domain(host: str, candidates: set[str]) -> bool:
    return any(host == candidate or host.endswith(f".{candidate}") for candidate in candidates)


def _source_type(item: dict[str, Any]) -> str:
    value = item.get("source_type") or item.get("kind") or ""
    return str(value).strip().casefold().replace("-", "_").replace(" ", "_")


def _government_domain(host: str) -> bool:
    return (
        host.endswith(".gov")
        or host.endswith(".gov.uk")
        or host.endswith(".gov.vn")
        or host.endswith(".gouv.fr")
        or host.endswith(".go.jp")
        or host.endswith(".gc.ca")
    )


def _official_path(url: str) -> bool:
    path = urlparse(url).path.casefold()
    segments = {segment for segment in path.split("/") if segment}
    return bool(
        segments
        & {
            "blog",
            "dataset",
            "datasets",
            "developer",
            "developers",
            "docs",
            "documentation",
            "paper",
            "papers",
            "research",
        }
    )


def _classify(item: dict[str, Any]) -> tuple[int, str, bool]:
    url = str(item.get("url") or "").strip()
    host = domain(url).casefold().split(":", 1)[0]
    source = str(item.get("source") or "").strip().casefold()
    source_kind = _source_type(item)

    if (
        _matches_domain(host, _SOCIAL_OR_FORUM_DOMAINS)
        or source.startswith("@")
        or source_kind in _WEAK_SOURCE_TYPES
        or item.get("is_unverified") is True
    ):
        return 3, "social, forum, screenshot, anonymous, or explicitly unverified source", True

    if host == "arxiv.org" or host.endswith(".arxiv.org"):
        return 1, "paper hosted on arXiv", True

    if (
        _matches_domain(host, _PRIMARY_SOURCE_DOMAINS)
        or _government_domain(host)
        or source_kind in _PRIMARY_SOURCE_TYPES
        or item.get("is_primary_source") is True
        or item.get("is_official") is True
    ):
        return 1, "primary, official, documentation, paper, dataset, or regulatory source", False

    is_reporting = _matches_domain(host, _REPORTING_DOMAINS) or source_kind in {
        "news",
        "reporting",
        "reputable_reporting",
    }
    if is_reporting and item.get("links_primary_evidence") is True:
        return 2, "reputable reporting marked as linking to primary evidence", False

    if is_reporting:
        return 3, "reporting source has no verified primary-evidence link in the item metadata", True

    if host and _official_path(url):
        return 1, "URL path indicates first-party documentation, blog, research, paper, or dataset", False

    return 3, "source type could not be verified from the available item metadata", True


def rank_sources(
    items: list[dict[str, Any]] | None = None,
    min_tier: int = 3,
) -> dict[str, Any]:
    """Rank sources from Tier 1 (strongest) to Tier 3 (signal only)."""
    try:
        if isinstance(min_tier, bool) or not isinstance(min_tier, int) or min_tier not in {1, 2, 3}:
            return {
                "tool": "rank_sources",
                "error": "invalid_min_tier",
                "message": "min_tier must be an integer from 1 to 3",
                "min_tier": min_tier,
            }

        if items is None:
            items = []
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            return {
                "tool": "rank_sources",
                "error": "invalid_items",
                "message": "items must be a list of objects",
                "min_tier": min_tier,
            }

        ranked_with_indexes: list[tuple[int, int, dict[str, Any]]] = []
        counts = {"tier_1": 0, "tier_2": 0, "tier_3": 0}

        for index, item in enumerate(items):
            tier, reason, needs_verification = _classify(item)
            ranked_item = dict(item)
            ranked_item.update({
                "source_tier": tier,
                "source_tier_label": {
                    1: "primary_or_official",
                    2: "reporting_with_primary_evidence",
                    3: "signal_only",
                }[tier],
                "tier_reason": reason,
                "needs_verification": needs_verification,
            })
            if domain(str(item.get("url") or "")).casefold().endswith("arxiv.org"):
                ranked_item["policy_warning"] = "arXiv papers are not automatically peer reviewed."
            counts[f"tier_{tier}"] += 1
            ranked_with_indexes.append((tier, index, ranked_item))

        ranked_with_indexes.sort(key=lambda entry: (entry[0], entry[1]))
        ranked = [item for tier, _, item in ranked_with_indexes if tier <= min_tier]

        return {
            "tool": "rank_sources",
            "items": ranked,
            "ranked": ranked,
            "input_count": len(items),
            "item_count": len(ranked),
            "filtered_out": len(items) - len(ranked),
            "tier_counts": counts,
            "min_tier": min_tier,
            "policy": POLICY_PATH,
            "error": None,
        }
    except Exception as exc:
        return {
            "tool": "rank_sources",
            "error": type(exc).__name__,
            "message": str(exc),
            "min_tier": min_tier,
        }
