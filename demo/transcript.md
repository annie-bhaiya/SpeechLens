# Actual walkthrough captions

00:00:00.163 - SpeechLens | same words, measured delivery
An actual local dashboard walkthrough. Experimental thresholds; human perceptual validation remains pending.

00:00:25.072 - Data provenance and review
Public speeches carry source, transcript and rights evidence. Generator supports are separate from perceptual labels; no independent human annotation is claimed.

00:00:55.335 - One transcript, levels zero to four
The explorer shows measured scores when evaluation is available. Levels describe injected edits, not independently rated performance.

00:01:20.122 - Subtle intervention
Listen to a near-perfect local pacing variant. Small accepted differences should not automatically trigger a penalty.

00:01:41.040 - Strong intervention
The strong local edit preserves intended words and pitch while changing native phrase duration. Its time map records the actual rendered sample count.

00:02:05.283 - Real upload and live CPU inference
The next result is computed from uploaded audio. The wait is shown in real time; no canned prediction or edited latency claim.

00:03:15.236 - Scores include evidence coverage
Clarity is diagnostic-only. Missing alignment or voicing evidence produces abstention; a high total can still hide a short serious defect.

00:03:40.347 - Native time and normalized voice
Reference and participant retain separate clocks. Relative semitones and dB remove constant voice/gain offsets while preserving expressive range.

00:04:08.858 - A playable, mathematically grounded finding
Participant 78.26 versus reference 125.87 words/minute. Duration ratio 1.608. Advice follows this evidence.

00:04:39.386 - Rubrics and reproducible exports
Preset weights are product choices, distinct from judging weights. Re-scoring reuses acoustic evidence and persists the selected rubric into the export.

00:05:05.904 - Acceptable gain control and stress limits
Non-clipping plus/minus 6 dB copies changed the fixture score by zero points. Pitch-shift resynthesis caused alignment abstention; this failed robustness condition is disclosed.

00:06:20.915 - Measured evaluation and publication status
The offline benchmark has completed. Localization uses synthetic supports, not human truth. Human agreement and generalization are unmeasured; public publication remains blocked.

00:06:49.011 - Reproduce locally
Run speechlens.ps1 setup, models, then serve. Inspect README, dataset card, six-page report, measured evaluation and blocker log. This is an upload-ready local demo, not a completed public submission.