import json
import sys
from pathlib import Path
from backend.app.storage import get_job, update
from backend.speechlens.pipeline import run
from backend.speechlens.config import STORAGE

if __name__=="__main__":
    job_id=sys.argv[1]
    row=get_job(job_id)
    if row is None:
        raise SystemExit("Job no longer exists")
    request=json.loads(row["request_json"])
    output=STORAGE/"jobs"/job_id
    result=run(output/request["participant_file"],request["transcript"],output,
               reference_path=Path(request["reference_path"]) if request.get("reference_path") else None,
               reference_text=request.get("reference_text"),preset=request["preset"],weights=request.get("weights"),
               use_cache=request.get("use_cache",True),
               stage=lambda stage,progress:update(job_id,stage=stage,progress=progress))
    update(job_id,status="succeeded",progress=1,stage="completed",result_path=str(output/"result.json"))
