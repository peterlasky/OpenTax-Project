# Form Model Status

This file is the permanent manifest-to-model checklist for every YAML-listed form or schedule in `forms-instructions-and-publications/IRS_Federal_Individual_2025.yaml`.

## Status legend

- `modeled`: present as a top-level form or schedule in `federal_1040_2025.json` and not currently classified as a thin scaffold
- `scaffolded`: present as a top-level form or schedule, but `problematic_forms_and_lines.txt` says it is still incomplete or too thin for reliable end-to-end use
- `missing`: listed in the YAML manifest, but no top-level modeled form currently exists in `federal_1040_2025.json`
- `out_of_scope`: intentionally not being modeled in the current project phase

## Current counts

- `modeled`: `13`
- `scaffolded`: `20`
- `missing`: `32`
- `out_of_scope`: `0`

## Master inventory

| Manifest form or schedule | Expected form ID | Status | Current modeled name / note |
| --- | --- | --- | --- |
| `1040` | `f1040` | `modeled` | `Form 1040` |
| `1040-SR` | `f1040sr` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040 Schedule 1` | `f1040s1` | `modeled` | `Schedule 1 (Form 1040) - Additional Income and Adjustments to Income` |
| `1040 Schedule 1-A` | `f1040s1a` | `modeled` | `Schedule 1-A (Form 1040) - Additional Deductions` |
| `1040 Schedule 2` | `f1040s2` | `modeled` | `Schedule 2 (Form 1040) - Additional Taxes` |
| `1040 Schedule 3` | `f1040s3` | `modeled` | `Schedule 3 (Form 1040) - Additional Credits and Payments` |
| `1040 Schedule A` | `f1040sa` | `modeled` | `Schedule A (Form 1040) - Itemized Deductions` |
| `1040 Schedule B` | `f1040sb` | `modeled` | `Schedule B (Form 1040) - Interest and Ordinary Dividends` |
| `1040 Schedule C` | `f1040sc` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040 Schedule D` | `f1040sd` | `modeled` | `Schedule D (Form 1040) - Capital Gains and Losses` |
| `1040 Schedule E` | `f1040se` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040 Schedule EIC` | `f1040sei` | `modeled` | `Schedule EIC (Form 1040) - Earned Income Credit` |
| `1040 Schedule F` | `f1040sf` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040 Schedule H` | `f1040sh` | `missing` | Manifest-listed, no top-level modeled form yet, and already referenced by `f1040s2` line `9` |
| `1040 Schedule J` | `f1040sj` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040 Schedule R` | `f1040sr_schedule_r` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040 Schedule SE` | `f1040sse` | `scaffolded` | `Schedule SE (Form 1040) - Self-Employment Tax` |
| `1040-ES` | `f1040es` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040-V` | `f1040v` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040-X` | `f1040x` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1098-E` | `f1098e` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1116` | `f1116` | `scaffolded` | `Form 1116 - Foreign Tax Credit` |
| `1116 Schedule B` | `f1116sb` | `modeled` | `Schedule B (Form 1116) - Foreign Tax Carryover Reconciliation` |
| `1116 Schedule C` | `f1116sc` | `modeled` | `Schedule C (Form 1116) - Foreign Tax Redeterminations` |
| `2106` | `f2106` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `2210` | `f2210` | `scaffolded` | `Form 2210 - Underpayment of Estimated Tax by Individuals, Estates, and Trusts` |
| `2210 Schedule AI` | `f2210_Schedule_AI` | `modeled` | `Form 2210 - Schedule AI Annualized Income Installment Method` |
| `2441` | `f2441` | `scaffolded` | `Form 2441 - Child and Dependent Care Expenses` |
| `2555` | `f2555` | `scaffolded` | `Form 2555 - Foreign Earned Income` |
| `3800` | `f3800` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `4137` | `f4137` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `4562` | `f4562` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `4684` | `f4684` | `scaffolded` | `Form 4684 - Casualties and Thefts` |
| `4797` | `f4797` | `scaffolded` | `Form 4797 - Sales of Business Property` |
| `4835` | `f4835` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `4952` | `f4952` | `scaffolded` | `Form 4952 - Investment Interest Expense Deduction` |
| `5329` | `f5329` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `5405` | `f5405` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `5695` | `f5695` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `6198` | `f6198` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `6251` | `f6251` | `scaffolded` | `Form 6251 - Alternative Minimum Tax for Individuals` |
| `6252` | `f6252` | `scaffolded` | `Form 6252 - Installment Sale Income` |
| `6781` | `f6781` | `scaffolded` | `Form 6781 - Gains and Losses From Section 1256 Contracts and Straddles` |
| `7203` | `f7203` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8283` | `f8283` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8396` | `f8396` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8582` | `f8582` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8582-CR` | `f8582cr` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8606` | `f8606` | `scaffolded` | `Form 8606 - Nondeductible IRAs` |
| `8615` | `f8615` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8812` | `f8812` | `scaffolded` | `Schedule 8812 (Form 1040) - Credits for Qualifying Children and Other Dependents` |
| `2025 Schedule 8812 (Form 1040)` | `f8812` | `scaffolded` | Alias entry in the YAML manifest; maps to the same modeled schedule as `8812` |
| `8814` | `f8814` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8862` | `f8862` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8863` | `f8863` | `scaffolded` | `Form 8863 - Education Credits` |
| `8880` | `f8880` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8888` | `f8888` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8889` | `f8889` | `scaffolded` | `Form 8889 - Health Savings Accounts` |
| `8949` | `f8949` | `modeled` | `Form 8949 - Sales and Other Dispositions of Capital Assets` |
| `8959` | `f8959` | `scaffolded` | `Form 8959 - Additional Medicare Tax` |
| `8960` | `f8960` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8962` | `f8962` | `scaffolded` | `Form 8962 - Premium Tax Credit` |
| `8995` | `f8995` | `scaffolded` | `Form 8995 - Qualified Business Income Deduction Simplified Computation` |
| `8995-A` | `f8995a` | `scaffolded` | `Form 8995-A - Qualified Business Income Deduction` |
| `9465` | `f9465` | `missing` | Manifest-listed, but no top-level modeled form yet |

## Audit rule

No YAML-listed form or schedule should exist outside this inventory. When a form is added to the JSON model, upgraded from scaffolded to modeled, or intentionally deferred, this file must be updated in the same work.
