import streamlit as st
import pandas as pd
import geopandas as gpd

@st.cache_data
def load_sensor_locations():
    """
    Loads and caches the static sensor location data from your file.
    """
    try:
        sensor_loc = pd.read_csv("data/sensor_location_cleaned.csv")
        sensor_loc[['Lat', 'Lon']] = sensor_loc['Lat/Long'].str.split(',', expand=True).astype(float)
        return sensor_loc
    except FileNotFoundError:
        st.error("Error: The file 'data/sensor_location_cleaned.csv' was not found.")
        st.stop()

@st.cache_data
def load_tram_metro_data():
    """
    Loads and caches the static tram and metro stop data.
    """
    try:
        url = "https://maps.amsterdam.nl/open_geodata/geojson_latlng.php?KAARTLAAG=TRAMMETRO_PUNTEN_2025&THEMA=trammetro"
        gdf = gpd.read_file(url)
        return gdf
    except Exception as e:
        st.warning(f"Could not load tram/metro data. Error: {e}")
        return gpd.GeoDataFrame()

def init_data_stream():
    """
    Initializes the live data feed by loading the full dataset.
    """
    if 'full_sensor_data' not in st.session_state:
        try:
            df = pd.read_csv('data/sensor_data.csv', 
                             index_col='timestamp', 
                             parse_dates=True)
            st.session_state.full_sensor_data = df
            st.session_state.data_index = 0
            print("Data stream initialized.")
        except FileNotFoundError:
            st.error("Error: The main data file 'data/SAIL2025...flow.csv' was not found.")
            st.stop()

# Load sensor locations

@st.cache_data

def load_sensor_data():

    sensor_data = pd.read_csv("data/sensor_data.csv")

    return sensor_data


def load_live_sensor_data():
    """
    Simulates a live feed by returning the NEXT row of data from the full dataset.
    """
    if 'full_sensor_data' not in st.session_state:
        init_data_stream()

    df = st.session_state.full_sensor_data
    index = st.session_state.data_index

    current_data_row = df.iloc[index]
    current_timestamp = df.index[index]

    sensor_data_dict = {col: [val] for col, val in current_data_row.items()}
    st.session_state.data_index = (st.session_state.data_index + 1) % len(df)

    return sensor_data_dict, current_timestamp