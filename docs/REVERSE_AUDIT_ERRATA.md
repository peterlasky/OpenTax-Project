# Reverse Audit Errata

Generated: `2026-04-02`

## Scope

This document records a separate reverse-audit pass over `federal_1040_2025.json`.

This pass treated the master JSON as the object being checked, not as authority. It compared modeled cells, line semantics, activation rules, carryouts, and repeating structures against primary IRS sources. It did not edit the JSON.

Audited slices in this pass:

- `f1040`
- `f1040sa`
- `f1040s1`
- `f1040s2`
- `f1040s3`
- `f1040sb`
- `f1040sd`
- `f1040sd_28_Rate_Gain`
- `f1040sd_Capital_Loss_Carryover`
- `f8812`
- `f1116`
- `f1116_Questionnaire`
- `f1116sb`
- `f1116sc`
- `f2441`
- `f8283`
- `f8949`
- `f8962`
- `f1040se`
- `f2210`
- `f4952`

Primary-source order used:

1. IRS form or schedule PDF
2. IRS instructions
3. IRS publications when the instructions depended on them
4. Project summaries only as navigation aids

Finding classes used:

- `error`
- `likely error`
- `ambiguous`
- `missing support`
- `needs judgment`

## Highest-Priority Findings

These are the findings most likely to produce mathematically wrong output rather than merely incomplete or weakly documented modeling.

### `f1116`

- `error` | `f1116.19`
  Line 19 does not implement the IRS rule correctly when line 18 is zero and can also divide by zero. The current expression returns `0` when IRS logic calls for `1` in at least one branch.
  Sources: IRS Instructions for Form 1116 (2025), limitation ratio discussion.

- `likely error` | `f1116.3f`
  The ratio is not capped at `1`, even though the instructions say not to enter more than `1`.
  Sources: IRS Instructions for Form 1116 (2025), line 3f.

- `likely error` | `f1116.4a`, `f1116.4b`
  Interest-allocation lines are modeled as broad Schedule A times-ratio shortcuts, but the instructions require narrower allocation methods and, for some cases, an asset method.
  Sources: IRS Instructions for Form 1116 (2025), lines 4a and 4b; Pub. 514 dependency.

### `f8962`

- `likely error` | `f8962.household_income_pct_fpl`
  The model appears to preserve decimals on the poverty-percentage step, while the instructions say to multiply by 100 and drop digits after the decimal.
  Sources: IRS Instructions for Form 8962 (2025), Worksheet 2.

- `likely error` | `f8962.applicable_figure`, `f8962.annual_contribution_amount`
  The cell explanation suggests entry as a percent such as `8.50`, while the IRS table is expressed as a decimal such as `0.0850`. That creates a 100x interpretation risk.
  Sources: IRS Instructions for Form 8962 (2025), Table 2 and line 8a.

- `likely error` | `f8962` monthly / annual SLCSP totals
  The model sums SLCSP across all `1095-A` entries, but the instructions say not to add column B across multiple same-state policies in the covered-family case.
  Sources: IRS Instructions for Form 8962 (2025), line 11 column (b) and lines 12 through 23 column (b).

- `likely error` | `f8962.26`
  The alternative calculation for year of marriage special rule is not modeled for the branch where line 24 exceeds line 25 and line 26 should be zero.
  Sources: IRS Instructions for Form 8962 (2025), line 26.

### `f2441`

- `likely error` | `f2441.8`
  The applicable-percentage logic appears to use a smooth decrement formula instead of the official bracket table, which misplaces at least some boundary values.
  Sources: IRS Instructions for Form 2441 (2025), Worksheet A percentage table.

- `likely error` | `_f2441_deemed_income`
  Student/disabled earned-income deeming is modeled annually instead of month by month, and does not appear to enforce the joint-month limitation correctly.
  Sources: IRS Instructions for Form 2441 (2025), lines 4 and 5.

- `likely error` | `f2441.12`
  The model sums all dependent-care benefits from W-2 box 10, but the instructions exclude excess amounts already included in wages to a specified extent.
  Sources: IRS Instructions for Form 2441 (2025), line 12.

### `f1040sd`

- `error` | `f1040sd.21`
  The line 21 formula uses `max(16, -capital_loss_limit())`, which can return a gain instead of zero / allowable loss behavior when line 16 is positive.
  Sources: IRS Schedule D instructions (2025), capital loss discussion and line 21 context.

## Detailed Findings By Form

### `f1040`

- `likely error` | `f1040.4b`
  IRA taxable amount is tied to the worksheet for Form 1040 lines 5a/5b, which is a pension/annuity worksheet rather than an IRA-specific taxable-amount path.
  Sources: Form 1040 lines 4 and 5; project worksheet naming and cell wiring.

- `missing support` | `f1040.7a`, `f1040.7b`
  Capital gain/loss remains materially manual rather than being fully derived from Schedule D / Form 8949 flows.
  Sources: Form 1040 instructions, capital gain references.

- `ambiguous` | `f1040.13a`
  QBI deduction still allows a compatibility helper path instead of relying only on Form 8995 / 8995-A.
  Sources: project JSON and cell explanation.

- `ambiguous` | `f1040.19`
  Child tax credit / other dependent credit still allows manual helper amounts to exceed the modeled Schedule 8812 carryout.
  Sources: Form 1040 / Schedule 8812 workflow and project equation.

- `missing support` | `f1040.eic_qualifying_children_count`
  EIC qualifying-child logic is still a manual helper rather than fully derived from dependent facts.
  Sources: Form 1040 / EIC instructions and project helper note.

### `f1040sa`

- `missing support` | `f1040sa.9`
  Investment interest depends completely on a still-partial Form 4952 implementation.
  Sources: Schedule A line 9; Form 4952 / Pub. 550 dependency.

- `ambiguous` | `f1040sa.5a` through `f1040sa.5e`
  SALT logic includes modeled cap behavior, but most sourcing and election facts are still manual and rely on user discipline.
  Sources: Schedule A instructions and project cell structure.

- `ambiguous` | `f1040sa.8d`
  Reserved mortgage-interest line is hard-coded to zero. This is acceptable only if the official form continues to leave that line unused.
  Sources: Schedule A (2025).

- `ambiguous` | `f1040sa.itemized`
  `itemized` is a synthetic alias rather than a printed-form line.
  Sources: project JSON.

### `f1040s1`, `f1040s2`, `f1040s3`

- `ambiguous` | `f1040s1.22`
  Reserved line hard-coded to zero.
  Sources: Schedule 1 (2025).

- `needs judgment` | `f1040s2.21`
  The equation includes line 20 in the subtotal, while the printed 2025 Schedule 2 line 21 text appears to name lines 4, 7 through 16, 18, and 19 only.
  Sources: Schedule 2 (2025) line 21 text.

- `ambiguous` | `f1040s2.17`
  Synthetic alias retained for compatibility even though it does not represent the official printed line-17 structure.
  Sources: Schedule 2 printed layout versus project JSON.

- `likely error` | `f1040s3.8` explanation
  The explanation references the wrong Form 1040 target line even though the equation route appears correct.
  Sources: Form 1040 and project explanation text.

- `ambiguous` | `f1040s3.15` explanation
  The explanation mixes the correct printed target with stale internal line-number language.
  Sources: Form 1040 line 31 and project explanation text.

- `ambiguous` | `f1040s3.6e`
  Reserved line hard-coded to zero.
  Sources: Schedule 3 (2025).

### `f8812`

