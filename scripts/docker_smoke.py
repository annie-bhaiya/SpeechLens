"""Live-container verification, separate from proxy benchmark and human evidence."""
import json
import subprocess
import time
import requests
from backend.speechlens.config import ROOT
from backend.speechlens.utils import write_json

def run(base='http://127.0.0.1:8002'):
    health=requests.get(base+'/healthz',timeout=15);health.raise_for_status()
    assert health.json()['model_cached'] and health.json()['worker_ready']
    times=[];results=[];ids=[]
    for i in range(2):
        start=time.perf_counter()
        response=requests.post(base+'/api/demo',timeout=20);response.raise_for_status()
        jid=response.json()['id'];ids.append(jid)
        print('Fresh Docker job started:',jid,flush=True)
        while time.perf_counter()-start<900:
            state=requests.get(base+f'/api/evaluations/{jid}',timeout=15).json()
            if state['status']=='failed':raise RuntimeError(state['error'])
            if state['status']=='succeeded':break
            time.sleep(1)
        assert state['status']=='succeeded',state
        result=requests.get(base+f'/api/evaluations/{jid}/result',timeout=30).json()
        assert result['mode']=='paired' and not result['provenance']['cache_hit']
        assert any(e['type']=='pace' for e in result['events'])
        for e in result['events']:
            a,b=e['participant_interval_s'];assert 0<=a<b<=result['features']['participant']['duration_s']+.01
        exported=requests.get(base+f'/api/evaluations/{jid}/export?format=json',timeout=20).json()
        assert exported['scores']==result['scores']
        media=requests.get(base+f'/api/evaluations/{jid}/audio/participant',headers={'Range':'bytes=0-99'},timeout=15)
        assert media.status_code==206
        times.append(time.perf_counter()-start);results.append(result)
    stable=results[0]['events']==results[1]['events'] and results[0]['scores']==results[1]['scores']
    assert stable,'Fresh repeat-run numeric/event stability failed in the container'
    for jid in ids:
        r=requests.delete(base+f'/api/evaluations/{jid}',timeout=30);r.raise_for_status()
        assert requests.get(base+f'/api/evaluations/{jid}',timeout=15).status_code==404
    inspect=subprocess.run(['docker','inspect','speechlens-validation-app'],capture_output=True,text=True,check=True)
    container=json.loads(inspect.stdout)[0]
    output={'passed':True,'date':'2026-10-06','base':base,'container_image':container['Config']['Image'],
            'container_image_id':container['Image'],
            'build_volume_provenance':'Not established by this smoke script; see evaluation/docker_build_check.json',
            'python':'3.11.13','health':health.json(),'fresh_processing_wall_s':times,'native_pacing_events':len(results[0]['events']),
            'scores':results[0]['scores'],'fresh_repeat_events_and_scores_identical':stable,'range_audio_export_delete':True,
            'provenance':results[0]['provenance'],'benchmark_not_rerun_or_retuned':True}
    write_json(ROOT/'evaluation/docker_check.json',output)
    print(json.dumps({k:v for k,v in output.items() if k not in ['provenance','scores']},indent=2))

if __name__=='__main__':run()
