#!/usr/bin/env bash
set -euo pipefail

scripts/fetch_sib.sh
python3 scripts/01_sentencize.py
python3 scripts/02_review_sentences.py
python3 scripts/03_chunk.py
python3 scripts/04_ner.py
python3 scripts/05_mention_store.py
python3 scripts/06_identity.py
python3 scripts/07_extract_relationships.py
python3 scripts/08_parse_relationships.py
python3 scripts/09_validate.py
