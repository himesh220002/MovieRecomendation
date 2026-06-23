import streamlit as st
import time

@st.dialog("My Dialog")
def my_dialog():
    st.write("This should appear instantly")
    with st.spinner("Loading 3 seconds..."):
        time.sleep(3)
    st.write("Done!")

if st.button("Open Dialog"):
    my_dialog()
