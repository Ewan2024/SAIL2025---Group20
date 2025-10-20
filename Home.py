# Import necessary libraries
import streamlit as st
from streamlit_folium import st_folium
from data_loader import load_sensor_data, load_sensor_locations, load_tram_metro_data
from map_utils import init_map, add_sensor_markers, add_sensor_labels, add_sensor_circles, add_sensor_arrows, add_stops_circles, add_heatmap

#  Configure Streamlit page 
st.set_page_config(
    page_title="SAIL 2025 Crowd Monitoring Dashboard",
    layout="wide",
    page_icon="📍"
)

# Load Data 
sensor_loc = load_sensor_locations()
sensor_data = load_sensor_data()
tram_metro_stops_gpd = load_tram_metro_data()

# Initialize default session state (if not set yet)
default_settings = {
    "map_style": "OpenStreetMap",
    "show_sensor_arrows": True,
    "show_sensor_loc": True,
    "show_sensor_labels": False,
    "show_sensor_data": True,
    "show_tram_metro_stops": False,
    "show_heatmap": False
}
for key, value in default_settings.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Streamlit app
def main():
    st.title("SAIL 2025 Crowd Monitoring Dashboard")

    # Retrieve stored settings, if no stored settings, fallback to defaults
    map_style = st.session_state.get("map_style", "OpenStreetMap")

    # Sidebar Controls
    st.sidebar.title("Navigation")
    
     # Map style selector
    st.session_state.map_style = st.sidebar.selectbox(
        "Map Style",
        [
            "OpenStreetMap",
            "CartoDB Positron",
            "CartoDB Dark_Matter",
            "Esri Satellite",
            "Google Satellite"
        ],
        index=[
            "OpenStreetMap",
            "CartoDB Positron",
            "CartoDB Dark_Matter",
            "Esri Satellite",
            "Google Satellite"
        ].index(st.session_state.map_style)
    )
    # Checkboxes reflecting defaults
    st.session_state.show_sensor_arrows = st.sidebar.checkbox(
        "Show crowd direction", value=st.session_state.show_sensor_arrows
    )
    st.session_state.show_sensor_loc = st.sidebar.checkbox(
        "Show sensor location", value=st.session_state.show_sensor_loc
    )
    st.session_state.show_sensor_labels = st.sidebar.checkbox(
        "Show sensor ID", value=st.session_state.show_sensor_labels
    )
    st.session_state.show_sensor_data = st.sidebar.checkbox(
        "Show sensor data", value=st.session_state.show_sensor_data
    )
    st.session_state.show_tram_metro_stops = st.sidebar.checkbox(
        "Show Tram & Metro Stops", value =st.session_state.show_tram_metro_stops
    )
    st.session_state.show_heatmap = st.sidebar.checkbox(
        "Show heatmap", value =st.session_state.show_heatmap
    )

    # Initialize map 
    m = init_map(map_style)

    # Add map layers based on current settings 
    if st.session_state.show_sensor_loc:
        add_sensor_markers(m, sensor_loc)
    if st.session_state.show_sensor_labels:
        add_sensor_labels(m, sensor_loc)
    if st.session_state.show_sensor_data:
        add_sensor_circles(m, sensor_loc, sensor_data)
    if st.session_state.show_sensor_arrows:
        add_sensor_arrows(m, sensor_loc, sensor_data)
    if st.session_state.show_tram_metro_stops:
        add_stops_circles(m, tram_metro_stops_gpd)
    if st.session_state.show_heatmap:
        add_heatmap(m, sensor_loc, sensor_data)
    # Display map 
    st_data = st_folium(m, width=1000, height=600)

#  Run the app 
if __name__ == "__main__":
    main()
