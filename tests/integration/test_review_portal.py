"""Workflow tests use generated signal fixtures and never count as real human reviews."""
import io
import json
import zipfile

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from backend.app import api, review, storage, jobs
from backend.speechlens.text import canonicalize

@pytest.fixture
def client(tmp_path,monkeypatch):
    root=tmp_path/'repo';root.mkdir()
    for name in ['manifests','transcripts','alignments','audio']:(root/'data'/name).mkdir(parents=True)
    text='These are intended words.'
    tokens=canonicalize(text)
    (root/'data/transcripts/text.json').write_text(json.dumps({'display_text':text}))
    rows=[]
    for name,split in [('ref','train'),('variant','train'),('other','test')]:
        sf.write(root/f'data/audio/{name}.wav',np.sin(np.arange(48000)*.05)*.1,16000)
        words=[{'id':w['id'],'text':w['text'],'start_s':i*.5,'end_s':i*.5+.4} for i,w in enumerate(tokens['tokens'])]
        (root/f'data/alignments/{name}.json').write_text(json.dumps({'words':words}))
        rows.append({'recording_id':name,'reference_id':name if name!='variant' else 'ref','transcript_id':'text','transcript_sha256':tokens['sha256'],
                     'audio_path':f'audio/{name}.wav','alignment_path':f'alignments/{name}.json','duration_s':3,
                     'generation_method':'reference' if name!='variant' else 'hidden_recipe','severity_label':4,'split':split})
    (root/'data/manifests/recordings.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
    for module in [review,storage,jobs,api]:monkeypatch.setattr(module,'STORAGE',tmp_path/'storage')
    monkeypatch.setattr(review,'ROOT',root)
    monkeypatch.setattr(jobs.worker,'start',storage.initialize)
    monkeypatch.setattr(jobs.worker,'stop',lambda:None)
    with TestClient(api.app) as c:yield c

def login(c,alias='reviewer_one',role='reviewer'):
    body={'alias':alias,'password':'test-passphrase-only','role':role,'consent':True}
    if role=='coordinator':body['coordinator_code']=review.coordinator_key()
    r=c.post('/api/review/session',json=body);assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def task(c,h,index=1):
    rows=c.get('/api/review/tasks',headers=h).json()['tasks']
    return rows[index]['id']

def annotation(c,h,tid,full=True):
    d=c.get(f'/api/review/tasks/{tid}',headers=h).json()
    return {'scope':'full_annotation' if full else 'acceptance','decision':'accept','notes':'Signal fixture for API testing, not a human judgment.',
            'baseline_rationale':'Fixture baseline accepted only inside isolated tests.','transcript':d['transcript'],
            'words':[{**w,'reviewed':True} for w in d['words']], 'events':[],
            'ratings':{k:0 for k in review.KINDS},'checks':{k:True for k in review.Checks.model_fields},'revision':d['revision'],'submit':True}

def test_blinding_session_isolation_and_locked_originals(client):
    one=login(client);tid=task(client,one)
    response=client.get('/api/review/tasks',headers=one)
    assert 'hidden_recipe' not in response.text and 'severity_label' not in response.text and 'variant' not in response.text
    assert client.get(f'/api/review/tasks/{tid}/audio/participant').status_code==401
    assert client.get(f'/api/review/tasks/{tid}/audio/participant',headers={**one,'Range':'bytes=0-99'}).status_code==206
    body=annotation(client,one,tid)
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=one,json=body).status_code==200
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=one,json=body).status_code==409
    two=login(client,'reviewer_two')
    assert client.get(f'/api/review/tasks/{tid}',headers=two).json()['draft'] is None
    assert client.get(f'/api/review/tasks/{tid}/adjudication',headers=one).status_code==403
    coord=login(client,'coordinator','coordinator')
    assert client.get(f'/api/review/tasks/{tid}/adjudication',headers=coord).status_code==409
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=two,json=annotation(client,two,tid)).status_code==200
    originals=client.get(f'/api/review/tasks/{tid}/adjudication',headers=coord).json()['reviews']
    assert {r['reviewer_id'] for r in originals}=={'reviewer_one','reviewer_two'}
    payload={'reviewers':['reviewer_one','reviewer_two'],'resolution_notes':'Checked both independent test fixture annotations.',
             'independent_humans_confirmed':True,'result':annotation(client,one,tid)}
    assert client.post(f'/api/review/tasks/{tid}/adjudication',headers=coord,json=payload).status_code==200
    assert client.post(f'/api/review/tasks/{tid}/adjudication',headers=coord,json=payload).status_code==409
    for header,expected in [(one,1),(coord,2)]:
        with zipfile.ZipFile(io.BytesIO(client.get('/api/review/export',headers=header).content)) as z:
            assert len([n for n in z.namelist() if n.startswith('independent/')])==expected
            assert ('private_task_mapping.json' in z.namelist())==(header==coord)

