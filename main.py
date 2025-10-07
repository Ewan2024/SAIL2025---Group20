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
    sensor_loc = pd.read_csv("data/sensor_location_cleaned.csv")
    # Split Lat/Long into floats
    sensor_loc[['Lat', 'Lon']] = sensor_loc['Lat/Long'].str.split(',', expand=True).astype(float)
    return sensor_loc

sensor_loc = load_sensor_locations()

# --- Load sensor locations ---
@st.cache_data
def load_sensor_data():
    sensor_data = pd.read_csv("data/sensor_data.csv")
    return sensor_data

sensor_data = load_sensor_data()

# --- Main app function ---
def main():
    st.title("SAIL 2025 Crowd Monitoring Dashboard")

    # --- Sidebar Controls---
    map_style = st.sidebar.selectbox(
        "Map Style",
        [
            "OpenStreetMap",
            "CartoDB Positron",
            "CartoDB Dark_Matter",
            "Esri Satellite",
            "Google Satellite"
        ]
    )
    show_sensor_loc = st.sidebar.checkbox("Show Sensor Locations", value=True)
    show_sensor_id = st.sidebar.checkbox("Show Sensor ID", value = False )
    show_sensor_data = st.sidebar.checkbox("Show Sensor Data", value = True)

    # --- Initialize map ---
    m = folium.Map(
        location=[52.3791, 4.9003],  # Centered on Amsterdam
        zoom_start=13,
        tiles=None # disable default tiles so we can add custom layers
    )
    # --- Add selected tile layer ---
    if map_style == "Esri Satellite":
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="Esri Satellite",
            overlay=False,
            control=True
        ).add_to(m)
    elif map_style == "Google Satellite":
        folium.TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            attr="Google",
            name="Google Satellite",
            overlay=False,
            control=True
        ).add_to(m)
    else:
        # For OpenStreetMap or CartoDB styles
        folium.TileLayer(map_style).add_to(m)

    # --- Add sensor markers if toggled ---
    if show_sensor_loc:
        missing_rows = [] # List to store rows with missing data
        for idx, row in sensor_loc.iterrows():
            # check if any critical column is missing
            if row[['Lat', 'Lon','Locatienaam','Objectummer']].isnull().any():
                missing_rows.append(idx)
                continue # skip this row
            # add marker if no missing value
            folium.Marker(
                location=[row['Lat'], row['Lon']],
                popup=f"{row['Locatienaam']} ({row['Objectummer']})",
                tooltip=row['Locatienaam'],
                icon=folium.Icon(
                    color='red',         # Base color of the marker
                    icon='map-marker',   # Options: 'map-marker', 'map-marker-alt', or 'thumbtack'
                    prefix='fa'
                )
            ).add_to(m)
        # ---- Display missing rows info on Streamlit ---
        if missing_rows:
            st.warning(f"Skipped {len(missing_rows)} row(s) due to missing data: {missing_rows}")

    # Add permanent name labels if enabled
    if show_sensor_id:
        missing_rows = [] # List to store rows with missing data
        for idx, row in sensor_loc.iterrows():
            # check if any critical column is missing
            if row[['Lat', 'Lon','Locatienaam','Objectummer']].isnull().any():
                missing_rows.append(idx)
                continue # skip this row
            folium.map.Marker(
                [row['Lat'], row['Lon']],
                icon=folium.DivIcon(
                    html=f"""
                        <div style="
                            font-size: 12px;
                            color: white;
                            background-color: rgba(0, 0, 0, 0.8);
                            padding: 3px 6px;
                            border-radius: 4px;
                            display: inline-block;
                            white-space: nowrap;
                            text-align: center;">
                            {row['Objectummer']}
                        </div>
                    """
                )
            ).add_to(m)
         # ---- Display missing rows info on Streamlit ---
        if missing_rows:
            st.warning(f"Skipped {len(missing_rows)} row(s) due to missing data: {missing_rows}")

    if show_sensor_data:
        missing_rows = [] # List to store rows with missing data
        for i, row in sensor_loc.iterrows():
            # check if any critical column is missing
            if row[['Lat', 'Lon','Locatienaam','Objectummer']].isnull().any():
                missing_rows.append(i)
                continue # skip this row
            # Get crowd data from sensor_data
            sensor_id = row['sensor_id_full']
            sensor_count = sensor_data[sensor_id][0]
            # Map intensity to color and radius dynamically
            if sensor_count <= 20:
                color = '#00FF00'   # green (low)
            elif sensor_count <= 50:
                color = '#FFFF00'   # yellow (medium)
            elif sensor_count <= 80:
                color = '#FFA500'   # orange (high)
            else:
                color = '#FF0000'   # red (very high)

            radius = 2 + (sensor_count * 0.8) # scale radius to make differences visible

            # Add circle overlay
            folium.CircleMarker(
                location =[row['Lat'],row['Lon']],
                radius = radius,
                color=color,
                fill = True,
                fill_color = color,
                fill_opacity = 0.6,
                popup=f"""
                    <b>{row['Locatienaam']}<b><br>
                    Objectummer: {row['Objectummer']}<br>
                    Intensity: {sensor_count}
                """
            ).add_to(m)
         # ---- Display missing rows info on Streamlit ---
        if missing_rows:
            st.warning(f"Skipped {len(missing_rows)} row(s) due to missing data: {missing_rows}")

    # --- Display map ---
    st_data = st_folium(m, width=1000, height=600)

# --- Run the app ---
if __name__ == "__main__":
    main()
