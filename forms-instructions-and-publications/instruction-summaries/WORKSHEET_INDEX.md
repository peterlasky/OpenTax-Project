# Worksheet Index

This file is the master worksheet inventory derived from the current instruction summaries, publication summaries, and modeled worksheet objects in `federal_1040_2025.json`.

## Status legend

- `modeled`: present as its own worksheet-like form in `federal_1040_2025.json`
- `embedded logic`: worksheet logic is implemented in another form or schedule, but not as its own worksheet object
- `gap`: summary evidence points to a worksheet path that is not currently modeled
- `ambiguous`: summary evidence implies a worksheet path, but the summary does not name it clearly enough yet
- `out of scope`: worksheet is real, but belongs to a return or regime not yet modeled in this project

## Master inventory

| Source summary | Worksheet reference | Owning form / scope | Status | Modeled ID | Notes / gap |
| --- | --- | --- | --- | --- | --- |
| `forms-instructions-and-publications/instruction-summaries/federal_info_worksheet.md` | `Form 1040 - Federal Information Worksheet` | `Form 1040` | `modeled` | `f1040_Federal_Info_Worksheet` | Intake-root worksheet. Source worksheet face also carries date-driven cues such as age as of `1-1-2026`. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Form 1040 - Simplified Method Worksheet (Lines 5a and 5b)` | `Form 1040` | `modeled` | `f1040_Lines_5a_and_5b` | Drives taxable pension / annuity amount. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Form 1040 - Social Security Benefits Worksheet (Lines 6a and 6b)` | `Form 1040` | `modeled` | `f1040_Lines_6a_and_6b` | Present as a standalone worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Form 1040 - Standard Deduction Worksheet for Dependents (Line 12e)` | `Form 1040` | `modeled` | `f1040_Line_12e_Standard_Deduction_Dependents` | Present as a standalone worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md`, `forms-instructions-and-publications/publication-summaries/p17.md` | `Form 1040 - Tax Computation Worksheet` | `Form 1040` | `modeled` | `f1040_Tax_Computation` | Also named in `p17.md` as part of the line `16` tax branch. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md`, `forms-instructions-and-publications/instruction-summaries/i2555.md` | `Form 1040 - Foreign Earned Income Tax Worksheet (Line 16)` | `Form 1040` | `modeled` | `f1040_Line_16_Foreign_Earned_Income_Tax` | Present as a standalone worksheet object; `i2555.pdf` explicitly points to this worksheet path. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Form 1040 - Qualified Dividends and Capital Gain Tax Worksheet (Line 16)` | `Form 1040` | `modeled` | `f1040_Line_16_Qualified_Dividends_Capital_Gain_Tax` | Present as a standalone worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Schedule 1 (Form 1040) - State and Local Income Tax Refund Worksheet (Line 1)` | `Schedule 1 (Form 1040)` | `modeled` | `f1040_Schedule_1_Line_1_State_Local_Tax_Refund` | Present as a standalone worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Schedule 1 (Form 1040) - Self-Employed Health Insurance Deduction Worksheet (Line 17)` | `Schedule 1 (Form 1040)` | `modeled` | `f1040_Schedule_1_Line_17_Self_Employed_Health_Insurance` | Present as a standalone worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Schedule 1 (Form 1040) - IRA Deduction Worksheet (Line 20)` | `Schedule 1 (Form 1040)` | `modeled` | `f1040_Schedule_1_Line_20_IRA_Deduction` | Present as a standalone worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Schedule 1 (Form 1040) - IRA Deduction Worksheet (Continued)` | `Schedule 1 (Form 1040)` | `modeled` | `f1040_Schedule_1_Line_20_IRA_Deduction_Continued` | Present as a standalone worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Schedule 1 (Form 1040) - Student Loan Interest Deduction Worksheet (Line 21)` | `Schedule 1 (Form 1040)` | `modeled` | `f1040_Schedule_1_Line_21_Student_Loan_Interest` | Present as a standalone worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md`, `forms-instructions-and-publications/publication-summaries/p596.md` | `Form 1040 - EIC Worksheet A (Line 27a)` | `Form 1040` | `modeled` | `f1040_Line_27a_EIC_Worksheet_A` | Publication `596` reinforces the need for worksheet-driven EIC handling. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md`, `forms-instructions-and-publications/publication-summaries/p596.md` | `Form 1040 - EIC Worksheet B (Line 27a)` | `Form 1040` | `modeled` | `f1040_Line_27a_EIC_Worksheet_B` | Publication `596` reinforces the need for worksheet-driven EIC handling. |
| `forms-instructions-and-publications/instruction-summaries/WORKSHEET_INDEX.md` | `Form 1040 - EIC Worksheet B (Continued)` | `Form 1040` | `modeled` | `f1040_Line_27a_EIC_Worksheet_B_Continued` | Present as a standalone worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/AUDIT_NOTES.md` | `State and Local Tax Deduction Worksheet` | `Schedule A (Form 1040)` | `embedded logic` | `` | Logic is implemented through `f1040sa.5e` and related Schedule A rules, but not modeled as a separate worksheet object. |
| `forms-instructions-and-publications/instruction-summaries/i2555.md` | `Form 6251 - Foreign Earned Income Tax Worksheet` | `Form 6251` | `gap` | `` | `i2555.pdf` explicitly directs `Form 6251` filers to this worksheet path, but no separate modeled worksheet object exists yet. |
| `forms-instructions-and-publications/publication-summaries/p590a.md` | `Publication 590-A - Appendix B Worksheet 1. Computation of Modified AGI (For use only by taxpayers who receive social security benefits)` | `IRA / Social Security coordination` | `gap` | `` | Special-case worksheet path named in `Pub. 590-A`; not separately modeled. |
| `forms-instructions-and-publications/publication-summaries/p590a.md` | `Publication 590-A - Appendix B Worksheet 2` | `IRA / Social Security coordination` | `gap` | `` | Special-case worksheet used to figure how much traditional IRA contribution can be deducted when Social Security interaction applies. |
| `forms-instructions-and-publications/publication-summaries/p590a.md` | `Publication 590-A - Appendix B Worksheet 3` | `IRA / Social Security coordination` | `gap` | `` | Special-case worksheet used to figure how much Social Security is taxable after IRA deduction interaction. |
| `forms-instructions-and-publications/publication-summaries/p915.md` | `Publication 915 - Worksheet 1. Figuring Your Taxable Benefits` | `Social Security / railroad benefits` | `modeled` | `f1040_Lines_6a_and_6b` | Modeled under the Form 1040 Social Security Benefits Worksheet path. |
| `forms-instructions-and-publications/publication-summaries/p915.md` | `Publication 915 - Worksheet 2. Figure Your Additional Taxable Benefits (From a Lump-Sum Payment for a Year After 1993)` | `Social Security / railroad benefits` | `gap` | `` | Lump-sum-election worksheet path is not separately modeled. |
| `forms-instructions-and-publications/publication-summaries/p915.md` | `Publication 915 - Worksheet 3. Figure Your Additional Taxable Benefits (From a Lump-Sum Payment for a Year Before 1994)` | `Social Security / railroad benefits` | `gap` | `` | Lump-sum-election worksheet path is not separately modeled. |
| `forms-instructions-and-publications/publication-summaries/p915.md` | `Publication 915 - Worksheet 4. Figure Your Taxable Benefits Under the Lump-Sum Election Method (Use With Worksheet 2 or 3)` | `Social Security / railroad benefits` | `gap` | `` | Lump-sum-election worksheet path is not separately modeled. |
| `forms-instructions-and-publications/publication-summaries/p523.md` | `Publication 523 - Worksheet 1. Find Your Exclusion Limit` | `home sale exclusion` | `gap` | `` | Exact worksheet title confirmed from source publication; no modeled worksheet object exists yet. |
| `forms-instructions-and-publications/publication-summaries/p523.md` | `Publication 523 - Worksheet 2. How To Figure Your Gain or Loss` | `home sale gain/loss` | `gap` | `` | Exact worksheet title confirmed from source publication; no modeled worksheet object exists yet. |
| `forms-instructions-and-publications/publication-summaries/p523.md` | `Publication 523 - Worksheet 3. Determine if You Have Taxable Gain` | `home sale taxable gain / reporting` | `gap` | `` | Exact worksheet title confirmed from source publication; no modeled worksheet object exists yet. |
| `forms-instructions-and-publications/publication-summaries/p555.md` | `allocation worksheet logic comparable to Form 8958` | `community-property allocation` | `gap` | `` | No `Form 8958` or equivalent allocation worksheet logic is currently modeled. |
| `forms-instructions-and-publications/publication-summaries/p596.md` | `Publication 596 - Worksheet 1. Investment Income` | `EIC special cases` | `gap` | `` | Required for certain EIC cases listed in `Pub. 596`; no modeled worksheet object exists yet. |
| `forms-instructions-and-publications/publication-summaries/p596.md` | `Publication 596 - Worksheet 2. Worksheet for Line 4 of Worksheet 1` | `EIC / Form 8814 Alaska dividend special case` | `gap` | `` | Special-case support worksheet named in `Pub. 596`; no modeled worksheet object exists yet. |
| `forms-instructions-and-publications/publication-summaries/p505.md` | `Form 1040-SS estimated-tax worksheet path` | `Form 1040-SS` | `out of scope` | `` | Real worksheet path, but this project currently models the `Form 1040` family rather than `Form 1040-SS`. |

