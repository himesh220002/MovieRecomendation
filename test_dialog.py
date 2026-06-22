import streamlit as st

@st.dialog("My Dialog")
def my_dialog():
    st.write("Inside dialog")
    if st.button("Click me inside"):
        st.write("Clicked inside!")

tab1, tab2 = st.tabs(["Tab 1", "Tab 2"])
with tab1:
    st.write("Tab 1")
    if st.button("Open Dialog 1"):
        my_dialog()
with tab2:
    st.write("Tab 2")
    if st.button("Open Dialog 2"):
        my_dialog()
