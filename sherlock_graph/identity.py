from __future__ import annotations

import re

from .models import (
    DisguiseEntity,
    DocumentEntity,
    EntityNode,
    EventEntity,
    LocationEntity,
    Mention,
    MomentEntity,
    ObjectEntity,
    OrganisationEntity,
    PersonEntity,
    PlanEntity,
)
from .schema import HOLMES_SCHEMA

HOLMES_IDENTITY_MAP = {
    "holmes": "person:holmes",
    "sherlock holmes": "person:holmes",
    "mr. holmes": "person:holmes",
    "mr holmes": "person:holmes",
    "the detective": "person:holmes",
    "watson": "person:watson",
    "dr. watson": "person:watson",
    "dr watson": "person:watson",
    "irene": "person:irene_adler",
    "irene adler": "person:irene_adler",
    "adler": "person:irene_adler",
    "miss adler": "person:irene_adler",
    "mrs. norton": "person:irene_adler",
    "mrs norton": "person:irene_adler",
    "mrs. godfrey norton": "person:irene_adler",
    "mrs godfrey norton": "person:irene_adler",
    "the woman": "person:irene_adler",
    "the king": "person:king_of_bohemia",
    "his majesty": "person:king_of_bohemia",
    "his majesty, the king of bohemia": "person:king_of_bohemia",
    "the count von kramm": "person:king_of_bohemia",
    "wilhelm": "person:king_of_bohemia",
    "my client": "person:king_of_bohemia",
    "client": "person:king_of_bohemia",
    "norton": "person:godfrey_norton",
    "godfrey norton": "person:godfrey_norton",
    "mr. norton": "person:godfrey_norton",
    "mr norton": "person:godfrey_norton",
    "husband": "person:godfrey_norton",
    "boswell": "person:watson",
    "baker street": "location:baker_street",
    "221b": "location:baker_street",
    "briony lodge": "location:briony_lodge",
    "serpentine avenue": "location:briony_lodge",
    "st. monica": "location:st_monica_church",
    "st monica": "location:st_monica_church",
    "st. monica's church": "location:st_monica_church",
    "st monica's church": "location:st_monica_church",
    "monica's church": "location:st_monica_church",
    "church of st. monica": "location:st_monica_church",
    "the photograph": "object:photograph",
    "photograph": "object:photograph",
    "the picture": "object:photograph",
    "picture": "object:photograph",
    "portrait": "object:photograph",
    "cabinet photograph": "object:photograph",
    "the letter": "document:letter",
    "letter": "document:letter",
    "the note": "document:letter",
    "note": "document:letter",
}

HOLMES_ENTITY_META = {
    "person:holmes": {"name": "Sherlock Holmes", "type": "Person", "wiki": "https://bakerstreet.fandom.com/wiki/Sherlock_Holmes"},
    "person:watson": {"name": "John H. Watson", "type": "Person", "wiki": "https://bakerstreet.fandom.com/wiki/John_H._Watson"},
    "person:irene_adler": {"name": "Irene Adler", "type": "Person", "wiki": "https://bakerstreet.fandom.com/wiki/Irene_Adler"},
    "person:king_of_bohemia": {"name": "King of Bohemia", "type": "Person", "wiki": "https://bakerstreet.fandom.com/wiki/Wilhelm_von_Ormstein"},
    "person:godfrey_norton": {"name": "Godfrey Norton", "type": "Person", "wiki": "https://bakerstreet.fandom.com/wiki/Godfrey_Norton"},
    "location:baker_street": {"name": "221B Baker Street", "type": "Location", "wiki": "https://bakerstreet.fandom.com/wiki/221B_Baker_Street"},
    "location:briony_lodge": {"name": "Briony Lodge", "type": "Location", "wiki": "https://bakerstreet.fandom.com/wiki/Briony_Lodge"},
    "location:st_monica_church": {"name": "St. Monica's Church", "type": "Location", "wiki": None},
    "object:photograph": {"name": "The photograph", "type": "Object", "wiki": None},
    "document:letter": {"name": "The letter", "type": "Document", "wiki": None},
}

MIN_SURFACE_LENGTH = 3
GENERIC_SURFACES = {
    "",
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
    "someone",
    "somebody",
    "something",
    "man",
    "woman",
    "gentleman",
    "lady",
    "the man",
    "the woman",
    "the gentleman",
    "the lady",
}
GENERIC_SLUGS = {
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
    "someone",
    "somebody",
    "something",
    "man",
    "woman",
    "gentleman",
    "lady",
    "the_man",
    "the_woman",
    "the_gentleman",
    "the_lady",
}


class HolmesIdentityResolver:
    DISPLAY_TYPE_BY_PREFIX = {
        "person": "Person",
        "location": "Location",
        "object": "Object",
        "document": "Document",
        "moment": "Moment",
        "event": "Event",
        "disguise": "Disguise",
        "plan": "Plan",
        "organisation": "Organisation",
    }

    ENTITY_CLASS_BY_PREFIX = {
        "person": PersonEntity,
        "location": LocationEntity,
        "object": ObjectEntity,
        "document": DocumentEntity,
        "moment": MomentEntity,
        "event": EventEntity,
        "disguise": DisguiseEntity,
        "plan": PlanEntity,
        "organisation": OrganisationEntity,
    }

    def normalize_surface(self, text: str) -> str:
        normalized = text.strip().lower()
        return re.sub(r"^[\"'\(\[]+|[\"'\),.;:!?\]]+$", "", normalized)

    def slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        return re.sub(r"_+", "_", slug)

    def resolve_canonical_id(self, mention: Mention) -> str | None:
        key = self.normalize_surface(mention.surface_form)
        if key in HOLMES_IDENTITY_MAP:
            return HOLMES_IDENTITY_MAP[key]

        if key == "monica":
            mention_type = str(mention.type).strip().lower()
            if mention_type in {"location", "event", "moment"}:
                return "location:st_monica_church"

        simplified = re.sub(r"^(mr|mrs|ms|dr|miss|sir|lady)\.?\s+", "", key)
        simplified = re.sub(r"^the\s+", "", simplified)
        if simplified in HOLMES_IDENTITY_MAP:
            return HOLMES_IDENTITY_MAP[simplified]

        if key in GENERIC_SURFACES:
            return None

        prefix = HOLMES_SCHEMA.prefix_for_mention_type(mention.type)
        if not prefix:
            return None
        if len(key) < MIN_SURFACE_LENGTH:
            return None

        slug = self.slugify(simplified or key)
        if not slug or slug in GENERIC_SLUGS:
            return None
        return f"{prefix}:{slug}"

    def build_entity(self, entity_id: str, inferred_name: str) -> EntityNode:
        inferred_prefix = entity_id.split(":", 1)[0] if ":" in entity_id else ""
        inferred_type = self.DISPLAY_TYPE_BY_PREFIX.get(inferred_prefix, "Object")
        meta = HOLMES_ENTITY_META.get(entity_id, {"name": inferred_name, "type": inferred_type, "wiki": None})
        entity_cls = self.ENTITY_CLASS_BY_PREFIX.get(inferred_prefix, EntityNode)
        entity_type = meta.get("type", inferred_type)
        if entity_cls is not EntityNode:
            entity_type = self.DISPLAY_TYPE_BY_PREFIX.get(inferred_prefix, inferred_type)
        return entity_cls(id=entity_id, name=meta["name"], wiki=meta["wiki"], type=entity_type)
