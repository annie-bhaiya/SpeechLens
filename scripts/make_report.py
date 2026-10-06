import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.graphics.shapes import Drawing,Rect,String,Line
from pypdf import PdfReader
from backend.speechlens.config import ROOT
from backend.speechlens.utils import write_json

TEAL=colors.HexColor('#087f89')
INK=colors.HexColor('#142235')
MUTED=colors.HexColor('#52687f')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Body',fontName='Helvetica',fontSize=10.5,leading=15,textColor=INK,spaceAfter=9))
styles.add(ParagraphStyle(name='Hero',fontName='Helvetica-Bold',fontSize=26,leading=31,textColor=INK,spaceAfter=17))
styles.add(ParagraphStyle(name='Sub',fontName='Helvetica-Bold',fontSize=13,leading=18,textColor=TEAL,spaceBefore=10,spaceAfter=9))
styles.add(ParagraphStyle(name='Kicker',fontName='Helvetica-Bold',fontSize=8.5,leading=12,textColor=TEAL,spaceAfter=12))
styles.add(ParagraphStyle(name='Caption',fontName='Helvetica',fontSize=9,leading=13,textColor=MUTED,spaceAfter=10))

def p(text,style='Body'):
    return Paragraph(escape(str(text)),styles[style])

def table(rows,widths=None):
    cells=[[p(c,'Caption') for c in row] for row in rows]
    t=Table(cells,colWidths=widths or [170,342],hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf3f4')),('VALIGN',(0,0),(-1,-1),'TOP'),
                          ('LINEBELOW',(0,0),(-1,0),.7,TEAL),('LINEBELOW',(0,1),(-1,-1),.4,colors.HexColor('#dce6eb')),
                          ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
                          ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    return t

def read(path,default):
    return json.loads((ROOT/path).read_text(encoding='utf-8')) if (ROOT/path).exists() else default

def diagram():
    d=Drawing(512,93)
    labels=['Validate','Align','Extract','Compare','Explain']
    for i,label in enumerate(labels):
        x=i*103
        d.add(Rect(x,42,91,39,rx=5,ry=5,fillColor=colors.HexColor('#edf5f6'),strokeColor=colors.HexColor('#bcd8dc')))
        d.add(String(x+45.5,57,label,fontName='Helvetica-Bold',fontSize=10,fillColor=TEAL,textAnchor='middle'))
        if i<4:d.add(Line(x+91,62,x+103,62,strokeColor=MUTED))
    d.add(String(0,15,'Independent recording clocks - matched canonical token IDs - deterministic evidence',fontName='Helvetica',fontSize=9,fillColor=MUTED))
    return d

def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#dce5eb'))
    canvas.line(42,39,554,39)
    canvas.setFont('Helvetica',8)
    canvas.setFillColor(MUTED)
    canvas.drawString(42,25,'SpeechLens | Track C | Experimental local prototype | 2026-10-05')
    canvas.drawRightString(554,25,str(doc.page))

def report():
    rows=[json.loads(l) for l in (ROOT/'data/manifests/recordings.jsonl').read_text().splitlines() if l]
    metrics=read('evaluation/metrics.json',{})
    integrity=read('evaluation/dataset_integrity.json',{})
    robust=read('evaluation/robustness.json',{})
    browser=read('evaluation/browser_e2e.json',{})
    worked=read('evaluation/browser_export.json',{})
    event=next((e for e in worked.get('events',[]) if e['type']=='pace'),None)
    story=[]
    def page(kicker,title):
        if story:story.append(PageBreak())
        story.extend([p(kicker,'Kicker'),p(title,'Hero')])
    page('01 / PROBLEM & SYSTEM','SpeechLens: same words, measured delivery')
    story.append(p('Track C calls for contrastive speech analytics with temporal flaw grounding. SpeechLens compares independent renditions of an identical intended transcript, keeps native acoustic clocks, and links each finding to audio, numeric evidence and a rehearsal action. It does not score argument quality or infer personal traits.'))
    story.append(diagram())
    story.append(p('Scope and execution','Sub'))
    story.append(p('English single-speaker audio, CPU inference, local persistent storage. A pinned Wav2Vec2 CTC model supplies intended-text alignment; FFT/MFCC, pYIN pitch, RMS energy and independent WebRTC VAD provide acoustic evidence. React renders uploads, processing feedback, native/token views and A/B playback.'))
    story.append(table([['Requirement','Implementation evidence'],['Data and same-text spectrum','Real WAVs, canonical transcripts, hash manifests, time maps and machine labels.'],['Temporal explanation','Participant/reference intervals, units, deltas, thresholds and structured coaching.'],['Reproducibility','Python/npm locks, pinned model revision, bounded worker, repeat checks and export.'],['External validity','Independent human labels, mirrors and original Track C.pdf unavailable; explicitly blocked.']]))
    story.append(p('Status: a functional local research prototype. GitHub and YouTube publication require authorized accounts; no invented public links or human review claims are included.','Caption'))
    page('02 / DATA ENGINEERING','A controlled spectrum, with honest labels')
    refs=[r for r in rows if r['generation_method']=='reference']
    story.append(p(f"Current release contains {len(rows)} recordings from {len(refs)} provisional excerpts, {len({r['speaker_id'] for r in rows})} speakers and {len({r['source_recording_id'] for r in rows})} source recordings. Speaker/source/text connections stay within train, validation or test. Public-address material primarily represents prepared oratory; the other named genre presets remain unvalidated."))
    story.append(table([['Sources','Rights and construction'],['Kennedy, Eisenhower, Nixon, Roosevelt','Official US federal speeches; recording and transcript provenance stored separately.'],['Reagan and Obama','Executive Office of the President public-domain source attribution.'],['Pearl Harbor digitization','Also retain CC BY-SA 2.0 attribution to W. Guy Finley/MSU Vincent Voice Library.'],['Each excerpt','Local pacing, intonation, pause, energy and recording-degradation proxies, levels 1-4; compound edits and gain/stretch/WORLD shams.']]))
    story.append(p('Time mapping and QA','Sub'))
    story.append(p('Piecewise maps use actual rendered sample counts. Inserted silence has a zero-length source interval; deleted spans have no inverse. Every variant is acoustically realigned, and propagated/realigned machine boundaries are compared. Transformation support and perceptual ground truth remain separate. All current perceptual reviews are pending.'))
    story.append(p('Some collected excerpts are 19-27 seconds, below the proposed 30-second minimum. Narrow, clean clause units were retained instead of padding with unrelated speech. Two independent human annotators, consenting human mirrors and transcript listening checks are required before claiming validated labels. See docs/annotation_guide.md.'))
    story.append(p(f"Integrity: {integrity.get('integrity_passed','not measured')}; pending-review recordings: {integrity.get('pending_review_recordings','not measured')}. A large synthetic count does not increase the number of independent speakers.",'Caption'))
    page('03 / DSP & ALIGNMENT','Separate voice, channel and native time')
    story.append(table([['Measurement','Definition / convention'],['Spectra and MFCC','25 ms Hann; 10 ms hop; 512-point FFT; 40 Slaney mel bands; natural-log power; orthonormal DCT-II; 13 MFCCs.'],['RMS and energy','RMS = sqrt(mean(x squared)); dBFS = 20 log10(RMS + epsilon). Keep original clipping/noise evidence.'],['Pitch','pYIN, 64 ms, 10 ms hop, 50-600 Hz. Unvoiced values remain null with explicit masks.'],['Speaker normalization','Pitch = 12 log2(F0 / median voiced F0); relative dB = dBFS - median speech energy. Preserve dynamic range.'],['Native pace and pauses','WPM = 60 N / elapsed seconds; articulation uses VAD-active time. Gap = next onset - prior offset, confirmed by VAD.']]))
    story.append(p('Alignment and mismatches','Sub'))
    story.append(p('Reference and participant align independently to canonical intended text. Chunked emissions retain actual clocks; CTC Viterbi enforces blank/repeat constraints. Greedy ASR edit matching and likelihood thresholds gate missing or uncertain words. Severe mismatch withholds paired scoring. Null words are never interpolated into plausible timestamps.'))
    story.append(p('Default WhisperX was replaced with a pinned Wav2Vec2 supplied-text implementation to reduce the CPU dependency footprint. Revision: 22aad52d435eb6dbaf354bdad9b0da84ce7d6156, Apache-2.0. WebRTC VAD is independent of pitch voicing; it is not diarization. Historical channel noise and octave errors remain failure risks.'))
    story.append(p('A transcript-normalized chart is a display coordinate only. It omits pauses and cannot replace elapsed-duration evidence. MFCC/spectral differences are corroborative channel diagnostics, never proof of poor articulation.'))
    page('04 / DETECTORS & RUBRIC','From a measured residual to a playable finding')
    story.append(p('Phrase detectors compare log duration, semitone range and relative energy range. Pause detectors use matched word boundaries and non-speech support. Clipping uses frame smoothing and onset/offset hysteresis. A flat reference, weak alignment or insufficient voicing triggers abstention. Thresholds are engineering tolerances, not population norms or calibrated accuracy probabilities.'))
    story.append(p('Score mathematics','Sub'))
    story.append(p('P_k = sum(I_u d_u a_u) / sum(I_u d_u); S_k = 100(1-P_k). Phrase exposure is fixed reference duration; pause boundaries have equal weight. Same-category overlapping evidence takes the maximum per unit. Missing evidence is excluded from numerator and denominator; a zero denominator yields null. Total = weighted mean of eligible categories, withheld below 60% scoring coverage.'))
    story.append(p('Default delivery weights: pacing 25%, pauses 20%, intonation 25%, energy 20%, clarity 10%. Clarity is diagnostic-only without validated intelligibility labels, so remaining weights renormalize. Compound category penalties are not independent causal claims. All four genre presets are configurable product choices.'))
    if event:
        m=event['measurements']
        story.append(table([['Actual fresh-upload example','Measured evidence'],['Quote',event['quote']],['Participant / reference WPM',f"{m['participant']:.2f} / {m['reference']:.2f}"],['Native duration ratio',f"{m['duration_ratio']:.3f}"],['Playable participant interval',f"{event['participant_interval_s'][0]:.2f}-{event['participant_interval_s'][1]:.2f} seconds"],['Correction',event['suggestion']]]))
    story.append(p('Exposure averaging can make the total look high despite a serious local defect. Findings and category coverage must be inspected alongside the total. Comparing a reference with itself is consistency, not proof of effective delivery.','Caption'))
    page('05 / MEASURED EVALUATION','Stress evidence, without human extrapolation')
    f1=metrics.get('held_out_test_macro_f1_tiou_0_5_proxy')
    rho=metrics.get('median_spearman_proxy')
    story.append(table([['Evaluation','Measured result / denominator'],['Event localization proxy',f"Held-out macro F1 at tIoU 0.5: {format(f1,'.3f') if f1 is not None else 'pending benchmark'}. Compare only to synthetic intervention support."],['Severity ordering proxy',f"Median defined Spearman: {format(rho,'.3f') if rho is not None else 'pending benchmark'}; evaluated recordings: {metrics.get('evaluated_recordings','pending')}. Undefined/all-missing groups disclosed in evaluation.md."],['Independent human evidence','0 human mirrors, 0 independent reviewers; human boundary accuracy, rubric agreement and generalization unmeasured.'],['Repeatability',str(robust.get('repeat_run',{}).get('same_events_scores_and_measurements','pending fresh-repeat check'))],['Browser end-to-end',f"Fresh upload, span playback, preset change, JSON export and mobile width passed: {browser.get('passed',False)}."],['Clean container','Docker daemon unavailable; Compose configuration provided, execution unverified.']]))
    if (ROOT/'evaluation/plots/severity.png').exists():
        story.append(Spacer(1,9))
        story.append(Image(str(ROOT/'evaluation/plots/severity.png'),width=512,height=128))
        story.append(p('Measured category penalties across injected levels. Synthetic support/severity are not independent perceptual ground truth.','Caption'))
    story.append(p('Failure analysis: proposed localization target missed','Sub'))
    story.append(p('Archival FDR recognition is weak; affected evidence can abstain. Pitch-shift resynthesis can withhold a score despite relative pitch intent. Identity-vocoder controls can trigger warnings. Low-pass damage is a recording proxy. Short pause penalties may be diluted. Only one test speaker is available; confidence intervals would imply unsupported precision. See evaluation.md for type counts, control exposure and ablation limits.'))
    page('06 / DASHBOARD & HANDOFF','A local prototype, ready for review')
    story.append(p('Upload same-text reference and participant audio, confirm English single-speaker scope, process, inspect scores/coverage, choose a finding, then play the matching spans separately. Charts label native seconds versus canonical token progress. Export includes schema-valid evidence, event CSV and full-resolution DSP artifacts. Uploads never enter the release dataset automatically.'))
    screenshot=ROOT/'docs/screenshots/dashboard-evidence.png'
    if screenshot.exists():
        from PIL import Image as PILImage
        with PILImage.open(screenshot) as img:w,h=img.size
        story.append(Image(str(screenshot),width=512,height=min(245,512*h/w)))
        story.append(p('Actual browser result from a fresh uploaded pair; captured without mocked processing.','Caption'))
    story.append(p('Clean-start commands','Sub'))
    story.append(p('Windows: ./speechlens.ps1 setup; ./speechlens.ps1 models; ./speechlens.ps1 serve. Open http://127.0.0.1:8000. Dataset files are bundled; source rebuilding needs network. See README.md for test, evaluation, report, video and release-check commands.'))
    story.append(p('Submission gates','Sub'))
    story.append(p('Local code, WAV dataset, dashboard, six-page report and actual browser capture are reviewable. Authorized GitHub/dataset publication and a viewable 3-10 minute YouTube link remain mandatory external gates. Human annotation and consenting mirrors remain pending. The supplied organizer Track C.pdf was absent; no claim of fully completed submission is made.'))
    story.append(p('Primary references: github.com/m-bain/whisperX; huggingface.co/facebook/wav2vec2-base-960h; librosa.org/doc/0.11.0; github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder; fastapi.tiangolo.com/tutorial/background-tasks. Complete URLs, licenses and source attribution: docs/licenses.md and data/provenance.','Caption'))
    path=ROOT/'docs/technical_report.pdf'
    SimpleDocTemplate(str(path),pagesize=(596,842),rightMargin=42,leftMargin=42,topMargin=43,bottomMargin=51,title='SpeechLens - Track C Technical Report',author='SpeechLens contributors').build(story,onFirstPage=footer,onLaterPages=footer)
    pages=len(PdfReader(path).pages)
    if pages>6:
        raise ValueError(f'Report exceeds six pages: {pages}; repair the layout, do not shrink text.')
    import fitz
    document=fitz.open(path)
    renders=ROOT/'tmp/pdfs'
    renders.mkdir(parents=True,exist_ok=True)
    for i,page in enumerate(document):
        page.get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(renders/f'report-{i+1}.png')
    write_json(ROOT/'evaluation/report_check.json',{'page_count':pages,'limit':6,'rendered_pages':pages,'visual_review':'required after generation'})
    print('Generated readable report:',pages,'pages; inspect tmp/pdfs/report-*.png')

if __name__=='__main__':report()
