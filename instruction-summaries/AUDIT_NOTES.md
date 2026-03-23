# Audit Notes

This file records source-backed mistakes, bug classes, and known instruction/model mismatches.

## Fixed

- `f1040_Federal_Info_Worksheet.taxpayer_age_1_1_2026`
- `f1040_Federal_Info_Worksheet.spouse_age_1_1_2026`
  Source basis:
  - `Federal Info Worksheet.pdf` explicitly shows `Date of birth` and `Age as of 1-1-2026`
  - `federal_1040_2025.json` already encoded `age_on_date(..., "2026-01-01")`
  Finding:
  - the Qt evaluator rewrote numeric self-references inside quoted strings, corrupting `"2026-01-01"` and forcing `age_on_date(...)` to return `0`
  Resolution:
  - fixed `src/tax_qt_app.py` so self-reference rewriting skips quoted strings
  Broader impact:
  - this bug class could also affect formulas using quoted date literals in helpers like `crossblocksum_date_range(...)`

- `f1040.26`
- `f2210.estimated_payment_period_a`
- `f2210.estimated_payment_period_b`
- `f2210.estimated_payment_period_c`
- `f2210.estimated_payment_period_d`
  Source basis:
  - these formulas use quoted date literals inside `crossblocksum_date_range(...)`
  Finding:
  - they were in the same evaluator risk class as the age formulas
  Resolution:
  - added executable tests confirming the quoted date boundaries now evaluate correctly

- `f1040sa.5e`
  Source basis:
  - `i1040sca.pdf` line `5e` and its State and Local Tax Deduction Worksheet
  Finding:
  - the model only used the simple `$40,000 / $20,000` cap and omitted the MAGI phaseout and worksheet floor behavior
  Resolution:
  - implemented the 2025 worksheet logic, including:
    - modified AGI branch
    - Puerto Rico / Form `2555` / Form `4563` adjustment path through Schedule `1-A` line `3`
    - post-floor halving rule for MFS
  Verification:
  - added executable tests for ordinary MFJ, excluded-income MAGI, and MFS phaseout cases

- `f1040.4a`
- `f1040.5a`
  Source basis:
  - `1099-R` block already captures gross distributions and has an `ira_sep_simple` discriminator
  Finding:
  - the gross-distribution lines were still manual, creating avoidable redundancy
  Resolution:
  - gross IRA distributions now flow automatically to `4a`
  - gross non-IRA pension / annuity distributions now flow automatically to `5a`
  Verification:
  - added executable regression test for mixed IRA and pension `1099-R` entries

- `f1040s1a.2b`
  Source basis:
  - description explicitly says `Amount from Form 2555 line 45`
  - the current model already has `f2555.foreign_earned_income_exclusion`
  Finding:
  - line `2b` remained manual despite a modeled upstream source
  Resolution:
  - wired `f1040s1a.2b` from `f2555.foreign_earned_income_exclusion`
  Verification:
  - added executable test covering the flow into Schedule `1-A`

- evaluator numeric-literal handling
  Finding:
  - after fixing quoted strings, the audit uncovered a second evaluator bug class: large bare integer constants such as `10000` and `500000` were being interpreted as self-cell references
  Resolution:
  - fixed `src/tax_qt_app.py` so only bare numeric tokens that are actual cell IDs on the current form are rewritten as self references
  Ongoing authoring rule:
  - when a formula needs numeric constants that could collide with numeric line IDs, prefer decimal literals like `1.0`, `10000.0`, and `500000.0`

## Remaining source-backed gaps

- `f1040s1a.2c`
  Source basis:
  - description says `Amount from Form 2555 line 50`
  Finding:
  - current upstream `f2555` modeling only exposes `foreign_earned_income_exclusion` and `housing_deduction`
  Status:
  - still needs a tighter line-level mapping for the line `50` amount

- `f1040s1a.2d`
  Source basis:
  - description says `Amount from Form 4563 line 15`
  Finding:
  - no corresponding modeled `f4563` form currently exists in the master JSON
  Status:
  - still a real upstream incompleteness rather than a formula bug

## Audit loop status

- first loop:
  - found and fixed quoted-string date evaluation bug
- second loop:
  - found and fixed SALT phaseout incompleteness
  - found and fixed numeric-literal/self-reference evaluator bug
  - reduced `1099-R` gross-line redundancy
- third loop:
  - verified the above fixes with executable tests
  - refreshed the Doe sample return with the current serializer and formula set

## Process rule going forward

- when a field label or instruction phrase implies a simple derivation from another captured fact, prefer a computed formula over a silent default
- when an instruction introduces a cap, threshold phaseout, or date-based branch, add it to `instruction-summaries/` and check whether the current model encodes the full rule, a partial rule, or an explicit override-only gap
