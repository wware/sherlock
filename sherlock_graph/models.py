from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .schema import HOLMES_SCHEMA, canonicalize_moment, canonicalize_predicate, extract_prefix

EPISTEMIC_STATUSES = {"ground_truth", "believed", "false_belief", "inferred"}


class Mention(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    surface_form: str
    type: str
    sentence_id: int | None = None
    chunk_id: int | None = None
    canonical_id: str | None = None

    def as_record(self) -> dict:
        return self.model_dump(mode="json")


class EntityNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    id: str
    name: str
    type: str
    wiki: str | None = None

    @field_validator("id")
    @classmethod
    def id_must_be_prefixed(cls, value: str) -> str:
        if ":" not in value:
            raise ValueError(f"ID must have a type prefix, got {value!r}")
        return value

    def as_record(self) -> dict:
        return self.model_dump(mode="json")


class PersonEntity(EntityNode):
    type: Literal["Person"] = "Person"


class LocationEntity(EntityNode):
    type: Literal["Location"] = "Location"


class ObjectEntity(EntityNode):
    type: Literal["Object"] = "Object"


class DocumentEntity(EntityNode):
    type: Literal["Document"] = "Document"


class MomentEntity(EntityNode):
    type: Literal["Moment"] = "Moment"


class EventEntity(EntityNode):
    type: Literal["Event"] = "Event"


class DisguiseEntity(EntityNode):
    type: Literal["Disguise"] = "Disguise"


class PlanEntity(EntityNode):
    type: Literal["Plan"] = "Plan"


class OrganisationEntity(EntityNode):
    type: Literal["Organisation"] = "Organisation"


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
        if not extract_prefix(value):
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
        if not HOLMES_SCHEMA.is_known_predicate(self.predicate):
            raise ValueError(f"Unknown predicate {self.predicate!r}")
        return self

    def as_record(self) -> dict:
        return {
            "subject_id": self.subject_id,
            "predicate": self.predicate,
            "object_id": self.object_id,
            "at_moment": self.at_moment,
            "known_to": sorted(self.known_to),
            "epistemic_status": self.epistemic_status,
            "sentence_ids": list(self.sentence_ids),
            "chunk_id": self.chunk_id,
        }
