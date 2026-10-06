# SpeechLens progress

The implementation prompt is the contract. This is a new local repository; no existing source code or recordings were supplied.

| Phase | Status | Evidence |
|---|---|---|
| 0 Inspection/contract | Complete | Prompt read; requirements matrix and blockers created |
| 1 CPU compatibility | Locally verified | Python 3.11, locked packages, pinned CPU model, actual archival audio spike |
| 2 Vertical slice | Locally verified | Fresh upload, detected native pacing, A/B playback, persisted preset and schema-valid export |
| 3 Public sources | Collected; human QA blocked | 13 provisional excerpts, six speakers, seven original recordings; rights/provenance retained |
| 4 Spectrum/labels | Structurally verified; human QA blocked | 346 recordings, five level 1-4 families, compounds, gain/sham controls and eight held-out noise variants; all human reviews pending |
| 5 DSP | Locally verified with limitation | Known-signal tests and gain/resampling checks pass; pitch-shift alignment robustness fails |
| 6 Detection/scoring | Implemented | Evidence-linked deterministic detectors, null/coverage gates, four presets; engineering tolerances uncalibrated |
| 7 Evaluation | Measured; localization target failed | 346 rows; held-out proxy macro F1 0.436 vs target 0.75; defined-group median Spearman 0.949; full failures and audits retained |
| 8 Dashboard/deployment | Local browser verified; container blocked | React/FastAPI, durable bounded worker; Docker daemon absent |
| 9 Submission | Blocked | Publication, independent reviews and supplied organizer PDF absent |

Local packaging is complete: six-page PDF rendered and inspected on every page; actual captioned video is 448.93 seconds with retained upload-inference waits, a verified gain-control result and visible benchmark. MP4 stream decoding and sample speech-recognition checks pass. The source/participant audio is listening-normalized only in the video; analysis preserves original gain.

Frontend production build and actual browser fresh-upload test passed. The latter checks native playback, preset persistence in export, mobile width and absence of JavaScript errors. Benchmark targets will remain unchanged if measurements fail them.

22 backend checks and one frontend coordinate check pass. Actual running-job deletion removes the private directory and returns 404 afterward. Queue capacity is enforced transactionally across upload, demo and retry admission. Offline evaluation uses four bounded processes on the measured CPU; app processing remains serial.

Final release check passes every local artifact gate: no missing files or checksum errors, dataset ZIP CRC checked (1,081 entries), six reviewed PDF pages, 448.93-second reviewed video, passing tests and a fresh-upload browser check. Public submission remains blocked by the explicit gates above.
