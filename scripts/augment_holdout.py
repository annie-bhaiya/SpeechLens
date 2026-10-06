"""Noise is a held-out generation method: test sources only, no rule fitting."""
import json
import numpy as np
import soundfile as sf
from backend.speechlens.config import ROOT,PIPELINE
from backend.speechlens.utils import object_hash,sha256_file,write_json
from backend.speechlens.text import phrase_ids
from backend.speechlens.transforms import apply_edits,propagate_words
from backend.speechlens.alignment import align

def augment():
    path=ROOT/'data/manifests/recordings.jsonl'
    rows=[json.loads(l) for l in path.read_text().splitlines() if l]
    existing={r['recording_id'] for r in rows}
    for ref in [r for r in rows if r['generation_method']=='reference' and r['split']=='test']:
        text=json.loads((ROOT/'data/transcripts'/(ref['transcript_id']+'.json')).read_text())
        alignment=json.loads((ROOT/'data'/ref['alignment_path']).read_text())
        y,sr=sf.read(ROOT/'data'/ref['audio_path'],dtype='float32')
        ids=next(ids for ids in phrase_ids(text) if len(ids)>=4 and all(alignment['words'][i]['start_s'] is not None for i in ids))
        a,b=alignment['words'][ids[0]]['start_s'],alignment['words'][ids[-1]]['end_s']
        seed=int(object_hash(ref['pair_group_id']+'heldout-noise')[:8],16)
        for level,snr in enumerate([30,20,10,0],1):
            rid=ref['pair_group_id']+f'_heldout_noise_level{level}'
            if rid in existing:continue
            print('Held-out method',rid,flush=True)
            audio=ROOT/'data/audio'/(rid+'.wav')
            signal,mapping,events=apply_edits(y,[{'start_s':a,'end_s':b,'kind':'noise_proxy','snr_db':snr,'family':'clarity_proxy','severity':level,'token_ids':ids}],seed)
            sf.write(audio,signal,sr,subtype='PCM_16')
            actual,_=sf.read(audio,dtype='float32')
            aligned=align(actual,text,object_hash([sha256_file(audio),text['sha256'],PIPELINE]))
            write_json(ROOT/'data/alignments'/(rid+'.json'),aligned)
            write_json(ROOT/'data/events'/(rid+'.json'),{'events':events,'time_map':mapping,'propagated_words':propagate_words(alignment['words'],mapping),
                       'negative_review_status':'pending','label_kind':'transformation_support_not_perceptual_ground_truth'})
            rows.append({**ref,'recording_id':rid,'audio_path':'audio/'+audio.name,'audio_sha256':sha256_file(audio),
                'generation_method':'local_noise_proxy','flaw_family':'clarity_proxy','severity_label':level,'duration_s':len(actual)/sr,
                'alignment_path':'alignments/'+rid+'.json','events_path':'events/'+rid+'.json','alignment_coverage':aligned['coverage'],
                'holdout_generation_method':True,'seed':seed,'review_status':'pending','signal_quality':{'clipped_fraction':float(np.mean(np.abs(actual)>=.999))}})
    path.write_text('\n'.join(json.dumps(r) for r in rows)+'\n',encoding='utf-8')
    return rows

if __name__=='__main__':augment()
