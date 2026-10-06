# SpeechLens dataset card - provisional research release

## Actual release inventory

346 real mono 16 kHz WAV recordings; 13 source excerpts; 6 independent speakers; 7 source recordings. Reference duration range: 19.40-52.66 seconds. Proposed target 30-60 seconds is not met by every excerpt. Large synthetic counts do not increase independent sample size.

Family counts: {'accepted': 13, 'pace': 52, 'intonation': 52, 'pauses': 52, 'energy': 52, 'clarity_proxy': 60, 'accepted_gain': 13, 'sham_stretch': 13, 'sham_world': 13, 'compound2': 13, 'compound4': 13}. Each text has exact canonical SHA-256 identity across its mirrors. Splits are assigned before transformations and connected by speaker/source/text. Train speakers: Kennedy, Eisenhower, Nixon and Roosevelt; validation: Reagan; test: Obama. All Roosevelt sources share the same speaker split.

## Purpose and scope

Prepared English public addresses, primarily oratory. Four genre presets are configurable but not independently validated. This dataset is unsuitable for claims about overlapping voices, other languages, argument quality, personal traits or production generalization. Source excerpts are provisional delivery examples, not a unique optimal performance.

## Labels and transformations

Local pitch-preserving pacing stretches, WORLD pitch-range contraction, inserted pauses, energy-envelope flattening and low-pass recording-degradation proxies span levels 1-4. Compound edits and global-gain/stretch/WORLD identity controls are included. Additive noise at 30/20/10/0 dB SNR is held out as a generation method on the test speaker only; no thresholds are fitted on it. Seed and parameter recipes are retained. Clarity proxies are explicitly recording/channel degradation, not human under-articulation labels. Fade sample counts and monotone insertion/deletion-aware time maps are stored with supports. Each audio is acoustically realigned independently.

Current labels are transformation supports and unreviewed machine word boundaries. Perceptual intervals are null; reviewer lists are empty. Independent perceptual ground truth, human ordinal severity and two-reviewer adjudication are unavailable. All 346 recordings await human acceptance. Source text was drawn from published speech transcripts and checked by machine alignment; manual listening correction is pending.

## Provenance and rights

data/provenance includes retrieval date, original SHA-256, original file identity, source/rights page snapshot hashes, crop clocks, speaker, transcript source and separate rights evidence. Source-attested US federal/Executive Office public-domain status applies to the original official recordings/text. Pearl Harbor digitization also retains CC BY-SA 2.0 attribution. Wikimedia source-page snapshots are CC BY-SA. See docs/licenses.md. Public availability alone is not a reuse license.

## Evaluation and privacy

evaluation/metrics.json reports actual synthetic-support proxy localization, ordering and control false alarms with denominators. Human metrics are null. One held-out test speaker does not support strong uncertainty intervals. No filenames, generator parameters, levels or support labels enter inference. Private uploads never enter this dataset automatically. No consenting human mirrors were available.

## Release use

Dataset resides under data/ with audio, transcripts, alignments, events, provenance and manifests. The archive releases/speechlens-dataset.zip is a local upload-ready release. Checksums are in releases/checksums.txt. Public GitHub/Drive hosting remains blocked until authorized publication; a local archive does not satisfy the public dataset-link gate.
