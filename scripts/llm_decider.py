#!/usr/bin/env python3
"""
LLM decision helper for tool request selection.

If no LLM provider is configured, fall back to heuristic scoring.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List

from tool_request_scoring import score_candidate

BEST_REQUEST_TRIGGERS = (
    "make a wish",
    "fulfil a wish",
    "fulfill a wish",
    "what should we build",
    "build next",
    "build something",
)

IMPACT_SCORES = {"high": 3, "medium": 2, "low": 1}
FREQUENCY_SCORES = {
    "many-times-per-day": 4,
    "daily": 3,
    "weekly": 2,
    "once": 1,
}
DOMAIN_BONUS = {"inventory", "pantry", "capture", "recipe", "recipes"}


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_generic_request(request_text: str) -> bool:
    lower = request_text.lower()
    return any(trigger in lower for trigger in BEST_REQUEST_TRIGGERS)


def _best_score(candidate: Dict[str, Any]) -> Dict[str, Any]:
    breakdown: Dict[str, Any] = {}
    status = str(candidate.get("status") or "").lower()
    impact = str(candidate.get("impact") or "").lower()
    frequency = str(candidate.get("frequency") or "").lower()
    recency_days = candidate.get("recency_days")
    domain = candidate.get("domain") or []
    if isinstance(domain, str):
        domain = [part.strip().lower() for part in domain.split(",") if part.strip()]
    else:
        domain = [str(item).strip().lower() for item in domain if str(item).strip()]

    status_score = 2 if status in ("new", "triaging") else 0
    impact_score = IMPACT_SCORES.get(impact, 0)
    frequency_score = FREQUENCY_SCORES.get(frequency, 0)
    if recency_days is None:
        recency_score = 0
    elif recency_days <= 7:
        recency_score = 2
    elif recency_days <= 30:
        recency_score = 1
    else:
        recency_score = 0
    domain_bonus = 1 if set(domain).intersection(DOMAIN_BONUS) else 0

    breakdown["status_score"] = status_score
    breakdown["impact_score"] = impact_score
    breakdown["frequency_score"] = frequency_score
    breakdown["recency_score"] = recency_score
    breakdown["domain_bonus"] = domain_bonus

    total = status_score + impact_score + frequency_score + recency_score + domain_bonus
    return {"total_score": float(total), "breakdown": breakdown}


def _heuristic_decide(
    request_text: str,
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if _is_generic_request(request_text):
        ranked = []
        for item in candidates:
            scoring = _best_score(item)
            ranked.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "score": scoring["total_score"],
                    "breakdown": scoring["breakdown"],
                    "top_tokens": [],
                }
            )
        ranked.sort(key=lambda entry: entry["score"], reverse=True)
        top = ranked[0] if ranked else None
        second = ranked[1] if len(ranked) > 1 else None
        top_score = top["score"] if top else 0.0
        second_score = second["score"] if second else 0.0
        confidence = 0.0
        if top:
            confidence = max(top_score - second_score, 0.0) / max(top_score, 1.0)

        return {
            "selected_id": top["id"] if top else None,
            "confidence": round(confidence, 2),
            "why": ["Selected using status/impact/frequency/recency scoring."],
            "questions": [
                "What outcome matters most for this tool request?",
                "Any constraints for v0 (no automation, no OCR, etc.)?",
                "Where should outputs be stored (Notion DB name or ID)?",
            ],
            "plan_outline": [
                "Confirm target database + required properties.",
                "Define v0 input capture flow.",
                "Implement dry-run preview with explicit apply step.",
                "Add examples and basic validation.",
            ],
            "inputs_and_capture": {
                "what_user_provides_v0": ["TBD (confirm preferred input)"],
                "supported_inputs": ["TBD"],
                "unsupported_yet": ["TBD"],
            },
            "ranked": ranked[:5],
            "provider": "heuristic",
        }

    scored: List[Dict[str, Any]] = []
    for item in candidates:
        score = score_candidate(request_text, item)
        scored.append({"item": item, "score": score})

    scored.sort(key=lambda entry: entry["score"]["total_score"], reverse=True)
    top = scored[0] if scored else None
    second = scored[1] if len(scored) > 1 else None
    top_score = top["score"]["total_score"] if top else 0.0
    second_score = second["score"]["total_score"] if second else 0.0
    confidence = 0.0
    if top:
        confidence = max(top_score - second_score, 0.0) / max(top_score, 1.0)

    why: List[str] = []
    if top:
        breakdown = top["score"]["breakdown"]
        for key, value in breakdown.items():
            if key.endswith("_score") and value:
                why.append(f"{key.replace('_score', '').replace('_', ' ')} overlap contributes {value:.2f}.")
        bonuses = breakdown.get("bonuses") or []
        why.extend(bonuses)

    questions = [
        "What input format should v0 support (text paste, list, or photo upload later)?",
        "Where should the resulting items be stored (Notion DB name or ID)?",
        "Any constraints on automation vs manual review?",
    ]

    plan_outline = [
        "Confirm target database + required properties.",
        "Define v0 input capture flow (manual text paste or structured list).",
        "Implement dry-run preview with explicit apply step.",
        "Add examples and basic validation.",
    ]

    inputs_and_capture = {
        "what_user_provides_v0": [
            "Receipt text pasted from phone/email",
            "Optional store and purchase date",
        ],
        "supported_inputs": ["plain text", "manual list"],
        "unsupported_yet": ["photo OCR", "image upload"],
    }

    return {
        "selected_id": top["item"]["id"] if top else None,
        "confidence": round(confidence, 2),
        "why": why[:5] if why else ["Heuristic match based on token overlap."],
        "questions": questions,
        "plan_outline": plan_outline,
        "inputs_and_capture": inputs_and_capture,
        "ranked": [
            {
                "id": entry["item"]["id"],
                "title": entry["item"].get("title"),
                "url": entry["item"].get("url"),
                "score": entry["score"]["total_score"],
                "breakdown": entry["score"]["breakdown"],
                "top_tokens": entry["score"]["matches"].get("top_tokens", []),
            }
            for entry in scored[:5]
        ],
        "provider": "heuristic",
    }


def decide(
    request_text: str,
    candidates: List[Dict[str, Any]],
    profile: str | None = None,
    playbook: str | None = None,
) -> Dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if not provider:
        return _heuristic_decide(request_text, candidates)

    # Placeholder for future providers; fallback for now.
    return _heuristic_decide(request_text, candidates)


def main() -> int:
    parser = argparse.ArgumentParser(description="Decide on a tool request using LLM or fallback.")
    parser.add_argument("--request", required=True)
    parser.add_argument("--candidates-json", required=True)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--playbook", default=None)
    args = parser.parse_args()

    payload = _load_json(args.candidates_json)
    candidates = payload.get("result", {}).get("candidates", payload)
    output = decide(
        args.request,
        candidates,
        profile=args.profile,
        playbook=args.playbook,
    )
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
