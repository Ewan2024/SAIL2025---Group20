# Vessels_and_Car_Flow.py
# --- Minimal utilities to FLATTEN TomTom car-flow CSV into carflow_flat.parquet / carflow_flat.csv.gz ---

from pathlib import Path
import os, sys, csv
from io import StringIO
import pandas as pd

#  Paths / defaults 
ROOT = Path(__file__).resolve().parent
CARFLOW_SRC   = os.getenv("CARFLOW_SRC",  str(ROOT / "data" / "TomTom_data_20-24Aug2025.csv"))
OUT_PARQUET   = os.getenv("CARFLOW_FLAT", str(ROOT / "data" / "carflow_flat.parquet"))
OUT_CSV_GZ    = os.getenv("CARFLOW_FLAT_CSVGZ", str(ROOT / "data" / "carflow_flat.csv.gz"))

# Time parser (robust to subsecond + timezone variants) 
def _parse_time_iso8601_utc(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, utc=True, errors="coerce")
    s = s.astype("string").str.strip()
    t = pd.to_datetime(s, format="%Y-%m-%dT%H:%M:%S.%f%z", utc=True, errors="coerce")
    m = t.isna()
    if m.any():
        t.loc[m] = pd.to_datetime(s[m], format="%Y-%m-%dT%H:%M:%S%z", utc=True, errors="coerce")
    m = t.isna()
    if m.any():
        t.loc[m] = pd.to_datetime(s[m], utc=True, errors="coerce")
    return t

# Allow very large CSV fields (the inner "data" column can be huge) 
def _csv_field_unlimited():
    lim = sys.maxsize
    while True:
        try:
            csv.field_size_limit(lim)
            break
        except OverflowError:
            lim //= 10

# Convert buffered (time_raw, id, traffic_level) rows into a clean DataFrame 
def _pack_carflow(rows):
    df = pd.DataFrame(rows, columns=["time_raw", "id", "traffic_level"])
    t = _parse_time_iso8601_utc(df["time_raw"])
    df = (
        df.assign(
            time_utc=t,
            id=pd.to_numeric(df["id"], errors="coerce"),
            traffic_level=pd.to_numeric(df["traffic_level"], errors="coerce"),
        )
        .dropna(subset=["time_utc", "id", "traffic_level"])
        .loc[:, ["time_utc", "id", "traffic_level"]]
    )
    return df

# Stream-flatten the TomTom CSV:
# Each outer row has TIME and a nested CSV string in DATA. Handle both
# comma- and semicolon-delimited inner formats; handle labeled ("id,traffic_level")
# and unlabeled two-column inner schemas. Yields tidy DataFrames in batches. 
def carflow_flat_iter(path: str, batch_rows: int = 250_000):
    _csv_field_unlimited()
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        outer = csv.reader(f, delimiter=",", quotechar='"')
        header = next(outer)
        cols = {h.strip().lower(): i for i, h in enumerate(header)}
        t_idx, d_idx = cols.get("time"), cols.get("data")
        if t_idx is None or d_idx is None:
            raise ValueError(f"Expected 'time' and 'data' in header, got: {header}")

        buf = []
        for row in outer:
            if not row or len(row) <= d_idx:
                continue
            t = row[t_idx]
            inner = row[d_idx]
            if not inner:
                continue

            # Try inner CSV with commas first
            inner_io = StringIO(inner)
            ir = csv.reader(inner_io, delimiter=",", quotechar='"')
            hdr = next(ir, None)

            # If header came as "id;traffic_level" in one token, switch to semicolons
            if hdr and len(hdr) == 1 and ";" in hdr[0]:
                inner_io = StringIO(inner)
                ir = csv.reader(inner_io, delimiter=";", quotechar='"')
                hdr = next(ir, None)

            # If there's no header at all, attempt a simple "id,traffic_level" split
            if not hdr:
                txt = inner.replace("\n", "")
                parts = [p.strip() for p in (txt.split(",") if "," in txt else txt.split(";"))]
                if len(parts) == 2:
                    buf.append((t, parts[0], parts[1]))
                if len(buf) >= batch_rows:
                    yield _pack_carflow(buf); buf = []
                continue

            # Normalize header names
            hdr = [h.strip().lower() for h in hdr]

            # Labeled case: columns include "id" and "traffic_level"
            if "id" in hdr and "traffic_level" in hdr:
                id_i, tl_i = hdr.index("id"), hdr.index("traffic_level")
                for r in ir:
                    if len(r) <= max(id_i, tl_i):
                        continue
                    buf.append((t, r[id_i], r[tl_i]))
                    if len(buf) >= batch_rows:
                        yield _pack_carflow(buf); buf = []
            else:
                # Unlabeled two-column pairs: (id, traffic_level)
                if len(hdr) == 2:
                    buf.append((t, hdr[0], hdr[1]))
                    if len(buf) >= batch_rows:
                        yield _pack_carflow(buf); buf = []
                for r in ir:
                    if len(r) >= 2:
                        buf.append((t, r[0], r[1]))
                        if len(buf) >= batch_rows:
                            yield _pack_carflow(buf); buf = []

        # Flush remainder
        if buf:
            yield _pack_carflow(buf)

