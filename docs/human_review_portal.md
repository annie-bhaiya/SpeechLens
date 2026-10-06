# Human review and collection portal

Open **http://127.0.0.1:8000/review** after starting SpeechLens. The analysis sidebar also links to it. This workflow is designed for trusted people using this computer. The portal has pseudonymous accounts and role checks; the rest of the research app remains a local prototype. Do not expose the server publicly as a multi-user recruitment site.

## What is still needed from people

The portal supplies the forms, listening tools, validation and files. It does not supply human judgment. The current 346 public-source recordings still await human acceptance, and independent perceptual intervals/ratings remain unmeasured. No actual human performances have been collected yet. Automated test accounts and fake-device recordings use a separate `tmp/review-e2e` store and never count toward these gates.

People need to complete three jobs:

1. **Recording acceptance QA:** listen to the whole reference and rendition; check words/repetitions/omissions, single-speaker/channel quality, edited boundaries and untouched spans. Accept, reject or flag ambiguity. Give a rationale for an accepted public baseline.
2. **Full independent annotation:** additionally correct intended text, check every native-time word boundary (or explicitly mark an absent word), mark audible flaws with category/severity/uncertainty, rate the six categories and finalize the checklist. Two distinct people independently annotate the same representative tasks, especially held-out audio, subtle variants and edited boundaries.
3. **Real performances:** consenting adults read selected existing texts exactly. Collect acceptable alternatives plus subtle and strong versions from varied speakers. Include actual under-articulation if vocal clarity is to be evaluated; noise/codec/channel damage is a separate category.

The organizer brief does not prescribe a fixed human sample count or two-reviewer protocol. These are the project's evidence-quality targets. Larger independent speaker/source coverage is needed for stronger generalization claims. A portal alone does not establish them.

## Reviewer: step by step

- Create a pseudonymous reviewer ID and a passphrase of at least ten characters. Keep the passphrase to return to drafts. Do not share accounts. Consent to storage of your review.
- Open **Review & annotate**. Use **Assigned to me** if the coordinator assigned a set, or choose a listening task. Task numbers persist in the local database. Do not open Dataset explorer or system findings during independent work: those contain generator information that is deliberately hidden in this portal.
- In **Listen & decide**, play both complete recordings, select recording acceptance QA or full annotation, record the decision and listening notes. A stylistic difference from the reference is not automatically a flaw.
- In **Text & word times**, correct intended text and click **Apply corrected text / rebuild tokens** if words change. This clears old times and affected event token IDs. Public tasks begin with unreviewed machine boundaries; human recordings begin with empty times. Set start/end seconds or capture **Now** from the rendition player. Mark absent words **Missing** instead of inventing timestamps. Check **Reviewed** for each inspected word. Use pagination and, on narrow screens, scroll the boundary table horizontally.
- In **Audible flaws**, seek with the waveform or slider, capture native start/end, replay the interval, choose type and severity 1–4, note boundary uncertainty and audible evidence, and optionally list affected token IDs. Add each event. Overlapping categories are allowed. Rate all six whole-recording categories: 0 acceptable, 1 subtle, 2 mild, 3 strong, 4 egregious; null means cannot assess and needs an explanation.
- In **Check & submit**, confirm the actual listening work. No events requires an explicit no-flaws confirmation; that confirmation cannot coexist with events. **Save draft** works before completion. **Finalize independent review** validates and preserves the original file unchanged.
- If you completed acceptance-only QA, **Add full annotation** creates supplementary work and preserves the accepted QA original when saved. A finalized full annotation is immutable; resolve subsequent disagreements in adjudication.
- **Export files** downloads your saved draft/final review records and separate word-alignment/event JSON. Submitted and draft status remain explicit.

## Coordinator: assign, compare and adjudicate

On first initialization the app creates a random private coordinator code at:

`storage/human_review/coordinator-key.txt`

For a configured storage root, use `<SPEECHLENS_STORAGE>/human_review/coordinator-key.txt`. In Docker, it is `/app/storage/human_review/coordinator-key.txt` in the persistent upload volume. Read it locally, for example `Get-Content storage/human_review/coordinator-key.txt`; never commit or publish it. Sign in with a separate coordinator identity and that code.