- `missing support` | `f8812.4`, `f8812.6`, dependent TIN logic
  The 2025 valid-SSN / ITIN / ATIN rules for CTC versus ODC are not fully enforced in the model.
  Sources: Schedule 8812 instructions (2025), valid SSN discussion.

- `missing support` | `f8812.18a` and earned-income worksheet path
  Earned-income synthesis still has acknowledged gaps, including optional-farm-method handling and some specialized income adjustments.
  Sources: Schedule 8812 instructions and project notes.

- `missing support` | `f8812.21`
  The allocation of Form 8959 line 17 within the worksheet path remains partially manual.
  Sources: Schedule 8812 instructions and project notes.

- `needs judgment` | `f8812._meta.activation_rule`
  The activation rule uses bare cell ids in a way that depends on implicit scoping behavior.
  Sources: project JSON activation rule.

### `f1040sb`

- `likely error` | `f1040sb.2`
  Part I line 2 is described as a seller-financed / accrued-interest bucket, but the IRS treats seller-financed mortgage interest as a line-1 listing issue and line 2 more narrowly as a netting / adjustment result.
  Sources: IRS Instructions for Schedule B (2025), Part I.

- `likely error` | `f1040sb.3`
  The model uses line 3 as total taxable interest, but the 2025 Schedule B instructions describe line 3 as the savings-bond education exclusion cross-reference.
  Sources: IRS Instructions for Schedule B (2025), Part I line 3.

- `likely error` | `f1040sb` Part II row naming
  Ordinary-dividend detail rows are named `line_4_*`, but the printed ordinary-dividend listing line is line 5.
  Sources: IRS Instructions for Schedule B (2025), Part II line 5.

- `missing support` | `f1040sb` row counts
  The model caps payer rows instead of representing the IRS attach-statement workflow.
  Sources: IRS Instructions for Schedule B (2025), attach-statement guidance.

- `likely error` | `f1040sb.7a`
  A single boolean is used where the printed Part III asks two separate line-7a questions.
  Sources: IRS Instructions for Schedule B (2025), Part III.

- `ambiguous` | `f1040sb.7b`
  The field is described too broadly as foreign-country information, while the instructions tie it specifically to the FinCEN filing context.
  Sources: IRS Instructions for Schedule B (2025), line 7b.

- `missing support` | `f1040sb._meta.activation_rule`
  Filing triggers do not cover all the non-threshold reasons IRS requires Schedule B.
  Sources: IRS Instructions for Schedule B (2025), general filing conditions.

### `f1040sd` and related Schedule D worksheets

- `error` | `f1040sd.21`
  See highest-priority section above.

- `likely error` | `f1040sd.4`
  The description includes Form 4684, but the equation omits any `f4684` carryout.
  Sources: Schedule D instructions (2025), general reporting guidance.

- `likely error` | `f1040sd.11`
  Same issue as line 4: description names Form 4684, equation does not include it.
  Sources: Schedule D instructions (2025), general reporting guidance.

- `missing support` | `f1040sd_28_Rate_Gain.5`
  Long-term carryover worksheet line 5 omits the Schedule K-1 (Form 1041) box 11 code D component named in the instructions.
  Sources: Schedule D instructions (2025), 28% Rate Gain Worksheet.

- `missing support` | `f1040sd_28_Rate_Gain.1`, `.3`
  Collectibles and other worksheet sources remain manual rather than being derived from the underlying forms.
  Sources: Schedule D instructions (2025), 28% Rate Gain Worksheet.

- `ambiguous` | `f1040sd.qof_disposed_any` explanation
  The explanation overstates the consequence as simply attaching Form 8949, while the IRS instructions tie the issue more broadly to Form 8949 instructions and Form 8997.
  Sources: Schedule D instructions (2025), QOF disposal note.

### `f8949`

- `missing support` | direct Schedule D exception path (`direct_schedule_d_1a`, `direct_schedule_d_8a`)
  The direct-reporting exception for Schedule D lines 1a and 8a does not appear to enforce all IRS conditions, including some 1099-B / 1099-DA boxes and QOF-related exceptions.
  Sources: Schedule D instructions (2025), lines 1a and 8a exception discussion.

- `missing support` | `f8949` versus direct Schedule D reporting
  There is no model-level protection against counting the same economic disposition both on direct Schedule D exception lines and again in Form 8949 blocks.
  Sources: Schedule D instructions (2025), do-not-double-report rule.

- `ambiguous` | `f8949.blocks.*.gain_loss`
  Column (h) is a standalone editable field rather than a derived amount tied to proceeds, basis, and adjustment.
  Sources: Form 8949 / Schedule D instructions cross-reference.

- `ambiguous` | checkbox-family handling
  The data model uses separate blocks for each checkbox family but does not itself encode “one checkbox family per printed copy” beyond preview/export logic.
  Sources: Form 8949 printed structure and project JSON.

- `ambiguous` | `f8949.blocks.carryforward_records`
  Generic carryforward storage is hosted under Form 8949 even when used by unrelated forms such as `f1116` and `f4952`, which is semantically awkward for auditability.
  Sources: project JSON cross-references.

### `f1116`, `f1116sb`, `f1116sc`, `f1116_Questionnaire`

- `error` | `f1116.19`
  See highest-priority section above.

- `likely error` | `f1116.3f`
  See highest-priority section above.

- `likely error` | `f1116.3d`
  Line 3d appears to be forced from line 1a plus adjustments rather than representing the broader gross-foreign-income concept the instructions describe.
  Sources: IRS Instructions for Form 1116 (2025), lines 3d and 3e.

- `likely error` | `f1116.3e`
  Gross income from all sources appears not to systematically add back excluded foreign earned income and other instruction-required pieces.
  Sources: IRS Instructions for Form 1116 (2025), lines 3d and 3e.

- `likely error` | `f1116.4a`, `f1116.4b`
  See highest-priority section above.

- `missing support` | country / column structure
  The model does not represent the full per-country / per-category column structure required by the IRS form in the general case.
  Sources: IRS Instructions for Form 1116 (2025), line i and category discussions.

- `missing support` | treaty and 901(j) repeatability
  The model allows only one resourced-by-treaty and one 901(j)-style path at a time, while the IRS regime can require separate forms by treaty amount or sanctioned country.
  Sources: IRS Instructions for Form 1116 (2025), category guidance.

- `ambiguous` | `f1116sb` section-951A checkbox handling
  The current Schedule B handling for the reserved / section 951A checkbox family may not align cleanly with the official 2025 attachment.
  Sources: project JSON, tests, and IRS instruction category guidance.

- `needs judgment` | `f1116_section_951a.10`
  The line-10 carryover path excludes the Schedule B total used for other categories; it is not clear that the IRS treats section 951A as an exception here.
  Sources: IRS Instructions for Form 1116 (2025), line 10 / Schedule B discussion.

- `ambiguous` | carryforward-record storage path
  FTC carryovers are pulled through generic carryforward infrastructure stored under Form 8949, which is functionally possible but semantically confusing.
  Sources: project JSON equations and cross-references.

- `missing support` | passive-only 1099 sourcing
  1099-based foreign-tax helpers are passive-category only and do not support broader non-passive category sourcing.
  Sources: IRS Instructions for Form 1116 (2025) and project equations.

- `ambiguous` | questionnaire and filing policy
  The questionnaire / filing logic appears to include product-level guardrails rather than being a literal transcription of “who must file” law.
  Sources: project activation rules and tests.

- `missing support` | `f1116sc`
  Schedule C remains structurally simplified and not line-by-line equivalent to the official attachment.
  Sources: project JSON and IRS instructions on foreign tax redeterminations.

### `f8962`