# Writer: Parquet (fast & compact) 
def write_carflow_parquet(src: str = CARFLOW_SRC, out_parquet: str = OUT_PARQUET, batch_rows: int = 500_000):
    """
    Stream-flatten src into a Parquet file at out_parquet (Snappy compression).
    Requires pyarrow. Creates parent directories if needed.
    """
    import pyarrow as pa, pyarrow.parquet as pq  # import here so module doesn't hard-depend on pyarrow
    out = Path(out_parquet)
    out.parent.mkdir(parents=True, exist_ok=True)

    writer = None
    total = 0
    for chunk in carflow_flat_iter(src, batch_rows=batch_rows):
        table = pa.Table.from_pandas(chunk, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(str(out), table.schema, compression="snappy")
        writer.write_table(table)
        total += len(chunk)
        print(f"[parquet] rows written: {total:,}", flush=True)
    if writer:
        writer.close()
    print(f"[parquet] done → {out} ({total:,} rows)")

# Writer: CSV.GZ (portable fallback)
def write_carflow_csv_gz(src: str = CARFLOW_SRC, out_csv_gz: str = OUT_CSV_GZ, batch_rows: int = 500_000):
    """
    Stream-flatten src into a gzipped CSV at out_csv_gz.
    Always available. slower/larger than Parquet but very portable.
    """
    out = Path(out_csv_gz)
    out.parent.mkdir(parents=True, exist_ok=True)

    first = True
    total = 0
    for chunk in carflow_flat_iter(src, batch_rows=batch_rows):
        chunk.to_csv(out, index=False, mode=("w" if first else "a"),
                     header=first, compression="gzip")
        first = False
        total += len(chunk)
        print(f"[csv.gz] rows written: {total:,}", flush=True)
    print(f"[csv.gz] done → {out} ({total:,} rows)")

# Convenience: write both (Parquet if possible, plus CSV.GZ)
def write_carflow_both(src: str = CARFLOW_SRC,
                       out_parquet: str = OUT_PARQUET,
                       out_csv_gz: str = OUT_CSV_GZ,
                       batch_rows: int = 500_000):
    """
    Try to write Parquet first (if pyarrow present), then also write CSV.GZ.
    """
    try:
        write_carflow_parquet(src=src, out_parquet=out_parquet, batch_rows=batch_rows)
    except Exception as e:
        print(f"[parquet] skipped ({e}); continuing with CSV.GZ …", flush=True)
    write_carflow_csv_gz(src=src, out_csv_gz=out_csv_gz, batch_rows=batch_rows)

# ---------- CLI: run this file to build outputs ----------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Flatten TomTom car-flow CSV to Parquet/CSV.GZ.")
    ap.add_argument("--src", default=CARFLOW_SRC, help="Path to raw TomTom CSV (with nested 'data' column).")
    ap.add_argument("--parquet", default=OUT_PARQUET, help="Output Parquet path.")
    ap.add_argument("--csvgz", default=OUT_CSV_GZ, help="Output CSV.GZ path.")
    ap.add_argument("--rows", type=int, default=500_000, help="Batch size for streaming writes.")
    ap.add_argument("--mode", choices=["parquet", "csv", "both"], default="both",
                    help="Which outputs to produce.")
    args = ap.parse_args()

    if args.mode == "parquet":
        write_carflow_parquet(src=args.src, out_parquet=args.parquet, batch_rows=args.rows)
    elif args.mode == "csv":
        write_carflow_csv_gz(src=args.src, out_csv_gz=args.csvgz, batch_rows=args.rows)
    else:
        write_carflow_both(src=args.src, out_parquet=args.parquet, out_csv_gz=args.csvgz, batch_rows=args.rows)