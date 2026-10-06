# Track C — Complete implementation prompt for an AI engineering agent

Copy this entire file into an implementation agent as one prompt. It contains the problem requirements, design decisions, mathematical specification, execution sequence, verification gates, and submission checklist. The agent should build the solution, not return another plan.

---

## 1. Your mission and operating contract

You are the lead speech-signal-processing engineer, dataset engineer, full-stack developer, and evaluation researcher for **Multimodal AI Hackathon 2026, Track C: Contrastive Speech Analytics & Temporal Flaw Grounding**. Build a complete, runnable, evidence-backed submission named **SpeechLens**. Execute the work in this prompt through implementation, evaluation, documentation, and submission packaging.

The central task is to construct a custom dataset of effective public speeches and intentionally flawed performances of the **exact same transcripts**, spanning near-perfect to egregious delivery. Extract acoustic features, force-align transcript words, locate delivery flaws in time, explain the measured deviations, score against a reproducible custom rubric, and expose everything through an interactive dashboard.

Do not confuse this with ordinary speech transcription, an LLM critique of a transcript, or a generic presentation coach. Audio evidence and temporally grounded contrastive comparisons are the core product.

Work autonomously on reversible implementation choices. Inspect the available repository and environment first; preserve existing user work. Maintain `PROGRESS.md`, a requirements matrix, and an honest blocker log. Do not fabricate recordings, human reviews, performance results, external links, permissions, or completed uploads. If external credentials, redistribution rights, human recordings, or publication authority are unavailable, finish every locally achievable artifact and report the specific remaining action. Do not mark the entire submission complete while any mandatory deliverable is missing. Do not publish content or change repository visibility without authorization.

All numerical dataset sizes, thresholds, score weights, and performance gates below are **proposed engineering targets**, not organizer requirements or established scientific constants. Record deviations and why they were necessary. Prefer a smaller clean dataset over a large noisy one. Do not promise production-grade generalization from a hackathon-sized dataset.

## 2. Binding requirements and judging priorities

Source of organizer requirements: the supplied three-page `Track C.pdf`.

| Organizer requirement | Required implementation evidence |
|---|---|
| Effective public-speaker baseline | Source recordings, corrected transcripts, provenance, permissions/license evidence, and rationale for selection |
| Same-text flawed spectrum | Paired recordings at multiple flaw severities, exact transcript identity, transformation recipes or recording instructions |
| Accurate temporal labels | Word alignment plus independently reviewed flaw intervals and severity/type annotations |
| Advanced acoustic extraction | FFT/STFT, MFCCs, F0, energy, speech rate, pauses, and defensible clarity diagnostics |
| Temporal grounding | Start/end times on the participant's actual audio, with measurable localization accuracy |
| Mathematical explanation | Measured participant/reference values, delta, contextual interpretation, uncertainty, and an actionable correction |
| Interactive frontend | Audio and transcript upload, processing feedback, baseline/participant feature overlays, playable flaw regions |
| Reproducibility | Locked environments/models/configuration, deterministic scoring, repeat-run checks, runnable instructions |
| Speaker-agnostic comparison | Relative pitch/energy and cross-speaker evaluation without penalizing natural voice differences |

Judging weights: **data engineering and stress testing 30%; causal explainability and temporal grounding 25%; feature extraction 20%; dashboard 15%; reproducibility and code quality 10%.** Allocate effort accordingly; polish cannot substitute for reliable labels and measurements.

Mandatory final deliverables:

1. A GitHub repository link containing the complete codebase and documentation.
2. The custom paired dataset, including audio, transcripts, and alignment labels, either in GitHub or at a public Google Drive link included in the README. A dataset-building script alone does not satisfy this deliverable.
3. A functional interactive dashboard prototype.
4. Technical documentation of dataset construction, evaluation rubrics, architecture, and scoring methodology, **at most six pages**.
5. A **3–10 minute YouTube video** showing dataset collection, stress testing across qualities, and the dashboard detecting specific deviations.

The brief's context includes Interpretive Reading, Declamation, Extemporaneous, and Persuasive Oratory. Provide named rubric presets and disclose which genres the dataset actually validates. English and single-speaker speech are reasonable first-release scope choices; clearly report unsupported languages, overlapping speakers, and other limits. Text quality is discussed in the context, but the explicit contrastive task holds text constant. Keep the primary score a delivery score. Do not claim to measure argument quality through acoustic features. An optional separate content rubric may exist only if it has its own evidence and evaluation; it is not a substitute for the required work.

## 3. Product behavior and architectural decisions

The main workflow is: choose a curated reference speech or upload reference audio and its transcript; upload a participant rendition of the same text; confirm the transcript; process; inspect rubric scores and flagged regions; play matching reference/participant spans; inspect numeric evidence; export results.

Support two explicit modes:

- **Paired evaluation:** same canonical text, independently aligned reference and participant recordings. This is the primary graded mode.
- **Unpaired diagnostics:** participant audio and transcript without a reference. Report general pacing/pause/recording-quality observations with lower confidence. Do not display fabricated baseline overlays or pretend to have equivalent paired scores.

An arbitrary new transcript is evaluated in paired mode only if a compatible reference is supplied. A famous speaker is one useful example of effective delivery, not a unique optimum. Use accepted ranges, context, multiple good renditions when available, and human review so a stylistic difference does not automatically become a flaw.

Use a modular deterministic pipeline:

`ingest → validate → canonicalize text → align each recording → extract native-time features → match token/phrase units → detect and localize → score → explain → visualize/export`.

