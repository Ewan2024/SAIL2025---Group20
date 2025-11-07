import streamlit as st
import pandas as pd
import joblib
from datetime import timedelta
import plotly.graph_objects as go
from data_loader import load_live_sensor_data

#check whether user is logged in. Only then the page is loaded - only activate upon final implementation
#from security import check_login_status 
#check_login_status()

st.title("Crowd Prediction Dashboard")

# Functions

def create_features(df, sensor_cols, feature_cols, 
                    lags=[1,2,3,5,10,20,30,40,50,60,75],
                    rolling_windows=[3,5,10,20,40,60],
                    dropna=True):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    df_long = df[sensor_cols].reset_index().melt(
        id_vars='timestamp',
        value_vars=sensor_cols,
        var_name='location',
        value_name='count'
    )
    df_long = df_long.merge(df[feature_cols].reset_index(), on='timestamp', how='left')
    loc_map = {loc: i for i, loc in enumerate(sensor_cols)}
    df_long['location_id'] = df_long['location'].map(loc_map)
    df_long = df_long.sort_values(['location_id', 'timestamp'])
    for lag in lags:
        df_long[f'lag_{lag}'] = df_long.groupby('location_id')['count'].shift(lag)
    for w in rolling_windows:
        df_long[f'roll_mean_{w}'] = df_long.groupby('location_id')['count'].rolling(w).mean().reset_index(level=0, drop=True)
    if dropna:
        df_long = df_long.dropna()
    return df_long


def recursive_forecast(model, incoming_df, sensor_cols, feature_cols,
                       selected_sensor, current_timestamp,
                       steps=20, interval_minutes=3):
    forecast_results = []
    df_future = incoming_df.copy().set_index('timestamp')
    for step in range(1, steps + 1):
        ts = current_timestamp + pd.Timedelta(minutes=interval_minutes * step)
        feat_df = create_features(df_future.reset_index(), sensor_cols, feature_cols, dropna=False)
        latest_row = feat_df[feat_df["location"] == selected_sensor].sort_values("timestamp").tail(1)
        X_input = latest_row.drop(columns=["count", "location", "timestamp"])
        pred_val = model.predict(X_input)[0]
        forecast_results.append((ts, pred_val))
        # Append prediction for next step
        new_row = {"timestamp": ts}
        for col in sensor_cols:
            new_row[col] = pred_val if col == selected_sensor else df_future[col].iloc[-1]
        for col in feature_cols:
            new_row[col] = df_future[col].iloc[-1]
        df_future = pd.concat([df_future.reset_index(), pd.DataFrame([new_row])], ignore_index=True)
        df_future = df_future.set_index('timestamp')
    return pd.DataFrame(forecast_results, columns=["timestamp", "prediction"])


