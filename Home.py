import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import time #to work with the time in the dataset
from streamlit_autorefresh import st_autorefresh #allows the auto refresh of the dashbaord
from streamlit_js_eval import streamlit_js_eval
from data_loader import (load_live_sensor_data, load_sensor_locations, load_tram_metro_data, init_data_stream)
from map_utils import (init_map, add_sensor_markers, add_sensor_labels, add_sensor_circles, add_flow_sensor_circles, add_sensor_arrows, add_stops_circles, add_heatmap)
from calculate_crowd_flow import calculate_crowd_flow

#Import function used for login - only activate upon final implementation
#from pages.C_User_Authentification import load_user_data
#from pages.C_User_Authentification import save_user_data
#from pages.C_User_Authentification import hash_passwords
#from pages.C_User_Authentification import authenticate_user
#from pages.C_User_Authentification import login_page


st.set_page_config(
    page_title="SAIL 2025 Crowd Monitoring Dashboard",
    layout="wide",
    page_icon="📍"
)

REFRESH_INTERVAL = 5  # 180 seconds, this will be changed to milliseconds later in the code. As otherwise, this would have too many '0's'

# 1. Initialize session state on the first run
if "last_refresh" not in st.session_state:
    init_data_stream()
    st.session_state.last_refresh = 0.0
    st.session_state.sensor_data = {}
    st.session_state.current_timestamp = time.time()
    st.session_state.map_center = [52.37, 4.89] # Amsterdam, this is for the first time loading the map.
    st.session_state.map_zoom = 13 # Default zoom when loading the map for the first time

# Add authentication session state initialization - only activate upon full implementation
#if 'logged_in' not in st.session_state:
    #st.session_state['logged_in'] = False
#if 'username' not in st.session_state:
    #st.session_state['username'] = None

def main():
    if "scroll_position" in st.session_state:
        streamlit_js_eval(f"window.scrollTo(0, {st.session_state.scroll_position});")

    # 2. Auto refresh  
    st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="auto_refresher") #take time from refresh interval and convert to milliseconds

    # Refresh data if the time interval has passed (3 minutes)
    if time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
        sensor_data, timestamp = load_live_sensor_data()
        st.session_state.sensor_data = sensor_data
        st.session_state.current_timestamp = timestamp
        st.session_state.last_refresh = time.time()

    # Load data from session state for display
    sensor_loc = load_sensor_locations()
    tram_metro_stops_gpd = load_tram_metro_data()
    sensor_data = st.session_state.sensor_data
    current_timestamp = st.session_state.current_timestamp
    crowd_flow = calculate_crowd_flow(st.session_state.current_timestamp)  # Updating crowd flow dataset for current timestamp
    alt_sensor_data = {col: [val] for col, val in crowd_flow.loc[st.session_state.current_timestamp].items()} # Turning data frame into dictionary format


    # toggle between data sets
    # Initialize toggle state
    if "use_alt_data" not in st.session_state:
        st.session_state.use_alt_data = False

    # Sidebar toggle button
    if st.sidebar.button("Toggle Dataset"):
        st.session_state.use_alt_data = not st.session_state.use_alt_data

    # Use the appropriate dataset
    if st.session_state.use_alt_data:
        alt_sensor_data = {k: v for k, v in sensor_data.items() if v[0] is not None and not pd.isna(v[0])}
        st.sidebar.info("Showing **Crowd Flow**")
        display_sensor_data = alt_sensor_data
    else:
        st.sidebar.info("Showing **Crowd Count**")
        display_sensor_data = sensor_data


    # Sidebar and Map
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

    # Create the map using the center and zoom from session state - this allows for the zoom to stay at the same level and not go back to a fixed level after a refresh
    m = init_map(
        map_style=st.session_state.map_style,
        center=st.session_state.map_center,
        zoom=st.session_state.map_zoom
    )

    #if st.session_state.show_sensor_data: add_sensor_circles(m, sensor_loc, sensor_data)

    if st.session_state.show_sensor_data:
        if st.session_state.use_alt_data:
            add_flow_sensor_circles(m, sensor_loc, display_sensor_data)
        else:
            add_sensor_circles(m, sensor_loc, display_sensor_data)

    if st.session_state.show_sensor_arrows: add_sensor_arrows(m, sensor_loc, sensor_data)
    if st.session_state.show_heatmap: add_heatmap(m, sensor_loc, sensor_data)
    if st.session_state.show_sensor_loc: add_sensor_markers(m, sensor_loc)
    if st.session_state.show_sensor_labels: add_sensor_labels(m, sensor_loc)
    if st.session_state.show_tram_metro_stops: add_stops_circles(m, tram_metro_stops_gpd)

    map_output = st_folium(m, width=1200, height=700, key="folium_map")

    if map_output and map_output.get("center") and map_output.get("zoom"):
        st.session_state.map_center = map_output["center"]
        st.session_state.map_zoom = map_output["zoom"]

    time_left = REFRESH_INTERVAL - (time.time() - st.session_state.last_refresh) 
    display_time = current_timestamp if hasattr(current_timestamp, 'strftime') else st.session_state.current_timestamp
    st.header(f"Showing Data for: {display_time.strftime('%Y-%m-%d %H:%M:%S')}") #tells you what time the data is being shown
    st.caption(f"Next automatic data refresh in {int(max(0, time_left))} seconds.") #in how long the bashboard will refresh - this updates whenn you click on the page. Could not make this happen automatically

    st.session_state.scroll_position = streamlit_js_eval("return window.scrollY", key="get_scroll_position")

if __name__ == "__main__":
    main()
    
    #Below is the code that adds the login functionality as a landing page - only activate upon final implementation
    #if st.session_state['logged_in']:
        # Forward user to main dashboard (main()) if logged in 
        #st.sidebar.button("Logout", on_click=lambda: st.session_state.update(logged_in=False, username=None))
        #main()
    #else:
        # Forward user to Login/ Signup page if not logged in
        #st.set_page_config(page_title="Login Page", layout="wide", initial_sidebar_state="collapsed")
        #login_page()