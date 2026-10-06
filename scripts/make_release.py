import json
import zipfile
from pathlib import Path
from collections import Counter
from backend.speechlens.config import ROOT
from backend.speechlens.utils import sha256_file,write_json
from scripts.validate_dataset import validate

def release():
    submission_path=ROOT/'configs/submission.json'
    settings=json.loads(submission_path.read_text()) if submission_path.exists() else {}
    docker_path=ROOT/'evaluation/docker_check.json'
    docker_passed=docker_path.exists() and json.loads(docker_path.read_text()).get('passed',False)
    integrity=validate()
    if not integrity['integrity_passed']:raise ValueError('Dataset integrity failed')
    rows=[json.loads(l) for l in (ROOT/'data/manifests/recordings.jsonl').read_text().splitlines() if l]
    refs=[r for r in rows if r['generation_method']=='reference']
    families=Counter(r['flaw_family'] for r in rows)
    card=f'''# SpeechLens dataset card - provisional research release

## Actual release inventory

{len(rows)} real mono 16 kHz WAV recordings; {len(refs)} source excerpts; {integrity['independent_speakers']} independent speakers; {integrity['independent_sources']} source recordings. Reference duration range: {min(r['duration_s'] for r in refs):.2f}-{max(r['duration_s'] for r in refs):.2f} seconds. Proposed target 30-60 seconds is not met by every excerpt. Large synthetic counts do not increase independent sample size.

Family counts: {dict(families)}. Each text has exact canonical SHA-256 identity across its mirrors. Splits are assigned before transformations and connected by speaker/source/text. Train speakers: Kennedy, Eisenhower, Nixon and Roosevelt; validation: Reagan; test: Obama. All Roosevelt sources share the same speaker split.

## Purpose and scope

Prepared English public addresses, primarily oratory. Four genre presets are configurable but not independently validated. This dataset is unsuitable for claims about overlapping voices, other languages, argument quality, personal traits or production generalization. Source excerpts are provisional delivery examples, not a unique optimal performance.

## Labels and transformations

Local pitch-preserving pacing stretches, WORLD pitch-range contraction, inserted pauses, energy-envelope flattening and low-pass recording-degradation proxies span levels 1-4. Compound edits and global-gain/stretch/WORLD identity controls are included. Additive noise at 30/20/10/0 dB SNR is held out as a generation method on the test speaker only; no thresholds are fitted on it. Seed and parameter recipes are retained. Clarity proxies are explicitly recording/channel degradation, not human under-articulation labels. Fade sample counts and monotone insertion/deletion-aware time maps are stored with supports. Each audio is acoustically realigned independently.

Current labels are transformation supports and unreviewed machine word boundaries. Perceptual intervals are null; reviewer lists are empty. Independent perceptual ground truth, human ordinal severity and two-reviewer adjudication are unavailable. All {integrity['pending_review_recordings']} recordings await human acceptance. Source text was drawn from published speech transcripts and checked by machine alignment; manual listening correction is pending.

## Provenance and rights

data/provenance includes retrieval date, original SHA-256, original file identity, source/rights page snapshot hashes, crop clocks, speaker, transcript source and separate rights evidence. Source-attested US federal/Executive Office public-domain status applies to the original official recordings/text. Pearl Harbor digitization also retains CC BY-SA 2.0 attribution. Wikimedia source-page snapshots are CC BY-SA. See docs/licenses.md. Public availability alone is not a reuse license.

## Evaluation and privacy

evaluation/metrics.json reports actual synthetic-support proxy localization, ordering and control false alarms with denominators. Human metrics are null. One held-out test speaker does not support strong uncertainty intervals. No filenames, generator parameters, levels or support labels enter inference. Private uploads never enter this dataset automatically. No consenting human mirrors were available.

## Release use

Dataset resides under data/ with audio, transcripts, alignments, events, provenance and manifests. The archive releases/speechlens-dataset.zip is a local upload-ready release. Checksums are in releases/checksums.txt. Public GitHub/Drive hosting remains blocked until authorized publication; a local archive does not satisfy the public dataset-link gate.
'''
    (ROOT/'docs/dataset_card.md').write_text(card,encoding='utf-8')
    files=[]
    for directory in ['audio','transcripts','alignments','events','provenance','manifests']:
        files.extend(p for p in (ROOT/'data'/directory).rglob('*') if p.is_file())
    checksum='\n'.join(sha256_file(p)+'  '+p.relative_to(ROOT).as_posix() for p in sorted(files))+'\n'
    (ROOT/'releases').mkdir(exist_ok=True)
    (ROOT/'releases/checksums.txt').write_text(checksum,encoding='utf-8')
    archive=ROOT/'releases/speechlens-dataset.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for p in sorted(files):z.write(p,p.relative_to(ROOT).as_posix())
        for p in [ROOT/'docs/dataset_card.md',ROOT/'docs/licenses.md',ROOT/'docs/annotation_guide.md',ROOT/'releases/checksums.txt',ROOT/'configs/sources.json']:
            z.write(p,p.relative_to(ROOT).as_posix())
    manifest={'submission_complete':False,'dataset_integrity':integrity,'local_dataset_archive':archive.name,
        'dataset_archive_sha256':sha256_file(archive),
        'deliverables':[
            {'name':'GitHub repository','local_artifact':'.','url':settings.get('github_url'),'status':'remote_link_configured' if settings.get('github_url') else 'blocked','reason':'See evaluation/git_push.json for terminal push verification'},
            {'name':'Public paired dataset','local_artifact':'releases/speechlens-dataset.zip','url':settings.get('dataset_url'),'status':'existing_remote_data_human_review_pending' if settings.get('dataset_url') else 'local_ready_publication_blocked','reason':settings.get('dataset_note','Public hosting and independent human review pending')},
            {'name':'Interactive dashboard','local_artifact':'frontend/dist','url':'http://127.0.0.1:8000','status':'local_verified','verification':'evaluation/browser_e2e.json'},
            {'name':'Technical report','local_artifact':'docs/technical_report.pdf','url':None,'status':'local_ready' if (ROOT/'docs/technical_report.pdf').exists() else 'missing'},
            {'name':'YouTube demo','local_artifact':'demo/demo.mp4','url':settings.get('youtube_url'),'status':'local_ready_publication_deferred' if (ROOT/'demo/demo.mp4').exists() else 'missing','reason':'Publication deferred by user' if settings.get('youtube_publication_deferred_by_user') else 'No authorized YouTube publication account supplied'}],
        'remaining_gates':['Independent human alignment/perceptual review','Consenting human mirror recordings','YouTube link']+
                          ([] if settings.get('organizer_pdf_reviewed') else ['Original Track C.pdf review'])+
                          ([] if settings.get('github_url') else ['Public GitHub link'])+
                          ([] if settings.get('dataset_url') else ['Public dataset link'])+
                          ([] if docker_passed else ['Clean Docker execution'])}
    write_json(ROOT/'releases/submission_manifest.json',manifest)
    print('Dataset release:',len(files),'files;',archive.stat().st_size,'bytes. Public submission remains blocked.')

if __name__=='__main__':release()
