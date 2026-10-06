# Assumptions and deviations

- English, single-speaker speech; declared non-English language requests are rejected. Automatic language identification and overlap detection are not implemented reliably; user confirmation is required in the upload form.
- The full corpus contains 346 recordings from 13 excerpts, six speakers and seven original sources. Some source excerpts are shorter than the proposed 30-second minimum. All sources and perceptual labels are provisional until independent listening review.
- Host video inspection uses FFmpeg's decoded duration metadata because ffprobe is absent; the check prefers ffprobe if installed.
- Default CPU alignment uses a pinned Wav2Vec2 CTC model and supplied-text dynamic programming, the same model family used by WhisperX. Avoiding WhisperX's ASR/vocoder dependency tree is a deliberate architecture deviation. Greedy ASR edit matching gates absent words; uncertain words retain null timestamps.
- WebRTC VAD is independent of F0. It is a speech mask, not speaker diarization or a guarantee of intelligibility.
- Clarity is diagnostic-only because independently validated intelligibility labels are unavailable.
- Thresholds are conservative engineering tolerances, not population norms. Genre presets are product choices and are not all validated genres.
- No optional LLM, deep scoring model or DTW is required. Native elapsed durations always survive transcript-normalized visualization.
