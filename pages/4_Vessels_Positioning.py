#Vessels_Positioning.py
import os, io
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import pydeck as pdk

# Page config 
st.set_page_config(page_title="Vessel Positions", page_icon="⛵", layout="wide")
st.title("Vessel Positions")

# Source CSV (env override allowed)
SRC_DEFAULT = "data/Vesselposition_data_20-24Aug2025.csv"
SRC_PATH = Path(os.getenv("VESSELS_SRC", SRC_DEFAULT)).expanduser()

# Rolling window for “current” snapshot
WINDOW_MINUTES = 15

# How much of the file tail to read first (fast path)
TAIL_MB = 25   # tweak if needed (e.g., 50)

# Start auto-refresh only after first successful render
try:
    from streamlit_autorefresh import st_autorefresh
    if st.session_state.get("autoplay_ready", False):
        st_autorefresh(interval=5_000, key="vessels_autorefresh_3min")
except Exception:
    pass

#  Utilities 
def _mtime(path: Path) -> float:
    """Safe file mtime for cache-busting when the CSV changes."""
    try:
        return path.stat().st_mtime
    except Exception:
        return 0.0

@st.cache_data(ttl=0)
def _sniff(path_str: str):
    """Read a tiny sample from the start to discover delimiter and column names."""
    sample = pd.read_csv(
        path_str, nrows=2000, engine="python", sep=None,
        on_bad_lines="skip", encoding="utf-8-sig", compression="infer"
    )
    delim = "," if sample.shape[1] > 1 else ";"
    cols = list(sample.columns)

    def pick(names):
        for n in names:
            if n in cols:
                return n
        lower = {c.lower(): c for c in cols}
        for n in names:
            c = lower.get(n.lower())
            if c:
                return c
        return None

    lon = pick(["lon","longitude","x","long","lng","lon_dd"])
    lat = pick(["lat","latitude","y","lat_dd"])
    tim = pick(["upload-timestamp","time","timestamp","datetime"])
    vid = pick(["id","identifier-sensor","identifier","mmsi","vessel_id"])
    spd = pick(["speed-in-centimeters-per-second","speed_cm_s","speed"])
    return delim, lon, lat, tim, vid, spd

def _tail_bytes(path: Path, max_mb: int) -> io.StringIO:
    """Read only the last max_mb of a text file and return as a StringIO buffer."""
    max_bytes = max_mb * 1_000_000
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        start = max(end - max_bytes, 0)
        f.seek(start)
        chunk = f.read()
    # If we started mid-line, drop the first partial line
    if start > 0:
        try:
            chunk = chunk.split(b"\n", 1)[1]
        except Exception:
            pass
    return io.StringIO(chunk.decode("utf-8", errors="ignore"))

#  Loader (fast tail + fallback) 
@st.cache_data(ttl=0)
def load_latest_positions(path_str: str, file_mtime_key: float,
                          window_minutes: int = WINDOW_MINUTES,
                          tail_mb: int = TAIL_MB) -> pd.DataFrame:
    """
    Fast path: read only the tail of the file to find the newest time and rows in the window.
    Fallback: if tail doesn't cover the window, scan the whole file (chunked).
    """
    delim, lon_c, lat_c, t_c, id_c, spd_c = _sniff(path_str)
    if not all([lon_c, lat_c, t_c, id_c]):
        return pd.DataFrame(columns=["id_str","time_utc","lon","lat","speed_cm_s","time_ams"])

    rep = {",": ".", " ": ""}  # help with decimal commas/strays
    usecols = [t_c, lon_c, lat_c, id_c] + ([spd_c] if spd_c else [])

    #  FAST PATH: tail-only 
    tail_buf = _tail_bytes(Path(path_str), tail_mb)
    # Pass A: newest timestamp in tail
    try:
        t_tail = pd.read_csv(tail_buf, sep=delim, usecols=[t_c], encoding="utf-8-sig")
        max_utc_tail = pd.to_datetime(t_tail[t_c], utc=True, errors="coerce").max()
    except Exception:
        max_utc_tail = None

    if pd.notna(max_utc_tail):
        cutoff = max_utc_tail - pd.Timedelta(minutes=window_minutes)
        # Rewind tail and parse only rows within the window
        tail_buf2 = _tail_bytes(Path(path_str), tail_mb)
        parts = []
        for ch in pd.read_csv(
            tail_buf2, sep=delim, usecols=usecols, encoding="utf-8-sig",
            on_bad_lines="skip", engine="c", chunksize=150_000
        ):
            t = pd.to_datetime(ch[t_c], utc=True, errors="coerce")
            m = (t >= cutoff) & (t <= max_utc_tail)
            if not m.any():
                continue
            lon = pd.to_numeric(ch.loc[m, lon_c].astype(str).replace(rep, regex=True), errors="coerce")
            lat = pd.to_numeric(ch.loc[m, lat_c].astype(str).replace(rep, regex=True), errors="coerce")
            vid = ch.loc[m, id_c].astype(str)
            out = pd.DataFrame({"id_str": vid, "time_utc": t.loc[m], "lon": lon, "lat": lat})
            out["speed_cm_s"] = pd.to_numeric(ch.loc[m, spd_c], errors="coerce") if spd_c else np.nan
            parts.append(out.dropna(subset=["id_str","time_utc","lon","lat"]))

        if parts:
            v = pd.concat(parts, ignore_index=True).sort_values(["id_str","time_utc"])
            v = v.groupby("id_str", as_index=False).tail(1)
            v["time_ams"] = v["time_utc"].dt.tz_convert("Europe/Amsterdam")
            return v.reset_index(drop=True)

    #  FALLBACK: full scan (chunked) 
    parts = []
    max_utc = None
    # Pass 1: newest timestamp from full file (time column only)
    for ch in pd.read_csv(
        path_str, sep=delim, usecols=[t_c], encoding="utf-8-sig",
        compression="infer", on_bad_lines="skip", engine="c", chunksize=300_000
    ):
        t = pd.to_datetime(ch[t_c], utc=True, errors="coerce")
        m = t.max()
        if pd.notna(m):
            max_utc = m if (max_utc is None or m > max_utc) else max_utc
    if max_utc is None:
        return pd.DataFrame(columns=["id_str","time_utc","lon","lat","speed_cm_s","time_ams"])

    cutoff = max_utc - pd.Timedelta(minutes=window_minutes)
    # Pass 2: filter rows in the window, keep latest per vessel
    for ch in pd.read_csv(
        path_str, sep=delim, usecols=usecols, encoding="utf-8-sig",
        compression="infer", on_bad_lines="skip", engine="c", chunksize=300_000
    ):
        t = pd.to_datetime(ch[t_c], utc=True, errors="coerce")
        m = (t >= cutoff) & (t <= max_utc)
        if not m.any():
            continue
        lon = pd.to_numeric(ch.loc[m, lon_c].astype(str).replace(rep, regex=True), errors="coerce")
        lat = pd.to_numeric(ch.loc[m, lat_c].astype(str).replace(rep, regex=True), errors="coerce")
        vid = ch.loc[m, id_c].astype(str)
        out = pd.DataFrame({"id_str": vid, "time_utc": t.loc[m], "lon": lon, "lat": lat})
        out["speed_cm_s"] = pd.to_numeric(ch.loc[m, spd_c], errors="coerce") if spd_c else np.nan
        parts.append(out.dropna(subset=["id_str","time_utc","lon","lat"]))

    if not parts:
        return pd.DataFrame(columns=["id_str","time_utc","lon","lat","speed_cm_s","time_ams"])

    v = pd.concat(parts, ignore_index=True).sort_values(["id_str","time_utc"])
    v = v.groupby("id_str", as_index=False).tail(1)
    v["time_ams"] = v["time_utc"].dt.tz_convert("Europe/Amsterdam")
    return v.reset_index(drop=True)

