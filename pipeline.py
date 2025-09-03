import os
import tempfile
import pandas as pd
import streamlit as st
from typing import List, Callable, Optional
from ui_helpers import confirmation_modal, show_csv


from oci_helpers import (
    download_blob,
    upload_cloud_csv,
    load_cloud_csv,
    delete_objects,
)
from ml_models import (
    get_audio_emotion_model,
    get_whisper_model,
    get_text_emotion_classifier,
)
from utils import (
    preprocess_audio,
    decide_final_emotion,
)


def run_emotion_pipeline_for_files(
    object_names: List[str], progress_cb: Optional[Callable[[float], None]] = None
) -> None:
    """
    Downloads selected WAVs from OCI to a temp dir, runs the 4 steps,
    appends results to CSVs in OCI, syncs processed_incidents csv,
    and deletes the processed wavs from the bucket.
    """
    def _p(x):
        if progress_cb:
            progress_cb(x)

    tmpdir = tempfile.mkdtemp(prefix="wavs_")
    local_paths = []
    for name in object_names:
        data = download_blob(name)
        local_path = os.path.join(tmpdir, os.path.basename(name))
        with open(local_path, "wb") as f:
            f.write(data)
        local_paths.append(local_path)

    # Load previous CSVs or create empty with columns
    wav_cols = ["filename", "emotion", "confidence (%)"]
    wav_prev = load_cloud_csv("predicted_emotions.csv", wav_cols)

    trans_cols = ["filename", "transcription"]
    trans_prev = load_cloud_csv("transcription_output.csv", trans_cols)

    text_cols = ["filename", "emotion", "confidence_percent", "transcription"]
    text_prev = load_cloud_csv("transcription_output_with_emotion.csv", text_cols)

    # Step 1: Audio emotion (wav2vec)
    model = get_audio_emotion_model()
    new_rows = []
    for lp in local_paths:
        bn = os.path.basename(lp)
        if bn in (wav_prev["filename"].values if not wav_prev.empty else []):
            continue
        out_prob, score, index, label = model.classify_file(lp)
        raw_label = label[0].lower() if isinstance(label, (list, tuple)) else str(label).lower()
        key = raw_label[:3]
        emotion = {
            "ang": "Anger",
            "dis": "Disgust",
            "fea": "Fear",
            "hap": "Happy",
            "neu": "Neutral",
            "sad": "Sad",
            "cal": "Calm",
            "sur": "Surprised",
        }.get(key, "Unknown")
        conf = float(score) * 100
        new_rows.append([bn, emotion, f"{conf:.2f}"])
    wav_new = pd.DataFrame(new_rows, columns=wav_cols)
    wav_all = pd.concat([wav_prev, wav_new]).drop_duplicates(subset="filename", keep="last")
    upload_cloud_csv("predicted_emotions.csv", wav_all)
    _p(0.25)

    # Step 2: Whisper transcription
    whisper_model = get_whisper_model()
    new_rows_t = []
    for lp in local_paths:
        bn = os.path.basename(lp)
        if (not trans_prev.empty) and (bn in set(trans_prev["filename"].values)):
            continue
        cleaned = preprocess_audio(lp)
        result = whisper_model.transcribe(cleaned)
        transcription = (result.get("text") or "").strip()
        try:
            os.remove(cleaned)
        except Exception:
            pass
        new_rows_t.append([bn, transcription])
    trans_new = pd.DataFrame(new_rows_t, columns=trans_cols)
    trans_all = pd.concat([trans_prev, trans_new]).drop_duplicates(subset="filename", keep="last")
    upload_cloud_csv("transcription_output.csv", trans_all)
    _p(0.50)

    # Step 3: Text emotion classification
    clf = get_text_emotion_classifier()
    text_label_map = {
        "anger": "Anger",
        "disgust": "Disgust",
        "fear": "Fear",
        "joy": "Happy",
        "neutral": "Neutral",
        "sadness": "Sad",
        "calm": "Calm",
        "surprise": "Surprised",
    }
    new_rows_text = []
    for _, row in trans_all.iterrows():
        bn = row["filename"]
        if (not text_prev.empty) and (bn in set(text_prev["filename"].values)):
            continue
        text = row["transcription"]
        scores = clf(text)[0]
        best_label = None
        best_score = 0.0
        for item in scores:
            lbl = item["label"].lower()
            score = float(item["score"])
            if lbl in text_label_map and score > best_score:
                best_score = score
                best_label = text_label_map[lbl]
        if best_label is None:
            best_label = "Calm"
            best_score = 1.0
        new_rows_text.append({
            "filename": bn,
            "emotion": best_label,
            "confidence_percent": f"{best_score * 100:.2f}%",
            "transcription": text,
        })
    text_newdf = pd.DataFrame(new_rows_text)
    text_all = pd.concat([text_prev, text_newdf]).drop_duplicates(subset="filename", keep="last")
    upload_cloud_csv("transcription_output_with_emotion.csv", text_all)
    _p(0.75)

    # Step 4: Ensemble final emotion
    ens_cols = ["filename", "emotion", "transcription"]
    ens_prev = load_cloud_csv("final_emotion_ensemble.csv", ens_cols)
    new_rows_ens = []
    for bn in set(wav_all["filename"].values).union(set(text_all["filename"].values)):
        if (not ens_prev.empty) and (bn in set(ens_prev["filename"].values)):
            continue
        a_row = wav_all[wav_all["filename"] == bn]
        t_row = text_all[text_all["filename"] == bn]
        a_em = a_row["emotion"].values[0] if not a_row.empty else "neutral"
        t_em = t_row["emotion"].values[0] if not t_row.empty else "neutral"
        trans = t_row["transcription"].values[0] if not t_row.empty else ""
        final = decide_final_emotion(a_em, t_em)
        new_rows_ens.append({"filename": bn, "emotion": final, "transcription": trans})
    ens_new = pd.DataFrame(new_rows_ens)
    ens_all = pd.concat([ens_prev, ens_new]).drop_duplicates(subset="filename", keep="last")
    upload_cloud_csv("final_emotion_ensemble.csv", ens_all)

    # Sync processed_incidents csv
    upload_cloud_csv("processed_incidents_with_emotion.csv", ens_all.copy())
    _p(1.0)

    # Cleanup processed WAV files from cloud
    delete_objects(object_names)


def show_progress_ui() -> Callable[[float], None]:
    """Returns a callback function that updates a Streamlit progress bar."""

    progress_bar = st.progress(0)

    def progress_callback(progress: float):
        progress_bar.progress(min(max(progress, 0.0), 1.0))  # Clamp progress between 0 and 1

    return progress_callback


# Example usage in Streamlit app:
if __name__ == "__main__":
    st.title("Emotion Analysis Pipeline")
    uploaded_files = st.file_uploader("Upload WAV files", accept_multiple_files=True, type=["wav"])

    if uploaded_files:
        # Save uploaded files temporarily and get their names
        temp_dir = tempfile.mkdtemp(prefix="uploaded_wavs_")
        object_names = []
        for uploaded_file in uploaded_files:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            object_names.append(file_path)

        progress_cb = show_progress_ui()
        run_emotion_pipeline_for_files(object_names=object_names, progress_cb=progress_cb)
        st.success("Processing complete!")
