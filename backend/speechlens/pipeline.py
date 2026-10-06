from pathlib import Path
import json
import time
import platform
import importlib.metadata
import psutil
from .config import ROOT, STORAGE, PIPELINE, DETECTORS, PRESETS
from .text import canonicalize
from .ingest import decode
from .alignment import align
from .features import extract, display_features
from .comparison import compare
from .detectors import detect
from .scoring import aggregate
from .utils import object_hash, sha256_file, write_json, jsonable
from backend.app.schemas import Result

def version_fingerprint():
    source_files=list((ROOT/"backend/speechlens").glob("*.py")) + [ROOT/"backend/app/schemas.py"]
    return object_hash({str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(source_files)})

def runtime_memory():
    info=psutil.Process().memory_info()
    if hasattr(info,"peak_wset"):
        peak=info.peak_wset/(1024**2)
    else:
        import resource
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024 if platform.system()!="Darwin" else 1024**2)
    return {"process_lifetime_peak_resident_mb":peak,"current_resident_mb":info.rss/(1024**2),
            "logical_cpu_count":psutil.cpu_count(),"system_memory_gb":psutil.virtual_memory().total/(1024**3),
            "cpu":platform.processor(),"torch_threads":2}

def run(participant_path, transcript_text, output_dir, reference_path=None, reference_text=None,
        preset="persuasive_oratory", weights=None, stage=lambda *args:None, use_cache=True):
    started=time.perf_counter()
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    private=output_dir.resolve().is_relative_to(STORAGE.resolve())
    cache_root=output_dir/".private_cache" if private else ROOT/".cache"
    text=canonicalize(transcript_text)
    if reference_text is not None and canonicalize(reference_text)["sha256"]!=text["sha256"]:
        raise ValueError("Reference and participant canonical transcripts differ; paired evaluation requires the exact same text.")
    config={"pipeline":PIPELINE,"detectors":DETECTORS,"preset":PRESETS.get(preset),"weights":weights,
            "code":version_fingerprint()}
    config_hash=object_hash(config)
    stage("decoding and validating",.08)
    py,pm=decode(participant_path,output_dir/"participant.wav")
    ry,rm=decode(reference_path,output_dir/"reference.wav") if reference_path else (None,None)
    hashes={"participant":pm["original_sha256"],"reference":rm["original_sha256"] if rm else None,
            "transcript":text["sha256"],"configuration":config_hash}
    cache_key=object_hash(hashes)
    cache=cache_root/"results"/(cache_key+".json")
    def features_for(y,metadata):
        feature_key=object_hash([metadata["original_sha256"],PIPELINE,config["code"]])
        feature_path=cache_root/"features"/(feature_key+".json")
        if use_cache and feature_path.exists():
            return json.loads(feature_path.read_text())
        value=extract(y)
        if use_cache:
            write_json(feature_path,value)
        return value
    if use_cache and cache.exists():
        result=json.loads(cache.read_text())
        result["provenance"]["cache_hit"]=True
        write_json(output_dir/"participant_features_full.json",features_for(py,pm))
        if ry is not None:
            write_json(output_dir/"reference_features_full.json",features_for(ry,rm))
        write_json(output_dir/"result.json",result)
        stage("completed (matching hash cache)",1)
        return result
    stage("aligning participant intended text",.18)
    pa=align(py,text,object_hash([pm["original_sha256"],text["sha256"],config_hash]) if use_cache else None,cache_root/"alignments")
    stage("aligning reference independently",.35)
    ra=align(ry,text,object_hash([rm["original_sha256"],text["sha256"],config_hash]) if use_cache else None,cache_root/"alignments") if ry is not None else None
    stage("extracting participant FFT / MFCC / pYIN / VAD",.48)
    pf=features_for(py,pm)
    stage("extracting reference native-time features",.67)
    rf=features_for(ry,rm) if ry is not None else None
    write_json(output_dir/"participant_features_full.json",pf)
    if rf:
        write_json(output_dir/"reference_features_full.json",rf)
    stage("matching phrases and detecting deviations",.82)
    comparison=compare(text,pa,pf,ra,rf)
    events,units=detect(comparison,text,pf,paired=ra is not None)
    warnings=["Engineering thresholds and confidence heuristics are uncalibrated; human review is pending.",
              "Clarity is diagnostic-only. Recording quality cannot establish articulation quality.",
              "Single-speaker confirmation is user supplied; overlap detection is not validated."]
    for role,a in [("participant",pa),("reference",ra)]:
        if a is not None and a["coverage"]<PIPELINE["minimum_alignment_coverage"]:
            warnings.append(f"{role}: alignment coverage {a['coverage']:.1%}; affected phrases abstain.")
        if a is not None and a["asr_match_fraction"]<.6:
            warnings.append(f"{role}: substantial ASR/intended-text mismatch. Matching errors may be acoustic; paired scoring withheld.")
            # Do not let high forced-CTC likelihood turn severe mismatches into confident scores.
            for rows in units.values():
                for unit in rows:
                    unit["eligible"]=False
            events=[e for e in events if e["type"]=="recording_quality"]
    if ra is None:
        warnings.append("Unpaired mode: rate, pauses and quality are observations; no equivalent delivery score or reference overlay.")
    scores=aggregate(units,preset,weights,paired=ra is not None)
    if pf["quality"]["clipped_fraction"]>.01:
        scores["total"]=None
        scores["status"]="insufficient_recording_quality"
        warnings.append("Substantial clipping: overall delivery score withheld.")
    stage("validating and exporting evidence",.94)
    result={"schema_version":"1.0","mode":"paired" if ra is not None else "unpaired","transcript":text,
        "alignments":{"participant":pa,**({"reference":ra} if ra else {})},"events":events,"scores":scores,
        "features":{"participant":display_features(pf),**({"reference":display_features(rf)} if rf else {})},
        "comparison":comparison,"scoring_units":units,"warnings":warnings,
        "provenance":{"hashes":hashes,"cache_key":cache_key,"cache_hit":False,"configuration":config,
            "audio":{"participant":pm,"reference":rm},"device":"CPU","platform":platform.platform(),
            "processing_s":time.perf_counter()-started,
            "runtime":runtime_memory(),
            "packages":{n:importlib.metadata.version(n) for n in ["torch","transformers","librosa","numpy","scipy","soundfile","webrtcvad-wheels"]}}}
    result=jsonable(result)
    Result.model_validate(result)
    write_json(output_dir/"result.json",result)
    write_json(cache,result)
    stage("completed",1)
    return result
