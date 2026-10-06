import math
import numpy as np
from .config import DETECTORS as D
from .utils import object_hash
from .explanations import explain

def severity(value, warn, severe):
    return float(np.clip((value-warn)/(severe-warn),0,1))

def hysteresis_intervals(times,values,onset=.04,offset=.01,minimum_s=.15,merge_gap_s=.1):
    from scipy.ndimage import median_filter
    times=np.asarray(times,float)
    values=median_filter(np.asarray(values,float),size=15,mode="nearest")
    spans=[]
    start=None
    for t,value in zip(times,values):
        if start is None and value>=onset:
            start=max(0,float(t)-.0125)
        elif start is not None and value<offset:
            end=float(t)+.0125
            if end-start>=minimum_s:
                spans.append([start,end])
            start=None
    if start is not None and len(times) and times[-1]+.0125-start>=minimum_s:
        spans.append([start,float(times[-1]+.0125)])
    merged=[]
    for a,b in spans:
        if merged and a-merged[-1][1]<=merge_gap_s:
            merged[-1][1]=b
        else:
            merged.append([a,b])
    return merged

def event(kind, unit, p, r, observed, reference, delta, units, rule, amount):
    value = {"id": object_hash([kind,unit["id"],p["interval_s"],rule])[:16], "type":kind,
        "severity":amount, "severity_level":min(4,max(1,int(math.ceil(amount*4)))),
        "participant_interval_s":p["interval_s"], "reference_interval_s":r["interval_s"] if r else None,
        "token_ids":unit["token_ids"], "quote":unit.get("quote",""),
        "measurements":{"participant":observed,"reference":reference,"units":units}, "delta":delta,
        "rule_id":rule, "threshold_version":D["version"], "confidence":"heuristic_uncalibrated",
        "confidence_rationale":"Independent CTC alignment and sufficient acoustic support; thresholds have no human calibration.",
        "boundary_uncertainty_s":.1, "context":"Reference is one acceptable rendition; stylistic alternatives need review."}
    return explain(value)