- `likely error` | top-of-form checkbox / `alternative_calculation_for_marriage`
  The mapped checkbox may conflate the MFS domestic-abuse / spousal-abandonment certification with the separate alternative-calculation-for-year-of-marriage concept.
  Sources: IRS Instructions for Form 8962 (2025), line A and Part V.

- `missing support` | missing Line A cell
  The model does not appear to expose the IRS line-A certification explicitly.
  Sources: IRS Instructions for Form 8962 (2025), line A.

- `likely error` | `f8962.household_income_pct_fpl`
  See highest-priority section above.

- `likely error` | `f8962.applicable_figure`, `f8962.annual_contribution_amount`
  See highest-priority section above.

- `likely error` | monthly / annual SLCSP handling
  See highest-priority section above.

- `likely error` | `f8962.26`
  See highest-priority section above.

- `missing support` | shared-policy allocation defaults
  When shared-policy allocation is triggered, zero / missing allocation percentages can default to 100% instead of the IRS 50/50 fallback in at least one important situation.
  Sources: IRS Instructions for Form 8962 (2025), Part IV allocation.

- `missing support` | QSEHRA / ICHRA / MEC / unpaid-premium rules
  The model has some related flags but does not fully propagate them into the monthly PTC logic.
  Sources: IRS Instructions for Form 8962 (2025), eligibility and coverage-family rules.

- `ambiguous` | activation rule
  Activation partly depends on computed `annual_ptc`, which creates evaluation-order ambiguity relative to a cleaner factual-filing trigger.
  Sources: project activation rule and IRS “who must file” context.

### `f2441`

- `ambiguous` | qualifying-person full-year-resident checkbox
  A “full year resident” field is retained for layout reasons but does not align cleanly with the line-2 columns described in the instructions.
  Sources: IRS Instructions for Form 2441 (2025), line 2 columns.

- `ambiguous` | provider household-employee / tax-exempt field naming
  The cell id says `is_tax_exempt` while the explanation describes the household-employee checkbox, which weakens traceability.
  Sources: IRS Instructions for Form 2441 (2025), line 1 columns.

- `likely error` | `f2441.8`
  See highest-priority section above.

- `likely error` | deemed-income monthly logic
  See highest-priority section above.

- `missing support` | earned-income sourcing
  Earned income is still largely driven by W-2 / manual paths rather than the fuller rule set in the instructions.
  Sources: IRS Instructions for Form 2441 (2025), lines 4 and 5.

- `likely error` | `f2441.12`
  See highest-priority section above.

- `ambiguous` | `f2441.10`
  The credit-limit worksheet mapping depends on assumptions about how Schedule 3 amounts are packed in the master model and may diverge if those aliases drift.
  Sources: IRS Instructions for Form 2441 (2025), credit-limit worksheet and project wiring.

- `missing support` | attachment cases
  More-than-three providers / qualifying persons are represented only by flags, not by expandable attached detail.
  Sources: IRS Instructions for Form 2441 (2025), line 1 / line 2 attachment guidance.

### `f1040se`

- `likely error` | `f1040se.21`
  The cell mixes Part I property-column totals with Form 4835 carryout, which does not preserve the printed Schedule E line structure.
  Sources: Schedule E printed structure and project equation.

- `likely error` | Form 4835 carryout into `f1040se.21`
  Form 4835 is documented as landing on a later Schedule E line, but the model folds it into the same aggregate as Part I line 21 column totals.
  Sources: project explanations and Schedule E / Form 4835 workflow.

- `missing support` | three-property limit
  The model hard-caps Schedule E Part I to three rental / royalty columns and does not model the extra-page workflow.
  Sources: Schedule E printed layout and continuation expectations.

- `missing support` | five-passthrough limit
  The model hard-caps passthrough activities and collapses excess-activity behavior.
  Sources: Schedule E Parts II and III instructions.

- `missing support` | Part II versus Part III collapse
  Estates / trusts and partnership / S-corporation items are materially collapsed in a way that loses printed-form fidelity.
  Sources: Schedule E Parts II and III.

- `missing support` | limitation stack
  At-risk / passive / other Schedule E limitation interactions remain scaffold-level rather than full-form.
  Sources: Schedule E line structure and project equations.

### `f8283`

- `likely error` | `f8283.required_to_file_likely`
  The filing trigger uses aggregate noncash contributions over `$500`, but the IRS filing test depends on each item or group of similar items rather than just the grand total.
  Sources: IRS Instructions for Form 8283 (Rev. Dec. 2025), who must file and similar-items rules.

- `likely error` | `f8283.section_b_required_likely`
  Section B is triggered from aggregate over `$5,000`, but the real rule depends on per-item / group-of-similar-items thresholds and special cases.
  Sources: IRS Instructions for Form 8283, section-selection rules.

- `likely error` | Section A item explanations
  Section A row explanations are framed around Form 1098-C vehicle donations, but IRS Section A covers far more than vehicle-only paths.
  Sources: IRS Instructions for Form 8283, Section A coverage.

- `missing support` | overall form coverage
  The PDF map is only lightly populated relative to the full IRS form, confirming that most of the appraisal / donee / valuation structure is not modeled.
  Sources: project PDF field map and Form 8283 structure.

- `missing support` | `f8283.schedule_a_12`
  Schedule A carryout is a lumped total and does not preserve Section A / B, similar-item, or donee separation.
  Sources: IRS Instructions for Form 8283 and Schedule A noncash-donation workflow.

- `likely error` | 1098-C claimed-deduction logic
  The 1098-C carryout uses claimed deduction amount without modeling all IRS vehicle-donation limits tied to gross proceeds and exceptions.
  Sources: IRS Instructions for Form 8283 and vehicle-donation rules.

### `f2210`

- `likely error` | `f2210.1`
  The model ties line 1 to Form 1040 line 24 instead of the line 22 reference stated in the 2025 IRS instructions.
  Sources: IRS Instructions for Form 2210 (2025), Part I line 1.

- `ambiguous` | `f2210.safe_harbor_exception_met`
  The helper includes a line-4-based `< 1000` branch in addition to the line-7-based test, which does not match the way the IRS describes the no-penalty exception.
  Sources: IRS Instructions for Form 2210 (2025), exceptions.

- `missing support` | `f2210.3`
  The 2025 section-1062 / Notice 2026-3 adjustment is not modeled.
  Sources: IRS Instructions for Form 2210 (2025), line 3.

- `likely error` | `f2210.19` penalty engine
  The penalty engine does not replicate the official multi-rate-period Section B worksheet structure and may diverge for mid-period payments.
  Sources: IRS Instructions for Form 2210 (2025), Part III Section B worksheet and Table 2.

- `ambiguous` | estimated-tax payment timing
  Form 1040 line 26 and Form 2210 period-d handling can diverge for early-2026 estimated-tax payments applied to tax year 2025.
  Sources: IRS Instructions for Form 2210 (2025), line 11 / Table 1 and project equations.

- `likely error` | waiver boxes A / B
  The current implementation effectively forces zero penalty when waiver boxes are checked, but the IRS waiver process can be partial rather than total.
  Sources: IRS Instructions for Form 2210 (2025), waiver discussion.

- `missing support` | farmers / fishers rules
  The 2210-F path and the March 2, 2026 payment exception are not fully modeled.
  Sources: IRS Instructions for Form 2210 (2025), farmers and fishers.

- `missing support` | nonresident rules
  Form 1040-NR-specific modifications remain a defer-to-manual path.
  Sources: IRS Instructions for Form 2210 (2025), nonresident sections.