Keep preprocessing, alignment, feature extraction, detection, score aggregation, and explanation separate. Persist intermediate artifacts with hashes so problems can be diagnosed and a change to the rubric does not require repeating ASR.

### Recommended stack

| Layer | Default choice | Implementation constraint |
|---|---|---|
| DSP/backend | Python, NumPy, SciPy, librosa, SoundFile | Choose a mutually compatible supported Python release; pin resolved versions |
| Audio conversion | FFmpeg/ffprobe | Explicit sample rates, channels, codec settings, bounded subprocess runtime |
| Transcription/alignment | WhisperX with a pinned compatible alignment model | ASR drafts transcripts; alignment consumes corrected intended text; verify installed API |
| Alignment fallback | Montreal Forced Aligner in a separate environment | Only if the primary path is inadequate; pin dictionary and acoustic model |
| Pitch manipulation | PyWORLD; pitch-preserving time-stretch where appropriate | Quality-check transformed recordings and include sham-resynthesis controls |
| VAD | A pinned speech VAD implementation, such as Silero VAD | Keep VAD separate from F0 voicing; breaths and unvoiced consonants matter |
| Evaluation/calibration | pandas, scikit-learn, SciPy | Interpretable thresholds first; optional simple ordinal/pairwise model only if data supports it |
| API/schema | FastAPI, Pydantic, Uvicorn | Schema-validated requests/results, persistent job status |
| Worker | One bounded Python worker with SQLite job records | Durable queued/running/succeeded/failed states; no heavy inference in async request handlers |
| Frontend | React, TypeScript, Vite | One app, no unnecessary microservices |
| Charts/audio | Plotly.js and WaveSurfer.js or native audio | Shared selection state, explicit time-axis meaning, accessible controls |
| Storage | Local files plus SQLite | Configurable persistent volume; no cloud dependency for the demo |
| Tests | pytest, frontend test runner, Playwright | Mathematical, integration, and genuine end-to-end checks |
| Reproducibility | uv or equivalent Python lockfile, npm lockfile, Docker Compose | Pin model revisions and record CPU/GPU provenance |
| Documents/demo | Markdown, a PDF renderer, FFmpeg, browser recording | Technical PDF ≤6 pages; video 180–600 seconds |

Begin with a CPU-compatible path and optional GPU acceleration. Do not assume a GPU or invent throughput. Benchmark on the actual machine. Freeze working dependency versions after a small compatibility spike rather than asserting that all latest releases work together. Check package/model licenses and record their exact revisions.

Do not require a paid LLM API. Structured template explanations are sufficient and more reproducible. If an LLM is later offered for rephrasing, give it only validated evidence, prohibit invented measurements, preserve the original evidence JSON, and make it optional and non-scoring.

## 4. Dataset design: build the strongest part first

### 4.1 Coverage and size

Target **12 source excerpts, 30–60 seconds each, from at least six public speakers**, including several rhetorical styles. A useful fallback floor is six excerpts from at least four speakers, but disclose reduced generalization. Source actual effective public speech recordings; self-recordings and TTS can supplement them but must not silently replace the public baseline requirement.

For each source excerpt aim to create:

- One clean reference.
- Five flaw families × four intensity levels = 20 single-family variants.
- Two compound-flaw variants.
- Two negative controls, including a benign transformation and a sham processing condition.

At the target size, this is 300 recordings before additional human mirrors. Treat that count as a planning estimate; dataset QA decides what is retained. Add a small set of human same-text renditions by consenting speakers, including acceptable alternatives and subtle/strong flawed versions. These are crucial for detecting synthetic artifacts and speaker overfitting. If unavailable, the human generalization result must remain unmeasured.

### 4.2 Sourcing and provenance

For each source, retain URL, speaker, title, original recording identity, crop times, language, retrieval date, file checksum, transcript provenance, and redistribution/derivative-use evidence. Public availability alone is not proof of reuse permission. Select material with documented permission or appropriate reuse status, and distinguish rights in the recording from rights in the transcript. If rights cannot be established, replace the source; do not publish it and do not count a private inaccessible collection as the required public dataset.

Listen for clear single-speaker speech with limited music, applause, room noise, and edits. Maintain excluded-source reasons. Correct ASR manually, including contractions, numbers, repetitions, and punctuation. Preserve both display text and normalized alignment tokens with stable token IDs. A good baseline needs a short written delivery rationale and acoustic-quality review; celebrity alone is insufficient.

### 4.3 Flaw families and severity gradient

| Family | Controlled intervention | Evidence to target | Guardrail |
|---|---|---|---|
| Rushed or dragged pacing | Stretch/compress selected phrases while preserving pitch | Words/second, phrase duration ratio, inter-word timing | Preserve all words; changes to rate are not automatically flaws |
| Monotone or distorted intonation | Contract phrase F0 range around its median, or create misplaced contour changes | Semitone range, contour slope, emphasis contrasts | Preserve voicing and formants where possible; inspect artifacts |
| Misplaced/abnormal pauses | Insert/remove/extend silence at selected token boundaries | Pause duration and syntactic/rhetorical position | Do not remove consonants; punctuation is only a weak context cue |
| Missing or excessive emphasis/energy control | Smooth energy flattening, phrase fades, or targeted misplaced stress | Relative dB envelope and joint F0/duration emphasis | Whole-file gain is a negative control, not weak-delivery ground truth |
| Reduced vocal clarity | Human under-articulation where possible; explicitly labeled signal degradations as separate proxies | Intelligibility checks and acoustic quality evidence | Low-pass/noise/codec damage is recording degradation, not proof of poor articulation |

