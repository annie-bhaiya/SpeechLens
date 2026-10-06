import io
import time
import pytest
from fastapi.testclient import TestClient
from backend.app import storage
from backend.app import jobs
from backend.app import api as api_module
from backend.speechlens.config import PIPELINE

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,"STORAGE",tmp_path)
    monkeypatch.setattr(jobs,"STORAGE",tmp_path)
    monkeypatch.setattr(api_module,"STORAGE",tmp_path)
    # Validation tests don't launch inference subprocesses; worker durability tested independently.
    monkeypatch.setattr(jobs.worker,"start",storage.initialize)
    monkeypatch.setattr(jobs.worker,"stop",lambda:None)
    with TestClient(api_module.app) as client:
        yield client

def request(client,**data):
    return client.post('/api/evaluations',data={"transcript":"These are the intended words.","single_speaker":"true",**data},files={"participant":("speech.wav",b"audio input pending decode","audio/wav")})

def test_language_speaker_and_text_validation(client):
    assert request(client,language='fr').status_code==422
    assert request(client,single_speaker='false').status_code==422
    assert request(client,transcript='').status_code==422
    assert request(client,preset='unknown').status_code==422
    assert request(client,weights='{"pacing":1}').status_code==422

def test_opaque_jobs_safe_files_and_delete(client,tmp_path):
    response=client.post('/api/evaluations',data={"transcript":"intended words","single_speaker":"true"},files={"participant":("../../escape.wav",b"data","audio/wav")})
    assert response.status_code==202
    job_id=response.json()['id']
    assert len(job_id)==32
    assert (tmp_path/'jobs'/job_id/'participant_original.wav').exists()
    assert not (tmp_path/'escape.wav').exists()
    assert client.get(f'/api/evaluations/{job_id}/result').status_code==409
    assert client.get('/api/evaluations/not-a-job').status_code==404
    assert client.delete(f'/api/evaluations/{job_id}').status_code==204
    assert not (tmp_path/'jobs'/job_id).exists()
    assert client.get(f'/api/evaluations/{job_id}').status_code==404

def test_empty_unsupported_and_oversized_upload(client,monkeypatch):
    data={"transcript":"intended words","single_speaker":"true"}
    assert client.post('/api/evaluations',data=data,files={"participant":('a.exe',b'a')}).status_code==415
    assert client.post('/api/evaluations',data=data,files={"participant":('a.wav',b'')}).status_code==422
    monkeypatch.setitem(PIPELINE,'max_upload_bytes',8)
    assert client.post('/api/evaluations',data=data,files={"participant":('a.wav',b'a'*9)}).status_code==413

def test_durable_interruption_and_retry(client):
    job=storage.create_job({"transcript":"words"})
    claim=storage.claim_job()
    assert claim['id']==job['id']
    storage.initialize()
    recovered=storage.get_job(job['id'])
    assert recovered['status']=='queued'
    storage.claim_job()
    storage.initialize()
    assert storage.get_job(job['id'])['status']=='failed'
    assert client.post(f"/api/evaluations/{job['id']}/retry").status_code==202
    assert storage.get_job(job['id'])['status']=='queued'

def test_queue_bound_is_atomic_and_applies_to_retries(client):
    from concurrent.futures import ThreadPoolExecutor
    def enqueue(_):
        try:
            return storage.create_job({'transcript':'words'})['id']
        except storage.QueueFullError:
            return None
    with ThreadPoolExecutor(max_workers=12) as executor:
        admitted=[j for j in executor.map(enqueue,range(16)) if j]
    assert len(admitted)==10
    assert request(client).status_code==429
    storage.update(admitted[0],status='failed')
    storage.create_job({'transcript':'replacement'})
    assert client.post(f'/api/evaluations/{admitted[0]}/retry').status_code==429

def test_invalid_weight_shapes_are_validation_errors(client):
    for weights in ['[]','{}','["pacing","pauses","intonation","energy","clarity"]','"bad"']:
        assert request(client,weights=weights).status_code==422
    assert client.post('/api/evaluations/'+'a'*32+'/rescore',json={'weights':['pacing']}).status_code==422
