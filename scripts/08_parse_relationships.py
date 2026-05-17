#!/usr/bin/env python3
"""
Relationship parser.
Input:  raw_relationships.jsonl
Output: candidates.jsonl   (parseable candidates)
        rejected.jsonl     (parse failures, with failure_reason)

Uses Pydantic for validation and normalisation.
Requires: pip install pydantic
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Literal

try:
    from pydantic import BaseModel, ConfigDict, field_validator, model_validator
except Exception:  # pragma: no cover - optional dependency fallback
    BaseModel = None

KNOWN_PREDICATES = {
    "located_at",
    "knows_at",
    "possesses",
    "disguised_as",
    "authored",
    "contains",
    "married_to",
    "employed_by",
}
EPISTEMIC_STATUSES = {"ground_truth", "believed", "false_belief", "inferred"}
# Defensive normalization for common LLM output variants, even though prompts require canonical predicates.
PREDICATE_ALIASES = {
    "located_in": "located_at",
    "in_location": "located_at",
    "is_at": "located_at",
    "knows": "knows_at",
    "acquainted_with": "knows_at",
    "has": "possesses",
    "owns": "possesses",
    "holds": "possesses",
    "carries": "possesses",
    "written_by": "authored",
    "wrote": "authored",
    "sent": "authored",
    "inside": "contains",
    "works_for": "employed_by",
    "employed_at": "employed_by",
}


def canonicalize_predicate(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    return PREDICATE_ALIASES.get(normalized, normalized)


def canonicalize_moment(value: str | None, sentence_ids: tuple[int, ...]) -> str | None:
    if sentence_ids:
        default = f"moment:sent_{min(sentence_ids)}"
    else:
        default = None

    if value is None:
        return default

    raw = value.strip().lower()
    if not raw:
        return default

    if re.fullmatch(r"moment:sent_\d+", raw):
        return raw

    sent_match = re.search(r"(?:sent(?:ence)?[_\s-]*)(\d+)", raw)
    if sent_match:
        return f"moment:sent_{sent_match.group(1)}"

    trailing_num = re.search(r"(\d+)$", raw)
    if trailing_num:
        return f"moment:sent_{trailing_num.group(1)}"

    return default


if BaseModel:
    class RelationshipCandidate(BaseModel):
        model_config = ConfigDict(frozen=True)

        subject_id: str
        predicate: str
        object_id: str
        at_moment: str | None = None
        known_to: frozenset[str] = frozenset()
        epistemic_status: Literal["ground_truth", "believed", "false_belief", "inferred"] = "ground_truth"
        sentence_ids: tuple[int, ...] = ()
        chunk_id: int | None = None

        @field_validator("predicate")
        @classmethod
        def normalise_predicate(cls, value: str) -> str:
            return canonicalize_predicate(value)

        @field_validator("subject_id", "object_id")
        @classmethod
        def require_prefix(cls, value: str) -> str:
            if ":" not in value:
                raise ValueError(f"ID must have a type prefix, got {value!r}")
            return value.strip()

        @model_validator(mode="before")
        @classmethod
        def normalise_moment(cls, values: dict) -> dict:
            sentence_ids = tuple(values.get("sentence_ids", []))
            values["at_moment"] = canonicalize_moment(values.get("at_moment"), sentence_ids)
            return values

        @model_validator(mode="after")
        def predicate_must_be_known(self) -> "RelationshipCandidate":
            if self.predicate not in KNOWN_PREDICATES:
                raise ValueError(f"Unknown predicate {self.predicate!r}")
            return self
else:
    class RelationshipCandidate:
        def __init__(
            self,
            subject_id: str,
            predicate: str,
            object_id: str,
            at_moment: str | None = None,
            known_to: frozenset[str] = frozenset(),
            epistemic_status: Literal["ground_truth", "believed", "false_belief", "inferred"] = "ground_truth",
            sentence_ids: tuple[int, ...] = (),
            chunk_id: int | None = None,
        ) -> None:
            predicate = canonicalize_predicate(predicate)
            sentence_ids = tuple(sentence_ids)
            at_moment = canonicalize_moment(at_moment, sentence_ids)
            if ":" not in subject_id:
                raise ValueError(f"ID must have a type prefix, got {subject_id!r}")
            if ":" not in object_id:
                raise ValueError(f"ID must have a type prefix, got {object_id!r}")
            if predicate not in KNOWN_PREDICATES:
                raise ValueError(f"Unknown predicate {predicate!r}")
            if epistemic_status not in EPISTEMIC_STATUSES:
                raise ValueError(f"Unknown epistemic_status {epistemic_status!r}")
            self.subject_id = subject_id.strip()
            self.predicate = predicate
            self.object_id = object_id.strip()
            self.at_moment = at_moment
            self.known_to = frozenset(known_to)
            self.epistemic_status = epistemic_status
            self.sentence_ids = sentence_ids
            self.chunk_id = chunk_id

        def model_dump_json(self) -> str:
            return json.dumps(
                {
                    "subject_id": self.subject_id,
                    "predicate": self.predicate,
                    "object_id": self.object_id,
                    "at_moment": self.at_moment,
                    "known_to": sorted(self.known_to),
                    "epistemic_status": self.epistemic_status,
                    "sentence_ids": list(self.sentence_ids),
                    "chunk_id": self.chunk_id,
                }
            )


def main(
    in_file: str = "raw_relationships.jsonl",
    candidates_out: str = "candidates.jsonl",
    rejected_out: str = "rejected.jsonl",
) -> None:
    raw = [json.loads(l) for l in pathlib.Path(in_file).read_text(encoding="utf-8").splitlines() if l.strip()]

    candidates, rejected = [], []
    for rel in raw:
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
            candidates.append(candidate)
        except Exception as exc:
            rejected.append({**rel, "failure_reason": str(exc), "stage": "parser"})

    with pathlib.Path(candidates_out).open("w", encoding="utf-8") as f:
        for candidate in candidates:
            f.write(candidate.model_dump_json() + "\n")

    with pathlib.Path(rejected_out).open("w", encoding="utf-8") as f:
        for rel in rejected:
            f.write(json.dumps(rel) + "\n")

    print(f"Parsed:   {len(candidates)}")
    print(f"Rejected: {len(rejected)}")


if __name__ == "__main__":
    main()