Use configurable levels 0=accepted, 1=subtle, 2=mild, 3=strong, 4=egregious. Initial pace ratios might be 1.08/1.18/1.35/1.60 and F0-range multipliers 0.85/0.65/0.40/0.15. These are generator starting points, not universal evaluation thresholds; confirm perceptual severity and revise. Include both directions for pace and suitable bidirectional flaws elsewhere. Randomize local positions and parameter values within levels so the detector cannot memorize one threshold recipe.

Generate local interventions as well as global ones. Near-perfect variants should include small but meaningful defects and acceptable differences, because indiscriminate detection must be penalized. Include quality-matched sham transformations using the same vocoder/stretcher with identity settings; otherwise models may detect the tool instead of the flaw. Never expose filenames, severity labels, transform parameters, or generation metadata as inference features.

### 4.4 Annotation and exact time mapping

Store both the transformation support interval and the independently assessed perceptual flaw interval. They may differ. Transformation support is not automatically human ground truth.

After duration-changing edits, compute and store a piecewise source-to-variant time map. For a source interval `[a,b]` rendered with duration multiplier `k`, interior mapping is `t′=a′+k(t−a)`; every later segment receives the accumulated duration shift. Inserted pauses create explicit added target intervals. A deleted interval has no one-to-one inverse. Store monotone segments plus insertion/deletion events rather than pretending the mapping is always bijective. Include fades/crossfades in support intervals and track their actual sample counts.

Align the generated audio again and compare against propagated word boundaries. Review all edited boundaries and all subtle variants. Inspect non-edited spans for artifacts. For human mirrors, annotate from listening and waveform evidence; there is no synthetic time map. Permit overlapping flaw labels.

Create an annotation guide defining labels, levels, onset/offset conventions, ambiguity, and acceptable alternative delivery. Have two reviewers independently annotate a representative subset, especially held-out evaluation audio, then adjudicate disagreements. Report boundary disagreement and ordinal agreement if reviews exist. An agent's self-review is not two independent human reviewers.

### 4.5 Dataset records and splits

Use JSONL manifests and separate word/event JSON. Each recording record needs:

```json
{
  "recording_id": "spk01_excerpt01_pace_level2_001",
  "pair_group_id": "spk01_excerpt01",
  "reference_id": "spk01_excerpt01_good",
  "speaker_id": "spk01",
  "source_recording_id": "source01",
  "transcript_id": "text01",
  "transcript_sha256": "COMPUTED_HASH",
  "audio_path": "audio/spk01_excerpt01_pace_level2_001.wav",
  "audio_sha256": "COMPUTED_HASH",
  "sample_rate_hz": 16000,
  "duration_s": 42.0,
  "generation_method": "local_time_stretch",
  "flaw_family": "pace",
  "severity_label": 2,
  "split": "train",
  "alignment_path": "alignments/recording_id.json",
  "events_path": "events/recording_id.json",
  "provenance_id": "provenance01",
  "review_status": "pending"
}
```

This is a schema illustration, not a real dataset row. Generate real paths, hashes, and values; no placeholders may survive into release data. Multiple-flaw examples need per-event types and severities rather than only the coarse record label. Word records need canonical ID, text, start/end seconds, alignment confidence/source, and review status. Event records need interval, token span if applicable, type, severity, provenance, uncertainty, and reviewer/adjudication metadata.

Split before generating variants. With six source speakers, use approximately four train, one validation, one test speaker; all excerpts, mirrors, transformations, and near-duplicates tied to a source remain together. All uses of the same text must stay in one split, including renditions by other speakers: construct connected groups over speaker/source/transcript relationships and split whole groups. Plan collection to keep these groups viable. Report the small number of independent sources behind large variant counts. Supplement the fixed split with leave-one-source/speaker-out analysis if feasible.

Use train for fitting, validation for threshold/model selection, and test once after freezing settings. Providing the held-out reference at inference is allowed because the task is paired comparison; using its flaw labels to tune parameters is not. Hold out at least one generation method or parameter regime and test human recordings separately.

Release a dataset card, annotation guide, license/provenance table, split manifest, checksums, generation recipes, seeds, and scripts. If GitHub cannot hold the audio sensibly, place the complete release in an authorized public Google Drive folder and put the verified link plus download/verification commands in README. Include a small legally redistributable demo subset in the repository.

## 5. Signal processing and mathematics

Use seconds throughout public schemas and explicitly document all conversions to frame/sample indices. Maintain native reference and participant clocks. Never report a warped display coordinate as a real participant timestamp.

### 5.1 Audio ingestion

Retain the original file and lossless canonical audio. Decode to mono 16 kHz for the main pipeline, preserving original duration and documenting downmixing. Keep higher-rate source audio for optional diagnostics where useful. Detect empty/silent audio, clipping, invalid decoding, excessive duration, and unsupported multi-speaker content. Avoid denoising, compression, or global amplitude normalization before quality measurements; these can erase evidence. A separate listening-normalized copy is allowed if clearly identified.

Use configurable limits, initially ten minutes and 100 MB per upload. Compare duration before/after conversion and preserve timing offsets. Do not trim leading/trailing silence without retaining the offset mapping.

### 5.2 STFT, spectrum, and MFCC

For samples `x[n]`, a Hann window `w[n]`, frame length `L=400` (25 ms at 16 kHz), hop `H=160` (10 ms), and `NFFT=512`, compute:

`X(m,k)=Σ(n=0…L−1) x[mH+n]w[n]exp(−j2πkn/NFFT)`.

Use `|X|²` with documented normalization as the power spectrum. Compute log-mel energies and MFCCs:

`M(m,b)=log(ε+Σk B(b,k)|X(m,k)|²)`;

