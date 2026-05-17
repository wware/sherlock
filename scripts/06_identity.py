#!/usr/bin/env python3
"""
Identity server.
Input:  mentions.jsonl
Output: mentions_resolved.jsonl  (mentions with canonical_id added)
        entities.jsonl           (one record per canonical entity)
"""

import json
import pathlib
import re
from collections import Counter

IDENTITY_MAP = {
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

ENTITY_META = {
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

TYPE_PREFIX = {
    "person": "person",
    "location": "location",
    "object": "object",
    "document": "document",
    "moment": "moment",
    "event": "event",
    "disguise": "disguise",
    "plan": "plan",
    "organisation": "organisation",
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


def normalize_surface(text: str) -> str:
    normalized = text.strip().lower()
    normalized = re.sub(r"^[\"'\(\[]+|[\"'\),.;:!?\]]+$", "", normalized)
    return normalized


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug


def resolve_canonical_id(mention: dict) -> str | None:
    surface_form = mention.get("surface_form", "")
    key = normalize_surface(surface_form)
    if key in IDENTITY_MAP:
        return IDENTITY_MAP[key]

    if key == "monica":
        # In this corpus, standalone "Monica" mentions are references to St. Monica's Church.
        # Keep this constrained to location/event/moment mentions to avoid person-name collisions.
        mention_type = str(mention.get("type", "")).strip().lower()
        if mention_type in {"location", "event", "moment"}:
            return "location:st_monica_church"

    # Try matching without common honorifics/articles.
    simplified = re.sub(r"^(mr|mrs|ms|dr|miss|sir|lady)\.?\s+", "", key)
    simplified = re.sub(r"^the\s+", "", simplified)
    if simplified in IDENTITY_MAP:
        return IDENTITY_MAP[simplified]

    if key in GENERIC_SURFACES:
        return None

    mention_type = str(mention.get("type", "")).strip().lower()
    prefix = TYPE_PREFIX.get(mention_type)
    if not prefix:
        return None

    if len(key) < MIN_SURFACE_LENGTH:
        return None

    slug = slugify(simplified or key)
    if not slug or slug in GENERIC_SLUGS:
        return None

    return f"{prefix}:{slug}"


def main(
    in_file: str = "mentions.jsonl",
    resolved_out: str = "mentions_resolved.jsonl",
    entities_out: str = "entities.jsonl",
) -> None:
    mentions = [json.loads(l) for l in pathlib.Path(in_file).read_text(encoding="utf-8").splitlines() if l.strip()]

    resolved = []
    unresolved = []
    seen_entities = set()
    display_names: dict[str, Counter] = {}

    for mention in mentions:
        canonical_id = resolve_canonical_id(mention)
        mention["canonical_id"] = canonical_id
        if canonical_id:
            resolved.append(mention)
            seen_entities.add(canonical_id)
            display_names.setdefault(canonical_id, Counter())[mention.get("surface_form", "").strip()] += 1
        else:
            unresolved.append(mention)

    with pathlib.Path(resolved_out).open("w", encoding="utf-8") as f:
        for mention in resolved + unresolved:
            f.write(json.dumps(mention) + "\n")

    with pathlib.Path(entities_out).open("w", encoding="utf-8") as f:
        for entity_id in sorted(seen_entities):
            name_candidates = display_names.get(entity_id, Counter()).most_common(1)
            inferred_name = name_candidates[0][0] if name_candidates else entity_id
            inferred_prefix = entity_id.split(":", 1)[0] if ":" in entity_id else ""
            inferred_type = inferred_prefix.capitalize() if inferred_prefix in TYPE_PREFIX else "Unknown"
            meta = ENTITY_META.get(entity_id, {"name": inferred_name, "type": inferred_type, "wiki": None})
            f.write(json.dumps({"id": entity_id, **meta}) + "\n")

    print(f"Resolved:   {len(resolved)} mentions → {len(seen_entities)} entities")
    print(f"Unresolved: {len(unresolved)} mentions")
    if unresolved:
        print("\nTop unresolved surface forms (add to IDENTITY_MAP):")
        for sf, n in Counter(m["surface_form"] for m in unresolved).most_common(10):
            print(f"  {n:3d}x  {sf!r}")


if __name__ == "__main__":
    main()
