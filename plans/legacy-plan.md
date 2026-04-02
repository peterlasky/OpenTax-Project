# Open Tax Plan

Legacy note:
- `plans/legacy-plan.md` is now a legacy historical rebuild document.
- Active planning lives in `plans/README.md` and the plan files under `plans/`.

## 1. Purpose and scope
This project exists to answer a specific question:

- can a single legacy rebuild document, together with the IRS source materials in this repo, guide a strong LLM to rebuild accurate and usable federal individual tax software

The required output is not just a static tax model. The project is two linked products:

- a structured federal tax model in `federal_1040_2025.json`
- a Qt desktop app that lets a user load a return, enter data, review the forms, and see a live PDF preview

This plan is meant to be a clean rebuild document. It should tell an LLM what matters, what order to build in, what rules must survive, and what current repo artifacts already exist.

### Scope Ceiling
Current product scope should not exceed `TurboTax Premier`.

That means:

- prioritize ordinary federal individual returns
- include common homeowner, investor, retirement, education, child-credit, health-insurance, and passive/rental branches
- avoid drifting into broad business-entity software, payroll platforms, or professional-preparer scope
- architecture may be more general than Premier, but implementation priorities and claims of completeness should stay inside that ceiling

### Primary Deliverables

- `federal_1040_2025.json`
  The **master logic/model file** for the Federal 2025 individual package.
- `src/main.py`
  The Qt editor for taxpayer returns built from the model.
- `reference-data/federal/2025/`
  Machine-readable tax tables, thresholds, and parameters that should not be hardcoded into equations.
- `reference-data/federal/2025/pdf_field_maps/`
  Generated per-form PDF widget catalogs and mappings used by the preview system.
- `reference-data/federal/2025/pdf_mappings/`
  Legacy hand-authored PDF mappings retained as an input to the generated field-map layer.
- `forms-instructions-and-publications/publication-summaries/`
  Concise publication and instruction summaries used as an early searchable rule/index layer.  
- `docs/build_manifest.json`
  Machine-readable snapshot of current modeled state, wiring, conventions, and gaps.

## 2. Source Materials
The source tree is the authority base for the rebuild.

- `forms-instructions-and-publications/IRS_Federal_Individual_2025.yaml`
  Canonical inventory of forms, instructions, publications, worksheets, and information returns.  URLS are here for download if they have not already been downloaded via a `downloader.py` tool.
- `forms-instructions-and-publications/forms/`
  IRS forms and schedules such as `f1040.pdf`.
- `forms-instructions-and-publications/instructions/`
  Instruction PDFs such as `i1040gi.pdf`.
- `forms-instructions-and-publications/publications/`
  IRS publications.
- `forms-instructions-and-publications/information-returns/`
  Blank W-2, 1099, 1098, and related forms used for source-block modeling.
- `forms-instructions-and-publications/worksheets/`
  Standalone worksheet PDFs.
- `forms-instructions-and-publications/publication-summaries/` and `forms-instructions-and-publications/instruction-summaries/`
  Important step to avoid forcing the model to read and reread each .pdf multiple times.  Creation of complete yet semantically concise `.md` files for each.  Least verbosity.  Prioritize model's understanding at subsequent passes over human readability.  

Important note:
- publications are not optional commentary: they often define elections, worksheet logic, exceptions, attribution rules, sourcing rules, and eligibility rules that are not obvious from the face of a form

## 3. Rebuild Principles

- build cells from source facts upward, not from top-line outputs downward
- determining the type of data and source of the data (or the formula computing the data) depends on a careful reading, which includes the name of the cell, the instructions for the cell, and any reference to the cell in the relevant publications.  If the name of the cell is, for example, age as of 1-1-2026, then you should be able to create an equation that computes the age based on birthday or birth year.
- Maintain default values.
- prefer explicit data flow over hidden assumptions
- preserve the distinction between user-entered facts and computed results
- keep the JSON model and the Qt app aligned; they are one system
- preserve traceability from a computed value back to a worksheet, form line, source block, or reference table
- do not hardcode IRS tables into scattered equations when they belong in reference data
- do not ask the user to enter the same fact twice if it can flow through from a lower-rank source
- some cells are calculated based on other cells but can also be overwritten.  Some cannot be overwritten.

## 4. Early Workflow
The first part of a rebuild should happen in this order.

1. Read `README.md`, `plans/README.md`, `docs/build_manifest.json`, and this legacy `plans/legacy-plan.md` for historical context.
2. Inventory the IRS materials from the YAML manifest.
3. Create or refresh `docs/FORM_MODEL_STATUS.md` so every YAML-listed form or schedule is marked as `modeled`, `scaffolded`, `missing`, or `out_of_scope`.
4. Create or refresh `forms-instructions-and-publications/publication-summaries/` and `forms-instructions-and-publications/instruction-summaries/` early, before deep form wiring.
5. Create or refresh publication-to-form/worksheet associations in `reference-data/federal/2025/publication_associations.json`.
6. Indentify all worksheets and their heirarchies.  Such as Form XXXX.Line @$#@$ worksheet, etc.  or worksheets that should be standalone
7. Build or validate the intake layer first.
8. Then build the main return, core schedules, core worksheets, and common follow-on forms.

Why summaries come early:

- they make publication-defined worksheet dependencies visible sooner
- they reduce the chance of forgetting elections and exceptions until late
- they give the rebuild process a searchable shorthand layer without replacing the actual PDFs

Why the form-status inventory comes early:

- it prevents manifest-listed forms such as `Schedule H` from disappearing into generic phrases like "other YAML-listed forms"
- it separates truly missing forms from scaffolded forms and fully modeled forms
- it forces the audit trail to stay synchronized with the actual JSON model

## 5. Build Order
- Use dependency order, not convenience order.  
- Periodically, review dependencies to ensure that user entered data flows upward.  Example. Interest on a mortgage could be entered into a 1098 entry form, which then flows upward to the 1040 Schedule A to compute the Schedule A deduction.   But it might flow to a worksheet first.  Please be careful.  
- When constructing the dependencies, check against instruction summaries and relevant publications.  

### 5.1 Always-first layer

- `f1040_Federal_Info_Worksheet`
- core repeating source blocks under the owning form:
  - `dependents`
  - `w2`
  - `1099_int`
  - `1099_div`
  - `1099_r`
  - `1099_b`
  - `1099_da`
  - `1099_s`
  - `ssa_1099`
  - `rrb_1099`
  - other common information returns as needed

### 5.2 Core return layer

- `f1040`
- `f1040sr`
- top-of-form identity and status fields
- line flows directly driven by source blocks

### 5.3 Core worksheet layer

- `f1040_Lines_5a_and_5b`
- `f1040_Lines_6a_and_6b`
- `f1040_Line_12e_Standard_Deduction_Dependents`
- `f1040_Tax_Computation`
- `f1040_Line_16_Foreign_Earned_Income_Tax`
- `f1040_Line_16_Qualified_Dividends_Capital_Gain_Tax`
- `f1040_Schedule_1_Line_1_State_Local_Tax_Refund`
- `f1040_Schedule_1_Line_17_Self_Employed_Health_Insurance`
- `f1040_Schedule_1_Line_20_IRA_Deduction`
- `f1040_Schedule_1_Line_20_IRA_Deduction_Continued`
- `f1040_Schedule_1_Line_21_Student_Loan_Interest`
- `f1040_Line_27a_EIC_Worksheet_A`
- `f1040_Line_27a_EIC_Worksheet_B`
- `f1040_Line_27a_EIC_Worksheet_B_Continued`

### 7.4 Common follow-on forms

- `f8812`
- `f8863`
- `f2441`
- `f8889`
- `f8949`
- `f8962`
- `f8995`
- `f8995a`
- `f1116`
- `f2210`
- `f8606`
- `f8959`
- `f6251`

### 7.5 Business, rental, investment, and specialty layer

- `f1040sc`
- `f1040sd`
- `f1040se`
- `f1040sf`
- `f4562`
- `f4797`
- `f4952`
- `f6198`
- `f7203`
- `f8582`
- `f8582cr`
- `f4684`
- `f5329`
- `f5695`
- and similar YAML-listed forms as triggered by facts

## 8. Current Working State
Use `docs/build_manifest.json` as the machine-readable snapshot. As of the current repo state, the important human summary is:

- the federal info worksheet exists and is the intended intake root
- the core `f1040` exists
- the main Social Security, pension simplification, tax computation, IRA deduction, student loan interest, and EIC helper worksheets exist
- `f8949` and `f1040sd` exist
- the PDF preview system exists and has `f1040` mapping support
- publication summaries exist for all publication files currently in the repo

Current known incompleteness includes:

- several `1040` lines still depend on schedules not fully built
- `1099_b`, `1099_da`, and `1099_s` are not yet automatically transformed into `f8949` rows
- some Schedule D flows remain partially manual because upstream forms are missing
- reference tables still need continued import/validation

## 9. Data Model Contract
The JSON model is a dependency graph.

### 9.1 Top-level structure

- jurisdiction-year root such as `Federal 2025`
- forms keyed by stable form/worksheet IDs
- each form has `_meta`
- each form has `cells`
- some forms also own `blocks`

### 9.2 Form metadata

- `_meta.name`
- `_meta.active`
- `_meta.rank`

Rules:

- `rank` is a float
- lower rank means earlier evaluation and earlier display order
- forms and worksheets must be evaluated in ascending rank order

### 9.3 Cell contract
Every cell should support the following core fields.

- `order`
- `format`
- `default`
- `value`
- `manual_entry`
- `override_possible`
- `required_rule`
- `equation` when computed
- `description`
- `explanation`

Rules:

- every cell must have `order`
- `order` is the primary in-form display sort key
- untouched manual-entry cells should remain visually blank in the UI
- computed cells should be read-only unless `override_possible` is true

### 9.4 Block contract
Repeating user-entered sources live under `blocks` on the owning form, not as top-level forms.

Each block should carry:

- `active`
- `multiple_copies`
- `description`
- `explanation`
- `user_entered`
- `min_entries`
- `max_entries`
- `item_cells`
- `entries`

Each normal block item cell should also carry `required_rule`.

## 10. Naming Rules
Use stable shorthand IDs consistently.

### 10.1 Forms and schedules

