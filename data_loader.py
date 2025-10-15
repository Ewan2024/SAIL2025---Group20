import pandas as pd
import geopandas as gpd
import streamlit as st

# Load sensor locations
@st.cache_data
def load_sensor_data():
    sensor_data = pd.read_csv("data/sensor_data.csv")
    return sensor_data

# Load sensor locations
@st.cache_data
def load_sensor_locations():
    sensor_loc = pd.read_csv("data/sensor_location_cleaned.csv")
    # Split Lat/Long into floats
    sensor_loc[['Lat', 'Lon']] = sensor_loc['Lat/Long'].str.split(',', expand=True).astype(float)
    return sensor_loc

def load_tram_metro_data():
    url = "https://maps.amsterdam.nl/open_geodata/geojson_latlng.php?KAARTLAAG=TRAMMETRO_PUNTEN_2025&THEMA=trammetro"
    gdf = gpd.read_file(url)
    return gdf
