from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
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
_ALLOWED_STATUSES = {"ready", "waiting_for_first_scheduled_brief", "failed"}


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
        age = datetime.now(UTC) - self.generated_at
        return timedelta(0) <= age <= timedelta(hours=max_age_hours)

    @property
    def presentation_status(self) -> str:
        if self.status != "ready":
            return self.status.replace("_", " ").upper()
        return "FRESH" if self.is_fresh() else "STALE"

    @property
    def is_publishable(self) -> bool:
        return (
            self.status == "ready"
            and self.is_fresh()
            and self.source_count > 0
            and bool(self.roles)
            and bool(self.citations)
        )


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return tuple(item.strip() for item in value if item.strip())


def _parse_datetime(value: Any, field: str = "generated_at") -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone information")
    return parsed.astimezone(UTC)


def _parse_as_of(value: Any, generated_at: datetime) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("as_of must be an ISO date")
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("as_of must be an ISO date") from exc
    if parsed > generated_at.date():
        raise ValueError("as_of cannot be later than generated_at")
    return parsed.isoformat()


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

    generated_at = _parse_datetime(payload.get("generated_at"))
    if generated_at > datetime.now(UTC) + timedelta(minutes=5):
        raise ValueError("generated_at cannot be in the future")
    as_of = _parse_as_of(payload.get("as_of"), generated_at)
    status = str(payload.get("status", "")).strip().lower()
    if status not in _ALLOWED_STATUSES:
        raise ValueError("status is not approved")

    source_count = payload.get("source_count", 0)
    if not isinstance(source_count, int) or isinstance(source_count, bool):
        raise ValueError("source_count must be an integer")
    if source_count < 0:
        raise ValueError("source_count must not be negative")

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
    citation_urls: set[str] = set()
    for item in citations_raw:
        if not isinstance(item, dict):
            raise ValueError("citation entries must be objects")
        label = str(item.get("label", "")).strip()
        url = str(item.get("url", "")).strip()
        if not label or not url.startswith("https://"):
            raise ValueError("citation label and HTTPS URL are required")
        if url in citation_urls:
            raise ValueError("citation URLs must be unique")
        verified_at_raw = item.get("verified_at")
        verified_at = _parse_datetime(verified_at_raw, "citation.verified_at")
        if verified_at > generated_at + timedelta(minutes=5):
            raise ValueError("citation verification cannot be later than generated_at")
        if generated_at - verified_at > timedelta(hours=48):
            raise ValueError("citation verification is too old for a current brief")
        citation_urls.add(url)
        citations.append(
            {
                "label": label,
                "url": url,
                "verified_at": verified_at.isoformat(),
            }
        )

    roles_raw = payload.get("roles", [])
    if not isinstance(roles_raw, list):
        raise ValueError("roles must be a list")
    roles = tuple(_parse_role(item) for item in roles_raw)

    headline = str(synthesis.get("headline", "")).strip()
    signal_policy_note = str(synthesis.get("signal_policy_note", "")).strip()
    if status == "ready":
        if not roles:
            raise ValueError("ready brief must include analyst roles")
        if source_count <= 0 or not citations:
            raise ValueError("ready brief must include verified sources")
        if source_count != len(citation_urls):
            raise ValueError("source_count must match unique citations")
        if not headline or not signal_policy_note:
            raise ValueError("ready brief must include synthesis and signal policy")

    return CouncilBrief(
        generated_at=generated_at,
        as_of=as_of,
        status=status,
        source_count=source_count,
        roles=roles,
        headline=headline,
        research_stance=stance,
        consensus=_strings(synthesis.get("consensus", []), "consensus"),
        disagreements=_strings(synthesis.get("disagreements", []), "disagreements"),
        risk_flags=_strings(synthesis.get("risk_flags", []), "risk_flags"),
        next_checks=_strings(synthesis.get("next_checks", []), "next_checks"),
        signal_policy_note=signal_policy_note,
        citations=tuple(citations),
    )


def load_council_brief(path: Path = BRIEF_PATH) -> CouncilBrief:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_council_brief(payload)