`c(m,q)=Σ(b=0…B−1) M(m,b)cos[πq(b+1/2)/B]`.

Start with 40 mel bands and 13 MFCCs, with specified DCT normalization; optional deltas are diagnostic. Fix centering/padding conventions and test frame timestamps. A 512-point FFT zero-pads the 400-sample window; do not claim it creates additional physical frequency resolution.

MFCCs describe spectral shape and are strongly influenced by phonetic content, speaker, and channel. Compare text-matched units, apply training-fitted scaling where needed, and use them as diagnostic/corroborative features. MFCC distance alone is not a reliable causal definition of poor speaking.

### 5.3 F0 and speaker normalization

Use pYIN or another validated estimator with voicing probability. Pitch estimation needs a longer window than the 25 ms spectral window for low voices: start near 64 ms with the same 10 ms hop, use an appropriately broad configurable search range such as 50–600 Hz, and flag octave errors/range clipping. Avoid treating unvoiced frames as zero pitch. Keep missing values and voicing masks explicit.

Convert voiced F0 to semitones relative to a robust per-recording center:

`p_s(t)=12 log2(F0_s(t)/median_voiced(F0_s))`.

This removes a constant pitch offset while preserving variation in semitones. **Do not divide every recording by its own pitch standard deviation or range:** that would normalize away monotony. For a phrase compute `R_p=Q90(p)−Q10(p)`, robust slope, and token-level prominence. Detect deficient variation using a ratio such as `R_participant/(R_reference+ε)` plus a minimum absolute reference range and adequate voiced coverage. A flat reference cannot justify a monotony accusation.

Report raw Hertz for transparency, normalized semitone curves for cross-speaker comparison, and reference/participant range values. Low voicing coverage triggers uncertainty or abstention, not a low pitch score.

### 5.4 Energy and recording quality

Compute frame RMS and digital level:

`RMS_m=sqrt((1/L)Σn x[mH+n]²)`;

`E_m=20log10(RMS_m+ε)` dBFS for appropriately normalized floating-point PCM.

Use `E_rel=E−median_speech(E)` for delivery comparison, keeping dynamic range and local prominence. Do not divide by per-recording energy standard deviation, which can erase flattening. Whole-file gain should not change the delivery judgment materially. Uncalibrated microphone recordings cannot establish absolute vocal loudness or sound-pressure level. Treat clipping, noise, reverberation, and codec effects as recording-quality findings with separate labels.

### 5.5 Rate, pauses, and emphasis

For a phrase containing `N` matched words, use `WPM=60N/T_elapsed`. Also calculate articulation rate using estimated speech-active duration, and explicitly distinguish its denominator from elapsed duration. If syllable rates are implemented, state dictionary/estimation limitations.

At word boundary `i`, `pause_i=max(0,start_(i+1)−end_i)`. Confirm candidate gaps with VAD and waveform/energy evidence; forced alignment gaps alone may be wrong. Attach pauses to boundaries, not invented words. Punctuation and rhetorical annotations supply context but do not impose universal durations.

Use duration ratios `r_d=T_participant/T_reference` and `log(r_d)`; retain global rate deviations as well as local deviations. If local residuals subtract a global tempo offset, keep a separate global score so uniformly rushed speech is still detectable.

Define interpretable emphasis measures from within-phrase relative energy, semitone prominence, and matched-word duration. Standardize with train-fitted robust scales and explicit floors. Require reference emphasis and contextual evidence before declaring missing/misplaced emphasis. Document correlations so one acoustic cause does not create three independent penalties.

### 5.6 Forced alignment and shared-text comparison

Obtain corrected transcripts before final dataset alignment. Normalize punctuation/numbers for the aligner while retaining mappings back to display tokens. Use ASR segments or bounded phrase windows as coarse anchors and align the intended text within those windows. Verify how the pinned alignment API accepts supplied text; do not replace it silently with ASR output.

Align reference and participant independently. Validate monotonicity, in-range boundaries, unaligned tokens, confidence, and improbable word durations. A transcript with missing/repeated words needs explicit edit matching and a mismatch report. Do not force absent words into plausible-looking timestamps. Severe mismatch should block paired scoring for affected spans while leaving unaffected diagnostics available.

Match by canonical word and phrase IDs. Plot native-time features and, separately, a transcript-normalized view (token index plus within-token progress). Interpolate only within valid voiced/observed regions; never bridge long pauses with a smooth fictional F0 curve. For pauses, use boundary events or a pause comparison panel because word warping would collapse them.

Optional constrained DTW can compare contour shape within matched phrases using:

`D(i,j)=c(i,j)+min[D(i−1,j),D(i,j−1),D(i−1,j−1)]`,

with band/slope constraints and masked missing values. It must never replace native-time duration/pause metrics or warp away the flaw being measured. The initial system should work without DTW.

### 5.7 Reference envelopes and deviations

For each interpretable statistic `f_j` compute a signed paired residual using an appropriate transform:

`δ_j=g_j(f_participant)−g_j(f_reference)`.

Use logs for positive duration/range ratios and additive differences for semitone/dB quantities. From accepted training pairs estimate residual center `μ_j` and robust scale `σ_j=max(1.4826 MAD(δ_j),σ_floor,j)`. Then:

`z_j=(δ_j−μ_j)/σ_j`.

Do not estimate a normative population variance from a single reference rendition. When good-pair coverage is insufficient, use disclosed conservative engineering tolerances and report uncalibrated confidence. Use genre/context strata only when enough examples exist; otherwise pool and acknowledge the limitation.

