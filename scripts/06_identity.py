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
    "miss adler": "person:irene_adler",
    "mrs. norton": "person:irene_adler",
    "mrs norton": "person:irene_adler",
    "the woman": "person:irene_adler",
    "the king": "person:king_of_bohemia",
    "his majesty": "person:king_of_bohemia",
    "the count von kramm": "person:king_of_bohemia",
    "wilhelm": "person:king_of_bohemia",
    "norton": "person:godfrey_norton",
    "godfrey norton": "person:godfrey_norton",
    "mr. norton": "person:godfrey_norton",
    "baker street": "location:baker_street",
    "221b": "location:baker_street",
    "briony lodge": "location:briony_lodge",
    "serpentine avenue": "location:briony_lodge",
    "st. monica": "location:st_monica_church",
    "the photograph": "object:photograph",
    "the picture": "object:photograph",
    "the letter": "object:letter",
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
    "object:letter": {"name": "The letter", "type": "Object", "wiki": None},
}


def normalize_surface(text: str) -> str:
    normalized = text.strip().lower()
    normalized = re.sub(r"^[\"'\(\[]+|[\"'\),.;:!?\]]+$", "", normalized)
    return normalized


def main(
    in_file: str = "mentions.jsonl",
    resolved_out: str = "mentions_resolved.jsonl",
    entities_out: str = "entities.jsonl",
) -> None:
    mentions = [json.loads(l) for l in pathlib.Path(in_file).read_text(encoding="utf-8").splitlines() if l.strip()]

    resolved = []
    unresolved = []
    seen_entities = set()

    for mention in mentions:
        key = normalize_surface(mention.get("surface_form", ""))
        canonical_id = IDENTITY_MAP.get(key)
        mention["canonical_id"] = canonical_id
        if canonical_id:
            resolved.append(mention)
            seen_entities.add(canonical_id)
        else:
            unresolved.append(mention)

    with pathlib.Path(resolved_out).open("w", encoding="utf-8") as f:
        for mention in resolved + unresolved:
            f.write(json.dumps(mention) + "\n")

    with pathlib.Path(entities_out).open("w", encoding="utf-8") as f:
        for entity_id in sorted(seen_entities):
            meta = ENTITY_META.get(entity_id, {"name": entity_id, "type": "Unknown", "wiki": None})
            f.write(json.dumps({"id": entity_id, **meta}) + "\n")

    print(f"Resolved:   {len(resolved)} mentions → {len(seen_entities)} entities")
    print(f"Unresolved: {len(unresolved)} mentions")
    if unresolved:
        print("\nTop unresolved surface forms (add to IDENTITY_MAP):")
        for sf, n in Counter(m["surface_form"] for m in unresolved).most_common(10):
            print(f"  {n:3d}x  {sf!r}")


if __name__ == "__main__":
    main()
