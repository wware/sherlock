#!/usr/bin/env python3
"""
Relationship validator.
Input:  candidates.jsonl
Output: relationships.jsonl  (valid triples)
        rejected.jsonl       (domain/range failures; appended to any parser rejects)
"""

from __future__ import annotations

import json
import pathlib
from collections import Counter

SCHEMA = {
    "located_at": {"dom": {"person", "object"}, "ran": {"location"}},
    "knows_at": {"dom": {"person"}, "ran": {"person"}},
    "possesses": {"dom": {"person"}, "ran": {"object"}},
    "disguised_as": {"dom": {"person"}, "ran": {"disguise"}},
    "authored": {"dom": {"person"}, "ran": {"document"}},
    "contains": {"dom": {"location"}, "ran": {"object"}},
    "married_to": {"dom": {"person"}, "ran": {"person"}},
    "employed_by": {"dom": {"person"}, "ran": {"person", "organisation"}},
}


def prefix(entity_id: str) -> str:
    return entity_id.split(":", 1)[0] if ":" in entity_id else ""


def validate(candidate: dict) -> tuple[bool, str]:
    predicate = candidate.get("predicate", "")
    if predicate not in SCHEMA:
        return False, f"predicate {predicate!r} not in schema"

    dom = SCHEMA[predicate]["dom"]
    ran = SCHEMA[predicate]["ran"]
    subject_prefix = prefix(candidate.get("subject_id", ""))
    object_prefix = prefix(candidate.get("object_id", ""))

    if subject_prefix not in dom:
        return False, f"subject prefix {subject_prefix!r} not in dom({predicate})={dom}"
    if object_prefix not in ran:
        return False, f"object prefix {object_prefix!r} not in ran({predicate})={ran}"
    return True, "ok"


def load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rejection_category(reason: str) -> str:
    lowered = reason.lower()
    if "unknown predicate" in lowered or "predicate" in lowered:
        return "predicate_mismatch"
    if "id must have a type prefix" in lowered:
        return "id_format"
    if "not in dom(" in lowered or "not in ran(" in lowered:
        return "schema_domain_range"
    if "epistemic_status" in lowered:
        return "epistemic_status"
    return "other"


def main(
    candidates_file: str = "candidates.jsonl",
    relationships_out: str = "relationships.jsonl",
    rejected_file: str = "rejected.jsonl",
    mentions_resolved_file: str = "mentions_resolved.jsonl",
    entities_file: str = "entities.jsonl",
    raw_relationships_file: str = "raw_relationships.jsonl",
    chunks_file: str = "chunks.jsonl",
) -> None:
    candidates = load_jsonl(pathlib.Path(candidates_file))

    valid, rejected = [], []
    for candidate in candidates:
        ok, reason = validate(candidate)
        if ok:
            valid.append(candidate)
        else:
            rejected.append({**candidate, "failure_reason": reason, "stage": "validator"})

    rej_path = pathlib.Path(rejected_file)
    existing = rej_path.read_text(encoding="utf-8") if rej_path.exists() else ""
    with rej_path.open("w", encoding="utf-8") as f:
        f.write(existing)
        for rel in rejected:
            f.write(json.dumps(rel) + "\n")

    with pathlib.Path(relationships_out).open("w", encoding="utf-8") as f:
        for rel in valid:
            f.write(json.dumps(rel) + "\n")

    all_rejected = load_jsonl(rej_path)
    total_rejected = len(all_rejected)
    print(f"Valid:    {len(valid)}")
    print(f"Rejected: {len(rejected)} (validator) + prior stages = {total_rejected} total")

    if all_rejected:
        print("\nRejection breakdown by category:")
        for category, n in Counter(rejection_category(r.get("failure_reason", "")) for r in all_rejected).most_common():
            print(f"  {n:3d}x  {category}")

        print("\nRejection breakdown by stage:")
        for stage, n in Counter(r.get("stage", "unknown") for r in all_rejected).most_common():
            print(f"  {n:3d}x  {stage}")

    mentions_resolved = load_jsonl(pathlib.Path(mentions_resolved_file))
    entities = load_jsonl(pathlib.Path(entities_file))
    raw_relationships = load_jsonl(pathlib.Path(raw_relationships_file))
    chunks = load_jsonl(pathlib.Path(chunks_file))

    print("\nCoverage summary:")
    print(f"  mentions_resolved.jsonl: {len(mentions_resolved)}")
    print(f"  entities.jsonl:          {len(entities)}")
    print(f"  raw_relationships.jsonl: {len(raw_relationships)}")
    print(f"  candidates.jsonl:        {len(candidates)}")
    print(f"  relationships.jsonl:     {len(valid)}")
    print(f"  rejected.jsonl:          {total_rejected}")

    if chunks and raw_relationships:
        raw_per_chunk = Counter(rel.get("chunk_id") for rel in raw_relationships if rel.get("chunk_id") is not None)
        avg = len(raw_relationships) / len(chunks)
        print(f"\nRaw relationships per chunk: avg {avg:.2f} across {len(chunks)} chunks")
        if raw_per_chunk:
            print("Top chunks by raw relationship count:")
            for chunk_id, n in raw_per_chunk.most_common(5):
                print(f"  chunk {chunk_id}: {n}")


if __name__ == "__main__":
    main()
