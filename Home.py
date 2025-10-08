# Import necessary libraries
import streamlit as st
from streamlit_folium import st_folium
from data_loader import load_sensor_data, load_sensor_locations
from map_utils import init_map, add_sensor_markers, add_sensor_labels, add_sensor_circles

#  Configure Streamlit page 
st.set_page_config(
    page_title="SAIL 2025 Crowd Monitoring Dashboard",
    layout="wide",
    page_icon="📍"
)

# Load Data 
sensor_loc = load_sensor_locations()
sensor_data = load_sensor_data()

# Streamlit app
def main():
    st.title("SAIL 2025 Crowd Monitoring Dashboard")

    # Sidebar Controls
    st.sidebar.title("Navigation")
    
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
    show_sensor_labels = st.sidebar.checkbox("Show Sensor ID", value = False )
    show_sensor_data = st.sidebar.checkbox("Show Sensor Data", value = True)

    

    # Initialize map 
    m = init_map(map_style)

    # Add sensor markers if toggled 
    if show_sensor_loc:
        add_sensor_markers(m, sensor_loc)
    # Add permanent name labels if enabled
    if show_sensor_labels:
        add_sensor_labels(m, sensor_loc)
    # Add sensor data circles if enabled
    if show_sensor_data:
        add_sensor_circles(m, sensor_loc, sensor_data)
    
    # Display map 
    st_data = st_folium(m, width=1000, height=600)

# --- Run the app ---
if __name__ == "__main__":
    main()
