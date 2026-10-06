# SpeechLens

Evidence-first contrastive speech analytics for Track C. Upload two performances of the **same intended transcript**, compare native-time pacing, pauses, pitch and energy, play grounded findings, inspect the measured rule, and export reproducible evidence. English single-speaker CPU prototype; no paid LLM or cloud service is required.

**Status:** functional local implementation, real provisional paired audio and measured checks. This is **not a completed public hackathon submission**: authorized GitHub/dataset/YouTube publication, independent human reviews/mirrors, original `Track C.pdf` verification and a clean Docker run remain outstanding. [BLOCKERS.md](BLOCKERS.md) is authoritative.

| Mandatory deliverable | Location | Status |
|---|---|---|
| GitHub repository URL | This local Git repository | Blocked: no authorized remote/publication account |
| Public paired dataset | `data/`, `releases/speechlens-dataset.zip`, [dataset card](docs/dataset_card.md) | Real local data; public link and human acceptance pending |
| Interactive dashboard | [Local dashboard](http://127.0.0.1:8000) | Fresh-upload browser test passes; launch below |
| Technical report, at most 6 pages | [technical_report.pdf](docs/technical_report.pdf) | Generated locally; page/render verification recorded |
| 3-10 minute YouTube video | `demo/demo.mp4`, `demo/captions.vtt`, `demo/transcript.md` | Local capture/assembly; YouTube URL blocked |

No external submission URLs are invented. `releases/submission_manifest.json` and `releases/release_check.json` distinguish missing links, unavailable network checks, local artifacts and completed verification.

## Clean start on Windows

Prerequisites: Python launcher/current Python, Node 24 with npm, internet for first dependency/model downloads. Python 3.11 is selected by `.python-version`; setup installs uv 0.12.23 and resolves the exact committed lock. Existing public dataset WAVs are bundled in the folder/release. PowerShell from the repository root:

```powershell
.\speechlens.ps1 setup
.\speechlens.ps1 models
.\speechlens.ps1 serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000), then **Process demo pair**, or upload your own reference, corrected text and same-text participant. Confirm the single-speaker/English scope. User uploads stay in `storage/jobs/<opaque-id>/`; the dashboard can delete them. Never add unconsented uploads to the release.

In an environment with uv/npm/make:

```bash
make setup
make models
make serve
```

Alternative explicit server command after setup: `.venv\Scripts\python -m uvicorn backend.app.api:app --host 127.0.0.1 --port 8000`. On Unix, use `.venv/bin/python`. Offline model loading uses the pinned local snapshot once weights and tokenizer files exist. ffmpeg is supplied by imageio-ffmpeg when no system binary is available.

## Reproduction commands

| Task | Windows | make equivalent |
|---|---|---|
| Dependency install + production frontend | `.\speechlens.ps1 setup` | `make setup` |
| Pinned CPU model | `.\speechlens.ps1 models` | `make models` |
| One-source demo generation | `.\speechlens.ps1 demo-data` | `make demo-data` |
| Full deterministic data construction | `.\speechlens.ps1 dataset-build` | `make dataset-build` |
| Hash/time/split validation | `.\speechlens.ps1 dataset-validate` | `make dataset-validate` |
| Backend/frontend tests | `.\speechlens.ps1 test` | `make test` |
| Full proxy evaluation + robustness | `.\speechlens.ps1 evaluate` | `make evaluate` |
| Live browser upload test | `.\speechlens.ps1 e2e` | `uv run python -m scripts.browser_e2e` |
| Six-page report + PNG renders | `.\speechlens.ps1 report` | `make report` |
| Actual captioned browser video | `.\speechlens.ps1 demo-video` | `make demo-video` |
| Dataset archive/manifest/checksums | `.\speechlens.ps1 release` | `make release` |
| All submission gates | `.\speechlens.ps1 release-check` | `make release-check` |

Browser commands require the live server and `.venv\Scripts\python -m playwright install chromium`. Video captures actual actions and inference; it does not synthesize a fake app demo. Playwright capture is silent, so actual public WAV spans played in the walkthrough are muxed at logged offsets; this is disclosed in `evaluation/video_check.json`. Exported evidence and captions accompany it. No account publication occurs automatically.

The final demo is **448.93 seconds (7:29)**, with continuous capture and retained inference waits. It verifies the acceptable gain control's exact source hash and visible score of 100. Video listening audio is normalized separately; original analysis levels are unchanged. Representative scenes, full MP4 decoding and a sample CTC audio-recognition check passed. Independent human listening/annotation remains unmeasured. Report generation requires the completed full evaluation, renders every page under `tmp/pdfs`, and resets its visual-review gate until the new renders are inspected.

`demo-data` intentionally replaces the active manifest with a small vertical slice; run `dataset-build` to restore the full corpus. Generation preserves published speech identity but requires human review to accept final transcripts, perceptual severity, edited boundaries and non-edited artifacts. Do not confuse structural validation with independent annotation.

## Architecture and measurement

`ingest → validate → canonicalize → independent CTC alignment → native DSP → matched token/phrase units → detectors → rubric → template explanations → dashboard/export`.

One bounded inference subprocess is supervised by a thread; SQLite stores durable queued/running/succeeded/failed states. Interrupted jobs recover once, explicit retry is available, processing is capped at 900 seconds, uploads at 100 MB/600 seconds, and queue occupancy at ten jobs. CPU is the tested path. API schema and routes are visible at [OpenAPI docs](http://127.0.0.1:8000/docs).

The alignment default is a pinned Wav2Vec2 CTC implementation, a deliberate alternative to WhisperX's dependency tree. It consumes intended text, uses independent acoustic ASR edit matching as a mismatch gate and leaves uncertain words null. The 377 MB Apache-2.0 model snapshot is cached separately; exact revision and checksum are in `releases/model_manifest.json`.

FFT/STFT, 13 MFCCs/40 mel bands, pYIN with voicing masks, independent WebRTC VAD, RMS/dBFS, native elapsed/articulation rate and word-boundary pauses are persisted. Relative semitones remove median pitch; relative dB removes speech energy offset. Dynamic range is retained. Charts label token-normalized display coordinates separately from actual seconds; A/B playback is separate because durations differ.

Clarity remains diagnostic-only: noise/filter/channel damage and ASR mismatch do not establish poor articulation. Four YAML genre presets are product choices, not organizer judging weights. Missing evidence gives null categories; a total requires 60% scoring coverage. Scores express consistency with one supplied rendition, not absolute speaking ability. The evidence drawer carries quote, intervals, observed/reference values, units, delta, formula, threshold version and a specific correction.

## Evaluation snapshot

The current measured artifacts are [metrics](evaluation/metrics.json), [robustness](evaluation/robustness.json), [runtime](evaluation/runtime.json), [browser verification](evaluation/browser_e2e.json), [model integration](evaluation/model_integration.json), [failure cases](evaluation/failure_cases/localization.json), [ablation evidence](evaluation/ablations/measured.json), and [per-event rows](evaluation/per_event.csv).

The completed corpus has **346 recordings, 13 excerpts, six speakers and seven sources**, with zero structural errors or split leakage. Held-out synthetic-support macro F1 at tIoU 0.5 is **0.436**, missing the unchanged **0.75** target; micro F1 is 0.415 (17 matches, 9 false predictions, 39 missed supports). The held-out additive-noise method matches **0/8** supports. Median defined within-family Spearman is **0.949** over 39 of 52 requested groups; missing/constant groups are disclosed. All 149 predicted events pass quote, native-clock, numeric-value and rule audits.

The benchmark used four CPU processes on a 24-thread Windows host with 31.7 GB RAM: 30.3 minutes elapsed, median 0.716 processing seconds/audio second over uncached results, maximum reported per-process lifetime peak 2.20 GiB. These contention/cache-aware benchmark values differ from the serial app: the final fresh-upload browser check took 55.1 seconds end to end. 22 backend tests and one frontend test pass; npm audit reports zero vulnerabilities for the locked frontend dependencies.

Human alignment accuracy, perceptual localization, rubric validity, inter-rater agreement and human generalization are **unmeasured**. Localization metrics compare predictions to synthetic intervention support and are explicitly labeled proxies. Only one held-out test speaker supports no meaningful population confidence interval. Targets are retained even when they fail. See `evaluation/metrics.json` for actual counts and gate results.

The full offline benchmark can use `.venv\Scripts\python -m scripts.run_evaluation --workers 4` on a host with sufficient memory. References warm serially before concurrent variant processes. Measured per-recording latency then includes contention, and peak memory is the maximum per-process high water rather than aggregate pool memory; it is not the app's serial-upload latency. The default evaluation command uses one worker. Original acceptance targets are unchanged.

The fresh-upload vertical slice found a strong local duration ratio of 1.61 and a pacing score of 84.3. Its exposure-averaged total remained 95.5: short serious defects can be diluted, so inspect events and category scores. Non-clipping ±6 dB fixture copies showed a 0-point score shift; resampling was stable. A pitch-shift copy caused alignment abstention. Fresh repeated inference gave identical event IDs, values and displayed scores on this CPU environment. These are fixture results, not speaker-general performance claims.

## Containers, storage and cleanup

```bash
docker compose up --build
```

Compose binds loopback port 8000 and preserves separate upload/model volumes. The implementation host had no running Docker daemon, so **clean-container execution is unverified**. The container requires first-run model downloads through `docker compose exec speechlens /app/.venv/bin/python -m scripts.download_models`. Mounted caches enable later offline use.

`SPEECHLENS_STORAGE` selects the private storage directory. Public research caches in `.cache/` are ignored. Job caches are inside the private job directory and removed on deletion. Dataset originals under `data/originals/` are ignored; redistributable cropped WAVs and labels are retained in `data/`. Do not delete persistent upload volumes as routine cleanup. No authentication or multi-user ownership is implemented; keep this trusted local prototype bound to loopback.

## Documentation and attribution

[Architecture](docs/architecture.md), [math](docs/math.md), [scoring](docs/scoring.md), [reproducibility](docs/reproducibility.md), [annotation guide](docs/annotation_guide.md), [requirements matrix](requirements_matrix.md), [assumptions](ASSUMPTIONS.md), [progress](PROGRESS.md), [licenses](docs/licenses.md).

Detailed measured [evaluation and failure analysis](docs/evaluation.md) and [provisional baseline rationale/QA](docs/baseline_review.md) accompany the release. `release-check` exits with code 2 while mandatory public links or human acceptance are blocked; inspect its JSON for local-artifact success separately.

Repository code: MIT. Model: Apache-2.0. Source recordings/transcripts have separate documented public-domain or derivative attribution, including CC BY-SA 2.0 for the Pearl Harbor digitization. Wikimedia source-page snapshots retain their own CC BY-SA terms. Full URLs, exact original identities, crop times and source evidence hashes live in `data/provenance/`.