def plot_crowd_data(selected_sensor, historic_data, current_data, latest, multi_df, interval_minutes, forecast_steps):
    # Standardise colors and line styles
    colors = {"historic": "blue", "current": "orange", "prediction_1step": "red",
              "prediction_multistep": "purple", "actual_future": "green"}
    line_styles = {"historic": "solid", "current": "solid", "prediction_1step": "dash",
                   "prediction_multistep": "dash", "actual_future": "solid"}

    # Historic + current dataframes
    hist_df = pd.DataFrame({"timestamp": historic_data.index,
                            "value": historic_data[selected_sensor].values,
                            "type": "historic"})
    curr_df = pd.DataFrame({"timestamp": [current_timestamp],
                            "value": current_data[selected_sensor].values,
                            "type": "current"})
    
    # 1-step prediction (removed, as it is covered by multi-step pred)
    # t1_timestamp = current_timestamp + pd.Timedelta(minutes=interval_minutes)
    # t1_val = latest.loc[latest["location"] == selected_sensor, "prediction"].values[0]
    # pred1_df = pd.DataFrame({"timestamp": [t1_timestamp], "value": [t1_val], "type": "prediction_1step"})

    # Multi-step prediction
    multi_df_plot = pd.DataFrame({"timestamp": multi_df["timestamp"],
                                  "value": multi_df["prediction"],
                                  "type": "prediction_multistep"})
    
    # Actual future (purely to evaluate accuracy of model,
    # future data will not be known in actual run)
    future_end_time = current_timestamp + pd.Timedelta(minutes=interval_minutes * forecast_steps)
    actual_future_df = df[(df.index > current_timestamp) & (df.index <= future_end_time)][[selected_sensor]].copy()
    actual_future_df = actual_future_df.reset_index().rename(columns={selected_sensor: "value"})
    actual_future_df["type"] = "actual_future"
    # Combine all
    plot_df = pd.concat([hist_df, curr_df, multi_df_plot, actual_future_df], ignore_index=True) #pred1_df
    # Plot
    fig = go.Figure()
    for t in plot_df["type"].unique():
        subset = plot_df[plot_df["type"] == t].sort_values("timestamp")
        fig.add_trace(go.Scatter(x=subset["timestamp"], y=subset["value"],
                                 mode="lines+markers", name=t,
                                 line=dict(color=colors[t], dash=line_styles[t], width=2),
                                 marker=dict(size=6, color=colors[t])))
    # Zoom past 1 hour + forecast
    one_hour_ago = current_timestamp - pd.Timedelta(hours=1)
    fig.update_layout(title=f"Actual vs Predicted Crowd Count for {selected_sensor}",
                      xaxis_title="Timestamp", yaxis_title="Crowd Count",
                      legend_title="Type", template="plotly_white",
                      xaxis=dict(range=[one_hour_ago, future_end_time]))
    st.plotly_chart(fig, use_container_width=True)



# Load model and data

MODEL_DIR = 'Notebooks/crowd_count_model.pkl'
DATA_FILE = 'data/crowd_weather_merged.csv'
model = joblib.load(MODEL_DIR)
df = pd.read_csv(DATA_FILE)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')

sensor_data, current_timestamp = load_live_sensor_data()
sensor_cols = df.columns[0:-14]
feature_cols = df.columns[-14:]

# Historic / current
historic_data = df[df.index < current_timestamp].copy()
current_data = df[df.index == current_timestamp].copy()
incoming_df = pd.concat([historic_data, current_data]).reset_index()
feature_df = create_features(incoming_df.copy(), sensor_cols, feature_cols, dropna=False)
latest = feature_df[feature_df['timestamp'] == current_timestamp].copy()
latest["prediction"] = model.predict(latest.drop(columns=["count", "location", "timestamp"]))


# Interactive sensor selection

selected_sensor = st.selectbox("Select a sensor to view", options=sensor_cols)

# Multi-step forecast
FORECAST_STEPS = 20
INTERVAL_MINUTES = 3
multi_df = recursive_forecast(model, incoming_df, sensor_cols, feature_cols,
                              selected_sensor, current_timestamp, steps=FORECAST_STEPS,
                              interval_minutes=INTERVAL_MINUTES)

# Plot
plot_crowd_data(selected_sensor, historic_data, current_data, latest, multi_df,
                INTERVAL_MINUTES, FORECAST_STEPS)


# (Archived Code)
# import streamlit as st
# import pandas as pd
# import numpy as np
# import joblib
# import os
# import time
# from datetime import timedelta
# import plotly.graph_objects as go
# import plotly.express as px
# from data_loader import load_live_sensor_data


# #check whether user is logged in. Only then the page is loaded - only activate upon final implementation
# #from security import check_login_status 
# #check_login_status()


# # Functions 
# def create_features(df, sensor_cols, feature_cols, 
#                     lags=[1,2,3,5,10,20,30,40,50,60,75],
#                     rolling_windows=[3,5,10,20,40,60],
#                     dropna=True):

#     df['timestamp'] = pd.to_datetime(df['timestamp'])
#     df = df.set_index('timestamp')

#     # Wide → Long
#     df_long = df[sensor_cols].reset_index().melt(
#         id_vars='timestamp',
#         value_vars=sensor_cols,
#         var_name='location',
#         value_name='count'
#     )

#     # Attach feature columns back
#     df_long = df_long.merge(
#         df[feature_cols].reset_index(),
#         on='timestamp',
#         how='left'
#     )

