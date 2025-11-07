import folium
import pandas as pd
import streamlit as st
import folium.plugins
from folium.plugins import HeatMap


def init_map(map_style, center, zoom):
    """Initializes the map with a given center, zoom, and style."""

    if isinstance(center, dict): 
        location = [center['lat'], center['lng']]
    else:
        location = center

    m = folium.Map(
        location=location, 
        zoom_start=zoom,
        tiles=None,
        control_scale=True
    )
    #Add selected tile layer
    if map_style == "Esri Satellite":
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri", name="Esri Satellite", overlay=False, control=True
        ).add_to(m)
    elif map_style == "Google Satellite":
        folium.TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            attr="Google", name="Google Satellite", overlay=False, control=True
        ).add_to(m)
    else:
        folium.TileLayer(map_style).add_to(m)
    
    return m

# Add sensor markers if turned on
def add_sensor_markers(m, sensor_loc):      
    missing_rows = [] # List to store rows with missing data
    for idx, row in sensor_loc.iterrows():
        # check if any critical column is missing
        if row[['Lat', 'Lon','Locatienaam','Objectummer']].isnull().any():
            missing_rows.append(idx)
            continue 
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
    return missing_rows #to announce to user if there is data

# Add sensor labels
def add_sensor_labels(m, sensor_loc):
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
    return missing_rows

# Add sensor circles for crowd flow
def add_flow_sensor_circles(m, sensor_loc, sensor_data):
    missing_rows = [] # List to store rows with missing data
    for i, row in sensor_loc.iterrows():
        # check if any critical column is missing
        if row[['Lat', 'Lon','Locatienaam','Objectummer']].isnull().any():
            missing_rows.append(i)
            continue # skip this row
        # Get crowd data from sensor_data
        sensor_id = row['sensor_id_full']
        sensor_count = sensor_data[sensor_id][0]
        #sensor_count = sensor_data.get(sensor_id, [None])[0]
        #if sensor_count is None or pd.isna(sensor_count):
            #continue
        # Map intensity to color and radius dynamically
        if sensor_count <= 1:
            color = '#00FF00'   # green (low)
        elif sensor_count <= 6:
            color = '#FFFF00'   # yellow (medium)
        elif sensor_count <= 12:
            color = '#FFA500'   # orange (high)
        else:
            color = '#FF0000'   # red (very high)

        radius = 2 + (sensor_count * 1) # scale radius to make differences visible

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
        #Display missing rows info on Streamlit
    return missing_rows
    #if missing_rows:
        #st.warning(f"Skipped {len(missing_rows)} row(s) due to missing data: {missing_rows}")

# Add sensor circles 
def add_sensor_circles(m, sensor_loc, sensor_data):
    missing_rows = [] # List to store rows with missing data
    for i, row in sensor_loc.iterrows():
        # check if any critical column is missing
        if row[['Lat', 'Lon','Locatienaam','Objectummer']].isnull().any():
            missing_rows.append(i)
            continue # skip this row
        # Get crowd data from sensor_data
        sensor_id = row['sensor_id_full']
        sensor_count = sensor_data[sensor_id][0]
        #sensor_count = sensor_data.get(sensor_id, [None])[0]
        #if sensor_count is None or pd.isna(sensor_count):
            #continue
        # Map intensity to color and radius dynamically
        if sensor_count <= 50:
            color = "#05FA05"   # green (low)
        elif sensor_count <= 100:
            color = '#FFFF00'   # yellow (medium)
        elif sensor_count <= 150:
            color = '#FFA500'   # orange (high)
        else:
            color = '#FF0000'   # red (very high)

        radius = 2 + (sensor_count * 0.2) # scale radius to make differences visible

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
        #Display missing rows info on Streamlit
    return missing_rows

