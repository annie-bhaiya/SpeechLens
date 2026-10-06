import numpy as np
import pytest
from backend.speechlens.features import extract,frames,robust_range,speech_mask
from backend.speechlens.transforms import apply_edits,map_time,propagate_words
from backend.speechlens.scoring import aggregate
from backend.speechlens.evaluation import tiou,match_events
from backend.speechlens.text import canonicalize,phrase_ids
from backend.speechlens.utils import object_hash,jsonable
from backend.speechlens.alignment import ctc_path

def test_known_sine_frequency_rms_and_stft_clock():
    y=.2*np.sin(2*np.pi*220*np.arange(32000)/16000).astype(np.float32)
    f=extract(y)
    assert abs(f["pitch"]["median_hz"]-220)<2
    assert np.median(f["spectral"]["rms"])==pytest.approx(.2/np.sqrt(2),rel=.01)
    assert f["spectral"]["time_s"][0]==.0125
    assert np.diff(f["spectral"]["time_s"])[0]==pytest.approx(.01)
    assert f["spectral"]["mfcc"].shape[1]==13
    assert len(f["spectral"]["stft_frequency_hz"])==257

def test_silence_masks_and_missing_pitch():
    f=extract(np.zeros(16000,np.float32))
    assert not np.any(f["pitch"]["voiced_mask"])
    assert np.isnan(f["pitch"]["f0_hz"]).all()
    assert not speech_mask(np.zeros(16000,np.float32)).any()
    assert robust_range([None,np.nan]) is None
    assert jsonable([np.nan,np.inf])==[None,None]

def test_insertion_and_deletion_map_native_samples():
    y=np.ones(48000,np.float32)*.1
    result,mapping,support=apply_edits(y,[{"start_s":1,"end_s":1,"kind":"insertion","duration_s":.5,"family":"pauses"}])
    assert len(result)==len(y)+8000
    assert map_time(mapping,.5)==.5
    assert map_time(mapping,1.5)==2
    assert support[0]["target_end_s"]-support[0]["target_start_s"]==.5
    words=[{"id":0,"text":"one","start_s":.5,"end_s":1},{"id":1,"text":"two","start_s":1,"end_s":1.5}]
    mapped=propagate_words(words,mapping)
    assert mapped[0]["end_s"]==1
    assert mapped[1]["start_s"]==1.5
    deleted,dm,_=apply_edits(y,[{"start_s":1,"end_s":2,"kind":"deletion","family":"pauses"}])
    assert len(deleted)==32000
    assert map_time(dm,1.5) is None
    assert map_time(dm,2.5)==1.5

def test_duration_map_is_computed_from_rendered_sample_counts():
    y=np.sin(2*np.pi*220*np.arange(48000)/16000).astype(np.float32)*.1
    result,mapping,_=apply_edits(y,[{"start_s":1,"end_s":2,"kind":"stretch","duration_multiplier":1.35,"family":"pace"}])
    assert len(result)==53600
    assert map_time(mapping,1.5)==pytest.approx(1.675)
    assert map_time(mapping,2.5)==pytest.approx(2.85)

def test_score_exposure_overlap_and_missing_evidence():
    units={k:[] for k in ["pacing","pauses","intonation","energy","clarity"]}
    assert aggregate(units)["total"] is None
    assert aggregate(units)["categories"]["pacing"]["score"] is None
    row={"id":1,"exposure":3,"eligible":True,"severity":.4}
    units["pacing"]=[row,{**row,"severity":.6}]
    scores=aggregate(units)
    assert scores["categories"]["pacing"]["score"]==40
    assert scores["total"] is None  # surviving category must not hide missing coverage
    for category in ["pauses","intonation","energy"]:
        units[category]=[{"id":1,"exposure":1,"eligible":True,"severity":0}]
    scores=aggregate(units)
    assert 0<=scores["total"]<=100
    assert "clarity" not in scores["included_weights"]
    assert sum(scores["included_weights"].values())==pytest.approx(1)

def test_ctc_repeated_letters_need_blanks():
    lp=np.log(np.array([[.1,.8,.1],[.8,.1,.1],[.1,.8,.1],[.8,.1,.1]]))
    path=ctc_path(lp,[1,1],blank=0)
    assert 1 in path and 3 in path
    assert path.tolist()==[1,2,3,4]

def test_matching_is_one_to_one_and_type_gated():
    p=[{"type":"pace","interval_s":[0,2]},{"type":"pace","interval_s":[0,2]},{"type":"energy","interval_s":[5,7]}]
    t=[{"type":"pace","interval_s":[0,2]},{"type":"intonation","interval_s":[5,7]}]
    counts=match_events(p,t)
    assert (counts["tp"],counts["fp"],counts["fn"])==(1,2,1)
    assert tiou([0,2],[1,3])==pytest.approx(1/3)

def test_normalized_text_identity_and_cache_invalidation():
    assert canonicalize("We have 12 apples!")["sha256"]==canonicalize("we have twelve apples.")["sha256"]
    assert object_hash({"audio":"a","config":1})!=object_hash({"audio":"a","config":2})
    assert object_hash({"audio":"a","config":1})!=object_hash({"audio":"b","config":1})
    assert canonicalize("go go")["tokens"][1]["id"]==1
    with pytest.raises(ValueError):canonicalize("hola",language="es")
    with pytest.raises(ValueError):canonicalize("你好")
