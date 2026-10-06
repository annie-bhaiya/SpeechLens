import os
import subprocess
import sys
import threading
import time
from backend.speechlens.config import PIPELINE, ROOT, STORAGE
from .storage import initialize,claim_job,update,get_job

class Worker:
    def __init__(self):
        self.stop_event=threading.Event()
        self.thread=None
        self.process=None
        self.job_id=None
        self.lock=threading.Lock()
        self.finished=threading.Event()
        self.finished.set()

    def start(self):
        initialize()
        self.thread=threading.Thread(target=self.loop,name="speechlens-bounded-worker",daemon=True)
        self.thread.start()

    def loop(self):
        while not self.stop_event.is_set():
            row=claim_job()
            if not row:
                self.stop_event.wait(.3)
                continue
            job_id=row["id"]
            directory=STORAGE/"jobs"/job_id
            log=None
            try:
                with self.lock:
                    current=get_job(job_id)
                    if current is None or current["status"]!="running":
                        continue
                    self.job_id=job_id
                    self.finished=threading.Event()
                    directory.mkdir(parents=True,exist_ok=True)
                    log=(directory/"worker.log").open("w",encoding="utf-8")
                    environment={**os.environ,"PYTHONUTF8":"1","HF_HUB_DISABLE_TELEMETRY":"1"}
                    self.process=subprocess.Popen([sys.executable,"-m","scripts.process_job",job_id],cwd=ROOT,
                                                   stdout=log,stderr=log,env=environment,
                                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
                    process=self.process
                try:
                    code=process.wait(timeout=PIPELINE["worker_timeout_s"])
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise RuntimeError("CPU processing exceeded 15 minutes; use a shorter excerpt and retry.")
                if code:
                    lines=(directory/"worker.log").read_text(encoding="utf-8",errors="replace").splitlines()
                    detail=next((s for s in reversed(lines) if s.startswith(("ValueError:","RuntimeError:","OSError:"))),"Processing failed; inspect local worker.log.")
                    update(job_id,status="failed",stage="failed",error=detail[:600])
            except Exception as error:
                update(job_id,status="failed",stage="failed",error=str(error)[:600])
            finally:
                if log is not None:
                    log.close()
                with self.lock:
                    self.process,self.job_id=None,None
                    self.finished.set()

    def cancel(self,job_id):
        update(job_id,status="failed",stage="cancelled",error="Deleted by owner")
        active=False
        finished=None
        with self.lock:
            if self.job_id==job_id:
                active=True
                finished=self.finished
                if self.process is not None:
                    self.process.kill()
                    self.process.wait(timeout=10)
        if active and not finished.wait(timeout=10):
            raise RuntimeError('Worker file handles have not closed; retry deletion shortly.')

    def stop(self):
        self.stop_event.set()
        with self.lock:
            if self.process is not None:
                self.process.terminate()
        if self.thread:
            self.thread.join(timeout=10)

worker=Worker()
