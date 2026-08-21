from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "configs").is_dir():
        return source_root

    installed_root = Path(__file__).resolve().parents[1]
    if (installed_root / "configs").is_dir():
        return installed_root

    working_root = Path.cwd()
    if (working_root / "configs").is_dir():
        return working_root

    raise FileNotFoundError("Cakrawala runtime resources are unavailable")


def load_yaml(relative_path: str) -> dict[str, Any]:
    path = project_root() / relative_path
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {relative_path}")
    return data
