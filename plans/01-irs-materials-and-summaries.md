# IRS Materials And Summaries Workflow

Tax year: `2025`

Change the tax year declaration first if this workflow is reused for another filing year.

## Purpose

This document is the step-by-step workflow for building or refreshing the IRS materials layer that feeds the project. A model should be able to follow it either:

- from a cold start, when no current manifest exists yet
- from an existing repo state, when the manifest and local PDFs already exist but need to be refreshed, corrected, or expanded

This workflow governs the authority layer only: forms, instructions, publications, worksheets, information returns, markdown summaries, and the downloader workflow that keeps those artifacts local.

It also governs the derived PDF inventory artifacts that later workstreams depend on:

- `forms-instructions-and-publications/pdf_form_scan.json` as the fillability and field-count audit
- `reference-data/federal/2025/pdf_field_maps/` as the separate per-form widget catalog and mapping layer derived from local PDFs
- `forms-instructions-and-publications/generated-information-returns/` as the repo-owned replacement preview templates for source-document blocks that should not use the original non-fillable IRS information-return PDFs directly
- `forms-instructions-and-publications/generated-worksheets/` as the repo-owned fillable worksheet templates for modeled worksheets that do not have a suitable IRS fillable PDF artifact

These derived artifacts come from the local IRS PDFs. They are not embedded directly into the master JSON.

## Primary artifacts

- `forms-instructions-and-publications/IRS_Federal_Individual_2025.yaml`
- `forms-instructions-and-publications/forms/`
- `forms-instructions-and-publications/instructions/`
- `forms-instructions-and-publications/publications/`
- `forms-instructions-and-publications/worksheets/`
- `forms-instructions-and-publications/information-returns/`
- `forms-instructions-and-publications/generated-worksheets/`
- `forms-instructions-and-publications/generated-information-returns/`
- `forms-instructions-and-publications/instruction-summaries/`
- `forms-instructions-and-publications/publication-summaries/`
- `forms-instructions-and-publications/pdf_form_scan.json`
- `forms-instructions-and-publications/forms/build_pdf_field_maps.py`
- `forms-instructions-and-publications/forms/build_generated_worksheet_templates.py`
- `forms-instructions-and-publications/forms/build_generated_info_return_templates.py`
- `reference-data/federal/2025/publication_associations.json`
- `reference-data/federal/2025/pdf_field_maps/`
- `src/downloader.py`

## Entry modes

### Mode A: First-time bootstrap

Use this mode when the tax-year manifest does not exist yet or is too incomplete to trust.

Target outcomes:

- create the YAML manifest for the tax year
- create the expected folder structure
- populate the repo with the required PDFs
- establish the summary layer
- verify that the downloader can reconstruct the local document tree from the manifest

### Mode B: Refresh / nth-pass maintenance

Use this mode when the YAML manifest already exists and the repo already contains some or most of the materials.

Target outcomes:

- identify missing, stale, or misnamed documents
- add newly required forms, instructions, publications, worksheets, or information returns
- refresh summaries and publication associations as needed
- use the downloader to fetch only what is missing unless a full refresh is required

## Workflow

### Step 1: Declare the tax year and target paths

- confirm the tax year at the top of this workflow before doing anything else
- use the tax year consistently in the manifest filename, publication associations path, and any other year-specific references
- for the current repo format, the target manifest is `forms-instructions-and-publications/IRS_Federal_Individual_2025.yaml`

### Step 2: Ensure the folder structure exists

The materials tree should contain, at minimum:

- `forms-instructions-and-publications/forms/`
- `forms-instructions-and-publications/instructions/`
- `forms-instructions-and-publications/publications/`
- `forms-instructions-and-publications/worksheets/`
- `forms-instructions-and-publications/information-returns/`
- `forms-instructions-and-publications/generated-worksheets/`
- `forms-instructions-and-publications/generated-information-returns/`
- `forms-instructions-and-publications/instruction-summaries/`
- `forms-instructions-and-publications/publication-summaries/`

If bootstrapping from scratch, create these folders before trying to download or summarize anything.

### Step 3: Create or refresh the YAML manifest

If the tax-year manifest does not exist:

- create it using the current repo format
- add section headers for the document classes required by this project
- populate it with the tax-year inventory of forms, instructions, publications, worksheets, and information returns

If the tax-year manifest already exists:

- audit it rather than rebuilding it blindly
- correct dead links, missing entries, duplicates, naming mismatches, and filename inconsistencies
- add newly in-scope materials rather than inventing ad hoc local files outside the manifest

The current file format is YAML with top-level sections such as:

- `Forms`
- `Information_returns`
- `Worksheets`
- `Instructions`
- `Publications`

Use stable human-readable keys and IRS PDF URLs as values. Keep the repo's current naming conventions unless there is a strong reason to normalize a broken name.

### Step 4: Audit what already exists locally

Before downloading:

- compare the manifest entries against the local folders
- identify which PDFs already exist and appear usable
- identify which entries are missing, stale, misnamed, or need replacement
- identify any local files that are not represented in the manifest

If a local file is obsolete or replaced, prefer moving it into `trash/` rather than deleting it outright unless specifically directed otherwise.

### Step 5: Build or use the downloader

The current repo already has a downloader at `src/downloader.py`.

Current behavior:

