import streamlit as st
import time

#check whether user is logged in. Only then the page is loaded - only activate upon final implementation
#from security import check_login_status 
#check_login_status()

st.session_state.force_refresh_home = True

# Configure streamlit page
st.set_page_config(
    page_title = "Settings - SAIL 2025 Dashboard",
    layout = "centered",
    page_icon = "⚙️"
)

st.title("Map Settings")

st.write("Update Default Map Settings")

# Initialize default settings if missing 
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

# Form for settings 
with st.form("settings_form"):
    st.subheader("Map Appearance")
    map_style = st.selectbox(
        "Choose Map Style",
        [
            "OpenStreetMap",
            "CartoDB Positron",
            "CartoDB Dark_Matter",
            "Esri Satellite",
            "Google Satellite"
        ], index = ["OpenStreetMap",
                     "CartoDB Positron",
                     "CartoDB Dark_Matter",
                     "Esri Satellite",
                     "Google Satellite"].index(st.session_state.map_style)
    )

    st.subheader("Data Layers")
    show_sensor_arrows = st.checkbox("Show crowd direction (arrows)", st.session_state.show_sensor_arrows)
    show_sensor_loc = st.checkbox("Show sensor locations (markers)", st.session_state.show_sensor_loc)
    show_sensor_labels = st.checkbox("Show sensor IDs (labels)", st.session_state.show_sensor_labels)
    show_sensor_data = st.checkbox("Show sensor data (circles)", st.session_state.show_sensor_data)
    show_tram_metro_stops = st.checkbox("Show Tram & Metro Stops (circles)", st.session_state.show_tram_metro_stops)
    show_heatmap = st.checkbox("Show heatmap", st.session_state.show_heatmap)

    submitted = st.form_submit_button("Save Settings")

    if submitted:
        st.session_state.map_style = map_style
        st.session_state.show_sensor_arrows = show_sensor_arrows
        st.session_state.show_sensor_loc = show_sensor_loc
        st.session_state.show_sensor_labels = show_sensor_labels
        st.session_state.show_sensor_data = show_sensor_data
        st.session_state.show_tram_metro_stops = show_tram_metro_stops
        st.session_state.show_heatmap = show_heatmap

        st.success("Settings saved successfully! Go back to the Home page to view changes.")