#     # Add numeric location ID
#     loc_map = {loc: i for i, loc in enumerate(sensor_cols)}
#     df_long['location_id'] = df_long['location'].map(loc_map)

#     # Sort
#     df_long = df_long.sort_values(['location_id', 'timestamp'])

#     # Lag features
#     for lag in lags:
#         df_long[f'lag_{lag}'] = df_long.groupby('location_id')['count'].shift(lag)

#     # Rolling windows
#     for w in rolling_windows:
#         df_long[f'roll_mean_{w}'] = (
#             df_long.groupby('location_id')['count']
#             .rolling(w)
#             .mean()
#             .reset_index(level=0, drop=True)
#         )

#     if dropna:
#         df_long = df_long.dropna()

#     return df_long

# st.title("Crowd Prediction Dashboard")

# def recursive_forecast(model, incoming_df, sensor_cols, feature_cols,
#                        selected_sensor, current_timestamp,
#                        steps=20, interval_minutes=3):
#     """
#     Performs recursive multi-step forecasting for a single sensor.
#     """
#     forecast_results = []

#     # Work on a copy
#     df_future = incoming_df.copy()
#     df_future = df_future.set_index('timestamp')

#     for step in range(1, steps + 1):

#         # Next timestamp
#         ts = current_timestamp + pd.Timedelta(minutes=interval_minutes * step)

#         # Build features for all sensors at all previous timestamps
#         feat_df = create_features(df_future.reset_index(), sensor_cols, feature_cols, dropna=False)

#         # Get latest feature row for selected sensor
#         latest_row = feat_df[feat_df["location"] == selected_sensor].sort_values("timestamp").tail(1)
#         X_input = latest_row.drop(columns=["count", "location", "timestamp"])

#         # Predict
#         pred_val = model.predict(X_input)[0]
#         forecast_results.append((ts, pred_val))

#         # Append prediction to df_future for next step
#         # Keep all other sensor counts the same as last timestamp
#         new_row = {"timestamp": ts}
#         for col in sensor_cols:
#             if col == selected_sensor:
#                 new_row[col] = pred_val
#             else:
#                 new_row[col] = df_future[col].iloc[-1]

#         # Add feature columns (weather/time features)
#         for col in feature_cols:
#             new_row[col] = df_future[col].iloc[-1]

#         # Append
#         df_future = pd.concat([df_future.reset_index(), pd.DataFrame([new_row])], ignore_index=True)
#         df_future = df_future.set_index('timestamp')

#     forecast_df = pd.DataFrame(forecast_results, columns=["timestamp", "prediction"])
#     return forecast_df



# # Configure for multi-step forecasting
# FORECAST_STEPS = 20       # 5 steps → 5 × 3 min = 15 minutes ahead
# INTERVAL_MINUTES = 3     # sampling rate



# # Load data
# MODEL_DIR = 'Notebooks/crowd_count_model.pkl'  # folder with joblib XGBoost model
# DATA_FILE = 'data/crowd_weather_merged.csv'  # merged_df CSV
# model = joblib.load(MODEL_DIR)
# df = pd.read_csv(DATA_FILE)
# df['timestamp'] = pd.to_datetime(df['timestamp'])
# df = df.set_index('timestamp')
# sensor_data, current_timestamp = load_live_sensor_data() 
# sensor_cols = df.columns[0:-14]
# feature_cols = df.columns[-14:]

# st.write(f"Current timestamp: {current_timestamp}")

# # Split: everything before `current_timestamp` is historic
# historic_data = df[df.index < current_timestamp].copy()
# current_data = df[df.index == current_timestamp].copy()
# # st.subheader("Historic Data (before current timestamp)")
# # st.write(historic_data)
# # st.subheader("Live Sensor Data (current timestamp)")
# # st.write(current_data)

# # Create features for prediction
# incoming_df = pd.concat([historic_data, current_data]).reset_index()

# # st.subheader("Incoming Dataframe")
# # st.write(incoming_df)

