# --- Import necessary libraries ---
import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd

# --- Configure Streamlit page ---
st.set_page_config(
    page_title="SAIL 2025 Crowd Monitoring Dashboard",
    layout="wide",
    page_icon="📍"
)

# --- Load sensor locations ---
@st.cache_data
def load_sensor_locations():
    sensor_loc = pd.read_csv("data/sensor_location.csv")
    # Split Lat/Long into floats
    sensor_loc[['Lat', 'Lon']] = sensor_loc['Lat/Long'].str.split(',', expand=True).astype(float)
    return sensor_loc

sensor_loc = load_sensor_locations()

# --- Main app function ---
def main():
    st.title("SAIL 2025 Crowd Monitoring Dashboard")

    # --- Sidebar ---
    map_style = st.sidebar.selectbox(
        "Map Style",
        ["OpenStreetMap"]
    )
    show_sensor_loc = st.sidebar.checkbox("Show Sensor Locations", value=True)

    # --- Initialize map ---
    m = folium.Map(
        location=[52.3791, 4.9003],  # Centered on Amsterdam
        zoom_start=13,
        tiles=map_style
    )

    # --- Add sensor markers if toggled ---
    if show_sensor_loc:
        for idx, row in sensor_loc.iterrows():
            folium.Marker(
                location=[row['Lat'], row['Lon']],
                popup=f"{row['Locatienaam']} ({row['Objectummer']})",
                icon=folium.Icon(color='blue', icon='camera', prefix='fa')
            ).add_to(m)

    # --- Display map ---
    st_data = st_folium(m, width=1000, height=600)

# --- Run the app ---
if __name__ == "__main__":
    main()
