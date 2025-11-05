import streamlit as st
import pandas as pd
from Vessels_and_Car_Flow import load_vessels

st.set_page_config(page_title="Vessel Positions", page_icon="⛵", layout="wide")
st.title("Vessel Positions")

@st.cache_data
def get_vessels():
    return load_vessels()

v = get_vessels()
if v.empty:
    st.error("No vessel data loaded. Check data_loader.py paths.")
else:
    cols = [c for c in ["time_utc","lon","lat","id","name","port-role","speed-in-centimeters-per-second"] if c in v.columns]
    st.dataframe(v[cols].head(50), use_container_width=True)
