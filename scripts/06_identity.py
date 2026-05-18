#!/usr/bin/env python3
"""
Identity server.
Input:  mentions.jsonl
Output: mentions_resolved.jsonl  (mentions with canonical_id added)
        entities.jsonl           (one record per canonical entity)
"""

from __future__ import annotations

import json
import pathlib
from collections import Counter

from sherlock_graph.identity import HolmesIdentityResolver
from sherlock_graph.models import Mention


def main(
    in_file: str = "mentions.jsonl",
    resolved_out: str = "mentions_resolved.jsonl",
    entities_out: str = "entities.jsonl",
) -> None:
    mentions = [Mention.model_validate_json(line) for line in pathlib.Path(in_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    resolver = HolmesIdentityResolver()

    resolved = []
    unresolved = []
    seen_entities = set()
    display_names: dict[str, Counter] = {}

    for mention in mentions:
        canonical_id = resolver.resolve_canonical_id(mention)
        mention_record = mention.as_record()
        mention_record["canonical_id"] = canonical_id
        resolved_mention = Mention.model_validate(mention_record)
        if canonical_id:
            resolved.append(resolved_mention)
            seen_entities.add(canonical_id)
            display_names.setdefault(canonical_id, Counter())[mention.surface_form.strip()] += 1
        else:
            unresolved.append(resolved_mention)

    with pathlib.Path(resolved_out).open("w", encoding="utf-8") as f:
        for mention in resolved + unresolved:
            f.write(json.dumps(mention.as_record()) + "\n")

    with pathlib.Path(entities_out).open("w", encoding="utf-8") as f:
        for entity_id in sorted(seen_entities):
            name_candidates = display_names.get(entity_id, Counter()).most_common(1)
            inferred_name = name_candidates[0][0] if name_candidates else entity_id
            entity = resolver.build_entity(entity_id, inferred_name)
            f.write(json.dumps(entity.as_record()) + "\n")

    print(f"Resolved:   {len(resolved)} mentions → {len(seen_entities)} entities")
    print(f"Unresolved: {len(unresolved)} mentions")
    if unresolved:
        print("\nTop unresolved surface forms (add to IDENTITY_MAP):")
        for sf, n in Counter(m.surface_form for m in unresolved).most_common(10):
            print(f"  {n:3d}x  {sf!r}")


if __name__ == "__main__":
    main()
