"""Actual model tests for missing/repeated words and unpaired abstention."""
import json
from pathlib import Path
from backend.speechlens.config import ROOT
from backend.speechlens.pipeline import run
from backend.speechlens.utils import write_json

def checks():
    rows=[json.loads(l) for l in (ROOT/'data/manifests/recordings.jsonl').read_text().splitlines() if l]
    ref=next(r for r in rows if r['generation_method']=='reference' and r['alignment_coverage']>=.99)
    path=ROOT/'data'/ref['audio_path']
    text=json.loads((ROOT/'data/transcripts'/(ref['transcript_id']+'.json')).read_text())['display_text']
    out=ROOT/'.cache/model_integration'
    unpaired=run(path,text,out/'unpaired')
    assert unpaired['scores']['total'] is None
    assert set(unpaired['features'])=={'participant'}
    assert not any(e['type']!='recording_quality' for e in unpaired['events'])
    mismatch='Purple elephants silently rearrange the northern telescope. Unrelated invented speech content.'
    wrong=run(path,mismatch,out/'mismatch',path,mismatch)
    assert wrong['scores']['total'] is None
    assert wrong['alignments']['participant']['asr_match_fraction']<.6
    repeated=text.replace('my fellow Americans','my fellow fellow Americans')
    repeat=run(path,repeated,out/'repetition',path,repeated)
    assert repeat['alignments']['participant']['edits']
    # Inserted intended token must remain uncertain rather than a confident ASR equality.
    fellow=[w for w in repeat['alignments']['participant']['words'] if w['text'].lower()=='fellow']
    assert len(fellow)==2 and any(not w['recognized_match'] for w in fellow)
    try:
        run(path,text,out/'different_text',path,mismatch)
        raise AssertionError('Different reference text accepted')
    except ValueError as error:
        assert 'transcripts differ' in str(error)
    result={'passed':True,'reference_id':ref['recording_id'],'unpaired_score':None,'unpaired_reference_absent':True,
            'severe_mismatch_score':None,'severe_mismatch_match_fraction':wrong['alignments']['participant']['asr_match_fraction'],
            'repeated_token_edit_report':repeat['alignments']['participant']['edits'],
            'mismatched_reference_rejected':True,'model_revision':wrong['alignments']['participant']['revision']}
    write_json(ROOT/'evaluation/model_integration.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':checks()
