import asyncio
import csv
import io
import json
import shutil
import uuid
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,field_validator
from .jobs import worker
from .storage import create_job,get_job,update,delete_record,connection,requeue,QueueFullError
from .schemas import Job,Result
from backend.speechlens.config import ROOT,STORAGE,PIPELINE,PRESETS
from backend.speechlens.ingest import EXTENSIONS
from backend.speechlens.text import canonicalize
from backend.speechlens.scoring import aggregate
from backend.speechlens.utils import write_json,object_hash

@asynccontextmanager
async def lifespan(app):
    worker.start()
    yield
    worker.stop()

app=FastAPI(title="SpeechLens",version="0.1.0",lifespan=lifespan)

class RubricRequest(BaseModel):
    preset:str='persuasive_oratory'
    weights:dict[str,float]|None=None

    @field_validator('weights')
    @classmethod
    def nonempty_weights(cls,value):
        if value is not None and not value:
            raise ValueError('Explicit weights must name all five categories')
        return value

def require_job(job_id):
    row=get_job(job_id)
    if row is None:
        raise HTTPException(404,"Evaluation not found")
    return row

def read_result(job_id):
    row=require_job(job_id)
    if row["status"]!="succeeded":
        raise HTTPException(409,"Evaluation has not succeeded")
    return json.loads(Path(row["result_path"]).read_text(encoding="utf-8"))

def records():
    path=ROOT/"data/manifests/recordings.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line] if path.exists() else []

def reference_records():
    return [r for r in records() if r["generation_method"]=="reference"]

@app.get("/healthz")
def health():
    model_path=ROOT/".cache/models"/"models--facebook--wav2vec2-base-960h"/"snapshots"/PIPELINE["alignment_revision"]
    return {"status":"ok","worker_ready":bool(worker.thread and worker.thread.is_alive()),
            "model_cached":(model_path/"model.safetensors").exists(),"device":"CPU","bounded_workers":1,
            "model_revision":PIPELINE["alignment_revision"]}

@app.get("/api/rubrics")
def rubrics():
    return PRESETS

@app.get("/api/references")
def references():
    output=[]
    for row in reference_records():
        text=json.loads((ROOT/"data/transcripts"/(row["transcript_id"]+".json")).read_text(encoding="utf-8"))
        output.append({"id":row["recording_id"],"speaker_id":row["speaker_id"],"title":row.get("title",row["pair_group_id"]),
                       "duration_s":row["duration_s"],"transcript":text["display_text"],
                       "review_status":row["review_status"],"split":row["split"],"provenance_id":row["provenance_id"]})
    return output

async def save_upload(upload,directory,role):
    suffix=Path(upload.filename or "").suffix.lower()
    if suffix not in EXTENSIONS:
        raise HTTPException(415,"Unsupported audio extension")
    path=directory/(role+"_original"+suffix)
    total=0
    try:
        with path.open("wb") as file:
            while chunk:=await upload.read(1024*1024):
                total+=len(chunk)
                if total>PIPELINE["max_upload_bytes"]:
                    raise HTTPException(413,"Upload exceeds 100 MB")
                file.write(chunk)
        if total==0:
            raise HTTPException(422,"Empty upload")
    finally:
        await upload.close()
    return path