# feature_df = create_features(
#     incoming_df.copy(),
#     sensor_cols=sensor_cols,
#     feature_cols=feature_cols,
#     dropna=False
# )

# # st.subheader("Feature Dataframe")
# # st.write(feature_df)

# # Keep only the rows that belong to the current timestamp
# latest = feature_df[feature_df['timestamp'] == current_timestamp].copy()

# # st.subheader("Latest Dataframe")
# # st.write(latest)

# X_pred = latest.drop(columns=["count", "location", "timestamp"])

# # st.subheader("X_pred")
# # st.write(X_pred)

# # Predict
# preds = model.predict(X_pred)
# latest["prediction"] = preds

# # st.subheader("Predictions for Current Timestamp")
# # st.write(latest[["location", "prediction"]])

# # import plotly.express as px
# # fig = px.bar(latest, x="location", y="prediction",
# #              title="Predicted Crowd Count Per Location")
# # st.plotly_chart(fig, use_container_width=True)


# # Sensor selection
# selected_sensor = st.selectbox(
#     "Select a location / sensor",
#     options=sensor_cols
# )

# # Build Plot data

# # 1. Historic data for the selected sensor
# hist_series = historic_data[selected_sensor].dropna()
# hist_df = pd.DataFrame({
#     "timestamp": hist_series.index,
#     "value": hist_series.values,
#     "type": "historic"
# })

# # 2. Current value for this sensor
# if selected_sensor in current_data.columns and not current_data.empty:
#     curr_df = pd.DataFrame({
#         "timestamp": [current_timestamp],
#         "value": current_data[selected_sensor].values,
#         "type": ["current"]
#     })
# else:
#     curr_df = pd.DataFrame(columns=["timestamp", "value", "type"])

# # 3. Prediction for this sensor
# pred_val = latest.loc[latest["location"] == selected_sensor, "prediction"].values[0]
# prediction_timestamp = current_timestamp + pd.Timedelta(minutes=3)
# pred_df = pd.DataFrame({
#     "timestamp": [prediction_timestamp],
#     "value": [pred_val],
#     "type": ["prediction"]
# })

# # Combine into one dataframe
# plot_df = pd.concat([hist_df, curr_df, pred_df], ignore_index=True)

# # st.write("DataFrame to Plot")
# # st.write(plot_df)

# # Plot
# fig = go.Figure()

# # Main connected line
# fig.add_trace(go.Scatter(
#     x=plot_df.sort_values("timestamp")["timestamp"],
#     y=plot_df.sort_values("timestamp")["value"],
#     mode="lines+markers",
#     name="crowd_count",
#     line=dict(width=2),
# ))

# # Add marker overlays to distinguish each type
# for t, color in {
#     "historic": "blue",
#     "current": "orange",
#     "prediction": "red"
# }.items():
#     subset = plot_df[plot_df["type"] == t]
#     fig.add_trace(go.Scatter(
#         x=subset["timestamp"],
#         y=subset["value"],
#         mode="markers",
#         name=t,
#         marker=dict(size=10, color=color)
#     ))


# st.plotly_chart(fig, use_container_width=True)


# # Multi-step forecast 

# multi_df = recursive_forecast(
#     model=model,
#     incoming_df=incoming_df,
#     sensor_cols=sensor_cols,
#     feature_cols=feature_cols,
#     selected_sensor=selected_sensor,
#     current_timestamp=current_timestamp,
#     steps=FORECAST_STEPS,
#     interval_minutes=INTERVAL_MINUTES
# )

# # Historic
# hist_series = historic_data[selected_sensor].dropna()
# hist_df = pd.DataFrame({
#     "timestamp": hist_series.index,
#     "value": hist_series.values,
#     "type": "historic"
# })

# # Current
# curr_df = pd.DataFrame({
#     "timestamp": [current_timestamp],
#     "value": current_data[selected_sensor].values,
#     "type": ["current"]
# })

# # 1-step prediction (t + 3min)
# t1_timestamp = current_timestamp + pd.Timedelta(minutes=INTERVAL_MINUTES)
# t1_val = latest.loc[latest["location"] == selected_sensor, "prediction"].values[0]

