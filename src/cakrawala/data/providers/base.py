from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cakrawala.data.provenance import ProvenanceRecord


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    data: Any
    provenance: ProvenanceRecord
