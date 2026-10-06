# Signal processing and units

Let x be floating PCM at 16000 Hz. With L=400, H=160 and a periodic Hann window, STFT[m,k] = sum over n of x[mH+n]w[n]exp(-2 pi i kn/512). The FFT zero pads the 25 ms window; it does not create physical frequency resolution. Use 40 Slaney mel filters over 0-8000 Hz, natural-log power floored at 1e-10, orthonormal DCT-II, first 13 coefficients. Store spectral centroid, flatness and zero-crossing rate as diagnostics.

RMS[m] = sqrt(mean(x_frame^2)); dBFS = 20 log10(RMS + 1e-10). Relative energy = dBFS - median(dBFS on speech-VAD frames). This is digital level, not calibrated sound pressure. VAD is WebRTC mode 2 on independent 20 ms PCM frames. It is separate from pYIN voicing: breaths and unvoiced consonants can be speech.

pYIN searches 50-600 Hz on 64 ms frames with 10 ms hop. Unvoiced F0 is null, never zero. Pitch semitones = 12 log2(F0 / median voiced F0). Range = Q90 - Q10. A flat or weakly voiced reference cannot support a monotony finding. No per-recording standard-deviation normalization erases expression. Pitch-edge fraction is disclosed; octave errors remain a limitation.

Phrase WPM = 60 * matched intended words / native elapsed seconds. Articulation WPM uses estimated VAD-active seconds instead; the denominator is explicit. Gap = max(0, next word onset - previous offset); a candidate pause needs independent non-speech support. Punctuation is a weak context cue, not a mandatory duration.

CTC alignment uses a 2U+1 state graph with blank emissions, self/one-state transitions, and a two-state skip only for distinct nonblank symbols. Greedy ASR edit matching and likelihood thresholds gate absent/uncertain words. Canonical intended text remains separate from ASR. Chunked emissions retain native timestamps; candidate source excerpts use acoustic ASR anchors before final supplied-text alignment. Machine confidence is not an accuracy probability.

Duration residual = ln(T_participant/T_reference). Pitch/energy range ratio preserves physical semitone/dB units in explanations. Engineering tolerance maps directional residual to a clipped severity in [0,1]. No robust population sigma is estimated from one reference. Accepted training-pair calibration is unavailable and thresholds remain explicitly uncalibrated.

Maps are piecewise source/target intervals computed from actual rendered sample counts. Interior t' = a' + (target_length/source_length)(t-a). Insertions have zero source length and positive target length. Deletions have no invertible interior; propagated words touched by deletion are missing. Fades record actual sample counts. Re-alignment residuals compare two machine estimates, not human boundary accuracy.

Event `measurements.units` applies to observed/reference values. Pace `delta` is the dimensionless natural log of the duration ratio, not a words/minute difference; its formula and duration fields define it explicitly. Other range/pause/spectral deltas are participant minus reference in their stated units.