### `f4952`

- `missing support` | investment-income sourcing
  Investment income is only partially sourced and still depends heavily on manual classification.
  Sources: project explanations and Pub. 550 dependency.

- `missing support` | `f4952.4g`
  The election workflow remains scaffold-level and does not model full timing, revocation, and optimization behavior.
  Sources: project explanations and Pub. 550 dependency.

- `likely error` | `f4952.4d`, `f4952.4e`
  Capital gain distributions appear in both the line-4d and line-4e helper paths, which risks overstating one side unless the facts happen to justify both inclusions simultaneously.
  Sources: project equations and Form 4952 line structure.

- `missing support` | passive-activity / other limitation interaction
  The JSON computes the arithmetic of lines 1 through 8 but does not model all IRC / instruction-level limitation interactions.
  Sources: Form 4952 legal and publication context.

- `ambiguous` | `f4952.filing_exception_met`
  The filing-exception helper uses a strict `> 1` threshold in a way that is not transparently tied to the IRS instruction wording.
  Sources: project JSON and Form 4952 exception context.

- `ambiguous` | carryforward-record storage
  Carryforward data is pulled from `f8949.carryforward_records`, which is functionally possible but semantically strange for Form 4952 auditability.
  Sources: project equations and block host choice.

## Cross-Form Notes

- `needs judgment` | internal audit note staleness
  `docs/problematic_forms_and_lines.txt` appears stale in at least one place: it describes the child-tax-credit issue as Form 1040 line 18, while the current master JSON puts that behavior on line 19.

- `ambiguous` | synthetic compatibility aliases
  Several forms still contain synthetic helper lines or aliases that are not printed-form lines. They may be operationally useful, but they weaken one-to-one auditability against the IRS forms.

- `missing support` | attachment / overflow behavior
  Multiple forms still use fixed-row limits where the IRS expects attached statements or additional pages. This is especially visible in Schedule B, Schedule E, Form 2441, and some source-document workflows.

## Suggested Follow-Up Order

1. Fix mathematically wrong or high-risk line logic first:
   `f1116.19`, `f1116.3f`, `f8962` applicable-figure / SLCSP handling, `f2441.8`, `f2441` deemed-income logic, `f1040sd.21`, `f2210.1`, `f2210.19`.
2. Fix line-semantics mismatches next:
   `f1040sb` Part I / Part II numbering and Part III question structure, `f1040.4b`, `f1040se.21`.
3. Then address structural support gaps:
   `f8283` filing / Section B triggers, `f1116` country/category repeatability, `f8962` shared-policy allocation defaults, `f4952` classification/election scaffolding.

## Completion Note

This reverse-audit pass is complete for the slices listed in the Scope section. No JSON edits were made as part of this audit pass.

## JSON Lines And Suggested Fixes

This appendix maps each detailed finding to the current JSON field / expression and a suggested remediation path. The entries below are one-to-one with the Detailed Findings section; the Highest-Priority section is only a duplicate summary.

### `f1040`

- `f1040.4b`
  Current JSON: `equation: "f1040_Lines_5a_and_5b.9"`.
  Suggested helper replacement: route `4b` through an IRA-specific taxable-amount workflow, likely a dedicated IRA basis / taxable-distribution worksheet keyed to Form 1040 line 4b and Pub. 590-B, instead of the pension / annuity worksheet.

- `f1040.7a`
  Current JSON: `manual_entry: true`, `override_possible: true`.
  Suggested helper replacement: derive `7a` from Schedule D and any permitted direct-capital-gain exceptions, then leave manual override only for explicitly unsupported branches.

- `f1040.7b`
  Current JSON: `format: "boolean"`, `manual_entry: true`, `explanation: "Schedule D not required"`.
  Suggested helper replacement: compute the checkbox from direct-reporting conditions rather than relying on manual entry.

- `f1040.13a`
  Current JSON: `equation: "max(f8995.15, f8995a.39, qbi_deduction_total)"`.
  Suggested structural replacement: demote `qbi_deduction_total` to an explicit fallback / audit-only helper or remove it once `f8995` / `f8995a` are authoritative.

- `f1040.19`
  Current JSON: `equation: "max(f8812.14, child_tax_credit_amount + other_dependent_credit_amount)"`.
  Suggested replacement formula: if Schedule 8812 is the authoritative carryout, the replacement formula should be `equation: "f8812.14"`, with `child_tax_credit_amount` and `other_dependent_credit_amount` moved to separately labeled adjustment helpers instead of sitting inside a `max(...)` override path.

- `f1040.eic_qualifying_children_count`
  Current JSON: no equation; `format: "0"`, `manual_entry: true`, `override_possible: false`, with explanation `Explicit helper input used by the EIC table lookup until qualifying-child logic is modeled in more detail.`
  Suggested structural replacement: derive this from dependent facts and EIC qualification rules, with a separate exception bucket only for unsupported edge cases.

### `f1040sa`

- `f1040sa.9`
  Current JSON: `equation: "f4952.8"`.
  Suggested structural replacement: keep the carryout, but only after strengthening Form 4952 sourcing and limitation logic; until then, label this as provisional in both explanation text and audit status.

- `f1040sa.5a` through `f1040sa.5e`
  Current JSON: `5a_sales_tax_election`, `5a`, `5b`, and `5c` are manual-entry cells with no equation; `5d` is `equation: "5a + 5b + 5c"`; `5e` is `equation: "min(5d, (max(10000.0, 40000.0 - (max(0.0, (f1040s1a.3 - (500000.0 - (f1040.filing_status_married_separately * 250000.0)))) * 0.30)) / (1.0 + f1040.filing_status_married_separately)))"`.
  Suggested structural replacement: keep taxpayer elections manual, but add clearer source-bucket structure so state income tax, sales tax, and property tax flows are distinct and easier to validate.

- `f1040sa.8d`
  Current JSON: `equation: "0"`, `description: "Reserved for future use"`, `explanation: "Schedule A line 8d."`
  Suggested structural replacement: leave at zero only if the 2025 official form keeps the line reserved; otherwise rebuild when the printed form assigns content.

- `f1040sa.itemized`
  Current JSON: `equation: "17"`, `description: "Compatibility alias for total itemized deductions"`, `explanation: "Synthetic compatibility cell used by the current Form 1040 line 12e equation."`
  Suggested structural replacement: keep it if operationally useful, but rename or document it more explicitly as a non-printed helper alias.

### `f1040s1`, `f1040s2`, `f1040s3`

- `f1040s1.22`
  Current JSON: `equation: "0"`.
  Suggested structural replacement: keep as a reserved placeholder only while the printed line remains unused; otherwise replace with the actual line mapping.

- `f1040s2.21`
  Current JSON: `equation: "4 + 7 + 8 + 9 + 10 + 11 + 12 + 13 + 14 + 15 + 16 + 18 + 19 + 20"`.
  Suggested replacement formula: if the 2025 printed line-21 text is controlling, the replacement formula is likely `equation: "4 + 7 + 8 + 9 + 10 + 11 + 12 + 13 + 14 + 15 + 16 + 18 + 19"` with line `20` removed.

- `f1040s2.17`
  Current JSON: `equation: "21"`, `description: "Compatibility alias for total other taxes"`, `explanation: "Synthetic compatibility cell for the current Form 1040 equation that still points to Schedule 2 cell 17."`
  Suggested structural replacement: rename it as an internal helper or move the compatibility mapping behind a dedicated alias namespace rather than using a printed-form line id.

