"""A minimal persistent command-line counter."""

import argparse
from pathlib import Path


def read_count(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Increment or show a saved count.")
    parser.add_argument("action", choices=("increment", "show"))
    parser.add_argument("--file", type=Path, default=Path("counter.txt"))
    args = parser.parse_args()
    count = read_count(args.file)
    if args.action == "increment":
        count += 1
        args.file.write_text(str(count), encoding="utf-8")
    print(count)


if __name__ == "__main__":
    main()
