#!/usr/bin/env python3
"""
Relationship parser.
Input:  raw_relationships.jsonl
Output: candidates.jsonl   (parseable candidates)
        rejected.jsonl     (parse/early-schema failures, with failure_reason)
"""

from __future__ import annotations

import json
import pathlib
import sys

try:
    from sherlock_graph.models import RelationshipCandidate
    from sherlock_graph.schema import HOLMES_SCHEMA
except ModuleNotFoundError:  # pragma: no cover - direct execution fallback
    sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
    from sherlock_graph.models import RelationshipCandidate
    from sherlock_graph.schema import HOLMES_SCHEMA


def main(
    in_file: str = "raw_relationships.jsonl",
    candidates_out: str = "candidates.jsonl",
    rejected_out: str = "rejected.jsonl",
) -> None:
    raw_relationships = [
        json.loads(line) for line in pathlib.Path(in_file).read_text(encoding="utf-8").splitlines() if line.strip()
    ]

    candidates, rejected = [], []
    for rel in raw_relationships:
        try:
            candidate = RelationshipCandidate(
                subject_id=rel["subject_id"],
                predicate=rel["predicate"],
                object_id=rel["object_id"],
                at_moment=rel.get("at_moment"),
                known_to=frozenset(rel.get("known_to", [])),
                epistemic_status=rel.get("epistemic_status", "ground_truth"),
                sentence_ids=tuple(rel.get("sentence_ids", [])),
                chunk_id=rel.get("chunk_id"),
            )
            allowed, reason = HOLMES_SCHEMA.allows(candidate.subject_id, candidate.predicate, candidate.object_id)
            if not allowed:
                raise ValueError(reason)
            candidates.append(candidate)
        except Exception as exc:
            rejected.append({**rel, "failure_reason": str(exc), "stage": "parser"})

    with pathlib.Path(candidates_out).open("w", encoding="utf-8") as f:
        for candidate in candidates:
            f.write(json.dumps(candidate.as_record()) + "\n")

    with pathlib.Path(rejected_out).open("w", encoding="utf-8") as f:
        for rel in rejected:
            f.write(json.dumps(rel) + "\n")

    print(f"Parsed:   {len(candidates)}")
    print(f"Rejected: {len(rejected)}")


if __name__ == "__main__":
    main()
