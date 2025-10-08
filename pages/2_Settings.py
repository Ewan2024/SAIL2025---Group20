import streamlit as st

st.title("Map Settings")

prefs = st.session_state.user_prefs

# Allow users to change settings
st.subheader("Map Style")
prefs["map_style"] = st.selectbox(
    "Choose map style:",
    ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter", "Esri Satellite", "Google Satellite"],
    index=["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter", "Esri Satellite", "Google Satellite"].index(prefs["map_style"])
)

st.subheader("Layers")
prefs["show_markers"] = st.checkbox("Show Sensor Markers", prefs["show_markers"])
prefs["show_labels"] = st.checkbox("Show Sensor Labels", prefs["show_labels"])
prefs["show_circles"] = st.checkbox("Show Sensor Circles", prefs["show_circles"])
prefs["show_arrows"] = st.checkbox("Show Sensor Arrows", prefs["show_arrows"])

# Save button 
if st.button("Save Preferences"):
    st.success("Preferences saved! Go back to the Map View to see changes.")
