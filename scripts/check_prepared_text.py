"""Accept a restored checkpoint only if structurally complete and still unused."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from topic_history import DuplicateTopicError, TopicHistory


def usable_checkpoint(path: Path, history_path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(payload, dict) or not isinstance(payload.get("title"), str)
                or not payload["title"].strip() or not isinstance(payload.get("narration"), str)
                or not payload["narration"].strip()):
            raise ValueError("Incomplete prepared text")
    except (ValueError, OSError):
        path.unlink(missing_ok=True)
        return False
    try:
        # Corrupt permanent history remains fatal; only an actual duplicate is
        # recoverable by choosing fresh text in this slot.
        TopicHistory(history_path).check_unique(payload)
    except DuplicateTopicError:
        path.unlink()
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    args = parser.parse_args()
    usable = usable_checkpoint(args.path, args.history)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"usable={str(usable).lower()}\n")
    print("Prepared text is complete and unused" if usable else "No reusable unused text; request fresh generation")


if __name__ == "__main__":
    main()
