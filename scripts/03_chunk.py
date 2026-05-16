#!/usr/bin/env python3
"""
Chunker.
Input:  sentences.jsonl
Output: chunks.jsonl  (id, sentence_ids, text)

Adjust CHUNK_SIZE and OVERLAP to taste.
"""

import json
import pathlib

CHUNK_SIZE = 8
OVERLAP = 2


def main(
    in_file: str = "sentences.jsonl",
    out_file: str = "chunks.jsonl",
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    sentences = [json.loads(l) for l in pathlib.Path(in_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    if not sentences:
        pathlib.Path(out_file).write_text("", encoding="utf-8")
        print("Wrote 0 chunks")
        return

    chunks = []
    i = 0
    chunk_id = 0
    step = chunk_size - overlap

    while i < len(sentences):
        window = sentences[i : i + chunk_size]
        chunks.append(
            {
                "id": chunk_id,
                "sentence_ids": [s["id"] for s in window],
                "text": " ".join(s["text"] for s in window),
                "start_sent": window[0]["id"],
                "end_sent": window[-1]["id"],
            }
        )
        chunk_id += 1
        i += step

    with pathlib.Path(out_file).open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")

    print(f"Wrote {len(chunks)} chunks (size={chunk_size}, overlap={overlap})")
    print(f"Sentence coverage: {chunks[-1]['end_sent'] + 1}/{len(sentences)} sentences")


if __name__ == "__main__":
    main()
