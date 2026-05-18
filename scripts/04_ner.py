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
import re
import sys

import anthropic
try:
    from sherlock_graph.schema import HOLMES_LLM_ENTITY_TYPES
except ModuleNotFoundError:  # pragma: no cover - direct execution fallback
    sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
    from sherlock_graph.schema import HOLMES_LLM_ENTITY_TYPES

try:
    from llm_json import anthropic_text, parse_llm_json
except ModuleNotFoundError:  # pragma: no cover - direct execution fallback
    sys.path.append(str(pathlib.Path(__file__).resolve().parent))
    from llm_json import anthropic_text, parse_llm_json

PROMPT_PATH = pathlib.Path("prompts/ner_system_prompt.txt")


def sentence_contains_surface(sentence_text: str, surface_form: str) -> bool:
    escaped = re.escape(surface_form.strip())
    if not escaped:
        return False
    pattern = r"\b" + escaped.replace(" ", r"\s+") + r"\b"
    return bool(re.search(pattern, sentence_text, flags=re.IGNORECASE))


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
            chunk_sentence_ids = [sid for sid in chunk["sentence_ids"] if sid in sentences]
            sentence_text_by_id = {sid: sentences[sid]["text"] for sid in chunk_sentence_ids}
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
                result = parse_llm_json(anthropic_text(resp))
                for entity in result.get("entities", []):
                    if entity.get("type") not in HOLMES_LLM_ENTITY_TYPES:
                        continue
                    surface_form = str(entity.get("surface_form", "")).strip()
                    if not surface_form:
                        continue
                    sentence_id = entity.get("sentence_id")
                    if sentence_id not in sentence_text_by_id:
                        # Recover sentence assignment from chunk context.
                        matching_sid = next(
                            (sid for sid, text in sentence_text_by_id.items() if sentence_contains_surface(text, surface_form)),
                            None,
                        )
                        if matching_sid is None and len(chunk_sentence_ids) == 1:
                            matching_sid = chunk_sentence_ids[0]
                        if matching_sid is None:
                            continue
                        entity["sentence_id"] = matching_sid
                    entity["chunk_id"] = chunk["id"]
                    f.write(json.dumps(entity) + "\n")
            except Exception as exc:
                errors += 1
                print(f"  chunk {chunk['id']}: parse error — {exc}")

    print(f"Done. {errors} parse errors. See {out_file}.")


if __name__ == "__main__":
    main()
