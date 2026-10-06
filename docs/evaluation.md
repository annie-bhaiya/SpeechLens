# Measured evaluation and failure analysis

All localization and severity metrics below use synthetic transformation support. They do not measure independent perceptual accuracy. Thresholds were frozen before test evaluation; failed targets have not been lowered.

Inventory: 346 recordings, 13 excerpts, 6 speakers, 7 source recordings. Train/validation/test counts: {'train': 234, 'validation': 52, 'test': 60}. Structural integrity passed: True. Human-reviewed recordings: 0.

Held-out test macro F1 at tIoU 0.5: 0.4362 (target 0.75). Median defined within-source/family Spearman: 0.9487 (target 0.80). Ordering coverage: {'groups_requested': 52, 'groups_with_category_evidence': 48, 'groups_with_defined_spearman': 39, 'definition': 'Median is over defined within-family correlations. Constant penalties and all-missing groups are not perfect ordering; see per-group nulls, pairwise accuracy and coverage.'}

| Split/type | TP | FP | FN | Precision | Recall | F1 | Matched mean onset / offset error (s) |
|---|---:|---:|---:|---:|---:|---:|---|
| train/pace | 6 | 21 | 48 | 0.2222 | 0.1111 | 0.1481 | 0.0000 / 0.0204 |
| train/intonation | 24 | 6 | 30 | 0.8000 | 0.4444 | 0.5714 | 0.0047 / 0.0055 |
| train/pauses | 11 | 2 | 25 | 0.8462 | 0.3056 | 0.4490 | 0.2709 / 0.2802 |
| train/energy | 16 | 0 | 20 | 1.0000 | 0.4444 | 0.6154 | 0.0013 / 0.0288 |
| train/recording_quality | 0 | 13 | 36 | 0.0000 | 0.0000 | 0.0000 | unmeasured / unmeasured |
| validation/pace | 2 | 0 | 10 | 1.0000 | 0.1667 | 0.2857 | 0.0000 / 0.1460 |
| validation/intonation | 8 | 2 | 4 | 0.8000 | 0.6667 | 0.7273 | 0.0000 / 0.0100 |
| validation/pauses | 2 | 2 | 6 | 0.5000 | 0.2500 | 0.3333 | 0.0500 / 0.0609 |
| validation/energy | 5 | 1 | 3 | 0.8333 | 0.6250 | 0.7143 | 0.0000 / 0.0120 |
| validation/recording_quality | 2 | 0 | 6 | 1.0000 | 0.2500 | 0.4000 | 0.0000 / 0.0200 |
| test/pace | 0 | 8 | 12 | 0.0000 | 0.0000 | 0.0000 | unmeasured / unmeasured |
| test/intonation | 6 | 0 | 6 | 1.0000 | 0.5000 | 0.6667 | 0.0000 / 0.1600 |
| test/pauses | 2 | 0 | 6 | 1.0000 | 0.2500 | 0.4000 | 0.4850 / 0.4785 |
| test/energy | 5 | 1 | 3 | 0.8333 | 0.6250 | 0.7143 | 0.0000 / 0.0040 |
| test/recording_quality | 4 | 0 | 12 | 1.0000 | 0.2500 | 0.4000 | 0.0000 / 0.0000 |

Counts include missed events; low boundary error on a small matched subset is not high recall. Pause rows are boundary events; pace/intonation/energy are phrase supports. Both tIoU 0.3 and 0.5, micro/macro aggregates, subtle-condition counts and held-out method metrics are retained in metrics.json.

## Controls and ordinal ordering

| Split | Unreviewed control recordings | Events | Minutes | Events/minute proxy | Predicted union duration (s) |
|---|---:|---:|---:|---:|---:|
| train | 36 | 3 | 19.86 | 0.151 | 3.19 |
| validation | 8 | 0 | 3.91 | 0.000 | 0.00 |
| test | 8 | 0 | 3.49 | 0.000 | 0.00 |

These accepted/sham controls have not been independently reviewed. The reviewed-control target of <=1 event/minute cannot be claimed passed. Per-recording condition identities remain in recording_scores.json and the manifest. Undefined Spearman for constant penalties is null, not perfect ordering; violations and downward penalty magnitudes are retained.

## Actual fixture robustness

| Condition | Score | Shift from baseline | Coverage |
|---|---:|---:|---:|
| gain_minus6 | 100.0000 | 0.0000 | 1.000 |
| gain_plus6 | 100.0000 | 0.0000 | 1.000 |
| resample_22050 | 100.0000 | 0.0000 | 1.000 |
| pitch_plus2st | unmeasured | unmeasured | 0.000 |
| noise_10db | unmeasured | unmeasured | 0.427 |
| clipped | unmeasured | unmeasured | 1.000 |
| aac_128kbps | 100.0000 | 0.0000 | 1.000 |

Fresh repeat result: identical event IDs, intervals, values and displayed scores = True. This is a same-machine check; no clean-container result exists.

## Failure interpretation and ablation limits

- Pitch-shift resynthesis loses ASR matching and can abstain despite relative-pitch centering. This is a failed full-pipeline robustness condition.
- Archival channel noise, weak voiced support and intended-text mismatch make Roosevelt examples unreliable for some phrase categories. Null scores are retained.
- Low-pass/noise proxies are recording defects, not human under-articulation. The spectral rule can miss additive noise because it targets centroid loss; the held-out method is reported separately.
- Exposure weighting dilutes short severe local edits; read the playable event and category coverage beside the total.
- A transformed phrase can disturb acoustic word boundaries in non-edited neighbors, creating false pace/pause events. Independent review is needed to separate alignment artifacts from audible defects.
- Raw versus normalized pitch/energy, native versus token progress, alignment gating, compound/single and ordinary/sham evidence is retained in evaluation/ablations and per-recording rows. No counterfactual accuracy improvement or human agreement is claimed without labels.
- No leave-one-speaker-out fitting analysis was added: thresholds are not fitted, and the available held-out test has only one independent speaker. Source-level plots describe dependence without treating variants as independent people.

## Alignment and evidence audit

Quote/clock/value/rule audit: {'events_audited': 149, 'all_quote_clock_value_rule_checks_passed': True, 'human_advice_usefulness': None}. Human advice usefulness remains null. Machine coverage by condition/speaker is in alignment_coverage.json; independently corrected boundary errors are unavailable.

Runtime: {'platform': 'Windows-10-10.0.26200-SP0', 'device': 'CPU', 'benchmark_wall_s': 1820.1394617000187, 'benchmark_concurrent_variants': 4, 'median_processing_s_per_audio_s': 0.7159105209061056, 'peak_memory_mb': 2250.0703125, 'cold_warm_note': 'References warmed serially, variants use the stated process concurrency. Per-recording cache flags/timings in runtime.json include contention; app worker is serial. First inference per process includes model initialization. Peak memory is maximum per-process lifetime high water, not aggregate worker-pool memory.'}. Per-recording cache state and latency are in runtime.json. Model/library initialization and process-lifetime peak memory are disclosed.
