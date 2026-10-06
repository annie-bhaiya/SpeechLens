"""Measured intervention-support benchmarks; human validity stays unmeasured."""
import argparse
import csv
import json
import platform
import time
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict
import numpy as np
from scipy.stats import spearmanr
from backend.speechlens.config import ROOT,PIPELINE,DETECTORS
from backend.speechlens.pipeline import run,version_fingerprint
from backend.speechlens.utils import write_json,object_hash
from backend.speechlens.evaluation import match_events,summarize_counts
from scripts.validate_dataset import validate

TYPE={"pace":"pace","intonation":"intonation","pauses":"pauses","energy":"energy","clarity_proxy":"recording_quality"}
CATEGORY={"pace":"pacing","intonation":"intonation","pauses":"pauses","energy":"energy"}

def measured_task(pair):
    row,reference=pair
    rid=row['recording_id']
    print('Evaluating',rid,flush=True)
    text=json.loads((ROOT/'data/transcripts'/(row['transcript_id']+'.json')).read_text())['display_text']
    started=time.perf_counter()
    result=run(ROOT/'data'/row['audio_path'],text,ROOT/'.cache/evaluation'/rid,ROOT/'data'/reference['audio_path'],text)
    return row,result,time.perf_counter()-started

def evaluate(split="all",workers=1):
    from scripts.augment_holdout import augment
    augment()
    integrity=validate()
    if not integrity["integrity_passed"]:
        raise ValueError("Dataset integrity failed")
    rows=[json.loads(line) for line in (ROOT/"data/manifests/recordings.jsonl").read_text().splitlines() if line]
    lookup={r["recording_id"]:r for r in rows}
    if split!="all":
        rows=[r for r in rows if r["split"]==split]
    freeze={"pipeline":PIPELINE,"detectors":DETECTORS,"code":version_fingerprint(),"selection":"No fitting; engineering tolerances frozen before benchmark"}
    write_json(ROOT/"evaluation/frozen_config.json",freeze)
    by_split=defaultdict(lambda:defaultdict(lambda:{"tp":0,"fp":0,"fn":0,"onset_errors":[],"offset_errors":[]}))
    failures,latencies,all_events,gradients=[],[],[],defaultdict(list)
    audits=[]
    alignment_rows=[]
    method_counts={str(c):{'tp':0,'fp':0,'fn':0} for c in [.3,.5]}
    condition_counts=defaultdict(lambda:{'tp':0,'fp':0,'fn':0,'recordings':0})
    controls=defaultdict(lambda:{"events":0,"minutes":0,"duration_s":0,"recordings":0})
    scores={}
    started=time.perf_counter()
    def measured(row):
        return measured_task((row,lookup[row['reference_id']]))
    def outputs():
        # Warm every reference before parallel variants so shared reference
        # feature/alignment cache files are read rather than concurrently written.
        for row in rows:
            if row['generation_method']=='reference':
                yield measured(row)
        variants=[r for r in rows if r['generation_method']!='reference']
        if workers==1:
            yield from map(measured,variants)
        else:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                yield from executor.map(measured_task,[(r,lookup[r['reference_id']]) for r in variants])
    for row,result,elapsed in outputs():
        rid=row['recording_id']
        score=result["scores"]["total"]
        category_scores={k:v["score"] for k,v in result["scores"]["categories"].items()}
        scores[rid]={"score":score,"events":len(result["events"]),"category_scores":category_scores,
                     "coverage":result["scores"]["coverage"],"cache_hit":result["provenance"]["cache_hit"]}
        alignment_rows.append({'recording_id':rid,'speaker_id':row['speaker_id'],'split':row['split'],
            'condition':row['flaw_family'],'level':row['severity_label'],
            'coverage':result['alignments']['participant']['coverage'],
            'asr_match_fraction':result['alignments']['participant']['asr_match_fraction'],
            'independent_boundary_error':None})
        label=json.loads((ROOT/"data"/row["events_path"]).read_text())
        truth=[{"type":TYPE[e["family"]],"interval_s":[e["target_start_s"],e["target_end_s"]]} for e in label["events"] if e["family"] in TYPE and e["severity"]>0]
        pred=[{"type":e["type"],"interval_s":e["participant_interval_s"]} for e in result["events"]]
        for cutoff in [.3,.5]:
            for family in TYPE.values():
                ps=[p for p in pred if p["type"]==family]
                ts=[t for t in truth if t["type"]==family]
                counts=match_events(ps,ts,cutoff)
                if row.get('holdout_generation_method'):
                    for key in ['tp','fp','fn']:method_counts[str(cutoff)][key]+=counts[key]
                if cutoff==.5:
                    condition=f"{row['split']}/{'near_perfect' if row['severity_label']==1 else row['flaw_family']}"
                    for key in ['tp','fp','fn']:condition_counts[condition][key]+=counts[key]
                    if family=='pace':condition_counts[condition]['recordings']+=1
                accumulator=by_split[row["split"]][str(cutoff)+"/"+family]
                for key in ["tp","fp","fn"]:
                    accumulator[key]+=counts[key]
                for i,j,iou in counts["matches"]:
                    accumulator["onset_errors"].append(abs(ps[i]["interval_s"][0]-ts[j]["interval_s"][0]))
                    accumulator["offset_errors"].append(abs(ps[i]["interval_s"][1]-ts[j]["interval_s"][1]))
                if cutoff==.5 and (counts["fp"] or counts["fn"]):
                    failures.append({"recording_id":rid,"split":row["split"],"type":family,**{k:counts[k] for k in ["tp","fp","fn"]},
                                    "reason":"Mismatch against synthetic support; human perceptual truth is unavailable."})
        if row["severity_label"]==0:
            control=controls[row["split"]]
            control["events"]+=len(pred)
            control["minutes"]+=row["duration_s"]/60
            control["duration_s"]+=union_duration([e["interval_s"] for e in pred])
            control["recordings"]+=1
        family=row["flaw_family"]
        if family in CATEGORY:
            category_score=category_scores[CATEGORY[family]]
            if category_score is not None:
                gradients[(row["pair_group_id"],family)].append((row["severity_label"],100-category_score))
        latencies.append({"recording_id":rid,"split":row["split"],"duration_s":row["duration_s"],"wall_s":elapsed,
                          "memory":result["provenance"].get("runtime"),
                          "processing_s":result["provenance"]["processing_s"],"cache_hit":result["provenance"]["cache_hit"]})
        for event in result["events"]:
            expected_quote=(" / ".join if event['type']=='pauses' else " ".join)(result['transcript']['tokens'][i]['text'] for i in event['token_ids'])
            audits.append({'recording_id':rid,'event_id':event['id'],'quote_matches':event['quote']==expected_quote,
                           'native_interval_valid':0<=event['participant_interval_s'][0]<=event['participant_interval_s'][1]<=row['duration_s'],
                           'numeric_values_present':isinstance(event['measurements']['participant'],(int,float)),
                           'rule_and_thresholds_present':bool(event['rule_id'] and event['thresholds'])})
            all_events.append({"recording_id":rid,"split":row["split"],"type":event["type"],"severity":event["severity"],
                               "start_s":event["participant_interval_s"][0],"end_s":event["participant_interval_s"][1],
                               "rule_id":event["rule_id"],"participant_value":event["measurements"]["participant"],"reference_value":event["measurements"]["reference"]})
        write_json(ROOT/"evaluation/recording_scores.json",scores)
    localization={}
    for s,types in by_split.items():
        localization[s]={}
        for key,counts in types.items():
            localization[s][key]={**summarize_counts(counts),"mean_onset_error_s":float(np.mean(counts["onset_errors"])) if counts["onset_errors"] else None,
                                 "mean_offset_error_s":float(np.mean(counts["offset_errors"])) if counts["offset_errors"] else None,
                                 "matched_events":len(counts["onset_errors"]),"missed_events":counts["fn"]}
    ordering=[]
    for (source,family),values in gradients.items():
        values.sort()
        levels,penalties=zip(*values)
        rho=float(spearmanr(levels,penalties).statistic) if len(set(penalties))>1 else None
        pairs=[(i,j) for i in range(len(values)) for j in range(i+1,len(values))]
        ordering.append({"source":source,"family":family,"n":len(values),"spearman":rho,
                         "pairwise_strict_ordering_accuracy":sum(penalties[j]>penalties[i] for i,j in pairs)/len(pairs) if pairs else None,
                         "monotonicity_violations":sum(penalties[j]<penalties[i] for i,j in pairs),"levels":list(levels),"penalties":list(penalties)})
        ordering[-1]['sum_downward_adjacent_penalty_points']=sum(max(0,penalties[i]-penalties[i+1]) for i in range(len(penalties)-1))
    for s,c in controls.items():
        c["false_events_per_minute_proxy"]=c["events"]/c["minutes"] if c["minutes"] else None
        c["negative_review_status"]="unreviewed synthetic accepted/sham controls; not reviewed human negatives"
    ratios=[l["processing_s"]/l["duration_s"] for l in latencies if not l["cache_hit"]]
    f1s=[v["f1"] for k,v in localization.get("test",{}).items() if k.startswith("0.5/") and v["f1"] is not None]
    correlations=[o["spearman"] for o in ordering if o["spearman"] is not None]
    aggregates={}
    for s,types in localization.items():
        aggregates[s]={}
        for cutoff in ['0.3','0.5']:
            selected=[v for k,v in types.items() if k.startswith(cutoff+'/')]
            counts={k:sum(v[k] for v in selected) for k in ['tp','fp','fn']}
            valid=[v['f1'] for v in selected if v['f1'] is not None]
            aggregates[s][cutoff]={'micro':summarize_counts(counts),'macro_f1':float(np.mean(valid)) if valid else None}
    metrics={"benchmark_kind":"synthetic_intervention_support_proxy_not_perceptual_accuracy","dataset_integrity":integrity,
        "evaluated_recordings":len(rows),"configuration_hash":object_hash(freeze),"localization":localization,
        "localization_aggregates":aggregates,
        "held_out_generation_method":{"method":"local_noise_proxy","split":"test only","n":sum(r.get('holdout_generation_method',False) for r in rows),"thresholds_tuned_on_method":False,
            'localization':{c:summarize_counts(v) for c,v in method_counts.items()}},
        'condition_localization_tiou_0_5':{c:{**summarize_counts(v),'recordings':v['recordings']} for c,v in condition_counts.items()},
        'alignment_coverage_by_speaker':{s:{'n':sum(a['speaker_id']==s for a in alignment_rows),
            'mean_coverage':float(np.mean([a['coverage'] for a in alignment_rows if a['speaker_id']==s])),
            'independent_boundary_accuracy':None} for s in sorted({a['speaker_id'] for a in alignment_rows})},
        "explanation_audit":{"events_audited":len(audits),'all_quote_clock_value_rule_checks_passed':all(all(a[k] for k in ['quote_matches','native_interval_valid','numeric_values_present','rule_and_thresholds_present']) for a in audits),'human_advice_usefulness':None},
        "held_out_test_macro_f1_tiou_0_5_proxy":float(np.mean(f1s)) if f1s else None,
        "severity_ordering":ordering,"median_spearman_proxy":float(np.median(correlations)) if correlations else None,
        "controls":dict(controls),"human_alignment_boundary_accuracy":None,"independent_human_agreement":None,
        "human_generalization":None,"human_recordings":0,"independent_reviewers":0,
        "confidence_intervals":None,"uncertainty_note":"Only one held-out test speaker. No informative group-bootstrap interval or human validity claim.",
        "runtime":{"platform":platform.platform(),"device":"CPU","benchmark_wall_s":time.perf_counter()-started,
                   'benchmark_concurrent_variants':workers,
                   "median_processing_s_per_audio_s":float(np.median(ratios)) if ratios else None,
                   "peak_memory_mb":max((l["memory"]["process_lifetime_peak_resident_mb"] for l in latencies if l["memory"]),default=None),
                   "cold_warm_note":"References warmed serially, variants use the stated process concurrency. Per-recording cache flags/timings in runtime.json include contention; app worker is serial. First inference per process includes model initialization. Peak memory is maximum per-process lifetime high water, not aggregate worker-pool memory."},
        "gates":{"synthetic_macro_f1_target":.75,"synthetic_macro_f1_passed":bool(f1s and np.mean(f1s)>=.75),
                 "severity_spearman_target":.8,"severity_spearman_passed":bool(correlations and np.median(correlations)>=.8),
                 "human_alignment_gate":"unmeasured","human_reviews_gate":"blocked","clean_container_gate":"Docker daemon unavailable"}}
    write_json(ROOT/"evaluation/metrics.json",metrics)
    write_json(ROOT/"evaluation/runtime.json",latencies)
    write_json(ROOT/"evaluation/failure_cases/localization.json",failures)
    write_json(ROOT/"evaluation/explanation_audit.json",audits)
    write_json(ROOT/'evaluation/alignment_coverage.json',alignment_rows)
    write_csv(ROOT/"evaluation/per_event.csv",all_events)
    make_plots(ordering,localization)
    print(json.dumps({"recordings":len(rows),"test_macro_f1_proxy":metrics["held_out_test_macro_f1_tiou_0_5_proxy"],"median_spearman_proxy":metrics["median_spearman_proxy"]},indent=2))
    return metrics

