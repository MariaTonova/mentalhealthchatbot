import streamlit as st
import requests

st.title("Mood-Based Chatbot")

user_input = st.text_input("Enter your message:")
if user_input:
    response = requests.post("http://127.0.0.1:5000/chat", json={"message": user_input})
    result = response.json()
    st.write(f"Mood detected: **{result['mood']}**")
    st.write(f"Bot response: _{result['response']}_")