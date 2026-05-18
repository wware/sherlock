from __future__ import annotations

import importlib
from typing import Any

from .models import EntityNode, RelationshipCandidate

KGRAPH_MODULE_CANDIDATES = ("kgschema", "kgraph")
KGRAPH_SYMBOL_NAMES = ("BaseEntity", "BaseRelationship", "DomainSchema")


def _resolve_kgraph_symbols() -> tuple[type[Any] | None, type[Any] | None, type[Any] | None]:
    for module_name in KGRAPH_MODULE_CANDIDATES:
        try:
            module = importlib.import_module(module_name)
        except (ModuleNotFoundError, ImportError):
            continue
        base_entity = getattr(module, KGRAPH_SYMBOL_NAMES[0], None)
        base_relationship = getattr(module, KGRAPH_SYMBOL_NAMES[1], None)
        domain_schema = getattr(module, KGRAPH_SYMBOL_NAMES[2], None)
        if base_entity and base_relationship and domain_schema:
            return base_entity, base_relationship, domain_schema
    return None, None, None


KGRAPH_BASE_ENTITY, KGRAPH_BASE_RELATIONSHIP, KGRAPH_DOMAIN_SCHEMA = _resolve_kgraph_symbols()
KGRAPH_AVAILABLE = all((KGRAPH_BASE_ENTITY, KGRAPH_BASE_RELATIONSHIP, KGRAPH_DOMAIN_SCHEMA))


def to_kgraph_entity_payload(entity: EntityNode) -> dict[str, Any]:
    return entity.as_record()


def to_kgraph_relationship_payload(relationship: RelationshipCandidate) -> dict[str, Any]:
    return relationship.as_record()