- `f1040`
- `f1040sr`
- `f1040s1`
- `f1040sa`
- `f1040sd`

Rule:

- `f` + IRS shorthand, no spaces

### 10.2 Worksheets

- `f1040_Federal_Info_Worksheet`
- `f1040_Lines_5a_and_5b`
- `f1040_Line_16_Qualified_Dividends_Capital_Gain_Tax`

Rule:

- use stable descriptive worksheet IDs
- reuse an existing ID if already present in the repo
- for not-yet-built publication worksheets, use the same style when planning future additions
- worksheet `_meta.name` should lead with the owning form or schedule so the hierarchy is obvious in the UI
- if a worksheet is specific to one target, name it like `Form 1040 - ...`, `Schedule A (Form 1040) - ...`, or `Schedule D (Form 1040) - ...`
- if a worksheet genuinely applies to multiple targets, the title should still lead with the narrowest clear owner or explicitly name the shared scope

### 10.3 Blocks

- `w2`
- `1099_int`
- `1099_div`
- `dependents`

Rule:

- lowercase
- underscores where useful
- stable names that match the document type or repeated object

### 10.4 Cell IDs

- numbered form lines use line IDs like `1a`, `2b`, `12e`, `35a`
- unnumbered entry areas use word IDs like `first_name`, `state`, `filing_status_single`
- worksheet lines can use stringified numbers like `"1"` when appropriate

## 11. Equation and Linkage Rules

### 11.1 Same-form reference

- use the cell key directly
- example: `1a + 1b + 1c`

### 11.2 Cross-form reference

- use `form_id.cell_id`
- example: `f1040s1.10`
- example: `f1040_Federal_Info_Worksheet.taxpayer_first_name`

### 11.3 Sum over a block

- use `sum(block_id.*.field_name)`
- example: `sum(w2.*.box_1)`
- example: `sum(1099_int.*.box_8)`

### 11.4 Specific block entry

- use `block_id.index.field_name`
- example: `w2.0.box_1`

### 11.5 Repeating sub-entry

- use `block_id.index.field_name.sub_index.sub_field`
- example: `w2.0.box_12.0.amount`

### 11.6 Conditional source resolution

- conditional worksheet choice may use `or` chains
- example: a line may resolve from a Schedule D worksheet, qualified-dividend worksheet, ordinary tax computation worksheet, or foreign-earned-income worksheet depending on facts

### 11.7 Overrides

- if a computed cell is overridden, downstream evaluation must use the override until it is cleared
- override behavior must come from `override_possible`, not from UI guesswork

## 12. Requiredness and Input Semantics
The UI should not treat `format` as the whole semantic contract.

Track at least these concepts:

- storage type
- manual vs computed vs overrideable
- single-choice vs independent booleans
- conditionally enabled vs visible vs not applicable
- required vs optional vs conditionally required

`required_rule` should support:

- `always`
- `optional`
- a formula string

Examples that must survive:

- filing status is a one-hot choice
- spouse fields depend on filing status
- foreign-address fields depend on the foreign-address flag
- taxpayer/spouse recipient selectors on block rows should be `T` / `S` radios in the Qt app

## 13. Reference Data Rules
Do not force all IRS logic into inline equations.

Keep table-driven logic in `reference-data/federal/2025/`, including:

- ordinary income tax tables and parameters
- earned income credit table
- simplified method tables
- capital gain and qualified dividend tax parameters
- similar datasets that are naturally reference data rather than cell equations

Rule:

- if the IRS says “use the table,” import the table
- if the IRS gives a worksheet flow, preserve it as worksheet logic

## 14. Publication Rules

- publication summaries should be created or refreshed early
- `reference-data/federal/2025/publication_associations.json` should map publications to associated forms and worksheets using repo-style shorthand IDs
- publications refine rules, definitions, elections, embedded worksheets, and exceptions
- form structure normally starts from the form face and instructions, then publications complete the rule set

Examples of publication-heavy areas:

- `Pub. 550` for `f4952`
- `Pub. 915` for Social Security taxation
- `Pub. 590-A` and `Pub. 590-B` for IRA logic
- `Pub. 974` for `f8962`
- `Pub. 503` for `f2441`
- `Pub. 523` for main-home sale treatment

## 15. Qt App Contract
The Qt editor must remain aligned with the model.

### 15.0 Current Starting Point / Workability

The app should be described from the current repo state, not only from an ideal rebuild target.

Current starting point:

- the app is a working Qt desktop editor backed by `federal_1040_2025.json`
- it can start a blank return from the master template
- it can import an existing taxpayer return JSON
- it can save taxpayer return data in the flat return-data format
- it can recalculate modeled formulas after committed edits
- it can display used forms, worksheets, and active information-return blocks automatically in the left sheet list
- it can load and work with the current `John/Jane Doe` sample return
- it has live `f1040` PDF preview support in the current architecture when the preview dependencies and mappings are available

Current workability baseline:

- a user must be able to open the app and start or import a return without crashes
- a user must be able to enter and review taxpayer facts and source-document facts
- computed values must recalculate and remain reviewable in-sheet
- overrides must be visually distinct
- if a computed value is overridden, deleting the override value should restore the formula-computed value
- returns must be saveable and reloadable without copying the entire master template into the saved file
- the app may still be tax-coverage-incomplete and yet remain workable as an editor/review tool

Current non-workable examples:

- a return cannot be loaded or saved reliably
- a formula field shows stale or obviously wrong values because the evaluator is broken
- a user cannot clear an override back to the formula result
- used forms or blocks are hidden in a way that prevents review of the active return

### 15.1 Startup and file behavior

- app starts with no return loaded
- `New Return` copies from `federal_1040_2025.json`
- `Import Return` opens an existing taxpayer return
- taxpayer return files belong in `returns/`
- initial visible sheets should be:
  - `f1040_Federal_Info_Worksheet`
  - `f1040`

### 15.2 Table behavior

- rows sorted by `order`
- sheet list sorted by `rank`
- show debug columns for override and requiredness state
- preserve JSON types where practical

### 15.3 Visual semantics

- required-but-missing cells get subtle yellow background in the value area only
- invalid format gets bright red text in the value area only
- editable booleans use checkboxes or radios
- mirrored boolean choices downstream should display as check mark / blank rather than interactive controls
- one-hot groups should visually gray out unselected rows

### 15.4 Override policy

- mirrored identity and top-of-return facts from `f1040_Federal_Info_Worksheet` should generally not be overrideable downstream
- scenario overrides are for computed tax-result paths, not for copying a different name or SSN onto a form
- if a user clears an overridden computed cell, the override should be removed and the formula-computed value should return

## 16. PDF Preview Contract
The PDF preview system is part of the intended product, not a side experiment.

Current design intent:

- `f1040` has a mapped live preview path
- preview updates should happen on committed edits, not each keystroke
- widget-level mappings belong in `reference-data/federal/2025/pdf_field_maps/`
- legacy hand-authored mappings may still live in `reference-data/federal/2025/pdf_mappings/` as generator input
- text rendering may use overlay-first logic when AcroForm/XFA behavior is unreliable

## 17. Validation Rules
A rebuild is not complete until these checks pass.

- all forms and worksheets have stable IDs
- every cell has `order`
- every form/worksheet has `_meta.rank`
- equations resolve to existing cells, worksheets, or block fields
- no circular dependencies remain
- user-entered source blocks stay explicit
- blank manual cells remain blank in the UI
- overridden computed values propagate correctly
- PDF preview mappings remain coherent for currently supported forms and continue to respect the separate field-map layer

## 18. Immediate Priorities After Any Rebuild

1. Keep the federal info worksheet authoritative.
2. Keep source-document intake explicit and block-based.
3. Close missing schedule and worksheet dependency chains before adding isolated niche forms.
4. Use the publication summaries and publication associations to identify rule-heavy missing forms.
5. Continue importing and validating reference tables.

## 19. Bottom Line
If an LLM starts from this repo and follows this plan, it should be able to rebuild a dependency-aware federal individual tax package centered on `f1040`, with explicit source blocks, explicit worksheets, Qt editing support, and live PDF preview behavior, while staying within the current `TurboTax Premier` scope ceiling.
# Plan: Reconstructing the Federal 1040 Tax Code

**Goals:** 
  1. Use IRS forms, instructions, publications, and information returns—together with this plan and a deep-thinking LLM—to reconstruct the federal Form 1040 tax logic as a structured, executable model (JSON) where every line’s source and every data link is explicit. 
  2. Using qt build tax software that:
   - takes inputs in a spreadsheet-like interface using qt or other module
   - calculates and/or takes inputs
   - fill in the forms in real time
   - allows loading and saving of progress

  *Optional goal: 
   allow users to enter in information returns like W-2s and 1099-s via scanned pdfs and have the entries transcribed into a useable format.*
 


**Current product scope ceiling:** For now, target a level of user-facing functionality that does not go beyond `TurboTax Premier`. The architecture may remain more general than that, but implementation priorities, form coverage, automation depth, and claims of completeness should all stay within that practical ceiling unless this document is intentionally revised later.

**Audience:** Anyone (or an LLM) with access to the project’s attached tax forms, instructions, and publications who needs to extend, validate, or rebuild the 1040 model.

---

## 1. Project layout and inputs

| Path | Purpose |
|------|--------|
| `forms-instructions-and-publications/` | Root for IRS materials and downloader |
| `forms-instructions-and-publications/IRS_Federal_Individual_2025.yaml` | Master list: Forms, Instructions, Publications, Worksheets, Information_returns (URLs) |
| `forms-instructions-and-publications/downloader.py` | Downloads PDFs into `forms/`, `instructions/`, `publications/`, `information-returns/` |
| `forms-instructions-and-publications/forms/` | Form PDFs (e.g. f1040.pdf, f1040s1.pdf) |
| `forms-instructions-and-publications/instructions/` | Instruction PDFs (e.g. i1040gi.pdf) |
| `forms-instructions-and-publications/publications/` | Publication PDFs (e.g. p17.pdf) |
| `forms-instructions-and-publications/publication-summaries/` | Concise working summaries of publications, used as a fast rule/index layer before deeper publication rereads |
| `forms-instructions-and-publications/information-returns/` | W-2, 1099-INT, 1099-DIV, 1098, etc. (blank forms for reference) |
| `forms-instructions-and-publications/worksheets/` | **Standalone worksheet PDFs** (e.g. Federal Info Worksheet.pdf) when a worksheet is distributed as its own PDF rather than only inside instructions or publications |
| `reference-data/federal/2025/` | Versioned lookup tables, rate schedules, and worksheet parameter tables that should not be hardcoded into form equations |
| `docs/build_manifest.json` | Machine-readable snapshot of current model coverage, key wiring, source blocks, app contract, and known gaps; use this to improve reconstruction fidelity |
| `federal_1040_2025.json` | **Output model:** Federal individual package centered on Form 1040, including forms, schedules, worksheets, blocks, equations, and links |
| `docs/sample.json` | **Schema template:** Same structure, minimal example for reference |

