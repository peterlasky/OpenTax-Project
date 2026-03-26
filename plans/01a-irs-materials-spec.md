# IRS Materials Specification

Tax year: `2025`

Change the tax year declaration first if this specification is reused for another filing year.

## Purpose

This document is the simple specification for what the IRS materials layer must contain and how it must be organized.

Use `01-irs-materials-and-summaries.md` for the workflow. Use this file for the target state the workflow is meant to produce or maintain.

## Required source classes

The materials layer should explicitly account for these document classes:

- forms
- instructions
- publications
- worksheets
- information returns

## Required repo locations

- forms:
  `forms-instructions-and-publications/forms/`
- instructions:
  `forms-instructions-and-publications/instructions/`
- publications:
  `forms-instructions-and-publications/publications/`
- worksheets:
  `forms-instructions-and-publications/worksheets/`
- generated worksheets:
  `forms-instructions-and-publications/generated-worksheets/`
- information returns:
  `forms-instructions-and-publications/information-returns/`
- generated information-return templates:
  `forms-instructions-and-publications/generated-information-returns/`
- instruction summaries:
  `forms-instructions-and-publications/instruction-summaries/`
- publication summaries:
  `forms-instructions-and-publications/publication-summaries/`
- tax-year manifest:
  `forms-instructions-and-publications/IRS_Federal_Individual_2025.yaml`
- publication associations:
  `reference-data/federal/2025/publication_associations.json`
- PDF fillability scan:
  `forms-instructions-and-publications/pdf_form_scan.json`
- PDF widget-map generator:
  `forms-instructions-and-publications/forms/build_pdf_field_maps.py`
- generated PDF widget maps:
  `reference-data/federal/2025/pdf_field_maps/`

## Manifest contract

The tax-year YAML manifest is the canonical inventory of the materials layer.

It should:

- exist for the target tax year
- contain the current in-scope inventory of forms, instructions, publications, worksheets, and information returns
- use stable human-readable keys
- use IRS PDF URLs as values when the source is an IRS PDF
- reflect the local document set rather than allowing undocumented local extras to accumulate

The current repo format uses top-level sections like:

- `Forms`
- `Information_returns`
- `Worksheets`
- `Instructions`
- `Publications`

## What belongs in each class

### Forms

Use for filing forms and schedules that the taxpayer or software prepares.

Examples:

- `1040`
- `1040 Schedule A`
- `1116`
- `2210`

### Instructions

Use for IRS instruction PDFs that explain how to complete forms and schedules.

Examples:

- `1040`
- `1116`
- `2555`

### Publications

Use for IRS publications that define broader tax rules, elections, worksheets, exceptions, and classification logic.

Examples:

- `Publication 17`
- `Publication 505`
- `Publication 550`
- `Publication 590-A`

### Worksheets

Use for standalone worksheet PDFs or worksheet artifacts that deserve explicit tracking apart from a form or publication.

If a worksheet only exists inside instructions or a publication and there is no separate PDF, it may still belong in the worksheet inventory conceptually even if the downloadable artifact is the instruction or publication PDF.

When the app needs a printable/fillable worksheet artifact and there is no suitable IRS fillable worksheet PDF, the repo may generate a worksheet template in `forms-instructions-and-publications/generated-worksheets/`.

### Information returns

Use for payer-furnished source documents and related source-reference forms.

Examples:

- `W-2`
- `1099-INT`
- `1099-DIV`
- `1098`
- `K-1`
- `K-3`

These are input-source references, not usually targets for instruction summaries.

When the app needs a printable/fillable preview for these source documents, it may use repo-generated linear templates instead of the original IRS information-return PDFs. Those generated templates belong in `forms-instructions-and-publications/generated-information-returns/`.

## Summary requirements

Create summaries for:

- instructions
- publications

Do not make blank-form summaries the default. The high-value summary targets are the documents that explain the rules behind the model.

### Summary locations

- instruction summaries:
  `forms-instructions-and-publications/instruction-summaries/`
- publication summaries:
  `forms-instructions-and-publications/publication-summaries/`

### Summary style

Summaries should be:

- concise
- semantically dense
- optimized for retrieval of rules and dependencies
- written to help later modeling passes understand the tax logic quickly

Each summary should try to surface:

- the purpose of the document
- major branches and elections
- worksheets
- thresholds and phaseouts
- cross-form dependencies
- edge cases or exceptions
- any facts that affect sourcing, allocation, attribution, carryovers, or filing triggers

## Downloader contract

The downloader for the materials layer is `src/downloader.py`.

It should be able to:

- read the tax-year YAML manifest
- create missing destination folders
- download documents into the correct repo locations
- skip files that already exist by default
- report failures clearly

Minimum supported operational modes:

- full download from the tax-year YAML
- missing-only download for maintenance passes

If the current implementation supports fewer categories than the manifest eventually needs, expand the downloader rather than inventing undocumented manual exceptions.

## PDF artifact contract

The materials layer must also support the later PDF preview/fill workflow through derived artifacts built from the local PDFs.

- `pdf_form_scan.json` should record whether a local PDF is fillable and how many fields it exposes
- `pdf_field_maps/` should contain one generated widget catalog per modeled fillable form
- `pdf_field_maps/` is a separate layer from the master JSON: the master model stores high-level PDF metadata, while the widget-to-source mapping lives in the generated field-map files
- retained hand-authored mappings should survive regeneration by being merged into the generated field maps rather than copied into the master JSON
- generated worksheet templates may be repo-authored artifacts rather than IRS-downloaded artifacts when the goal is a fillable worksheet preview/export path
- generated information-return templates may be repo-authored artifacts rather than IRS-downloaded artifacts when the goal is a simple fillable preview for source-document blocks

This specification intentionally keeps PDF widget mapping out of `federal_1040_2025.json` so tax logic and PDF-rendering details can evolve separately.

## Current target format

The materials layer is complete enough for project use when:

- the tax-year YAML manifest exists and matches the intended scope
- local PDFs are present for the active source set
- forms, instructions, publications, worksheets, and information returns are stored in the correct folders
- the fillability scan and generated PDF widget maps are current enough for later modeling and GUI work
- instruction and publication summaries exist in the summaries folders
- publication associations are current enough to guide later modeling work
- a model can rebuild or refresh the materials layer from the manifest plus downloader without guessing the folder structure

## Handling updates and replacements

- when a manifest entry changes, prefer updating the manifest and re-running the downloader rather than making undocumented local-only changes
- when replacing obsolete files, move the old artifact to `trash/` if you want a reversible removal
- when a URL is dead, find the correct live source and update the manifest
- when a source document has no instructions, do not force a fake instruction summary just for symmetry
