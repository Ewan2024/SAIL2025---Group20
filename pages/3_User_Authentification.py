#imports
import streamlit as st
import hashlib 
import pickle
import os

#path to pkl file used for user data (username and passoword) storage
user_database = "data/user_database.pkl"

#load user data from the pickle file
def load_user_data():
    # Return empty dictionary with "username" key if the database is empty or the file is non-existent
    if not os.path.exists(user_database) or os.path.getsize(user_database) == 0:
        return {"username": {}}

    with open(user_database, "rb") as file:
        return pickle.load(file)
    
#store username and hashed password in a pickle file
def save_user_data(data):
    with open(user_database, "wb") as file:
        pickle.dump(data, file)

#hash the password for increased data security
def hash_passwords(password):
    password_bytes = password.encode('utf-8')
    return hashlib.sha256(password_bytes).hexdigest()

#autheticator function
def authenticate_user(username, password, user_data):
    if username not in user_data["username"]:
        return False

    #access hashed password assigned to user based on key "username"
    stored_pw = user_data['username'][username]["hashed_password"]
    #call hash_passwords function to convert user input to hash format
    input_pw = hash_passwords(password)
    #compare stored and input password by value and return a boolean
    return stored_pw == input_pw

#combine all defined function in one main function
def login_page():

    #Configure streamlit page
    st.set_page_config(page_title="Crowd Data Line Graph", page_icon="📈", layout="wide")
    st.title("Login Page")
    st.caption("Welcome to the Sail 2025 Crowd Management Dashboard")

    option = st.selectbox("Login/Signup", ["Login", "Sign Up"])

    #Login functionality
    user_data = load_user_data() #define user data --> python dictionary with key "usernames" and value "password"

    if option == "Login": #if login is selcted...
        st.subheader("Login to your Account")
        login_username = st.text_input("Username")
        login_password = st.text_input("Password", type = "password")

        if st.button("Login"): #if login button is pressed call authenticate_user function

            authentication_state = authenticate_user(login_username, login_password, user_data)

            if authentication_state == True:
                st.success(f"Welcome back {login_username} !")
            
            else: #In case username is not found in database
                st.error("Invalid Username or Password.")


    else: #if sign up is selceted...
        st.subheader("Create new account")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type = "password")

        if st.button("Create Account"): #if create account is selected...
            #error if not all fields are filled
            if not new_username or not new_password:
                st.warning("Please enter both username and password!")
            #warning in case username already exists
            elif new_username in user_data["username"]:
                st.warning("Username already exists. Please login instead.")
            else:
                #call hash_password function to hash password
                hash_pwd = hash_passwords(new_password)
                #add username and hashed password in dictionary format
                user_data["username"][new_username] = {
                "hashed_password": hash_pwd
                }
                #add new user data to pickle file calling the save_user_data function
                save_user_data(user_data)
                st.success("Your account has successfully been created! You can now Log in :)")

login_page()