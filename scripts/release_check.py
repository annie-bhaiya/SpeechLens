import json
import re
import subprocess
from pathlib import Path
import requests
from pypdf import PdfReader
from backend.speechlens.config import ROOT
from backend.speechlens.ingest import ffmpeg_executable
from backend.speechlens.utils import sha256_file,write_json
from scripts.validate_dataset import validate

def duration(path):
    import shutil
    ffprobe=shutil.which('ffprobe')
    if ffprobe:
        result=subprocess.run([ffprobe,'-v','error','-show_entries','format=duration','-of','json',str(path)],capture_output=True,text=True,timeout=30,check=True)
        return float(json.loads(result.stdout)['format']['duration'])
    result=subprocess.run([ffmpeg_executable(),'-i',str(path)],capture_output=True,text=True,timeout=30)
    match=re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)',result.stderr)
    return int(match[1])*3600+int(match[2])*60+float(match[3]) if match else None

def check():
    integrity=validate()
    artifacts=['README.md','uv.lock','frontend/package-lock.json','frontend/dist/index.html','docs/dataset_card.md','docs/annotation_guide.md','evaluation/metrics.json','evaluation/robustness.json','evaluation/browser_e2e.json','docs/technical_report.pdf','demo/demo.mp4','demo/captions.vtt','releases/checksums.txt','releases/submission_manifest.json','releases/speechlens-dataset.zip']
    missing=[p for p in artifacts if not (ROOT/p).exists()]
    checksum_errors=[]
    path=ROOT/'releases/checksums.txt'
    if path.exists():
        for line in path.read_text().splitlines():
            sha,name=line.split('  ',1)
            if not (ROOT/name).exists() or sha256_file(ROOT/name)!=sha:checksum_errors.append(name)
    report=ROOT/'docs/technical_report.pdf'
    pages=len(PdfReader(report).pages) if report.exists() else None
    video=ROOT/'demo/demo.mp4'
    seconds=duration(video) if video.exists() else None
    reviews={}
    for name in ['report','video']:
        review=ROOT/'evaluation'/(name+'_check.json')
        value=json.loads(review.read_text()) if review.exists() else {}
        reviews[name]=value.get('visual_review')=='passed'
    tests=ROOT/'evaluation/test_check.json'
    browser=ROOT/'evaluation/browser_e2e.json'
    execution={'tests_passed':bool(tests.exists() and json.loads(tests.read_text()).get('passed')),
               'fresh_browser_passed':bool(browser.exists() and json.loads(browser.read_text()).get('passed') and json.loads(browser.read_text()).get('fresh_upload'))}
    links=[]
    submission=ROOT/'releases/submission_manifest.json'
    if submission.exists():
        for item in json.loads(submission.read_text())['deliverables']:
            url=item.get('url')
            if not url:
                links.append({'name':item['name'],'url':None,'status':'blocked_missing_public_link' if item['name']!='Technical report' else 'local_artifact'})
                continue
            try:
                response=requests.get(url,timeout=20,allow_redirects=True)
                links.append({'name':item['name'],'url':url,'status':'accessible' if response.ok else 'failed','http_status':response.status_code})
            except requests.RequestException as error:
                links.append({'name':item['name'],'url':url,'status':'network_check_unavailable','reason':str(error)[:200]})
    local=not missing and not checksum_errors and integrity['integrity_passed'] and pages is not None and pages<=6 and seconds is not None and 180<=seconds<=600 and all(reviews.values()) and all(execution.values())
    public=all(l['status']=='accessible' for l in links if l['name'] in ['GitHub repository','Public paired dataset','YouTube demo']) and len(links)>=5
    result={'local_artifacts_passed':local,'submission_complete':bool(local and public and integrity['human_label_gate_passed']),
            'missing_artifacts':missing,'checksum_errors':checksum_errors,'dataset_integrity':integrity,
            'pdf_pages':pages,'video_duration_s':seconds,'video_duration_passed':bool(seconds is not None and 180<=seconds<=600),
            'visual_reviews':reviews,'execution_checks':execution,
            'links':links,'human_review_gate_passed':integrity['human_label_gate_passed']}
    write_json(ROOT/'releases/release_check.json',result)
    print(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    result=check()
    raise SystemExit(0 if result['submission_complete'] else 2)
