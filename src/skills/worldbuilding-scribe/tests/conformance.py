#!/usr/bin/env python3
"""Conformance: canon-folder statuses vs the director's recorded decisions.

Usage: python3 conformance.py <world-folder> <decisions.json>

decisions.json:
{ "batches": [ { "n": 1,
                 "approved": ["entities/x", ...],   # incl. approve-with-edit
                 "deferred": ["ideas/y", ...],
                 "rejected": ["relations/z", ...] } ] }
Checks: approved -> status: canon; deferred -> status: draft;
rejected -> file absent. Exit code 1 on any failure.
"""
import json, sys, glob, os
import yaml

world, decisions = sys.argv[1], sys.argv[2]
arts = {}
for f in glob.glob(os.path.join(world, "**", "*.md"), recursive=True):
    try:
        fm = yaml.safe_load(open(f, encoding="utf-8").read().split("---")[1])
    except Exception:
        continue
    if isinstance(fm, dict) and "id" in fm:
        arts[fm["id"]] = fm.get("status")

fails = []
dec = json.load(open(decisions, encoding="utf-8"))
for b in dec.get("batches", []):
    n = b.get("n", "?")
    for i in b.get("approved", []):
        if arts.get(i) != "canon":
            fails.append(f"batch {n}: {i} approved but status={arts.get(i, 'MISSING')}")
    for i in b.get("deferred", []):
        if arts.get(i) != "draft":
            fails.append(f"batch {n}: {i} deferred but status={arts.get(i, 'MISSING')}")
    for i in b.get("rejected", []):
        if i in arts:
            fails.append(f"batch {n}: {i} rejected but present (status={arts[i]})")

print(f"artifacts: {len(arts)}")
print("conformance: clean" if not fails else "CONFORMANCE FAILURES:")
for x in fails:
    print("  " + x)
sys.exit(1 if fails else 0)
