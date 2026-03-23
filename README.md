# Open Tax Project

### The Challenge: 
Can we design a ```plan.md``` file sufficient for an LLM to recreate accurate and useable Federal tax software?

### Scope
In order to limit the scope of this exercise, I've created a .yaml of all the relevant items:
  - Forms and schedules
  - Instructions
  - Publications
  - Information Returns (W-2, 1099-INT, etc.)

Providing these isn't strictly necessary, but will limit scope.  For the current phase, the intended functional scope should not exceed `TurboTax Premier`. 

### Rules
  Create a plan.md that can guide an LLM from start to finish:
  - Manual entry of primary data
  - Creation of worksheets as described in instructions and publications
  - Flow through so no duplicate entries are needed
  - Correctly linking lines and cells with formulas
  - Filling in of forms for filing in .pdf format
  - Enforce formatting rules, heirarchy rules, etc.
  
  Optional:
  - Allow information returns to be entered initially by scanning .pdfs issued by employers, financial institutions, etc.

### Motivation
  - Learn how to design a project that can prompt a model in a highly complex task.
  - To test the gradual improvement over time of LLMs.
- 





# DRAFT MATERIAL BELOW - possibly to be deleted
- `federal_1040_2025_old.json`
  Backup copy of the earlier model state.

- `source-code/downloader.py`
  Downloads IRS PDFs into the project folders. Keep this file.

- `source-code/tax_qt_app.py`
  Qt desktop editor for reviewing and entering data against the model.

- `sample.json`
  Small schema reference file.

- `build_manifest.json`
  Machine-readable snapshot of current model coverage, key wiring, source blocks, app behavior expectations, and known gaps.

- `docs/COVERAGE_STATEMENT.md`
  Plain-language scope: what the JSON model guarantees vs. what still requires IRS sources, overrides, or professional judgment.

- `reference-data/federal/2025/`
  Versioned lookup tables, rate schedules, and worksheet parameter tables used by the evaluator.

## IRS source tree

- `forms-instructions-and-publications/forms/`
  IRS forms and schedules.

- `forms-instructions-and-publications/instructions/`
  IRS instructions.

- `forms-instructions-and-publications/publications/`
  IRS publications.

- `forms-instructions-and-publications/information-returns/`
  Blank W-2, 1099, 1098, and similar forms used as reference for block modeling.

- `forms-instructions-and-publications/worksheets/`
  Standalone worksheet PDFs.

- `forms-instructions-and-publications/IRS_Federal_Individual_2025.yaml`
  Canonical source manifest for forms, instructions, publications, worksheets, and information returns.

- `reference-data/federal/2025/manifest.json`
  Machine-readable inventory of the Federal 2025 table-driven datasets.

## Environment

Install dependencies with:

```bash
pip install -r requirements.txt
```

If you are already inside the project virtualenv, run tools from the project root.

## Common commands

Run the Qt editor:

```bash
python source-code/tax_qt_app.py
```

The Qt app now starts with no return loaded. From there you can:

- choose `New Return` to start a fresh return from the `federal_1040_2025.json` template, or
- choose `Import Return` to open an existing saved return JSON.

Saved returns are intended to live in the project's `returns/` folder.

## Current direction

- The master JSON remains the source of tax logic and structure.
- Taxpayer-specific data should live in a separate return-data file.
- The near-term target is a dependency-aware federal individual package whose supported functionality does not go beyond `TurboTax Premier`.
- The long-term architecture may support broader tax coverage later, but that broader scope is explicitly out of bounds for the current implementation target.
- The package should be editable and reviewable directly in Qt without relying on spreadsheet export.

