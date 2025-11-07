# pages/Car_Flow_Map.py
# Car Flow — auto-play map 
# Shows NWB road segments colored by traffic_level for the
# current 3-minute frame, advances automatically on refresh.

import json, zipfile, time
from pathlib import Path
import pandas as pd
import streamlit as st
import pydeck as pdk

#check whether user is logged in. Only then the page is loaded - only activate upon final implementation
from security import check_login_status 
check_login_status()

# Streamlit page setup 
st.set_page_config(page_title="Car Flow — Map", page_icon="🗺️🚗", layout="wide")
st.title("Car Flow — Map")

# Auto-refresh every 3 minutes
# st_autorefresh returns a monotonically increasing counter.
# We'll use that counter to advance frames.
try:
    from streamlit_autorefresh import st_autorefresh
    TICK = st_autorefresh(interval=180_000, key="carflow_autorefresh")  # 180_000 ms = 3 min
except Exception:
    TICK = 0  # if the package isn't available, fall back to 0 (no auto-advance)

# Input data: flattened car-flow snapshot 
# Must contain columns: time_utc, id, traffic_level
DATA_PATH = Path("data/carflow_flat.csv.gz")

def _file_mtime(p: Path) -> float:
    """File modification time (used to invalidate cache only when file changes)."""
    try:
        return p.stat().st_mtime
    except Exception:
        return 0.0

@st.cache_data(ttl=0)
def load_carflow(path_str: str, mtime_key: float) -> pd.DataFrame:
    """
    Read a compact car-flow snapshot (CSV.GZ/Parquet) and:
      - parse time_utc to tz-aware datetimes,
      - create local time (Europe/Amsterdam),
      - group into 3-minute frames,
      - keep an id_str version for dict joins.
    Caching is keyed by file mtime so it only reloads when the file changes.
    """
    df = pd.read_csv(
        path_str,
        compression="infer",
        usecols=["time_utc", "id", "traffic_level"],
        dtype={"id": "Int64", "traffic_level": "float32"},
        parse_dates=["time_utc"],
    )
    df = df.dropna(subset=["time_utc", "id", "traffic_level"]).copy()
    df["time_local"] = df["time_utc"].dt.tz_convert("Europe/Amsterdam")
    df["frame_time"] = df["time_local"].dt.floor("3T")
    df["id_str"] = df["id"].astype("Int64").astype(str)
    return df

@st.cache_resource
def list_shps_in_zip(zip_path: str):
    """List all .shp members inside the given ZIP (no extraction)."""
    with zipfile.ZipFile(zip_path, "r") as z:
        return [n for n in z.namelist() if n.lower().endswith(".shp")]

@st.cache_resource
def read_shp_as_geojson(zip_path: str, shp_inside: str):
    """
    Read one shapefile member from the ZIP using GeoPandas, reproject to WGS84,
    and return as a GeoJSON-like dict + feature list + property keys list.
    """
    import geopandas as gpd
    g = gpd.read_file(f"zip://{zip_path}!{shp_inside}").to_crs(4326)
    gj = json.loads(g.to_json())
    feats = gj.get("features", [])
    prop_names = set()
    for f in feats[:1000]:
        prop_names.update((f.get("properties") or {}).keys())
    return gj, feats, sorted(prop_names)

def color_from_tl(tl):
    """Map traffic_level to RGBA (green→red)."""
    if pd.isna(tl): return [180, 180, 180, 80]
    if tl < 0.5:    return [46, 204, 113, 220]
    if tl < 0.7:    return [241, 196, 15, 220]
    if tl < 0.85:   return [230, 126, 34, 220]
    return [231, 76, 60, 220]

def detect_road_id_field(feats, id_candidates: set[str]) -> str:
    """
    Pick the NWB property name most likely to hold the TomTom segment ID by
    maximizing overlap with the set of IDs that have data in this frame.
    Falls back to common field names if overlap is zero.
    """
    counts = {}
    sample = feats[:5000] if len(feats) > 5000 else feats
    prop_names = set()
    for f in sample:
        prop_names.update((f.get("properties") or {}).keys())
    for name in prop_names:
        overlap = 0
        for f in sample:
            props = f.get("properties") or {}
            val = props.get(name)
            if val is None:
                continue
            try:
                s = str(int(val)) if isinstance(val, (int, float)) else str(val)
            except Exception:
                s = str(val)
            if s in id_candidates:
                overlap += 1
        counts[name] = overlap
    if counts:
        best = max(counts, key=counts.get)
        if counts[best] > 0:
            return best
    # common fallbacks
    for fb in ["WVK_ID", "WVKID", "wegvakid", "wegvak_id", "road_id", "ROAD_ID", "ID", "id"]:
        if any(fb in (f.get("properties") or {}) for f in sample):
            return fb
    # last resort: any property name
    return next(iter(prop_names)) if prop_names else "id"

