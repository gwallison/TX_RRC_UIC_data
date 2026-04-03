"""
Peek at the first N lines of uif700a.txt.gz to understand the actual record structure.
Prints each line with its length, the first 80 chars, and the record type code at pos 1-2.
"""
import gzip

DATA_FILE = "uif700a.txt.gz"
N_LINES = 30

record_types = {}

with gzip.open(DATA_FILE, "rt", encoding="ascii", errors="replace") as f:
    for i, line in enumerate(f):
        if i >= N_LINES:
            break
        raw = line.rstrip("\n")
        rec_type = raw[0:2] if len(raw) >= 2 else "??"
        record_types[rec_type] = record_types.get(rec_type, 0) + 1
        print(f"Line {i+1:3d} | len={len(raw):4d} | type={rec_type!r} | {raw[:80]!r}")

print()
print("--- Record type counts in first", N_LINES, "lines ---")
for rt, count in sorted(record_types.items()):
    print(f"  type {rt!r}: {count} records")