Convert directional deviation into severity evidence, for example `a_j=clip((z_bad−τ_warn)/(τ_severe−τ_warn),0,1)`, where `z_bad` has the proper sign or is two-sided as appropriate. Select thresholds using validation data, freeze them, and retain actual physical units in explanations.

## 6. Localization, scoring, and explanations

### 6.1 Detection/localization

Implement independent detectors for pace, pitch range/intonation, pauses, emphasis/energy, and clarity/recording quality. Each returns candidate events, measurable evidence, confidence inputs, and feature support. Use phrase-level windows for rate/monotony and boundary-level events for pauses. Do not claim frame-level accuracy for a statistic computed over an entire phrase.

For frame-supported events, use short median smoothing, separate onset/offset thresholds (hysteresis), configurable minimum duration, and merging only across small gaps of the same type. Initial smoothing/minimum durations near 150–300 ms are tuning values, not promises. Short pause errors need their own rules. Refine boundaries using alignment/VAD where appropriate and preserve uncertainty intervals.

Gate findings on alignment coverage, adequate voiced/speech support, input quality, and reference suitability. Confidence should be a documented heuristic unless calibrated against independent labels; never display an uncalibrated heuristic as an accuracy probability. Support “insufficient evidence.”

### 6.2 Rubric and deterministic scores

Provide versioned YAML presets for the four named genres and editable weights in the UI. Proposed default delivery weights: pacing 25%, pauses 20%, intonation 25%, emphasis/energy 20%, supported clarity/intelligibility 10%. These are product choices, **not the organizer's judging weights**.

For each category, build a disjoint set of scoring units (phrases or eligible boundaries). Let `a_u∈[0,1]` be validated severity, `d_u` its fixed exposure weight, and `I_u` indicate sufficient evidence. Compute:

`P_k = Σu I_u d_u a_u / Σu I_u d_u`; `S_k=100(1−P_k)`.

If the denominator is zero, return null. Exclude missing evidence from both numerator and denominator; do not treat missing observations as perfect delivery. Compute category coverage separately. Boundary-event categories may use equal boundary weights rather than seconds; document this. Use a calibrated peak-severity term only if validation demonstrates the mean otherwise hides short serious events.

Within a category, combine overlapping evidence by a documented maximum or bounded aggregation before integration so overlaps do not double-count. Across categories, define shared-cause handling and validate it on compound flaws. For eligible categories, `S=Σk w_k S_k/Σk w_k`; display included weights and coverage. Below a configured coverage floor, withhold the total or prominently label it partial; never show an unqualified high score from one surviving category.

Clarity scores require validated evidence. Without human intelligibility labels or a defensible model evaluation, report clarity as diagnostic-only and disclose the renormalized delivery weights. ASR errors alone cannot prove poor articulation. Reference recordings can also have flaws and need not score 100. Avoid a cosmetic rescaling designed to force ideal separation.

Make the score a pure function of versioned features/configuration. Persist feature, detector, rubric, dataset, and model versions. Same input/configuration must yield the same displayed score within documented numeric tolerances.

Optional learned enhancement: train an interpretable ordinal model or pairwise ranker on aggregate residual features with grouped splits. For quality function `qθ(x)` a pairwise loss is `Σ log(1+exp(−(qθ(good)−qθ(bad))))+λ||θ||²`. Compare to deterministic rules, keep localized evidence separate, and retain the simpler solution unless the learned model improves held-out outcomes. Do not train a deep model from scratch on a few source speeches.

### 6.3 Evidence-first explanations

Each event must contain: type, participant interval, reference interval or matched token IDs, transcript quote, observed/reference values, units, delta, threshold/rule version, context, confidence rationale, and a specific correction. Example structure:

```json
{
  "type": "rushed_phrase",
  "participant_interval_s": [12.4, 14.1],
  "reference_interval_s": [13.2, 16.0],
  "token_ids": [31, 32, 33, 34, 35, 36, 37, 38],
  "measurements": {"participant_wpm": 282.4, "reference_wpm": 171.4},
  "duration_ratio": 0.607,
  "rule_id": "pace.fast.v1",
  "interpretation": "This matched phrase is substantially compressed relative to the reference.",
  "suggestion": "Lengthen this phrase and preserve a short pause at its clause boundary."
}
```

This example uses eight words over 1.7 versus 2.8 seconds; it is illustrative, not a claimed result. Generate real quotes, values, thresholds, and intervals at runtime. Show why a deviation matters in the particular phrase, not just “z-score high.” Corrections should refer to the relevant phrase/boundary and suggest a measurable direction without demanding exact imitation.

Use “causal” carefully: controlled synthetic interventions provide evidence that a known manipulation produces a measured acoustic change. Observational audio supports a signal-based explanation, not certainty about intent, anxiety, biology, or listener response. Do not infer personal traits. For research evidence, compare an edited recording to its matched sham control and show restoration/removal of the edit reduces the corresponding detector response. Keep this separate from the user-facing confidence label.

## 7. API, files, and dashboard

Implement these contracts or equivalent clearly documented routes:

- `POST /api/evaluations`: multipart participant audio, transcript, reference ID or uploaded reference+text, preset/config; return `202` with a job ID.
- `GET /api/evaluations/{id}`: status, stage, progress, warnings, failure details, and result metadata.
- `GET /api/evaluations/{id}/result`: scores, coverage, alignments, events, feature series, provenance/config hashes.
- `GET /api/evaluations/{id}/audio/{role}`: safe streaming/seekable playback.
- `GET /api/references`: curated examples and supported metadata.
- `GET /api/evaluations/{id}/export`: JSON and CSV bundle or separately documented downloads.
- `DELETE /api/evaluations/{id}`: delete uploaded audio and derived results according to retention rules.
- `GET /healthz` and model/worker readiness information.

