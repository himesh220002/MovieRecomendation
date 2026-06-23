import streamlit as st
import time

st.title("Test")
st.write("This should appear instantly")

with st.spinner("Loading 3 seconds..."):
    time.sleep(3)
    
st.write("Done!")
