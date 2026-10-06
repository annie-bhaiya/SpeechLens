"""Private human research workflows. No detector/generator labels are returned to reviewers."""
import hashlib
import hmac
import io
import json
import secrets
import shutil
import sqlite3
import time
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import soundfile as sf
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.speechlens.config import ROOT, STORAGE, PIPELINE
from backend.speechlens.ingest import decode, EXTENSIONS
from backend.speechlens.text import canonicalize
from backend.speechlens.utils import object_hash, sha256_file

router = APIRouter(prefix='/api/review', tags=['Human review'])
KINDS = ['pace', 'intonation', 'pauses', 'energy', 'vocal_clarity', 'recording_quality']
CONSENT_VERSION = 'speechlens-human-consent-v1'

def now():
    return datetime.now(timezone.utc).isoformat()

def home():
    path = STORAGE / 'human_review'
    path.mkdir(parents=True, exist_ok=True)
    return path

@contextmanager
def db():
    con = sqlite3.connect(home() / 'reviews.sqlite', timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA foreign_keys=ON')
    try:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS identities (alias TEXT PRIMARY KEY, salt TEXT NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, alias TEXT NOT NULL, role TEXT NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, recording_id TEXT UNIQUE NOT NULL, kind TEXT NOT NULL, metadata TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS submissions (task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            reviewer TEXT NOT NULL, payload TEXT NOT NULL, revision INTEGER NOT NULL, status TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(task_id, reviewer));
        CREATE TABLE IF NOT EXISTS adjudications (task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
            coordinator TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS acceptance_originals (task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            reviewer TEXT NOT NULL, payload TEXT NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(task_id, reviewer));
        CREATE TABLE IF NOT EXISTS assignments (task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            reviewer TEXT NOT NULL REFERENCES identities(alias), scope TEXT NOT NULL, PRIMARY KEY(task_id,reviewer));
        ''')
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def coordinator_key():
    path = home() / 'coordinator-key.txt'
    if not path.exists():
        try:
            with path.open('x', encoding='utf-8') as f:
                f.write(secrets.token_urlsafe(32))
        except FileExistsError:
            pass
    return path.read_text().strip()

def catalog():
    path = ROOT / 'data/manifests/recordings.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines() if line] if path.exists() else []
    with db() as con:
        for row in rows:
            con.execute('INSERT OR IGNORE INTO tasks VALUES (?,?,?,?)',
                        (uuid.uuid4().hex, row['recording_id'], 'public', json.dumps(row)))
    coordinator_key()

def principal(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Sign in to the review portal.')
    digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
    with db() as con:
        row = con.execute('SELECT * FROM sessions WHERE digest=? AND expires>?', (digest, time.time())).fetchone()
    if not row:
        raise HTTPException(401, 'Session expired. Sign in again; saved drafts remain available.')
    return dict(row)

def coordinator(user=Depends(principal)):
    if user['role'] != 'coordinator':
        raise HTTPException(403, 'Coordinator access is required.')
    return user

@router.get('/context')
def context():
    isolated=(ROOT/'tmp').resolve() in STORAGE.resolve().parents
    return {'deployment':'trusted_local_computer','isolated_test_storage':isolated,
            'test_storage_root':str(STORAGE.resolve()) if isolated else None}

class Login(BaseModel):
    alias: str = Field(min_length=3, max_length=48, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(min_length=10, max_length=200)
    role: Literal['reviewer', 'coordinator'] = 'reviewer'
    coordinator_code: str | None = None
    consent: bool = False

@router.post('/session')
def login(body: Login):
    if not body.consent:
        raise HTTPException(422, 'Confirm voluntary participation and pseudonymous storage of your review.')
    if body.role == 'coordinator' and not hmac.compare_digest(body.coordinator_code or '', coordinator_key()):
        raise HTTPException(403, 'Coordinator code is incorrect. Read the local coordinator-key.txt file.')
    catalog()
    alias = body.alias.lower()
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        row = con.execute('SELECT * FROM identities WHERE alias=?', (alias,)).fetchone()
        salt = row['salt'] if row else secrets.token_hex(16)
        password = hashlib.pbkdf2_hmac('sha256', body.password.encode(), bytes.fromhex(salt), 200000).hex()
        if row and not hmac.compare_digest(row['password'], password):
            raise HTTPException(401, 'This reviewer ID already exists. Use its passphrase or choose your own ID.')
        if not row:
            con.execute('INSERT INTO identities VALUES (?,?,?)', (alias, salt, password))
        token = secrets.token_urlsafe(32)
        con.execute('INSERT INTO sessions VALUES (?,?,?,?)',
                    (hashlib.sha256(token.encode()).hexdigest(), alias, body.role, time.time() + 30*86400))
    return {'token': token, 'alias': alias, 'role': body.role, 'expires_in_days': 30}

@router.delete('/session', status_code=204)
def logout(user=Depends(principal)):
    with db() as con:
        con.execute('DELETE FROM sessions WHERE digest=?', (user['digest'],))

def task_row(task_id):
    with db() as con:
        row = con.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Review task not found.')
    return {**dict(row), 'metadata': json.loads(row['metadata'])}

def asset(task, role='participant'):
    row = task['metadata']
    if role not in ['participant', 'reference']:
        raise HTTPException(404, 'Unknown audio role.')
    if role == 'reference':
        with db() as con:
            r = con.execute('SELECT * FROM tasks WHERE recording_id=?', (row['reference_id'],)).fetchone()
        if not r:
            raise HTTPException(404, 'Reference unavailable.')
        return ROOT / 'data' / json.loads(r['metadata'])['audio_path']
    return (home() / 'performances' / task['id'] / 'canonical.wav') if task['kind']=='human' else ROOT / 'data' / row['audio_path']

def text_for(task):
    row = task['metadata']
    return row['transcript'] if task['kind']=='human' else json.loads((ROOT/'data/transcripts'/(row['transcript_id']+'.json')).read_text())['display_text']

def machine_words(task):
    if task['kind']=='human':
        return [{'id':w['id'], 'text':w['text'], 'start_s':None, 'end_s':None, 'missing':False, 'reviewed':False} for w in canonicalize(text_for(task))['tokens']]
    value = json.loads((ROOT/'data'/task['metadata']['alignment_path']).read_text())
    return [{'id':w['id'],'text':w['text'],'start_s':w['start_s'],'end_s':w['end_s'], 'missing':w['start_s'] is None, 'reviewed':False} for w in value['words']]

def public_summary(task, index, saved=None):
    row = task['metadata']
    return {'id':task['id'], 'label':f"{'Human rendition' if task['kind']=='human' else 'Listening task'} {index+1:03d}",
            'duration_s':row['duration_s'], 'kind':task['kind'], 'is_reference':row.get('generation_method')=='reference',
            'own_status':saved['status'] if saved else 'not_started', 'own_scope':json.loads(saved['payload']).get('scope') if saved else None}

@router.get('/tasks')
def tasks(user=Depends(principal)):
    catalog()
    with db() as con:
        rows = con.execute('SELECT * FROM tasks ORDER BY rowid').fetchall()
        saved = {r['task_id']:dict(r) for r in con.execute('SELECT * FROM submissions WHERE reviewer=?',(user['alias'],))}
        submitted = con.execute("SELECT count(*) FROM submissions WHERE status='submitted'").fetchone()[0]
        adjudicated = con.execute('SELECT count(*) FROM adjudications').fetchone()[0]
        assigned={r['task_id']:r['scope'] for r in con.execute('SELECT * FROM assignments WHERE reviewer=?',(user['alias'],))}
    values = [public_summary({**dict(r),'metadata':json.loads(r['metadata'])}, i, saved.get(r['id'])) for i,r in enumerate(rows)]
    for value in values:value['assigned_scope']=assigned.get(value['id'])
    return {'tasks':values, 'summary':{'tasks':len(values),'own_submitted':sum(v['own_status']=='submitted' for v in values),
                                      'independent_submissions':submitted,'adjudicated':adjudicated},
            'blinding':'Generation methods, intended severity, support labels and system predictions are hidden in this portal. Do not consult Dataset explorer while labeling.'}

@router.get('/tasks/{task_id}')
def detail(task_id: str, user=Depends(principal)):
    task = task_row(task_id)
    with db() as con:
        saved = con.execute('SELECT * FROM submissions WHERE task_id=? AND reviewer=?',(task_id,user['alias'])).fetchone()
        assignment=con.execute('SELECT scope FROM assignments WHERE task_id=? AND reviewer=?',(task_id,user['alias'])).fetchone()
    row = task['metadata']
    return {'id':task_id, 'duration_s':row['duration_s'], 'kind':task['kind'], 'is_reference':row.get('generation_method')=='reference',
            'transcript':text_for(task), 'words':machine_words(task), 'draft':json.loads(saved['payload']) if saved else None,
            'revision':saved['revision'] if saved else 0, 'status':saved['status'] if saved else 'not_started',
            'assigned_scope':assignment['scope'] if assignment else None,
            'baseline_instructions':'Check single-speaker/channel quality, intended words, and explain why this is an acceptable public delivery.' if row.get('generation_method')=='reference' else 'Compare with the reference; an acceptable stylistic alternative is not automatically a flaw.'}

@router.get('/tasks/{task_id}/audio/{role}')
def audio(task_id: str, role: str, user=Depends(principal)):
    return FileResponse(asset(task_row(task_id),role),media_type='audio/wav',filename=f'{role}.wav',headers={'Cache-Control':'no-store'})

@router.get('/tasks/{task_id}/waveform')
def waveform(task_id: str, user=Depends(principal)):
    y,sr = sf.read(asset(task_row(task_id)),dtype='float32',always_2d=True)
    y=y.mean(axis=1)
    bins=np.array_split(y, min(240,len(y)))
    return {'duration_s':len(y)/sr,'min':[float(b.min()) for b in bins],'max':[float(b.max()) for b in bins]}

class TextRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=30000)

@router.post('/tokens')
def tokens(body:TextRequest, user=Depends(principal)):
    try:
        c=canonicalize(body.transcript)
    except ValueError as e:
        raise HTTPException(422,str(e))
    return {'sha256':c['sha256'],'words':[{'id':w['id'],'text':w['text'],'start_s':None,'end_s':None,'missing':False,'reviewed':False} for w in c['tokens']]}

class Word(BaseModel):
    id:int = Field(ge=0)
    text:str
    start_s:float|None = Field(default=None,ge=0,allow_inf_nan=False)
    end_s:float|None = Field(default=None,ge=0,allow_inf_nan=False)
    missing:bool=False
    reviewed:bool=False

class HumanEvent(BaseModel):
    id:str=Field(min_length=1,max_length=80)
    type:Literal['pace','intonation','pauses','energy','vocal_clarity','recording_quality']
    severity:int=Field(ge=1,le=4)
    start_s:float=Field(ge=0,allow_inf_nan=False)
    end_s:float=Field(gt=0,allow_inf_nan=False)
    token_ids:list[int]=Field(default_factory=list,max_length=2000)
    uncertainty_s:float=Field(default=0,ge=0,allow_inf_nan=False)
    ambiguous:bool=False
    notes:str=Field(min_length=3,max_length=4000)

class Checks(BaseModel):
    reference_listened:bool=False
    rendition_listened:bool=False
    transcript_checked:bool=False
    boundaries_checked:bool=False
    unedited_spans_checked:bool=False
    independent:bool=False
    no_flaws_confirmed:bool=False

class Review(BaseModel):
    scope:Literal['acceptance','full_annotation']='acceptance'
    decision:Literal['accept','reject','ambiguous']|None=None
    notes:str=Field(default='',max_length=8000)
    baseline_rationale:str=Field(default='',max_length=4000)
    transcript:str=Field(min_length=1,max_length=30000)
    words:list[Word]=Field(max_length=2000)
    events:list[HumanEvent]=Field(default_factory=list,max_length=200)
    ratings:dict[str,int|None]=Field(default_factory=dict)
    checks:Checks=Field(default_factory=Checks)
    revision:int=Field(default=0,ge=0)
    submit:bool=False

def validate_review(body, task, final=False):
    duration=task['metadata']['duration_s']
    try:
        canonical=canonicalize(body.transcript)
    except ValueError as e:
        raise HTTPException(422,str(e))
    expected=[(w['id'],w['text']) for w in canonical['tokens']]
    if [(w.id,w.text) for w in body.words] != expected:
        raise HTTPException(422,'Apply the corrected transcript to rebuild token IDs before saving.')
    last=-1
    for w in body.words:
        if w.missing and (w.start_s is not None or w.end_s is not None):
            raise HTTPException(422,'Missing words must have empty start and end times.')
        if (w.start_s is None)!=(w.end_s is None):
            raise HTTPException(422,'A word needs both timestamps, or neither.')
        if w.start_s is not None:
            if not w.start_s < w.end_s <= duration+.001 or w.start_s<last:
                raise HTTPException(422,'Word times must be ordered, within the rendition, and start before end.')
            last=w.start_s
        if final and body.scope=='full_annotation' and (not w.reviewed or (not w.missing and w.start_s is None)):
            raise HTTPException(422,'Review every word boundary or explicitly mark the word missing before submitting full annotations.')
    ids=set(range(len(expected)))
    if len({e.id for e in body.events})!=len(body.events):
        raise HTTPException(422,'Event IDs must be unique.')
    for e in body.events:
        if not e.start_s<e.end_s<=duration+.001 or not set(e.token_ids)<=ids:
            raise HTTPException(422,'Flaw intervals and word IDs must refer to this rendition.')
    if any(k not in KINDS or (v is not None and (isinstance(v,bool) or not isinstance(v,int) or not 0<=v<=4)) for k,v in body.ratings.items()):
        raise HTTPException(422,'Category ratings must be severity 0–4 or null for unassessable evidence.')
    if final:
        required=['reference_listened','rendition_listened','transcript_checked','unedited_spans_checked','independent']
        if body.scope=='full_annotation':required.append('boundaries_checked')
        if not all(getattr(body.checks,k) for k in required) or body.decision is None:
            raise HTTPException(422,'Complete the listening checklist and accept/reject/ambiguous decision.')
        if body.decision!='accept' and len(body.notes.strip())<3:
            raise HTTPException(422,'Explain the rejection or ambiguity.')
        if task['metadata'].get('generation_method')=='reference' and body.decision=='accept' and len(body.baseline_rationale.strip())<10:
            raise HTTPException(422,'Explain why this baseline is an acceptable delivery.')
        if body.scope=='full_annotation':
            if set(body.ratings)!=set(KINDS):
                raise HTTPException(422,'Rate all six categories; use null when unassessable and explain it in notes.')
            if any(v is None for v in body.ratings.values()) and len(body.notes.strip())<3:
                raise HTTPException(422,'Explain unassessable category ratings in the review notes.')
            if not body.events and not body.checks.no_flaws_confirmed:
                raise HTTPException(422,'Confirm that no audible flaws were found, or add the perceptual events.')
            if body.events and body.checks.no_flaws_confirmed:
                raise HTTPException(422,'Audible events are present. Clear the no-flaws confirmation before submitting.')
    return canonical

def payload(body, canonical, reviewer):
    value=body.model_dump(exclude={'submit','revision'})
    value.update({'schema_version':'speechlens-human-review-v1','label_kind':'human_perceptual',
                  'reviewer_id':reviewer,'transcript_sha256':canonical['sha256'], 'consent_version':CONSENT_VERSION})
    for event in value['events']:
        event['perceptual_interval_s']=[event['start_s'],event['end_s']]
        event['reviewers']=[reviewer]
        event['label_kind']='perceptual'
    return value

def annotation_files(archive, prefix, value):
    """Export explicit word/event files alongside the complete review record."""
    alignment={'schema_version':'speechlens-human-alignment-v1','transcript':value['transcript'],
               'transcript_sha256':value['transcript_sha256'],'reviewer_id':value['reviewer_id'],
               'status':value.get('status','draft'),'scope':value['scope'],
               'words':[{**w,'source':'human_listener' if w['reviewed'] else 'unreviewed_estimate',
                         'review_status':'human_reviewed' if w['reviewed'] else 'pending','confidence':None} for w in value['words']]}
    events={'schema_version':'speechlens-human-events-v1','label_kind':'perceptual','status':value.get('status','draft'),
            'reviewer_id':value['reviewer_id'],'category_severity_ratings':value['ratings'],
            'events':[{**e,'participant_interval_s':[e['start_s'],e['end_s']],'severity_level':e['severity']} for e in value['events']]}
    archive.writestr(f'alignments/{prefix}.json',json.dumps(alignment,indent=2,allow_nan=False))
    archive.writestr(f'events/{prefix}.json',json.dumps(events,indent=2,allow_nan=False))

@router.put('/tasks/{task_id}/submission')
def save(task_id:str, body:Review, user=Depends(principal)):
    if user['role']!='reviewer':
        raise HTTPException(403,'Sign in as an independent reviewer to label recordings.')
    task=task_row(task_id)
    canonical=validate_review(body,task,body.submit)
    value=payload(body,canonical,user['alias'])
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        old=con.execute('SELECT * FROM submissions WHERE task_id=? AND reviewer=?',(task_id,user['alias'])).fetchone()
        if old and old['status']=='submitted':
            if json.loads(old['payload'])['scope']=='acceptance' and body.scope=='full_annotation':
                con.execute('INSERT OR IGNORE INTO acceptance_originals VALUES (?,?,?,?,?)',
                            (task_id,user['alias'],old['payload'],old['revision'],old['updated_at']))
            else:
                raise HTTPException(409,'Submitted independent reviews are immutable. Corrections belong in adjudication.')
        revision=old['revision'] if old else 0
        if body.revision!=revision:
            raise HTTPException(409,'A newer draft exists. Reload this task before saving.')
        timestamp=now()
        con.execute('INSERT OR REPLACE INTO submissions VALUES (?,?,?,?,?,?,?)',
                    (task_id,user['alias'],json.dumps(value,allow_nan=False),revision+1,'submitted' if body.submit else 'draft',old['created_at'] if old else timestamp,timestamp))
    return {'revision':revision+1,'status':'submitted' if body.submit else 'draft','saved_at':timestamp}

@router.get('/coordinator')
def coordinator_summary(user=Depends(coordinator)):
    catalog()
    with db() as con:
        result=[]
        for index,row in enumerate(con.execute('SELECT * FROM tasks ORDER BY rowid').fetchall()):
            reviews=[dict(r) for r in con.execute("SELECT reviewer,status,payload FROM submissions WHERE task_id=? AND status='submitted'",(row['id'],))]
            full=[r for r in reviews if json.loads(r['payload'])['scope']=='full_annotation']
            qa=[dict(r) for r in con.execute('SELECT reviewer,payload FROM acceptance_originals WHERE task_id=?',(row['id'],))]
            adj=con.execute('SELECT created_at FROM adjudications WHERE task_id=?',(row['id'],)).fetchone()
            assigned=[dict(r) for r in con.execute('SELECT reviewer,scope FROM assignments WHERE task_id=?',(row['id'],))]
            meta=json.loads(row['metadata'])
            result.append({'id':row['id'],'recording_id':row['recording_id'],'kind':row['kind'],
                           'label':f"{'Human rendition' if row['kind']=='human' else 'Listening task'} {index+1:03d}",
                           'split':meta.get('split'),'is_reference':meta.get('generation_method')=='reference',
                           'family':meta.get('flaw_family','human'),'declared_level':meta.get('severity_label'),
                           'assignments':assigned,
                           'submitted_reviews':len(reviews)+len(qa),'independent_full_reviews':len(full),'ready':len(full)>=2,
                           'adjudicated':bool(adj),'decisions':[json.loads(r['payload'])['decision'] for r in reviews+qa]})
        reviewers=[r['alias'] for r in con.execute('SELECT alias FROM identities WHERE alias!=?',(user['alias'],))]
    return {'tasks':result,'reviewer_ids':reviewers,'key_location':'storage/human_review/coordinator-key.txt','identity_limit':'Pseudonymous accounts do not verify that two accounts belong to two different humans; the coordinator must establish independence.'}

class Assignment(BaseModel):
    task_ids:list[str]=Field(min_length=1,max_length=1000)
    reviewer_ids:list[str]=Field(min_length=1,max_length=20)
    scope:Literal['acceptance','full_annotation']='full_annotation'

@router.post('/assignments')
def assign(body:Assignment,user=Depends(coordinator)):
    if len(set(body.reviewer_ids))!=len(body.reviewer_ids) or user['alias'] in body.reviewer_ids:
        raise HTTPException(422,'Use distinct reviewer IDs, separate from the coordinating identity.')
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        for alias in body.reviewer_ids:
            if not con.execute('SELECT 1 FROM identities WHERE alias=?',(alias,)).fetchone():
                raise HTTPException(422,'Each reviewer must create their own account before assignment.')
        for tid in body.task_ids:
            if not con.execute('SELECT 1 FROM tasks WHERE id=?',(tid,)).fetchone():
                raise HTTPException(404,'A selected task no longer exists. Refresh the queue.')
            for alias in body.reviewer_ids:
                con.execute('INSERT OR REPLACE INTO assignments VALUES (?,?,?)',(tid,alias,body.scope))
    return {'assigned_tasks':len(set(body.task_ids)),'reviewers':body.reviewer_ids,'scope':body.scope}

@router.get('/tasks/{task_id}/adjudication')
def adjudication_detail(task_id:str,user=Depends(coordinator)):
    task_row(task_id)
    with db() as con:
        rows=con.execute("SELECT * FROM submissions WHERE task_id=? AND status='submitted' ORDER BY updated_at",(task_id,)).fetchall()
        reviews=[{**json.loads(r['payload']),'submitted_at':r['updated_at']} for r in rows if json.loads(r['payload'])['scope']=='full_annotation']
        adj=con.execute('SELECT * FROM adjudications WHERE task_id=?',(task_id,)).fetchone()
    if len(reviews)<2:
        raise HTTPException(409,'Two independent full annotations must be submitted before adjudication opens.')
    return {'reviews':reviews,'adjudication':json.loads(adj['payload']) if adj else None}

class Adjudication(BaseModel):
    reviewers:list[str]=Field(min_length=2,max_length=20)
    resolution_notes:str=Field(min_length=10,max_length=8000)
    result:Review
    independent_humans_confirmed:bool=False

@router.post('/tasks/{task_id}/adjudication')
def adjudicate(task_id:str,body:Adjudication,user=Depends(coordinator)):
    originals=adjudication_detail(task_id,user)['reviews']
    by_id={r['reviewer_id']:r for r in originals}
    if len(set(body.reviewers))!=len(body.reviewers) or not set(body.reviewers)<=set(by_id):
        raise HTTPException(422,'Choose at least two distinct reviewers who submitted full annotations.')
    if user['alias'] in body.reviewers:
        raise HTTPException(422,'Use a coordinator who did not author the selected independent reviews.')
    if not body.independent_humans_confirmed or body.result.scope!='full_annotation':
        raise HTTPException(422,'Confirm distinct consenting humans and provide the resolved full annotation.')
    canonical=validate_review(body.result,task_row(task_id),True)
    value=payload(body.result,canonical,user['alias'])
    value.update({'status':'adjudicated','reviewers':body.reviewers,'resolution_notes':body.resolution_notes,
                  'independent_humans_confirmed':True,'original_review_hashes':{r:object_hash(by_id[r]) for r in body.reviewers}})
    for event in value['events']:event['reviewers']=body.reviewers;event['adjudication_status']='adjudicated'
    with db() as con:
        if con.execute('SELECT 1 FROM adjudications WHERE task_id=?',(task_id,)).fetchone():
            raise HTTPException(409,'This adjudication is already finalized; its independent originals are preserved.')
        con.execute('INSERT INTO adjudications VALUES (?,?,?,?)',(task_id,user['alias'],json.dumps(value,allow_nan=False),now()))
    return {'status':'adjudicated','reviewers':body.reviewers}

@router.get('/export')
def export(user=Depends(principal)):
    stream=io.BytesIO()
    counts={'submitted':0,'drafts':0,'adjudicated':0,'human_performances':0}
    with db() as con, zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        query='SELECT * FROM submissions' if user['role']=='coordinator' else 'SELECT * FROM submissions WHERE reviewer=?'
        rows=con.execute(query,() if user['role']=='coordinator' else (user['alias'],)).fetchall()
        for row in rows:
            value={**json.loads(row['payload']),'task_id':row['task_id'],'status':row['status'],'revision':row['revision'],'updated_at':row['updated_at']}
            counts['submitted' if row['status']=='submitted' else 'drafts']+=1
            archive.writestr(f"independent/{row['task_id']}/{row['reviewer']}.json",json.dumps(value,indent=2,allow_nan=False))
            annotation_files(archive,f"independent/{row['task_id']}/{row['reviewer']}",value)
        query='SELECT * FROM acceptance_originals' if user['role']=='coordinator' else 'SELECT * FROM acceptance_originals WHERE reviewer=?'
        for row in con.execute(query,() if user['role']=='coordinator' else (user['alias'],)).fetchall():
            value={**json.loads(row['payload']),'task_id':row['task_id'],'status':'submitted','revision':row['revision'],'updated_at':row['created_at']}
            counts['submitted']+=1
            archive.writestr(f"acceptance_originals/{row['task_id']}/{row['reviewer']}.json",json.dumps(value,indent=2))
        if user['role']=='coordinator':
            for row in con.execute('SELECT * FROM adjudications'):
                value={**json.loads(row['payload']),'task_id':row['task_id'],'created_at':row['created_at']}
                archive.writestr(f"adjudicated/{row['task_id']}.json",json.dumps(value,indent=2))
                annotation_files(archive,f"adjudicated/{row['task_id']}",value)
                counts['adjudicated']+=1
            mapping=[{'task_id':r['id'],'recording_id':r['recording_id'],'kind':r['kind']} for r in con.execute('SELECT * FROM tasks')]
            archive.writestr('private_task_mapping.json',json.dumps(mapping,indent=2))
        humans=[]
        for row in con.execute("SELECT * FROM tasks WHERE kind='human'"):
            meta=json.loads(row['metadata'])
            if user['role']=='coordinator' or meta['owner']==user['alias']:
                humans.append({'task_id':row['id'],**meta})
        counts['human_performances']=len(humans)
        archive.writestr('human_performances.jsonl','\n'.join(json.dumps(h) for h in humans))
        archive.writestr('README.txt','Private research export. Independent originals and adjudication are separate. Human audio stays on this computer and is not bundled. Public redistribution requires consent and coordinator QA. Reviewed labels do not enter inference automatically.\n')
        archive.writestr('summary.json',json.dumps(counts,indent=2))
    stream.seek(0)
    return StreamingResponse(stream,media_type='application/zip',headers={'Content-Disposition':'attachment; filename=speechlens-human-review.zip','Cache-Control':'no-store'})

@router.post('/performances',status_code=201)
async def performance(reference_id:str=Form(...),speaker_id:str=Form(...),transcript:str=Form(...),
                      intent:Literal['acceptable','subtle','strong']=Form(...),family:str=Form('acceptable'),
                      conditions:str=Form(...),adult_consent:bool=Form(False),research_consent:bool=Form(False),
                      publication_consent:bool=Form(False),derivative_consent:bool=Form(False),
                      readback_confirmed:bool=Form(False),
                      audio:UploadFile=File(...),user=Depends(principal)):
    catalog()
    if not adult_consent or not research_consent:
        raise HTTPException(422,'This collection flow requires adult voluntary consent for local research storage. Do not submit another person without their permission.')
    if not readback_confirmed:
        raise HTTPException(422,'Listen back and confirm the selected intended text before submitting.')
    if not 3<=len(speaker_id)<=48 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in speaker_id):
        raise HTTPException(422,'Use a 3–48 character speaker pseudonym containing letters, digits, hyphens or underscores.')
    if family not in KINDS+['acceptable'] or len(conditions.strip())<3 or len(conditions)>4000:
        raise HTTPException(422,'Select a delivery category and describe microphone/room conditions.')
    with db() as con:
        ref=con.execute("SELECT * FROM tasks WHERE recording_id=? AND kind='public'",(reference_id,)).fetchone()
        if not ref or json.loads(ref['metadata']).get('generation_method')!='reference':
            raise HTTPException(422,'Choose an existing reference text.')
        refmeta=json.loads(ref['metadata'])
        for existing in con.execute("SELECT metadata FROM tasks WHERE kind='human'"):
            m=json.loads(existing['metadata'])
            if m['speaker_id']=='human_'+speaker_id.lower() and m['split']!=refmeta['split']:
                raise HTTPException(422,'This speaker already belongs to another split. Choose a reference in the same split to prevent leakage.')
    try:
        text=canonicalize(transcript)
    except ValueError as error:
        raise HTTPException(422,str(error))
    if text['sha256']!=refmeta['transcript_sha256']:
        raise HTTPException(422,'Read the exact reference transcript. Canonical text must match; deviations must be recorded as missing words during review.')
    suffix=Path(audio.filename or '').suffix.lower()
    if suffix not in EXTENSIONS:
        raise HTTPException(415,'Use WAV, FLAC, OGG, MP3, M4A, MP4 or WebM audio.')
    task_id=uuid.uuid4().hex
    folder=home()/'performances'/task_id
    folder.mkdir(parents=True)
    original=folder/('original'+suffix)
    try:
        size=0
        with original.open('wb') as f:
            while chunk:=await audio.read(1024*1024):
                size+=len(chunk)
                if size>PIPELINE['max_upload_bytes']:raise HTTPException(413,'Recording exceeds 100 MB.')
                f.write(chunk)
        try:
            _,decoded=await run_in_threadpool(decode,original,folder/'canonical.wav')
        except (ValueError,RuntimeError) as e:
            raise HTTPException(422,str(e))
        metadata={'recording_id':'human_'+task_id,'reference_id':reference_id,'speaker_id':'human_'+speaker_id.lower(),
                  'source_recording_id':'human_'+task_id,'transcript':transcript,'transcript_id':refmeta['transcript_id'],
                  'transcript_sha256':text['sha256'],'split':refmeta['split'],'owner':user['alias'],
                  'declared_intent':intent,'declared_family':family,'conditions':conditions,'duration_s':decoded['duration_s'],
                  'audio_sha256':decoded['canonical_sha256'],'original_sha256':decoded['original_sha256'],
                  'generation_method':'consented_human_performance','review_status':'pending','alignment_status':'human_annotation_pending',
                  'consent':{'version':CONSENT_VERSION,'adult':True,'local_research':True,'public_redistribution':publication_consent,
                             'derivatives':derivative_consent,'readback_confirmed':True,'attested_by':user['alias'],'timestamp':now()},
                  'release_eligible':False,'created_at':now()}
        with db() as con:
            con.execute('BEGIN IMMEDIATE')
            # Recheck after decode: concurrent uploads must not create cross-split speaker leakage.
            for existing in con.execute("SELECT metadata FROM tasks WHERE kind='human'"):
                m=json.loads(existing['metadata'])
                if m['speaker_id']==metadata['speaker_id'] and m['split']!=metadata['split']:
                    raise HTTPException(422,'Concurrent submission placed this speaker in another split. Choose a text in that split.')
            con.execute('INSERT INTO tasks VALUES (?,?,?,?)',(task_id,metadata['recording_id'],'human',json.dumps(metadata)))
        return {'task_id':task_id,'recording_id':metadata['recording_id'],'duration_s':metadata['duration_s'],
                'status':'awaiting_human_review','private':True,'release_eligible':False}
    except Exception:
        shutil.rmtree(folder)
        raise
    finally:
        await audio.close()

@router.get('/performances')
def performances(user=Depends(principal)):
    with db() as con:
        rows=con.execute("SELECT * FROM tasks WHERE kind='human' ORDER BY rowid DESC").fetchall()
    return [{'task_id':r['id'],**json.loads(r['metadata'])} for r in rows if user['role']=='coordinator' or json.loads(r['metadata'])['owner']==user['alias']]

@router.delete('/performances/{task_id}',status_code=204)
def withdraw(task_id:str,user=Depends(principal)):
    task=task_row(task_id)
    if task['kind']!='human' or (task['metadata']['owner']!=user['alias'] and user['role']!='coordinator'):
        raise HTTPException(403,'Only the submitter or coordinator can withdraw a human recording.')
    folder=home()/'performances'/task_id
    if folder.exists():shutil.rmtree(folder)
    with db() as con:con.execute('DELETE FROM tasks WHERE id=?',(task_id,))