Use opaque job IDs, validated paths, extension plus decoded-content checks, bounded processing time/concurrency, and escaped transcript display. Keep user uploads out of the public dataset unless separately authorized. Persist job state; handle worker interruption and retries without corrupting results. Cache by audio/transcript hashes and complete pipeline configuration, not just filename.

Dashboard panels:

1. Upload/reference picker with drag-and-drop, transcript editing, supported-language notice, and a deterministic demo example.
2. Stage progress with actionable validation errors and recovery.
3. Delivery score/category cards with rubric weights, coverage, and uncertainty.
4. Reference and participant waveforms on native time axes, linked via matched tokens.
5. Pitch, relative energy, rate, and pauses; toggle native-time and transcript-normalized comparison, with labeled units.
6. Highlighted transcript with click-to-seek and unaligned-word indicators.
7. Flaw timeline/list, filterable by type/severity; clicking a flaw selects and plays the participant span and corresponding reference span.
8. Explanation/evidence drawer with exact values, formula/rule, context, and coaching action.
9. Dataset explorer demonstrating levels 0–4 for the same text and displaying measured score changes, not prefilled marketing charts.
10. Export controls and a compact reproducibility/provenance view.

Do not attempt to play unequal-duration paired audio simultaneously and call it synchronized; use A/B playback or explicitly token-linked navigation. Downsample display series without losing event peaks and retain full-resolution data for calculations. Distinguish ground-truth labels from predicted overlays in the dataset explorer. Include keyboard navigation, readable contrast, color-independent event cues, and mobile-width layout.

## 8. Ordered execution plan with completion gates

### Phase 0 — Inspect and freeze the contract

Inspect files, tools, hardware, repository status, available source audio, and credentials. Create `requirements_matrix.md`, `PROGRESS.md`, `ASSUMPTIONS.md`, and `BLOCKERS.md`. Map every organizer requirement to an artifact and a future verification step. Resolve rights/access blockers early while continuing local work. Gate: no requirement has been silently dropped.

### Phase 1 — Prove dependency compatibility

Create the Python/frontend environments and a small legal speech fixture. Demonstrate decode → supplied-text alignment → F0/RMS/MFCC → JSON output on CPU. Pin dependencies/model revisions only after this works. Define schemas and unit conventions. Gate: a real audio clip traverses the pipeline; no placeholder features.

### Phase 2 — Build the minimum vertical slice

Use one reference and one same-text local pacing/pause variant. Save correct word/time mappings, detect the deviation, render native-time charts and A/B playback, and export the evidence JSON. Gate: a reviewer can click a detected event and hear the corresponding error. This de-risks integration before expanding the corpus.

### Phase 3 — Collect and annotate baseline sources

Acquire the target excerpts, correct transcripts, document provenance, establish split groups, and review reference quality. Build the annotation guide and baseline alignment QA. Gate: every accepted source has usable audio, accurate text, evidence for distribution, a split, and reviewed timestamps.

### Phase 4 — Generate/review the spectrum

Implement deterministic local transformations with time maps; generate severity families, compound edits, sham variants, and negative controls. Add consenting human mirrors where available. Independently review labels and reject artifacts. Gate: manifest validation passes; real audio and label files exist; no pair crosses splits; difficult/near-perfect examples are included.

### Phase 5 — Finish DSP and normalized comparison

Implement all formulas, masks, window/frame conventions, phrase/token mapping, and signal-quality checks. Preserve global pace and pitch/energy range. Gate: synthetic known-signal tests and real audio spot checks agree; gain/pitch offsets do not create systematic delivery penalties.

### Phase 6 — Detectors, confidence, rubric, explanation

Implement deterministic detectors, localization, aggregation, abstention, presets, schema-backed explanations, and result hashes. Calibrate only on train/validation. Gate: each event is traceable to measured evidence; no circular use of injected labels or transform metadata at inference.

### Phase 7 — Evaluation and freeze

Run the evaluation matrix below. Inspect failures, tune using validation only, then freeze a release configuration and run held-out test evaluation. Produce metrics, plots, ablations, and failure examples. Gate: results are actual measured outputs with denominators, split identities, and uncertainty; failed targets are disclosed.

### Phase 8 — Complete the dashboard and deployment package

Finish job handling, upload validation, all core visualizations, export, responsive states, and accessibility. Produce Docker Compose and a local quickstart. Add authorized hosting only if available; a local functional prototype still needs a reliable demo path. Gate: a clean machine/container can run the app and process a new upload, not only cached examples.

### Phase 9 — Package all five mandatory deliverables

Finalize repository, release data, ≤6-page technical PDF, video, and README links. Record the full demo and prepare captions/transcript. Publish only with appropriate access/authorization; otherwise produce the upload-ready files and precise blocker. Gate: inspect every submission link and verify actual file accessibility rather than inferring it from successful upload.

Use the dataset and temporal explanation phases as the critical path. If time is constrained, reduce breadth, fancy visual effects, optional learning, and optional DTW before weakening data QA, test separation, or evidence grounding. A blocked mandatory output remains a blocker, not an optional item.

## 9. Evaluation and meaningful tests

### 9.1 Metrics