**Where worksheets come from:** Worksheets may appear in any of three places: (1) **inside instruction PDFs** (e.g. 1040 General Instructions), (2) **inside publication PDFs** (when a pub includes a worksheet), or (3) as **standalone PDFs in the worksheets folder**. The YAML **Worksheets** section lists worksheet names by form; standalone PDFs in `worksheets/` are added manually or via downloader when the IRS provides a separate file. Build the model from all three sources as needed.

**Important source-rule reminder:** Publications are not just commentary. They often contain elections, definitions, attribution rules, exceptions, and computational guidance that are not obvious from a form's printed line numbering. Example: `Form 4952` depends materially on `Pub. 550` for investment-interest definitions and the line `4g` election mechanics, and Schedule `8812` line `21` depends on RRTA / `CT-2` source detail that is not visible from the line numbering alone.

**Early-publication-summary rule:** Fairly early in a rebuild, create or refresh concise markdown summaries in `forms-instructions-and-publications/publication-summaries/` for the publication set in scope. These summaries are not a substitute for the PDFs, but they are an important intermediate artifact: they make publication rules searchable, expose cross-form dependencies sooner, and reduce the chance that publication-driven worksheets, elections, and exceptions are forgotten until late in the process.

**Primary instruction set for 1040:** `instructions/i1040gi.pdf` (General Instructions for Form 1040). It covers the main 1040 and Schedules 1, 1-A, 2, 3 and lists all worksheets.

### 1.1 Package scope and build order

**Mission scope:** Build the federal individual package represented by `IRS_Federal_Individual_2025.yaml`, not just a two-form prototype. The YAML is the canonical superset and may contain forms beyond the current implementation target. For the current phase, however, use the YAML as the source inventory while constraining actual product goals to functionality not beyond `TurboTax Premier`. Forms, worksheets, blocks, instructions, and publications should therefore be prioritized in dependency order with Premier-level personal-return coverage first; forms beyond that ceiling may exist as references or future candidates, but they should not redefine what "done" means right now.

**Build-order rule:** Lower rows in the table below must receive lower `_meta.rank` values and be built first. A later row may depend on an earlier row; an earlier row must not depend on a later one.

| Order # | Build group | Type | Primary items | Activation rule / notes |
|---------|-------------|------|---------------|--------------------------|
| 1 | Intake | **Worksheet** | `f1040_Federal_Info_Worksheet` | Always build first. This is the primary source for taxpayer identity, filing status, address, and related top-of-return data. |
| 2 | Core input blocks | **Blocks** | `dependents`, `w2`, `w2g`, `1099_int`, `1099_div`, `1099_r`, `1099_b`, `1099_g`, `1099_nec`, `1099_misc`, `1099_k`, `1099_sa`, `1099_q`, `1099_s`, `1099_c`, `1098`, `1098_e`, `1098_t` | Build as user-entered sources. Activate by facts present in the taxpayer’s documents; keep schema ready even when entries are empty. |
| 3 | Main return | **Forms** | `f1040`, `f1040sr` | Build the main return after intake and core input blocks. `1040-SR` should share logic with `1040` where possible. |
| 4 | Core schedules | **Forms** | `f1040s1`, `f1040s1a`, `f1040s2`, `f1040s3`, `f1040sa`, `f1040sb`, `f1040sei`, `f1040sse` | These are the first dependency layer below or beside the 1040 and should be built before specialty forms that feed them. |
| 5 | Core 1040 worksheets | **Worksheets** | Simplified Method, Social Security Benefits, Standard Deduction for Dependents, Tax Computation, Foreign Earned Income Tax, Qualified Dividends and Capital Gain Tax, State and Local Tax Refund, Self-Employed Health Insurance, IRA Deduction, Student Loan Interest, EIC worksheets, and other 1040 worksheets listed in YAML | Build every worksheet named under `Worksheets -> 1040`. These often feed `1040`, `Schedule 1`, or other core schedules directly. |
| 6 | Common follow-on forms | **Forms** | `f8812`, `f8863`, `f2441`, `f8889`, `f8949`, `f8962`, `f8995`, `f8995a`, `f1116`, `f2210`, `f8606`, `f8959`, `f6251` | Build after the core package. These are common attachments triggered by credits, education, health coverage, investment sales, foreign tax, self-employment, and QBI facts. |
| 7 | Business and investment schedules/forms | **Forms** | `f1040sc`, `f1040sd`, `f1040se`, `f1040sf`, `f4797`, `f4562`, `f4952`, `f6198`, `f7203`, `f8582`, `f8582cr`, `f6252`, `f6781` | Build once the core package is stable. These forms tend to depend on the taxpayer’s trade, rental, farm, partnership, or investment facts. |
| 8 | Specialty and support forms | **Forms** | `f2106`, `f2555`, `f3800`, `f4137`, `f4684`, `f4835`, `f5329`, `f5405`, `f5695`, `f8283`, `f8396`, `f8615`, `f8814`, `f8862`, `f8880`, `f8888`, `f8960`, `f9465` and similar YAML forms | Build after the common package unless a core dependency requires one sooner. These are conditionally active and should be driven by facts and prior-form outputs. |
| 9 | Publications layer | **Publications / rules** | `Publication 17`, `505`, `596`, `915`, `970`, `590-A`, `590-B`, `969`, `974`, `550`, `936`, and other YAML publications as needed | Use publications to resolve rules and worksheets not fully described on the face of a form or in the general instructions. Publications are authority sources, not top-level JSON forms. |

**Activation rule:** The package should be broad, but not every form is active on every return. Build the schema for the relevant forms and blocks, then activate them conditionally based on user facts, information-return presence, instruction triggers, or dependencies from lower-ranked forms. In the current phase, activation and automation priorities should remain within the `TurboTax Premier` ceiling even if the broader schema can later be extended.

**Federal Information Worksheet requirement:** `f1040_Federal_Info_Worksheet` must be fully modeled, not stubbed. Follow **Section 4.4**: open `worksheets/Federal Info Worksheet.pdf`, ensure `_meta.name = "Federal Information Worksheet"`, `_meta.active = true`, and `_meta.rank = 1.0`, then add every entry place with `order`, `format`, `default`, `value`, `description` or `explanation`, and `manual_entry` as appropriate.

### 1.2 Dependency hierarchy

Use the following hierarchy when deciding rank and build order:

1. Intake worksheets and user-entered blocks
2. Main return identity and top-of-form fields
3. Core 1040 schedules and embedded worksheets
4. Common follow-on forms that feed the 1040 or its core schedules
5. Business, investment, and specialty forms
6. Publications and instructions as authority sources for rules, edge cases, and worksheet logic

When two forms depend on each other indirectly, split the logic so the lower-ranked form produces the intermediate values first and the higher-ranked form consumes them later. Do not model circular dependencies.

---

## 2. Data linkage: all ways data can link

The model is a **directed graph**: values flow from sources (user entry, information returns, worksheets) into form lines. Below are every supported linkage type.

### 2.1 Single cell → single cell (same form)

- **Syntax:** In `equation`, use the **cell key** (line number or name).
- **Examples:** `"equation": "1a + 1b + 1c"`, `"equation": "9 - 11"`, `"equation": "19a + 19b"`.
- **Rule:** Unqualified identifiers (e.g. `1a`, `9`) refer to another cell on the **same form**.

### 2.2 Single cell → single cell (another form or worksheet)

- **Syntax:** `form_id.cell_id`. Form ID is the key of the form (e.g. `f1040s1`, `f1040_Lines_5a_and_5b`).
- **Examples:**  
  - `"equation": "f1040s1.10"` (Schedule 1 line 10 → 1040)  
  - `"equation": "f1040_Lines_5a_and_5b.9"` (Simplified Method Worksheet line 9 → 1040 line 5b)  
  - `"equation": "f1040_Federal_Info_Worksheet.taxpayer_first_name"` (Federal Information Worksheet → 1040)  
  - `"equation": "f1040sa.itemized"` (Schedule A total → 1040)
- **Rule:** Cross-form references must use `form_id.cell_id`. Worksheet forms use names like `f1040_Lines_5a_and_5b`, `f1040_Line_16_Qualified_Dividends_Capital_Gain_Tax`, `f1040_Federal_Info_Worksheet`.

**Dependencies and rank:** Data flows from lower-rank forms and worksheets to higher-rank ones. If a higher-rank form (for example, Form 1040 at rank 2.0) uses data collected on a lower-rank worksheet (for example, Federal Information Worksheet at rank 1.0), point the higher-rank cell to the lower-rank one with `equation: "f1040_Federal_Info_Worksheet.cell_id"` and `manual_entry: false` (plus `override_possible: true` if the user may override it). Build and evaluate in rank order so every dependency is available before the dependent form is computed.

### 2.3 Cell → sum over a block (totals from information returns)

- **Syntax:** `sum(block_id.*.field_name)`. The `*` means “all entries” in that block.
- **Examples:**  
  - `"equation": "sum(w2.*.box_1)"` → 1040 line 1a (total wages from all W-2s)  
  - `"equation": "sum(1099_int.*.box_1)"` → 1040 line 2b (total taxable interest from all 1099-INTs)  
  - `"equation": "sum(1099_int.*.box_8)"` → 1040 line 2a (total tax-exempt interest)
- **Rule:** `block_id` is the key of a block under `blocks` (e.g. `w2`, `1099_int`, `dependents`). The equation evaluator must expand `*` over `blocks[block_id].entries` and sum the given `field_name`.

### 2.4 Cell → one specific block entry

