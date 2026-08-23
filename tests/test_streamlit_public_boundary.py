from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STREAMLIT_ENTRYPOINT = ROOT / "app" / "streamlit_app.py"
ROOT_STREAMLIT_ENTRYPOINT = ROOT / "streamlit_app.py"
PUBLIC_UI = ROOT / "src" / "cakrawala" / "terminal" / "enhanced_ui.py"
LEGACY_UI_MODULE = ROOT / "src" / "cakrawala" / "terminal" / "ui.py"
REMOVED_PERSONAL_UI = ROOT / "src" / "cakrawala" / "terminal" / "personal_ui.py"


def test_streamlit_entrypoint_uses_public_ui() -> None:
    for path in (STREAMLIT_ENTRYPOINT, ROOT_STREAMLIT_ENTRYPOINT):
        source = path.read_text(encoding="utf-8")
        assert "from cakrawala.terminal.enhanced_ui import run" in source
        assert "personal_ui" not in source


def test_public_streamlit_has_no_personal_auth_controls() -> None:
    forbidden = (
        "Personal Mode",
        "st.login",
        "st.logout",
        "st.user",
        "database_personal_url",
        "owner_sub",
    )
    for path in (PUBLIC_UI, LEGACY_UI_MODULE):
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source


def test_legacy_ui_run_delegates_to_public_terminal() -> None:
    source = LEGACY_UI_MODULE.read_text(encoding="utf-8")
    assert "from cakrawala.terminal.enhanced_ui import run as run_public_terminal" in source
    assert "run_public_terminal()" in source


def test_legacy_streamlit_personal_workspace_is_removed() -> None:
    assert not REMOVED_PERSONAL_UI.exists()