- **Alignment:** median, mean, and P90 absolute onset/offset error against independently checked word boundaries; fraction unaligned and coverage by speaker/condition.
- **Localization:** event precision/recall/F1 at temporal IoU thresholds 0.3 and 0.5. `tIoU=intersection_duration/union_duration`. Match predicted/true events one-to-one by type with maximum-weight matching and the stated cutoff. Unmatched predictions are false positives; unmatched labels are false negatives. Report micro and macro results.
- **Boundary accuracy:** start/end errors for matched events plus missed-event counts, so good errors on a tiny matched subset cannot conceal low recall. Separate short pause events and phrase-level events.
- **False alarms:** on accepted/sham controls, report false events/minute and false-positive duration; distinguish genuinely unlabeled regions from reviewed negatives.
- **Severity ordering:** within each source/family, Spearman correlation between injected/reviewed severity and penalty, pairwise ordering accuracy, and frequency/magnitude of monotonicity violations.
- **Rubric validity:** compare system category scores with independent human category ratings where available; report sample counts, rank correlation, and disagreement. No human labels means no claim of human agreement.
- **Robustness:** benign gain changes, resampling, encoding, constant pitch shifts within reasonable ranges, held-out speakers/texts/transforms, background noise, and human mirrors. Distinguish acceptable invariance from quality degradation that should trigger a warning.
- **Explainability:** audit whether quoted text, values, intervals, direction, and rule match the actual output; separately assess whether advice is useful. Include controlled edit/removal experiments.
- **Runtime:** cold/warm latency, peak memory, processing-seconds/audio-second, hardware, and model-cache state.
- **Reproducibility:** repeated runs and a clean-container run with fixed input/configuration, event comparison, numeric tolerances, and displayed-score stability.

Bootstrap at the source/speaker group level, not independent synthetic-variant rows. Report confidence intervals only when the number of independent groups supports an informative estimate; disclose weak evidence from small test sets.

### 9.2 Provisional acceptance targets

Treat these as development gates to aim for and report honestly, not guaranteed outcomes:

| Check | Initial target |
|---|---|
| Dataset integrity | 100% references/paths/checksums/labels valid; no split leakage |
| Reviewed clean alignment | Median boundary error ≤100 ms and P90 ≤250 ms |
| Synthetic local flaws | Macro event F1 ≥0.75 at tIoU 0.5, reported per type |
| Near-perfect/human conditions | Report separately; no assumed threshold or synthetic-to-human extrapolation |
| Accepted control false alarms | ≤1 predicted flaw/minute on reviewed controls |
| Severity gradient | Within-family median Spearman correlation ≥0.8 with penalty |
| Benign global gain invariance | Total score shift ≤3/100 for non-clipping ±6 dB copies |
| Same-environment repeated run | Same event IDs/types and displayed scores; numeric values within declared tolerance |
| End-to-end app | Real upload → completed result → playable timestamp → exported evidence passes |
| Technical document/video | PDF ≤6 pages; video 180–600 seconds |

If a target fails, record the failure and resulting product limitation. Do not lower a target after seeing test results without retaining the original and explaining the change; use validation for subsequent improvements.

### 9.3 Required test cases and ablations

Unit tests: known-frequency sine for F0 sanity (not speech validity), known RMS sine level, silence/unvoiced masks, deterministic STFT timestamps, inserted pause length, duration-changing time map, word mapping after insertion/deletion, monotonic aligned timestamps, bounded score aggregation, missing-evidence behavior, and hash/cache invalidation. Test detectors on intentionally localized edits, not just schema construction.

Integration: audio/transcript mismatch, omitted/repeated words, clipped/noisy speech, short input, silent input, unsupported language, corrupted/oversized upload, job interruption/retry, and a reference that is itself unusually flat. Confirm no duplicate penalties for overlapping same-category events and no healthy score for an all-missing case.

End-to-end: upload a real reference/participant pair in the browser, wait for completion, inspect an event, seek playback, change preset, and export a schema-valid result. Test live processing separately from cached demonstrations.

Ablations: raw versus normalized pitch/energy; native duration metrics versus over-warped comparison; single-family versus compound flaws; with/without alignment quality gating; synthetic versus human examples; ordinary versus sham-resynthesized controls. Show which design choices actually improve accuracy or reduce bias.

## 10. Repository and reproducible commands

Use this layout or a comparably clear one:

```text
README.md
PROGRESS.md
ASSUMPTIONS.md
BLOCKERS.md
requirements_matrix.md
pyproject.toml / uv.lock
compose.yaml / Dockerfile*
.env.example / .gitignore
backend/app/{api,schemas,jobs,storage}.py
backend/speechlens/{ingest,text,alignment,features,comparison,detectors,scoring,explanations}.py
frontend/src/{components,pages,api,types}/
frontend/package.json / package-lock.json
configs/{pipeline,detectors,rubrics,splits}/
scripts/{download_models,build_dataset,validate_dataset,run_evaluation,make_release}/
data/{demo,manifests,transcripts,alignments,events,provenance}/
tests/{unit,integration,e2e}/
evaluation/{metrics.json,per_event.csv,plots,ablations,failure_cases}/
docs/{dataset_card,annotation_guide,architecture,math,scoring,reproducibility}.md
docs/technical_report.pdf
demo/{script.md,storyboard.md,captions.vtt,demo.mp4}
releases/{checksums.txt,submission_manifest.json}
```

Keep large local/generated caches ignored; do not omit the required public dataset release. Include code license and separate data/model attribution. Exclude credentials and unconsented uploads.

Implement and test commands equivalent to:

```bash
make setup
make models
make demo-data
make dataset-validate
make dataset-build
make test
make evaluate
make report
make demo-video
docker compose up --build
make release-check
```

These are contracts to implement, not commands assumed to exist. Document exact prerequisites, first-run downloads, offline operation after caches are prepared, supported devices, volume locations, and cleanup. `make demo-video` may assemble already captured footage; it must not fake a real app demo. `release-check` should validate manifests, required artifacts, PDF page count, video duration, and submission-link status. Keep unavailable network checks distinguishable from failed links.

