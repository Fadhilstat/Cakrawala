from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ProvenanceRecord:
    provider: str
    source_url: str
    fetched_at: datetime
    sha256: str
    byte_count: int


def build_provenance(provider: str, source_url: str, raw: bytes) -> ProvenanceRecord:
    return ProvenanceRecord(
        provider=provider,
        source_url=source_url,
        fetched_at=datetime.now(timezone.utc),
        sha256=hashlib.sha256(raw).hexdigest(),
        byte_count=len(raw),
    )
