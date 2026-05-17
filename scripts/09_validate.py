#!/usr/bin/env python3
"""
Relationship validator.
Input:  candidates.jsonl
Output: relationships.jsonl  (valid triples)
        rejected.jsonl       (domain/range failures; appended to any parser rejects)
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
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

    at_moment = candidate.get("at_moment")
    if at_moment is not None:
        at_moment = str(at_moment).strip()
        if at_moment and not re.fullmatch(r"moment:sent_\d+", at_moment):
            return False, f"at_moment must be sentence-indexed form moment:sent_<n>, got {at_moment!r}"
    return True, "ok"


def load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rejection_category(reason: str) -> str:
    lowered = reason.lower()
    if "unknown predicate" in lowered or "not in schema" in lowered:
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
    min_relationships: int = 1,
    min_relationships_per_chunk: float = 0.03,
    min_resolved_ratio: float = 0.15,
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

    if raw_relationships and len(chunks) > 0:
        raw_per_chunk = Counter()
        raw_total = 0
        for rel in raw_relationships:
            raw_total += 1
            chunk_id = rel.get("chunk_id")
            if chunk_id is not None:
                raw_per_chunk[chunk_id] += 1
        avg = raw_total / len(chunks)
        print(f"\nRaw relationships per chunk: avg {avg:.2f} across {len(chunks)} chunks")
        if raw_per_chunk:
            print("Top chunks by raw relationship count:")
            for chunk_id, n in raw_per_chunk.most_common(5):
                print(f"  chunk {chunk_id}: {n}")

    print("\nQuality gates:")
    gate_failures = []
    chunk_count = max(len(chunks), 1)
    relationships_per_chunk = len(valid) / chunk_count

    resolved_mentions = sum(1 for mention in mentions_resolved if mention.get("canonical_id"))
    resolved_ratio = resolved_mentions / max(len(mentions_resolved), 1)

    print(f"  min relationships:          {min_relationships} (actual {len(valid)})")
    print(f"  min rel/chunk:              {min_relationships_per_chunk:.3f} (actual {relationships_per_chunk:.3f})")
    print(f"  min resolved mention ratio: {min_resolved_ratio:.3f} (actual {resolved_ratio:.3f})")

    if len(valid) < min_relationships:
        gate_failures.append("relationships below threshold")
    if relationships_per_chunk < min_relationships_per_chunk:
        gate_failures.append("relationships-per-chunk below threshold")
    if resolved_ratio < min_resolved_ratio:
        gate_failures.append("resolved mention ratio below threshold")

    if gate_failures:
        print("\nQuality gate failures:")
        for failure in gate_failures:
            print(f"  - {failure}")
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate relationship candidates and enforce quality gates.")
    parser.add_argument("--candidates_file", default="candidates.jsonl")
    parser.add_argument("--relationships_out", default="relationships.jsonl")
    parser.add_argument("--rejected_file", default="rejected.jsonl")
    parser.add_argument("--mentions_resolved_file", default="mentions_resolved.jsonl")
    parser.add_argument("--entities_file", default="entities.jsonl")
    parser.add_argument("--raw_relationships_file", default="raw_relationships.jsonl")
    parser.add_argument("--chunks_file", default="chunks.jsonl")
    parser.add_argument("--min_relationships", type=int, default=1)
    parser.add_argument("--min_relationships_per_chunk", type=float, default=0.03)
    parser.add_argument("--min_resolved_ratio", type=float, default=0.15)
    args = parser.parse_args()
    main(
        candidates_file=args.candidates_file,
        relationships_out=args.relationships_out,
        rejected_file=args.rejected_file,
        mentions_resolved_file=args.mentions_resolved_file,
        entities_file=args.entities_file,
        raw_relationships_file=args.raw_relationships_file,
        chunks_file=args.chunks_file,
        min_relationships=args.min_relationships,
        min_relationships_per_chunk=args.min_relationships_per_chunk,
        min_resolved_ratio=args.min_resolved_ratio,
    )
