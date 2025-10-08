<<<<<<< Updated upstream
import streamlit as st

def login_page():

    st.title("Welcome to the Sail 2025 Crowd Management Dashboard") #add title to login page

    option = st.selectbox("Login/Signup", ["Login", "Sign Up"]) #offer login or signup option to user

    if option == "Login": #if login is selcted...
        username = st.text_input("Username")
        password = st.text_input("Password", type = "password")
        st.button("Login")

    else: #if sign up is selceted
        username = st.text_input("Username")
        password = st.text_input("Password", type = "password")

        email = st.text_input("Enter your EMail address")
        st.button("Create Account")
=======
import streamlit_authenticator as stauth

>>>>>>> Stashed changes
