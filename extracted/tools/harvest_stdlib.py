# -*- coding: utf-8 -*-
"""A free, offline, high-quality corpus of REAL Python and technical English: the source code of Python's own standard library (idiomatic Python, with
English docstrings and comments), from the Python installed on THIS machine (PSF license: use is allowed). Output: documents separated by a form feed,
ready for tools/prepare_corpus.py.
  python tools/harvest_stdlib.py --out raw/stdlib.txt            (add --site to also read installed packages' sources: check their licenses first)
Tests and tutorials folders are skipped (they are huge and repetitive)."""
import argparse, os, sys, sysconfig

SKIP = {"__pycache__", "test", "tests", "idlelib", "lib2to3", "turtledemo", "ensurepip", "site-packages", "dist-packages", "config-3"}

def harvest(roots, out, max_files=0):
    n = size = 0
    with open(out, "w", encoding="utf-8") as f:
        for root in roots:
            for r, ds, fs in os.walk(root):
                ds[:] = sorted(d for d in ds if d not in SKIP or (root != sysconfig.get_paths()["stdlib"] and d in {"site-packages", "dist-packages"}))
                for fn in sorted(fs):
                    if not fn.endswith(".py"): continue
                    try: t = open(os.path.join(r, fn), encoding="utf-8").read()
                    except Exception: continue
                    if 200 <= len(t) <= 200_000:
                        f.write(t + "\f"); n += 1; size += len(t)
                        if max_files and n >= max_files: return n, size
    return n, size

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--site", action="store_true"); ap.add_argument("--max-files", type=int, default=0); a = ap.parse_args()
    roots = [sysconfig.get_paths()["stdlib"]] + ([sysconfig.get_paths()["purelib"]] if a.site else [])
    n, size = harvest(roots, a.out, a.max_files); print(f"{a.out}: {n} files, {size / 1e6:.1f} MB from {roots}")
