import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import time
from datetime import timedelta
import plotly.graph_objects as go
from data_loader import load_live_sensor_data


#check whether user is logged in. Only then the page is loaded - only activate upon final implementation
#from security import check_login_status 
#check_login_status()

st.session_state.force_refresh_home = True

# # --- Functions ---



# # --- CONFIG ---
MODELS_DIR = 'TS_1_models_xgb'  # folder with joblib XGBoost models
DATA_FILE = 'data/crowd_weather_merged.csv'  # merged_df CSV
PAST_HOURS = 3 # lookback for feature creation
ROLL_STEPS = 10 # number of rolling prediction steps 
STEP_MINUTES = 3 #how far each step moves in minutes


# # --- LOAD DATA ---
df = pd.read_csv(DATA_FILE)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')
sensor_data, current_timestamp = load_live_sensor_data() 
sensor_cols = df.columns[0:-14]
feature_cols = df.columns[-14:]

st.write(f"Current timestamp: {current_timestamp}")

# Split dynamically: everything before `current_timestamp` is historic
historic_data = df[df.index < current_timestamp].copy()
current_data = df[df.index == current_timestamp].copy()

st.write(historic_data)
st.write(current_data)

# --- LOAD MODELS ---
scaler = joblib.load(f'{MODELS_DIR}/scaler.joblib')
models = {}
for sensor in sensor_cols:
    try:
        models[sensor] = joblib.load(f'{MODELS_DIR}/xgb_{sensor}.joblib')
    except:
        st.warning(f'Model for {sensor} not found.')

# --- Streamlit Interface ---
st.title("Crowd Prediction Dashboard")
selected_sensor = st.selectbox("Select sensor to visualize", sensor_cols)

# --- CURRENT INPUT ---
X_live = df.loc[[current_timestamp], feature_cols]
X_scaled = scaler.transform(X_live)

# --- ROLLING FORECAST ---
rolling_preds = []
last_features = X_live.copy()
last_time = current_timestamp

for step in range(ROLL_STEPS):
    step_preds = {}
    for sensor in sensor_cols:
        if sensor in models:
            model = models[sensor]
            step_preds[sensor] = model.predict(scaler.transform(last_features))[0]
        else:
            step_preds[sensor] = np.nan

    next_time = last_time + timedelta(minutes=STEP_MINUTES)
    rolling_preds.append({'timestamp': next_time, **step_preds})

    # Update for next step
    last_features = df.iloc[[-1]][feature_cols].copy()
    last_time = next_time

rolling_pred_df = pd.DataFrame(rolling_preds).set_index('timestamp')

# --- VISUALIZATION ---
fig = go.Figure()

# Historic data
fig.add_trace(go.Scatter(
    x=historic_data.index,
    y=historic_data[selected_sensor],
    mode='lines',
    name=f"{selected_sensor} (historic)",
    line=dict(color='blue')
))

# Current point
if not current_data.empty:
    fig.add_trace(go.Scatter(
        x=current_data.index,
        y=current_data[selected_sensor],
        mode='markers',
        name=f"{selected_sensor} (current)",
        marker=dict(color='orange', size=10)
    ))

# Rolling forecast
fig.add_trace(go.Scatter(
    x=rolling_pred_df.index,
    y=rolling_pred_df[selected_sensor],
    mode='lines+markers',
    name=f"{selected_sensor} (forecast)",
    line=dict(color='red', dash='dash')
))

fig.update_layout(
    title=f"Rolling Forecast for {selected_sensor}",
    xaxis_title="Time",
    yaxis_title="Crowd Count",
    legend_title="Legend",
    template="plotly_white",
    width=1200,
    height=600
)
st.plotly_chart(fig, use_container_width=True)

# --- DETAILS PANEL ---
with st.expander("🔍 Prediction Details"):
    st.dataframe(rolling_pred_df.tail(ROLL_STEPS))

st.caption(f"Forecast generated for {ROLL_STEPS * STEP_MINUTES} minutes ahead ({ROLL_STEPS} steps × {STEP_MINUTES} min).")