- `f1040s3.8`
  Current JSON: `equation: "1 + 2 + 3 + 4 + 5a + 5b + 7"` with explanation `Schedule 3 line 8. Enter on Form 1040 line 19a in the current master model.`
  Suggested structural replacement: update the explanation to match the actual equation / carryout target.

- `f1040s3.15`
  Current JSON: `equation: "9 + 10 + 11 + 12 + 14"` with explanation `Schedule 3 line 15. Enter on Form 1040 line 31 in the printed form; retained here for current master-model line 23 wiring.`
  Suggested structural replacement: rewrite the explanation to use only official printed-form targets plus any clearly labeled internal alias note.

- `f1040s3.6e`
  Current JSON: `equation: "0"`.
  Suggested structural replacement: keep only while the line remains reserved on the official form.

### `f8812`

- `f8812.4`, `f8812.6`
  Current JSON: `f8812.4` is `equation: "sum(f1040.dependents.*.child_tax_credit)"`; `f8812.6` is `equation: "sum(f1040.dependents.*.credit_other_dependents)"`.
  Suggested structural replacement: add dependent-level TIN type / validity / issuance-timing facts and drive CTC versus ODC eligibility from them.

- `f8812.18a`
  Current JSON: `equation: "f8812_Earned_Income_Worksheet.7"`; that worksheet line 7 is `equation: "max(0, 3 - 6)"`, and the line-18a explanation explicitly notes residual unsupported branches remain manual on the worksheet.
  Suggested helper replacement: extend the earned-income worksheet inputs and equations to cover optional farm method and remaining specialized adjustments.

- `f8812.21`
  Current JSON: `equation: "f8812_Additional_Medicare_Tax_and_RRTA_Tax_Worksheet.16"` with explanation that it includes W-2 and Puerto Rico Form 499R-2/W-2PR withholding inputs.
  Suggested helper replacement: add explicit split cells or a rule engine that assigns Form 8959 line 17 between the correct worksheet destinations without double counting.

- `f8812._meta.activation_rule`
  Current JSON: `activation_rule: "14 > 0.0 or 27 > 0.0 or 4 > 0.0 or 6 > 0.0"`.
  Suggested helper replacement: scope the rule explicitly with `f8812.` prefixes or move the logic to a helper to avoid accidental ambiguity.

### `f1040sb`

- `f1040sb._meta.activation_rule`
  Current JSON: `"3 > 1500.0 or 6 > 1500.0 or 7a or 8"`.
  Suggested helper replacement: expand the activation logic to include non-threshold filing triggers from the instructions, not just the dollar tests and foreign-account questions.

- `f1040sb.2`
  Current JSON: no equation; `manual_entry: true`, `description: "Seller-financed mortgage or accrued interest adjustments"`, `explanation: "Schedule B line 2 manual adjustment bucket."`
  Suggested structural replacement: align line 2 specifically to the printed net-adjustment role after line-1 detail rather than describing it as a seller-financed bucket.

- `f1040sb.3`
  Current JSON: `equation: "1 + 2"`, `description: "Total taxable interest"`, `explanation: "Schedule B line 3."`
  Suggested structural replacement: shift the computed taxable-interest total to the correct printed line identity for 2025, and reserve line 3 for the education-savings-bond exclusion reference if that is what the official form requires.

- `f1040sb` Part II row ids
  Current JSON: payer/amount cells are literally named `line_4_payer_1` through `line_4_payer_15` and `line_4_amount_1` through `line_4_amount_15`, with helper equations `schedule_b_dividend_name(n)` / `schedule_b_dividend_amount(n)`.
  Suggested structural replacement: rename these to `line_5_*` or otherwise align them with the official Part II line numbering.

- `f1040sb` fixed row counts
  Current JSON: Part I has `line_1_payer_1` through `line_1_payer_14`; Part II has `line_4_payer_1` through `line_4_payer_15`.
  Suggested structural replacement: preserve the first-page rows but add an attached-statement / overflow structure rather than silently capping the schedule.

- `f1040sb.7a`
  Current JSON: one manual boolean cell with `description: "Foreign account question"` and `explanation: "Schedule B Part III line 7a."`
  Suggested structural replacement: split into two separate booleans matching the two IRS line-7a questions.

- `f1040sb.7b`
  Current JSON: a manual text cell with `description: "Foreign country"` and `explanation: "Schedule B Part III line 7b."`
  Suggested structural replacement: tighten the explanation and conditional logic so the field is clearly tied to the FinCEN-reporting question.

### `f1040sd` and related Schedule D worksheets

- `f1040sd.21`
  Current JSON: `equation: "max(16, -capital_loss_limit())"`.
  Suggested replacement formula: a safer replacement formula is `equation: "min(0, max(16, -capital_loss_limit()))"` so gains on line 16 do not incorrectly survive onto line 21, while losses are still capped at the annual limit.

- `f1040sd.4`
  Current JSON: `equation: "f6252.schedule_d_short_term + f6781.schedule_d_4 + f8824.schedule_d_4"` while the description still says `Short-term gain or (loss) from Forms 6252, 4684, 6781, and 8824`.
  Suggested structural replacement: either add the appropriate `f4684` carryout or remove the description claim until that source is modeled.

- `f1040sd.11`
  Current JSON: `equation: "f4797.schedule_d_11 + f1040.undistributed_long_term_capital_gains_total + f6252.schedule_d_long_term + f6781.schedule_d_11 + f8824.schedule_d_11"` while the description still mentions Form 4684.
  Suggested structural replacement: add the `f4684` path if appropriate for the official line or narrow the description.

- `f1040sd_28_Rate_Gain.5`
  Current JSON: `equation: "f1040sd.14"`.
  Suggested structural replacement: add a source bucket for that K-1 item and include it in the worksheet equation.

- `f1040sd_28_Rate_Gain.1`, `.3`
  Current JSON: both are manual-entry cells with no equation; line 1 is described as `Collectibles gain or (loss) from Form 8949 Part II`, and line 3 as `Collectibles gain or (loss) from Forms 4684, 6252, 6781, and 8824`.
  Suggested structural replacement: derive these from Form 8949 collectibles flags and the relevant upstream forms where possible, leaving manual inputs only for unsupported special cases.

- `f1040sd.qof_disposed_any`
  Current JSON: explanation says `Schedule D top checkbox. If yes, attach Form 8949 and satisfy the additional reporting requirements.`
  Suggested structural replacement: rewrite the explanation to reflect the broader IRS instruction set, including Form 8997 and the Form 8949 instruction dependency.

### `f8949`

- direct Schedule D exception helpers
  Current JSON: `direct_schedule_d_1a` is `equation: "capital_direct_schedule_d_total(\"1a\")"` and `direct_schedule_d_8a` is `equation: "capital_direct_schedule_d_total(\"8a\")"`; the helper in `src/main.py` only admits selected 1099-B / 1099-DA box families with basis reported and no nonzero adjustment.
  Suggested helper replacement: add explicit block fields for all disqualifying boxes / elections referenced in the 2025 instructions and enforce them in the helper.

- direct-reporting versus Form 8949 duplication
  Current JSON: there is no exclusivity equation, activation rule, or validator preventing the same transaction class from populating both the direct Schedule D helper path and the Form 8949 blocks.
  Suggested structural replacement: add a deduplication / exclusivity flag at the transaction-source level or a validation warning when both paths are populated for the same lot class.

- `f8949.blocks.*.gain_loss`
  Current JSON: each block's `item_cells.gain_loss` is a manual numeric field with no equation and explanation `Form 8949 column (h). This is the amount that flows to the Schedule D line totals.`
  Suggested structural replacement: compute it by default from proceeds, basis, and adjustment amount, while preserving override only for explicitly exceptional codes.

