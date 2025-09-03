import numpy as np
import soundfile as sf
import noisereduce as nr

def preprocess_audio(file_path: str) -> str:
    audio, sr = sf.read(file_path)
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    reduced = nr.reduce_noise(y=audio, sr=sr)
    cleaned_path = file_path.replace(".wav", "_cleaned.wav")
    sf.write(cleaned_path, reduced, sr)
    return cleaned_path

def decide_final_emotion(audio_em: str, text_em: str) -> str:
    audio_em = (audio_em or "").lower()
    text_em = (text_em or "").lower()
    mapping = {
        ("anger", "happy"): "Anger",
        ("anger", "neutral"): "Anger",
        ("neutral", "fear"): "Fear",
        ("sad", "neutral"): "Sad",
        ("neutral", "happy"): "Happy",
        ("calm", "neutral"): "Calm",
        ("disgust", "neutral"): "Disgust",
        ("fear", "neutral"): "Fear",
        ("happy", "sad"): "Happy",
        ("surprise", "neutral"): "Surprised",
    }
    if (audio_em, text_em) in mapping:
        return mapping[(audio_em, text_em)]
    if audio_em in {"anger", "sad", "calm", "disgust", "fear", "happy", "surprise", "neutral"}:
        return audio_em.capitalize()
    return text_em.capitalize() if text_em else "Neutral"
