import numpy as np
from scipy.optimize import linear_sum_assignment

def tiou(a,b):
    intersection=max(0,min(a[1],b[1])-max(a[0],b[0]))
    union=max(a[1],b[1])-min(a[0],b[0])
    return intersection/union if union>0 else 0.0

def match_events(predictions,truth,cutoff=.5):
    # A cardinality bonus prevents one high-IoU match from displacing two eligible matches.
    matrix=np.zeros((len(predictions),len(truth)))
    for i,p in enumerate(predictions):
        for j,t in enumerate(truth):
            overlap=tiou(p["interval_s"],t["interval_s"])
            if p["type"]==t["type"] and overlap>=cutoff:
                matrix[i,j]=min(len(predictions),len(truth))+1+overlap
    matches=[]
    if matrix.size:
        a,b=linear_sum_assignment(-matrix)
        matches=[(int(i),int(j),tiou(predictions[i]["interval_s"],truth[j]["interval_s"])) for i,j in zip(a,b) if matrix[i,j]>0]
    tp=len(matches)
    return {"tp":tp,"fp":len(predictions)-tp,"fn":len(truth)-tp,"matches":matches}

def summarize_counts(counts):
    tp,fp,fn=counts["tp"],counts["fp"],counts["fn"]
    return {**{k:counts[k] for k in ["tp","fp","fn"]},"precision":tp/(tp+fp) if tp+fp else None,
            "recall":tp/(tp+fn) if tp+fn else None,"f1":2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
