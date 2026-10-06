"""Real browser upload; no mocked API, prefilled result or fabricated capture."""
import argparse
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from backend.speechlens.config import ROOT
from backend.speechlens.utils import write_json
from backend.app.schemas import Result

def browser_e2e(base='http://127.0.0.1:8000'):
    rows=[json.loads(l) for l in (ROOT/'data/manifests/recordings.jsonl').read_text().splitlines() if l]
    participant=next(r for r in rows if r['flaw_family']=='pace' and r['severity_label']==4 and r['split']=='train' and r['alignment_coverage']>.9)
    reference=next(r for r in rows if r['recording_id']==participant['reference_id'])
    transcript=json.loads((ROOT/'data/transcripts'/(reference['transcript_id']+'.json')).read_text())['display_text']
    images=ROOT/'docs/screenshots'
    images.mkdir(parents=True,exist_ok=True)
    videos=ROOT/'demo/recordings/e2e'
    videos.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(videos),record_video_size={'width':1440,'height':1000},accept_downloads=True)
        page=context.new_page()
        console_errors=[]
        page.on('pageerror',lambda e:console_errors.append(str(e)))
        page.goto(base)
        page.get_by_role('heading',name='Hear the difference.').wait_for()
        page.screenshot(path=str(images/'dashboard-upload.png'),full_page=True)
        page.locator('#reference-select').select_option('upload')
        page.get_by_label('Reference audio',exact=True).set_input_files(str(ROOT/'data'/reference['audio_path']))
        page.locator('#reference-text').fill(transcript)
        page.get_by_label('Participant audio',exact=True).set_input_files(str(ROOT/'data'/participant['audio_path']))
        page.locator('#transcript').fill(transcript)
        page.get_by_role('checkbox').check()
        with page.expect_response(lambda r:r.url.endswith('/api/evaluations') and r.request.method=='POST') as created:
            page.get_by_role('button',name='Analyze delivery').click()
        assert created.value.status==202
        job_id=created.value.json()['id']
        page.get_by_test_id('results').wait_for(timeout=900000)
        result=page.request.get(f'{base}/api/evaluations/{job_id}/result').json()
        Result.model_validate(result)
        assert result['provenance']['cache_hit'] is False
        assert result['mode']=='paired'
        assert any(e['type']=='pace' for e in result['events'])
        row=page.get_by_test_id('event-row').first
        row.scroll_into_view_if_needed()
        row.click()
        page.get_by_role('button',name='Play participant span',exact=True).click()
        audio=page.get_by_label('participant audio',exact=True)
        time.sleep(.4)
        current=audio.evaluate('(a)=>a.currentTime')
        assert current>=result['events'][0]['participant_interval_s'][0]-.2
        page.get_by_role('button',name='Play reference span',exact=True).click()
        page.locator('.rubric summary').click()
        page.get_by_label('Genre preset',exact=True).select_option('declamation')
        page.get_by_role('button',name='Token comparison',exact=True).click()
        page.screenshot(path=str(images/'dashboard-analysis.png'),full_page=True)
        page.locator('.evidence-grid').screenshot(path=str(images/'dashboard-evidence.png'))
        with page.expect_download() as download:
            page.get_by_role('link',name='Evidence JSON',exact=True).click()
        exported=ROOT/'evaluation/browser_export.json'
        download.value.save_as(exported)
        Result.model_validate_json(exported.read_text())
        assert json.loads(exported.read_text())['scores']['preset']=='declamation'
        page.get_by_role('button',name='Dataset explorer',exact=True).click()
        page.screenshot(path=str(images/'dashboard-dataset.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        page.get_by_role('button',name='Speech analysis',exact=False).click()
        page.screenshot(path=str(images/'dashboard-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
        context.close()
        browser.close()
    report={'passed':True,'job_id':job_id,'fresh_upload':True,'playback_native_time_s':current,
            'schema_valid_export':True,'preset_change':True,'mobile_no_horizontal_overflow':True,
            'console_errors':console_errors,'wall_s':time.perf_counter()-started,'capture':'actual Playwright browser recording'}
    assert not console_errors
    write_json(ROOT/'evaluation/browser_e2e.json',report)
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    args=parser.parse_args()
    browser_e2e(args.url)