def add_sensor_arrows(m, sensor_loc, sensor_data):
    missing_rows = []

    for i, row in sensor_loc.iterrows():
        # Skip if any critical value is missing
        if row[['Lat', 'Lon', 'Locatienaam', 'Objectummer', 'sensor_direction']].isnull().any():
            missing_rows.append(i)
            continue

        lat = row['Lat']
        lon = row['Lon']
        direction = row['sensor_direction']
        sensor_id = row['sensor_id_full']

        # Get crowd count from sensor_data
        count = sensor_data.get(sensor_id, [0])[0]

        # Define color based on count
        if count <= 20:
            color = '#00FF00'  # green
        elif count <= 50:
            color = '#FFFF00'  # yellow
        elif count <= 80:
            color = '#FFA500'  # orange
        else:
            color = '#FF0000'  # red

        # Add arrow marker using direction
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f"""
                    <div style="
                        font-size: 24px;
                        transform: rotate({direction}deg);
                        color: {color};
                        font-weight: bold;
                    ">→</div>
                """
            ),
            popup=folium.Popup(f"""
                <b>{row['Locatienaam']}</b><br>
                Objectummer: {row['Objectummer']}<br>
                Intensity: {count}<br>
                Direction: {direction}°
            """, max_width=300)
        ).add_to(m)

    # Warning for skipped rows
    return missing_rows

def add_flow_sensor_arrows(m, sensor_loc, sensor_data):
    missing_rows = []

    for i, row in sensor_loc.iterrows():
        # Skip if any critical value is missing
        if row[['Lat', 'Lon', 'Locatienaam', 'Objectummer', 'sensor_direction']].isnull().any():
            missing_rows.append(i)
            continue

        lat = row['Lat']
        lon = row['Lon']
        direction = row['sensor_direction']
        sensor_id = row['sensor_id_full']

        # Get crowd count from sensor_data
        count = sensor_data.get(sensor_id, [0])[0]

        # Define color based on count
        if count <= 1:
            color = '#00FF00'  # green
        elif count <= 5:
            color = '#FFFF00'  # yellow
        elif count <= 10:
            color = '#FFA500'  # orange
        else:
            color = '#FF0000'  # red

        # Add arrow marker using direction
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f"""
                    <div style="
                        font-size: 24px;
                        transform: rotate({direction}deg);
                        color: {color};
                        font-weight: bold;
                    ">→</div>
                """
            ),
            popup=folium.Popup(f"""
                <b>{row['Locatienaam']}</b><br>
                Objectummer: {row['Objectummer']}<br>
                Intensity: {count}<br>
                Direction: {direction}°
            """, max_width=300)
        ).add_to(m)

    # Warning for skipped rows
    return missing_rows

def add_stops_circles(m, tram_metro_gdf):
    tram_metro_stop_group = folium.FeatureGroup(name="Tram/Metro Stops", show=True)
    for _, row in tram_metro_gdf.iterrows():
        lon, lat = row.geometry.coords[0]  # geometry is Point(lat, lon)
        popup_text = f"<b>{row['Naam']}</b><br>Type: {row['Modaliteit']}<br>Lijnen: {row['Lijn']}"
        folium.CircleMarker(
            location=[lon, lat],
            radius=5,
            color="blue" if row["Modaliteit"] == "Tram" else "red",
            fill=True,
            fill_opacity=0.8,
            popup=popup_text
        ).add_to(tram_metro_stop_group)
    tram_metro_stop_group.add_to(m)

def add_heatmap(m, sensor_loc, sensor_data):
    heat_data = []
    missing_rows = []  
    for i, row in sensor_loc.iterrows():
        if row[['Lat', 'Lon', 'Locatienaam', 'Objectummer']].isnull().any():
            missing_rows.append(i)
            continue 

        sensor_id = row['sensor_id_full']
        sensor_count = sensor_data.get(sensor_id, [0])[0] 

        if sensor_count > 0:
            heat_data.append([float(row['Lat']), float(row['Lon']), float(sensor_count)])

    if heat_data:
        HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(m)

    return missing_rows