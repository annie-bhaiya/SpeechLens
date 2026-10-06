"""Acquire documented sources, locate intended excerpts, retain pending human QA."""
import html
import json
import re
import subprocess
from difflib import SequenceMatcher
from datetime import date
import requests
import soundfile as sf
from backend.speechlens.config import ROOT,PIPELINE
from backend.speechlens.ingest import ffmpeg_executable
from backend.speechlens.alignment import align,emissions,greedy_words
from backend.speechlens.text import canonicalize
from backend.speechlens.utils import sha256_file,object_hash,write_json

def download(url,path):
    if path.exists():
        return
    r=requests.get(url,timeout=120,headers={"User-Agent":"SpeechLensResearch/0.1 public-domain source collection"})
    r.raise_for_status()
    if len(r.content)>100*1024*1024:
        raise ValueError("Source exceeds bounded download size")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(r.content)

def collect():
    sources=json.loads((ROOT/"configs/sources.json").read_text())
    rows,failures=[],[]
    for source in sources:
        print("Source",source["id"],flush=True)
        page_url="https://commons.wikimedia.org/wiki/File:"+source["file"].replace(" ","_")
        page_path=ROOT/"data/provenance/source_pages"/(source["file"]+".html")
        try:
            download(page_url,page_path)
            content=page_path.read_text(encoding="utf-8")
            expected="PD-USGov" if source["rights"]=="PD-USGov" else "Executive Office of the President"
            if source["rights"]=="PD-USGov" and not any(s in content for s in ["PD US Government","PD-USGov","United States Federal Government","U.S. federal government","PD US Government"]):
                raise ValueError("Rights evidence does not support configured public-domain claim; inspect source page")
            urls=re.findall(r'https://upload.wikimedia.org[^\s"<>]+\.ogg',content)
            url=next(html.unescape(u) for u in urls if "/transcoded/" not in u and "/archive/" not in u)
            original=ROOT/"data/originals"/(source["id"]+".ogg")
            download(url+"?download=1",original)
            candidate=ROOT/".cache/sources"/(source["id"]+".wav")
            candidate.parent.mkdir(parents=True,exist_ok=True)
            if not candidate.exists():
                subprocess.run([ffmpeg_executable(),"-v","error","-y","-nostdin","-i",str(original),
                                "-ss",str(source["candidate_start_s"]),"-t",str(source["candidate_duration_s"]),
                                "-ac","1","-ar","16000","-c:a","pcm_f32le",str(candidate)],check=True,timeout=60)
            y,sr=sf.read(candidate,dtype="float32")
            lp,times,processor=emissions(y)
            anchors=greedy_words(lp,times,processor)
            draft=processor.batch_decode([lp.argmax(-1)])[0]
            write_json(ROOT/"data/provenance"/(source["id"]+"_asr_draft.json"),{"recognized_text":draft,"status":"machine_draft_not_corrected_human_transcript"})
            print("Draft",draft[:500],flush=True)
            provenance={"id":source["id"],"speaker":source["speaker"],"title":source["file"],"url":page_url,
                "download_url":url,"recording_sha256":sha256_file(original),"retrieved_date":str(date.today()),
                "license":source["rights"],"recording_rights_evidence":page_url,"evidence_sha256":sha256_file(page_path),
                "transcript_url":source["transcript_url"],"transcript_rights":"US federal official speech; public-domain original text",
                "language":"en","independent_review_status":"pending",
                "selection_rationale":"Clear rhetorical clause boundaries, deliberate pacing and public address context; selected as one delivery example, not a unique optimum.",
                "quality_review":"Machine DSP QA only; historical recording channel and any applause remain potential confounds."}
            write_json(ROOT/"data/provenance"/(source["id"]+".json"),provenance)
            for excerpt in source["excerpts"]:
                text=canonicalize(excerpt["text"])
                # Use ASR anchors to avoid forcing unrelated introductions/applause into the snippet.
                intended=text["canonical_text"].split()
                matches={}
                for block in SequenceMatcher(None,intended,[w["text"] for w in anchors],autojunk=False).get_matching_blocks():
                    for offset in range(block.size):
                        matches[block.a+offset]=block.b+offset
                # A plural ending or ASR spelling error may still supply an acoustic crop anchor.
                # This is a disclosed machine anchor, not a corrected perceptual word label.
                for endpoint in [0,len(intended)-1]:
                    if endpoint not in matches and matches:
                        neighbour=min(matches) if endpoint==0 else max(matches)
                        candidate_indices=range(max(0,matches[neighbour]-3),matches[neighbour]+1) if endpoint==0 else range(matches[neighbour],min(len(anchors),matches[neighbour]+5))
                        best=max(candidate_indices,key=lambda i:SequenceMatcher(None,intended[endpoint],anchors[i]["text"]).ratio())
                        if SequenceMatcher(None,intended[endpoint],anchors[best]["text"]).ratio()>=.8:
                            matches[endpoint]=best
                if 0 not in matches or len(intended)-1 not in matches:
                    failures.append({"excerpt":excerpt["id"],"reason":"Endpoint ASR anchor missing; crop requires human QA"})
                    print("Excluded endpoint",excerpt["id"],flush=True)
                    continue
                a=max(0,anchors[matches[0]]["start_s"]-.15)
                b=min(len(y)/sr,anchors[matches[len(intended)-1]]["end_s"]+.15)
                audio=ROOT/"data/audio"/(excerpt["id"]+"_good.wav")
                audio.parent.mkdir(parents=True,exist_ok=True)
                sf.write(audio,y[round(a*sr):round(b*sr)],sr,subtype="PCM_16")
                cropped,_=sf.read(audio,dtype="float32")
                aligned=align(cropped,text,object_hash([sha256_file(audio),text["sha256"],PIPELINE]))
                write_json(ROOT/"data/transcripts"/(excerpt["id"]+".json"),{**text,"provenance":source["transcript_url"],"review_status":"source_text_machine_alignment_human_correction_pending"})
                write_json(ROOT/"data/alignments"/(excerpt["id"]+"_good.json"),aligned)
                write_json(ROOT/"data/events"/(excerpt["id"]+"_good.json"),{"events":[],"negative_review_status":"pending","label_kind":"unreviewed_reference"})
                rows.append({"recording_id":excerpt["id"]+"_good","pair_group_id":excerpt["id"],"reference_id":excerpt["id"]+"_good",
                    "speaker_id":source.get("speaker_id",source["id"]),"source_recording_id":source["id"],"transcript_id":excerpt["id"],"transcript_sha256":text["sha256"],
                    "audio_path":"audio/"+audio.name,"audio_sha256":sha256_file(audio),"sample_rate_hz":sr,"duration_s":len(cropped)/sr,
                    "generation_method":"reference","flaw_family":"accepted","severity_label":0,"split":source["split"],
                    "alignment_path":"alignments/"+excerpt["id"]+"_good.json","events_path":"events/"+excerpt["id"]+"_good.json",
                    "provenance_id":source["id"],"review_status":"pending","title":source["speaker"]+" / "+excerpt["id"],
                    "source_crop_s":[a+source["candidate_start_s"],b+source["candidate_start_s"]],"alignment_coverage":aligned["coverage"]})
                print("Retained provisional",excerpt["id"],round(len(cropped)/sr,2),aligned["coverage"],flush=True)
        except Exception as error:
            failures.append({"source":source["id"],"reason":str(error)})
            print("Source failure",source["id"],str(error),flush=True)
    manifest=ROOT/"data/manifests/references.jsonl"
    manifest.parent.mkdir(parents=True,exist_ok=True)
    manifest.write_text("\n".join(json.dumps(r) for r in rows)+"\n",encoding="utf-8")
    write_json(ROOT/"data/provenance/excluded_sources.json",failures)
    print("Collected",len(rows),"provisional excerpts; human acceptance remains pending.")

if __name__=="__main__":
    collect()