- checkbox-family handling
  Current JSON: transactions are partitioned only by which block they live in, such as `st_box_a`, `st_box_b`, `lt_box_d`, `lt_box_e`, etc.; there is no shared category enum or exclusivity validator.
  Suggested structural replacement: add a transaction-level category enum or validator so one row belongs to exactly one checkbox family.

- `f8949.blocks.carryforward_records`
  Current JSON: block explanation says `Use one entry per carryforward amount brought from another tax year into the current return. This is the generic carryforward contract for saved return data until cross-year linking is modeled more deeply.`
  Suggested structural replacement: move generic carryforward storage to a neutral owner such as `f1040_Federal_Info_Worksheet` or a dedicated cross-year helper form.

### `f1116`, `f1116sb`, `f1116sc`, `f1116_Questionnaire`

- `f1116.3d`
  Current JSON: `equation: "max(0, 1a + line_3d_adjustments)"`.
  Suggested structural replacement: separate line 3d from line 1a conceptually and source it from true gross foreign-source income inputs, not just taxable-category gross plus an adjustment bucket.

- `f1116.3e`
  Current JSON: `equation: "max(0, f1040.9 + f1040.2a + line_3e_adjustments)"`.
  Suggested structural replacement: expand the line-3e base to include the specific all-sources items the instructions require, including excluded foreign earned income where applicable.

- `f1116.3f`
  Current JSON: `equation: "((3e > 0.0) * (3d / 3e)) + ((3e <= 0.0) * 0.0)"`.
  Suggested replacement formula: the replacement formula should be `equation: "min(1.0, 3d / 3e) if 3e > 0.0 else 0.0"` so the ratio is both guarded and capped without relying on boolean multiplication.

- `f1116.4a`
  Current JSON: `equation: "f1040sa.8e * 3f + other_line_4a_adjustments"`.
  Suggested structural replacement: rebuild around the actual home-mortgage-interest allocation rules instead of a blanket ratio shortcut.

- `f1116.4b`
  Current JSON: `equation: "f1040sa.9 * 3f + other_line_4b_adjustments"` with explanation `Form 1116 line 4b: Schedule A investment interest (line 9, from Form 4952 when applicable) multiplied by line 3f, plus manual adjustments.`
  Suggested structural replacement: add the asset-method / instruction-driven apportionment path and keep the ratio shortcut only as a temporary fallback.

- `f1116.19`
  Current JSON: `equation: "((18 > 0.0) * min(1.0, 17 / 18)) + ((18 <= 0.0) * 0.0)"`, even though the explanation says `If line 17 is more than line 18, enter 1.`
  Suggested replacement formula: the replacement formula should be something like `equation: "1.0 if 18 <= 0.0 and 17 >= 18 else (min(1.0, 17 / 18) if 18 > 0.0 else 0.0)"`, or the equivalent in helper form, so the line can actually return `1` in the IRS-required branch.

- country and category repeatability
  Current JSON: filing-sequence slots enumerate one copy per category family such as `f1116_passive`, `f1116_general`, `f1116_section_951a`, `f1116_resourced_by_treaty`, plus parallel `f1116sc_*` copies, but not a true repeatable per-country / per-treaty data structure.
  Suggested structural replacement: model repeatable 1116 copy specs keyed by category and, where required, treaty / country instance.

- treaty and `901(j)` categories
  Current JSON: category selection is represented by one boolean per category on each form copy, and `category_selection_count` just sums those booleans.
  Suggested structural replacement: support multiple instances or attachment copies per treaty-resourced amount / sanctioned-country category.

- `f1116_section_951a.10`
  Current JSON: `equation: "category_carryforward_records_total + manual_line_10_carryback_adjustments"` even though the explanation still says `using Schedule B totals when present`; by contrast, the base `f1116.10` equation explicitly references `f1116sb.3xiv`.
  Suggested structural replacement: verify against the 2025 Schedule B / instructions and either include the same carryover source or explicitly document the IRS exception.

- `f1116` carryforward storage
  Current JSON: `category_carryforward_records_total` is a long equation beginning `category_selection_valid * ((category_passive * crossblocksum_match("f8949","carryforward_records","amount","target_form","f1116","target_line","10","category","passive","tax_year","2024")) + ... )`, and the source block itself says it is a generic carryforward contract.
  Suggested structural replacement: move the carryforward records to a neutral cross-year storage block and update all dependent equations.

- 1099 passive-only sourcing
  Current JSON: `category_foreign_tax_from_information_returns` is `equation: "(category_selection_valid * category_passive * (sum(f1040.1099_int.*.box_6) + sum(f1040.1099_div.*.box_7)))"` and its explanation says the common information returns are treated as passive-category inputs.
  Suggested structural replacement: add category attribution fields / rules so information-return facts can feed non-passive 1116 categories when appropriate.

- `f1116sc`
  Current JSON: `_meta.name` is `Legacy Schedule C (Form 1116) Worksheet` and `_meta.activation_rule` is simply `"False"`.
  Suggested structural replacement: rebuild Schedule C line by line and tie activation to actual foreign-tax-redetermination facts.

### `f8962`

- `f8962.alternative_calculation_for_marriage`
  Current JSON: there is one manual boolean field, `alternative_calculation_for_marriage`, with explanation `Checkbox for the special year-of-marriage alternative calculation.`
  Suggested structural replacement: add a separate Line A certification field for the MFS domestic-abuse / spousal-abandonment rule and keep the year-of-marriage calculation distinct.

- `f8962.household_income_pct_fpl`
  Current JSON: `equation: "((household_income / federal_poverty_line) * 100) if federal_poverty_line > 0 else 0"`.
  Suggested replacement formula: the replacement formula should truncate rather than retain decimals, ideally as `equation: "floor((household_income / federal_poverty_line) * 100) if federal_poverty_line > 0 else 0"`. If the expression engine does not support `floor`, this should move to a helper such as `f8962_household_income_pct_fpl()`.

- `f8962.applicable_figure`
  Current JSON: manual input with explanation `Form 8962 line 7 applicable figure from the instructions table, entered as a percent value such as 8.50.`
  Suggested structural replacement: choose one explicit contract and encode it consistently: either store the IRS decimal directly, such as `0.0850`, or rename this field to make clear it is a percent-entered value and convert it before any multiplication.

- `f8962.annual_contribution_amount`
  Current JSON: `equation: "round((household_income * applicable_figure) / 100, 0)"`.
  Suggested replacement formula: if `applicable_figure` is stored in IRS decimal form, the replacement formula should be `equation: "round(household_income * applicable_figure, 0)"`. If percent-entry is retained instead, the current `/ 100` contract should be made explicit in both field naming and explanation.

- `f8962` SLCSP annual / monthly totals
  Current JSON: `annual_slcsp` uses `equation: "f8962_policy_annual_total(\"slcsp\")"`, `monthly_slcsp_total` uses the month-by-month totals, and the current helper in `src/main.py` sums every `1095-A` entry via `_f8962_policy_annual_total()` / `_f8962_policy_monthly_total()` without a same-state covered-family exception.
  Suggested helper replacement: add policy-grouping logic for column B so same-state covered-family situations do not simply sum all `1095-A` SLCSP amounts. The fix should introduce a policy-selection or grouped-SLCSP helper and route `annual_slcsp` / monthly column-B cells through that helper instead of the unconditional sum.

