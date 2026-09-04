"""Create a deterministic SHA256SUMS manifest for public release assets."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("assets", nargs="+", type=Path)
    args = parser.parse_args()
    assets = [asset.resolve(strict=True) for asset in args.assets]
    names = [asset.name for asset in assets]
    if len(names) != len(set(names)):
        parser.error("Asset basenames must be unique")
    lines = [f"{sha256(asset)}  {asset.name}" for asset in sorted(assets, key=lambda item: item.name)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