# Guard: input files must exist / contain frames 
if not DATA_PATH.exists():
    st.error("data/carflow_flat.csv.gz not found.")
    st.stop()
mtime = _file_mtime(DATA_PATH)
cf = load_carflow(str(DATA_PATH), mtime)
if cf.empty:
    st.error("Car-flow file has no rows after parsing.")
    st.stop()
frames = sorted(cf["frame_time"].dropna().unique())
if not frames:
    st.error("No 3-minute frames found in car-flow data.")
    st.stop()

# Auto-play state (no slider) 
# frame_idx = which frame to show; last_tick = last seen refresh counter
if "frame_idx" not in st.session_state:
    st.session_state.frame_idx = 0
if "last_tick" not in st.session_state:
    st.session_state.last_tick = -1

# Safety clamp if frames list length changes
if st.session_state.frame_idx >= len(frames):
    st.session_state.frame_idx = 0

# Advance exactly when the refresh counter increases
if TICK > st.session_state.last_tick:
    st.session_state.frame_idx = (st.session_state.frame_idx + 1) % len(frames)
    st.session_state.last_tick = TICK

# Current frame to render
idx = st.session_state.frame_idx
current_frame = frames[idx]

# Aggregate traffic by segment for this frame 
snap = cf[cf["frame_time"] == current_frame].copy()
traffic_by_id = snap.groupby("id_str")["traffic_level"].mean().to_dict()
ids_with_data = set(traffic_by_id.keys())

# Read NWB shapefile (from ZIP) 
zip_path = "data/NWB_roads.zip"
if not Path(zip_path).exists():
    st.error(f"ZIP not found: {zip_path}")
    st.stop()
shp_names = list_shps_in_zip(zip_path)
if not shp_names:
    st.error("No .shp inside ZIP.")
    st.stop()

# Pick the first .shp inside the ZIP (simplest, no UI)
shp_inside = shp_names[0]

# Load shapefile geometry as GeoJSON-like dict
roads, feats, prop_fields = read_shp_as_geojson(zip_path, shp_inside)
if not feats:
    st.error("Road geometry has no features.")
    st.stop()

# Detect which NWB property holds the TomTom ID 
road_id_field = detect_road_id_field(feats, ids_with_data)

#  Build a filtered FeatureCollection with colors + width 
view_feats = []
for f in feats:
    props = f.get("properties") or {}
    raw_val = props.get(road_id_field)
    if raw_val is None:
        continue
    try:
        rid_str = str(int(raw_val)) if isinstance(raw_val, (int, float)) else str(raw_val)
    except Exception:
        rid_str = str(raw_val)

    # keep only segments that have data in this frame
    if rid_str not in ids_with_data:
        continue

    tl = float(traffic_by_id[rid_str])
    new_props = dict(props)
    new_props["rgba"] = color_from_tl(tl)  # color by traffic_level
    new_props["width"] = 3.0               # constant line width

    view_feats.append({
        "type": "Feature",
        "geometry": f.get("geometry"),
        "properties": new_props,
        "id": rid_str,                      # expose clean ID for tooltip
        "traffic_level": round(tl, 2),      # expose rounded TL for tooltip
    })

roads_view = {"type": "FeatureCollection", "features": view_feats}

# Map centering heuristic: first feature's first coordinate 
lat0, lon0 = 52.37, 4.90  # Amsterdam fallback
try:
    g0 = next((g for g in view_feats if g.get("geometry", {}).get("coordinates")), None)
    if g0:
        geom = g0["geometry"]
        if geom.get("type") == "LineString":
            lon0, lat0 = geom["coordinates"][0]
        elif geom.get("type") == "MultiLineString":
            lon0, lat0 = geom["coordinates"][0][0]
except Exception:
    pass  # keep fallback center

# PyDeck layer + deck 
layer = pdk.Layer(
    "GeoJsonLayer",
    roads_view,
    stroked=True,
    filled=False,
    get_line_color="properties.rgba",
    get_line_width="properties.width",
    pickable=True,
    auto_highlight=True,
)

deck = pdk.Deck(
    map_style=None,  # OSM default
    initial_view_state=pdk.ViewState(latitude=lat0, longitude=lon0, zoom=10),
    layers=[layer],
    tooltip={"html": "<b>ID:</b> {id}<br/><b>Traffic level:</b> {traffic_level}"},
)

#  Render map + footer 
st.pydeck_chart(deck, use_container_width=True)

st.caption(
    f"Auto-play (3-min) • Frame: {pd.Timestamp(current_frame).strftime('%Y-%m-%d %H:%M')} • "
    f"Roads rendered: {len(view_feats):,} • "
    f"Data range: {cf['time_local'].min():%Y-%m-%d %H:%M} → {cf['time_local'].max():%Y-%m-%d %H:%M}"
)