# Page body 
if not SRC_PATH.exists():
    st.error(f"File not found: {SRC_PATH}")
    st.stop()

with st.spinner("Loading latest vessel positions…"):
    v = load_latest_positions(str(SRC_PATH), _mtime(SRC_PATH), window_minutes=WINDOW_MINUTES, tail_mb=TAIL_MB)

if v.empty:
    st.warning(f"No rows in the last {WINDOW_MINUTES} minutes (based on newest timestamp).")
    st.stop()

# Optional highlighting
ids = v["id_str"].unique().tolist()
sel = st.sidebar.multiselect("Highlight vessel IDs (optional)", options=sorted(ids))

# Tooltip text
v["time_txt"] = v["time_ams"].dt.strftime("%Y-%m-%d %H:%M:%S")
v["lon_txt"]  = v["lon"].map(lambda x: f"{x:.5f}")
v["lat_txt"]  = v["lat"].map(lambda x: f"{x:.5f}")
v["spd_txt"]  = np.where(v["speed_cm_s"].notna(), (v["speed_cm_s"]/100.0).map(lambda x: f"{x:.2f} m/s"), "n/a")
v["tooltip"]  = (
    "ID: " + v["id_str"].astype(str)
    + "<br/>Time: " + v["time_txt"]
    + "<br/>Lon: " + v["lon_txt"]
    + "<br/>Lat: " + v["lat_txt"]
    + "<br/>Speed: " + v["spd_txt"]
)

# Colors: highlighted red, others blue
is_sel = v["id_str"].isin(sel)
v["r"] = np.where(is_sel, 255, 30).astype(int)
v["g"] = np.where(is_sel,   0,144).astype(int)
v["b"] = np.where(is_sel,   0,255).astype(int)
v["a"] = np.where(is_sel, 220,180).astype(int)

data_for_map = v.rename(columns={"lon":"longitude","lat":"latitude"})
lat0 = float(data_for_map["latitude"].median())
lon0 = float(data_for_map["longitude"].median())

layer = pdk.Layer(
    "ScatterplotLayer",
    data=data_for_map,
    get_position=["longitude","latitude"],
    get_radius=28,
    filled=True,
    pickable=True,
    opacity=0.85,
    get_fill_color="[r, g, b, a]",
)

deck = pdk.Deck(
    map_style=None,
    initial_view_state=pdk.ViewState(latitude=lat0, longitude=lon0, zoom=12),
    layers=[layer],
    tooltip={"html": "{tooltip}"},
)
st.pydeck_chart(deck, use_container_width=True)

st.caption(
    f"Vessels: {len(v):,} • File time (UTC): {v['time_utc'].max():%Y-%m-%d %H:%M:%S %Z} • "
    f"Auto-update: every 3 minutes • Window: last {WINDOW_MINUTES} minutes • "
    f"Source: {SRC_PATH}"
)

# Enable auto-refresh after first successful render, then rerun once to start the loop
if not st.session_state.get("autoplay_ready", False):
    st.session_state.autoplay_ready = True
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass