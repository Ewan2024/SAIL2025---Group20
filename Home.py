import streamlit as st
from streamlit_folium import st_folium
import time

from data_loader import (load_live_sensor_data, load_sensor_locations, load_tram_metro_data, init_data_stream)
from map_utils import (init_map, add_sensor_markers, add_sensor_labels, add_sensor_circles, add_sensor_arrows, add_stops_circles, add_heatmap)

st.set_page_config(
    page_title="SAIL 2025 Crowd Monitoring Dashboard",
    layout="wide",
    page_icon="📍"
)
REFRESH_INTERVAL = 180  

if 'last_refresh' not in st.session_state:
    print("First run: Initializing session state...")
    init_data_stream()
    st.session_state.last_refresh = 0.0
    sensor_data, timestamp = load_live_sensor_data()
    st.session_state.sensor_data = sensor_data
    st.session_state.current_timestamp = timestamp
    st.session_state.last_refresh = time.time()

def main():
    if time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
        print(f"Timer elapsed. Refreshing data at {time.strftime('%X')}")
        sensor_data, timestamp = load_live_sensor_data()
        st.session_state.sensor_data = sensor_data
        st.session_state.current_timestamp = timestamp
        st.session_state.last_refresh = time.time()
        st.rerun()

    sensor_loc = load_sensor_locations()  
    tram_metro_stops_gpd = load_tram_metro_data() 
    sensor_data = st.session_state.sensor_data
    current_timestamp = st.session_state.current_timestamp

    st.title("SAIL 2025 Crowd Monitoring Dashboard")
    
    time_left = REFRESH_INTERVAL - (time.time() - st.session_state.last_refresh)
    st.header(f"Showing Data for: {current_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption(f"Next data refresh in {int(max(0, time_left))} seconds. (Updates on interaction)")

    st.sidebar.title("Map Options")
    st.session_state.map_style = st.sidebar.selectbox("Map Style", 
        ["OpenStreetMap", "CartoDB Positron", "CartoDB Dark_Matter"], 
        index=["OpenStreetMap", "CartoDB Positron", "CartoDB Dark_Matter"].index(st.session_state.get("map_style", "CartoDB Positron")))
    
    st.sidebar.subheader("Layer Toggles")
    st.session_state.show_sensor_data = st.sidebar.checkbox("Show Sensor Data (Circles)", value=st.session_state.get("show_sensor_data", True))
    st.session_state.show_sensor_arrows = st.sidebar.checkbox("Show Crowd Direction", value=st.session_state.get("show_sensor_arrows", True))
    st.session_state.show_heatmap = st.sidebar.checkbox("Show Heatmap", value=st.session_state.get("show_heatmap", True))
    st.session_state.show_sensor_loc = st.sidebar.checkbox("Show Sensor Markers", value=st.session_state.get("show_sensor_loc", False))
    st.session_state.show_sensor_labels = st.sidebar.checkbox("Show Sensor IDs", value=st.session_state.get("show_sensor_labels", False))
    st.session_state.show_tram_metro_stops = st.sidebar.checkbox("Show Tram & Metro Stops", value=st.session_state.get("show_tram_metro_stops", False))

    m = init_map(st.session_state.map_style)
    
    if st.session_state.show_sensor_data: add_sensor_circles(m, sensor_loc, sensor_data)
    if st.session_state.show_sensor_arrows: add_sensor_arrows(m, sensor_loc, sensor_data)
    if st.session_state.show_heatmap: add_heatmap(m, sensor_loc, sensor_data)
    if st.session_state.show_sensor_loc: add_sensor_markers(m, sensor_loc)
    if st.session_state.show_sensor_labels: add_sensor_labels(m, sensor_loc)
    if st.session_state.show_tram_metro_stops: add_stops_circles(m, tram_metro_stops_gpd)
    
    st_folium(m, width=1200, height=700, key=str(current_timestamp))

if __name__ == "__main__":
    main()