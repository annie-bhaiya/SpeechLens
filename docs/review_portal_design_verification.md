# SpeechLens review portal: design verification

Disposition: **ship for private use on this computer**, within the automated verification limits below. This records an ordinary extension of the existing interface, not a new visual identity or a human acceptance result.

## Scope and authority

The requested surface supports recording acceptance QA, independent annotation-file creation, coordinator adjudication and consenting adults' same-text contributions. `PRODUCT.md` and `.impeccable/surfaces/human-review.md` establish that local operating context and the separation of machine supports, independent originals and adjudication. The incumbent `frontend/src/main.tsx` and `styles.css` supply the visual authority; `frontend/src/components/ReviewPortal.tsx` and `review.css` extend it.

No root `DESIGN.md` existed at intake. No durable visual-system change was approved. This verification therefore documents the implemented extension without inventing a creative north star, creating global normative tokens, writing a design sidecar or repairing unrelated surfaces.

## Inherited visual language

| Element | Observed implementation and application |
| --- | --- |
| Color | The incumbent teal action color (`--teal: #087f89`), navy (`--ink: #142235`), cool page background (`#f5f7f9`) and body ink (`#243144`) carry into the portal. White containers and pale teal selection/notice fills distinguish work regions. The portal uses its own descriptive gray (`#536477`) and borders (`#dbe3ea`, fields `#bac8d3`) within that palette. |
| Type | DM Sans remains the body/control family; Manrope remains the heading family. Portal body text, labels and primary/secondary controls are 14px; headings are 36/23/17px on desktop, with a 29px main heading and 21px section heading on mobile. Paragraphs use 1.7 line height and a 74ch maximum. Timing columns use tabular numerals. Supporting metadata remains smaller (11–13px). |
| Forms and actions | Existing teal primary and white outlined secondary actions remain recognizable. Native text, number, select, checkbox, range, file and audio controls carry labels and completion requirements. Main fields/actions have a 44px minimum height, 6px corners and a teal 2px focus outline offset by 3px. Disabled actions have explicit muted fills. Word timing controls use 14px text and 40px minimum height. |
| Shape and depth | Flat white work containers use light borders and 12px corners; notices and fields use 6px corners. The portal relies on tonal layering rather than new shadows or decorative assets. Navigation retains teal selected states and border indicators. Color transitions are brief (150ms). |
| Layout | The desktop shell is capped at 1560px with 34px side padding. A 255px ledger accompanies the flexible editor. At 1100px, padding/gaps and the ledger narrow; at 720px, the welcome, editor, paired audio, ratings, originals and contribution columns stack. Mobile shell padding is 17px; the queue scrolls within a 180px region. Wide boundary and coordinator tables scroll inside their wrappers, preserving the page width. |

The extension increases reading and editing sizes for the human workflow while preserving the incumbent palette and forms. The existing analysis surface still contains compact 8–13px labels, controls and metadata. This is an observed pre-existing difference, not a violation of a missing normative design file; it was left untouched. Some palette values are literal declarations in both stylesheets rather than references to shared variables. Token consolidation was outside this extension.

## Finish findings and resolution

All four finish fixes are resolved in the inspected implementation and evidence:

1. **Mobile workflow note:** the paragraph wraps beside the icon, and completion status occupies its own wrapping row instead of squeezing the guidance.
2. **Mobile task filtering:** filter and search labels/fields use the full ledger width.
3. **Native-time waveform:** SVG `preserveAspectRatio="none"` makes the drawn horizontal coordinate span match the visible width. Click position maps through the element's bounding rectangle to recording duration, matching the native player clock; the range slider remains available.
4. **Word editing:** timing inputs and row buttons use 14px type and 40px height. The 660px minimum-width table scrolls inside its wrapper; pages contain up to 25 words.

The finish review supplied a single mechanical detector result of `[]`; this documentation pass did not repeat it. The ship disposition applies to the extension after those fixes.

## Evidence and limits

This documentation pass inspected both stylesheets, the waveform/table implementation, `evaluation/review_portal_e2e.json` and all ten images in `docs/screenshots/review/`: welcome, annotation, word boundaries, adjudication and performance at 1440px desktop and 390px mobile. The images show readable guidance, stacked mobile forms, contained wide tables and clearly separate independent originals and resolution editing.

The E2E artifact reports `passed: true`, no JavaScript errors and no mobile document overflow. Its passing checks cover blinded drafts and immutable final files, completion validation, native audio seek/replay, independent account isolation, two-review adjudication, coordinator assignment, separate alignment/event exports, fake-device microphone capture/private decode, consent gating and withdrawal. It also records the word-control font floor and waveform seek geometry.

These are **automated fixtures**, isolated in `tmp/review-e2e`. Fixture reviewer identities, consent confirmations, annotations, coordinator attestations and microphone audio do not establish distinct consenting humans, real listening judgments, real performances or accuracy. The screenshots explicitly label the test content. Actual human QA and real contribution collection remain to be performed. The report does not certify public deployment, public dataset release, every browser/device or a comprehensive accessibility audit.
