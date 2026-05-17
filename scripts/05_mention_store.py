#!/usr/bin/env python3
"""
Mention store.
Input:  raw_mentions.jsonl
Output: mentions.jsonl  (deduplicated by surface_form + sentence_id + type)
"""

import json
import pathlib
from collections import Counter

PRONOUN_SURFACES = {
    "he",
    "she",
    "him",
    "her",
    "his",
    "hers",
    "they",
    "them",
    "their",
    "it",
    "its",
}


def main(in_file: str = "raw_mentions.jsonl", out_file: str = "mentions.jsonl") -> None:
    raw = [json.loads(l) for l in pathlib.Path(in_file).read_text(encoding="utf-8").splitlines() if l.strip()]

    seen = set()
    unique = []
    dropped_pronouns = 0
    for mention in raw:
        surface = mention.get("surface_form", "").strip().lower()
        if surface in PRONOUN_SURFACES and len(surface.split()) == 1:
            dropped_pronouns += 1
            continue
        key = (
            surface,
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
    print(f"Duplicates:      {len(raw) - len(unique) - dropped_pronouns}")
    print(f"Pronouns pruned: {dropped_pronouns}")

    by_type = Counter(m.get("type", "?") for m in unique)
    print("\nMentions by entity type:")
    for typ, n in by_type.most_common():
        print(f"  {typ:<15} {n}")


if __name__ == "__main__":
    main()