def detect(comparison, transcript, features, paired=True):
    events, units = [], {k:[] for k in ["pacing","pauses","intonation","energy","clarity"]}
    for phrase in comparison["phrases"]:
        p,r = phrase["participant"],phrase["reference"]
        exposure = max(.1, r.get("elapsed_s",.1)) if r else 1.0
        eligible = paired and p["eligible"] and r["eligible"] and len(phrase["token_ids"])>=D["minimum_phrase_words"]
        amount = 0.0
        if eligible:
            delta = math.log(p["elapsed_s"]/r["elapsed_s"])
            amount = severity(abs(delta),D["pace_log_warn"],D["pace_log_severe"])
            if amount>0:
                e = event("pace",phrase,p,r,p["wpm"],r["wpm"],delta,"words/minute","pace.log_duration.v1",amount)
                e["formula"] = "delta=ln(participant_elapsed/reference_elapsed); severity=clip((abs(delta)-warn)/(severe-warn),0,1)"
                e["measurements"].update({"participant_elapsed_s":p["elapsed_s"],"reference_elapsed_s":r["elapsed_s"],
                                           "duration_ratio":p["elapsed_s"]/r["elapsed_s"]})
                e["thresholds"]={"warn_log_ratio":D["pace_log_warn"],"severe_log_ratio":D["pace_log_severe"]}
                events.append(e)
        units["pacing"].append({"id":phrase["id"],"exposure":exposure,"eligible":eligible,"severity":amount})
        for category, key, minimum in [("intonation","pitch_range_st",D["reference_pitch_range_min_st"]),
                                        ("energy","energy_range_db",D["reference_energy_range_min_db"])]:
            enough = eligible and p.get(key) is not None and r.get(key) is not None and r[key]>=minimum
            if category=="intonation":
                enough = enough and min(p.get("voiced_frames",0),r.get("voiced_frames",0))>=D["minimum_voiced_frames"]
            amount = 0.0
            prefix = "pitch" if category=="intonation" else "energy"
            if enough:
                ratio = p[key]/(r[key]+1e-9)
                amount = severity(-ratio,-D[prefix+"_ratio_warn"],-D[prefix+"_ratio_severe"])
                if amount>0:
                    e = event(category,phrase,p,r,p[key],r[key],p[key]-r[key],"semitones" if category=="intonation" else "relative dB",
                              category+".range_ratio.v1",amount)
                    e["formula"]="R=Q90-Q10; ratio=R_participant/R_reference; severity=clip((warn-ratio)/(warn-severe),0,1)"
                    e["thresholds"]={"warn_ratio":D[prefix+"_ratio_warn"],"severe_ratio":D[prefix+"_ratio_severe"],"reference_minimum":minimum}
                    e["measurements"]["range_ratio"]=ratio
                    events.append(e)
            units[category].append({"id":phrase["id"],"exposure":exposure,"eligible":bool(enough),"severity":amount})
        if eligible and p.get("spectral_centroid_hz") is not None and r.get("spectral_centroid_hz",0)>500:
            ratio=p["spectral_centroid_hz"]/r["spectral_centroid_hz"]
            amount=severity(-ratio,-.55,-.25)
            if amount>0:
                e=event("recording_quality",phrase,p,r,p["spectral_centroid_hz"],r["spectral_centroid_hz"],
                        p["spectral_centroid_hz"]-r["spectral_centroid_hz"],"Hz spectral centroid","quality.spectral_loss_proxy.v1",amount)
                e["formula"]="centroid=sum(f*power)/sum(power); text-matched ratio < 0.55 triggers a diagnostic channel-loss proxy"
                e["thresholds"]={"warn_ratio":.55,"severe_ratio":.25}
                e["context"]="Spectral shape also depends on phonetics, speaker and channel. This diagnostic never penalizes articulation."
                events.append(e)
    for boundary in comparison["boundaries"]:
        p,r = boundary["participant"],boundary["reference"]
        eligible = paired and p and r and p["eligible"] and r["eligible"]
        amount = 0.0
        if eligible:
            delta = p["pause_s"]-r["pause_s"]
            # Only call a gap a pause when the longer gap has actual non-speech support.
            supported = (p if delta>0 else r)["vad_silence_fraction"]>=.65
            amount = severity(abs(delta),D["pause_delta_warn_s"],D["pause_delta_severe_s"]) if supported else 0.0
            if amount>0:
                boundary["quote"]=" / ".join(transcript["tokens"][i]["text"] for i in boundary["token_ids"])
                e = event("pauses",boundary,p,r,p["pause_s"],r["pause_s"],delta,"seconds","pause.native_gap.v1",amount)
                # Deleted pauses have a short but playable participant context interval.
                if e["participant_interval_s"][1]-e["participant_interval_s"][0]<.1:
                    center=e["participant_interval_s"][0]
                    e["participant_interval_s"]=[max(0,center-.15),min(features["duration_s"],center+.15)]
                e["formula"]="delta=participant_gap-reference_gap; gaps confirmed by independent speech VAD"
                e["thresholds"]={"warn_delta_s":D["pause_delta_warn_s"],"severe_delta_s":D["pause_delta_severe_s"]}
                events.append(e)
        units["pauses"].append({"id":boundary["id"],"exposure":1,"eligible":bool(eligible),"severity":amount})
    quality = features["quality"]
    if quality["clipped_fraction"]>.001:
        spectral=features.get("spectral",{})
        spans=hysteresis_intervals(spectral["time_s"],spectral["clipped_fraction"]) if "clipped_fraction" in spectral else [[0,features["duration_s"]]]
        for index,span in enumerate(spans):
            span[1]=min(span[1],features["duration_s"])
            e = event("recording_quality",{"id":-index-1,"token_ids":[],"quote":""}, {"interval_s":span},None,
                      quality["clipped_fraction"],None,quality["clipped_fraction"],"fraction of samples (whole recording)","quality.clipping.v1",0)
            e["formula"]="25 ms frame clipped fraction, 150 ms median filter, 0.04/0.01 onset/offset hysteresis, minimum 150 ms"
            e["thresholds"]={"warn_file_clipped_fraction":.001,"frame_onset":.04,"frame_offset":.01}
            events.append(e)
    return events,units