def test_draft_revision_interval_and_completion_validation(client):
    h=login(client);tid=task(client,h)
    body=annotation(client,h,tid);body['submit']=False
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=body).json()['revision']==1
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=body).status_code==409
    body['revision']=1;body['submit']=True;body['checks']['independent']=False
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=body).status_code==422
    body['checks']['independent']=True;body['words'][0]['reviewed']=False
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=body).status_code==422
    body['words'][0]['reviewed']=True;body['words'][0]['end_s']=99
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=body).status_code==422
    body['words'][0]['end_s']=.4
    body['events']=[{'id':'e1','type':'pace','severity':1,'start_s':1,'end_s':4,'notes':'out of bounds'}]
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=body).status_code==422
    body['events'][0]['end_s']=2;body['events'][0]['token_ids']=[100]
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=body).status_code==422
    body['events'][0]['token_ids']=[2]
    body['checks']['no_flaws_confirmed']=False
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=body).status_code==200

def test_acceptance_only_does_not_unlock_adjudication(client):
    for alias in ['reviewer_one','reviewer_two']:
        h=login(client,alias);tid=task(client,h)
        assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=annotation(client,h,tid,False)).status_code==200
    coord=login(client,'coordinator','coordinator')
    state=client.get('/api/review/coordinator',headers=coord).json()['tasks'][1]
    assert state['submitted_reviews']==2 and state['independent_full_reviews']==0 and not state['ready']

def test_supplementary_annotation_preserves_final_acceptance(client):
    h=login(client);tid=task(client,h)
    original=annotation(client,h,tid,False)
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=original).status_code==200
    full=annotation(client,h,tid,True);full['submit']=False
    assert client.put(f'/api/review/tasks/{tid}/submission',headers=h,json=full).status_code==200
    with zipfile.ZipFile(io.BytesIO(client.get('/api/review/export',headers=h).content)) as z:
        original_file=next(n for n in z.namelist() if n.startswith('acceptance_originals/'))
        assert json.loads(z.read(original_file))['scope']=='acceptance'
        new_file=next(n for n in z.namelist() if n.startswith('independent/'))
        assert json.loads(z.read(new_file))['scope']=='full_annotation'
        assert json.loads(z.read(new_file))['status']=='draft'

def test_consented_performance_split_guard_and_withdrawal(client):
    h=login(client);login(client,'other_reviewer')
    signal=io.BytesIO();sf.write(signal,np.sin(np.arange(48000)*.05)*.1,16000,format='WAV')
    values={'reference_id':'ref','speaker_id':'speaker_one','transcript':'These are intended words.',
            'intent':'acceptable','conditions':'Synthetic signal fixture in an isolated test.',
            'adult_consent':'true','research_consent':'true','publication_consent':'false','readback_confirmed':'true'}
    def upload(**changes):return client.post('/api/review/performances',headers=h,data={**values,**changes},files={'audio':('test.wav',signal.getvalue(),'audio/wav')})
    assert upload(research_consent='false').status_code==422
    assert upload(readback_confirmed='false').status_code==422
    assert upload(transcript='Wrong intended words.').status_code==422
    r=upload();assert r.status_code==201,r.text
    tid=r.json()['task_id'];assert not r.json()['release_eligible']
    assert upload(reference_id='other').status_code==422
    d=client.get(f'/api/review/tasks/{tid}',headers=h).json()
    assert all(w['start_s'] is None for w in d['words'])
    meta=client.get('/api/review/performances',headers=h).json()[0]
    assert not meta['consent']['public_redistribution'] and meta['split']=='train'
    other=login(client,'other_reviewer')
    assert client.get('/api/review/performances',headers=other).json()==[]
    assert client.delete(f'/api/review/performances/{tid}',headers=other).status_code==403
    assert client.delete(f'/api/review/performances/{tid}',headers=h).status_code==204
    assert client.get(f'/api/review/tasks/{tid}',headers=h).status_code==404
    assert not (review.home()/'performances'/tid).exists()

def test_identity_and_coordinator_authentication(client):
    assert client.post('/api/review/session',json={'alias':'unsafe/alias','password':'long-password','consent':True}).status_code==422
    login(client)
    assert client.post('/api/review/session',json={'alias':'reviewer_one','password':'different-passphrase','consent':True}).status_code==401
    assert client.post('/api/review/session',json={'alias':'coordinator','password':'long-password','role':'coordinator','coordinator_code':'wrong','consent':True}).status_code==403
    h=login(client)
    assert client.delete('/api/review/session',headers=h).status_code==204
    assert client.get('/api/review/tasks',headers=h).status_code==401

def test_assignment_is_private_and_sets_requested_scope(client):
    first=login(client);second=login(client,'reviewer_two');coord=login(client,'coordinator','coordinator')
    tid=task(client,first)
    body={'task_ids':[tid],'reviewer_ids':['reviewer_one','reviewer_two'],'scope':'full_annotation'}
    assert client.post('/api/review/assignments',headers=first,json=body).status_code==403
    assert client.post('/api/review/assignments',headers=coord,json=body).status_code==200
    for h in [first,second]:
        assert client.get(f'/api/review/tasks/{tid}',headers=h).json()['assigned_scope']=='full_annotation'
        response=client.get('/api/review/tasks',headers=h)
        row=next(t for t in response.json()['tasks'] if t['id']==tid)
        assert row['assigned_scope']=='full_annotation' and 'hidden_recipe' not in response.text
    body['reviewer_ids']=['reviewer_one','missing_account']
    assert client.post('/api/review/assignments',headers=coord,json=body).status_code==422
