from pathlib import Path


def test_python_files_do_not_contain_em_dash() -> None:
    root = Path(__file__).resolve().parents[1]
    offenders = [
        path
        for path in root.rglob("*.py")
        if ".venv" not in path.parts and chr(0x2014) in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
