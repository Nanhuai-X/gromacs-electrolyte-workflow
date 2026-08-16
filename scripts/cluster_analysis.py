#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from collections import defaultdict
from common import dump_json

class UF:
    def __init__(self):
        self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        if self.p[x] != x:
            self.p[x] = self.find(self.p[x])
        return self.p[x]
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--edges", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    uf = UF()
    with open(args.edges, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            uf.union(row["a"], row["b"])
    groups = defaultdict(list)
    for node in uf.p:
        groups[uf.find(node)].append(node)
    sizes = sorted((len(v) for v in groups.values()), reverse=True)
    result = {"status": "PASS", "cluster_sizes": sizes, "cluster_count": len(sizes),
              "max_size": max(sizes, default=0), "definition": "connected components of declared contact graph"}
    dump_json(result, args.out)
    print("PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
