import streamlit as st
from pipeline import run_emotion_pipeline_for_files, show_progress_ui
#from pipeline import run_emotion_pipeline_for_files

def show():
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
            st.experimental_rerun()
        except Exception as e:
            st.session_state.processing = False
            st.error(f"Processing failed: {e}")
            if st.button("Back to start"):
                st.session_state.page = "Welcome"
                st.experimental_rerun()
