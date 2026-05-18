# sherlock

Build a typed graph for **"A Scandal in Bohemia"** using the 10-stage ingestion pipeline described in the referenced gist.

## Pipeline files

- `scripts/fetch_sib.sh`
- `scripts/01_sentencize.py`
- `scripts/02_review_sentences.py`
- `scripts/03_chunk.py`
- `prompts/ner_system_prompt.txt`
- `scripts/04_ner.py`
- `scripts/05_mention_store.py`
- `scripts/06_identity.py`
- `prompts/relationship_system_prompt.txt`
- `scripts/07_extract_relationships.py`
- `scripts/08_parse_relationships.py`
- `scripts/09_validate.py`
- `scripts/run_pipeline.sh`
- `sherlock_graph/` (shared typed graph schema/models used by stages 04/06/07/08/09)

## Quick start

```bash
chmod +x scripts/*.sh
scripts/fetch_sib.sh
python3 scripts/01_sentencize.py
python3 scripts/03_chunk.py
# Requires ANTHROPIC_API_KEY:
python3 scripts/04_ner.py
python3 scripts/05_mention_store.py
python3 scripts/06_identity.py
python3 scripts/07_extract_relationships.py
python3 scripts/08_parse_relationships.py
python3 scripts/09_validate.py
```

Final typed triples are written to `relationships.jsonl`; parser/validator failures are collected in `rejected.jsonl`.

The `sherlock_graph/kgraph_bridge.py` module provides early compatibility hooks so these typed records can be mapped into kgraph-style entity/relationship payloads when kgraph symbols are available.
