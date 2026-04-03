"""
Survey the full file: count record types and show sample records for each type.
"""
import gzip
from collections import Counter

DATA_FILE = "uif700a.txt.gz"
SAMPLE_COUNT = 3  # how many sample lines to show per type

type_counts = Counter()
type_samples = {}  # type -> list of sample lines

print("Scanning file... (this may take a minute)")

with gzip.open(DATA_FILE, "rt", encoding="ascii", errors="replace") as f:
    for i, line in enumerate(f):
        raw = line.rstrip("\n")
        rec_type = raw[0:2] if len(raw) >= 2 else "??"
        type_counts[rec_type] += 1
        if rec_type not in type_samples:
            type_samples[rec_type] = []
        if len(type_samples[rec_type]) < SAMPLE_COUNT:
            type_samples[rec_type].append((i + 1, len(raw), raw))

        if i % 500_000 == 0 and i > 0:
            print(f"  ...processed {i:,} lines so far")

print(f"\nTotal lines: {sum(type_counts.values()):,}\n")
print("=" * 70)
print(f"{'Record Type':12s} {'Count':>12s}")
print("=" * 70)
for rt, count in sorted(type_counts.items()):
    print(f"  {rt!r:10s} {count:>12,}")

print()
print("=" * 70)
print("Sample records per type (first few characters shown)")
print("=" * 70)
for rt in sorted(type_samples.keys()):
    print(f"\n--- Record Type {rt!r} ---")
    for line_no, length, raw in type_samples[rt]:
        # Show first 120 chars, then last 20 chars if record is longer
        if length > 140:
            preview = raw[:120] + " ... " + raw[-20:]
        else:
            preview = raw
        print(f"  Line {line_no:,} | len={length:4d} | {preview!r}")
