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
- `forms-instructions-and-publications/generated-worksheets/`
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
- for questionnaire/intake rows, prefer side-by-side yes/no checkboxes over radio buttons when the underlying data is tri-state; checked yes means `True`, checked no means `False`, and both unchecked means unanswered `None`
- when a required tri-state question is unanswered, show that state clearly in the value area so the user is forced to resolve it rather than silently carrying a default
- for repeating source-document blocks, support both adding and removing individual entries, and treat removal as a reindexing operation so later entries move up cleanly

### Phase 2: Form visibility and navigation

- auto-show forms that are filed, materially active, or useful for review
- keep the intake root and main return easy to find
- ensure keep-for-records forms can still appear when they have meaningful computed output
- organize the left navigation as a display tree rather than a flat list: `f1040_Federal_Info_Worksheet` first, `f1040` next, then subordinate filing forms in filing-order-derived sequence with indentation
- place repeating source-document blocks beneath their owning form and subordinate worksheets beneath the form or schedule that uses them
- when a worksheet or helper is ambiguous because it is publication-driven or shared across multiple parents, prefer inference from equation references and owner-title hints first, then allow optional metadata overrides rather than hardcoding GUI-only exceptions
- use concise navigator labels when the formal IRS title is too long; prefer model-provided shorthand where present, then safe derived abbreviations
- show repeated source-document blocks with copy counts such as `1099-INT x2`
- show category-specific multi-copy forms separately when that distinction matters, using compact suffixes such as category labels in parentheses
- maintain per-sheet completion state in the navigator; if a visible form, worksheet, or block-backed sheet is missing required input, render it as incomplete rather than visually identical to a complete sheet
- keep completion styling and filed-form styling compatible so the navigator communicates both filing/review status and missing-input status

### Phase 3: Return serialization

- preserve sparse JSON saves
- avoid losing source-block entries, overrides, or user-entered metadata
- keep load/save compatible with evolving model structure as much as practical

### Phase 4: PDF preview and fill

- auto-display the relevant local PDF when a form, schedule, worksheet, or information return is selected
- prefer explicit PDF metadata from the master JSON over filename guessing when choosing a preview source
- use filled preview when a separate field-map file provides renderable mappings
- fall back to raw PDF preview when no mapping exists but a local PDF does
- keep worksheet previews useful by generating fillable worksheet templates when no suitable IRS worksheet PDF exists
- keep information-return previews useful by using repo-generated fillable templates rather than trying to print the original non-fillable IRS source PDFs directly
- give source-document blocks explicit PDF metadata when the local file and fillable status are known
- when a form can require multiple filed copies of the same PDF layout, preview and export should be driven by a shared attachment-copy builder so the on-screen preview and final print package use the same row chunking and checkbox selection rules
- generated worksheet templates should look closer to IRS worksheets than to generic form builders: prefer underline-style entry areas, restrained headers/subheaders, and concise page numbering instead of noisy helper text

### Phase 5: Separate PDF mapping layer

- treat `reference-data/federal/2025/pdf_field_maps/` as the app's intermediate PDF widget layer
- each field-map file should record the source PDF, widget inventory, geometry, and any known `source` expressions or render modes
- keep legacy hand-authored mappings authoritative where they already exist
- allow generator-assisted heuristic mappings only where the PDF widget layout is close enough to the modeled cell layout to be trustworthy
- prefer leaving a form on raw preview over filling it with low-confidence guessed mappings
- for non-filed source documents such as information returns, prefer generated OpenTax templates over the original IRS non-fillable layouts when the goal is a fillable preview/print artifact
- for modeled worksheets that need preview/export coverage, prefer generated OpenTax worksheet templates when there is no suitable IRS fillable worksheet artifact

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
- for copy-aware row forms, keep one canonical field map for the IRS PDF and supply copy-scoped context at render time so the same map can render Box A copy 1, Box A copy 2, Box B copy 1, and so on without cloning the mapping file
- use this pattern for forms similar to Form 8949: same physical PDF layout, mutually exclusive checkbox families or row sections, and overflow that creates additional filed copies
- when a source-document block is backed by a generated template, the app should not fall back to the original `information-returns/` PDF just because it exists locally
- when a worksheet is backed by a generated template, keep the master JSON metadata and field maps aligned with that generated artifact on rebuild
- generated worksheet templates should avoid superfluous scaffolding text such as generic "worksheet entries" labels when the form title and field labels already explain the content

## Task checklist

- keep the UI synchronized with current cell and block metadata
- ensure new forms or blocks can appear without bespoke GUI rewrites when the schema already supports them
- add explicit handling only when a form truly needs special logic
- keep left-pane hierarchy rules predictable so a full return reads like a dependency tree rather than a random visible-sheet pile
- test visibility behavior whenever filing logic changes
- test save/load when adding new block structures or overrideable cells
- test PDF fallback behavior whenever preview routing changes
- test preview-expression support whenever new field-map expression forms are introduced
- regenerate `pdf_field_maps/` when the local PDF set or PDF-driving cells change materially
- when changing questionnaire UX, verify both interaction behavior and the required/unanswered visual state
- when changing navigator labels or state styling, verify shorthand labels, copy counts, category suffixes, and incomplete-state rendering together
- when changing repeating source-block behavior, verify add/remove/reindex flow and the preview's selected-entry behavior after removal

## Done means

- a user can load or start a return, enter source facts, review computed forms, and see the relevant PDFs without hunting through hidden state
- forms shown in the UI correspond to meaningful return activity
- save/load round-trips preserve entered and computed state correctly
- PDF preview behavior is predictable for raw, partially mapped, and fully mapped local forms
- the navigator communicates hierarchy, compact identity, copy counts, and incomplete state clearly enough that a user can tell what still needs attention

## Common failure modes

- UI logic drifting away from the JSON model's actual schema
- forms staying hidden even though they have meaningful computed values
- source facts entered in blocks not surfacing in the expected review form
- PDF preview silently failing when a local file exists but mapping is incomplete
- coupling PDF widget ids directly to GUI code instead of going through the separate field-map layer
- changing the tax model without adding the UI and preview coverage needed to expose the new behavior
