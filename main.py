import streamlit as st
from streamlit_folium import st_folium
import folium

st.set_page_config(
    page_title="Crowd Management Dashboard",
    layout="wide",
    page_icon="🗺️"
)

def main():
    st.title("SAIL Amsterdam Crowd Management Dashboard")

    st.sidebar.header("Filters")

    map_style = st.sidebar.selectbox(
        "Map Style",
        ["OpenStreetMap", "Stamen Terrain", "CartoDB positron"]
    )

    m = folium.Map(location=[52.3791, 4.9003], zoom_start=11, tiles=map_style)
    st_data = st_folium(m, width=700, height=500)

if __name__ == "__main__":
    main()
