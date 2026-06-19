"""Module entrypoint for seeding the Golden bucket."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from retail_agent.evaluation import DEFAULT_SEED_PATH, ingest_seed_trios


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for Golden-bucket ingestion."""

    parser = argparse.ArgumentParser(description="Ingest eval seed Trios into the Golden bucket.")
    parser.add_argument("--seed-path", type=Path, default=DEFAULT_SEED_PATH)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ingest seed Trios and write the inserted row count to stdout."""

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    inserted = ingest_seed_trios(args.seed_path)
    sys.stdout.write(f"Inserted {inserted} Golden Trios\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
