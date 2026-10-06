import copy
import pytest
from backend.speechlens.detectors import detect,hysteresis_intervals
from backend.speechlens.config import DETECTORS

def example():
    unit={"eligible":True,"interval_s":[1,5],"elapsed_s":4,"wpm":120,"pitch_range_st":5,"energy_range_db":8,"voiced_frames":100}
    phrase={"id":0,"token_ids":list(range(8)),"quote":"these are eight exact words in this phrase","participant":copy.deepcopy(unit),"reference":copy.deepcopy(unit)}
    comparison={"phrases":[phrase],"boundaries":[]}
    return comparison,{"tokens":[{"text":"word"} for _ in range(8)]},{"duration_s":10,"quality":{"clipped_fraction":0}}

def test_local_pace_detected_from_native_elapsed_duration():
    c,t,f=example()
    c["phrases"][0]["participant"].update(interval_s=[1,3],elapsed_s=2,wpm=240)
    events,_=detect(c,t,f)
    pace=next(e for e in events if e["type"]=="pace")
    assert pace["participant_interval_s"]==[1,3]
    assert pace["reference_interval_s"]==[1,5]
    assert pace["measurements"]["duration_ratio"]==.5
    assert pace["delta"]<0
    assert "Allow more" in pace["suggestion"]

def test_flat_reference_cannot_support_monotony_accusation():
    c,t,f=example()
    c["phrases"][0]["reference"]["pitch_range_st"]=.3
    c["phrases"][0]["participant"]["pitch_range_st"]=.1
    events,units=detect(c,t,f)
    assert not any(e["type"]=="intonation" for e in events)
    assert units["intonation"][0]["eligible"] is False

def test_weak_alignment_and_voicing_abstain():
    c,t,f=example()
    c["phrases"][0]["participant"]["eligible"]=False
    events,units=detect(c,t,f)
    assert not events
    assert not any(u["eligible"] for rows in units.values() for u in rows)
    c["phrases"][0]["participant"]["eligible"]=True
    c["phrases"][0]["participant"].update(voiced_frames=2,pitch_range_st=.1)
    events,units=detect(c,t,f)
    assert not any(e["type"]=="intonation" for e in events)

def test_pause_requires_silence_support():
    c,t,f=example()
    c["boundaries"]=[{"id":0,"token_ids":[0,1],"participant":{"eligible":True,"pause_s":2,"interval_s":[4,6],"vad_silence_fraction":.95},"reference":{"eligible":True,"pause_s":.2,"interval_s":[4,4.2],"vad_silence_fraction":.95}}]
    events,_=detect(c,t,f)
    assert any(e["type"]=="pauses" for e in events)
    c["boundaries"][0]["participant"]["vad_silence_fraction"]=.2
    events,_=detect(c,t,f)
    assert not any(e["type"]=="pauses" for e in events)

def test_frame_hysteresis_localizes_and_merges_only_small_gaps():
    import numpy as np
    times=np.arange(300)*.01+.0125
    values=np.zeros(300)
    values[100:180]=.2
    intervals=hysteresis_intervals(times,values)
    assert len(intervals)==1
    assert intervals[0][0]==pytest.approx(1,abs=.1)
    assert intervals[0][1]==pytest.approx(1.8,abs=.1)
