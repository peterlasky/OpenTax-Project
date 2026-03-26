# Master JSON Model Plan

## Purpose

This plan governs the buildout and hardening of `federal_1040_2025.json`, which is the project's master federal 2025 dependency graph.

The objective is not just to add forms. The objective is to make taxpayer facts flow upward correctly through blocks, worksheets, schedules, and forms so the model becomes increasingly reliable as an executable tax package.

## Primary artifacts

- `federal_1040_2025.json`
- `filing_sequence.json`
- `docs/federal_1040_2025.template.json`
- `docs/FORM_MODEL_STATUS.md`
- `problematic_forms_and_lines.txt`
- `tests/test_tax_logic.py`
- `forms-instructions-and-publications/pdf_form_scan.json`
- `reference-data/federal/2025/pdf_field_maps/`
- `forms-instructions-and-publications/instruction-summaries/`
- `forms-instructions-and-publications/publication-summaries/`

## Template-first rule

- When `docs/federal_1040_2025.template.json` exists, treat it as the schema reference for the master model and defer to it for structure and field expectations.
- Use the template to preserve the current top-level layout, form object shape, cell contract, block contract, and comment/documentation conventions.
- Do not invent a parallel schema if the template already answers the question.

If the template does not exist yet, use this rudimentary format until it is created:

- top level: metadata keys plus a jurisdiction root such as `Federal 2025`
- jurisdiction root: optional `_filing_sequence_index` plus top-level forms and worksheets
- each form: `_meta`, `cells`, and optional `blocks`
- each cell: `format`, `default`, `value`, `manual_entry`, `override_possible`, `description`, `explanation`, `order`, `required_rule`, and `equation` when computed
- each block: repeating-entry metadata plus `item_cells` and `entries`

## Core principles
- Build from source facts upward, not from top-line outputs backward.
- Preserve the distinction between user-entered facts and computed results.
- Prefer explicit data flow over hidden assumptions.
- Do not ask the user to enter the same fact twice if it can flow from a lower-rank source.
- Keep worksheets explicit when the instructions or publications make them real dependency carriers.
- Keep the JSON model and the GUI aligned. They are one system, not separate products.
- Use overrides sparingly and intentionally. A manual bucket is not a substitute for understanding the dependency graph.
- When a rule is publication-driven, model it from the publication as well as the form instructions.

## Build order

### Phase 1: Intake and source blocks

- strengthen source blocks under the owning form
- preserve block-based intake for W-2, 1099, 1098, K-1, K-3, and similar payer-furnished documents
- normalize source detail before trying to solve downstream carryouts

### Phase 2: Core return and core worksheets

- maintain `f1040_Federal_Info_Worksheet` as the intake root
- keep `f1040` and its immediate worksheets dependable
- make sure line-level dependencies are explicit and traceable

### Phase 3: Core schedules and common follow-on forms

- build in dependency order rather than convenience order
- prioritize forms that materially affect the return bottom line
- move a form from scaffolded to modeled only when major branches and downstream carryouts are genuinely reliable

### Phase 4: Tax-sensitive specialty areas

- focus on high-risk forms where thin scaffolds can materially misstate tax
- examples include international, AMT, estimated-tax penalties, NIIT, retirement/additional-tax regimes, passive-loss and basis limitations, and publication-driven investment logic

## Modeling rules

### Forms and metadata

- every top-level form or worksheet must have stable `_meta.name`, `_meta.active`, `_meta.rank`, and `_meta.filing_sequence`
- when a modeled sheet corresponds to a real PDF artifact, `_meta` should also carry explicit PDF metadata such as `fillable_form`, `pdf_source_path`, and `pdf_field_count`
- keep only high-level PDF metadata in the master JSON; widget-to-cell mapping belongs in the separate `reference-data/federal/2025/pdf_field_maps/` layer
- keep rank ordering coherent because it drives both evaluation and display order
- use `filing_sequence.json` as the authoritative catalog for IRS attachment sequence numbers
- store `filing_sequence` as either an IRS sequence string such as `07` or `19C`, or `null` when the form is not a sequenced attachment

### Cells

- each cell should have `format`, `default`, `value`, `manual_entry`, `override_possible`, `description`, `explanation`, `order`, and `required_rule`
- computed cells should have equations unless the current gap is explicitly manual
- use explanations to document non-obvious IRS meaning, upstream sources, or partial-model status

### Blocks

- repeating source sections belong in `blocks` on the owning form
- item schemas should be complete enough to preserve the original payer-furnished fact pattern
- add nested repeating structures only when the source form genuinely requires them
- when a block corresponds to a real source-document PDF, store explicit block metadata such as `fillable_form`, `pdf_source_path`, and `pdf_field_count` so preview routing does not rely on filename heuristics alone

### Filing logic

- use filing sequence metadata and form-visibility logic carefully
- a form should not auto-file just because a user touched a field unless that behavior is intentional
- distinguish between sequenced attachments and non-sequenced helpers, worksheets, vouchers, and recordkeeping forms

### PDF mapping boundary

- `pdf_form_scan.json` is the audit layer that tells the project which local PDFs are fillable and how many fields they expose
- `pdf_field_maps/` is the intermediate PDF widget layer; it may contain raw widget catalogs, hand-authored mappings, and safe heuristically generated mappings
- preview mappings should be expressed as separate `source` expressions in the field-map files, not as ad hoc PDF widget ids embedded in `federal_1040_2025.json`
- if a form is only partially modeled, keep the tax logic correct first and let the PDF layer remain partially mapped rather than inventing fake cells just to satisfy a PDF
- when adding or renaming cells that drive a mapped PDF, verify whether any `pdf_field_maps/` entries need corresponding updates

## Required companion updates

When the master model changes materially, update the related audit artifacts in the same work:

- `docs/FORM_MODEL_STATUS.md`
- `problematic_forms_and_lines.txt`
- relevant tests in `tests/test_tax_logic.py`
- relevant `pdf_field_maps/` generation or mapping artifacts when PDF-driving cells or form metadata changed
- relevant summary or audit notes if the new logic depends on instruction/publication analysis

## Task checklist

- add missing dependency carriers before relying on manual top-line placeholders
- replace manual compatibility cells with real upstream flows when possible
- keep equations idempotent and avoid duplicate carryout terms
- validate same-form and cross-form references carefully
- add regression tests for every nontrivial dependency batch
- re-check filed-form behavior when changing filing triggers or major carryouts
- prefer explicit helper cells over opaque giant equations when that improves reliability
- keep the master model and the separate PDF layer aligned without collapsing them into one file

## Done means

- taxpayer-entered facts flow from source blocks into the correct downstream lines
- the form's major branches are modeled rather than hidden behind vague manual buckets
- filing visibility and carryouts are coherent
- PDF metadata points to the right local artifacts without embedding widget-level preview logic in the master JSON
- tests cover the new logic
- status and audit docs reflect the new reality of the model

## Common failure modes

- adding a scaffold without wiring the downstream dependency it was meant to satisfy
- solving a top-level line while ignoring the worksheet or publication that actually controls it
- duplicating data entry instead of flowing lower-level facts upward
- pushing PDF widget-mapping details into the master JSON instead of keeping them in the separate field-map layer
- leaving stale status docs after a modeling upgrade
- relying on manual adjustment cells too long in tax-sensitive forms
