from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class NodeType(StrEnum):
    pass


class EdgeType(StrEnum):
    pass


class HolmesNodeType(NodeType):
    PERSON = "person"
    LOCATION = "location"
    OBJECT = "object"
    DOCUMENT = "document"
    MOMENT = "moment"
    EVENT = "event"
    DISGUISE = "disguise"
    PLAN = "plan"
    ORGANISATION = "organisation"


class HolmesEdgeType(EdgeType):
    LOCATED_AT = "located_at"
    KNOWS_AT = "knows_at"
    POSSESSES = "possesses"
    DISGUISED_AS = "disguised_as"
    AUTHORED = "authored"
    CONTAINS = "contains"
    MARRIED_TO = "married_to"
    EMPLOYED_BY = "employed_by"


HOLMES_LLM_ENTITY_TYPES = (
    "Person",
    "Location",
    "Object",
    "Document",
    "Moment",
    "Event",
    "Disguise",
    "Plan",
)

HOLMES_EDGE_ALIASES = {
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


def extract_prefix(entity_id: str) -> str:
    return entity_id.split(":", 1)[0] if ":" in entity_id else ""


def canonicalize_predicate(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    return HOLMES_EDGE_ALIASES.get(normalized, normalized)


def canonicalize_moment(value: str | None, sentence_ids: tuple[int, ...]) -> str | None:
    non_negative_ids = tuple(sid for sid in sentence_ids if isinstance(sid, int) and not isinstance(sid, bool) and sid >= 0)
    if non_negative_ids:
        default = f"moment:sent_{min(non_negative_ids)}"
    else:
        default = None
    if value is None:
        return default

    raw = value.strip().lower()
    if not raw:
        return default

    if re.fullmatch(r"moment:sent_\d+", raw):
        return raw

    sent_match = re.search(r"\bsent(?:ence)?[_\s-]*(\d+)\b", raw)
    if sent_match:
        return f"moment:sent_{sent_match.group(1)}"

    trailing_num = re.search(r"(\d+)$", raw)
    if trailing_num:
        return f"moment:sent_{trailing_num.group(1)}"

    return default


class PredicateConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)
    dom: frozenset[str]
    ran: frozenset[str]


class GraphSchema(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    node_type_enum: type[NodeType]
    edge_type_enum: type[EdgeType]
    type_prefixes: dict[str, str]
    predicate_constraints: dict[str, PredicateConstraint]

    @model_validator(mode="after")
    def validate_predicate_constraints(self) -> "GraphSchema":
        node_values = {member.value for member in self.node_type_enum}
        edge_values = {member.value for member in self.edge_type_enum}
        for predicate, constraint in self.predicate_constraints.items():
            if predicate not in edge_values:
                raise ValueError(f"predicate {predicate!r} is not declared in edge_type_enum")
            unknown_dom = set(constraint.dom) - node_values
            unknown_ran = set(constraint.ran) - node_values
            if unknown_dom:
                raise ValueError(f"predicate {predicate!r} has unknown domain prefixes: {sorted(unknown_dom)}")
            if unknown_ran:
                raise ValueError(f"predicate {predicate!r} has unknown range prefixes: {sorted(unknown_ran)}")
        return self

    def is_known_predicate(self, predicate: str) -> bool:
        return predicate in self.predicate_constraints

    def allows(self, subject_id: str, predicate: str, object_id: str) -> tuple[bool, str]:
        if predicate not in self.predicate_constraints:
            return False, f"predicate {predicate!r} not in schema"
        constraint = self.predicate_constraints[predicate]
        subject_prefix = extract_prefix(subject_id)
        object_prefix = extract_prefix(object_id)
        if subject_prefix not in constraint.dom:
            return False, f"subject prefix {subject_prefix!r} not in dom({predicate})={set(constraint.dom)}"
        if object_prefix not in constraint.ran:
            return False, f"object prefix {object_prefix!r} not in ran({predicate})={set(constraint.ran)}"
        return True, "ok"

    def prefix_for_mention_type(self, mention_type: str) -> str | None:
        return self.type_prefixes.get(str(mention_type).strip().lower())


HOLMES_SCHEMA = GraphSchema(
    name="holmes",
    node_type_enum=HolmesNodeType,
    edge_type_enum=HolmesEdgeType,
    type_prefixes={
        "person": "person",
        "location": "location",
        "object": "object",
        "document": "document",
        "moment": "moment",
        "event": "event",
        "disguise": "disguise",
        "plan": "plan",
        "organisation": "organisation",
    },
    predicate_constraints={
        "located_at": PredicateConstraint(dom=frozenset({"person", "object"}), ran=frozenset({"location"})),
        "knows_at": PredicateConstraint(dom=frozenset({"person"}), ran=frozenset({"person"})),
        "possesses": PredicateConstraint(dom=frozenset({"person"}), ran=frozenset({"object"})),
        "disguised_as": PredicateConstraint(dom=frozenset({"person"}), ran=frozenset({"disguise"})),
        "authored": PredicateConstraint(dom=frozenset({"person"}), ran=frozenset({"document"})),
        "contains": PredicateConstraint(dom=frozenset({"location"}), ran=frozenset({"object"})),
        "married_to": PredicateConstraint(dom=frozenset({"person"}), ran=frozenset({"person"})),
        "employed_by": PredicateConstraint(dom=frozenset({"person"}), ran=frozenset({"person", "organisation"})),
    },
)
