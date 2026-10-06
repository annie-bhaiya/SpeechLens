# Architecture

One FastAPI application serves the built React app and schema-validated API. SQLite persists opaque jobs; a supervisor runs one bounded CPU inference subprocess at a time. Heavy inference never runs in the async upload handler. Every subprocess has a 900-second limit. Interrupted jobs recover once automatically; failures permit explicit retry.

The worker preserves original uploads, writes mono 16 kHz floating canonical WAVs, aligns reference and participant independently, extracts full native-clock features, matches stable token/phrase IDs, applies deterministic rules and validates evidence JSON. Original quality measurements precede normalization. User confirmation supplies the single-speaker scope; diarization is unavailable.

Modules: `ingest`, `text`, `alignment`, `features`, `comparison`, `detectors`, `scoring`, `explanations`, `pipeline`. Deterministic SHA-256 keys include source audio, canonical transcript, all pipeline/detector/rubric settings and a source-code fingerprint. Public research caches live in `.cache`. Private job caches live inside the job folder and are deleted with uploads. Model cache holds only public weights.

Public schemas use seconds. Spectral frames use 400 samples, hop 160, FFT 512, uncentered periodic Hann windows. pYIN uses 1024 samples and the same hop with center=False. Frame timestamp = (frame_start + window_length/2)/16000. Frontend pitch gaps remain missing; token coordinate plots omit inter-word pauses and are explicitly labeled. Pauses and pace are always scored on native clocks.

Routes: POST /api/evaluations multipart participant, transcript, optional reference ID or uploaded reference+reference_text, preset, weights JSON, en language and single_speaker confirmation. GET job/status/result/audio/export, POST retry/rescore, DELETE job. GET /api/references, /api/rubrics, /api/dataset; POST /api/demo uses the actual pipeline with cache disabled. JSON and ZIP(JSON+CSV) exports are documented in the OpenAPI page at /docs.

Analysis uploads are private to the trusted local instance, but its analysis API has no authentication: bind loopback only. SQLite metadata and job folders use the configured persistent volume. Delete removes originals, canonical audio, derived output, logs and private cache. Explicit dataset scripts never incorporate user uploads.

## Human-work portal

`/review` serves a separate React entry over `/api/review`. A private WAL SQLite database under the selected storage root records salted passphrase hashes, expiring session-token hashes, reviewer/coordinator roles, opaque task mappings, assignments, optimistic draft revisions, immutable independent submissions, preserved acceptance originals and separate adjudication. The coordinator code is generated privately on initialization. Independent reviewers see intended text/audio and unreviewed timing estimates, without source filenames, split, generator levels, supports or system predictions. Coordinators can inspect planning metadata and compare submitted full annotations.

Original and canonical contributor audio remain in private storage. Decoding is bounded and offloaded; versioned consent/read-back attestations, canonical transcript identity and stable-speaker split constraints gate collection. Withdrawal removes audio and linked task/review/assignment/adjudication records. ZIP exports separate alignment/event JSON and retain explicit draft/independent/adjudicated provenance; they do not promote files into `data/` or change inference. The human pipeline remains manual and requires real distinct people; fixture identities/audio stay isolated under `tmp/`. See `docs/human_review_portal.md` for operation and limitations.