- **Syntax:** `block_id.index.field_name`. Index is 0-based.
- **Examples:** `w2.0.box_1` (first W-2, box 1), `dependents.1.ssn` (second dependent’s SSN).
- **Use:** When an equation or rule depends on a single entry (e.g. “if w2.0.box_13_statutory_employee then …”) rather than a sum.

### 2.5 Multi-entry cell within a block (one box, multiple lines)

- **Syntax:** `block_id.index.field_name.sub_index.sub_field`. The `field_name` is a cell whose `type` is `"repeating"`; it has its own `item_cells` and `entries`.
- **Examples:**  
  - `w2.0.box_12.0.code`, `w2.0.box_12.0.amount` (first W-2, first Box 12 line)  
  - `w2.0.box_12.1.code`, `w2.0.box_12.1.amount` (first W-2, second Box 12 line)
- **Rule:** Use when a form box has multiple code/amount (or similar) rows. The block’s `item_cells` contains a key (e.g. `box_12`) with `"type": "repeating"`, `item_cells`, and `entries`.

### 2.6 Conditional / alternative sources (one line, multiple possible worksheets)

- **Syntax:** In `equation`, use natural-language “or” or “or” in the string; the evaluator must resolve which form/worksheet applies (e.g. from filing status or other inputs).
- **Example:** `"equation": "f1040_Line_16_Qualified_Dividends_Capital_Gain_Tax.25 or f1040_Tax_Computation or f1040_Line_16_Foreign_Earned_Income_Tax.6"` (line 16 tax can come from one of several worksheets).
- **Rule:** Document in `explanation` which instructions decide which worksheet applies; the engine may implement “or” as a conditional branch.

### 2.7 User entry vs. computed; overrides

- **manual_entry: true** → Value is **entered by the user** (or from an information-return block the user filled). No `equation` (or equation is ignored for input).
- **manual_entry: false** → Value is **computed** from `equation`. May still have **override_possible: true** so the user can override the computed result.
- **Rule:** Every cell has either a user source or an equation (or both if override is allowed). Information-return blocks are listed in `_user_entered_sources`; data from those blocks is treated as user-entered.

### 2.8 Recipient (taxpayer vs. spouse)

- **Where:** In blocks that support joint returns (e.g. `w2`, `1099_int`), each entry has a **recipient** field: `"taxpayer"` or `"spouse"`.
- **UI rule:** When a block item field is a recipient-style taxpayer/spouse selector, render it in the Qt editor as a compact horizontal pair of radio buttons labeled `T` and `S`, storing the underlying values `"taxpayer"` and `"spouse"` respectively.
- **Linking:** Equations can be extended to filter by recipient (e.g. sum only `w2.*.box_1` where `recipient == "taxpayer"`) when the form or another schedule requires separate totals. For 1040 line 1a, the current model sums all W-2s regardless of recipient.

### 2.9 Default and current value

- **default:** Fallback when no value has been entered or computed.
- **value:** Current value (for now set equal to default when building the model). At runtime, value is updated by user input or equation evaluation.
- **Display rule:** Leave unfilled manual-entry cells and block fields visually blank in the UI. Do not show placeholder text, default zeros, or unchecked booleans as if they were entered data.

### 2.10 Input semantics and control states

This section describes the **kind of user input** a form, worksheet, or block field may take. These categories are **not mutually exclusive**. A cell can be text **and** conditionally enabled, or a computed field can still allow a manual override, or a yes/no answer can make later fields irrelevant.

An LLM building the software should treat these as **input semantics**, not just display formatting.

#### 2.10.1 Primitive input types

- **Amount / currency:** Dollar amounts and other decimal numeric entries. Usually format `0.00`. Examples: wages, taxable interest, deductions, credits, payments.
- **Integer / count:** Whole-number inputs. Usually format `0`. Examples: counts, exemption-like quantities, whole-number worksheet steps.
- **Percent / rate:** Numeric inputs expressed as rates or percentages. Usually format `0.00%`.
- **Date:** Calendar dates entered as text or a date widget. Usually format `date`. Examples: tax-year begin/end dates, some basis or acquisition/disposition dates on attached forms.
- **Text:** Free text or structured text. Usually format `text`. Examples: names, addresses, SSNs, occupations, payer names, explanatory text fields.
- **Boolean yes/no:** A binary answer. Usually format `boolean`. Examples: digital assets yes/no, checkboxes, presidential campaign fund, “valid for employment” style indicators.

#### 2.10.2 Choice and exclusivity patterns

- **Single-choice set:** One choice from several options. Example: filing status on Form 1040. The UI may render this as several checkboxes or a radio/select control, but the data model should enforce that only one option is selected.
- **Independent checkboxes:** Multiple boolean inputs where more than one may be true at the same time.
- **Yes/no gate:** A boolean answer that controls whether later cells are relevant. Example: a “No” answer may make the next few lines not applicable.

#### 2.10.3 Editability and state

- **Manual-entry cell:** User types or selects the value directly.
- **Computed cell:** Value is produced by equation and should normally be read-only.
- **Overrideable computed cell:** Value is normally computed, but the user may replace it manually. The UI should visually distinguish an override from a formula result.
- **Read-only derived cell:** Display-only result; never directly editable by the user.

#### 2.10.4 Conditional enablement and relevance

- **Enabled only when prior facts allow it:** A field may be uneditable until another answer makes it relevant. Example: spouse fields should not accept entry when the filer is single.
- **Visible but disabled:** The UI may still show the field for completeness, but it should be non-editable.
- **Hidden or collapsed when irrelevant:** For long forms or blocks, the UI may hide inputs that are not currently applicable.
- **Not applicable vs blank:** These are different. Blank means “no value entered yet.” Not applicable means “this field should not be used for this taxpayer because a prior fact or rule excludes it.”

#### 2.10.4A Requiredness

- **Requiredness is separate from editability.** A cell can be editable but optional, editable and always required, or editable only when some prior fact makes it required.
- **Schema field:** Every form cell and every block `item_cell` should carry a `required_rule` field.
- **Allowed first-pass values for `required_rule`:**
  - `always` — the field is always required
  - `optional` — the field is not inherently required
  - **formula string** — the field is required only when the formula evaluates true
- **Formula language:** Reuse the same general expression language used for `equation` where practical, including references to same-form cells, cross-form cells, and boolean / numeric comparisons.
- **Examples:**
  - taxpayer first name: `always`
  - spouse first name: `filing_status_married_jointly or filing_status_married_separately`
  - U.S. address line when foreign address box is not checked: `use_foreign_address <= 0.0`
  - foreign address line when foreign address box is checked: `use_foreign_address > 0.0`
- **Debugging rule:** The Qt editor should expose the raw `required_rule` value in a visible debug column so rebuilds can inspect and refine the requiredness model.

#### 2.10.5 Conditional formulas

- **Branching by prior answer:** A value may come from different sources depending on another cell. Example: if a prior checkbox or filing-status answer changes which worksheet applies.
- **Branching by applicability:** Some cells are computed only if a prerequisite is met; otherwise the result is blank, zero, or not applicable depending on the IRS rule.
- **Mixed-source formulas:** A cell may sum or compare values from several locations, and the set of sources may depend on an earlier answer.

#### 2.10.6 Repeating and grouped inputs

- **Repeating block entries:** Zero to many copies of the same structure. Examples: multiple W-2s, multiple 1099-INTs, multiple dependents.
- **Repeating sub-items within one field:** A single field may contain multiple code/value pairs. Example: W-2 Box 12, where the taxpayer may need to enter none, one, or several `{code, amount}` rows.
- **Grouped entry object:** Some inputs belong together and should be entered as one logical unit even if stored across several fields. Examples: name components, address components, dependent rows, payer-identification fields.

#### 2.10.7 Recommended software interpretation

When building the software, classify each cell or block field along these axes:

- **storage type:** text, boolean, integer, decimal, percent, date, repeating object, or grouped object
- **entry mode:** manual, computed, overrideable, or read-only
- **choice mode:** free entry, single-choice, multi-choice, or yes/no gate
- **state rule:** always enabled, conditionally enabled, conditionally visible, or not applicable
- **cardinality:** single value, zero-to-many rows, or grouped multi-field object

#### 2.10.8 Examples for the federal package

- **Filing status:** single-choice set; one selection controls later relevance and editability.
- **Spouse fields:** text inputs, but conditionally enabled based on filing status and related facts.
- **Digital assets question:** yes/no gate; later instructions may depend on the answer.
- **Federal Information Worksheet name fields:** manual text inputs that feed computed 1040 cells.
- **1040 top-of-form taxpayer name:** computed text input on the form, potentially overrideable.
- **W-2 Box 1:** decimal amount inside a repeating block entry.
- **W-2 Box 12:** repeating `{code, amount}` input with zero-to-many rows.
- **Worksheet lines:** often numeric or boolean, but some are computed, some are manual, and some become irrelevant when earlier steps say to stop.

#### 2.10.9 Modeling rule for the LLM

When in doubt, model the **input semantics** explicitly in the software layer even if the current JSON schema only stores `format`, `manual_entry`, `override_possible`, `equation`, and block repetition. The LLM should not assume that `format` alone is enough to determine UI behavior. IRS forms often require additional logic for:

- exclusivity
- conditional enablement
- conditional visibility
- stop/skip behavior
- repeating code/value entry
- override coloring and auditability

### 2.11 Formula-driven vs. table-driven logic

Do not force every IRS result into one style of computation. The model must distinguish between:

- **Formula-driven logic:** Arithmetic, `min` / `max`, branching, worksheet flows, and rate-schedule math that can be evaluated directly once the needed parameters are known.
- **Table-driven logic:** IRS-published lookup tables where the result comes from a row, band, or published table entry and should be imported as data rather than rewritten as ad hoc logic.

**Storage rule:** Keep table-driven datasets in `reference-data/federal/2025/`, not inside `federal_1040_2025.json`.

**Current Federal 2025 table inventory:**

- **Ordinary income tax data:** Form 1040 `line 16`, the Tax Table, and the higher-income ordinary tax computation data.
- **Earned Income Credit table:** Used by the 2025 EIC worksheets and 1040 `line 27a`.
- **Simplified Method tables:** Table 1 and Table 2 for the Simplified Method Worksheet on 1040 lines `5a` and `5b`.
- **Capital-gain / dividend tax parameters:** Filing-status thresholds and constants used by the Qualified Dividends and Capital Gain Tax Worksheet and the Schedule D Tax Worksheet.

