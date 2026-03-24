# Form Model Status

This file is the permanent manifest-to-model checklist for every YAML-listed form or schedule in `forms-instructions-and-publications/IRS_Federal_Individual_2025.yaml`.

## Status legend

- `modeled`: present as a top-level form or schedule in `federal_1040_2025.json` and not currently classified as a thin scaffold
- `scaffolded`: present as a top-level form or schedule, but still a thin scaffold, partial reconstruction, or dependency carrier rather than a reliable end-to-end IRS build
- `missing`: listed in the YAML manifest, but no top-level modeled form currently exists in `federal_1040_2025.json`
- `out_of_scope`: intentionally not being modeled in the current project phase

## Current counts

- `modeled`: `13`
- `scaffolded`: `86`
- `missing`: `13`
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
| `1040 Schedule C` | `f1040sc` | `scaffolded` | `Schedule C (Form 1040) - Profit or Loss From Business` |
| `1040 Schedule D` | `f1040sd` | `modeled` | `Schedule D (Form 1040) - Capital Gains and Losses` |
| `1040 Schedule E` | `f1040se` | `scaffolded` | `Schedule E (Form 1040) - Supplemental Income and Loss` |
| `1040 Schedule EIC` | `f1040sei` | `modeled` | `Schedule EIC (Form 1040) - Earned Income Credit` |
| `1040 Schedule F` | `f1040sf` | `scaffolded` | `Schedule F (Form 1040) - Profit or Loss From Farming` |
| `1040 Schedule H` | `f1040sh` | `scaffolded` | `Schedule H (Form 1040) - Household Employment Taxes` |
| `1040 Schedule J` | `f1040sj` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040 Schedule R` | `f1040sr_schedule_r` | `scaffolded` | `Schedule R (Form 1040) - Credit for the Elderly or the Disabled` |
| `1040 Schedule SE` | `f1040sse` | `scaffolded` | `Schedule SE (Form 1040) - Self-Employment Tax` |
| `1040-ES` | `f1040es` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040-V` | `f1040v` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1040-X` | `f1040x` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1098-E` | `f1098e` | `scaffolded` | `Form 1098-E - Student Loan Interest Statement` |
| `1116` | `f1116` | `scaffolded` | `Form 1116 - Foreign Tax Credit` |
| `1116 Schedule B` | `f1116sb` | `modeled` | `Schedule B (Form 1116) - Foreign Tax Carryover Reconciliation` |
| `1116 Schedule C` | `f1116sc` | `modeled` | `Schedule C (Form 1116) - Foreign Tax Redeterminations` |
| `2106` | `f2106` | `scaffolded` | `Form 2106 - Employee Business Expenses` |
| `2210` | `f2210` | `scaffolded` | `Form 2210 - Underpayment of Estimated Tax by Individuals, Estates, and Trusts` |
| `2210 Schedule AI` | `f2210_Schedule_AI` | `modeled` | `Form 2210 - Schedule AI Annualized Income Installment Method` |
| `2441` | `f2441` | `scaffolded` | `Form 2441 - Child and Dependent Care Expenses` |
| `2555` | `f2555` | `scaffolded` | `Form 2555 - Foreign Earned Income` |
| `3800` | `f3800` | `scaffolded` | `Form 3800 - General Business Credit` |
| `4137` | `f4137` | `scaffolded` | `Form 4137 - Social Security and Medicare Tax on Unreported Tip Income` |
| `4562` | `f4562` | `scaffolded` | `Form 4562 - Depreciation and Amortization` |
| `4684` | `f4684` | `scaffolded` | `Form 4684 - Casualties and Thefts` |
| `4797` | `f4797` | `scaffolded` | `Form 4797 - Sales of Business Property` |
| `4835` | `f4835` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `4952` | `f4952` | `scaffolded` | `Form 4952 - Investment Interest Expense Deduction` |
| `5329` | `f5329` | `scaffolded` | `Form 5329 - Additional Taxes on Qualified Plans and Other Tax-Favored Accounts` |
| `5405` | `f5405` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `5695` | `f5695` | `scaffolded` | `Form 5695 - Residential Energy Credits` |
| `6198` | `f6198` | `scaffolded` | `Form 6198 - At-Risk Limitations` |
| `6251` | `f6251` | `scaffolded` | `Form 6251 - Alternative Minimum Tax for Individuals` |
| `6252` | `f6252` | `scaffolded` | `Form 6252 - Installment Sale Income` |
| `6781` | `f6781` | `scaffolded` | `Form 6781 - Gains and Losses From Section 1256 Contracts and Straddles` |
| `7203` | `f7203` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8283` | `f8283` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8396` | `f8396` | `scaffolded` | `Form 8396 - Mortgage Interest Credit` |
| `8582` | `f8582` | `scaffolded` | `Form 8582 - Passive Activity Loss Limitations` |
| `8582-CR` | `f8582cr` | `scaffolded` | `Form 8582-CR - Passive Activity Credit Limitations` |
| `8606` | `f8606` | `scaffolded` | `Form 8606 - Nondeductible IRAs` |
| `8615` | `f8615` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8812` | `f8812` | `scaffolded` | `Schedule 8812 (Form 1040) - Credits for Qualifying Children and Other Dependents` |
| `2025 Schedule 8812 (Form 1040)` | `f8812` | `scaffolded` | `Schedule 8812 (Form 1040) - Credits for Qualifying Children and Other Dependents` |
| `8814` | `f8814` | `scaffolded` | `Form 8814 - Parents' Election To Report Child's Interest and Dividends` |
| `8862` | `f8862` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8863` | `f8863` | `scaffolded` | `Form 8863 - Education Credits` |
| `8880` | `f8880` | `scaffolded` | `Form 8880 - Credit for Qualified Retirement Savings Contributions` |
| `8888` | `f8888` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `8889` | `f8889` | `scaffolded` | `Form 8889 - Health Savings Accounts` |
| `8949` | `f8949` | `modeled` | `Form 8949 - Sales and Other Dispositions of Capital Assets` |
| `8959` | `f8959` | `scaffolded` | `Form 8959 - Additional Medicare Tax` |
| `8960` | `f8960` | `scaffolded` | `Form 8960 - Net Investment Income Tax` |
| `8962` | `f8962` | `scaffolded` | `Form 8962 - Premium Tax Credit` |
| `8995` | `f8995` | `scaffolded` | `Form 8995 - Qualified Business Income Deduction Simplified Computation` |
| `8995-A` | `f8995a` | `scaffolded` | `Form 8995-A - Qualified Business Income Deduction` |
| `9465` | `f9465` | `missing` | Manifest-listed, but no top-level modeled form yet |
| `1310` | `f1310` | `scaffolded` | `Form 1310 - Statement of Person Claiming Refund Due a Deceased Taxpayer` |
| `14039` | `f14039` | `scaffolded` | `Form 14039 - Identity Theft Affidavit` |
| `14039-B` | `f14039b` | `scaffolded` | `Form 14039-B - Business Identity Theft Affidavit` |
| `2120` | `f2120` | `scaffolded` | `Form 2120 - Multiple Support Declaration` |
| `2210-F` | `f2210f` | `scaffolded` | `Form 2210-F - Underpayment of Estimated Tax by Farmers and Fishermen` |
| `3115` | `f3115` | `scaffolded` | `Form 3115 - Application for Change in Accounting Method` |
| `3468` | `f3468` | `scaffolded` | `Form 3468 - Investment Credit` |
| `3903` | `f3903` | `scaffolded` | `Form 3903 - Moving Expenses` |
| `4136` | `f4136` | `scaffolded` | `Form 4136 - Credit for Federal Tax Paid on Fuels` |
| `4255` | `f4255` | `scaffolded` | `Form 4255 - Recapture of Investment Credit` |
| `4506` | `f4506` | `scaffolded` | `Form 4506 - Request for Copy of Tax Return` |
| `4852` | `f4852` | `scaffolded` | `Form 4852 - Substitute for Form W-2 or Form 1099-R` |
| `4868` | `f4868` | `scaffolded` | `Form 4868 - Application for Automatic Extension of Time To File` |
| `4972` | `f4972` | `scaffolded` | `Form 4972 - Tax on Lump-Sum Distributions` |
| `7206` | `f7206` | `scaffolded` | `Form 7206 - Self-Employed Health Insurance Deduction` |
| `8332` | `f8332` | `scaffolded` | `Form 8332 - Release/Revocation of Release of Claim to Exemption for Child by Custodial Parent` |
| `8379` | `f8379` | `scaffolded` | `Form 8379 - Injured Spouse Allocation` |
| `8453` | `f8453` | `scaffolded` | `Form 8453 - U.S. Individual Income Tax Transmittal for an IRS e-file Return` |
| `8586` | `f8586` | `scaffolded` | `Form 8586 - Low-Income Housing Credit` |
| `8801` | `f8801` | `scaffolded` | `Form 8801 - Credit for Prior Year Minimum Tax` |
| `8815` | `f8815` | `scaffolded` | `Form 8815 - Exclusion of Interest From Series EE and I U.S. Savings Bonds Issued After 1989` |
| `8822` | `f8822` | `scaffolded` | `Form 8822 - Change of Address` |
| `8824` | `f8824` | `scaffolded` | `Form 8824 - Like-Kind Exchanges` |
| `8829` | `f8829` | `scaffolded` | `Form 8829 - Expenses for Business Use of Your Home` |
| `8834` | `f8834` | `scaffolded` | `Form 8834 - Qualified Electric Vehicle Credit` |
| `8839` | `f8839` | `scaffolded` | `Form 8839 - Qualified Adoption Expenses` |
| `8853` | `f8853` | `scaffolded` | `Form 8853 - Archer MSAs and Long-Term Care Insurance Contracts` |
| `8857` | `f8857` | `scaffolded` | `Form 8857 - Request for Innocent Spouse Relief` |
| `8859` | `f8859` | `scaffolded` | `Form 8859 - District of Columbia First-Time Homebuyer Credit` |
| `8881` | `f8881` | `scaffolded` | `Form 8881 - Credit for Small Employer Pension Plan Startup Costs` |
| `8903` | `f8903` | `scaffolded` | `Form 8903 - Domestic Production Activities Deduction` |
| `8910` | `f8910` | `scaffolded` | `Form 8910 - Alternative Motor Vehicle Credit` |
| `8911` | `f8911` | `scaffolded` | `Form 8911 - Alternative Fuel Vehicle Refueling Property Credit` |
| `8915-D` | `f8915d` | `scaffolded` | `Form 8915-D - Qualified 2019 Disaster Retirement Plan Distributions and Repayments` |
| `8915-F` | `f8915f` | `scaffolded` | `Form 8915-F - Qualified Disaster Retirement Plan Distributions and Repayments` |
| `8919` | `f8919` | `scaffolded` | `Form 8919 - Uncollected Social Security and Medicare Tax on Wages` |
| `8936` | `f8936` | `scaffolded` | `Form 8936 - Clean Vehicle Credits` |
| `8936a` | `f8936a` | `scaffolded` | `Form 8936-A - Qualified Commercial Clean Vehicle Credit` |
| `8938` | `f8938` | `scaffolded` | `Form 8938 - Statement of Specified Foreign Financial Assets` |
| `8941` | `f8941` | `scaffolded` | `Form 8941 - Credit for Small Employer Health Insurance Premiums` |
| `8958` | `f8958` | `scaffolded` | `Form 8958 - Allocation of Tax Amounts Between Certain Individuals in Community Property States` |
| `8994` | `f8994` | `scaffolded` | `Form 8994 - Employer Credit for Paid Family and Medical Leave` |
| `9000` | `f9000` | `scaffolded` | `Form 9000 - Alternative Media Preference` |
| `982` | `f982` | `scaffolded` | `Form 982 - Reduction of Tax Attributes Due to Discharge of Indebtedness` |
| `SS-4` | `fss4` | `scaffolded` | `Form SS-4 - Application for Employer Identification Number` |
| `W-4` | `fw4` | `scaffolded` | `Form W-4 - Employee's Withholding Certificate` |
| `1040 Schedule LEP` | `f1040lep` | `scaffolded` | `Schedule LEP (Form 1040) - Request for Change in Language Preference` |

## Audit rule

No YAML-listed form or schedule should exist outside this inventory. When a form is added to the JSON model, upgraded from scaffolded to modeled, or intentionally deferred, this file must be updated in the same work.
