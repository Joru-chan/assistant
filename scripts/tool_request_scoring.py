#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Tuple

STOPWORDS = {
    "the",
    "and",
    "or",
    "to",
    "a",
    "an",
    "of",
    "in",
    "for",
    "with",
    "is",
    "are",
    "be",
    "it",
    "this",
    "that",
    "my",
    "your",
    "from",
    "on",
    "by",
    "as",
    "at",
    "like",
    "i",
    "me",
    "you",
    "we",
    "our",
    "want",
    "need",
    "lets",
    "let",
    "take",
    "make",
    "build",
    "implement",
    "create",
}

FIELD_WEIGHTS = {
    "title": 1.0,
    "description": 2.0,
    "desired_outcome": 3.0,
    "domain": 4.0,
}

KEYWORD_DOMAIN_MAP = {
    "receipt": {"inventory", "pantry"},
    "inventory": {"inventory", "pantry"},
    "pantry": {"pantry", "inventory"},
    "instagram": {"instagram", "recipes"},
    "recipe": {"recipes", "cooking"},
    "reel": {"instagram", "recipes"},
    "photo": {"capture", "pantry", "inventory"},
    "image": {"capture", "pantry", "inventory"},
    "ocr": {"capture", "knowledge"},
    "article": {"reading", "knowledge"},
    "articles": {"reading", "knowledge"},
    "knowledge": {"knowledge"},
    "items": {"inventory", "pantry"},
    "groceries": {"pantry", "inventory"},
}


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if token and token not in STOPWORDS]


def _normalize_domain(domain: Any) -> List[str]:
    if isinstance(domain, list):
        return [str(item).strip() for item in domain if str(item).strip()]
    if isinstance(domain, str):
        return [part.strip() for part in domain.split(",") if part.strip()]
    return []


def _overlap_score(query_tokens: Iterable[str], field_tokens: Iterable[str]) -> Tuple[float, List[str]]:
    query_set = set(query_tokens)
    field_set = set(field_tokens)
    if not query_set or not field_set:
        return 0.0, []
    overlap = sorted(query_set.intersection(field_set))
    score = len(overlap) / max(len(query_set), 1)
    return score, overlap


def score_candidate(query: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
    query_tokens = tokenize(query)
    title = str(candidate.get("title") or "")
    description = str(candidate.get("description") or "")
    desired_outcome = str(candidate.get("desired_outcome") or "")
    domain = _normalize_domain(candidate.get("domain"))
    domain_text = " ".join(domain)

    title_tokens = tokenize(title)
    desc_tokens = tokenize(description)
    outcome_tokens = tokenize(desired_outcome)
    domain_tokens = tokenize(domain_text)

    title_score, title_overlap = _overlap_score(query_tokens, title_tokens)
    desc_score, desc_overlap = _overlap_score(query_tokens, desc_tokens)
    outcome_score, outcome_overlap = _overlap_score(query_tokens, outcome_tokens)
    domain_score, domain_overlap = _overlap_score(query_tokens, domain_tokens)

    weighted_title = title_score * FIELD_WEIGHTS["title"]
    weighted_desc = desc_score * FIELD_WEIGHTS["description"]
    weighted_outcome = outcome_score * FIELD_WEIGHTS["desired_outcome"]
    weighted_domain = domain_score * FIELD_WEIGHTS["domain"]

    bonus = 0.0
    bonus_details: List[str] = []
    lower_query = query.lower()
    if lower_query and (
        lower_query in title.lower()
        or lower_query in description.lower()
        or lower_query in desired_outcome.lower()
    ):
        bonus += 0.4
        bonus_details.append("Exact phrase appears in title/description/outcome.")

    domain_set = {token for token in domain_tokens}
    for keyword, domains in KEYWORD_DOMAIN_MAP.items():
        if keyword in query_tokens and domain_set.intersection(domains):
            bonus += 0.3
            bonus_details.append(f"Keyword '{keyword}' matches domain tags.")

    total = weighted_title + weighted_desc + weighted_outcome + weighted_domain + bonus

    top_matches = sorted(set(title_overlap + desc_overlap + outcome_overlap + domain_overlap))

    return {
        "total_score": total,
        "breakdown": {
            "title_score": weighted_title,
            "description_score": weighted_desc,
            "desired_outcome_score": weighted_outcome,
            "domain_score": weighted_domain,
            "bonus_score": bonus,
            "bonuses": bonus_details,
        },
        "matches": {
            "title": title_overlap,
            "description": desc_overlap,
            "desired_outcome": outcome_overlap,
            "domain": domain_overlap,
            "top_tokens": top_matches,
        },
    }
