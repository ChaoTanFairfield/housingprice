import streamlit as st
import requests
import pandas as pd

# Title
st.title("Housing Price Prediction")

# Sidebar for input fields
st.sidebar.header("Enter House Details")

# User Inputs
square_feet = st.sidebar.number_input("Square Feet", min_value=100, max_value=10000, step=50)
bedrooms = st.sidebar.number_input("Bedrooms", min_value=1, max_value=10, step=1)
bathrooms = st.sidebar.number_input("Bathrooms", min_value=1, max_value=10, step=1)
location = st.sidebar.text_input("Location (City, State)")

# API Endpoint for Prediction
API_URL = "http://127.0.0.1:5000/predict"

# Submit Button
if st.sidebar.button("Predict Price"):
    if location:
        # Send data to backend API
        data = {
            "square_feet": square_feet,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "location": location
        }
        
        response = requests.post(API_URL, json=data)
        
        if response.status_code == 200:
            result = response.json()
            st.success(f"Estimated Price: **${result['predicted_price']:,}**")
        else:
            st.error("⚠️ Error getting prediction. Check backend connection.")
    else:
        st.warning("⚠️ Please enter a location.")

st.header("Location Preview")
st.map(pd.DataFrame({"lat": [41.160], "lon": [-73.257]}))  
