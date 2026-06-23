import streamlit as st
import time

st.title("Test")
st.write("This should appear instantly")

placeholder = st.empty()
placeholder.markdown("<div style='font-size: 50px'>LOADING...</div>", unsafe_allow_html=True)
time.sleep(3)
placeholder.markdown("<div style='font-size: 50px'>DONE</div>", unsafe_allow_html=True)
