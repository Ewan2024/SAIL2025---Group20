import csv, sys
from io import StringIO
from pathlib import Path
import pandas as pd

RAW = "data/TomTom_data_20-24Aug2025.csv"
OUT = Path("data/carflow_flat.csv.gz")

def field_limit():
    lim = sys.maxsize
    while True:
        try:
            csv.field_size_limit(lim); break
        except OverflowError: lim //= 10

def pack(rows):
    df = pd.DataFrame(rows, columns=["time_utc","id","traffic_level"])
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True, errors="coerce")
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df["traffic_level"] = pd.to_numeric(df["traffic_level"], errors="coerce")
    return df.dropna(subset=["time_utc","id","traffic_level"])

def iter_flat(path, batch=200_000):
    field_limit()
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        outer = csv.reader(f, delimiter=",", quotechar='"')
        header = next(outer)
        cols = {h.strip().lower(): i for i, h in enumerate(header)}
        t_idx, d_idx = cols.get("time"), cols.get("data")
        if t_idx is None or d_idx is None:
            raise ValueError(f"Expected 'time' and 'data' columns, got: {header}")
        buf = []
        for row in outer:
            if not row or len(row) <= d_idx: continue
            t, inner = row[t_idx], row[d_idx]
            if not inner: continue
            inner_io = StringIO(inner)
            ir = csv.reader(inner_io, delimiter=",", quotechar='"')
            hdr = next(ir, None)
            if hdr and len(hdr) == 1 and ";" in hdr[0]:
                inner_io = StringIO(inner); ir = csv.reader(inner_io, delimiter=";", quotechar='"')
                hdr = next(ir, None)
            if not hdr:
                parts = [p.strip() for p in inner.split(",")]
                if len(parts) == 2: buf.append((t, parts[0], parts[1]))
                if len(buf) >= batch: yield pack(buf); buf = []
                continue
            hdr = [h.strip().lower() for h in hdr]
            if "id" in hdr and "traffic_level" in hdr:
                id_i, tl_i = hdr.index("id"), hdr.index("traffic_level")
                for r in ir:
                    if len(r) <= max(id_i, tl_i): continue
                    buf.append((t, r[id_i], r[tl_i]))
                    if len(buf) >= batch: yield pack(buf); buf = []
            else:
                for r in ir:
                    if len(r) >= 2:
                        buf.append((t, r[0], r[1]))
                        if len(buf) >= batch: yield pack(buf); buf = []
        if buf: yield pack(buf)

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wrote = False
    for chunk in iter_flat(RAW):
        mode = "ab" if OUT.exists() and wrote else "wb"
        chunk.to_csv(OUT, mode=mode, index=False, header=not wrote, compression="gzip")
        wrote = True
    print(f"Done → {OUT}")

if __name__ == "__main__":
    main()