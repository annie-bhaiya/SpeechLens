"""Deterministic sample-count maps. Supports are intervention labels, not human truth."""
import numpy as np
import librosa
from scipy.signal import butter, sosfilt

SR=16000

def map_time(mapping,time_s,side="right"):
    segments=[s for s in mapping if s["source_end_s"]>s["source_start_s"]]
    candidates=[s for s in segments if s["source_start_s"]<=time_s<=s["source_end_s"]]
    if not candidates:
        raise ValueError("Time outside source mapping")
    s=candidates[-1] if side=="right" else candidates[0]
    if s["kind"]=="deletion":
        return None
    fraction=(time_s-s["source_start_s"])/(s["source_end_s"]-s["source_start_s"])
    return s["target_start_s"]+fraction*(s["target_end_s"]-s["target_start_s"])

def world_resynthesis(y,pitch_multiplier=1.0):
    import pyworld as pw
    x=y.astype(np.float64)
    f0,t=pw.harvest(x,SR,f0_floor=50,f0_ceil=600,frame_period=10)
    sp=pw.cheaptrick(x,f0,t,SR)
    ap=pw.d4c(x,f0,t,SR)
    voiced=f0>0
    if voiced.any():
        median=np.median(f0[voiced])
        f0[voiced]=median*2**(np.log2(f0[voiced]/median)*pitch_multiplier)
    result=pw.synthesize(f0,sp,ap,SR,frame_period=10).astype(np.float32)
    return np.pad(result,(0,max(0,len(y)-len(result))))[:len(y)]

def render_segment(segment,edit,rng):
    kind=edit["kind"]
    if kind=="stretch":
        result=librosa.effects.time_stretch(segment,rate=1/edit["duration_multiplier"])
    elif kind=="insertion":
        return np.zeros(round(edit["duration_s"]*SR),np.float32)
    elif kind=="deletion":
        return np.zeros(0,np.float32)
    elif kind in ("pitch","world_sham"):
        result=world_resynthesis(segment,edit.get("pitch_range_multiplier",1.0))
    elif kind=="energy":
        energy=librosa.feature.rms(y=segment,frame_length=400,hop_length=160,center=True)[0]
        envelope=np.interp(np.arange(len(segment)),np.arange(len(energy))*160,energy)
        target=np.median(envelope[envelope>.005]) if (envelope>.005).any() else .02
        gain=np.clip((target/(envelope+1e-8))**edit["flatten_amount"],.2,4)
        result=segment*gain
    elif kind=="lowpass_proxy":
        result=sosfilt(butter(6,edit["cutoff_hz"],fs=SR,output="sos"),segment).astype(np.float32)
    elif kind=="noise_proxy":
        rms=np.sqrt(np.mean(segment**2))
        result=segment+rng.normal(0,rms*10**(-edit["snr_db"]/20),len(segment))
    elif kind=="gain":
        result=segment*10**(edit["gain_db"]/20)
    else:
        raise ValueError("Unknown transform")
    # Blend actual 20 ms edges against unchanged/time-indexed source to reduce discontinuities.
    fade=min(round(.02*SR),len(result)//2,len(segment)//2)
    if fade:
        weight=np.linspace(0,1,fade)
        result[:fade]=segment[:fade]*(1-weight)+result[:fade]*weight
        result[-fade:]=result[-fade:]*(1-weight)+segment[-fade:]*weight
    return np.asarray(result,np.float32)

def apply_edits(y,edits,seed=2026):
    rng=np.random.default_rng(seed)
    output,mapping,supports=[],[],[]
    source_cursor,target_cursor=0,0
    for edit in sorted(edits,key=lambda e:(e["start_s"],e["end_s"])):
        a,b=round(edit["start_s"]*SR),round(edit["end_s"]*SR)
        if not source_cursor<=a<=b<=len(y):
            raise ValueError("Edits overlap, are unsorted, or exceed recording")
        if a>source_cursor:
            chunk=y[source_cursor:a]
            output.append(chunk)
            mapping.append({"kind":"identity","source_start_s":source_cursor/SR,"source_end_s":a/SR,
                            "target_start_s":target_cursor/SR,"target_end_s":(target_cursor+len(chunk))/SR})
            target_cursor+=len(chunk)
        result=render_segment(y[a:b],edit,rng)
        output.append(result)
        segment={"kind":edit["kind"],"source_start_s":a/SR,"source_end_s":b/SR,
                 "target_start_s":target_cursor/SR,"target_end_s":(target_cursor+len(result))/SR}
        mapping.append(segment)
        supports.append({**segment,"family":edit["family"],"severity":edit.get("severity",0),
                         "token_ids":edit.get("token_ids",[]),"parameters":edit,
                         "fade_samples":min(round(.02*SR),len(result)//2,(b-a)//2),
                         "label_kind":"transformation_support","perceptual_interval_s":None,
                         "review_status":"pending","reviewers":[],"uncertainty":"Not independently perceptually annotated"})
        source_cursor=b
        target_cursor+=len(result)
    if source_cursor<len(y):
        chunk=y[source_cursor:]
        output.append(chunk)
        mapping.append({"kind":"identity","source_start_s":source_cursor/SR,"source_end_s":len(y)/SR,
                        "target_start_s":target_cursor/SR,"target_end_s":(target_cursor+len(chunk))/SR})
    return np.concatenate(output),mapping,supports

def propagate_words(words,mapping):
    output=[]
    for word in words:
        copy=dict(word)
        if word["start_s"] is not None:
            copy["start_s"]=map_time(mapping,word["start_s"],"right")
            copy["end_s"]=map_time(mapping,word["end_s"],"left")
            if copy["start_s"] is None or copy["end_s"] is None:
                copy["start_s"],copy["end_s"]=None,None
        copy["source"]="propagated_transformation_map_not_independent_alignment"
        output.append(copy)
    return output
