import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import time
from datetime import timedelta
import plotly.graph_objects as go
from data_loader import load_live_sensor_data

OUT_DIR = '/Users/sheikharfahmi/Desktop/TIL_Python_Programming/SAIL2025---Group20/models_xgb'
os.makedirs(OUT_DIR, exist_ok=True)
MODELS_DIR = 'models_xgb'  # folder with joblib XGBoost models
DATA_FILE = 'data/crowd_weather_merged.csv'  # your merged_df CSV
PAST_HOURS = 1          # number of past hours to use as input
PREDICT_HORIZON = 1     # predict 1 hour ahead
STEP_HOURS = 1          # move window by 1 hour each sample

# --- Functions ---

def build_hourly_windows(df_hourly, sensor_cols, weather_cols, past_hours=1, predict_horizon=1):
    df = df_hourly.sort_values('timestamp').reset_index(drop=True)
    X_list = []
    y_list = []
    time_list = []

    n = len(df) #120 hours
    # earliest valid idx for t_end is past_hours -1, target index is t_end + predict_horizon
    for t_end in range(past_hours - 1, n - predict_horizon, STEP_HOURS):
        t_target = t_end + predict_horizon

        # Past window sensors: shape (past_hours, n_sensors)
        past_window = df.loc[t_end - (past_hours - 1): t_end, sensor_cols].fillna(0)
        # Flatten by hour-major order
        past_flat = past_window.values.flatten(order='C')  # length = past_hours * n_sensors

        # Aggregated summaries across the window (mean, std)
        past_mean = past_window.mean().values
        past_std = past_window.std().fillna(0).values

        # Weather at t_end (hourly) and optionally weather history can be added
        weather_t = df.loc[t_end, weather_cols].fillna(0).values if len(weather_cols) > 0 else np.array([])

        # Time features for t_end
        ts = df.loc[t_end, 'timestamp']
        hour = pd.to_datetime(ts).hour
        dow = pd.to_datetime(ts).dayofweek
        is_weekend = int(dow >= 5)
        time_sin = np.sin(2 * np.pi * hour / 24.0)
        time_cos = np.cos(2 * np.pi * hour / 24.0)

        time_feats = np.array([hour, dow, is_weekend, time_sin, time_cos])

        # Compose feature vector
        feat = np.concatenate([past_flat, past_mean, past_std, weather_t, time_feats])
        X_list.append(feat)

        # Target: sensor values at t_target
        y_list.append(df.loc[t_target, sensor_cols].values)
        time_list.append(df.loc[t_target, 'timestamp'])

    X = np.vstack(X_list)
    y = np.vstack(y_list)
    times = np.array(time_list)
    return X, y, times

def make_live_features(historic_df, current_df, sensor_cols, weather_cols, past_hours, scaler):
    df_combined = pd.concat([historic_df, current_df]).sort_values('timestamp')
    X_live, _, times_live = build_hourly_windows(
        df_combined, sensor_cols, weather_cols, past_hours=past_hours, predict_horizon=1
    )
    X_live_latest = X_live[-1].reshape(1, -1)
    return scaler.transform(X_live_latest), times_live[-1]


# --- LOAD DATA ---
df = pd.read_csv(DATA_FILE, parse_dates=['timestamp'])
df = df.sort_values('timestamp')
sensor_data, current_timestamp = load_live_sensor_data() 
# Split dynamically: everything before `current_timestamp` is historic
historic_data = df[df['timestamp'] < current_timestamp].copy()
current_data = sensor_data
sensor_cols = [col for col in df.columns[1:-15]]
weather_cols = [c for c in df.columns if 
                c in ['temperature','precipitation','wind_speed',
                      'wind_gust','pressure','humidity','dew_point']]

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
sensor_to_plot = st.selectbox("Select sensor to visualize", sensor_cols)



# show historic data
st.subheader("Historic Crowd Data")
st.line_chart(historic_data[['timestamp', sensor_to_plot]].set_index('timestamp'))
st.write(f"Current timestamp: {current_timestamp}")
st.write(f"Historic data size: {len(historic_data)}, Current data size: {len(current_data)}")
# --- Prediction Simulation ---
st.subheader("Predicted Crowd (Dynamic every 3 mins)")
placeholder = st.empty()  # for updating chart

# --- Live prediction ---
# Combine historic and current for feature context
historic_data_df = pd.DataFrame(historic_data)
current_data_df = pd.DataFrame(current_data)
current_data_df['timestamp'] = pd.to_datetime(current_timestamp)

X_live_scaled, pred_time = make_live_features(historic_data_df, current_data_df, sensor_cols, weather_cols, PAST_HOURS, scaler)

preds = {}
for sensor, model in models.items():
    preds[sensor] = model.predict(X_live_scaled)[0]


pred_df = pd.DataFrame([preds], index=[pred_time])


# --- Combine with historic ---
plot_df = pd.concat([historic_data.set_index('timestamp')[sensor_cols], pred_df])


# --- Select sensors ---
selected_sensors = st.multiselect("Select sensors to visualize", options=sensor_cols, default=[sensor_cols[0]])

# --- Plot 1: Historic + Predicted ---
fig1 = go.Figure()
for sensor in selected_sensors:
    fig1.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df[sensor],
        mode='lines+markers', name=f"{sensor}"
    ))

fig1.update_layout(title="Historic + Predicted Crowd Count",
                   xaxis_title="Time", yaxis_title="Crowd Count")
st.plotly_chart(fig1, use_container_width=True)



# Next step: Rolling predictions. 


