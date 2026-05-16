#!/usr/bin/env bash
# Fetch A Scandal in Bohemia from Project Gutenberg and strip header/footer.
# Output: sib.txt

set -euo pipefail

URL_PRIMARY="https://www.gutenberg.org/cache/epub/1661/pg1661.txt"
URL_FALLBACK="https://raw.githubusercontent.com/anoopshrma/Chat-with-Docs/18ebd0a28133139bcc029fdf50fd769174081a67/SampleDocs/Sherlock_holmes.txt"
RAW="${1:-sib_raw.txt}"
OUT="${2:-sib.txt}"

curl -fsSL "$URL_PRIMARY" -o "$RAW" || curl -fsSL "$URL_FALLBACK" -o "$RAW"
echo "Downloaded $(wc -c < "$RAW") bytes"

python3 - "$RAW" "$OUT" << 'PY'
import pathlib
import re
import sys

raw = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")

start = raw.find("*** START OF")
if start != -1:
    raw = raw[raw.index("\n", start) + 1 :]

end = raw.find("*** END OF")
if end != -1:
    raw = raw[:end]

# Isolate chapter I only: "A Scandal in Bohemia".
scandal_marker = re.search(r"\nI\.\s+A SCANDAL IN BOHEMIA\s*\n", raw)
if scandal_marker:
    raw = raw[scandal_marker.end() :]

next_story = re.search(r"\nII\.\s+THE RED-HEADED LEAGUE\s*\n", raw)
if next_story:
    raw = raw[: next_story.start()]

text = re.sub(r"\n{3,}", "\n\n", raw).strip()
pathlib.Path(sys.argv[2]).write_text(text, encoding="utf-8")
print(f"Wrote {len(text)} chars, {len(text.split())} words to {sys.argv[2]}")
PY
