# Architecture

One FastAPI application serves the built React app and schema-validated API. SQLite persists opaque jobs; a supervisor runs one bounded CPU inference subprocess at a time. Heavy inference never runs in the async upload handler. Every subprocess has a 900-second limit. Interrupted jobs recover once automatically; failures permit explicit retry.

The worker preserves original uploads, writes mono 16 kHz floating canonical WAVs, aligns reference and participant independently, extracts full native-clock features, matches stable token/phrase IDs, applies deterministic rules and validates evidence JSON. Original quality measurements precede normalization. User confirmation supplies the single-speaker scope; diarization is unavailable.

Modules: `ingest`, `text`, `alignment`, `features`, `comparison`, `detectors`, `scoring`, `explanations`, `pipeline`. Deterministic SHA-256 keys include source audio, canonical transcript, all pipeline/detector/rubric settings and a source-code fingerprint. Public research caches live in `.cache`. Private job caches live inside the job folder and are deleted with uploads. Model cache holds only public weights.

Public schemas use seconds. Spectral frames use 400 samples, hop 160, FFT 512, uncentered periodic Hann windows. pYIN uses 1024 samples and the same hop with center=False. Frame timestamp = (frame_start + window_length/2)/16000. Frontend pitch gaps remain missing; token coordinate plots omit inter-word pauses and are explicitly labeled. Pauses and pace are always scored on native clocks.

Routes: POST /api/evaluations multipart participant, transcript, optional reference ID or uploaded reference+reference_text, preset, weights JSON, en language and single_speaker confirmation. GET job/status/result/audio/export, POST retry/rescore, DELETE job. GET /api/references, /api/rubrics, /api/dataset; POST /api/demo uses the actual pipeline with cache disabled. JSON and ZIP(JSON+CSV) exports are documented in the OpenAPI page at /docs.

Uploads are private to the trusted local instance. No authentication or multi-user ownership is implemented: bind loopback only. SQLite metadata and job folders use the configured persistent volume. Delete removes originals, canonical audio, derived output, logs and private cache. Explicit dataset scripts never incorporate user uploads.
