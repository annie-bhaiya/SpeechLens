# SpeechLens progress

The implementation prompt defines project targets. The newly supplied organizer PDF has now been checked separately; `docs/organizer_requirements_review.md` distinguishes its actual deliverables from project targets. The original implementation started as a new local repository; the user subsequently supplied a GitHub remote and running Docker Linux engine.

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
| 8 Dashboard/deployment | Local browser and Linux container verified | React/FastAPI, durable bounded worker; clean dependency build, downloaded model, fresh/repeat CPU inference |
| 9 Submission | Incomplete, remaining human work/deferred publishing explicit | Organizer PDF verified; remote supplied, terminal push receipt recorded; human evidence missing, YouTube deferred |
| 10 Human-work portal | Software verified; actual people still needed | Acceptance QA, independent word/event annotation, assignment/two-review adjudication, consented private microphone/upload collection, exports and withdrawal |

Local packaging is complete: six-page PDF rendered and inspected on every page; actual captioned video is 448.93 seconds with retained upload-inference waits, a verified gain-control result and visible benchmark. MP4 stream decoding and sample speech-recognition checks pass. The source/participant audio is listening-normalized only in the video; analysis preserves original gain.

Frontend production build and actual browser fresh-upload test passed. The latter checks native playback, preset persistence in export, mobile width and absence of JavaScript errors. Benchmark targets will remain unchanged if measurements fail them.

29 backend checks and one frontend coordinate check pass. Actual running-job deletion removes the private directory and returns 404 afterward. Queue capacity is enforced transactionally across upload, demo and retry admission. Offline evaluation uses four bounded processes on the measured CPU; app processing remains serial.

Final release check passes every local artifact gate: no missing files or checksum errors, dataset ZIP CRC checked (1,081 entries), six reviewed PDF pages, 448.93-second reviewed video, passing tests and a fresh-upload browser check. Public submission remains blocked by the explicit gates above.

The portal browser check uses explicitly automated identities/audio in a temporary isolated store. It verifies immutable independent originals, supplemented QA provenance, completion validation, native seek/replay geometry, reviewer isolation, 60-task held-out assignment, two-review adjudication, separate word/event exports, microphone capture/private decoding, consent, withdrawal and desktop/mobile layout without JavaScript errors. The design finish review resolved four concrete issues and cleared the extension for private local use. No actual human review or performance has been fabricated or counted.

Dataset files already existed in the user's initial remote commit. This extension performs no dataset changes/republication and leaves the existing archive, report and video unchanged. Dataset and YouTube publication are deferred. The current scientific benchmark and its failed targets remain unchanged.
