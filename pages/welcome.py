import streamlit as st
from oci_helpers import list_wavs, upload_blob
from ui_helpers import confirmation_modal, show_csv  # Assuming these are in ui_helpers.py


def show():
    # Hero welcome message
    st.markdown("""
    <div class="app-hero">
      <h1>Welcome, <b>Lord Commander</b> ⚔️</h1>
      <p class="soft">Have a look in our <b>Trashery</b> — review incidents, pick samples, and process emotions.</p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.markdown("### 📄 processed_incidents_with_emotion.csv")
    show_csv("processed_incidents_with_emotion.csv", height=360)

    st.write("")
    st.markdown("### 🎧 sample_display — select up to 3 WAV files (prefix: <code>sample</code>)")
    sample_names = list_wavs(prefix="sample")
    sel = st.multiselect("Choose up to 3 files:", options=sample_names, max_selections=3)

    left, right = st.columns([3, 1])
    with left:
        st.caption(f"{len(sample_names)} available in cloud bucket.")
    with right:
        if st.button("Proceed", key="proceed_samples", use_container_width=True):
            if not sel:
                st.error("Select at least one file (max 3).")
            else:
                st.session_state.pending_action = "samples"
                st.session_state.pending_files = sel
                st.session_state.processing = True
                st.session_state.page = "Processing"
                st.rerun()

    st.write("")
    st.markdown("### ⬆️ Upload up to 3 new WAV files")
    up_files = st.file_uploader(
        "Drop .wav files here (max 3)",
        type=["wav"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.get('uploader_key', 0)}"
    )
    if up_files and len(up_files) > 3:
        st.error("You can upload at most 3 files at a time.")

    upload_col1, upload_col2 = st.columns([3, 1])
    with upload_col2:
        if st.button("Proceed", key="proceed_upload", use_container_width=True):
            if not up_files:
                st.error("Please upload 1–3 .wav files.")
            else:
                uploaded_names = []
                for f in up_files[:3]:
                    name = f.name
                    if not name.lower().endswith(".wav"):
                        continue
                    data = f.read()
                    upload_blob(name, data)
                    uploaded_names.append(name)
                st.session_state.pending_action = "upload"
                st.session_state.pending_files = uploaded_names
                st.session_state.processing = True
                st.session_state.page = "Processing"
                st.rerun()

    # Optionally show confirmation modal if pending action is set
    if st.session_state.get("pending_action") in ("samples", "upload") and st.session_state.get("pending_files"):
        confirmation_modal()