@app.post("/api/evaluations",status_code=202,response_model=Job)
async def evaluate(participant:UploadFile=File(...),transcript:str=Form(...),reference_id:str|None=Form(None),
                   reference:UploadFile|None=File(None),reference_text:str|None=Form(None),
                   preset:str=Form("persuasive_oratory"),weights:str|None=Form(None),language:str=Form("en"),
                   single_speaker:bool=Form(False)):
    if not single_speaker:
        raise HTTPException(422,"Confirm English single-speaker speech; overlapping voices are unsupported")
    try:
        canonicalize(transcript,language)
        parsed_weights=RubricRequest(preset=preset,weights=json.loads(weights) if weights else None).weights
        aggregate({k:[] for k in PRESETS["persuasive_oratory"]["weights"]},preset,parsed_weights)
        if reference_id and reference:
            raise ValueError("Choose a curated reference or an uploaded reference, not both")
        if reference and not reference_text:
            raise ValueError("An uploaded reference requires its corrected transcript")
    except (ValueError,TypeError) as error:
        raise HTTPException(422,str(error))
    with connection() as con:
        queued=con.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
    if queued>=10:
        raise HTTPException(429,"Worker queue is full; retry after existing jobs complete")
    job_id=uuid.uuid4().hex
    directory=STORAGE/"jobs"/job_id
    directory.mkdir(parents=True)
    try:
        participant_path=await save_upload(participant,directory,"participant")
        reference_path=None
        if reference_id:
            row=next((r for r in reference_records() if r["recording_id"]==reference_id),None)
            if row is None:
                raise HTTPException(404,"Curated reference not found")
            reference_path=ROOT/"data"/row["audio_path"]
            reference_text=json.loads((ROOT/"data/transcripts"/(row["transcript_id"]+".json")).read_text(encoding="utf-8"))["display_text"]
        elif reference:
            reference_path=await save_upload(reference,directory,"reference")
        if reference_path and canonicalize(reference_text)["sha256"]!=canonicalize(transcript)["sha256"]:
            raise HTTPException(422,"Paired mode requires identical canonical reference and participant transcripts")
        request={"participant_file":participant_path.name,"transcript":transcript,"reference_path":str(reference_path) if reference_path else None,
                 "reference_text":reference_text,"preset":preset,"weights":parsed_weights}
        return create_job(request,job_id)
    except QueueFullError as error:
        shutil.rmtree(directory)
        raise HTTPException(429,str(error))
    except Exception:
        shutil.rmtree(directory)
        raise

@app.get("/api/evaluations/{job_id}",response_model=Job)
def status(job_id:str):
    return require_job(job_id)

@app.get("/api/evaluations/{job_id}/result",response_model=Result)
def result(job_id:str):
    return read_result(job_id)

@app.post("/api/evaluations/{job_id}/retry",status_code=202,response_model=Job)
def retry(job_id:str):
    row=require_job(job_id)
    if row["status"]!="failed":
        raise HTTPException(409,"Only failed jobs can be retried")
    try:
        if not requeue(job_id):
            raise HTTPException(409,'Job state changed; refresh before retrying')
    except QueueFullError as error:
        raise HTTPException(429,str(error))
    return require_job(job_id)

@app.post("/api/evaluations/{job_id}/rescore")
def rescore(job_id:str,payload:RubricRequest):
    result=read_result(job_id)
    try:
        preset=payload.preset
        scores=aggregate(result["scoring_units"],preset,payload.weights,result["mode"]=="paired")
        if result["features"]["participant"]["quality"]["clipped_fraction"]>.01:
            scores["total"]=None
            scores["status"]="insufficient_recording_quality"
        result["scores"]=scores
        config=result["provenance"]["configuration"]
        config["preset"]=PRESETS[preset]
        config["weights"]=payload.weights
        result["provenance"]["hashes"]["configuration"]=object_hash(config)
        result["provenance"]["cache_key"]=object_hash(result["provenance"]["hashes"])
        result["provenance"]["rescore"]={"features_reused":True,"persisted_for_export":True}
        write_json(STORAGE/"jobs"/job_id/"result.json",result)
        return scores
    except ValueError as error:
        raise HTTPException(422,str(error))

@app.get("/api/evaluations/{job_id}/audio/{role}")
def audio(job_id:str,role:str):
    require_job(job_id)
    if role not in ("reference","participant"):
        raise HTTPException(404,"Unknown audio role")
    path=STORAGE/"jobs"/job_id/(role+".wav")
    if not path.exists():
        raise HTTPException(404,"Audio is not ready")
    return FileResponse(path,media_type="audio/wav",headers={"Cache-Control":"private, max-age=0"})