## Immediate conclusions

- The currently named `Form 1040` worksheet family is mostly present and modeled.
- The strongest worksheet coverage gaps inside the current federal individual domain are now explicit rather than ambiguous: `Form 6251` foreign-earned-income tax worksheet, `Pub. 590-A` Appendix B IRA/Social Security worksheets, `Pub. 915` lump-sum Social Security worksheets, `Pub. 596` investment-income worksheets, `Pub. 523` home-sale worksheets, and community-property allocation logic comparable to `Form 8958`.
- The remaining weakness is no longer worksheet naming ambiguity in the audited summaries; it is actual modeled-coverage gaps.

## Next inventory rule

When a summary mentions a worksheet path without the exact worksheet title, that summary should be upgraded before the inventory is treated as complete. This pass resolved the current ambiguous worksheet references by naming the relevant worksheets or source-publication worksheet paths. Each future worksheet entry should record:

- exact worksheet title if known
- owning form or schedule
- whether it is standalone or embedded
- modeled ID if present
- whether the evidence came from summary only or summary plus source PDF

## Review rule

When a worksheet name contains a direct computational cue such as an age date, threshold date, cap, or line-reference dependency, the model should either:

- encode that computation explicitly, or
- record a deliberate manual-entry exception in `AUDIT_NOTES.md`
