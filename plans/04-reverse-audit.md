# Reverse Audit Plan

## Purpose

This plan governs a separate validation pass over `federal_1040_2025.json`.

Unlike the modeling workflow, this workflow does not build or repair the master JSON. It treats the JSON as the object being audited and checks whether the modeled cells, lines, boxes, worksheets, and flows appear to match the primary IRS sources.

The objective is to produce an independent errata record:

- identify likely mistakes
- identify ambiguous or weakly supported modeling choices
- identify cells that appear incomplete, unsupported, or suspicious
- record why the concern exists and which source created that concern
- avoid editing the master JSON during the audit

## Primary artifacts

- `federal_1040_2025.json`
- `docs/federal_1040_2025.template.json`
- IRS form PDFs in `forms-instructions-and-publications/forms/`
- IRS instruction PDFs in `forms-instructions-and-publications/instructions/`
- IRS publication PDFs in `forms-instructions-and-publications/publications/`
- instruction summaries in `forms-instructions-and-publications/instruction-summaries/`
- publication summaries in `forms-instructions-and-publications/publication-summaries/`
- `docs/problematic_forms_and_lines.txt`
- a separate reverse-audit findings document such as `docs/REVERSE_AUDIT_ERRATA.md`

## Independence rule

- treat `federal_1040_2025.json` as the thing being checked, not the thing to trust
- do not "confirm" a JSON rule merely because it is internally consistent with nearby JSON cells
- do not use the master JSON as authority for IRS meaning
- use summaries as navigation aids and memory aids, not as the final authority when making a finding
- when the summaries and the primary sources appear to differ, defer to the primary sources and note the discrepancy

## Source priority

When checking whether a cell or box is modeled correctly, use sources in this order:

1. the IRS form or schedule itself, for what the line/box asks for and where the amount lands
2. the official IRS instructions for how the line/box is computed, limited, sourced, allocated, or triggered
3. relevant IRS publications when the rule is publication-driven, interpretive, or worksheet-based
4. project summaries only to accelerate navigation or highlight likely areas to inspect

## Scope

The reverse audit should step through the master JSON and evaluate, as applicable:

- top-level forms and worksheets
- form metadata that affects filing, activation, or display
- individual cells
- repeating block item fields
- computed carryouts between cells, forms, and worksheets
- questionnaire triggers when they claim to stand in for filing or visibility logic
- PDF-facing cells only to the extent needed to confirm that the underlying tax meaning is correct

The audit is about tax meaning and support first, not cosmetic naming issues.

## What to check

For each relevant line, box, worksheet field, or computed cell, check questions such as:

- does the JSON cell represent the same concept the IRS source is asking for
- is the upstream source of the value correct
- is the downstream carryout destination correct
- is the equation directionally correct even if still incomplete
- is the line actually a list/row structure rather than a single scalar cell
- is the form or worksheet activated under the right conditions
- is the line controlled by instructions or publications that the current JSON appears to ignore
- is the rule inherently ambiguous enough that the JSON should document the limitation more clearly

## Finding classes

Every finding should be classified. Use categories such as:

- `error`
- `likely error`
- `ambiguous`
- `missing support`
- `needs judgment`

If a finding is weak or speculative, say so explicitly rather than overstating certainty.

## Required content for each finding

Each reverse-audit finding should record:

- form id
- cell id or block field id
- IRS line / box / worksheet reference when known
- current JSON behavior or current modeled meaning
- the current JSON line, equation, field definition, activation rule, explanation text, or other specific model entry that is being challenged
- why it appears wrong, incomplete, ambiguous, or unsupported
- primary source citation(s) used for the concern
- confidence level
- suggested follow-up

The suggested follow-up may recommend modeling work, clarification, more research, or a targeted test. It must not silently patch the JSON as part of the audit pass.

Each finding should also include a concrete suggested fix path, such as:

- a revised equation shape
- a structural change to cells or blocks
- a new helper worksheet
- a new source fact or block field
- a narrower explanation or activation rule

The suggested fix is a recommendation only. The reverse audit still does not edit the JSON.

## Output format

Write findings to a separate errata document, not into `federal_1040_2025.json`.

Preferred output structure for `docs/REVERSE_AUDIT_ERRATA.md`:

- one section per form or worksheet under review
- one finding entry per challenged cell / line / box / block field
- concise explanation first, then supporting source notes
- clearly separate confirmed issues from lower-confidence ambiguities
- include, for each finding, the current JSON line or expression and a suggested fix path so the errata can double as an implementation queue without becoming a stealth modeling pass

Also keep `docs/problematic_forms_and_lines.txt` in mind as an existing quick-reference artifact, but the reverse-audit findings document should be the richer narrative record.

## Workflow

### Step 1: Pick the audit slice

- choose a form, worksheet, or closely related dependency cluster
- avoid trying to audit the full return blindly in one pass
- prefer natural clusters such as one form plus its governing worksheet and downstream carryouts

### Step 2: Read the modeled slice

- inspect the relevant `_meta`, `cells`, `blocks`, equations, activation rules, and explanations in `federal_1040_2025.json`
- note what the JSON is claiming before consulting the IRS sources in detail
- identify which cells are manual facts, computed amounts, triggers, or carryouts

### Step 3: Re-check against primary sources

- read the form PDF to confirm line/box structure
- read the instructions for the lines being audited
- read publications when the instructions defer to publication-driven classification or allocation rules
- use summaries only to navigate more quickly, not as the final proof

### Step 4: Compare claim versus source

- decide whether the current JSON entry appears supported, unsupported, wrong, incomplete, or genuinely ambiguous
- note whether the issue is structural, computational, activation-related, or documentation-related
- prefer small precise findings over vague "this form seems shaky" comments

### Step 5: Write findings without editing

- record the finding in the separate errata document
- do not edit the JSON in the reverse-audit pass
- do not fold the finding directly into a fix unless a separate implementation task is explicitly opened later

### Step 6: Identify follow-up work

- mark whether the issue likely needs JSON modeling work, more source research, test coverage, or a plan update
- if the issue affects multiple forms, note that broader impact explicitly

## Guardrails

- do not let the audit devolve into a stealth modeling pass
- do not "fix as you go"
- do not rely on project memory when the primary source is available
- do not collapse multiple distinct issues into one vague finding
- do not overstate certainty when the IRS source itself is unclear

## Done means

- the audited slice has been checked against the relevant primary sources
- findings are written in a separate errata document
- each finding explains why the JSON entry is suspect
- no JSON edits were made as part of the audit pass
- follow-up work is clear enough that a later implementation pass can act on it deliberately

## Common failure modes

- treating summaries as authority instead of as navigation aids
- allowing the current JSON structure to frame the audit too narrowly
- silently correcting the model instead of documenting the issue first
- writing findings that say something is wrong without naming the exact cell or line
- mixing confirmed issues and low-confidence speculation without labeling them clearly
