from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from cakrawala.config import load_yaml


@dataclass(frozen=True)
class ModelRoleHealth:
    role: str
    state: str
    model_name: str | None
    latest_verified_run: date | None
    stale: bool
    message: str


@dataclass(frozen=True)
class ModelHealthSummary:
    roles: tuple[ModelRoleHealth, ...]

    @property
    def production_ready(self) -> bool:
        return all(item.state == "PRODUCTION" and not item.stale for item in self.roles)

    @property
    def decision_support_state(self) -> str:
        if self.production_ready:
            return "PRODUCTION"
        if any(item.state == "RESEARCH_ONLY" for item in self.roles):
            return "RESEARCH_ONLY"
        if any(item.state == "PRODUCTION" or item.stale for item in self.roles):
            return "MIXED_OR_STALE"
        return "BASELINE_ONLY"


def _parse_date(value: object) -> date | None:
    if value in {None, ""}:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def load_model_health(*, today: date | None = None) -> ModelHealthSummary:
    payload = load_yaml("configs/models.yaml")
    reference_day = today or datetime.now(UTC).date()
    roles = payload.get("roles", {})
    candidates = payload.get("validation_candidates", {})

    if not isinstance(roles, dict) or not isinstance(candidates, dict):
        raise ValueError("model configuration must define roles and validation_candidates")

    output: list[ModelRoleHealth] = []
    for role, configured_model in roles.items():
        if configured_model:
            model_name = str(configured_model)
            candidate = candidates.get(model_name, {})
            if not isinstance(candidate, dict):
                candidate = {}
            promoted = candidate.get("promoted") is True
            latest = _parse_date(candidate.get("latest_verified_run"))
            stale = latest is None or (reference_day - latest).days > 8
            state = "PRODUCTION" if promoted else "RESEARCH_ONLY"
            message = (
                "Production role is backed by a promoted model."
                if promoted
                else "Configured model is not promoted and cannot support production decisions."
            )
        else:
            model_name = None
            latest = None
            stale = False
            state = "BASELINE_ONLY"
            message = (
                "No promoted model is assigned. Deterministic evidence remains "
                "the decision baseline."
            )

        output.append(
            ModelRoleHealth(
                role=str(role),
                state=state,
                model_name=model_name,
                latest_verified_run=latest,
                stale=stale,
                message=message,
            )
        )

    return ModelHealthSummary(roles=tuple(output))

