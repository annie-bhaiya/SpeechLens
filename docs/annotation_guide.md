# Annotation guide v1

Annotators must be consenting humans who listen independently. Machine boundary estimates and generator supports are aids, never independent ground truth. No independent reviews have occurred in this release.

1. Listen to the unmodified reference and an acceptable alternative if available. Check intended words, repetitions, missing words, overlap and channel quality.
2. Blind the variant filename, generation settings, severity and system prediction. Label each rendition before seeing the other annotator's decisions.
3. Label pace, intonation, pause placement, emphasis/energy and human under-articulation separately. Label low-pass, noise and clipping as recording degradation. Do not infer emotions, ability or personal traits.
4. Levels: 0 accepted alternative; 1 subtle; 2 mild; 3 strong; 4 egregious. Use a contextual listening judgment, not parameter thresholds. Mark ambiguous alternatives as ambiguous rather than forcing a flaw.
5. Phrase-level statistics receive phrase-level intervals. Mark the first audible affected word and the end of the last affected word. Pause intervals run from the prior word offset to the next onset. Note onset/offset uncertainty, trailing breaths and fades. Permit overlapping categories.
6. Review every subtle variant, edit boundary and non-edited span for resynthesis artifacts. Reject transformations that remove consonants or change intended words. Keep a rejection reason.
7. Independently correct intended display text, then inspect waveform and acoustic word boundaries. Null missing words; do not interpolate absent speech into timestamps.
8. Adjudicate after both independent files are saved. Preserve originals. Report mean/median/P90 boundary disagreement and ordinal agreement with denominators. Human scores require per-category ratings and reviewer IDs with consent-safe pseudonyms.

Event schema: participant start/end seconds, token IDs, type, severity 0-4, label kind (perceptual or transformation support), uncertainty, reviewer IDs, independent/adjudicated status, ambiguity notes. A deleted pause has no target support duration; annotate the audible boundary context separately. Current files contain machine transformation supports with `perceptual_interval_s: null` and `reviewers: []`.