- reads the YAML manifest at `forms-instructions-and-publications/IRS_Federal_Individual_2025.yaml`
- downloads sections into `forms/`, `instructions/`, `publications/`, and `information-returns/`
- skips files that already exist
- infers filenames from the URL path

If bootstrapping from zero and `src/downloader.py` does not exist, build a simple downloader that:

- reads the tax-year YAML manifest
- supports the current document classes used by the repo
- creates destination folders automatically
- downloads all listed files into the correct subfolders
- skips existing files by default
- reports failures clearly

If updating an existing repo, use the current downloader first and only extend it when the current manifest or folder scheme requires more coverage.

Minimum downloader modes to support:

- full download from the YAML into the repo folders
- missing-only download, which skips files that already exist

Preferred downloader improvements when needed:

- explicit command-line support for full vs missing-only runs
- better section handling, including worksheets if worksheet PDFs are listed in the manifest
- clearer reporting of skipped, downloaded, and failed items

### Step 6: Download or refresh the PDFs

For a first-time bootstrap:

- run the downloader against the full manifest
- verify that the expected local folders are populated

For an nth-pass refresh:

- run the downloader in missing-only mode if the local tree is mostly correct
- use a more forceful refresh only when filenames, URLs, or PDFs themselves need replacement

After downloading:

- verify that local filenames line up with how the repo references them
- check for broken IRS URLs or documents that actually redirect to prior-year files
- note any irreconcilable gaps in an audit note rather than silently ignoring them

### Step 6a: Refresh the PDF scan and widget catalogs

After the local PDFs are in place, refresh the machine-readable artifacts that describe fillability and widget structure.

- update `forms-instructions-and-publications/pdf_form_scan.json` so the repo has current `acroform` and `field_count` data
- regenerate `reference-data/federal/2025/pdf_field_maps/` using `forms-instructions-and-publications/forms/build_pdf_field_maps.py`
- regenerate `forms-instructions-and-publications/generated-worksheets/` using `forms-instructions-and-publications/forms/build_generated_worksheet_templates.py` when modeled worksheet schemas or worksheet PDF expectations change
- regenerate `forms-instructions-and-publications/generated-information-returns/` using `forms-instructions-and-publications/forms/build_generated_info_return_templates.py` when source-document block templates or block schemas change
- treat `pdf_field_maps/` as a separate intermediate layer between raw IRS PDFs and the app's fill-preview logic
- preserve any hand-authored mappings when regenerating; the generator should merge them into the field maps rather than discard them

This step exists so later workstreams do not need to rediscover PDF fillability or widget names from scratch.

### Step 7: Build or refresh the summary layer

Create or refresh markdown summaries for:

- instructions in `forms-instructions-and-publications/instruction-summaries/`
- publications in `forms-instructions-and-publications/publication-summaries/`

Use the summaries early, not as an afterthought. They exist to reduce repeated PDF rereads and to surface:

- elections
- worksheet logic
- thresholds
- exceptions
- phaseouts
- sourcing and allocation rules
- cross-form dependencies

Do not summarize ordinary blank forms just because they exist. The primary summary target is instructions and publications.

### Step 8: Refresh summary indexes and associations

When the source-material set changes materially:

- refresh the summary indexes in the summaries folders if they exist
- refresh `reference-data/federal/2025/publication_associations.json`
- add newly discovered publication-to-form or publication-to-worksheet relationships

This is where publication-defined worksheet paths should become visible before the master JSON workstream tries to implement them.

### Step 9: Final verification

Before considering the materials layer complete, confirm that:

- the YAML manifest matches the intended tax-year source inventory
- required PDFs exist locally in the correct folders
- `pdf_form_scan.json` reflects the current local fillable PDFs
- `pdf_field_maps/` can be regenerated from the local PDFs plus any retained hand-authored mappings
- generated worksheet templates can be regenerated for modeled worksheets that the app should preview or export as fillable PDFs
- generated information-return templates can be regenerated for the source-document block types the app previews instead of the original IRS PDFs
- instructions and publications have the expected summaries
- downloader behavior is sufficient to rebuild the local materials layer from the manifest
- publication associations and summary indexes reflect the current set

## Bootstrap checklist

- create the tax-year manifest if missing
- create the materials folders if missing
- build or verify `src/downloader.py`
- run a full download
- create or refresh the PDF scan and widget catalogs
- create the initial summary set
- create or refresh publication associations

## Refresh checklist

- audit the existing manifest
- fetch only missing or corrected files unless a full refresh is justified
- refresh the PDF scan and widget catalogs after source-PDF changes
- add summaries for new instructions or publications
- refresh indexes and associations
- move obsolete local artifacts to `trash/` when replacing them

## Done means

- a fresh model could use the manifest and downloader to reconstruct the current materials layer
- a later maintenance pass could use the same workflow to update only what changed
- forms, instructions, publications, worksheets, and information returns live in the expected locations
- the derived PDF audit layer exists so later workstreams know which PDFs are fillable and what widgets they expose
- the summary layer is current enough to support modeling work without repeated blind PDF rereads

## Common failure modes

- treating the existing YAML as untouchable even when it is stale or incomplete
- downloading documents without first deciding what belongs in which section
- letting filenames drift away from the manifest and summary references
- changing the local PDF set without refreshing `pdf_form_scan.json` and `pdf_field_maps/`
- forgetting to update summaries after adding new source materials
- relying on a downloader that only works for the current happy path and cannot rebuild the materials tree from scratch
