#!/usr/bin/env python3
"""
Mention store.
Input:  raw_mentions.jsonl
Output: mentions.jsonl  (deduplicated by surface_form + sentence_id + type)
"""

import json
import pathlib
from collections import Counter


def main(in_file: str = "raw_mentions.jsonl", out_file: str = "mentions.jsonl") -> None:
    raw = [json.loads(l) for l in pathlib.Path(in_file).read_text(encoding="utf-8").splitlines() if l.strip()]

    seen = set()
    unique = []
    for mention in raw:
        key = (
            mention.get("surface_form", "").strip().lower(),
            mention.get("sentence_id"),
            mention.get("type", ""),
        )
        if key not in seen:
            seen.add(key)
            unique.append(mention)

    with pathlib.Path(out_file).open("w", encoding="utf-8") as f:
        for mention in unique:
            f.write(json.dumps(mention) + "\n")

    print(f"Raw mentions:    {len(raw)}")
    print(f"Unique mentions: {len(unique)}")
    print(f"Duplicates:      {len(raw) - len(unique)}")

    by_type = Counter(m.get("type", "?") for m in unique)
    print("\nMentions by entity type:")
    for typ, n in by_type.most_common():
        print(f"  {typ:<15} {n}")


if __name__ == "__main__":
    main()
