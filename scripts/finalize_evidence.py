"""Write an auditable Markdown handoff from completed measured outputs."""
import json
from collections import defaultdict
from backend.speechlens.config import ROOT

def finalize():
    read=lambda name:json.loads((ROOT/name).read_text(encoding='utf-8'))
    metrics=read('evaluation/metrics.json')
    integrity=read('evaluation/dataset_integrity.json')
    robust=read('evaluation/robustness.json')
    rows=[json.loads(l) for l in (ROOT/'data/manifests/recordings.jsonl').read_text().splitlines() if l]
    scores=read('evaluation/recording_scores.json')
    metrics['severity_ordering_coverage']={'groups_requested':integrity['references']*4,
        'groups_with_category_evidence':len(metrics['severity_ordering']),
        'groups_with_defined_spearman':sum(g['spearman'] is not None for g in metrics['severity_ordering']),
        'definition':'Median is over defined within-family correlations. Constant penalties and all-missing groups are not perfect ordering; see per-group nulls, pairwise accuracy and coverage.'}
    from scripts.run_evaluation import CATEGORY,make_plots
    from backend.speechlens.utils import write_json
    for item in metrics['severity_ordering']:
        if 'levels' not in item:
            eligible=sorted(r['severity_label'] for r in rows if r['pair_group_id']==item['source'] and r['flaw_family']==item['family'] and scores[r['recording_id']]['category_scores'][CATEGORY[item['family']]] is not None)
            assert len(eligible)==len(item['penalties'])
            item['levels']=eligible
    write_json(ROOT/'evaluation/metrics.json',metrics)
    make_plots(metrics['severity_ordering'],metrics['localization'])
    controls=[]
    for reference in [r for r in rows if r['generation_method']=='reference']:
        group=[r for r in rows if r['pair_group_id']==reference['pair_group_id']]
        conditions={r['flaw_family']:scores[r['recording_id']] for r in group if r['severity_label']==0 or r['severity_label']==4}
        controls.append({'pair_group_id':reference['pair_group_id'],'split':reference['split'],
            'conditions':conditions,'note':'Same source/text, intervention present versus removed (reference), compounds and identity shams. These are synthetic controlled comparisons, not human causal ratings.'})
    write_json(ROOT/'evaluation/ablations/controlled_edit_removal.json',controls)
    lines=['# Measured evaluation and failure analysis','',
      'All localization and severity metrics below use synthetic transformation support. They do not measure independent perceptual accuracy. Thresholds were frozen before test evaluation; failed targets have not been lowered.','',
      f"Inventory: {len(rows)} recordings, {integrity['references']} excerpts, {integrity['independent_speakers']} speakers, {integrity['independent_sources']} source recordings. Train/validation/test counts: {integrity['splits']}. Structural integrity passed: {integrity['integrity_passed']}. Human-reviewed recordings: 0.",'',
      f"Held-out test macro F1 at tIoU 0.5: {metrics['held_out_test_macro_f1_tiou_0_5_proxy']:.4f} (target 0.75). Median defined within-source/family Spearman: {metrics['median_spearman_proxy']:.4f} (target 0.80). Ordering coverage: {metrics['severity_ordering_coverage']}",'',
      '| Split/type | TP | FP | FN | Precision | Recall | F1 | Matched mean onset / offset error (s) |','|---|---:|---:|---:|---:|---:|---:|---|']
    val=lambda v:'unmeasured' if v is None else f'{v:.4f}'
    for split,types in metrics['localization'].items():
        for key,m in types.items():
            if key.startswith('0.5/'):
                lines.append(f"| {split}/{key.split('/')[1]} | {m['tp']} | {m['fp']} | {m['fn']} | {val(m['precision'])} | {val(m['recall'])} | {val(m['f1'])} | {val(m['mean_onset_error_s'])} / {val(m['mean_offset_error_s'])} |")
    lines+=['','Counts include missed events; low boundary error on a small matched subset is not high recall. Pause rows are boundary events; pace/intonation/energy are phrase supports. Both tIoU 0.3 and 0.5, micro/macro aggregates, subtle-condition counts and held-out method metrics are retained in metrics.json.','',
      '## Controls and ordinal ordering','', '| Split | Unreviewed control recordings | Events | Minutes | Events/minute proxy | Predicted union duration (s) |','|---|---:|---:|---:|---:|---:|']
    for split,c in metrics['controls'].items():
        lines.append(f"| {split} | {c['recordings']} | {c['events']} | {c['minutes']:.2f} | {c['false_events_per_minute_proxy']:.3f} | {c['duration_s']:.2f} |")
    lines+=['','These accepted/sham controls have not been independently reviewed. The reviewed-control target of <=1 event/minute cannot be claimed passed. Per-recording condition identities remain in recording_scores.json and the manifest. Undefined Spearman for constant penalties is null, not perfect ordering; violations and downward penalty magnitudes are retained.','',
      '## Actual fixture robustness','', '| Condition | Score | Shift from baseline | Coverage |','|---|---:|---:|---:|']
    for c in robust['conditions']:
        lines.append(f"| {c['condition']} | {val(c['score'])} | {val(c['absolute_score_shift'])} | {c['coverage']:.3f} |")
    lines+=['',f"Fresh repeat result: identical event IDs, intervals, values and displayed scores = {robust['repeat_run']['same_events_scores_and_measurements']}. This is a same-machine check; no clean-container result exists.",'',
      '## Failure interpretation and ablation limits','',
      '- Pitch-shift resynthesis loses ASR matching and can abstain despite relative-pitch centering. This is a failed full-pipeline robustness condition.',
      '- Archival channel noise, weak voiced support and intended-text mismatch make Roosevelt examples unreliable for some phrase categories. Null scores are retained.',
      '- Low-pass/noise proxies are recording defects, not human under-articulation. The spectral rule can miss additive noise because it targets centroid loss; the held-out method is reported separately.',
      '- Exposure weighting dilutes short severe local edits; read the playable event and category coverage beside the total.',
      '- A transformed phrase can disturb acoustic word boundaries in non-edited neighbors, creating false pace/pause events. Independent review is needed to separate alignment artifacts from audible defects.',
      '- Raw versus normalized pitch/energy, native versus token progress, alignment gating, compound/single and ordinary/sham evidence is retained in evaluation/ablations and per-recording rows. No counterfactual accuracy improvement or human agreement is claimed without labels.',
      '- No leave-one-speaker-out fitting analysis was added: thresholds are not fitted, and the available held-out test has only one independent speaker. Source-level plots describe dependence without treating variants as independent people.',
      '', '## Alignment and evidence audit','',
      f"Quote/clock/value/rule audit: {metrics['explanation_audit']}. Human advice usefulness remains null. Machine coverage by condition/speaker is in alignment_coverage.json; independently corrected boundary errors are unavailable.",'',
      f"Runtime: {metrics['runtime']}. Per-recording cache state and latency are in runtime.json. Model/library initialization and process-lifetime peak memory are disclosed."]
    (ROOT/'docs/evaluation.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # Selection rationale is contextual; machine quality review cannot certify effectiveness.
    rationale={
      'jfk':'Prepared inaugural oratory with parallel clauses and rhetorical contrast.',
      'eisenhower':'Conversational televised farewell, providing a restrained delivery contrast.',
      'nixon':'Prepared televised resignation with clear clause boundaries and contextual pauses.',
      'fdr':'Historically influential public addresses; channel limitations and lower machine coverage retained.',
      'reagan':'Prepared inaugural oratory reserved for validation, with phrase-level contrast.',
      'obama':'Contemporary official televised address, isolated as the test speaker.'}
    baseline=['# Provisional baseline selection and machine QA','',
      'These sources offer prepared public delivery contrasts. Fame is not an effectiveness label. Independent listening, transcript correction and acceptance remain pending; none is asserted to be a unique optimum.','',
      '| Excerpt | Speaker/split | Duration | Machine coverage | Rationale |','|---|---|---:|---:|---|']
    for r in rows:
        if r['generation_method']=='reference':
            baseline.append(f"| {r['pair_group_id']} | {r['speaker_id']}/{r['split']} | {r['duration_s']:.2f}s | {r['alignment_coverage']:.3f} | {rationale.get(r['speaker_id'],'Prepared public speech.')} |")
    baseline+=['','Source/rights URLs, exact crop clocks, original identities and separate transcript evidence are stored in data/provenance. No source was excluded solely because its eventual test score was poor. Short excerpts are a disclosed collection deviation.']
    (ROOT/'docs/baseline_review.md').write_text('\n'.join(baseline)+'\n',encoding='utf-8')
    print('Finalized measured evaluation and provisional baseline documentation.')

if __name__=='__main__':finalize()
