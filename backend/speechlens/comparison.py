import numpy as np
from .features import feature_slice, robust_range
from .text import phrase_ids
from .config import PIPELINE

def summarize(ids, alignment, features):
    words = [alignment["words"][i] for i in ids]
    valid = [w for w in words if w["start_s"] is not None]
    coverage = len(valid)/len(words)
    if not valid:
        return {"eligible": False, "coverage": coverage, "interval_s": None}
    a, b = valid[0]["start_s"], valid[-1]["end_s"]
    T = b-a
    pitch = feature_slice(features["pitch"], "semitones", a,b)
    energy = feature_slice(features["spectral"], "energy_relative_db", a,b)
    mask = feature_slice(features["spectral"], "speech_mask", a,b).astype(bool)
    voiced = pitch[np.isfinite(pitch)]
    slope = float(np.polyfit(np.linspace(a,b,len(pitch))[np.isfinite(pitch)],voiced,1)[0]) if len(voiced)>2 else None
    active = float(np.sum(mask)*.01)
    return {"eligible": coverage>=PIPELINE["minimum_alignment_coverage"] and T>.2,
            "coverage": coverage, "interval_s": [a,b], "word_count": len(ids), "elapsed_s": T,
            "wpm": 60*len(ids)/T if T>0 else None, "speech_active_s": active,
            "articulation_wpm": 60*len(ids)/active if active>0 else None,
            "pitch_range_st": robust_range(pitch), "voiced_frames": len(voiced), "pitch_slope_st_per_s": slope,
            "energy_range_db": robust_range(energy[mask]) if mask.any() else None,
            "spectral_centroid_hz": float(np.mean(feature_slice(features["spectral"],"centroid_hz",a,b))),
            "spectral_flatness": float(np.mean(feature_slice(features["spectral"],"flatness",a,b))),
            "mean_alignment_confidence": float(np.mean([w["confidence"] for w in valid]))}

def compare(transcript, pa, pf, ra=None, rf=None):
    phrases = []
    for i,ids in enumerate(phrase_ids(transcript)):
        phrases.append({"id": i, "token_ids": ids, "quote": " ".join(transcript["tokens"][j]["text"] for j in ids),
                        "participant": summarize(ids,pa,pf), "reference": summarize(ids,ra,rf) if ra else None})
    boundaries = []
    for i in range(len(transcript["tokens"])-1):
        entry = {"id": i, "token_ids": [i,i+1]}
        for role, alignment, feat in [("participant",pa,pf),("reference",ra,rf)]:
            if alignment is None:
                entry[role] = None
                continue
            left,right = alignment["words"][i:i+2]
            if left["end_s"] is None or right["start_s"] is None:
                entry[role] = {"eligible":False}
                continue
            a,b = left["end_s"], right["start_s"]
            silence = feature_slice(feat["spectral"],"speech_mask",a,b)
            entry[role] = {"eligible": True, "pause_s": max(0,b-a), "interval_s":[a,max(a,b)],
                           "vad_silence_fraction": float(1-np.mean(silence)) if len(silence) else 1.0}
        boundaries.append(entry)
    all_ids = [t["id"] for t in transcript["tokens"]]
    return {"phrases": phrases, "boundaries": boundaries,
            "global": {"participant":summarize(all_ids,pa,pf), "reference":summarize(all_ids,ra,rf) if ra else None}}
