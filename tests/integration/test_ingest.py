import numpy as np
import soundfile as sf
import pytest
from backend.speechlens.ingest import decode

def test_corrupted_short_silent_and_unsupported_audio(tmp_path):
    for filename,y in [('silent.wav',np.zeros(16000)),('short.wav',np.ones(8000)*.1)]:
        p=tmp_path/filename
        sf.write(p,y,16000)
        with pytest.raises(ValueError):decode(p)
    bad=tmp_path/'corrupt.wav'
    bad.write_bytes(b'not an audio file')
    with pytest.raises(ValueError):decode(bad)
    txt=tmp_path/'speech.txt'
    txt.write_text('speech')
    with pytest.raises(ValueError):decode(txt)

def test_downmix_resample_preserves_duration_and_does_not_normalize(tmp_path):
    y=np.sin(2*np.pi*220*np.arange(44100)/44100)*.1
    path=tmp_path/'stereo.wav'
    sf.write(path,np.column_stack([y,y]),44100,subtype='FLOAT')
    result,metadata=decode(path,tmp_path/'canonical.wav')
    assert len(result)==16000
    assert metadata['original_channels']==2
    assert np.max(result)==pytest.approx(.1,abs=.002)

def test_clipping_is_preserved_as_evidence(tmp_path):
    y=np.clip(2*np.sin(2*np.pi*220*np.arange(16000)/16000),-1,1)
    path=tmp_path/'clip.wav'
    sf.write(path,y,16000,subtype='FLOAT')
    result,metadata=decode(path)
    assert metadata['clipped_fraction']>.5
