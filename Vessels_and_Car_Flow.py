from pathlib import Path
import os
import sys
import csv
from io import StringIO
import pandas as pd

__all__ = ["load_vessels", "load_carflow_flat"]

VESSELS_SRC  = os.getenv("VESSELS_SRC",  "data/Vesselposition_data_20-24Aug2025.csv")
CARFLOW_SRC  = os.getenv("CARFLOW_SRC",  "data/TomTom_data_20-24Aug2025.csv")

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


def _maybe_rd_to_lonlat(df: pd.DataFrame) -> pd.DataFrame:
  
    cols = {c.lower(): c for c in df.columns}
    if "lon" in cols and "lat" in cols:
        return df

    if "position-x" in cols and "position-y" in cols:
        try:
            from pyproj import Transformer  
            x = pd.to_numeric(df[cols["position-x"]], errors="coerce")
            y = pd.to_numeric(df[cols["position-y"]], errors="coerce")
            m = x.notna() & y.notna()
            if m.any():
                lon, lat = Transformer.from_crs(28992, 4326, always_xy=True).transform(
                    x[m].to_numpy(), y[m].to_numpy()
                )
                out = df.loc[m].copy()
                out["lon"], out["lat"] = lon, lat
                return out
        except Exception:
          
            pass
    return df

def load_vessels(src: str = VESSELS_SRC) -> pd.DataFrame:
    p = Path(src).expanduser()
    df = pd.read_csv(p if p.exists() else src, engine="python", sep=None,
                     encoding="utf-8-sig", on_bad_lines="skip", compression="infer")

    df = _maybe_rd_to_lonlat(df)

  
    lon = next((c for c in df.columns if c.lower() in {"lon","longitude","x","long","lng","lon_dd"}), None)
    lat = next((c for c in df.columns if c.lower() in {"lat","latitude","y","lat_dd"}), None)
    if lon is None or lat is None:
        raise ValueError("Vessels file must contain lon/lat (or convertible position-x/position-y) columns.")

    df["lon"] = pd.to_numeric(df[lon].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    df["lat"] = pd.to_numeric(df[lat].astype(str).str.replace(",", ".", regex=False), errors="coerce")


    tcol = next((c for c in df.columns if any(k in c.lower() for k in
                 ["time_utc","upload-timestamp","time","timestamp","datetime"])), None)
    if tcol:
        df["time_utc"] = _parse_time_iso8601_utc(df[tcol])

    return df.dropna(subset=["lon","lat"]).reset_index(drop=True)


def _csv_field_unlimited():
    lim = sys.maxsize
    while True:
        try:
            csv.field_size_limit(lim); break
        except OverflowError:
            lim //= 10

def _pack(rows):
    df = pd.DataFrame(rows, columns=["time_raw","id","traffic_level"])
    t = _parse_time_iso8601_utc(df["time_raw"])
    df = df.assign(
        time_utc=t,
        id=pd.to_numeric(df["id"], errors="coerce"),
        traffic_level=pd.to_numeric(df["traffic_level"], errors="coerce"),
    ).dropna(subset=["time_utc","id","traffic_level"])
    return df[["time_utc","id","traffic_level"]]

def _carflow_flat_iter(path: str, batch_rows: int = 250_000):
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
            t, inner = row[t_idx], row[d_idx]
            if not inner:
                continue
         
            inner_io = StringIO(inner)
            ir = csv.reader(inner_io, delimiter=",", quotechar='"')
            hdr = next(ir, None)
            
            if not hdr:
                txt = inner.replace("\n", "")
                parts = [p.strip() for p in (txt.split(",") if "," in txt else txt.split(";"))]
                if len(parts) == 2:
                    buf.append((t, parts[0], parts[1]))
                if len(buf) >= batch_rows:
                    yield _pack(buf); buf = []
                continue
          
            if len(hdr) == 1 and ";" in hdr[0]:
                inner_io = StringIO(inner)
                ir = csv.reader(inner_io, delimiter=";", quotechar='"')
                hdr = next(ir, None)
            hdr = [h.strip().lower() for h in hdr]
            if "id" in hdr and "traffic_level" in hdr:
                id_i, tl_i = hdr.index("id"), hdr.index("traffic_level")
                for r in ir:
                    if len(r) <= max(id_i, tl_i):
                        continue
                    buf.append((t, r[id_i], r[tl_i]))
                    if len(buf) >= batch_rows:
                        yield _pack(buf); buf = []
            else:
                
                if len(hdr) == 2:
                    buf.append((t, hdr[0], hdr[1]))
                    if len(buf) >= batch_rows:
                        yield _pack(buf); buf = []
                for r in ir:
                    if len(r) >= 2:
                        buf.append((t, r[0], r[1]))
                        if len(buf) >= batch_rows:
                            yield _pack(buf); buf = []
        if buf:
            yield _pack(buf)

def load_carflow_flat(src: str | None = None) -> pd.DataFrame:
    
    if src is None:
        p_flat = Path(CARFLOW_FLAT).expanduser()
        if p_flat.exists():
            return pd.read_parquet(p_flat) if p_flat.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(p_flat, compression="infer")
        src = CARFLOW_SRC

    p = Path(src).expanduser()
    if p.exists():
        if p.suffix.lower() in {".parquet", ".pq"}:
            return pd.read_parquet(p)
        if p.suffix.lower() == ".gz":
            return pd.read_csv(p, compression="infer")
       
        chunks = list(_carflow_flat_iter(str(p)))
        return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["time_utc","id","traffic_level"])
    else:
  
        df = pd.read_csv(src, engine="python", sep=None, on_bad_lines="skip", encoding="utf-8-sig", compression="infer")
        if {"time_utc","id","traffic_level"}.issubset(df.columns):
            return df
        raise ValueError("Car Flow source is not flat and not local; flatten locally first or provide a flat URL.")