Ask reviewers to create their own accounts first. In **Adjudication**, choose a queue view (baselines, held-out test, subtle, all or work in progress), select tasks, enter reviewer IDs and assign the same **full independent annotation** set to two people. Acceptance QA can be assigned separately. Assignment contains no generator/severity details in the reviewer workspace.

The coordinator's queue deliberately includes recording identities/split information for planning; it must not be shown to independent annotators before they finalize. Reviewer IDs do not prove that two humans are distinct: the coordinator must establish this outside the account mechanism.

After two full annotations are submitted, **Compare & resolve** opens. Inspect both original event intervals, word boundaries, category ratings and notes. The resolved editor starts from the first original; change it to the agreed final result, document disagreements/resolution, confirm actual reviewer independence and finalize. A coordinator cannot adjudicate their own selected reviewer identity. Original hashes and reviewer IDs remain attached to the resolved file. Acceptance-only submissions do not unlock this gate.

Human boundary agreement, ordinal agreement, prediction-versus-human accuracy and human generalization must be computed from real completed exports. The current proxy benchmark remains frozen; portal test fixtures are not added to it.

## Contributor: real human performances

Open **Real performances**, choose an existing reference, read/download its exact intended text, and use a stable speaker pseudonym. Use a quiet room, one speaker, a steady microphone distance and original audio without added processing.

Choose acceptable/subtle/strong intent and a focus category, then record via the microphone or upload an original WAV/FLAC/OGG/MP3/M4A/MP4/WebM. Microphone permission is requested only when recording starts. The recording stops at ten minutes; uploads are bounded at 100 MB and 1–600 seconds. Listen back before submitting. An intended flaw label is collection metadata, not a human perceptual verdict.

Required attestations cover voluntary adult participation, authorization to submit, private local research use and listening back with the intended text. Public redistribution and derivative permission are separate optional choices. A private-only contribution remains private. Consent is a versioned timestamped attestation; verify any additional institutional or organizer consent requirements before release.

The server validates decoding, preserves original and canonical audio/hashes, checks canonical text identity and keeps the speaker in the reference's split. A speaker cannot contribute across conflicting splits. New human tasks appear in the listening queue with empty word times, awaiting actual review. **Withdraw** removes local audio plus linked assignments, reviews and adjudication; downloaded copies must be handled separately.

## Storage and exported files

- `storage/human_review/reviews.sqlite`: WAL database for pseudonymous identities, expiring session hashes, opaque task mapping, assignments, drafts, independent originals and adjudication. Passphrases use salted PBKDF2; tokens and coordinator code are private.
- `storage/human_review/performances/<opaque-task-id>/original.*` and `canonical.wav`: private contributor audio.
- ZIP `independent/<task-id>/<reviewer>.json`: complete saved review, including status, revision and provenance.
- ZIP `acceptance_originals/...`: preserved finalized QA when later supplemented.
- ZIP `alignments/independent/...` and `events/independent/...`: separate word/event annotation files. Draft/unreviewed estimates remain labeled accordingly.
- Coordinator-only ZIP `adjudicated/...`, corresponding `alignments/adjudicated/...` and `events/adjudicated/...`, and `private_task_mapping.json` linking opaque IDs to recording identities.
- `human_performances.jsonl`: contributor metadata/consent/hashes. Original human audio is intentionally not bundled by the generic review export; it remains in private storage. Release eligibility stays false until a coordinator performs consent, transcript, annotation, split and quality checks.

Neither export nor upload automatically alters `data/`, inference or the published proxy measurements. Back up private storage deliberately. Do not put it in Git or a public dataset without the relevant permission and release QA. Dataset and YouTube publication are deferred by the user's current instruction.

## Verified behavior

`evaluation/review_portal_e2e.json` records actual browser tests of draft/final validation, account isolation, native seeking/replay, two-review adjudication, task assignment, alignment/event export, fake-device microphone capture/decoding, private submission, withdrawal and desktop/mobile layout. `tests/integration/test_review_portal.py` verifies API boundaries and private storage invariants with isolated signal fixtures. These checks demonstrate software behavior, not actual human listening or consent.

For developer E2E, start a **separate isolated backend** with `SPEECHLENS_STORAGE=E:\multimodal\tmp\review-e2e`, start `npm --prefix frontend run dev -- --port 5173`, then run `.venv\Scripts\python -m scripts.review_portal_e2e`. The script refuses a server whose storage is not the specified temporary fixture directory. Stop that server and restart with the normal storage root for people.
