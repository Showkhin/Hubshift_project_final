import streamlit as st
from ui_helpers import show_csv  # Assuming this helper for CSV display


def show():
    st.markdown("## ✅ Results")
    st.markdown("### 📄 processed_incidents_with_emotion.csv")
    show_csv("processed_incidents_with_emotion.csv", height=420)

    st.markdown("### 📚 Supporting CSVs")
    tab1, tab2, tab3, tab4 = st.tabs([
        "predicted_emotions",
        "transcription_output",
        "transcription_output_with_emotion",
        "final_emotion_ensemble",
    ])
    with tab1:
        show_csv("predicted_emotions.csv")
    with tab2:
        show_csv("transcription_output.csv")
    with tab3:
        show_csv("transcription_output_with_emotion.csv")
    with tab4:
        show_csv("final_emotion_ensemble.csv")

    st.write("")
    st.button("⬅️ Back to start", on_click=lambda: st.session_state.update({"page": "Welcome"}))
