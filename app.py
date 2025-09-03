import streamlit as st
from pages import welcome, processing, results

if "page" not in st.session_state:
    st.session_state.page = "Welcome"
if "pending_files" not in st.session_state:
    st.session_state.pending_files = []
if "processing" not in st.session_state:
    st.session_state.processing = False

def main():
    if st.session_state.page == "Welcome":
        welcome.show()
    elif st.session_state.page == "Processing":
        processing.show()
    elif st.session_state.page == "Results":
        results.show()

if __name__ == "__main__":
    main()
