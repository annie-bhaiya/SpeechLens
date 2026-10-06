"""Capture an actual 6-minute app walkthrough with synchronized caption/A-B audio.

No canned result replaces inference. Browser video is silent; real source spans
played during capture are muxed at recorded timestamps, disclosed in metadata.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from backend.speechlens.config import ROOT
from backend.speechlens.ingest import ffmpeg_executable
from backend.speechlens.utils import write_json
from scripts.release_check import duration

def timestamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'

def video(base='http://127.0.0.1:8000'):
    rows=[json.loads(l) for l in (ROOT/'data/manifests/recordings.jsonl').read_text().splitlines() if l]
    reference=next(r for r in rows if r['generation_method']=='reference' and r['split']=='train' and r['alignment_coverage']>=.99)
    group=reference['pair_group_id']
    variant=next(r for r in rows if r['pair_group_id']==group and r['flaw_family']=='pace' and r['severity_label']==4)
    subtle=next(r for r in rows if r['pair_group_id']==group and r['flaw_family']=='pace' and r['severity_label']==1)
    control=next(r for r in rows if r['pair_group_id']==group and r['flaw_family']=='accepted_gain')
    text=json.loads((ROOT/'data/transcripts'/(reference['transcript_id']+'.json')).read_text())['display_text']
    directory=ROOT/'demo/recordings/walkthrough'
    directory.mkdir(parents=True,exist_ok=True)
    captions,audio_spans,captures=[],[],[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(directory),record_video_size={'width':1440,'height':1000},accept_downloads=True)
        page=context.new_page()
        origin=time.perf_counter()
        offset=0
        page.goto(base)
        def elapsed():return offset+time.perf_counter()-origin
        def hold(until):
            while elapsed()<until:
                time.sleep(min(.5,until-elapsed()))
        def caption(title,body,end):
            start=elapsed()
            captions.append({'start_s':start,'end_s':end,'text':title+'\n'+body})
            page.evaluate('''([title,body])=>{let box=document.getElementById('demo-caption');if(!box){box=document.createElement('div');box.id='demo-caption';box.style.cssText='position:fixed;bottom:18px;left:260px;right:26px;z-index:99999;background:#142235f0;color:white;border:1px solid #70b9bc;border-radius:8px;padding:18px 23px;font:16px/1.5 Arial;box-shadow:0 8px 25px #0003;pointer-events:none';document.body.appendChild(box)}box.replaceChildren();let h=document.createElement('strong');h.textContent=title;h.style.cssText='display:block;color:#81d7d2;font-size:19px;margin-bottom:4px';let b=document.createElement('span');b.textContent=body;box.append(h,b);}''',[title,body])
        caption('SpeechLens | same words, measured delivery','An actual local dashboard walkthrough. Experimental thresholds; human perceptual validation remains pending.',25)
        hold(25)
        page.get_by_role('button',name='Method & provenance',exact=True).click()
        caption('Data provenance and review','Public speeches carry source, transcript and rights evidence. Generator supports are separate from perceptual labels; no independent human annotation is claimed.',55)
        hold(40)
        page.locator('.method h3').nth(3).scroll_into_view_if_needed()
        hold(55)
        page.get_by_role('button',name='Dataset explorer',exact=True).click()
        page.get_by_label('Source excerpt',exact=True).select_option(group)
        page.get_by_label('Flaw family',exact=True).select_option('pace')
        page.get_by_role('button',name='LEVEL 0',exact=False).first.click()
        caption('One transcript, levels zero to four','The explorer shows measured scores when evaluation is available. Levels describe injected edits, not independently rated performance.',80)
        page.get_by_label('Dataset recording audio',exact=True).evaluate('(a)=>a.play()')
        start=elapsed();audio_spans.append({'offset_s':start,'path':reference['audio_path'],'start_s':0,'duration_s':min(9,reference['duration_s']),'label':'reference playback'})
        hold(start+min(9,reference['duration_s']))
        page.get_by_label('Dataset recording audio',exact=True).evaluate('(a)=>a.pause()')
        hold(80)
        page.get_by_role('button',name='LEVEL 1',exact=False).first.click()
        caption('Subtle intervention','Listen to a near-perfect local pacing variant. Small accepted differences should not automatically trigger a penalty.',101)
        page.get_by_label('Dataset recording audio',exact=True).evaluate('(a)=>a.play()')
        audio_spans.append({'offset_s':elapsed(),'path':subtle['audio_path'],'start_s':0,'duration_s':9,'label':'subtle variant playback'})
        hold(audio_spans[-1]['offset_s']+9)
        page.get_by_label('Dataset recording audio',exact=True).evaluate('(a)=>a.pause()')
        hold(101)
        page.get_by_role('button',name='LEVEL 4',exact=False).first.click()
        caption('Strong intervention','The strong local edit preserves intended words and pitch while changing native phrase duration. Its time map records the actual rendered sample count.',125)
        page.get_by_label('Dataset recording audio',exact=True).evaluate('(a)=>a.play()')
        audio_spans.append({'offset_s':elapsed(),'path':variant['audio_path'],'start_s':0,'duration_s':9,'label':'strong variant playback'})
        hold(audio_spans[-1]['offset_s']+9)
        page.get_by_label('Dataset recording audio',exact=True).evaluate('(a)=>a.pause()')
        hold(125)
        page.get_by_role('button',name='Speech analysis',exact=False).click()
        page.locator('#reference-select').select_option('upload')
        page.get_by_label('Reference audio',exact=True).set_input_files(str(ROOT/'data'/reference['audio_path']))
        page.locator('#reference-text').fill(text)
        page.get_by_label('Participant audio',exact=True).set_input_files(str(ROOT/'data'/variant['audio_path']))
        page.locator('#transcript').fill(text)
        page.get_by_role('checkbox').first.check()
        caption('Real upload and live CPU inference','The next result is computed from uploaded audio. The wait is shown in real time; no canned prediction or edited latency claim.',195)
        with page.expect_response(lambda r:r.url.endswith('/api/evaluations') and r.request.method=='POST') as request:
            page.get_by_role('button',name='Analyze delivery',exact=True).click()
        job_id=request.value.json()['id']
        page.locator('.job').scroll_into_view_if_needed()
        page.get_by_test_id('results').wait_for(timeout=900000)
        result=page.request.get(base+f'/api/evaluations/{job_id}/result').json()
        assert result['provenance']['cache_hit'] is False
        hold(max(195,elapsed()+3))
        page.locator('.score-grid').scroll_into_view_if_needed()
        caption('Scores include evidence coverage','Clarity is diagnostic-only. Missing alignment or voicing evidence produces abstention; a high total can still hide a short serious defect.',elapsed()+25)
        hold(elapsed()+25)
        page.locator('.acoustic-panel').scroll_into_view_if_needed()
        caption('Native time and normalized voice','Reference and participant retain separate clocks. Relative semitones and dB remove constant voice/gain offsets while preserving expressive range.',elapsed()+28)
        hold(elapsed()+14)
        page.get_by_role('button',name='Token comparison',exact=True).click()
        hold(elapsed()+14)
        page.get_by_role('button',name='Native time',exact=True).click()
        page.get_by_test_id('event-row').first.scroll_into_view_if_needed()
        page.get_by_test_id('event-row').first.click()
        page.locator('.evidence-grid').scroll_into_view_if_needed()
        event=next(e for e in result['events'] if e['type']=='pace')
        caption('A playable, mathematically grounded finding',f"Participant {event['measurements']['participant']:.2f} versus reference {event['measurements']['reference']:.2f} words/minute. Duration ratio {event['measurements']['duration_ratio']:.3f}. Advice follows this evidence.",elapsed()+35)
        page.get_by_role('button',name='Play participant span',exact=True).click()
        a,b=event['participant_interval_s']
        audio_spans.append({'offset_s':elapsed(),'path':variant['audio_path'],'start_s':a,'duration_s':b-a,'label':'detected participant span'})
        hold(elapsed()+max(9,b-a+1))
        page.get_by_role('button',name='Play reference span',exact=True).click()
        a,b=event['reference_interval_s']
        audio_spans.append({'offset_s':elapsed(),'path':reference['audio_path'],'start_s':a,'duration_s':b-a,'label':'matched reference span'})
        hold(elapsed()+max(9,b-a+1))
        page.locator('.explanation details summary').click()
        hold(elapsed()+12)
        page.locator('.rubric summary').click()
        page.get_by_label('Genre preset',exact=True).select_option('declamation')
        caption('Rubrics and reproducible exports','Preset weights are product choices, distinct from judging weights. Re-scoring reuses acoustic evidence and persists the selected rubric into the export.',elapsed()+25)
        hold(elapsed()+10)
        with page.expect_download() as downloaded:
            page.get_by_role('link',name='Evidence JSON',exact=True).click()
        downloaded.value.save_as(ROOT/'demo/exported_evidence.json')
        hold(elapsed()+15)
        page.get_by_role('button',name='Dataset explorer',exact=True).click()
        caption('Acceptable gain control and stress limits','Non-clipping plus/minus 6 dB copies changed the fixture score by zero points. Pitch-shift resynthesis caused alignment abstention; this failed robustness condition is disclosed.',elapsed()+28)
        page.get_by_label('Flaw family',exact=True).select_option('controls')
        page.get_by_test_id('record-'+control['recording_id']).click()
        with page.expect_response(lambda r:'/api/demo?' in r.url and r.request.method=='POST') as control_request:
            page.get_by_role('button',name='Process this recording',exact=True).click()
        control_job_id=control_request.value.json()['id']
        # A prior result can remain in the DOM while the request is in flight.
        # Wait on the new durable job before accepting its result element.
        while True:
            job=page.request.get(base+f'/api/evaluations/{control_job_id}').json()
            if job['status']=='succeeded':break
            if job['status']=='failed':raise RuntimeError(job.get('error','Control processing failed'))
            if elapsed()>540:raise RuntimeError('Control wait would exceed the video duration bound')
            time.sleep(.5)
        page.get_by_test_id('results').wait_for(timeout=900000)
        control_result=page.request.get(base+f'/api/evaluations/{control_job_id}/result').json()
        assert control_result['provenance']['hashes']['participant']==control['audio_sha256']
        assert control_result['provenance']['cache_hit'] is False
        assert control_result['scores']['total']==100
        page.locator('.score-grid').scroll_into_view_if_needed()
        hold(elapsed()+15)
        # Do not turn a potentially long offline benchmark wait into apparent
        # fast inference. The upload wait above remains fully captured. A later
        # benchmark segment is visibly identified as a separate recording.
        edited_benchmark_wait=False
        if not (ROOT/'evaluation/metrics.json').exists():
            capture=page.video.path()
            state=context.storage_state()
            context.close()
            captures.append(capture)
            deadline=time.perf_counter()+3600
            while not (ROOT/'evaluation/metrics.json').exists():
                if time.perf_counter()>deadline:
                    raise RuntimeError('Offline benchmark did not finish; main capture is retained for review.')
                time.sleep(2)
            offset=duration(Path(capture))
            context=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(directory),record_video_size={'width':1440,'height':1000},storage_state=state)
            page=context.new_page()
            origin=time.perf_counter()
            page.goto(base)
            edited_benchmark_wait=True
        page.get_by_role('button',name='Method & provenance',exact=True).click()
        caption('Later: measured benchmark and publication status' if edited_benchmark_wait else 'Measured evaluation and publication status','The offline benchmark has completed. Localization uses synthetic supports, not human truth. Human agreement and generalization are unmeasured; public publication remains blocked.',elapsed()+28)
        page.get_by_test_id('benchmark').scroll_into_view_if_needed()
        hold(elapsed()+28)
        caption('Reproduce locally','Run speechlens.ps1 setup, models, then serve. Inspect README, dataset card, six-page report, measured evaluation and blocker log. This is an upload-ready local demo, not a completed public submission.',max(384,elapsed()+25))
        hold(max(384,elapsed()+25))
        capture=page.video.path()
        context.close()
        captures.append(capture)
        browser.close()
    end=elapsed()
    for i,c in enumerate(captions):
        c['end_s']=captions[i+1]['start_s'] if i+1<len(captions) else end
    (ROOT/'demo/captions.vtt').write_text('WEBVTT\n\n'+'\n\n'.join(f"{i+1}\n{timestamp(c['start_s'])} --> {timestamp(c['end_s'])}\n{c['text']}" for i,c in enumerate(captions))+'\n',encoding='utf-8')
    (ROOT/'demo/transcript.md').write_text('# Actual walkthrough captions\n\n'+'\n\n'.join(f"{timestamp(c['start_s'])} - {c['text']}" for c in captions),encoding='utf-8')
    inputs=[]
    for capture in captures:inputs.extend(['-i',str(capture)])
    filters=[]
    video_map='0:v'
    if len(captures)>1:
        for i in range(len(captures)):filters.append(f'[{i}:v]setpts=PTS-STARTPTS[v{i}]')
        filters.append(''.join(f'[v{i}]' for i in range(len(captures)))+f'concat=n={len(captures)}:v=1:a=0[video]')
        video_map='[video]'
    audio_labels=[]
    for i,s in enumerate(audio_spans,len(captures)):
        inputs.extend(['-i',str(ROOT/'data'/s['path'])])
        filters.append(f"[{i}:a]atrim=start={s['start_s']}:duration={s['duration_s']},asetpts=PTS-STARTPTS,adelay={round(s['offset_s']*1000)}:all=1[a{i}]")
        audio_labels.append(f'[a{i}]')
    filters.append(''.join(audio_labels)+f'amix=inputs={len(audio_spans)}:normalize=0,apad=whole_dur={end},loudnorm=I=-18:TP=-1.5:LRA=11[audio]')
    output=ROOT/'demo/demo.mp4'
    subprocess.run([ffmpeg_executable(),'-v','error','-y',*inputs,'-filter_complex',';'.join(filters),'-map',video_map,'-map','[audio]',
                    '-t',str(end),'-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','128k','-movflags','+faststart',str(output)],check=True,timeout=300)
    seconds=duration(output)
    if not 180<=seconds<=600:raise ValueError(f'Video duration outside submission bounds: {seconds}')
    write_json(ROOT/'evaluation/video_check.json',{'duration_s':seconds,'job_id':job_id,'fresh_inference':True,'capture_paths':[str(Path(c).relative_to(ROOT)) for c in captures],
               'control_job_id':control_job_id,'control_source_hash_matches':True,'control_score':control_result['scores']['total'],
               'edit_policy':'Fresh upload inference wait is retained in real time. Offline benchmark waiting, if needed, is outside capture; final segment is visibly titled Later.' if edited_benchmark_wait else 'Continuous actual capture, no removed inference wait.',
               'audio_policy':'Browser capture is silent. Actual public reference/participant WAV spans played during capture are muxed at recorded offsets. Video audio only is listening-normalized to -18 LUFS/-1.5 dBTP; analysis WAV gain and quality evidence are preserved.',
               'audio_spans':audio_spans,'captions':len(captions),'visual_review':'required representative segments','youtube_url':None})
    print('Actual captioned browser demo assembled:',seconds,'seconds. YouTube upload remains blocked.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    args=parser.parse_args()
    video(args.url)
