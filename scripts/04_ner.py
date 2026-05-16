#!/usr/bin/env python3
"""
LLM NER pass.
Input:  chunks.jsonl, sentences.jsonl
Output: raw_mentions.jsonl

Requires: pip install anthropic
Set ANTHROPIC_API_KEY in environment.
"""

import json
import pathlib

import anthropic

ENTITY_TYPES = ["Person", "Location", "Object", "Document", "Moment", "Event", "Disguise", "Plan"]
PROMPT_PATH = pathlib.Path("prompts/ner_system_prompt.txt")


def main(
    chunk_file: str = "chunks.jsonl",
    sentence_file: str = "sentences.jsonl",
    out_file: str = "raw_mentions.jsonl",
) -> None:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    client = anthropic.Anthropic()
    chunks = [json.loads(l) for l in pathlib.Path(chunk_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    sentences = {
        s["id"]: s for s in (json.loads(l) for l in pathlib.Path(sentence_file).read_text(encoding="utf-8").splitlines() if l.strip())
    }

    out = pathlib.Path(out_file)
    errors = 0

    with out.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            body = "\n".join(
                f"[sent {sid}] {sentences[sid]['text']}" for sid in chunk["sentence_ids"] if sid in sentences
            )

            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": body}],
            )
            try:
                result = json.loads(resp.content[0].text)
                for entity in result.get("entities", []):
                    if entity.get("type") not in ENTITY_TYPES:
                        continue
                    entity["chunk_id"] = chunk["id"]
                    f.write(json.dumps(entity) + "\n")
            except Exception as exc:
                errors += 1
                print(f"  chunk {chunk['id']}: parse error — {exc}")

    print(f"Done. {errors} parse errors. See {out_file}.")


if __name__ == "__main__":
    main()
