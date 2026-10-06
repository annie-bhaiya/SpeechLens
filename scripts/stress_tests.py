import json
import time
import numpy as np
import soundfile as sf
import librosa
from backend.speechlens.config import ROOT
from backend.speechlens.pipeline import run
from backend.speechlens.utils import write_json,object_hash
from backend.speechlens.features import extract,robust_range

def stress():
    rows=[json.loads(l) for l in (ROOT/'data/manifests/recordings.jsonl').read_text().splitlines() if l]
    reference=min((r for r in rows if r['generation_method']=='reference' and r['split']=='train' and r['alignment_coverage']>=.99),key=lambda r:r['duration_s'])
    path=ROOT/'data'/reference['audio_path']
    text=json.loads((ROOT/'data/transcripts'/(reference['transcript_id']+'.json')).read_text())['display_text']
    y,sr=sf.read(path,dtype='float32')
    out=ROOT/'.cache/stress'
    out.mkdir(parents=True,exist_ok=True)
    baseline=run(path,text,out/'baseline',path,text)
    checks=[]
    for name,signal,rate in [('gain_minus6',y*10**(-6/20),sr),('gain_plus6',y*10**(6/20),sr),
                             ('resample_22050',librosa.resample(y,orig_sr=sr,target_sr=22050),22050),
                             ('pitch_plus2st',librosa.effects.pitch_shift(y,sr=sr,n_steps=2),sr),
                             ('noise_10db',y+np.random.default_rng(2026).normal(0,np.sqrt(np.mean(y*y))*10**(-10/20),len(y)),sr),
                             ('clipped',np.clip(y*12,-1,1),sr)]:
        transformed=out/(name+'.wav')
        sf.write(transformed,signal,rate,subtype='FLOAT')
        result=run(transformed,text,out/name,path,text)
        a,b=baseline['scores']['total'],result['scores']['total']
        shift=abs(a-b) if a is not None and b is not None else None
        checks.append({'condition':name,'baseline_score':a,'score':b,'absolute_score_shift':shift,
                       'events':len(result['events']),'coverage':result['scores']['coverage'],
                       'quality':result['features']['participant']['quality'],
                       'gain_gate_passed':bool(shift is not None and shift<=3) if name.startswith('gain') else None,
                       'note':'Actual measured output. Pitch-shift resynthesis is not artifact-free.'})
        print(name,checks[-1],flush=True)
    # Real codec round-trip; format metadata is not an inference feature.
    from backend.speechlens.ingest import ffmpeg_executable
    import subprocess
    encoded=out/'aac_128kbps.m4a'
    subprocess.run([ffmpeg_executable(),'-v','error','-y','-i',str(path),'-c:a','aac','-b:a','128k',str(encoded)],check=True,timeout=60)
    encoded_result=run(encoded,text,out/'aac_128kbps',path,text)
    a,b=baseline['scores']['total'],encoded_result['scores']['total']
    checks.append({'condition':'aac_128kbps','baseline_score':a,'score':b,'absolute_score_shift':abs(a-b) if a is not None and b is not None else None,'events':len(encoded_result['events']),'coverage':encoded_result['scores']['coverage'],'quality':encoded_result['features']['participant']['quality'],'gain_gate_passed':None,'note':'Actual AAC encoding and decoding, not simulated compression.'})
    # Repeated fresh inference, excluding cache hits, should retain event IDs and displayed scores.
    variant=next(r for r in rows if r['pair_group_id']==reference['pair_group_id'] and r['flaw_family']=='pace' and r['severity_label']==4)
    first=run(ROOT/'data'/variant['audio_path'],text,out/'repeat1',path,text,use_cache=False)
    second=run(ROOT/'data'/variant['audio_path'],text,out/'repeat2',path,text,use_cache=False)
    signature=lambda r:{'events':[{k:e[k] for k in ['id','type','participant_interval_s','measurements','severity']} for e in r['events']], 'scores':r['scores']}
    repeat=object_hash(signature(first))==object_hash(signature(second))
    write_json(ROOT/'evaluation/robustness.json',{'reference_id':reference['recording_id'],'conditions':checks,
        'configuration_hash':first['provenance']['hashes']['configuration'],
        'repeat_run':{'cache_used':False,'same_events_scores_and_measurements':repeat,'tolerance':'exact JSON values in this CPU environment'},
        'human_generalization':None,'clean_container_run':None,'clean_container_reason':'Docker daemon unavailable'})
    # Observable ablations, not a tuned alternative model: compare raw center offsets vs normalized residuals.
    raw=extract(y)
    gain=extract(y*10**(-6/20))
    voiced=np.asarray(raw['pitch']['semitones'])
    energy=np.asarray(raw['spectral']['energy_relative_db'])
    gain_energy=np.asarray(gain['spectral']['energy_relative_db'])
    shifted=extract(librosa.effects.pitch_shift(y,sr=sr,n_steps=2))
    raw_hz=np.asarray(raw['pitch']['f0_hz'],dtype=float)
    shifted_hz=np.asarray(shifted['pitch']['f0_hz'],dtype=float)
    ablation={'raw_vs_normalized_pitch':{'raw_voiced_median_hz':float(np.nanmedian(raw_hz)),'shifted_voiced_median_hz':float(np.nanmedian(shifted_hz)),
             'raw_semitone_center_shift':float(12*np.log2(np.nanmedian(shifted_hz)/np.nanmedian(raw_hz))),
             'relative_semitone_center_original':float(np.nanmedian(voiced)),
             'relative_semitone_center_shifted':float(np.nanmedian(np.asarray(shifted['pitch']['semitones'],dtype=float))),
             'note':'Relative centering removes global offset mathematically; full pipeline pitch-shift robustness can still fail alignment.'},
        'raw_vs_normalized_energy':{'raw_median_dbfs_shift':gain['quality']['median_speech_dbfs']-raw['quality']['median_speech_dbfs'],
             'relative_energy_median_abs_delta_db':float(np.median(np.abs(energy-gain_energy))),
             'energy_range_preserved_db':robust_range(energy)},
        'native_vs_warped_duration':{'native_phrase_ratios':[e['measurements']['duration_ratio'] for e in first['events'] if e['type']=='pace'],
                                    'within_token_progress_duration':1.0,'note':'A token-progress axis collapses duration by definition; scoring uses native elapsed seconds.'},
        'alignment_gating':{'eligible_phrase_count':sum(p['participant']['eligible'] for p in first['comparison']['phrases']),
                            'all_phrase_count':len(first['comparison']['phrases']),'counterfactual_detector_accuracy':None},
        'single_vs_compound':'See per-recording results and per-event.csv; no independent human causal rating.',
        'ordinary_vs_sham':'See evaluation control event counts, reported separately by condition in recording_scores.json.',
        'synthetic_vs_human':{'synthetic_available':True,'human_n':0,'human_metrics':None}}
    write_json(ROOT/'evaluation/ablations/measured.json',ablation)
    return checks

if __name__=='__main__':
    stress()
