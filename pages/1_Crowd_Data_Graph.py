# pages/1_Crowd_Data_Line_Graph.py
import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_sensor_data

st.set_page_config(page_title="Crowd Data Line Graph", page_icon="📈", layout="wide")

st.title("Crowd Data Line Graph")

# Load data
sensor_data = load_sensor_data()


# converts dataset into longformat for plotly express
sensor_data_long = sensor_data.melt(
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
fig = px.line(filtered_sensors, x="timestamp", y="flow_count", color="sensor_id", title="Crowd Flow")
fig.show()

st.plotly_chart(fig)