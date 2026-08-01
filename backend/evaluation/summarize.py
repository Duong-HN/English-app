from __future__ import annotations

import argparse
import json
from pathlib import Path

from .rubric import summarize_reviews


def load_reviews(path: Path) -> list[dict]:
    reviews = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise SystemExit(f"Review at {path}:{line_number} must be an object")
        reviews.append(value)
    return reviews


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize human AI evaluation reviews")
    parser.add_argument("reviews", type=Path, help="JSONL file containing one review per line")
    args = parser.parse_args()
    print(json.dumps(summarize_reviews(load_reviews(args.reviews)), indent=2))


if __name__ == "__main__":
    main()
