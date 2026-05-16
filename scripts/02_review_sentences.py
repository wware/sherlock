#!/usr/bin/env python3
"""
Review sentence split before running LLM stages.
Prints a sample and flags suspiciously short or long sentences.
"""

import json
import pathlib


def main(path: str = "sentences.jsonl") -> None:
    sentences = [json.loads(l) for l in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]

    print(f"Total sentences: {len(sentences)}")
    if not sentences:
        return
    print(f"Avg length:      {sum(len(s['text']) for s in sentences) // len(sentences)} chars\n")

    short = [s for s in sentences if len(s["text"]) < 20]
    long = [s for s in sentences if len(s["text"]) > 400]

    if short:
        print(f"Short sentences ({len(short)}) — possible split errors:")
        for s in short[:10]:
            print(f"  [{s['id']:3d}] {s['text']!r}")

    if long:
        print(f"\nLong sentences ({len(long)}) — possible missed boundaries:")
        for s in long[:5]:
            print(f"  [{s['id']:3d}] {s['text'][:80]}...")

    print("\nFirst 5 sentences:")
    for s in sentences[:5]:
        print(f"  [{s['id']:3d}] {s['text']}")


if __name__ == "__main__":
    main()
