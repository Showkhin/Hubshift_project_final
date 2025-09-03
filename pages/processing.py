import streamlit as st
import os

from pipeline import run_emotion_pipeline_for_files, show_progress_ui


def show():
    st.title("Processing Selected Files")

    if "pending_files" not in st.session_state or not st.session_state.pending_files:
        st.warning("No files selected. Returning to welcome page.")
        st.session_state.page = "Welcome"
        st.rerun()

    cb = show_progress_ui()

    if st.session_state.processing:
        try:
            cb(0.0)
            names = st.session_state.pending_files
            run_emotion_pipeline_for_files(names, progress_cb=cb)
            st.session_state.processing = False
            st.session_state.pending_action = None
            st.session_state.pending_files = []
            st.session_state.page = "Results"
            st.success("Processing complete!")
            st.rerun()
        except Exception as e:
            st.session_state.processing = False
            st.error(f"Processing failed: {e}")
            if st.button("Back to start"):
                st.session_state.page = "Welcome"
                st.rerun()
    else:
        st.info("Processing not started.")
