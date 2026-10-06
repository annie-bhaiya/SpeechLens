import numpy as np
from scipy.fft import dct
from scipy.signal import get_window
import librosa
import webrtcvad
from .config import PIPELINE
from .utils import jsonable

def speech_mask(y, sr=16000):
    vad = webrtcvad.Vad(2)
    width = 320
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    flags = [vad.is_speech(pcm[i:i+width].tobytes(), sr) for i in range(0, len(pcm)-width+1, width)]
    return np.asarray(flags, bool)

def frames(y, length=400, hop=160):
    if len(y) < length:
        y = np.pad(y, (0, length-len(y)))
    return np.lib.stride_tricks.sliding_window_view(y, length)[::hop].copy()

def extract(y):
    sr, L, H = 16000, PIPELINE["frame_samples"], PIPELINE["hop_samples"]
    audio_frames = frames(y, L, H)
    time_s = (np.arange(len(audio_frames))*H + L/2)/sr
    rms = np.sqrt(np.mean(audio_frames.astype(np.float64)**2, axis=1))
    clipping = np.mean(np.abs(audio_frames)>=.999,axis=1)
    energy = 20*np.log10(rms+1e-10)
    spectrum = np.fft.rfft(audio_frames * get_window("hann", L, fftbins=True), n=512, axis=1)
    power = (np.abs(spectrum)**2).T
    mel_filter = librosa.filters.mel(sr=sr, n_fft=512, n_mels=40, fmin=0, fmax=8000, htk=False, norm="slaney")
    log_mel = np.log(np.maximum(mel_filter @ power, 1e-10))
    mfcc = dct(log_mel, type=2, axis=0, norm="ortho")[:13].T
    vad = speech_mask(y)
    speech = vad[np.minimum((time_s/.02).astype(int), max(0, len(vad)-1))] if len(vad) else np.zeros(len(time_s), bool)
    speech_center = float(np.median(energy[speech])) if speech.any() else None
    relative_energy = energy-speech_center if speech_center is not None else np.full(len(energy), np.nan)
    # pYIN is kept independent of VAD: unvoiced speech remains speech in the VAD mask.
    f0, voiced, probability = librosa.pyin(y, fmin=PIPELINE["pitch_min_hz"], fmax=PIPELINE["pitch_max_hz"],
                                         sr=sr, frame_length=1024, hop_length=H, center=False, fill_na=np.nan)
    pitch_time = (np.arange(len(f0))*H+512)/sr
    finite = voiced & np.isfinite(f0)
    center_hz = float(np.median(f0[finite])) if finite.any() else None
    semitones = 12*np.log2(f0/center_hz) if center_hz else np.full(len(f0), np.nan)
    crossings = np.mean(np.diff(np.signbit(audio_frames), axis=1), axis=1)
    frequencies = np.fft.rfftfreq(512, 1/sr)
    centroid = (power*frequencies[:, None]).sum(axis=0)/(power.sum(axis=0)+1e-10)
    flatness = np.exp(np.mean(np.log(power+1e-10), axis=0))/(np.mean(power+1e-10, axis=0))
    quality = {"clipped_fraction": float(np.mean(np.abs(y)>=.999)), "peak_dbfs": float(20*np.log10(np.max(np.abs(y))+1e-10)),
               "speech_fraction": float(np.mean(speech)), "voiced_fraction": float(np.mean(finite)),
               "median_speech_dbfs": speech_center,
               "noise_floor_dbfs_proxy": float(np.percentile(energy[~speech], 50)) if (~speech).any() else None,
               "mean_spectral_centroid_hz": float(np.mean(centroid)),
               "pitch_near_search_edge_fraction": float(np.mean((f0[finite]<55)|(f0[finite]>570))) if finite.any() else None}
    # Signed min/max waveform envelope keeps local transient peaks for display.
    bins = max(1, int(sr*.025))
    wave = frames(y, bins, bins)
    return {"version": "dsp-v1", "duration_s": len(y)/sr,
            "spectral": {"time_s": time_s, "rms": rms, "energy_dbfs": energy, "energy_relative_db": relative_energy,
                         "speech_mask": speech, "mfcc": mfcc, "centroid_hz": centroid,
                         "clipped_fraction": clipping,
                         "flatness": flatness, "zero_crossing_rate": crossings,
                         "stft_db": 10*np.log10(power[:, ::10]+1e-10), "stft_time_s": time_s[::10],
                         "stft_frequency_hz": frequencies},
            "pitch": {"time_s": pitch_time, "f0_hz": f0, "semitones": semitones,
                      "voiced_mask": voiced, "voicing_probability": probability, "median_hz": center_hz},
            "waveform": {"time_s": (np.arange(len(wave))*bins+bins/2)/sr,
                         "min": wave.min(axis=1), "max": wave.max(axis=1)}, "quality": quality}

def feature_slice(feature, key, start, end):
    time = np.asarray(feature["time_s"])
    values = np.asarray([np.nan if x is None else x for x in feature[key]], dtype=float)
    return values[(time>=start)&(time<=end)]

def robust_range(values):
    values = np.asarray(values, float)
    values = values[np.isfinite(values)]
    return float(np.percentile(values,90)-np.percentile(values,10)) if len(values) else None

def display_features(features):
    # 50 Hz pitch/energy (including null gaps); STFT is diagnostic export only.
    return jsonable({"duration_s": features["duration_s"], "quality": features["quality"],
        "waveform": features["waveform"],
        "pitch": {k: (v[::2] if isinstance(v, (np.ndarray,list)) else v) for k,v in features["pitch"].items()},
        "spectral": {k: np.asarray(v)[::2] for k,v in features["spectral"].items()
                     if k in ("time_s","energy_dbfs","energy_relative_db","speech_mask")}})
