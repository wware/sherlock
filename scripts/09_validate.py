#!/usr/bin/env python3
"""
Stage 10: relationship validator.
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


def main(
    candidates_file: str = "candidates.jsonl",
    relationships_out: str = "relationships.jsonl",
    rejected_file: str = "rejected.jsonl",
) -> None:
    candidates = [json.loads(l) for l in pathlib.Path(candidates_file).read_text(encoding="utf-8").splitlines() if l.strip()]

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

    total_rejected = len([line for line in rej_path.read_text(encoding="utf-8").splitlines() if line.strip()])
    print(f"Valid:    {len(valid)}")
    print(f"Rejected: {len(rejected)} (validator) + prior stages = {total_rejected} total")

    if rejected:
        print("\nRejection breakdown:")
        for reason, n in Counter(r["failure_reason"].split("not in")[0].strip() for r in rejected).most_common():
            print(f"  {n:3d}x  {reason}")


if __name__ == "__main__":
    main()