**Modeling rule:** If instructions say “use the table,” import the table. If instructions say “complete the worksheet” or apply bracket/rate math, keep the worksheet formulaic and store any shared thresholds or schedule data in `reference-data/federal/2025/` when that is cleaner than hardcoding constants into form cells.

---

## 3. Schema summary (for the JSON model)

- **Jurisdiction-year:** Top-level key (e.g. `"Federal 2025"`).
- **Forms:** Each form has `_meta` (e.g. `name`, **active**, **rank**) and **cells**. **active** (boolean): whether this form or worksheet is currently active. **rank** (float): display and **evaluation** order for forms and worksheets (e.g. `1.0`, `2.0`); use floats so worksheets can be slid in between later (e.g. `1.5` between `1.0` and `2.0`). Evaluate forms from lowest rank to highest rank so dependencies are available before dependents are computed. Each cell has a unique **cell key** and an **order** number; **every cell must have an order #**. Each cell has:
  - **order** (integer): 1-based position on the form (top-to-bottom, left-to-right). **Required:** every cell must have an order number; validation fails if any cell is missing it.
  - **format** (e.g. `0.00`, `0`, `date`, `boolean`, `text`)
  - **default** and **value**
  - **manual_entry**, **override_possible**
  - **required_rule** (`always`, `optional`, or a formula string telling the software when the field is required)
  - **equation** (if computed)
  - **description** (form/worksheet wording), **explanation** (longer clarification)
- **Equation evaluation:** Required. Evaluate equations in dependency order: across forms, use ascending `_meta.rank`; within a form, resolve referenced cells before dependent cells. When `order` is not enough to determine this, use dependency analysis. Circular references are errors and must be fixed.
- **Blocks:** Under a form, **blocks** hold 0-to-many entries (e.g. W-2s, 1099-INTs, dependents). Each block has:
  - **active** (boolean): whether this block is currently active (e.g. `true` for w2, 1099_int; `false` if not in use).
  - **multiple_copies** (boolean): whether the taxpayer can have multiple entries (e.g. `true` for W-2s, 1099s—one per employer/payer; `false` if at most one entry). Must be explicit so it is clear when multiple copies are possible.
  - **description**, **explanation**, **user_entered** (true for information returns)
  - **min_entries**, **max_entries**
  - **item_cells:** schema for one entry (each key is a field; each field can be a normal cell or `"type": "repeating"` with nested **item_cells** and **entries**). Each normal item cell should also carry a `required_rule`.
  - **entries:** array of objects (empty in the seed model)
- **Worksheets:** Modeled as **forms** with IDs like `f1040_Lines_5a_and_5b`. Their cells use line numbers (1, 2, 3, …) and reference the main form (e.g. `f1040.15`) or other worksheets as needed.

---

## 4. Process: Converting a PDF into a JSON form or block

This section is the **single reference** for how to add a new form, worksheet, or information return to the tax model. Use it for every new PDF. It can be amended as the process is refined.

**When to use:** Whenever you need to turn an IRS form PDF, a worksheet (from instructions), or an information-return PDF into a proper sheet (form or block) in the JSON.

**References:** Schema and field meanings → Section 3. Data linkage syntax → Section 2. Naming → Section 6.

### 4.1 Classify the PDF

| Type | What it is | Where the PDF lives | What you add in JSON |
|------|------------|---------------------|----------------------|
| **Form / Schedule** | IRS form with line/box numbers (e.g. 1040, Schedule 1, Schedule A) | `forms/` | A **form** with `_meta`, **cells** (and optionally **blocks**) |
| **Worksheet** | Step-by-step worksheet; may be in instructions, a publication, or standalone | `instructions/` (embedded in PDF), `publications/` (embedded), or **`worksheets/`** (standalone PDF) | A **form** with worksheet-style form ID and **cells** (line numbers) |
| **Information return** | Furnished by employer/payer (W-2, 1099-INT, 1099-DIV, 1098, etc.) | `information-returns/` | A **block** under the form that consumes it (e.g. under `f1040`) |

Decide which row applies before starting. For worksheets, check the **scope checklist (Section 1.1)** to see if the worksheet is currently in scope; if it is a standalone PDF, place it in `worksheets/`. If unclear, use the instructions or publication that references the PDF.

### 4.2 Before you start

- **Scope checklist:** Check **Section 1.1** (Scope checklist). For the time being, only add forms, worksheets, and blocks that are listed there. When adding a new item, add it to the checklist and then build it.
- **PDF in place:** Form/schedule in `forms/`; worksheet in instructions (embedded), in a publication (embedded), or as a standalone PDF in `worksheets/`; information return in `information-returns/`.
- **Jurisdiction-year:** The top-level key (e.g. `Federal 2025`) must exist in the JSON. Add it if missing.
- **Naming:** Use Section 6 for **form_id**, **block_id**, and **cell** keys. Stick to the conventions so references and tooling stay consistent.

### 4.3 Steps: Form or schedule (PDF with lines/boxes)

1. **Add the form.** Under the jurisdiction, add a key (e.g. `f1040s1`, `f1040sa`). Set `_meta.name` to the form’s official title and `_meta.active` to `true` or `false` (whether the form is currently in use).
2. **Add `cells`.** For **every** entry place on the PDF, add one cell—including **all areas above the first numbered line** (e.g. above line 1a on Form 1040). That means: form header/tax-year fields, taxpayer and spouse name and SSN, address, filing-status checkboxes, digital-asset question, dependent-table checkboxes and any “see instructions” checkboxes, and every other box or field the user can fill. Do not skip the top of the form.
   - **Cell key:** Use the line/box identifier from the form when present: line number + letter if any (e.g. `1a`, `2b`, `12e`). Some entry places on the form are **not numbered**; they must still be given a unique cell ID—ideally a **brief word description that does not start with a digit** (e.g. `standard_deduction`, `first_name`, `filing_status_single`). Must be unique on this form.
   - **Order #:** **Every cell must have an order number.** Assign a unique **order** (integer) to every cell: 1 for the first entry place on the form, 2 for the second, and so on in top-to-bottom (and left-to-right where relevant) form order. Export and display sort by this; validation fails if any cell is missing `order`.
  - **Required:** `order` (required for all cells), `format`, `default`, `value`, `required_rule`, and either `description` or `explanation` (Section 3).
   - **description:** Wording as it appears on the form (or a short label).
   - **explanation:** Clarification from instructions (where the value comes from, which schedule/worksheet, etc.).
   - **manual_entry:** `true` if the user enters it (or it comes from an information-return block); `false` if it is computed.
   - **override_possible:** `true` only if the instructions allow the user to override the computed value.
   - **equation:** If the line is a total or comes from another form/worksheet/block, set per Section 2 (e.g. `1a + 1b`, `f1040s1.10`, `sum(w2.*.box_1)`).
3. **Evaluation order.** Do not rely on JSON key order. Export and display sort by `order`. Equation evaluation is separate: evaluate forms by ascending **rank**, then evaluate cells in dependency order within each form.
4. **Dependencies.** If a form (e.g. 1040) has cells that are also collected on a lower-rank form or worksheet (e.g. Federal Information Worksheet, rank 1.0), set the higher-rank cell’s **equation** to that source cell (e.g. `f1040_Federal_Info_Worksheet.taxpayer_first_name`) and set **manual_entry: false**. Use **override_possible: true** only when the user may override the pulled value.
5. **Cross-references.** Every `equation` that references another form or block must use the correct syntax (Section 2). If the referenced form or block is not yet in the JSON, rely on the cell’s **default** and document the dependency (e.g. in `explanation` or in the process log).
6. **Check:** No duplicate cell keys; every equation reference is either valid or explicitly defaulted.
7. **Display and validation check.** Computed cells must evaluate correctly, and untouched manual-entry cells should remain visually blank until the user enters data.

### 4.4 Steps: Worksheet (from instructions, publication, or standalone PDF)

Worksheets may be found in the 1040 (or other) instruction PDF, in a publication PDF, or as a **standalone PDF in the `worksheets/` folder**. Use the same process for all three; ensure the worksheet is in the scope checklist (Section 1.1) before adding.

1. **Add the form.** Under the jurisdiction, add a form with a worksheet-style ID (e.g. `f1040_Lines_5a_and_5b`). Set `_meta.name` to the worksheet title and `_meta.active` to `true` or `false`. **Every cell must have an order number** (1, 2, 3, …).
2. **Add `cells`.** For each line in the worksheet, add a cell with a numeric-string key (`"1"`, `"2"`, …) when the worksheet has line numbers. If a worksheet has unnumbered entry places, give each a unique cell ID—ideally a **brief word description that does not start with a digit**.
3. **Equations.** From the instructions, set `equation` for each line (same-form refs or `form_id.cell_id` to pull from 1040/schedule/other worksheet). Use **description** / **explanation** from the instruction text.
4. **Link from the main form.** On the form that uses the worksheet result (e.g. 1040), set the target line’s `equation` to `worksheet_form_id.line` (e.g. `f1040_Lines_5a_and_5b.9`).
5. **Check:** No duplicate line keys; all references valid or defaulted.
6. **Display and validation check.** Worksheet references must evaluate correctly and remain explicit in the model.

### 4.5 Steps: Information return (W-2, 1099-*, 1098, etc.)

1. **Choose the parent form.** The return’s data flows into a form (e.g. 1040). Under that form, ensure a **blocks** object exists, then add a **block** with a lowercase, underscore ID (e.g. `w2`, `1099_int`, `1098`).
2. **Block metadata.** Set **active** (boolean), **multiple_copies** (boolean: `true` when the taxpayer can have multiple entries, e.g. multiple W-2s or 1099s; `false` when at most one), `description`, `explanation`, `user_entered: true`, and `min_entries` / `max_entries` (use `null` for “unlimited”).
3. **Add `item_cells`.** For each box or field on the return, add a key (e.g. `box_1`, `payer_name`, `recipient`) with `format`, `default`, `value`, `description`, `explanation`. For a box that allows multiple lines (e.g. W-2 Box 12: code + amount), use **type: "repeating"** with nested **item_cells** and **entries** (Section 2.5).
   - Each normal `item_cell` should also have `required_rule` using the same `always` / `optional` / formula convention as form cells.
