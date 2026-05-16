#!/usr/bin/env python3
"""
Sentence boundary detection + numbering.
Input:  sib.txt
Output: sentences.jsonl  (id, text, char_start, char_end, hash)

Install optional NLP support: pip install spacy && python -m spacy download en_core_web_sm
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re


def sentencize_with_spacy(text: str):
    import spacy  # type: ignore

    nlp = spacy.load(
        "en_core_web_sm",
        disable=["ner", "lemmatizer", "attribute_ruler", "tagger"],
    )
    doc = nlp(text)
    for sent in doc.sents:
        s = sent.text.strip()
        if s:
            yield s, sent.start_char, sent.end_char


def sentencize_fallback(text: str):
    # Basic sentence splitter fallback for environments without spaCy model.
    boundaries = [m.end() for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z\"'])", text)]
    starts = [0] + boundaries
    ends = boundaries + [len(text)]
    for start, end in zip(starts, ends):
        s = text[start:end].strip()
        if s:
            yield s, start, end


def main(in_file: str = "sib.txt", out_file: str = "sentences.jsonl") -> None:
    text = pathlib.Path(in_file).read_text(encoding="utf-8")

    try:
        rows = list(sentencize_with_spacy(text))
    except Exception:
        rows = list(sentencize_fallback(text))

    out = pathlib.Path(out_file)
    count = 0
    with out.open("w", encoding="utf-8") as f:
        for i, (s, start, end) in enumerate(rows):
            record = {
                "id": i,
                "text": s,
                "char_start": start,
                "char_end": end,
                "hash": hashlib.sha1(s.encode()).hexdigest()[:12],
            }
            f.write(json.dumps(record) + "\n")
            count += 1

    print(f"Wrote {count} sentences to {out}")


if __name__ == "__main__":
    main()
