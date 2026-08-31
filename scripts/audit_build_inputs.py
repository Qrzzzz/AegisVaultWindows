"""Reject PyInstaller inputs that leaked in from an undeclared host toolchain."""

from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [item for child in value for item in _strings(child)]
    if isinstance(value, dict):
        return [item for child in value.items() for item in _strings(child)]
    return []


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-toc", required=True, type=Path)
    args = parser.parse_args()
    toc_path = args.analysis_toc.resolve(strict=True)
    value = ast.literal_eval(toc_path.read_text(encoding="utf-8"))

    windows_root = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")).resolve()
    allowed_roots = {
        ROOT.resolve(),
        Path(sys.base_prefix).resolve(),
        Path(sys.prefix).resolve(),
        windows_root,
    }
    absolute_paths = {
        Path(item).resolve()
        for item in _strings(value)
        if os.path.isabs(item)
    }
    unexpected = sorted(
        str(path)
        for path in absolute_paths
        if not any(_is_within(path, root) for root in allowed_roots)
    )
    if unexpected:
        parser.error("PyInstaller consumed undeclared host paths:\n" + "\n".join(unexpected))
    print(f"PyInstaller input-root audit passed: {len(absolute_paths)} absolute paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
