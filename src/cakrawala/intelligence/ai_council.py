from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

BRIEF_PATH = Path("data/ai_briefs/latest.json")
_ALLOWED_STANCES = {
    "RISK ON",
    "CAUTIOUS",
    "RISK OFF",
    "MIXED",
    "INSUFFICIENT EVIDENCE",
}


@dataclass(frozen=True)
class CouncilRole:
    role: str
    summary: str
    confidence: str
    evidence: tuple[str, ...]
    risks: tuple[str, ...]


@dataclass(frozen=True)
class CouncilBrief:
    generated_at: datetime
    as_of: str
    status: str
    source_count: int
    roles: tuple[CouncilRole, ...]
    headline: str
    research_stance: str
    consensus: tuple[str, ...]
    disagreements: tuple[str, ...]
    risk_flags: tuple[str, ...]
    next_checks: tuple[str, ...]
    signal_policy_note: str
    citations: tuple[dict[str, str], ...]

    def is_fresh(self, *, max_age_hours: int = 36) -> bool:
        return datetime.now(UTC) - self.generated_at <= timedelta(hours=max_age_hours)


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return tuple(item.strip() for item in value if item.strip())


def _parse_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("generated_at must be an ISO timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("generated_at must include timezone information")
    return parsed.astimezone(UTC)


def _parse_role(item: Any) -> CouncilRole:
    if not isinstance(item, dict):
        raise ValueError("role entries must be objects")
    role = str(item.get("role", "")).strip()
    summary = str(item.get("summary", "")).strip()
    confidence = str(item.get("confidence", "")).strip().lower()
    if not role or not summary:
        raise ValueError("role and summary are required")
    if confidence not in {"low", "medium", "high"}:
        raise ValueError("confidence must be low, medium, or high")
    return CouncilRole(
        role=role,
        summary=summary,
        confidence=confidence,
        evidence=_strings(item.get("evidence", []), "role.evidence"),
        risks=_strings(item.get("risks", []), "role.risks"),
    )


def parse_council_brief(payload: Any) -> CouncilBrief:
    if not isinstance(payload, dict):
        raise ValueError("AI council brief must be a JSON object")
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported AI council schema version")

    synthesis = payload.get("synthesis")
    if not isinstance(synthesis, dict):
        raise ValueError("synthesis object is required")

    stance = str(synthesis.get("research_stance", "")).strip().upper()
    if stance not in _ALLOWED_STANCES:
        raise ValueError("research_stance is not approved")

    citations_raw = payload.get("citations", [])
    if not isinstance(citations_raw, list):
        raise ValueError("citations must be a list")
    citations: list[dict[str, str]] = []
    for item in citations_raw:
        if not isinstance(item, dict):
            raise ValueError("citation entries must be objects")
        label = str(item.get("label", "")).strip()
        url = str(item.get("url", "")).strip()
        if not label or not url.startswith("https://"):
            raise ValueError("citation label and HTTPS URL are required")
        citations.append({"label": label, "url": url})

    roles_raw = payload.get("roles", [])
    if not isinstance(roles_raw, list):
        raise ValueError("roles must be a list")

    return CouncilBrief(
        generated_at=_parse_datetime(payload.get("generated_at")),
        as_of=str(payload.get("as_of", "")).strip(),
        status=str(payload.get("status", "")).strip(),
        source_count=int(payload.get("source_count", 0)),
        roles=tuple(_parse_role(item) for item in roles_raw),
        headline=str(synthesis.get("headline", "")).strip(),
        research_stance=stance,
        consensus=_strings(synthesis.get("consensus", []), "consensus"),
        disagreements=_strings(synthesis.get("disagreements", []), "disagreements"),
        risk_flags=_strings(synthesis.get("risk_flags", []), "risk_flags"),
        next_checks=_strings(synthesis.get("next_checks", []), "next_checks"),
        signal_policy_note=str(synthesis.get("signal_policy_note", "")).strip(),
        citations=tuple(citations),
    )


def load_council_brief(path: Path = BRIEF_PATH) -> CouncilBrief:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_council_brief(payload)
