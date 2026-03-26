# GUI And PDF Workflow Plan

## Purpose

This plan governs the desktop application and PDF workflow: how a taxpayer return is edited, evaluated, displayed, serialized, and previewed.

The aim is a usable Qt-based tax editor where the JSON model drives the interface, the user can enter facts once, and the right forms appear with live calculated values and meaningful PDF previews.

## Primary artifacts

- `src/main.py`
- `src/pdf_preview.py`
- `returns/`
- `federal_1040_2025.json`
- `tests/test_tax_logic.py`
- `forms-instructions-and-publications/pdf_form_scan.json`
- PDF files under `forms-instructions-and-publications/`
- `forms-instructions-and-publications/generated-information-returns/`
- any reference-data or PDF mapping files used by preview/fill logic
- `reference-data/federal/2025/pdf_field_maps/`
- `reference-data/federal/2025/pdf_mappings/`

## Principles

- the GUI is a view/editor over the master model, not a separate tax engine
- users should enter source facts once and let them flow upward
- visibility should reflect real filing or review relevance, not just static hardcoded lists
- keep manual overrides visible and understandable
- raw PDF preview is better than no preview when a local PDF exists but field mapping is incomplete
- explicit form metadata should identify whether a modeled sheet is a fillable form and which local PDF should be displayed for it
- keep the PDF widget-mapping layer separate from the master JSON so preview/fill logic can evolve independently of tax logic
- save/load must preserve the sparse return format cleanly

## Workstreams

### Phase 1: Data-entry UX

- maintain spreadsheet-like editing for forms and blocks
- keep source-document entry simple and repeatable
- support clear distinction between manual cells, computed cells, and overridden computed cells

### Phase 2: Form visibility and navigation

- auto-show forms that are filed, materially active, or useful for review
- keep the intake root and main return easy to find
- ensure keep-for-records forms can still appear when they have meaningful computed output

### Phase 3: Return serialization

- preserve sparse JSON saves
- avoid losing source-block entries, overrides, or user-entered metadata
- keep load/save compatible with evolving model structure as much as practical

### Phase 4: PDF preview and fill

- auto-display the relevant local PDF when a form, schedule, worksheet, or information return is selected
- prefer explicit PDF metadata from the master JSON over filename guessing when choosing a preview source
- use filled preview when a separate field-map file provides renderable mappings
- fall back to raw PDF preview when no mapping exists but a local PDF does
- keep information-return previews useful by using repo-generated fillable templates rather than trying to print the original non-fillable IRS source PDFs directly
- give source-document blocks explicit PDF metadata when the local file and fillable status are known

### Phase 5: Separate PDF mapping layer

- treat `reference-data/federal/2025/pdf_field_maps/` as the app's intermediate PDF widget layer
- each field-map file should record the source PDF, widget inventory, geometry, and any known `source` expressions or render modes
- keep legacy hand-authored mappings authoritative where they already exist
- allow generator-assisted heuristic mappings only where the PDF widget layout is close enough to the modeled cell layout to be trustworthy
- prefer leaving a form on raw preview over filling it with low-confidence guessed mappings
- for non-filed source documents such as information returns, prefer generated OpenTax templates over the original IRS non-fillable layouts when the goal is a fillable preview/print artifact

## PDF-specific rules

- store local PDFs in stable locations under `forms-instructions-and-publications/`
- keep `fillable_form`, `pdf_source_path`, and `pdf_field_count` aligned with `pdf_form_scan.json` and the local PDF inventory
- keep widget-level mapping details in `pdf_field_maps/`, not in `federal_1040_2025.json`
- use `source` expressions in the field maps so the preview engine can resolve either direct cell references or small computed expressions
- support three states explicitly:
  raw local PDF only, generated field map without renderable mappings, and filled preview with renderable mappings
- preserve the distinction between previewing a blank/local form and generating a filled filing preview
- round and format displayed values according to the target PDF's practical needs
- prefer mapping improvements for high-value forms first
- when a form uses repeating blocks or cross-form source documents, prefer explicit block-aware expressions over hardcoded one-off GUI logic
- when a source-document block is backed by a generated template, the app should not fall back to the original `information-returns/` PDF just because it exists locally

## Task checklist

- keep the UI synchronized with current cell and block metadata
- ensure new forms or blocks can appear without bespoke GUI rewrites when the schema already supports them
- add explicit handling only when a form truly needs special logic
- test visibility behavior whenever filing logic changes
- test save/load when adding new block structures or overrideable cells
- test PDF fallback behavior whenever preview routing changes
- test preview-expression support whenever new field-map expression forms are introduced
- regenerate `pdf_field_maps/` when the local PDF set or PDF-driving cells change materially

## Done means

- a user can load or start a return, enter source facts, review computed forms, and see the relevant PDFs without hunting through hidden state
- forms shown in the UI correspond to meaningful return activity
- save/load round-trips preserve entered and computed state correctly
- PDF preview behavior is predictable for raw, partially mapped, and fully mapped local forms

## Common failure modes

- UI logic drifting away from the JSON model's actual schema
- forms staying hidden even though they have meaningful computed values
- source facts entered in blocks not surfacing in the expected review form
- PDF preview silently failing when a local file exists but mapping is incomplete
- coupling PDF widget ids directly to GUI code instead of going through the separate field-map layer
- changing the tax model without adding the UI and preview coverage needed to expose the new behavior