- `f8962.26`
  Current JSON: `equation: "max(0, 24 - 25)"` with explanation `Form 8962 line 26 routed to Schedule 3 line 9.`
  Suggested replacement formula: the minimal replacement formula is `equation: "0 if alternative_calculation_for_marriage and 24 > 25 else max(0, 24 - 25)"`; the fuller fix is to feed that branch from explicit Part V helper cells rather than only the top-level boolean.

- shared-policy allocation defaults
  Current JSON: `allocation_factor` behavior comes from `_f8962_entry_allocation_factor()` in `src/main.py`, which returns `1.0` when no percentages are present and returns `0.0` when the stored percent is zero or blank; the `f8962` JSON line items route through that helper for annual and monthly reconciliation totals.
  Suggested helper replacement: encode the IRS default-allocation branch explicitly. When the shared-policy fact pattern matches the no-agreement case, populate the effective allocation percentage as `50%` for each relevant column instead of falling back to `1.0` or `0.0`.

- QSEHRA / ICHRA / MEC / premium rules
  Current JSON: related flags exist mainly on `f1040.blocks.1095_a.item_cells`, such as `employer_coverage_affordable` and `qsehra_affordable`, but the `f8962` Part II equations route through `f8962_policy_*` totals and do not directly incorporate a full month-level QSEHRA / ICHRA / MEC eligibility model.
  Suggested structural replacement: add explicit month-level eligibility / premium-adjustment cells and equations for each rule family.

- `f8962._meta.activation_rule`
  Current JSON: `"block_has_entries(\"f1040\",\"1095_a\") or annual_advance_ptc > 0.0 or annual_ptc > 0.0 or form_has_user_activity(\"f8962\")"`.
  Suggested helper replacement: prefer activation based on factual filing triggers such as APTC received / claimable PTC facts, not on computed `annual_ptc`.

### `f2441`

- qualifying-person resident checkbox
  Current JSON: cells such as `qualifying_person_1_full_year_resident` are manual booleans whose explanation says `Retained for the current PDF row layout. Use when the printed checkbox in the row should be marked.`
  Suggested structural replacement: either map it to a real IRS concept with accurate naming or remove it from the semantic model and keep it only in the PDF layer.

- provider household-employee / tax-exempt naming
  Current JSON: cells are named `provider_1_is_tax_exempt`, etc., but the description says `Care provider 1 was household employee` and the explanation says `Printed line-1 checkbox for whether the provider was a household employee during the year.`
  Suggested structural replacement: rename the cell ids / explanations to match the official provider table columns exactly.

- `f2441.8`
  Current JSON: `equation: "f2441_applicable_percentage()"`, and `_f2441_applicable_percentage()` reduces from `0.35` by `0.01` per `$2,000` step until hitting `0.20`.
  Suggested helper replacement: there is no trustworthy one-line arithmetic replacement here; the replacement should be a table-lookup helper such as `equation: "f2441_applicable_percentage_lookup(7)"`, where the helper mirrors the official Worksheet A brackets exactly instead of using a smooth decrement formula.

- deemed-income logic
  Current JSON: line 4 and line 5 use `equation: "f2441_earned_income(\"taxpayer\")"` and `equation: "f2441_earned_income(\"spouse\") if f1040.filing_status_married_jointly else 4"`, while `_f2441_deemed_income()` multiplies student/disabled months by a flat monthly amount and `_f2441_earned_income()` takes an annual `max(...)`.
  Suggested helper replacement: compute deemed earned income month by month, then aggregate it using the exact IRS line-4 and line-5 rules, including the married-joint joint-month limitation rather than one annual max comparison.

- earned-income sourcing
  Current JSON: `_f2441_earned_income()` in `src/main.py` uses W-2 `box_1` sums by recipient, adds `taxpayer_earned_income_adjustments` or `spouse_earned_income_adjustments`, then compares that annual amount against `_f2441_deemed_income(...)`.
  Suggested helper replacement: add the full instruction-driven earned-income sources and exclusions.

- `f2441.12`
  Current JSON: `equation: "sum(f1040.w2.*.box_10) + line12_additional_non_w2_benefits"` with explanation `Form 2441 line 12 from W-2 box 10 plus any supported non-W-2 dependent-care-benefit amounts.`
  Suggested structural replacement: split line 12 into gross benefits received, benefits already included in wages, and net benefits carried into Part III. The line-12/13/14 flow should follow the instruction worksheet instead of summing all box-10 amounts directly into the benefit total.

- `f2441.10`
  Current JSON: `equation: "max_zero(f1040.18 - f1040s3.1 - f1040_Schedule_3_Line_6l_Negative_Form_8978.2)"`.
  Suggested structural replacement: rebuild the credit-limit worksheet from the exact printed source lines used by the 2025 instructions rather than from broad Schedule 3 aliases, so future Schedule 3 rewiring cannot silently change the Form 2441 limit.

- overflow attachments
  Current JSON: the form has booleans such as `more_than_three_qualifying_persons` and `more_than_three_providers`, but no repeatable overflow blocks for attached additional rows.
  Suggested structural replacement: add repeatable overflow blocks or an attached-statement structure for providers and qualifying persons beyond three.

### `f1040se`

- `f1040se.21`
  Current JSON: `equation: "property_1_line21 + property_2_line21 + property_3_line21 + f1040se.21_manual_component + f4835.schedule_e_40"`.
  Suggested structural replacement: keep Schedule E Part I property-column line-21 totals separate from Form 4835 carryouts. Form 4835 should land on its actual printed Schedule E destination line first, and only then roll into the page total through the printed form structure.

- Form 4835 carryout
  Current JSON: the same `f1040se.21` equation appends `+ f4835.schedule_e_40` directly to the Part I property total.
  Suggested structural replacement: remove `f4835.schedule_e_40` from the line-21 aggregate and route it through the later Schedule E line where farm-rental income from Form 4835 belongs, then aggregate from that printed destination.

- three-property limit
  Current JSON: Schedule E Part I is modeled through fixed property-column cells like `property_1_line21`, `property_2_line21`, and `property_3_line21`.
  Suggested structural replacement: model Part I as a repeating block with page/overflow handling.

- five-passthrough limit
  Current JSON: passthrough activity fields are modeled in fixed slot families rather than a repeating activity block.
  Suggested structural replacement: convert passthrough activity rows to a repeating structure.

- Part II / Part III collapse
  Current JSON: current Schedule E aggregation uses a compressed passthrough structure, including equations like `f1040se.28_k1_income_total + f1040se.passthrough_adjustments + f7203.schedule_e_basis_adjustment`, rather than distinct printed sections for each entity class.
  Suggested structural replacement: split them into the printed form sections with separate row structures and carryouts.

- limitation stack
  Current JSON: limitation effects are represented through broad aggregate adjustments such as `passthrough_adjustments`, `21_manual_component`, and similar compressed carryout cells rather than a line-by-line limitation stack.
  Suggested structural replacement: model the printed limitation structure and upstream supporting forms instead of one combined adjustment layer.

### `f8283`

- `f8283.required_to_file_likely`
  Current JSON: `equation: "f8283.schedule_a_12 > 500.0"`.
  Suggested structural replacement: replace the one-number trigger with per-item or group-of-similar-items filing logic, so the filing test is driven by the IRS reporting unit rather than the final Schedule A carryout.

- `f8283.section_b_required_likely`
  Current JSON: `equation: "f8283.schedule_a_12 > 5000.0"`.
  Suggested structural replacement: compute Section B status by contributed item group, donee, and the applicable special-case rules, rather than using a single post-aggregation threshold.

