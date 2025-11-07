import os
import pandas as pd
import numpy as np
import streamlit as st
import pydeck as pdk
from pathlib import Path

#check whether user is logged in. Only then the page is loaded - only activate upon final implementation
from security import check_login_status 
check_login_status()

st.session_state.force_refresh_home = True

st.set_page_config(page_title="Vessel Positions", page_icon="⛵", layout="wide")
st.title("Vessel Positions")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5_000, key="vessels_autorefresh_3min")
except Exception:
    pass

SRC_DEFAULT = "data/Vesselposition_data_20-24Aug2025.csv"
SRC_PATH = Path(os.getenv("VESSELS_SRC", SRC_DEFAULT)).expanduser()

def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except Exception:
        return 0.0

@st.cache_data(ttl=0)
def _sniff(path_str: str):
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
        low = {c.lower(): c for c in cols}
        for n in names:
            c = low.get(n.lower())
            if c:
                return c
        return None

    lon = pick(["lon","longitude","x","long","lng","lon_dd"])
    lat = pick(["lat","latitude","y","lat_dd"])
    tim = pick(["upload-timestamp","time","timestamp","datetime"])
    vid = pick(["id","identifier-sensor","identifier","mmsi","vessel_id"])
    spd = pick(["speed-in-centimeters-per-second","speed_cm_s","speed"])
    return delim, lon, lat, tim, vid, spd

#@st.cache_data(ttl=0)
def load_latest_positions(path_str: str, file_mtime_key: float, window_minutes: int = 15) -> pd.DataFrame:
    delim, lon_c, lat_c, t_c, id_c, spd_c = _sniff(path_str)
    if not all([lon_c, lat_c, t_c, id_c]):
        return pd.DataFrame(columns=["id_str","time_utc","lon","lat","speed_cm_s","time_ams"])

    # Pass 1: find latest timestamp present in the file
    max_utc = None
    for ch in pd.read_csv(
        path_str, sep=delim, usecols=[t_c], encoding="utf-8-sig",
        compression="infer", on_bad_lines="skip", engine="c", chunksize=400_000
    ):
        t = pd.to_datetime(ch[t_c], utc=True, errors="coerce")
        m = t.max()
        if pd.notna(m):
            max_utc = m if (max_utc is None or m > max_utc) else max_utc
    if max_utc is None:
        return pd.DataFrame(columns=["id_str","time_utc","lon","lat","speed_cm_s","time_ams"])

    cutoff = max_utc - pd.Timedelta(minutes=window_minutes)

    # Pass 2: keep rows within [cutoff, max_utc], then take the latest per vessel
    usecols = [t_c, lon_c, lat_c, id_c] + ([spd_c] if spd_c else [])
    parts = []
    rep = {",": ".", " ": ""}  # help with decimal commas/strays
    for ch in pd.read_csv(
        path_str, sep=delim, usecols=usecols, encoding="utf-8-sig",
        compression="infer", on_bad_lines="skip", engine="c", chunksize=400_000
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
    v = v.groupby("id_str", as_index=False).tail(1)  # one latest point per vessel
    v["time_ams"] = v["time_utc"].dt.tz_convert("Europe/Amsterdam")
    return v.reset_index(drop=True)

if not SRC_PATH.exists():
    st.error(f"File not found: {SRC_PATH}")
    st.stop()

v = load_latest_positions(str(SRC_PATH), _mtime(SRC_PATH), window_minutes=15)
if v.empty:
    st.warning("No rows in the last 15 minutes (based on latest timestamp in file).")
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
    "ID: " + v["id_str"].astype(str) +
    "<br/>Time: " + v["time_txt"] +
    "<br/>Lon: " + v["lon_txt"] +
    "<br/>Lat: " + v["lat_txt"] +
    "<br/>Speed: " + v["spd_txt"]
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
    f"Vessels: {len(v):,} • Latest file time (UTC): {v['time_utc'].max():%Y-%m-%d %H:%M:%S %Z} • "
    f"Auto-refresh: every 3 minutes • Window: last 15 minutes • Source: {SRC_PATH}"
)