from .config import PRESETS, PIPELINE

def aggregate(units, preset="persuasive_oratory", weights=None, paired=True):
    if preset not in PRESETS:
        raise ValueError("Unknown rubric preset.")
    weights = weights or PRESETS[preset]["weights"]
    if set(weights)!=set(PRESETS[preset]["weights"]) or any(not isinstance(v,(int,float)) or not 0<=v<=1 for v in weights.values()) or sum(weights.values())<=0:
        raise ValueError("Weights must name all five categories, be finite in [0,1], and have positive sum.")
    categories={}
    for key, rows in units.items():
        # Identical unit evidence is combined by maximum, never counted repeatedly.
        disjoint={}
        for row in rows:
            existing=disjoint.get(row["id"])
            if existing is None or row["severity"]>existing["severity"]:
                disjoint[row["id"]]=row
        all_exposure=sum(u["exposure"] for u in disjoint.values())
        supported=[u for u in disjoint.values() if u["eligible"]]
        exposure=sum(u["exposure"] for u in supported)
        score=100*(1-sum(u["exposure"]*u["severity"] for u in supported)/exposure) if exposure else None
        categories[key]={"score":round(score,1) if score is not None else None,
                         "coverage":exposure/all_exposure if all_exposure else 0,
                         "weight":weights[key],"eligible_units":len(supported),"total_units":len(disjoint),
                         "status":"diagnostic_only" if key=="clarity" else "uncalibrated" if score is not None else "insufficient_evidence"}
    included=[k for k,v in categories.items() if v["score"] is not None and weights[k]>0]
    denominator=sum(weights[k] for k in included)
    # Clarity is diagnostic-only, so required coverage denominator excludes its weight.
    scoring_weight=sum(weights[k] for k in weights if k!="clarity")
    coverage=sum(weights[k]*categories[k]["coverage"] for k in included)/scoring_weight if scoring_weight else 0
    total=sum(weights[k]*categories[k]["score"] for k in included)/denominator if denominator else None
    if not paired or coverage<PIPELINE["coverage_floor"]:
        total=None
    return {"total":round(total,1) if total is not None else None,"coverage":coverage,"categories":categories,
            "included_weights":{k:weights[k]/denominator for k in included} if denominator else {},
            "preset":preset,"rubric_version":PRESETS[preset]["version"],
            "status":"uncalibrated_paired" if total is not None else "insufficient_evidence" if paired else "unpaired_diagnostics",
            "shared_cause_policy":"Separate dimension scores; compound totals are not independent causal effects.",
            "clarity_note":"No validated human intelligibility evidence; clarity excluded and remaining weights renormalized."}
