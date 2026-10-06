import argparse
import json
import numpy as np
import soundfile as sf
from backend.speechlens.config import ROOT,PIPELINE
from backend.speechlens.utils import object_hash,sha256_file,write_json
from backend.speechlens.alignment import align
from backend.speechlens.text import phrase_ids
from backend.speechlens.transforms import apply_edits,propagate_words

def build(demo=False):
    references=[json.loads(line) for line in (ROOT/"data/manifests/references.jsonl").read_text().splitlines() if line]
    if demo:
        # Choose train, not held-out test, for the default demonstration.
        references=sorted(references,key=lambda r:(r["split"]!="train",-r["alignment_coverage"]))[:1]
    rows=list(references)
    for row in references:
        text=json.loads((ROOT/"data/transcripts"/(row["transcript_id"]+".json")).read_text())
        alignment=json.loads((ROOT/"data"/row["alignment_path"]).read_text())
        y,sr=sf.read(ROOT/"data"/row["audio_path"],dtype="float32")
        eligible=[]
        for ids in phrase_ids(text):
            words=[alignment["words"][i] for i in ids]
            if len(ids)>=4 and all(w["start_s"] is not None for w in words):
                eligible.append((ids,words[0]["start_s"],words[-1]["end_s"]))
        if not eligible:
            print("No editable aligned phrase",row["recording_id"],flush=True)
            continue
        seed=int(object_hash(row["pair_group_id"])[:8],16)
        rng=np.random.default_rng(seed)
        ids,a,b=eligible[int(rng.integers(len(eligible)))]
        definitions=[]
        for family in ["pace","intonation","pauses","energy","clarity_proxy"]:
            for level in range(1,5):
                edit={"start_s":a,"end_s":b,"family":family,"severity":level,"token_ids":ids}
                jitter=float(rng.uniform(.98,1.02))
                if family=="pace":
                    ratio=[1.08,1.18,1.35,1.6][level-1]*jitter
                    if seed%2:
                        ratio=1/ratio
                    edit.update(kind="stretch",duration_multiplier=ratio)
                elif family=="intonation":
                    edit.update(kind="pitch",pitch_range_multiplier=[.85,.65,.4,.15][level-1]*jitter)
                elif family=="pauses":
                    # Insert at a verified word boundary; never cut a consonant.
                    left=alignment["words"][ids[-1]]
                    next_word=alignment["words"][ids[-1]+1] if ids[-1]+1<len(alignment["words"]) else None
                    boundary=left["end_s"]
                    if next_word and next_word["start_s"] is not None:
                        boundary=(left["end_s"]+next_word["start_s"])/2
                    edit.update(start_s=boundary,end_s=boundary,kind="insertion",duration_s=[.15,.5,1.1,2.0][level-1]*jitter)
                elif family=="energy":
                    edit.update(kind="energy",flatten_amount=[.15,.4,.7,1.0][level-1])
                else:
                    edit.update(kind="lowpass_proxy",cutoff_hz=[3500,2400,1500,750][level-1]*jitter)
                definitions.append((family,level,[edit]))
        definitions.extend([
            ("accepted_gain",0,[{"start_s":0,"end_s":len(y)/sr,"kind":"gain","gain_db":-6,"family":"accepted","severity":0}]),
            ("sham_stretch",0,[{"start_s":a,"end_s":b,"kind":"stretch","duration_multiplier":1,"family":"accepted","severity":0,"token_ids":ids}]),
            ("sham_world",0,[{"start_s":a,"end_s":b,"kind":"world_sham","pitch_range_multiplier":1,"family":"accepted","severity":0,"token_ids":ids}])])
        # Non-overlapping compound supports with separate per-event labels.
        if len(eligible)>1:
            ids2,c,d=next(e for e in eligible if e[1]>=b or e[2]<=a)
            definitions.extend([(f"compound{level}",level,[
                {"start_s":a,"end_s":b,"kind":"stretch","duration_multiplier":{2:1.2,4:1.6}[level],"family":"pace","severity":level,"token_ids":ids},
                {"start_s":c,"end_s":d,"kind":"pitch","pitch_range_multiplier":{2:.65,4:.15}[level],"family":"intonation","severity":level,"token_ids":ids2}]) for level in [2,4]])
        for family,level,edits in definitions:
            recording_id=f"{row['pair_group_id']}_{family}_level{level}"
            audio=ROOT/"data/audio"/(recording_id+".wav")
            print("Generating",recording_id,flush=True)
            transformed,mapping,supports=apply_edits(y,edits,seed)
            sf.write(audio,transformed,sr,subtype="PCM_16")
            variant,_=sf.read(audio,dtype="float32")
            aligned=align(variant,text,object_hash([sha256_file(audio),text["sha256"],PIPELINE]))
            propagated=propagate_words(alignment["words"],mapping)
            residuals=[abs(w["start_s"]-p["start_s"]) for w,p in zip(aligned["words"],propagated) if w["start_s"] is not None and p["start_s"] is not None]
            write_json(ROOT/"data/alignments"/(recording_id+".json"),aligned)
            write_json(ROOT/"data/events"/(recording_id+".json"),{"events":supports,"time_map":mapping,
                       "propagated_words":propagated,"realigned_vs_propagated_mean_onset_s":float(np.mean(residuals)) if residuals else None,
                       "negative_review_status":"pending","label_kind":"transformation_support_not_perceptual_ground_truth"})
            rows.append({**row,"recording_id":recording_id,"audio_path":"audio/"+audio.name,"audio_sha256":sha256_file(audio),
                "duration_s":len(variant)/sr,"generation_method":"local_"+edits[0]["kind"],"flaw_family":family,"severity_label":level,
                "alignment_path":"alignments/"+recording_id+".json","events_path":"events/"+recording_id+".json",
                "alignment_coverage":aligned["coverage"],"seed":seed,"review_status":"pending",
                "signal_quality":{"clipped_fraction":float(np.mean(np.abs(variant)>=.999))},"generation_metadata_inference_access":False})
    path=ROOT/"data/manifests/recordings.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows)+"\n",encoding="utf-8")
    write_json(ROOT/"configs/splits/manifest.json",{r["pair_group_id"]:r["split"] for r in rows})
    print("Built",len(rows),"recordings. All perceptual reviews pending.")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--demo",action="store_true")
    args=parser.parse_args()
    build(args.demo)
    if not args.demo:
        from scripts.augment_holdout import augment
        augment()
