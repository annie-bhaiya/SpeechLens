# Requirements matrix

| Requirement | Artifact | Verification / gate |
|---|---|---|
| Effective public baseline and rights | data/provenance, docs/dataset_card.md | Source pages, checksums, explicit review state |
| Same-text severity spectrum 0-4 | scripts/build_dataset.py, data/manifests | Exact canonical hashes, real WAVs, deterministic recipes |
| Independent temporal labels | data/alignments, data/events, docs/annotation_guide.md, docs/human_review_portal.md | Portal creates separate word/event files and preserved originals; actual independent human work still pending |
| FFT/STFT/MFCC/F0/RMS/VAD/rate/pauses | backend/speechlens/features.py | Known-signal tests and real audio spike |
| Actual participant clock grounding | comparison.py, detectors.py | Piecewise maps, native interval checks, browser seek |
| Evidence/math/coaching | explanations.py, schemas.py | Values, rules, quotes and intervals audited |
| Four rubric presets/coverage | configs/rubrics, scoring.py | Missing evidence null; overlap maxima; pure aggregation |
| Speaker normalization | features.py | Gain/pitch invariance tests; range retained |
| Upload/dashboard/explorer/export | backend/app, frontend/src | Real-upload browser E2E |
| Durable bounded worker/storage | jobs.py, storage.py | Restart/retry/delete and invalid upload tests |
| Speaker/source/text split isolation | scripts/validate_dataset.py | Connected-component split leakage check |
| Alignment/localization/ordering/runtime | scripts/run_evaluation.py, evaluation | Actual denominators and failure cases; human metrics null |
| Locks/models/CPU/Docker/commands | uv.lock, package-lock.json, compose.yaml | Frozen installs; clean container status explicitly recorded |
| Technical report <=6 pages | docs/technical_report.pdf | Programmatic page count plus render inspection |
| 180-600s actual demonstration | demo/demo.mp4 | Actual capture only; ffprobe when installed, FFmpeg duration fallback plus visual inspection |
| Public GitHub/dataset/YouTube | releases/submission_manifest.json | Real verified URLs or blocked null fields |
| License/retention/no invented results | LICENSE, docs, BLOCKERS.md | Original uploads private, attribution, honest release check |
| Supplied organizer brief verification | Track C.pdf, docs/organizer_requirements_review.md | All three pages read/rendered; organizer deliverables/weights separated from project targets |
| Human acceptance/annotation workflow | backend/app/review.py, frontend/src/components/ReviewPortal.tsx | Account isolation, blinded queue, native times, immutable originals, assignment and two-review adjudication verified with isolated fixtures |
| Consented real-performance collection | /review, private storage/human_review | Microphone/upload, read-back/consent, canonical identity, speaker split and withdrawal verified; actual human contributions absent |
| Local portal design/readability | docs/review_portal_design_verification.md, docs/screenshots/review | Four finish fixes resolved; ten desktop/mobile captures, geometry assertions, no document overflow; cleared for private local use |
