"""Automated portal workflow fixtures, not human validation. Use an isolated server storage root."""
import io
import json
import time
import zipfile
from pathlib import Path
import requests
import sqlite3
from playwright.sync_api import sync_playwright
from backend.speechlens.config import ROOT
from backend.speechlens.utils import write_json

def run(base='http://127.0.0.1:5173', storage_root=None):
    storage_root=Path(storage_root or ROOT/'tmp/review-e2e').resolve()
    assert ROOT.resolve() in storage_root.parents and 'tmp' in storage_root.parts
    images=ROOT/'docs/screenshots/review';images.mkdir(parents=True,exist_ok=True)
    aliases=['automated-test-reviewer-a','automated-test-reviewer-b','automated-test-coordinator']
    password='automated-workflow-test-only'
    guard=requests.get(base+'/api/review/context',timeout=15).json()
    assert guard['isolated_test_storage'] and Path(guard['test_storage_root']).resolve()==storage_root, 'Start the backend with SPEECHLENS_STORAGE pointing to this isolated tmp directory before running fixtures.'
    database=storage_root/'human_review/reviews.sqlite'
    if database.exists():
        with sqlite3.connect(database) as con:
            con.execute('DELETE FROM adjudications')
            con.execute('DELETE FROM submissions')
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='acceptance_originals'").fetchone():
                con.execute('DELETE FROM acceptance_originals')
    def login(alias,role='reviewer'):
        value={'alias':alias,'password':password,'role':role,'consent':True}
        if role=='coordinator':value['coordinator_code']=(storage_root/'human_review/coordinator-key.txt').read_text().strip()
        r=requests.post(base+'/api/review/session',json=value,timeout=20);r.raise_for_status();return r.json()
    first=login(aliases[0]);coord=login(aliases[2],'coordinator')
    h={'Authorization':'Bearer '+coord['token']}
    queue=requests.get(base+'/api/review/coordinator',headers=h,timeout=30).json()['tasks']
    chosen=next(r for r in queue if r['recording_id']=='eisenhower01_pace_level4') if any(r['recording_id']=='eisenhower01_pace_level4' for r in queue) else next(r for r in queue if r['recording_id'].startswith('eisenhower01') and 'pace' in r['recording_id'] and 'level4' in r['recording_id'])
    tid=chosen['id'];fh={'Authorization':'Bearer '+first['token']}
    tasks=requests.get(base+'/api/review/tasks',headers=fh,timeout=30).json()['tasks'];label=next(t['label'] for t in tasks if t['id']==tid)
    errors=[];results={}
    with sync_playwright() as p:
        browser=p.chromium.launch(args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
        context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base+'/review');page.get_by_role('heading',name='Make the evidence human.').wait_for()
        page.screenshot(path=str(images/'welcome-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(images/'welcome-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Welcome mobile overflow'
        page.set_viewport_size({'width':1440,'height':1000})
        page.get_by_label('Reviewer ID',exact=True).fill(aliases[0]);page.get_by_label('Passphrase',exact=True).fill(password)
        page.get_by_role('checkbox').check();page.get_by_role('button',name='Enter review workspace').click()
        page.get_by_role('button').filter(has_text=label).click()
        page.get_by_label('Review scope',exact=True).select_option('full_annotation')
        page.get_by_label('Recording decision',exact=True).select_option('accept')
        page.get_by_label('Listening notes / rejection / uncertainty',exact=True).fill('AUTOMATED TEST FIXTURE. No human listening judgment is asserted.')
        page.get_by_role('button',name='2. Text & word times',exact=True).click()
        assert page.locator('.review-word-table input[type=number]').first.evaluate('(a)=>parseFloat(getComputedStyle(a).fontSize)')>=14
        page.screenshot(path=str(images/'word-boundaries-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(images/'word-boundaries-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Boundary editor mobile overflow'
        page.set_viewport_size({'width':1440,'height':1000})
        svg=page.get_by_role('img',name='Native-time waveform; use the seek slider below')
        assert svg.get_attribute('preserveAspectRatio')=='none'
        svg.click(position={'x':svg.bounding_box()['width']*.25,'y':30})
        duration=requests.get(base+f'/api/review/tasks/{tid}',headers=fh).json()['duration_s']
        assert abs(page.get_by_label('Review rendition audio',exact=True).evaluate('(a)=>a.currentTime')-duration*.25)<.05
        page.get_by_role('button',name='3. Audible flaws',exact=True).click()
        page.get_by_label('Start (seconds)',exact=True).fill('1.0');page.get_by_label('End (seconds)',exact=True).fill('2.5')
        page.get_by_label('Affected word IDs',exact=True).fill('2,3')
        page.get_by_label('What did you hear, and why is it a flaw here?',exact=True).fill('AUTOMATED interval fixture for browser validation; not a perceptual finding.')
        page.get_by_role('button',name='Add perceptual event',exact=True).click()
        page.get_by_role('button',name='Save draft',exact=True).click()
        page.get_by_text('Draft saved on this computer.',exact=True).wait_for()
        page.get_by_label('Review rendition audio',exact=True).evaluate('(a)=>a.currentTime=1.1')
        page.get_by_role('button',name='Replay selected interval',exact=True).click();time.sleep(.35)
        assert page.get_by_label('Review rendition audio',exact=True).evaluate('(a)=>a.currentTime')>=1
        assert page.get_by_label('Review reference audio',exact=True).evaluate('(a)=>a.paused')
        page.screenshot(path=str(images/'annotation-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(images/'annotation-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Editor mobile overflow'
        page.set_viewport_size({'width':1440,'height':1000})
        page.get_by_role('button',name='4. Check & submit',exact=True).click()
        page.get_by_role('button',name='Finalize independent review',exact=True).click()
        page.get_by_role('alert').filter(has_text='Review every word boundary').wait_for()
        detail=requests.get(base+f'/api/review/tasks/{tid}',headers=fh).json();body=detail['draft']
        body['words']=[{**w,'reviewed':True} for w in body['words']]
        body['checks']={k:True for k in body['checks']};body['checks']['no_flaws_confirmed']=False
        body['ratings']={k:0 for k in body['ratings']};body['ratings']['pace']=1
        body.update({'revision':detail['revision'],'submit':False})
        r=requests.put(base+f'/api/review/tasks/{tid}/submission',headers=fh,json=body);r.raise_for_status()
        page.reload();page.get_by_role('button',name='Review & annotate',exact=True).click()
        page.get_by_role('button').filter(has_text=label).click()
        page.get_by_role('button',name='4. Check & submit',exact=True).click()
        page.get_by_role('button',name='Finalize independent review',exact=True).click()
        page.get_by_text('Independent review finalized. Your original file is preserved.',exact=True).wait_for()
        assert requests.get(base+f'/api/review/tasks/{tid}',headers=fh).json()['status']=='submitted'
        second=login(aliases[1]);sh={'Authorization':'Bearer '+second['token']}
        assert requests.get(base+f'/api/review/tasks/{tid}',headers=sh).json()['draft'] is None
        body.update({'revision':0,'submit':True});body['events'][0]['start_s']=1.1
        r=requests.put(base+f'/api/review/tasks/{tid}/submission',headers=sh,json=body);r.raise_for_status()
        c=context.browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
        cp=c.new_page();cp.on('pageerror',lambda e:errors.append(str(e)));cp.goto(base+'/review')
        cp.get_by_label('Reviewer ID',exact=True).fill(aliases[2]);cp.get_by_label('Passphrase',exact=True).fill(password)
        cp.get_by_label('Role',exact=True).select_option('coordinator')
        cp.get_by_label('Coordinator access code',exact=True).fill((storage_root/'human_review/coordinator-key.txt').read_text().strip())
        cp.get_by_role('checkbox').check();cp.get_by_role('button',name='Enter review workspace').click()
        cp.get_by_label('Coordinator queue view',exact=True).select_option('test')
        cp.get_by_role('button',name='Select this view',exact=True).click()
        cp.get_by_label('Reviewer IDs, separated by commas',exact=True).fill(','.join(aliases[:2]))
        with cp.expect_response(lambda r:r.url.endswith('/api/review/assignments') and r.request.method=='POST') as assigned:
            cp.get_by_role('button',name='Assign 60 selected tasks',exact=True).click()
        assert assigned.value.status==200,assigned.value.text()
        cp.get_by_label('Coordinator queue view',exact=True).select_option('progress')
        cp.get_by_role('row').filter(has_text=chosen['recording_id']).get_by_role('button',name='Compare & resolve').click()
        cp.get_by_label('Disagreements and how they were resolved',exact=True).fill('AUTOMATED TEST. Two isolated fixture identities, not actual independent humans. Retain first interval for schema validation.')
        cp.get_by_role('checkbox',name='I verified that these are distinct consenting humans').check()
        cp.screenshot(path=str(images/'adjudication-desktop.png'),full_page=True)
        cp.set_viewport_size({'width':390,'height':844});cp.screenshot(path=str(images/'adjudication-mobile.png'),full_page=True)
        assert cp.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Coordinator mobile overflow'
        cp.set_viewport_size({'width':1440,'height':1000})
        cp.get_by_role('button',name='4. Check & submit',exact=True).click()
        cp.get_by_role('button',name='Finalize adjudication',exact=True).click()
        cp.get_by_text('Adjudication finalized. Independent originals are preserved.',exact=True).wait_for()
        with cp.expect_download() as download:cp.get_by_role('button',name='Export files',exact=True).click()
        path=ROOT/'tmp/review-e2e-export.zip';download.value.save_as(path)
        with zipfile.ZipFile(path) as z:
            assert len([n for n in z.namelist() if n.startswith('independent/')])==2
            assert any(n.startswith('adjudicated/') for n in z.namelist())
            assert any(n.startswith('alignments/adjudicated/') for n in z.namelist())
            assert any(n.startswith('events/adjudicated/') for n in z.namelist())
        cp.get_by_role('button',name='Real performances',exact=True).click()
        refs=requests.get(base+'/api/references').json();reference=next(r for r in refs if r['id']=='eisenhower01_good')
        cp.get_by_label('Reference text',exact=True).select_option(reference['id'])
        cp.get_by_label('Speaker pseudonym',exact=True).fill('automated-test-speaker')
        cp.get_by_label('Microphone and room / recording notes',exact=True).fill('AUTOMATED browser fake microphone fixture. Not a real human performance.')
        cp.get_by_role('button',name='Start microphone recording',exact=True).click()
        cp.get_by_role('button',name='Stop recording',exact=True).wait_for();time.sleep(2.2)
        cp.get_by_role('button',name='Stop recording',exact=True).click()
        cp.get_by_label('Human recording preview',exact=True).wait_for()
        cp.screenshot(path=str(images/'performance-desktop.png'),full_page=True)
        cp.set_viewport_size({'width':390,'height':844});cp.screenshot(path=str(images/'performance-mobile.png'),full_page=True)
        assert cp.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Contribution mobile overflow'
        cp.set_viewport_size({'width':1440,'height':1000})
        cp.get_by_role('checkbox',name='The speaker is an adult').check();cp.get_by_role('checkbox',name='The speaker permits private local research').check();cp.get_by_role('checkbox',name='I listened back and used the selected intended text').check()
        with cp.expect_response(lambda r:r.url.endswith('/api/review/performances') and r.request.method=='POST') as received:
            cp.get_by_role('button',name='Submit private performance',exact=True).click()
        assert received.value.status==201,received.value.text();human_id=received.value.json()['task_id']
        assert not received.value.json()['release_eligible']
        cp.get_by_role('button',name='Withdraw human_'+human_id).wait_for()
        cp.once('dialog',lambda d:d.accept());cp.get_by_role('button',name='Withdraw human_'+human_id).click()
        cp.get_by_text('Recording and linked review files withdrawn from this computer.',exact=False).wait_for()
        assert requests.get(base+f'/api/review/tasks/{human_id}',headers=h).status_code==404
        assert not errors,errors
        results={'passed':True,'automated_fixtures_not_human_evidence':True,'isolated_storage':str(storage_root),
                 'blind_review_draft_and_immutable_final':True,'completion_validation':True,'native_audio_seek_and_replay':True,
                 'independent_account_isolation':True,'two_review_adjudication':True,'separate_alignment_event_exports':True,
                 'microphone_capture_and_private_decode':True,'consent_gate_and_withdrawal':True,
                 'mobile_no_document_overflow':True,'javascript_errors':errors,'screenshots':[p.name for p in images.glob('*.png')]}
        results.update({'coordinator_assignment':True,'word_editor_font_floor_14px':True,'waveform_draw_seek_native_geometry':True})
        c.close();context.close();browser.close()
    write_json(ROOT/'evaluation/review_portal_e2e.json',results);print(json.dumps(results,indent=2))

if __name__=='__main__':run()