- Section A row explanations
  Current JSON: representative Section A item fields include explanations such as `Auto-populated from the corresponding Form 1098-C row when available...`
  Suggested structural replacement: broaden the row descriptions and source model so Section A can represent the full range of IRS property categories.

- form completeness
  Current JSON: the modeled carryout is largely driven by `noncash_contributions_from_1098c`, `other_noncash_contributions`, `schedule_a_12`, and threshold booleans, without the fuller appraisal, donee, declaration, and valuation structure of the official form.
  Suggested structural replacement: add the missing appraisal, donee, valuation, and declaration structure before treating the form as more than a partial scaffold.

- `f8283.schedule_a_12`
  Current JSON: `equation: "max(0, f8283.noncash_contributions_from_1098c + f8283.other_noncash_contributions)"`.
  Suggested structural replacement: preserve Section A / Section B item structure, donee structure, and valuation-related qualifiers upstream, then aggregate to Schedule A only at the last carryout step.

- 1098-C deduction logic
  Current JSON: `noncash_contributions_from_1098c` is `equation: "sum(f1040.1098_c.*.claimed_deduction_amount)"`.
  Suggested structural replacement: explicitly model gross-proceeds limitation and the instruction exceptions for vehicle donations.

### `f2210`

- `f2210.1`
  Current JSON: `equation: "f1040.24"`, explanation says Form 1040 line 24.
  Suggested replacement formula: if the audit conclusion is correct, the replacement formula is likely `equation: "f1040.22"`, followed by any needed adjustments to downstream line-2 overlap logic.

- `f2210.safe_harbor_exception_met`
  Current JSON: `equation: "((4 < 1000.0) + (7 < 1000.0) + (6 >= 9) + (f1040_Federal_Info_Worksheet.prior_year_full_year_return_for_2210 * f1040_Federal_Info_Worksheet.prior_year_no_tax_liability_for_2210)) > 0.0"`.
  Suggested helper replacement: re-express the no-penalty logic directly in terms of the official Part I comparisons and exceptions, using the exact IRS line references rather than mixing helper thresholds like both `4 < 1000` and `7 < 1000` into one composite boolean.

- `f2210.3`
  Current JSON: `equation: "f1040.32"`.
  Suggested helper replacement: add the 2025 section-1062 / Notice 2026-3 adjustment branch explicitly.

- `f2210.19`
  Current JSON: `equation: "f2210_penalty()"`; the helper in `src/main.py` uses a simplified event-based engine with hardcoded annual rate handling, waiver suppression, and payment allocation logic rather than the full printed worksheet structure.
  Suggested helper replacement: implement the official multi-period worksheet or a mathematically equivalent segmented engine.

- estimated-tax payment timing
  Current JSON: Form 1040 line 26 uses calendar-year estimated-tax-payment summing, while Form 2210 quarter logic uses date-range helpers such as `crossblocksum_date_range("f1040","estimated_tax_payments_detail",...)` for separate installment periods.
  Suggested helper replacement: unify the tax-year payment-date rules and make the Form 1040 line-26 versus 2210-period distinctions explicit where the IRS requires them.

- waiver boxes A / B
  Current JSON: the `f2210_penalty()` helper returns `0.0` when the Part II box A or B booleans are checked, effectively suppressing automated penalty calculation.
  Suggested helper replacement: model partial-waiver behavior separately from full-waiver behavior.

- farmers / fishers
  Current JSON: the model includes a farmer / fisher annual-payment percentage branch, but the automated penalty helper does not implement a full Form 2210-F or March 2 exception workflow.
  Suggested helper replacement: add Form 2210-F workflow and the early-payment exception logic.

- nonresident rules
  Current JSON: there is no 1040-NR-specific Form 2210 computation branch in the current automated helper, so those cases effectively fall back to manual treatment.
  Suggested helper replacement: add 1040-NR-specific line logic or explicitly exclude those cases from automated treatment.

### `f4952`

- investment-income sourcing
  Current JSON: line 4a is `equation: "obvious_1099_investment_income + (f1040_Federal_Info_Worksheet.include_passive_1099_misc_box_2_in_f4952_line_4a * sum(f1040.1099_misc.*.box_2)) + other_investment_income_adjustments + f8814.investment_income_carryin"`, and `obvious_1099_investment_income` itself is a helper aggregate rather than a full Pub. 550 classification model.
  Suggested structural replacement: add explicit source buckets for each IRS / Pub. 550 investment-income category.

- `f4952.4g`
  Current JSON: `equation: "min(4b + 4e, (line_4g_use_manual_split * (line_4g_elected_from_4e + line_4g_elected_from_4b)) + ((line_4g_use_manual_split <= 0.0) * (line_4g_default_from_4e + line_4g_default_from_4b)))"`.
  Suggested helper replacement: model election timing, revocation, and attribution rules directly from Pub. 550 guidance.

- `f4952.4d`, `f4952.4e`
  Current JSON: `4d` includes `obvious_investment_capital_gain_distributions` in `equation: "max(0, investment_property_dispositions_total + obvious_investment_capital_gain_distributions + other_investment_disposition_adjustments + capital_loss_carryover_adjustments_for_4d)"`; `4e` also includes the same helper in `equation: "min(4d, max(0, investment_property_net_capital_gain_total + obvious_investment_capital_gain_distributions + other_net_capital_gain_adjustments))"`.
  Suggested structural replacement: separate “disposition gain” sourcing from “net capital gain eligible for election” sourcing so the same dollars are not blindly used twice.

- passive-activity / other limitation interaction
  Current JSON: the form computes line arithmetic, but the final investment-interest deduction still depends on partial source classification and does not encode a broader passive / at-risk limitation regime.
  Suggested structural replacement: add the missing passive / at-risk / classification dependencies before treating the final deduction as authoritative.

- `f4952.filing_exception_met`
  Current JSON: `equation: "((filing_exception_interest_and_dividend_income > 1) * (5 <= 0.0) * (2 <= 0.0))"`.
  Suggested helper replacement: no single safe replacement formula should be asserted until the filing-exception test is decomposed into the exact instruction elements; the current `> 1` magic-number comparison should be replaced either by an explicit line-based comparison or by a named helper that encodes the IRS rule directly.

- carryforward storage
  Current JSON: line 2 uses `carryforward_records_line_2_total`, which is `equation: "crossblocksum_match(\"f8949\",\"carryforward_records\",\"amount\",\"target_form\",\"f4952\",\"target_line\",\"7\",\"tax_year\",\"2024\")"` before falling back to the worksheet helper amount.
  Suggested structural replacement: move the carryforward infrastructure to a neutral owner and update the line-2 equation.

### Cross-Form And Process Findings

- stale internal audit note
  Current JSON context: the child-tax-credit carryout currently lands at `f1040.19` via `equation: "max(f8812.14, child_tax_credit_amount + other_dependent_credit_amount)"`, so any note still referring to line 18 is stale.
  Suggested structural replacement: update the internal audit note to match the current form mapping.

- synthetic compatibility aliases
  Current JSON context: examples include `f1040s2.17` with `equation: "21"` and `f1040sa.itemized` with `equation: "17"`, both explicitly described as compatibility aliases.
  Suggested structural replacement: either namespace them as helpers or document them clearly as non-printed compatibility cells.

- attachment / overflow behavior
  Current JSON context: examples include fixed Schedule B row families like `line_1_payer_1` through `line_1_payer_14`, fixed Form 2441 provider / qualifying-person row slots, and fixed Schedule E property / passthrough slot families.
  Suggested structural replacement: convert those areas to repeatable blocks plus attachment-copy / overflow metadata rather than fixed-row caps.
