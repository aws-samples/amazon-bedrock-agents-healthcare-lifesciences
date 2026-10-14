"""Download EPFL Clinical Guidelines dataset and save as individual text files for S3 upload."""

import os
import re
from datasets import load_dataset

OUTPUT_DIR = "guidelines-data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading dataset...")
ds = load_dataset("epfl-llm/guidelines")
train = ds["train"]
print(f"Total guidelines: {len(train)}")

saved = 0
for i, row in enumerate(train):
    text = row.get("clean_text", "") or row.get("raw_text", "")
    if not text or len(text) < 100:
        continue

    source = row.get("source", "unknown")
    title = row.get("title", "") or f"guideline-{i}"
    overview = row.get("overview", "") or ""

    # Build document with metadata header
    doc = f"Source: {source}\nTitle: {title}\n"
    if overview:
        doc += f"Overview: {overview}\n"
    doc += f"\n{text}"

    # Short filename — keeps S3 key metadata under 2048 bytes
    filename = f"{source}_{i}.txt"

    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write(doc)
    saved += 1

    if saved % 5000 == 0:
        print(f"  Saved {saved}...")

print(f"\nDone. Saved {saved} guidelines to {OUTPUT_DIR}/")
