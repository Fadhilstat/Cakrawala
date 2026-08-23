from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if any(part == ".git" or part.startswith(".venv") for part in path.parts):
            continue
        if chr(0x2014) in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(root)))
    if offenders:
        print("Em dash found in Python files:")
        for offender in offenders:
            print(f"- {offender}")
        return 1
    print("Python no-em-dash check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