# pred1_df = pd.DataFrame({
#     "timestamp": [t1_timestamp],
#     "value": [t1_val],
#     "type": ["prediction_1step"]
# })

# # Multi-step forecast
# multi_df_plot = pd.DataFrame({
#     "timestamp": multi_df["timestamp"],
#     "value": multi_df["prediction"],
#     "type": ["prediction_multistep"] * len(multi_df)
# })

# # Combine all
# plot_df = pd.concat([hist_df, curr_df, pred1_df, multi_df_plot], ignore_index=True)

# # Plot
# fig = go.Figure()

# # Main connected line
# fig.add_trace(go.Scatter(
#     x=plot_df.sort_values("timestamp")["timestamp"],
#     y=plot_df.sort_values("timestamp")["value"],
#     mode="lines+markers",
#     name="crowd_count",
#     line=dict(width=2),
# ))

# # Add marker overlays to distinguish each type
# for t, color in {
#     "historic": "blue",
#     "current": "orange",
#     "prediction_multistep": "red"
# }.items():
#     subset = plot_df[plot_df["type"] == t]
#     fig.add_trace(go.Scatter(
#         x=subset["timestamp"],
#         y=subset["value"],
#         mode="markers",
#         name=t,
#         marker=dict(size=10, color=color)
#     ))

# st.plotly_chart(fig, use_container_width=True)

# # Visualise Actual vs Prediction

# # Prepare actual future values
# future_end_time = current_timestamp + pd.Timedelta(minutes=INTERVAL_MINUTES * FORECAST_STEPS)
# actual_future_df = df[(df.index > current_timestamp) & (df.index <= future_end_time)][[selected_sensor]].copy()
# actual_future_df = actual_future_df.reset_index()
# actual_future_df = actual_future_df.rename(columns={selected_sensor: "value"})
# actual_future_df["type"] = "actual_future"

# # 1-step prediction
# t1_timestamp = current_timestamp + pd.Timedelta(minutes=INTERVAL_MINUTES)
# t1_val = latest.loc[latest["location"] == selected_sensor, "prediction"].values[0]
# pred1_df = pd.DataFrame({
#     "timestamp": [t1_timestamp],
#     "value": [t1_val],
#     "type": "prediction_1step"
# })

# # Multi-step prediction
# multi_df_plot = pd.DataFrame({
#     "timestamp": multi_df["timestamp"],
#     "value": multi_df["prediction"],
#     "type": "prediction_multistep"
# })

# # Historic + current
# hist_df = pd.DataFrame({
#     "timestamp": historic_data.index,
#     "value": historic_data[selected_sensor].values,
#     "type": "historic"
# })
# curr_df = pd.DataFrame({
#     "timestamp": [current_timestamp],
#     "value": current_data[selected_sensor].values,
#     "type": "current"
# })

# # Combine all
# plot_df = pd.concat([hist_df, curr_df, pred1_df, multi_df_plot, actual_future_df], ignore_index=True)

# # Plot
# fig = go.Figure()

# # Define line styles
# line_styles = {
#     "historic": "solid",
#     "current": "solid",
#     "prediction_1step": "dash",
#     "prediction_multistep": "dash",
#     "actual_future": "solid"
# }

# colors = {
#     "historic": "blue",
#     "current": "orange",
#     "prediction_1step": "red",
#     "prediction_multistep": "purple",
#     "actual_future": "green"
# }

# for t in plot_df["type"].unique():
#     subset = plot_df[plot_df["type"] == t].sort_values("timestamp")
#     fig.add_trace(go.Scatter(
#         x=subset["timestamp"],
#         y=subset["value"],
#         mode="lines+markers",
#         name=t,
#         line=dict(color=colors[t], dash=line_styles[t], width=2),
#         marker=dict(size=6)
#     ))

# fig.update_layout(
#     title=f"Actual vs Predicted Crowd Count for {selected_sensor}",
#     xaxis_title="Timestamp",
#     yaxis_title="Crowd Count",
#     legend_title="Type",
#     template="plotly_white"
# )

# st.plotly_chart(fig, use_container_width=True)