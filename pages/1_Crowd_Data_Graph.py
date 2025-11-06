# pages/1_Crowd_Data_Line_Graph.py
import streamlit as st
import pandas as pd
import plotly.express as px
import time #to work with the time in the dataset
from streamlit_autorefresh import st_autorefresh #allows the auto refresh of the dashbaord

#import sys, os
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_loader import (init_data_stream, load_live_sensor_data, load_sensor_data)
from calculate_crowd_flow import add_new_row

#check whether user is logged in. Only then the page is loaded - only activate upon final implementation
#from security import check_login_status 
#check_login_status()

st.session_state.force_refresh_home = True

st.set_page_config(page_title="Crowd Data Line Graph", page_icon="📈", layout="wide")

st.title("Crowd Data Line Graph")


# Initializes count_frame if it doesn't exist yet
if "count_frame" not in st.session_state:
    # load data sets
    sensor_data = load_sensor_data()

    # Remove unwanted columns if they exist
    sensor_data = sensor_data.drop(columns=[col for col in ['level_0', 'index'] if col in sensor_data.columns])

    # Select the first row to initialize count_frame
    first_row = sensor_data.iloc[0]

    st.session_state.count_frame = pd.DataFrame([first_row], columns=sensor_data.columns)


REFRESH_INTERVAL = 180  # 180 seconds, this will be changed to milliseconds later in the code. As otherwise, this would have too many '0's'

# 1. Initialize session state on the first run
if "last_refresh" not in st.session_state:
    init_data_stream()
    st.session_state.last_refresh = 0.0
    st.session_state.sensor_data = {}
    st.session_state.current_timestamp = time.time()


# 2. Auto refresh  
st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="auto_refresher") #take time from refresh interval and convert to milliseconds

# Refresh data if the time interval has passed (3 minutes)
if time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
    sensor_data, timestamp = load_live_sensor_data()
    st.session_state.sensor_data = sensor_data
    st.session_state.current_timestamp = timestamp
    count_frame = add_new_row(st.session_state.current_timestamp)  # Updating crowd flow dataset for current timestamp
    st.session_state.count_frame = count_frame
    st.session_state.last_refresh = time.time()


# Load data
#sensor_data = load_sensor_data()
count_frame = st.session_state.count_frame
current_timestamp = st.session_state.current_timestamp


# converts dataset into longformat for plotly express
#count_frame = count_frame.reset_index()
sensor_data_long = count_frame.melt(
    id_vars=["timestamp", "hour", "minute", "day", "month", "weekday", "is_weekend"],
    var_name="sensor_id",
    value_name="flow_count"
)


# Sidebar controls
sensor_options = sensor_data_long["sensor_id"].unique()
selected_options = st.sidebar.multiselect("Select sensors to display",
                                          options = sensor_options,
                                          default = "CMSA-GAKH-01_0"
                                          )


# creates a dataset that only includes the selected sensors
filtered_sensors = sensor_data_long[sensor_data_long["sensor_id"].isin(selected_options)]


# Plot line graph
fig = px.line(filtered_sensors, x="timestamp", y="flow_count", color="sensor_id", title="Crowd Count")
fig.show()

fig.update_layout(xaxis_title="Time", yaxis_title="Crowd Count", legend_title="Sensor Names")

st.plotly_chart(fig, use_container_width=True)