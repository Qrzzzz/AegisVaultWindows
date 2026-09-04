"""Create the deterministic public ZIP around the signed Windows executable."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _source_date_epoch() -> int:
    value = subprocess.run(
        ["git", "-C", str(ROOT), "show", "-s", "--format=%ct", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    return int(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--executable", type=Path)
    inputs.add_argument("--directory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-date-epoch", type=int)
    args = parser.parse_args()

    directory = args.directory.resolve(strict=True) if args.directory else None
    executable = args.executable.resolve(strict=True) if args.executable else None
    output = args.output.resolve()
    epoch = args.source_date_epoch if args.source_date_epoch is not None else _source_date_epoch()
    timestamp = dt.datetime.fromtimestamp(epoch, tz=dt.UTC).replace(tzinfo=None)
    timestamp = max(timestamp, dt.datetime(1980, 1, 1))
    zip_timestamp = (timestamp.year, timestamp.month, timestamp.day, timestamp.hour, timestamp.minute, timestamp.second // 2 * 2)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        files = sorted(path for path in directory.rglob("*") if path.is_file()) if directory else [executable]
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in files:
                assert path is not None
                if path.is_symlink():
                    raise ValueError("Package inputs must not be symlinks")
                name = path.relative_to(directory).as_posix() if directory else path.name
                info = zipfile.ZipInfo(name, date_time=zip_timestamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100755 & 0xFFFF) << 16
                with path.open("rb") as source, archive.open(info, "w", force_zip64=True) as destination:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
