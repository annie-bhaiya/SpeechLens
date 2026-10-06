# Delivery rubric v1

Four YAML product presets: Interpretive Reading, Declamation, Extemporaneous, Persuasive Oratory. None has human validation yet. The public-address corpus offers primarily prepared oratory, not extemporaneous or interpretive-reading genre coverage. These delivery weights are distinct from organizer judging weights.

Default weights: pacing .25, pauses .20, intonation .25, emphasis/energy .20, clarity .10. Clarity requires independently validated intelligibility evidence; it is null/diagnostic-only here, so included weights are renormalized. ASR error and low-pass filtering never become vocal-articulation penalties.

Phrase units have fixed reference elapsed exposure. Pause boundaries have equal exposure. In each category, combine duplicate evidence for a unit by maximum severity. Category penalty = sum eligible exposure * severity / sum eligible exposure; score = 100(1-penalty). Unsupported units are removed from both numerator and denominator. Coverage is eligible exposure divided by available exposure. No eligible denominator yields null. Weighted scoring coverage excludes the diagnostic clarity weight; below .60, total is withheld.

Pace detects either sign of log native-duration ratio. Pitch/energy detect deficient Q90-Q10 range only when the reference has enough range. Boundary pauses need at least .65 non-speech fraction on the longer gap. Reference quality, aligned word coverage, phrase length and voiced support gate results. Severe ASR/intended mismatch and substantial clipping withhold scoring. No calibrated peak-severity boost or fitted learned model is used.

Scores measure consistency with a supplied delivery example under engineering tolerances. Comparing a recording to itself may score 100 but does not prove that reference is an effective speech. Large pauses can dilute an equally weighted boundary penalty; this is disclosed rather than cosmetically rescaled. Separate category penalties in a compound total do not imply independent causes.

Every event includes actual participant/reference clocks, stable token IDs, quote, observed/reference values, units, signed delta, formula, thresholds, version, confidence rationale and rehearsal direction. Advice follows validated numeric evidence through structured templates; no paid or optional LLM participates in scoring.
