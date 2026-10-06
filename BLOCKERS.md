# Remaining work and required inputs

The supplied `Track C.pdf` has been read and checked against the implementation. Its five deliverables and judging weights are recorded in `docs/organizer_requirements_review.md`. Linux Docker is verified in `evaluation/docker_check.json`. The user supplied the Git remote and authorized a terminal push; `evaluation/git_push.json` records the outcome. These are no longer missing-input blockers.

| Remaining work | Data/files or people needed | Where to do it |
| --- | --- | --- |
| Human acceptance of the 346 provisional recordings, including 13 baselines | Actual listening decisions, corrected text, quality/boundary checks and baseline rationale | `/review`, recording acceptance QA; assignment supported |
| Independent word/event annotation and adjudication | Two distinct people independently inspect representative held-out/subtle/edited tasks; native word start/end or explicit missing words, audible event intervals, severity, uncertainty, six category ratings and resolution notes | `/review`, full annotation, then coordinator adjudication; export separate alignment/event JSON and preserved originals |
| Real human performances and generalization evidence | Consenting adult speakers read existing exact texts: acceptable alternatives and subtle/strong renditions; original audio, stable pseudonyms, recording conditions and explicit consent. Human under-articulation is needed for vocal-clarity claims | `/review`, Real performances; private collection, read-back confirmation, split checks and withdrawal |
| Evaluate completed human labels | Actual exported independent/adjudicated annotation files and consented, accepted human audio; record agreement and accuracy with denominators | Follow `docs/human_review_portal.md`; automated fixture exports do not qualify |
| Failed localization target and noise/pitch robustness | Training/validation human evidence for calibration; robust detector/alignment changes and an honest held-out rerun | Existing failure cases and metrics remain frozen until a separate measured improvement |
| Some reference excerpts are below the project's 30–60 second target | Longer licensed same-text excerpts and transcript/rights/provenance, or an explicitly documented scope decision | Existing references include 19–27 second excerpts. This duration target comes from the implementation project, not the organizer PDF |
| Dataset publishing | Deferred by user; any future release needs accepted labels, rights/consent checks and chosen hosting | Initial remote already contains `data/`; this extension changes no dataset files or archive |
| YouTube demo | Deferred by user; future upload needs the publishing account and resulting public URL | Existing local 7:29 video remains unchanged |

The organizer PDF does not mandate a fixed human sample count, two annotators, a 0.75 F1 threshold, Docker or 30–60 second excerpts. Those are project evidence/validation targets, kept explicit rather than attributed to the organizer.

The portal removes the missing-tooling block. It cannot replace distinct humans, listening judgments or consent. Production review/contribution storage contains no automated human evidence; integration/browser fixtures are isolated. No human accuracy, inter-rater agreement or human generalization is claimed.

Frozen held-out synthetic-support macro F1 is **0.436** at tIoU 0.5, below the unchanged **0.75** project target. Held-out additive noise has **0/8** support matches. A +2 semitone copy caused ASR/alignment abstention. Median defined severity Spearman is **0.949**, but only **39/52** groups have defined correlations. The portal and Docker verification do not resolve those scientific limitations.

Host ffprobe remains absent; video inspection uses the packaged FFmpeg metadata fallback. This is a tooling limitation, not a missing organizer deliverable. No credentials are recorded here.
