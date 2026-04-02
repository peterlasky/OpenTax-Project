# Plans

This folder contains the active planning documents for the project.

`legacy-plan.md` in this folder is a legacy historical document. Keep it for context, but put new planning guidance in the active plan files here.

## Active plans

- `01-irs-materials-and-summaries.md`
  The workflow document for IRS materials. Covers first-time bootstrap, nth-pass refresh, manifest creation or maintenance, downloader use, PDF download/refresh, PDF scan and widget-catalog regeneration, generated worksheet and information-return templates, and summary generation.
- `01a-irs-materials-spec.md`
  The target-state specification for the IRS materials layer. Defines what classes of documents must exist, where they belong, what gets summarized, and what the downloader must support.
- `02-master-json-model.md`
  Covers construction and hardening of `federal_1040_2025.json`, including dependencies, worksheet layering, filing rules, PDF metadata, tri-state questionnaire modeling, navigator shorthand metadata, and the boundary between the master model and the separate PDF widget-mapping layer.
- `03-gui-and-pdf-workflow.md`
  Covers the desktop app, form visibility, editing behavior, save/load flow, PDF preview/fill behavior, navigator completion/shorthand behavior, repeating-block add/remove/reindex behavior, the separate `pdf_field_maps` methodology, generated worksheet/source-document templates, and end-to-end UX validation.
- `04-reverse-audit.md`
  Covers the separate read-only audit workflow that checks `federal_1040_2025.json` against primary IRS sources, records suspected errors or ambiguities, and writes findings to a separate errata document without editing the model.

## How to use these plans

- Start here, then read the specific plan for the workstream you are touching.
- When a task spans multiple workstreams, follow the owning plan first and cross-check the others before making changes.
- Keep `docs/FORM_MODEL_STATUS.md`, `docs/problematic_forms_and_lines.txt`, tests, and relevant summaries in sync with substantive work.

## Workstream boundaries

- IRS materials plan:
  Split between a workflow doc and a specification doc. Together they govern manifest creation or maintenance, downloader behavior, source-document inventory, normalization, storage layout, summary generation, fillability scans, generated worksheet/source-document templates, and generated PDF widget catalogs.
- Master JSON plan:
  Governs tax logic, intake blocks, equations, helper worksheets, filing sequences, dependency ordering, and the metadata contract that points into the separate PDF layer without embedding widget mappings directly in the master JSON.
- GUI/PDF plan:
  Governs the Qt editor, interaction model, return serialization, raw-vs-filled PDF preview, the `pdf_field_maps` runtime contract, and PDF output flow.
- Reverse-audit plan:
  Governs the independent verification workflow that reviews modeled cells and flows against forms, instructions, and publications, then records errata without changing the master JSON.

## Update rule

If a change alters project structure, workflow, or definition of done for one of these areas, update the relevant file in `plans/` in the same work.
