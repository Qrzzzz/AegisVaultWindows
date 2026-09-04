"""Console script entrypoint."""

from __future__ import annotations

from aegisvault.backend.server import main as run


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
