# Model coverage statement (Federal 2025)

This project reconstructs Form 1040 and related schedules as **structured, executable JSON** plus a reference evaluator. It is **not** a guarantee of IRS-complete tax outcomes for every taxpayer.

## What “done” means here

- **Wiring:** Lines reference sources (worksheets, schedules, blocks) with explicit equations where automated.
- **Known gaps:** Documented in `plan.md`, `problematic_forms_and_lines.txt`, and form cell explanations.
- **Form status tracking:** Every YAML-listed form or schedule should have an explicit status in `docs/FORM_MODEL_STATUS.md`.
- **Nonresident / edge returns:** Use **Federal Information Worksheet** flags and **manual** cells when the automated path does not apply (e.g. Form 1040–NR limitation lines, Form 2210 deferral).

## Recent target areas (not full IRC parity)

| Area | Behavior |
|------|----------|
| **Form 1116 lines 4a–4b** | Default: Schedule A mortgage (8e) and investment interest (9) × line 3f, plus manual buckets. |
| **Form 1116 lines 18–20** | Form 1040: taxable income `f1040.15` and tax stack `f1040.16 + f1040.17`. Form 1040–NR: manual amounts when worksheet flag is set. QD/capital-gain limitation worksheets from instructions may still require overrides. |
| **Form 4952 line 4a** | Optional inclusion of passive **1099-MISC box 2** royalties via worksheet flag (Pub. 550 classification remains taxpayer responsibility). |
| **Form 2210 line 19** | Automated helper only when not deferred, no waiver boxes A/B, and safe-harbor exception not met. |

## Completing a real filing

Use IRS forms, instructions, and publications as the **authority**. This model is a **decision-support and linkage graph**, not a substitute for professional advice or IRS software certification.