def union_duration(intervals):
    merged=[]
    for a,b in sorted(intervals):
        if merged and a<=merged[-1][1]:
            merged[-1][1]=max(merged[-1][1],b)
        else:
            merged.append([a,b])
    return sum(b-a for a,b in merged)

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as file:
        if rows:
            writer=csv.DictWriter(file,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

def make_plots(ordering,localization):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':14,'axes.titlesize':16,'axes.labelsize':15,'xtick.labelsize':14,'ytick.labelsize':14})
    directory=ROOT/"evaluation/plots"
    directory.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,4,figsize=(12,3),sharey=True)
    for ax,family in zip(axes,CATEGORY):
        for row in ordering:
            if row["family"]==family:
                ax.plot(row['levels'],row["penalties"],alpha=.6,marker='o',markersize=3,label=row["source"])
        ax.set(title=family,xlabel="Injected level",xticks=[1,2,3,4],ylim=(0,100))
        ax.grid(alpha=.2)
    axes[0].set_ylabel("Penalty / 100")
    fig.suptitle("Synthetic severity ordering - no human perceptual ratings",fontsize=16)
    fig.tight_layout()
    fig.savefig(directory/"severity.png",dpi=170)
    plt.close(fig)
    test=localization.get("test",{})
    selected={k.split('/')[1]:v["f1"] or 0 for k,v in test.items() if k.startswith("0.5/")}
    fig,ax=plt.subplots(figsize=(7,3))
    ax.bar(selected.keys(),selected.values(),color="#087f89")
    ax.set(ylim=(0,1),ylabel="Event F1 against intervention support",title="Held-out speaker - tIoU 0.5 synthetic proxy")
    fig.tight_layout()
    fig.savefig(directory/"localization.png",dpi=170)
    plt.close(fig)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--split",choices=["all","train","validation","test"],default="all")
    parser.add_argument('--workers',type=int,choices=range(1,5),default=1,help='Bounded offline benchmark concurrency; app inference remains serial.')
    args=parser.parse_args()
    evaluate(args.split,args.workers)