@app.get("/api/evaluations/{job_id}/export")
def export(job_id:str,format:str="zip"):
    result=read_result(job_id)
    if format=="json":
        return FileResponse(STORAGE/"jobs"/job_id/"result.json",media_type="application/json",filename="speechlens-evidence.json")
    if format!="zip":
        raise HTTPException(422,"Export format must be json or zip")
    csv_buffer=io.StringIO()
    writer=csv.DictWriter(csv_buffer,fieldnames=["id","type","severity","start_s","end_s","quote","rule_id","participant","reference","units"])
    writer.writeheader()
    for e in result["events"]:
        writer.writerow({"id":e["id"],"type":e["type"],"severity":e["severity"],"start_s":e["participant_interval_s"][0],
             "end_s":e["participant_interval_s"][1],"quote":e["quote"],"rule_id":e["rule_id"],
             "participant":e["measurements"]["participant"],"reference":e["measurements"]["reference"],"units":e["measurements"]["units"]})
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("result.json",json.dumps(result,indent=2,allow_nan=False))
        archive.writestr("events.csv",csv_buffer.getvalue())
        for role in ["participant","reference"]:
            full=STORAGE/"jobs"/job_id/(role+"_features_full.json")
            if full.exists():
                archive.write(full,role+"_features_full.json")
    buffer.seek(0)
    return StreamingResponse(buffer,media_type="application/zip",headers={"Content-Disposition":"attachment; filename=speechlens-evidence.zip"})

@app.delete("/api/evaluations/{job_id}",status_code=204)
def delete(job_id:str):
    row=require_job(job_id)
    # A running worker has open handles; stop it before removing its private folder.
    try:
        worker.cancel(job_id)
    except RuntimeError as error:
        raise HTTPException(409,str(error))
    update(job_id,status="failed",stage="deleted",error="Deleted by owner")
    directory=(STORAGE/"jobs"/job_id).resolve()
    if directory.parent!=(STORAGE/"jobs").resolve():
        raise HTTPException(400,"Unsafe storage path")
    if directory.exists():
        shutil.rmtree(directory)
    delete_record(job_id)

@app.get("/api/dataset")
def dataset():
    measurements={}
    path=ROOT/"evaluation/recording_scores.json"
    if path.exists():
        measurements=json.loads(path.read_text())
    return {"recordings":[{**r,"measured":measurements.get(r["recording_id"])} for r in records()],
            "labels":"Transformation support only; independent perceptual ground truth pending."}

@app.get('/api/evaluation-summary')
def evaluation_summary():
    summary={}
    for name in ['metrics','robustness']:
        path=ROOT/'evaluation'/(name+'.json')
        summary[name]=json.loads(path.read_text()) if path.exists() else None
    summary['status']='measured' if summary['metrics'] else 'benchmark_pending'
    return summary

@app.get("/api/dataset/{recording_id}/audio")
def dataset_audio(recording_id:str):
    row=next((r for r in records() if r["recording_id"]==recording_id),None)
    if not row:
        raise HTTPException(404,"Recording not found")
    return FileResponse(ROOT/"data"/row["audio_path"],media_type="audio/wav")

@app.post("/api/demo",status_code=202,response_model=Job)
def demo(recording_id:str|None=None):
    if recording_id:
        row=next((r for r in records() if r['recording_id']==recording_id),None)
    else:
        clean=[r for r in reference_records() if r['split']=='train' and r.get('alignment_coverage',0)>=.99]
        chosen=min(clean,key=lambda r:r['duration_s']) if clean else None
        row=next((r for r in records() if r['flaw_family']=='pace' and r['severity_label']==4 and (chosen is None or r['reference_id']==chosen['recording_id'])),None)
    if not row:
        raise HTTPException(404,"Build the demo dataset first")
    reference=next(r for r in reference_records() if r["recording_id"]==row["reference_id"])
    text=json.loads((ROOT/"data/transcripts"/(row["transcript_id"]+".json")).read_text(encoding="utf-8"))["display_text"]
    job_id=uuid.uuid4().hex
    directory=STORAGE/"jobs"/job_id
    directory.mkdir(parents=True)
    shutil.copy2(ROOT/"data"/row["audio_path"],directory/"participant_original.wav")
    try:
        return create_job({"participant_file":"participant_original.wav","transcript":text,
            "reference_path":str(ROOT/"data"/reference["audio_path"]),"reference_text":text,
            "preset":"persuasive_oratory","use_cache":False},job_id)
    except QueueFullError as error:
        shutil.rmtree(directory)
        raise HTTPException(429,str(error))

dist=ROOT/"frontend/dist"
if dist.exists():
    app.mount("/",StaticFiles(directory=dist,html=True),name="dashboard")
