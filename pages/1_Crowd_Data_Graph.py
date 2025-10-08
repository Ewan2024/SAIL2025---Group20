# pages/1_Crowd_Data_Line_Graph.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from data_loader import load_sensor_data

st.set_page_config(page_title="Crowd Data Line Graph", page_icon="📈", layout="wide")

st.title("Crowd Data Line Graph")

# Load data
sensor_data = load_sensor_data()

# Sidebar controls

# Filter data

# Plot line graph
fig, ax = plt.subplots(figsize=(10, 4))

st.pyplot(fig)