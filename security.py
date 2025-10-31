import streamlit as st
import time

def check_login_status():
    #Display of Logout Button on every page of the dashbaord
    st.sidebar.button("Logout", on_click=lambda: st.session_state.update(logged_in=False, username=None), key="logout_sidebar")
    
    #Initialise session state
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    #check if user is not logged in --> rest of code (the page in sidebar) is not loaded
    if not st.session_state['logged_in']:
        st.error("Access Denied. Please log in to view this page. Click '''home''' to log in.")
        st.stop() #stops further execution of the code