4. **Seed data.** Set `entries: []` in the seed model.
5. **Link from the form.** On the consuming form, set the corresponding line’s `equation` to `sum(block_id.*.box_n)` (or the appropriate field) and `manual_entry: false`.
6. **User-entered list.** If not already present, add this block’s ID to the top-level **\_user_entered_sources** array.
7. **Check:** No duplicate keys in `item_cells`; `sum(block_id.*.field)` uses an existing block and field.
8. **Display and validation check.** Block aggregates and block-item references must remain explicit and readable in equations, e.g. `sum(w2.*.box_1)` or `w2.0.box_1`.

### 4.6 After adding any form or block

- **Validate.** Run a validator or equivalent validation pass to catch duplicate cells, unresolved references, circular dependencies, and missing `order` / `rank` values where required. Fix or document any missing references and rely on defaults as specified.
- **Format codes.** Ensure every cell’s `format` matches a known format so evaluation and UI display behave correctly.
- **Form order in display.** The UI sorts form cells by each cell’s **order** number. **Every cell must have an order #**; validation fails if any cell is missing it.
- **Equation order in evaluation.** The evaluator must compute forms in ascending **rank** and compute cells in dependency order within each form. If a dependency cannot be resolved yet, reorder evaluation; if a cycle exists, raise an error.
- **UI review behavior.** Blank inputs must stay blank, and computed cells must display computed results without being mistaken for manual entries.

### 4.7 Keeping this process clear

- **Amend this section** when the process changes. Prefer updating the steps above over adding one-off notes elsewhere.
- **Resolve ambiguity** by tying each step to the schema (Section 3) and linkage rules (Section 2). If something is still ambiguous, add one sentence to this section and, if needed, to Section 3 or 6.

---

## 5. Step-by-step methodology to build the federal individual package

This section applies the **process in Section 4** to the full federal individual package centered on Form 1040. Use this workflow with the attached PDFs, the YAML manifest, and the existing `federal_1040_2025.json` (or a copy) to extend or rebuild the package in dependency order.

### 5.0 Lightweight implementation roadmap

Use the phased steps below as the detailed build method, but keep this higher-level roadmap in mind when deciding what to do next.

1. **Establish the intake and source-of-truth layer first.**
   Build the Federal Information Worksheet, core source blocks, and the top-of-return facts that everything else depends on.
2. **Create concise publication summaries early.**
   Before the build gets deep, write or refresh shorthand summaries for the current publication set so publication-defined elections, thresholds, embedded worksheets, and cross-form dependencies are easy to search while forms are being wired.
3. **Close the core filing loop next.**
   Make the 1040, its core schedules, and the most common worksheets internally coherent enough that a typical personal return can be entered, reviewed, recalculated, and saved.
4. **Expand into common Premier-level attachments iteratively.**
   Add the next most common follow-on forms and worksheets in dependency order, prioritizing the ones that unlock realistic investor / homeowner / family-credit returns over niche branches.
5. **Use publications to finish rules, not to start structure.**
   The face of the form and its instructions should usually define the JSON structure first; publications then refine definitions, elections, exceptions, and edge-case math.
6. **Prefer closing dependency chains over adding isolated forms.**
   A strong LLM should look for the next missing upstream or downstream link that makes an existing path reliable, rather than simply adding whichever form is easiest.
7. **Treat the Qt app and the JSON model as one system.**
   When schema semantics such as requiredness, override policy, mirroring, or boolean choice behavior become important, update both the model contract and the editor behavior so the software remains rebuildable from the plan.

The roadmap is intentionally not too detailed. The point is to preserve priorities, dependency thinking, and product boundaries while still leaving room for a frontier model to decide the best next implementation move from the actual current state.

### Phase A: Build the manifest and build order

1. Start with `IRS_Federal_Individual_2025.yaml` as the canonical superset of forms, instructions, publications, worksheets, and information returns.
2. Create or refresh concise markdown summaries in `forms-instructions-and-publications/publication-summaries/` for the publication files that are in scope so their worksheets, elections, thresholds, and form cross-references are searchable before deeper form wiring begins.
3. Assign each item to a build group from Section 1.1: intake, blocks, main return, core schedules, core worksheets, common follow-on forms, business/investment forms, or specialty forms.
4. Assign provisional `_meta.rank` values so each form or worksheet is evaluated only after all of its dependencies are available.
5. Mark each item as one of:
   - **always-on core**
   - **conditionally active**
   - **authority only** (publication or instruction source, not a JSON form)

### Phase B: Map the main return structure from the PDFs

1. **Open Form 1040 PDF** (`forms/f1040.pdf`). List **every** entry place on the form in top-to-bottom order:
   - **Above the first numbered line:** Header/tax-year fields, taxpayer and spouse name and SSN, address (street, apt, city, state, ZIP), main home in U.S. checkbox, Presidential Election Campaign checkboxes, foreign-address fields (if applicable), filing-status checkboxes and any conditional name fields, Digital Assets Yes/No, Dependents table (or block) and any “more than four dependents” / “lived apart” checkboxes. Give each a cell with a word-style ID and an **order** number (1, 2, 3, …).
   - **Numbered lines:** Then list every line and subline (1a–1z, 2a, 2b, … through 38), each with the next **order** number.
