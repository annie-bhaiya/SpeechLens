import json
from pathlib import Path
from collections import defaultdict
import soundfile as sf
from backend.speechlens.config import ROOT
from backend.speechlens.text import canonicalize
from backend.speechlens.utils import sha256_file,write_json
from backend.app.schemas import Alignment

def validate(manifest=None):
    manifest=Path(manifest or ROOT/"data/manifests/recordings.jsonl")
    rows=[json.loads(line) for line in manifest.read_text().splitlines() if line]
    ids={r["recording_id"] for r in rows}
    errors=[]
    pending=0
    connections=defaultdict(set)
    def check(condition,message):
        if not condition:
            errors.append(message)
    check(len(ids)==len(rows),"Duplicate recording IDs")
    for row in rows:
        rid=row["recording_id"]
        for key in ["audio_path","alignment_path","events_path"]:
            path=(ROOT/"data"/row[key]).resolve()
            check(path.is_relative_to((ROOT/"data").resolve()),rid+": unsafe "+key)
            check(path.exists(),rid+": missing "+key)
        try:
            audio=ROOT/"data"/row["audio_path"]
            info=sf.info(audio)
            check(sha256_file(audio)==row["audio_sha256"],rid+": checksum mismatch")
            check(info.samplerate==row["sample_rate_hz"]==16000,rid+": sample rate mismatch")
            check(abs(info.duration-row["duration_s"])<=1/16000,rid+": duration mismatch")
            text=json.loads((ROOT/"data/transcripts"/(row["transcript_id"]+".json")).read_text())
            check(text["sha256"]==row["transcript_sha256"]==canonicalize(text["display_text"])["sha256"],rid+": canonical text mismatch")
            aligned=Alignment.model_validate_json((ROOT/"data"/row["alignment_path"]).read_text())
            check(len(aligned.words)==len(text["tokens"]),rid+": word count mismatch")
            last=0
            for word in aligned.words:
                if word.start_s is not None:
                    check(last-1e-6<=word.start_s<=word.end_s<=info.duration+1e-6,rid+": invalid word clock")
                    last=word.end_s
            events=json.loads((ROOT/"data"/row["events_path"]).read_text())
            for e in events["events"]:
                check(0<=e["target_start_s"]<=e["target_end_s"]<=info.duration+1e-6,rid+": support interval out of range")
                check(e["label_kind"]=="transformation_support" or e["review_status"]=="adjudicated",rid+": label status unclear")
                check(0<=e["severity"]<=4,rid+": severity invalid")
            mapping=events.get("time_map",[])
            for left,right in zip(mapping,mapping[1:]):
                check(abs(left["source_end_s"]-right["source_start_s"])<=1/16000,rid+": source map discontinuity")
                check(abs(left["target_end_s"]-right["target_start_s"])<=1/16000,rid+": target map discontinuity")
            check(row["reference_id"] in ids,rid+": missing reference")
            check((ROOT/"data/provenance"/(row["provenance_id"]+".json")).exists(),rid+": missing provenance")
        except Exception as error:
            errors.append(rid+": "+str(error))
        pending+=row["review_status"]!="adjudicated"
        for key in ["speaker_id","source_recording_id","transcript_sha256","pair_group_id"]:
            connections[(key,row[key])].add(row["split"])
    for key,splits in connections.items():
        check(len(splits)==1,f"Connected source/speaker/text leakage: {key}: {splits}")
    by_id={r["recording_id"]:r for r in rows}
    for row in rows:
        ref=by_id.get(row["reference_id"])
        if ref:
            check(ref["transcript_sha256"]==row["transcript_sha256"],row["recording_id"]+": same-text pairing broken")
            check(ref["split"]==row["split"],row["recording_id"]+": cross-split reference")
    result={"integrity_passed":not errors,"recordings":len(rows),"references":sum(r["generation_method"]=="reference" for r in rows),
            "independent_speakers":len({r["speaker_id"] for r in rows}),"independent_sources":len({r["source_recording_id"] for r in rows}),
            "pending_review_recordings":pending,"human_label_gate_passed":pending==0,"errors":errors,
            "splits":{s:sum(r["split"]==s for r in rows) for s in ["train","validation","test"]}}
    write_json(ROOT/"evaluation/dataset_integrity.json",result)
    return result

if __name__=="__main__":
    result=validate()
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result["integrity_passed"] else 1)