## 11. Six-page technical report

The ≤6-page limit applies to the final technical report, not this implementation prompt or the entire repository documentation. Produce a readable PDF with no tiny-type workaround. Suggested allocation:

1. Problem, scope, contributions, architecture diagram, and requirement mapping.
2. Dataset sources, same-text construction, severity gradient, labels, splits, provenance.
3. Signal processing, forced alignment, time mapping, and speaker normalization.
4. Temporal detectors, score/rubric formulas, confidence, and worked evidence example.
5. Measured evaluation, stress tests, ablations, and representative errors.
6. Dashboard workflow, reproducibility, limitations, and concise references.

Use real plots and actual screenshots. Put extensive implementation details in repository Markdown and link them, while ensuring the report itself still covers every required technical topic. Render and visually inspect every page; verify page count programmatically.

## 12. Demo video and submission handoff

Target a **6–8 minute** narrated or clearly captioned demo within the required 3–10 minute range. Proposed sequence:

- 0:00–0:35: problem and what makes the system contrastive.
- 0:35–1:35: source provenance, transcript correction, generation/re-recording, and temporal label review.
- 1:35–2:25: play same-text accepted/subtle/strong variants and show real stress-test outcomes.
- 2:25–4:40: demonstrate actual upload and processing, pitch/energy/rate overlays, flaw selection, A/B audio, mathematical evidence, and actionable advice.
- 4:40–5:40: held-out evaluation, human/synthetic distinctions, and speaker normalization/negative controls.
- 5:40–6:40: reproducibility, limitations/failure case, repository/dataset/report locations.

Include at least one subtle flaw, one obvious flaw, and one acceptable variation that is not incorrectly penalized. If editing around inference wait time, label the edit; do not imply impossible latency. Provide captions and a transcript. Inspect the final video with ffprobe and play representative segments to verify intelligible audio, visible charts, correct timing, and duration. Upload to YouTube only with authorized access, and verify the resulting video is viewable by judges. A local MP4 is an upload-ready artifact but does not alone satisfy the required YouTube-link deliverable.

README must contain GitHub URL, dataset location, dashboard launch/access instructions, technical PDF link, YouTube URL, setup commands, model/data licenses, evaluation snapshot, hardware/runtime notes, and limitations. External links must be real and verified; leave blocked fields clearly marked rather than inventing them.

Final agent response should provide a compact deliverables table with artifact/link, completion status, and verification result; summarize measured results and remaining blockers. Include the exact clean-start command. Do not state “fully complete” until all five mandatory deliverables exist and are accessible in their required forms.

## 13. Technical references and version policy

Consult official sources and the installed package APIs when implementing. The following primary references were checked while preparing this prompt on 2026-10-05; they are starting points, not a compatible dependency lockfile:

- WhisperX implementation and supplied-text alignment code: https://github.com/m-bain/whisperX and https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py . The project supplies ASR and alignment functionality; verify the pinned release's API and model requirements.
- librosa pYIN reference: https://librosa.org/doc/0.10.2/generated/librosa.pyin.html . Consult the documentation matching the installed version for parameters, voicing outputs, frame sizes, and centering.
- librosa MFCC reference: https://librosa.org/doc/0.10.2/generated/librosa.feature.mfcc.html . Specify preprocessing and transform settings explicitly.
- PyWORLD source/documentation: https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder . Validate resynthesis quality and use sham controls; no vocoder guarantees perceptually perfect edits.
- Montreal Forced Aligner alignment workflow: https://montreal-forced-aligner.readthedocs.io/en/v3.3.5/user_guide/workflows/alignment.html . Use only if needed, with a compatible pinned dictionary/model.
- FastAPI background-task guidance: https://fastapi.tiangolo.com/tutorial/background-tasks/ . Keep heavy processing in the bounded worker architecture described above.

Record all additional references, versions, and implementation decisions in the repository. Mathematical formulas and thresholds in this prompt are an engineering specification to implement and validate, not claims that any one paper establishes this complete system.

## 14. Definition of done

Before finishing, verify all of the following:

- [ ] Actual public-speaker reference recordings and exact-text flawed mirrors exist with documented source/reuse evidence.
- [ ] The spectrum includes near-perfect, strong, local, compound, and negative-control examples.
- [ ] Audio, transcripts, word alignment, flaw intervals, severity, provenance, split IDs, and checksums are complete and validated.
- [ ] Train/validation/test separation is by connected source/speaker/text groups; inference never reads generator labels.
- [ ] Speaker normalization removes pitch/gain offsets while preserving pitch/energy expressiveness.
- [ ] Native-time pacing and pauses remain measurable despite any alignment/visual warping.
- [ ] Every predicted event is playable and traceable to a numeric comparison, contextual rule, and correction.
- [ ] Missing/poor evidence produces uncertainty or abstention rather than false precision or perfect scores.
- [ ] Rubric weights, coverage, thresholds, and all relevant versions are explicit and reproducible.
- [ ] Independent held-out results, control false alarms, severity ordering, and failure cases are published honestly.
- [ ] The dashboard supports new audio/transcript uploads and genuine processing, not only canned outputs.
- [ ] A clean environment can reproduce the demo and evaluation using documented commands.
- [ ] The GitHub repository, required accessible dataset, functional dashboard, ≤6-page report, and 3–10 minute YouTube video are all present, or each missing item is explicitly marked blocked.

**Now implement the system and complete the deliverables. Start by inspecting the environment, creating the requirements matrix, and proving the one-pair vertical slice. Continue through the phases; do not stop after giving a plan.**