2. For each cell (by order #), note:
   - **Label** on the form → use as **description**.
   - **Instructions** (from `instructions/i1040gi.pdf`) → use for **explanation** and to decide if the line is from another form, a worksheet, or a sum of information returns.
3. Mark which lines are **totals** (sum of other lines on the same form), which are **from schedules/worksheets**, and which are **from information returns** (W-2, 1099, 1098).

### Phase C: Build worksheets and identify others from instructions

1. **Build standalone worksheets first.** Any standalone worksheet listed in Section 1.1 must be fully built into the JSON from its PDF, not left as a stub. Build the **Federal Information Worksheet** from `worksheets/Federal Info Worksheet.pdf` before the main return so the 1040 can pull from it.
2. **Open General Instructions** (`instructions/i1040gi.pdf`). Search for “worksheet” and “Worksheet.”
3. List every worksheet named (e.g. “Simplified Method Worksheet—Lines 5a and 5b,” “Social Security Benefits Worksheet—Lines 6a and 6b”). For worksheets that are **in scope** (Section 1.1), ensure they are built into the JSON as above. For others, when adding later:
   - Give it a **form ID** (e.g. `f1040_Lines_5a_and_5b`, `f1040_Lines_6a_and_6b`).
   - Add it as a **form** under the jurisdiction-year in the JSON.
   - From the instructions (or its PDF in `worksheets/`), list the **line numbers** and operations. Add **cells** with **order**, **equation** where the instructions define a formula.

### Phase D: Map information returns to 1040 lines

1. For each information return type (W-2, 1099-INT, 1099-DIV, 1099-R, 1098, etc.):
   - Open the **blank form** from `information-returns/` (e.g. `f1099int.pdf`).
   - List **box numbers** and their meanings (from the form or its instructions).
2. Create or extend a **block** (e.g. `1099_int`) with **item_cells** matching those boxes. Include **recipient** (taxpayer/spouse) and **payer_name** (or similar) for identification.
3. For each 1040 line that is “total of X from information returns,” set **equation** to **sum(block_id.*.box_n)** and **manual_entry: false**. Example: 2b = `sum(1099_int.*.box_1)`.

### Phase E: Map schedules to 1040

1. For each core schedule (e.g. Schedule 1, 1-A, 2, 3, A, B, EIC, SE) open the **form** and **instructions**.
2. Add a **form** (e.g. `f1040s1`) with **cells** for each line. Use **equation** for totals and for references to other lines/schedules.
3. On the 1040, set the corresponding line’s **equation** to **schedule_id.line_or_cell** (e.g. `f1040s1.10`, `f1040s1.26`).

### Phase F: Build common follow-on forms

1. Build the common follow-on forms that the core return frequently depends on, such as `8812`, `8863`, `2441`, `8889`, `8949`, `8962`, `8995`, `8995a`, `1116`, `2210`, `8606`, `8959`, and `6251`.
2. Use the form PDF for line structure, the instructions for equations and carryovers, and publications where the instructions defer to them.
3. Wire each form into the 1040, a schedule, or a worksheet only after the referenced result cell is clearly identified.

Status note: `f1116` and `f2210` now exist as first-pass scaffolds in the master JSON and are wired to `Schedule 3 line 1` and `Form 1040 line 38`, respectively. `f1116` now also pulls common foreign-tax amounts from `1099-INT`, `1099-DIV`, a `foreign_tax_credit_items` overflow block, a generic `carryforward_records` block, newly added attachment forms `f1116sb` and `f1116sc` for carryover reconciliation and redeterminations, structured line `1a` gross-income support, **lines `4a`–`4b` default allocation from Schedule A × line `3f`**, and **lines `18`–`20` tied to Form 1040 taxable income and tax stack (with Form 1040-NR manual overrides on the Federal Information Worksheet)**. `f2210` includes safe harbor, **Part II waiver boxes A/B and worksheet-driven deferral** suppressing the automated penalty helper, dated estimated payments, withholding timing, and Schedule AI hooks. Remaining gaps include full QD/capital-gain limitation worksheets for `1116`, multi-form `1116` filing, full `1040-NR` column penalty math, and every `Pub. 514` / `Pub. 550` edge case. `f4952` adds an **optional passive 1099-MISC royalty path** when flagged; full investment-income classification still relies on user judgment and manual buckets.
4. Status note: `f8812` has now been incorporated from the downloaded 2025 form and its instructions. The model now includes the Additional Medicare Tax and RRTA Tax Worksheet for line `21`, Puerto Rico `499R-2/W-2PR` withholding inputs, RRTA `W-2 box 14` and `CT-2` source blocks, and a bona fide Puerto Rico fact flag for the line `27` branch. The remaining `8812` gaps are the Credit Limit Worksheet A/B chain, earned-income chart/worksheet synthesis for line `18a`, and the allocation of Form `8959` line `17` between the RRTA employee and employee-representative worksheet branches.

### Phase G: Build business, investment, and specialty forms

1. Build conditionally active schedules and forms such as `Schedule C`, `D`, `E`, `F`, `H`, `SE`, `4797`, `4562`, `4952`, `6198`, `7203`, `8582`, `2555`, `5329`, `5695`, and other YAML-listed forms as facts require.
2. Use publications to resolve basis, passive loss, depreciation, retirement, foreign income, and education-credit logic where the form instructions are not sufficient on their own. `Pub. 550` is specifically required for `Form 4952`, because investment-interest definitions, qualified-dividend / capital-gain elections, and attribution ordering are not fully recoverable from the form face alone.
3. Keep specialty forms below the core package in rank unless the instructions clearly require an earlier dependency.

### Phase H: Handle multi-entry boxes

1. If a form or information return has a **box that allows multiple lines** (e.g. W-2 Box 12: code + amount), model it as a **repeating** cell:
   - In the block’s **item_cells**, add a key (e.g. `box_12`) with **type: "repeating"**, **item_cells** (e.g. `code`, `amount`), and **entries: []**.
2. References use **block_id.index.field_name.sub_index.sub_field** (e.g. `w2.0.box_12.1.amount`).

### Phase I: Add descriptions and explanations

1. **description:** Match the exact or shortened wording on the form or worksheet.
2. **explanation:** One or two sentences from the instructions (which line to pull from, which box, which worksheet, or “user enters from form X”).

### Phase J: Wire dependencies by rank and validate links

1. **Wire dependencies.** For every higher-rank form, point any duplicated or sourced cells to the lower-rank form they come from (for example, 1040 rank 2.0 pulls from Federal Information Worksheet rank 1.0 with `equation: "f1040_Federal_Info_Worksheet.taxpayer_first_name"`, `manual_entry: false`, `override_possible: true`). Evaluate forms in **rank order** (lowest first), then evaluate cells in dependency order within each form.
2. For every cell with an **equation**, check that:
   - Referenced **form_id** and **cell_id** exist.
   - **sum(block_id.*.field)** uses a **block_id** and **field_name** that exist in that block’s **item_cells**.
3. Ensure no circular dependencies (e.g. line 9 depends on line 10). Resolve order (e.g. Schedule 1 line 10 before 1040 line 9) in the evaluation graph; if a cycle remains, treat it as a modeling error.

### Phase K: Validate against publications and export

1. For lines whose rules depend on detailed IRS interpretation, confirm the modeled logic against the cited publication as well as the form instructions.
2. Run validation to catch missing references, missing `order`, missing `rank`, unresolved worksheet outputs, and circular dependencies.
3. Review the model in the UI and in JSON form:
   - blank inputs remain blank
   - formulas evaluate correctly
   - cross-form and block references follow the naming rules in Section 6
4. Treat any unresolved or unsupported equation path as a modeling gap that must be closed before the package is considered complete.

---

## 6. Naming conventions

| Element | Convention | Example |
|--------|-------------|---------|
| Form ID (1040) | `f1040` | Main form |
| Form ID (schedule) | `f` + form number, no spaces | `f1040s1`, `f1040sa`, `f1040s2` |
| Worksheet form ID | `f1040_` + short descriptor from worksheet name | `f1040_Lines_5a_and_5b`, `f1040_Line_16_Qualified_Dividends_Capital_Gain_Tax` |
| Block ID (info returns) | Lowercase, underscores | `w2`, `1099_int`, `1099_div`, `dependents` |
| Cell key (1040) | Line number + letter if any | `1a`, `2b`, `12e`, `35a` |
| Cell key (unnumbered) | Brief word description, does not start with a digit | `standard_deduction`, `employer_ein` |
| Cell key (worksheet) | Line number (string), or word if unnumbered | `"1"`, `"9"`, `"18"` |
| **order** (cell) | Integer: 1-based position on form (top-to-bottom); **required** for every cell; sort key for display/evaluation support | `1`, `2`, `34` |
| **rank** (form _meta) | Float: display/sort order for forms and worksheets; use 1.0, 2.0, etc. so items can be slid in between (e.g. 1.5) | `1.0`, `2.0` |
| **active** (form/block) | Boolean: whether the form or block is currently active in the model | `true`, `false` |
| **multiple_copies** (block) | Boolean: whether multiple entries are possible (e.g. multiple W-2s, 1099s) | `true` for w2, 1099_int; `false` if at most one |
| Format codes | UI / evaluator data-format codes | `0.00`, `0`, `date`, `boolean`, `text` |

---

## 7. Key IRS materials (references)

- **Form 1040:** `forms/f1040.pdf`
- **1040 General Instructions (and embedded worksheets):** `instructions/i1040gi.pdf`
- **Schedules 1–3, A–E, etc.:** Listed in `IRS_Federal_Individual_2025.yaml` under Forms; PDFs in `forms/`.
- **Publications (e.g. 17, 915):** `publications/`; use when instructions say “see Pub. X.” Some publications contain embedded worksheets.
- **Information returns (W-2, 1099-INT, etc.):** `information-returns/`; no separate instructions in-app—user enters from furnished copies.
- **Worksheets:** (1) **YAML:** `IRS_Federal_Individual_2025.yaml` → **Worksheets** → `1040` lists worksheet names; (2) **embedded** in instruction or publication PDFs; (3) **standalone:** `worksheets/` (e.g. Federal Info Worksheet.pdf). Use the scope checklist (Section 1.1) to see which worksheets are currently in the build.
- **Reference data:** `reference-data/federal/2025/`; use for imported tax tables, rate schedules, EIC data, Simplified Method tables, and other lookup-driven artifacts.

---

## 8. Qt editor

The project should include a Qt desktop editor for working directly with the tax JSON model. The editor is a review and data-entry surface over the JSON; it does not replace the JSON schema or the dependency rules above.

### 8.1 Purpose

- Start, open, review, and edit a taxpayer-specific return JSON that is separate from the master tax-model JSON.
- Present the included forms and worksheets in a spreadsheet-like interface.
- Let the user review and edit current values while preserving the underlying JSON structure.
- Save taxpayer-specific return files under stable filenames in a dedicated returns folder.

### 8.2 Initial behavior

- The app should start with **no return loaded**. Do not automatically open the master model as the working return.
- The startup status text should make this clear (for example: “No return loaded. Choose New Return or Import Return.”).
- The left side shows a scrollable list of currently visible forms and worksheets.
- The main area shows the selected form or worksheet as a spreadsheet-like table.
- After a new or imported return is loaded, the initial visible sheets are limited to:
  - `f1040_Federal_Info_Worksheet`
  - `f1040`

### 8.2.1 Starting a return

- **New Return** should create a fresh in-memory return by copying the master template file `federal_1040_2025.json`.
- **Import Return** should open an existing taxpayer return JSON.
- The app should treat `federal_1040_2025.json` as the structural template and logic source, **not** as the user’s live return file.
- Taxpayer-specific return files belong in a dedicated project folder named `returns/`.
- The app should create `returns/` if it does not exist.
- Saved return JSON files should normally be written into `returns/`, not scattered elsewhere in the filesystem.

### 8.3 Required controls

- **New Return**: create a fresh taxpayer return from `federal_1040_2025.json`.
- **Import Return**: open an existing saved return JSON, preferably defaulting to `returns/`.
- **Save Return As**: save the current in-memory return under a filename in `returns/`.
- **Add Sheet**: add another included form or worksheet from the loaded JSON to the visible sheet list.
- **Remove Sheet**: remove the selected sheet from the visible list without deleting it from the JSON model.

### 8.4 Table behavior

- Show at least: `Cell ID`, `Description`, `Value`, `Format`, `Equation`, a debugging column that shows whether `override_possible` is `yes` or `no`, and a debugging column that shows the raw `required_rule`.
- Keep the table sorted by the cell `order` field.
- Manual-entry cells must be editable.
- Computed cells may be read-only unless override behavior is explicitly supported for that cell.
- If a computed cell is overrideable and the user changes it, downstream equations must use the overridden value, not the underlying formula result, until the override is cleared.
- If a cell is **currently required and still missing** (`required_rule` is `always` or its formula currently evaluates true, and the current value is still treated as not provided), the **Value column only** should receive a subtle light-yellow background as a visual cue.
- The yellow requiredness cue should clear once information has been provided for that field.
- If a value is entered in the correct cell but in an obviously wrong format, the **Value column text** should turn bright red as a non-blocking warning.
- The editor should preserve JSON types where possible:
  - booleans stay booleans
  - numeric fields stay numeric
  - text and dates stay strings unless a richer widget is added later

### 8.4.3 Input format validation cues

- Format validation should be **non-blocking** for text-style fields unless the parser already rejects the input for basic type reasons. The user may continue editing, but visibly invalid formats should be easy to spot.
- Invalid-format warnings should appear in the **Value column only** using bright red text.
- The app may also expose the reason as a tooltip or similar debugging aid.
- Current practical validation expectations include:
  - **SSN:** require `iii-ii-iiii` where each `i` is a digit, for example `123-45-6789`
  - **Phone number:** accept practical punctuation such as spaces, parentheses, periods, plus signs, and hyphens, but reject obviously malformed entries
  - **Phone extension:** digits only
  - **Email address:** standard email shape such as `name@example.com`
  - **Person-name fields:** allow practical personal-name conventions such as letters, spaces, hyphens, apostrophes, and concatenated letter-only names such as `MarkWayne`; reject obvious junk such as punctuation-only strings
- For now, the Qt app may infer these validations from known cell IDs and labels such as `*_ssn`, `*_phone`, `*_phone_ext`, `*_first_name`, `*_last_name`, `*_middle_initial`, `*_suffix`, and `*_full_name`.
- A rebuild should preserve the distinction between:
  - **missing required** input, shown with subtle yellow background, and
  - **present but badly formatted** input, shown with bright red text.

### 8.4.1 Boolean rendering rules

- Do not display editable booleans as raw `true` / `false` text when a richer control is available.
- For editable ordinary booleans, use a **checkbox** widget:
  - unchecked = `false`
  - checked = `true`
- For editable **one-hot boolean groups** where exactly one option should be selected, use **radio buttons** instead of separate checkboxes.
- Current required example: filing-status groups such as `filing_status_single`, `filing_status_married_jointly`, `filing_status_married_separately`, `filing_status_hoh`, and `filing_status_qss` should behave as one radio group on the source worksheet where the user makes the selection.
- Yes/no pairs stored as separate booleans may also be rendered as radio buttons when the pair is mutually exclusive.
- Recipient-style taxpayer/spouse selectors on block entries should not remain free-text when the schema clearly expects only those two values; they should render as a horizontal `T` / `S` radio pair and commit only `"taxpayer"` or `"spouse"`.

### 8.4.2 Boolean display rules for flow-through data

- On supporting forms that merely mirror a lower-rank source value, do **not** show live checkbox or radio controls just because the value is boolean.
- For non-editable mirrored boolean cells:
  - display a check mark for selected / true
  - display blank for unselected / false
- For one-hot groups, once one option is selected, the unselected rows in that group should be visually deemphasized across the row (for example, with a light gray background and dimmer text).
- The requiredness highlight rule still applies to boolean rows. If a checkbox, radio row, or mirrored boolean row is currently required and still missing, its **Value column / widget area only** should receive the same subtle light-yellow background.
- This dimming rule should apply both:
  - on the source sheet where the selection is made, and
  - on downstream sheets where the same choice flows through as display-only data.

### 8.5 Relationship to the model

- The UI only shows forms and worksheets that already exist in the loaded JSON.
- The sheet list should follow the form `rank` order from the JSON.
- The editor must not invent new schema fields on save.
- Load/save behavior must round-trip the JSON cleanly so the validator and future evaluator still work.
- The UI layer may infer richer controls such as radio groups from existing boolean naming patterns, but it must not rewrite the underlying JSON schema just to achieve better ergonomics.
- Override behavior in the UI must come directly from the model’s `override_possible` field rather than from ad hoc widget rules.

### 8.5.1 Override policy

- `override_possible` is not a general “let the user edit anything” switch. It exists to support scenario exploration and justified manual replacement of computed tax results.
- Basic identity and administrative facts that flow from `f1040_Federal_Info_Worksheet` into downstream forms should normally **not** be overrideable.
- In particular, mirrored values such as taxpayer name, spouse name, SSN, address, filing-status booleans, and similar top-of-return identity/status fields should be modeled with `override_possible: false` on downstream forms.
- The same rule applies to mirrored identity headers on attachment forms such as `f8949`: these are display-only copies of return identity, not scenario inputs.
- A rebuild should preserve the distinction between:
  - **source facts** entered once in the correct worksheet or block,
  - **mirrored read-only copies** of those facts on other forms, and
  - **overrideable computed tax-result cells** where scenario exploration is actually meaningful.

### 8.6 Planned expansion

- Add block editors for repeating inputs such as W-2s, 1099s, and dependents.
- Continue adding richer widgets for dates and numeric formats.
- Preserve live formula evaluation and dependency-aware recalculation in the UI.
- Expand the visible sheet set as more forms and worksheets are added to the JSON package.

---

## 9. Reconstruction-critical state

This section captures the implementation details most likely to be lost if the current master JSON and Python files are deleted. A future rebuild should preserve these choices unless there is a deliberate reason to change them.

When available, use `docs/build_manifest.json` together with this section. The manifest is the machine-readable snapshot; this section is the prose explanation.

### 9.1 Current naming and ordering conventions

- Form and worksheet IDs use stable JSON keys such as `f1040`, `f1040sd`, `f8949`, `f1040_Federal_Info_Worksheet`, and `f1040_Line_16_Qualified_Dividends_Capital_Gain_Tax`.
- Every form and worksheet has `_meta.rank` as a float. Rank controls display order and evaluation order.
- Every cell has an integer `order`. `order` is the primary in-form sort key and must match form order, not alphanumeric ID order.
- Unnumbered entry areas still receive explicit word-based cell IDs and must also receive `order`.
- Repeating user-entered sources live under `blocks` on the owning form, not as top-level forms.

### 9.2 Current forms and worksheets already modeled

- `f1040`
- `f1040_Federal_Info_Worksheet`
- `f1040_Lines_5a_and_5b`
- `f1040_Lines_6a_and_6b`
- `f1040_Tax_Computation`
- `f1040_Line_16_Foreign_Earned_Income_Tax`
- `f1040_Line_16_Qualified_Dividends_Capital_Gain_Tax`
- `f1040_Schedule_1_Line_1_State_Local_Tax_Refund`
- `f1040_Line_27a_EIC_Worksheet_A`
- `f1040_Line_27a_EIC_Worksheet_B`
- `f1040_Line_27a_EIC_Worksheet_B_Continued`
- `f1040sd`
- `f1040sd_Capital_Loss_Carryover`
- `f1040sd_28_Rate_Gain`
- `f1040sd_Unrecaptured_Section_1250_Gain`
- `f1040sd_Schedule_D_Tax`
- `f8949`

### 9.3 Current user-entered source blocks already modeled

- `dependents`
- `w2`
- `1099_int`
- `ssa_1099`
- `rrb_1099`
- `1099_div`
- `2439`
- `1099_b`
- `1099_da`
- `1099_s`
- `1099_r`

These are modeled as repeating blocks with `multiple_copies: true` where appropriate. A rebuild should preserve the rule that employer/payer-furnished forms are entered as source blocks first and only then summed or routed into tax forms.

### 9.4 Current cross-form wiring already established

- Top-of-Form 1040 identity fields pull from `f1040_Federal_Info_Worksheet`.
- `f1040.1a` pulls from `sum(w2.*.box_1)`.
- `f1040.2a` and `f1040.2b` pull from `1099_int`.
- `f1040.3a` and `f1040.3b` pull from `1099_div`.
- `f1040.6a` and the Social Security worksheet use helper totals fed by `ssa_1099` and `rrb_1099`.
- `f1040.25` is computed from W-2 withholding plus withholding from the currently modeled information returns.
- `f8949` exists as the transaction-entry surface for capital-asset sales.
- `f1040sd` lines `1b`, `2`, `3`, `8b`, `9`, and `10` pull from `f8949`.
- `f1040sd.13` pulls capital gain distributions from `1099_div`.
- `f1040sd.11` currently pulls the modeled `2439` amount and is only partially complete because other upstream forms are not yet built.
- `f1040.16` currently resolves from the Schedule D Tax Worksheet, the Qualified Dividends and Capital Gain Tax Worksheet, the Tax Computation Worksheet, or the Foreign Earned Income Tax Worksheet depending on which path applies.

### 9.5 Qt editor conventions that must survive a rebuild

- The Qt app is a view/edit surface over the JSON model, not a replacement for the model.
- At startup it should show **no loaded return**. After `New Return` or `Import Return`, the first visible sheets should be `f1040_Federal_Info_Worksheet` and `f1040`.
- `New Return` should copy from `federal_1040_2025.json`; `Import Return` should open an existing saved return; and saved returns should live in `returns/`.
- The sheet list must follow form `rank`.
- Form rows must follow cell `order`.
- Computed values must recalculate in dependency order.
- Cross-form flows already expected by the user, such as Federal Information Worksheet name fields flowing into Form 1040, must continue to work.
- If a user overrides a computed cell, the UI must visibly distinguish the override by text color.
- If a user overrides a computed cell, dependency evaluation must also respect that overridden value for downstream cells.
- The table should include an `Override?` debugging column so rebuilds can expose `override_possible` explicitly during testing.
- The table should also include a `Required Rule` debugging column showing the raw per-cell `required_rule` string.
- Cells whose `required_rule` is currently active and still missing should highlight only the `Value` column with a subtle light-yellow background, including boolean widget rows.
- Cells with obviously invalid entered formats should highlight the `Value` text in bright red, while still preserving the entered value for debugging and further editing.
- Editable booleans should render as checkboxes or radios rather than `true` / `false` text.
- One-hot boolean groups such as filing status should render as radio buttons on the source sheet and as display-only check-mark rows on mirrored sheets.
- Unselected rows in an active one-hot group should be slightly greyed out across the row, both on the source sheet and on mirrored flow-through sheets.
- Boolean display widgets are a UI convenience layered on top of the JSON model; the underlying JSON should remain explicit booleans rather than being collapsed into a single enum field unless the plan itself is intentionally revised.
- Mirrored Federal Information Worksheet identity/status fields on downstream forms should not be overrideable.
- Every form cell and block item cell should carry a `required_rule` field seeded at least to `optional`, with core identity / spouse / address requirements promoted to `always` or formulas as the model becomes more complete.
- Load and Save As must round-trip the JSON cleanly.

### 9.6 Known incompleteness that should not be mistaken for design intent

- Several `1040` lines still reference schedules that have not yet been built, including `Schedule 1`, `Schedule 1-A`, `Schedule 2`, `Schedule 3`, and `Schedule A`.
- `f8949` source-return blocks (`1099_b`, `1099_da`, `1099_s`) exist, but there is not yet an automatic transformation from those source blocks into `8949` rows.
- Some Schedule D lines still remain partially manual because upstream forms such as `4797`, `6252`, `4684`, `6781`, and K-1-driven forms are not yet modeled.
- The reference-data directory has been created, but the full 2025 Tax Table, EIC table, and Simplified Method tables still need to be imported.

### 9.7 Rebuild rule

If the codebase is rebuilt from markdown and PDFs alone, preserve the conventions in Sections `9.1` through `9.6` as the default target state. Do not “simplify” away ranks, orders, helper totals, block-based source intake, or the distinction between formula-driven and table-driven logic unless the plan is intentionally revised.

---

## 10. Output artifact

- **Primary:** `federal_1040_2025.json` — jurisdiction `Federal 2025`, containing the federal individual package defined by the build order in Section 1.1. Each cell has format, default, value, description, explanation, and equation (if computed).
- **Schema reference:** `docs/sample.json` — same structure with minimal examples and `_comments` describing every linkage type and convention above.
- **Reference data:** `reference-data/federal/2025/` — machine-readable lookup tables, rate schedules, and worksheet parameter tables used by the evaluator.
- **Build manifest:** `docs/build_manifest.json` — machine-readable snapshot of current modeled coverage, key flows, app expectations, and known gaps.

Using this plan with the attached forms, instructions, and publications, a deep-thinking LLM (or a human) can reconstruct and maintain the 1040 tax code as a single, consistent JSON model where every data link is explicit and traceable.
