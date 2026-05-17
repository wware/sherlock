#!/usr/bin/env python3
"""
LLM relationship extraction.
Input:  chunks.jsonl, mentions_resolved.jsonl, entities.jsonl, sentences.jsonl
Output: raw_relationships.jsonl

Requires: pip install anthropic
Set ANTHROPIC_API_KEY in environment.
"""

import collections
import json
import pathlib

import anthropic

PROMPT_PATH = pathlib.Path("prompts/relationship_system_prompt.txt")


def main(
    chunks_file: str = "chunks.jsonl",
    mentions_file: str = "mentions_resolved.jsonl",
    entities_file: str = "entities.jsonl",
    sentences_file: str = "sentences.jsonl",
    out_file: str = "raw_relationships.jsonl",
) -> None:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    client = anthropic.Anthropic()

    chunks = {c["id"]: c for c in (json.loads(l) for l in pathlib.Path(chunks_file).read_text(encoding="utf-8").splitlines() if l.strip())}
    sentences = {s["id"]: s for s in (json.loads(l) for l in pathlib.Path(sentences_file).read_text(encoding="utf-8").splitlines() if l.strip())}
    entities = [json.loads(l) for l in pathlib.Path(entities_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    entity_by_id = {entity["id"]: entity for entity in entities if "id" in entity}

    mentions_by_chunk = collections.defaultdict(list)
    for mention in (json.loads(l) for l in pathlib.Path(mentions_file).read_text(encoding="utf-8").splitlines() if l.strip()):
        if mention.get("canonical_id"):
            mentions_by_chunk[mention["chunk_id"]].append(mention)

    out = pathlib.Path(out_file)
    errors = 0
    written = 0
    total_chunks = len(chunks)
    skipped_no_entities = 0
    skipped_missing_sentences = 0
    chunk_response_empty = 0
    processed_chunks = 0
    with out.open("w", encoding="utf-8") as f:
        for chunk_id, chunk in chunks.items():
            chunk_entities = {m["canonical_id"] for m in mentions_by_chunk.get(chunk_id, [])}
            if len(chunk_entities) < 2:
                skipped_no_entities += 1
                continue

            chunk_entity_rows = []
            for entity_id in sorted(chunk_entities):
                entity = entity_by_id.get(entity_id)
                if entity:
                    chunk_entity_rows.append(f"  {entity['id']} — {entity.get('name', entity_id)} ({entity.get('type', 'Unknown')})")
                else:
                    chunk_entity_rows.append(f"  {entity_id}")
            chunk_entity_list = "\n".join(chunk_entity_rows)

            available_sentence_ids = [sid for sid in chunk["sentence_ids"] if sid in sentences]
            if not available_sentence_ids:
                skipped_missing_sentences += 1
                continue
            body = "\n".join(f"[sent {sid}] {sentences[sid]['text']}" for sid in available_sentence_ids)
            user_msg = (
                "Use only the entity IDs listed below and the permitted predicates from the system prompt.\n"
                "If no valid relationship is supported by the passage, return an empty array.\n\n"
                f"Entities present in this passage:\n{chunk_entity_list}\n\n"
                f"Passage:\n{body}"
            )

            processed_chunks += 1
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            try:
                result = json.loads(resp.content[0].text)
                relationships = result.get("relationships", [])
                if not relationships:
                    chunk_response_empty += 1
                for rel in relationships:
                    rel["chunk_id"] = chunk_id
                    f.write(json.dumps(rel) + "\n")
                    written += 1
            except Exception as exc:
                errors += 1
                print(f"  chunk {chunk_id}: {exc}")

    print(f"Done. {errors} parse errors. See {out_file}.")
    print("\nRelationship extraction coverage:")
    print(f"  chunks total:                     {total_chunks}")
    print(f"  chunks processed by LLM:          {processed_chunks}")
    print(f"  chunks skipped (<2 entities):     {skipped_no_entities}")
    print(f"  chunks skipped (no sentences):    {skipped_missing_sentences}")
    print(f"  chunks with empty relationships:  {chunk_response_empty}")
    print(f"  relationships emitted:            {written}")


if __name__ == "__main__":
    main()
