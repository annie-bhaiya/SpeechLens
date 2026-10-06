import json
import sqlite3
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from backend.speechlens.config import STORAGE

class QueueFullError(ValueError):
    pass

def check_capacity(con):
    if con.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]>=10:
        raise QueueFullError('Worker queue is full; retry after existing jobs complete')

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connection():
    STORAGE.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(STORAGE/"jobs.sqlite",timeout=30)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def initialize():
    with connection() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, status TEXT NOT NULL, stage TEXT NOT NULL, progress REAL NOT NULL,
            error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, attempts INTEGER NOT NULL,
            request_json TEXT NOT NULL, result_path TEXT)""")
        con.execute("UPDATE jobs SET status='queued',stage='recovered after interruption',progress=0,updated_at=? WHERE status='running' AND attempts<2",(now(),))
        con.execute("UPDATE jobs SET status='failed',error='Interrupted twice; retry explicitly',updated_at=? WHERE status='running'",(now(),))

def create_job(request,job_id=None):
    job_id=job_id or uuid.uuid4().hex
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        check_capacity(con)
        timestamp=now()
        con.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)",(job_id,"queued","queued",0,None,timestamp,timestamp,0,json.dumps(request),None))
    return get_job(job_id)

def requeue(job_id):
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        check_capacity(con)
        cursor=con.execute("UPDATE jobs SET status='queued',stage='retry queued',progress=0,error=NULL,updated_at=? WHERE id=? AND status='failed'",(now(),job_id))
        return cursor.rowcount==1

def get_job(job_id):
    if len(job_id)!=32 or any(c not in "0123456789abcdef" for c in job_id):
        return None
    with connection() as con:
        row=con.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
    return dict(row) if row else None

def claim_job():
    with connection() as con:
        con.execute("BEGIN IMMEDIATE")
        row=con.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if row:
            con.execute("UPDATE jobs SET status='running',stage='starting CPU worker',attempts=attempts+1,updated_at=? WHERE id=?",(now(),row["id"]))
    return dict(row) if row else None

def update(job_id,**fields):
    allowed={"status","stage","progress","error","result_path"}
    if not set(fields)<=allowed:
        raise ValueError("Invalid job field")
    fields["updated_at"]=now()
    with connection() as con:
        con.execute("UPDATE jobs SET "+",".join(k+"=?" for k in fields)+" WHERE id=?",(*fields.values(),job_id))

def delete_record(job_id):
    with connection() as con:
        con.execute("DELETE FROM jobs WHERE id=?",(job_id,))
