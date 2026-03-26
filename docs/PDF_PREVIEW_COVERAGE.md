# PDF Preview Coverage

Generated: 2026-03-25

This report audits the current preview/fill coverage driven by the live master JSON, local PDF inventory, legacy preview mappings in `reference-data/federal/2025/pdf_mappings/`, and generated widget catalogs in `reference-data/federal/2025/pdf_field_maps/`.

## Coverage Rules

- `filled_preview_ready`: explicit local PDF plus a preview mapping file.
- `raw_preview_only`: explicit local PDF but no preview mapping yet.
- `no_preview_pdf`: no explicit local PDF source in the model.
- `fillable_form`: the local PDF has one or more detected fillable fields according to `forms-instructions-and-publications/pdf_form_scan.json`.

## Summary

| Scope | Active items | Filled preview ready | Raw preview only | No preview PDF |
| --- | ---: | ---: | ---: | ---: |
| Top-level forms / schedules / worksheets | 137 | 3 | 105 | 29 |
| Source-document and helper blocks | 54 | 5 | 21 | 28 |

## Filled Preview Ready Forms

| Form ID | Name | Filing sequence | Fillable | Field count | PDF source |
| --- | --- | --- | --- | ---: | --- |
| `f1040` | Form 1040 | `None` | yes | 199 | `forms-instructions-and-publications/forms/f1040.pdf` |
| `f1040sa` | Schedule A (Form 1040) - Itemized Deductions | `07` | yes | 33 | `forms-instructions-and-publications/forms/f1040sa.pdf` |
| `f8812` | Schedule 8812 (Form 1040) - Credits for Qualifying Children and Other Dependents | `47` | yes | 41 | `forms-instructions-and-publications/forms/f1040s8.pdf` |

## Raw Preview Only Forms

| Form ID | Name | Filing sequence | Fillable | Field count | PDF source |
| --- | --- | --- | --- | ---: | --- |
| `f1040es` | Form 1040-ES - Estimated Tax for Individuals | `None` | yes | 118 | `forms-instructions-and-publications/forms/f1040es.pdf` |
| `f1040lep` | Schedule LEP (Form 1040) - Request for Change in Language Preference | `77` | yes | 23 | `forms-instructions-and-publications/forms/f1040lep.pdf` |
| `f1040s1` | Schedule 1 (Form 1040) - Additional Income and Adjustments to Income | `01` | yes | 73 | `forms-instructions-and-publications/forms/f1040s1.pdf` |
| `f1040s1a` | Schedule 1-A (Form 1040) - Additional Deductions | `1A` | yes | 54 | `forms-instructions-and-publications/forms/f1040s1a.pdf` |
| `f1040s2` | Schedule 2 (Form 1040) - Additional Taxes | `02` | yes | 63 | `forms-instructions-and-publications/forms/f1040s2.pdf` |
| `f1040s3` | Schedule 3 (Form 1040) - Additional Credits and Payments | `03` | yes | 37 | `forms-instructions-and-publications/forms/f1040s3.pdf` |
| `f1040sb` | Schedule B (Form 1040) - Interest and Ordinary Dividends | `08` | yes | 72 | `forms-instructions-and-publications/forms/f1040sb.pdf` |
| `f1040sc` | Schedule C (Form 1040) - Profit or Loss From Business | `09` | yes | 105 | `forms-instructions-and-publications/forms/f1040sc.pdf` |
| `f1040sd` | Schedule D (Form 1040) - Capital Gains and Losses | `12` | yes | 55 | `forms-instructions-and-publications/forms/f1040sd.pdf` |
| `f1040se` | Schedule E (Form 1040) - Supplemental Income and Loss | `13` | yes | 185 | `forms-instructions-and-publications/forms/f1040se.pdf` |
| `f1040sei` | Schedule EIC (Form 1040) - Earned Income Credit | `43` | yes | 38 | `forms-instructions-and-publications/forms/f1040sei.pdf` |
| `f1040sf` | Schedule F (Form 1040) - Profit or Loss From Farming | `14` | yes | 89 | `forms-instructions-and-publications/forms/f1040sf.pdf` |
| `f1040sh` | Schedule H (Form 1040) - Household Employment Taxes | `44` | yes | 72 | `forms-instructions-and-publications/forms/f1040sh.pdf` |
| `f1040sj` | Schedule J (Form 1040) - Income Averaging for Farmers and Fishermen | `20` | yes | 27 | `forms-instructions-and-publications/forms/f1040sj.pdf` |
| `f1040sr` | Form 1040-SR - U.S. Tax Return for Seniors | `None` | yes | 27 | `forms-instructions-and-publications/forms/f1040sr.pdf` |
| `f1040sse` | Schedule SE (Form 1040) - Self-Employment Tax | `17` | yes | 27 | `forms-instructions-and-publications/forms/f1040sse.pdf` |
| `f1040v` | Form 1040-V - Payment Voucher | `None` | yes | 15 | `forms-instructions-and-publications/forms/f1040v.pdf` |
| `f1040x` | Form 1040-X - Amended U.S. Individual Income Tax Return | `None` | yes | 166 | `forms-instructions-and-publications/forms/f1040x.pdf` |
| `f1098e` | Form 1098-E - Student Loan Interest Statement | `None` | yes | 21 | `forms-instructions-and-publications/forms/f1098e.pdf` |
| `f1116` | Form 1116 - Foreign Tax Credit | `19` | yes | 118 | `forms-instructions-and-publications/forms/f1116.pdf` |
| `f1116sb` | Schedule B (Form 1116) - Foreign Tax Carryover Reconciliation | `None` | yes | 222 | `forms-instructions-and-publications/forms/f1116sb.pdf` |
| `f1116sc` | Schedule C (Form 1116) - Foreign Tax Redeterminations | `19C` | yes | 256 | `forms-instructions-and-publications/forms/f1116sc.pdf` |
| `f1310` | Form 1310 - Statement of Person Claiming Refund Due a Deceased Taxpayer | `87` | yes | 25 | `forms-instructions-and-publications/forms/f1310.pdf` |
| `f14039` | Form 14039 - Identity Theft Affidavit | `None` | yes | 72 | `forms-instructions-and-publications/forms/f14039.pdf` |
| `f14039b` | Form 14039-B - Business Identity Theft Affidavit | `None` | yes | 48 | `forms-instructions-and-publications/forms/f14039b.pdf` |
| `f2106` | Form 2106 - Employee Business Expenses | `129` | yes | 87 | `forms-instructions-and-publications/forms/f2106.pdf` |
| `f2120` | Form 2120 - Multiple Support Declaration | `114` | yes | 16 | `forms-instructions-and-publications/forms/f2120.pdf` |
| `f2210` | Form 2210 - Underpayment of Estimated Tax by Individuals, Estates, and Trusts | `06` | yes | 199 | `forms-instructions-and-publications/forms/f2210.pdf` |
| `f2210_Schedule_AI` | Form 2210 - Schedule AI Annualized Income Installment Method | `None` | yes | 199 | `forms-instructions-and-publications/forms/f2210.pdf` |
| `f2210f` | Form 2210-F - Underpayment of Estimated Tax by Farmers and Fishermen | `6A` | yes | 21 | `forms-instructions-and-publications/forms/f2210f.pdf` |
| `f2441` | Form 2441 - Child and Dependent Care Expenses | `21` | yes | 72 | `forms-instructions-and-publications/forms/f2441.pdf` |
| `f2555` | Form 2555 - Foreign Earned Income | `34` | yes | 160 | `forms-instructions-and-publications/forms/f2555.pdf` |
| `f3115` | Form 3115 - Application for Change in Accounting Method | `None` | yes | 294 | `forms-instructions-and-publications/forms/f3115.pdf` |
| `f3468` | Form 3468 - Investment Credit | `None` | yes | 321 | `forms-instructions-and-publications/forms/f3468.pdf` |
| `f3800` | Form 3800 - General Business Credit | `22` | yes | 1921 | `forms-instructions-and-publications/forms/f3800.pdf` |
| `f3903` | Form 3903 - Moving Expenses | `170` | yes | 10 | `forms-instructions-and-publications/forms/f3903.pdf` |
| `f4136` | Form 4136 - Credit for Federal Tax Paid on Fuels | `79` | yes | 485 | `forms-instructions-and-publications/forms/f4136.pdf` |
| `f4137` | Form 4137 - Social Security and Medicare Tax on Unreported Tip Income | `24` | yes | 34 | `forms-instructions-and-publications/forms/f4137.pdf` |
| `f4255` | Form 4255 - Recapture of Investment Credit | `172` | yes | 646 | `forms-instructions-and-publications/forms/f4255.pdf` |
| `f4506` | Form 4506 - Request for Copy of Tax Return | `None` | yes | 43 | `forms-instructions-and-publications/forms/f4506.pdf` |
| `f4562` | Form 4562 - Depreciation and Amortization | `179` | yes | 277 | `forms-instructions-and-publications/forms/f4562.pdf` |
| `f4684` | Form 4684 - Casualties and Thefts | `26` | yes | 162 | `forms-instructions-and-publications/forms/f4684.pdf` |
| `f4797` | Form 4797 - Sales of Business Property | `27` | yes | 182 | `forms-instructions-and-publications/forms/f4797.pdf` |
| `f4835` | Form 4835 - Farm Rental Income and Expenses | `37` | yes | 63 | `forms-instructions-and-publications/forms/f4835.pdf` |
| `f4852` | Form 4852 - Substitute for Form W-2 or Form 1099-R | `None` | yes | 34 | `forms-instructions-and-publications/forms/f4852.pdf` |
| `f4868` | Form 4868 - Application for Automatic Extension of Time To File | `None` | yes | 17 | `forms-instructions-and-publications/forms/f4868.pdf` |
| `f4952` | Form 4952 - Investment Interest Expense Deduction | `51` | yes | 17 | `forms-instructions-and-publications/forms/f4952.pdf` |
| `f4972` | Form 4972 - Tax on Lump-Sum Distributions | `28` | yes | 58 | `forms-instructions-and-publications/forms/f4972.pdf` |
| `f5329` | Form 5329 - Additional Taxes on Qualified Plans and Other Tax-Favored Accounts | `29` | yes | 75 | `forms-instructions-and-publications/forms/f5329.pdf` |
| `f5405` | Form 5405 - Repayment of the First-Time Homebuyer Credit | `58` | yes | 25 | `forms-instructions-and-publications/forms/f5405.pdf` |
| `f5695` | Form 5695 - Residential Energy Credits | `75` | yes | 167 | `forms-instructions-and-publications/forms/f5695.pdf` |
| `f6198` | Form 6198 - At-Risk Limitations | `31` | yes | 34 | `forms-instructions-and-publications/forms/f6198.pdf` |
| `f6251` | Form 6251 - Alternative Minimum Tax for Individuals | `32` | yes | 62 | `forms-instructions-and-publications/forms/f6251.pdf` |
| `f6252` | Form 6252 - Installment Sale Income | `67` | yes | 49 | `forms-instructions-and-publications/forms/f6252.pdf` |
| `f6781` | Form 6781 - Gains and Losses From Section 1256 Contracts and Straddles | `None` | yes | 71 | `forms-instructions-and-publications/forms/f6781.pdf` |
| `f7203` | Form 7203 - S Corporation Shareholder Stock and Debt Basis Limitations | `None` | yes | 188 | `forms-instructions-and-publications/forms/f7203.pdf` |
| `f7206` | Form 7206 - Self-Employed Health Insurance Deduction | `None` | yes | 16 | `forms-instructions-and-publications/forms/f7206.pdf` |
| `f8283` | Form 8283 - Noncash Charitable Contributions | `36` | yes | 117 | `forms-instructions-and-publications/forms/f8283.pdf` |
| `f8332` | Form 8332 - Release/Revocation of Release of Claim to Exemption for Child by Custodial Parent | `None` | yes | 11 | `forms-instructions-and-publications/forms/f8332.pdf` |
| `f8379` | Form 8379 - Injured Spouse Allocation | `None` | yes | 63 | `forms-instructions-and-publications/forms/f8379.pdf` |
| `f8396` | Form 8396 - Mortgage Interest Credit | `138` | yes | 26 | `forms-instructions-and-publications/forms/f8396.pdf` |
| `f8453` | Form 8453 - U.S. Individual Income Tax Transmittal for an IRS e-file Return | `None` | yes | 23 | `forms-instructions-and-publications/forms/f8453.pdf` |
| `f8582` | Form 8582 - Passive Activity Loss Limitations | `858` | yes | 205 | `forms-instructions-and-publications/forms/f8582.pdf` |
| `f8582cr` | Form 8582-CR - Passive Activity Credit Limitations | `None` | yes | 52 | `forms-instructions-and-publications/forms/f8582cr.pdf` |
| `f8586` | Form 8586 - Low-Income Housing Credit | `None` | yes | 14 | `forms-instructions-and-publications/forms/f8586.pdf` |
| `f8606` | Form 8606 - Nondeductible IRAs | `48` | yes | 45 | `forms-instructions-and-publications/forms/f8606.pdf` |
| `f8615` | Form 8615 - Tax for Certain Children Who Have Unearned Income | `33` | yes | 32 | `forms-instructions-and-publications/forms/f8615.pdf` |
| `f8801` | Form 8801 - Credit for Prior Year Minimum Tax | `801` | yes | 57 | `forms-instructions-and-publications/forms/f8801.pdf` |
| `f8814` | Form 8814 - Parents' Election To Report Child's Interest and Dividends | `40` | yes | 26 | `forms-instructions-and-publications/forms/f8814.pdf` |
| `f8815` | Form 8815 - Exclusion of Interest From Series EE and I U.S. Savings Bonds Issued After 1989 | `None` | yes | 39 | `forms-instructions-and-publications/forms/f8815.pdf` |
| `f8822` | Form 8822 - Change of Address | `None` | yes | 25 | `forms-instructions-and-publications/forms/f8822.pdf` |
| `f8824` | Form 8824 - Like-Kind Exchanges | `None` | yes | 63 | `forms-instructions-and-publications/forms/f8824.pdf` |
| `f8829` | Form 8829 - Expenses for Business Use of Your Home | `None` | yes | 58 | `forms-instructions-and-publications/forms/f8829.pdf` |
| `f8834` | Form 8834 - Qualified Electric Vehicle Credit | `None` | yes | 11 | `forms-instructions-and-publications/forms/f8834.pdf` |
| `f8839` | Form 8839 - Qualified Adoption Expenses | `38` | yes | 100 | `forms-instructions-and-publications/forms/f8839.pdf` |
| `f8853` | Form 8853 - Archer MSAs and Long-Term Care Insurance Contracts | `39` | yes | 38 | `forms-instructions-and-publications/forms/f8853.pdf` |
| `f8857` | Form 8857 - Request for Innocent Spouse Relief | `None` | yes | 208 | `forms-instructions-and-publications/forms/f8857.pdf` |
| `f8859` | Form 8859 - District of Columbia First-Time Homebuyer Credit | `None` | yes | 9 | `forms-instructions-and-publications/forms/f8859.pdf` |
| `f8862` | Form 8862 - Information To Claim Certain Credits After Disallowance | `None` | yes | 109 | `forms-instructions-and-publications/forms/f8862.pdf` |
| `f8863` | Form 8863 - Education Credits | `50` | yes | 77 | `forms-instructions-and-publications/forms/f8863.pdf` |
| `f8880` | Form 8880 - Credit for Qualified Retirement Savings Contributions | `54` | yes | 23 | `forms-instructions-and-publications/forms/f8880.pdf` |
| `f8881` | Form 8881 - Credit for Small Employer Pension Plan Startup Costs | `None` | yes | 29 | `forms-instructions-and-publications/forms/f8881.pdf` |
| `f8888` | Form 8888 - Allocation of Refund | `56` | yes | 20 | `forms-instructions-and-publications/forms/f8888.pdf` |
| `f8889` | Form 8889 - Health Savings Accounts | `52` | yes | 27 | `forms-instructions-and-publications/forms/f8889.pdf` |
| `f8903` | Form 8903 - Domestic Production Activities Deduction | `None` | yes | 78 | `forms-instructions-and-publications/forms/f8903.pdf` |
| `f8911` | Form 8911 - Alternative Fuel Vehicle Refueling Property Credit | `None` | yes | 15 | `forms-instructions-and-publications/forms/f8911.pdf` |
| `f8915d` | Form 8915-D - Qualified 2019 Disaster Retirement Plan Distributions and Repayments | `None` | yes | 30 | `forms-instructions-and-publications/forms/f8915d.pdf` |
| `f8915f` | Form 8915-F - Qualified Disaster Retirement Plan Distributions and Repayments | `None` | yes | 101 | `forms-instructions-and-publications/forms/f8915f.pdf` |
| `f8919` | Form 8919 - Uncollected Social Security and Medicare Tax on Wages | `61` | yes | 40 | `forms-instructions-and-publications/forms/f8919.pdf` |
| `f8936` | Form 8936 - Clean Vehicle Credits | `69` | yes | 31 | `forms-instructions-and-publications/forms/f8936.pdf` |
| `f8938` | Form 8938 - Statement of Specified Foreign Financial Assets | `None` | yes | 131 | `forms-instructions-and-publications/forms/f8938.pdf` |
| `f8941` | Form 8941 - Credit for Small Employer Health Insurance Premiums | `65` | yes | 28 | `forms-instructions-and-publications/forms/f8941.pdf` |
| `f8949` | Form 8949 - Sales and Other Dispositions of Capital Assets | `None` | yes | 202 | `forms-instructions-and-publications/forms/f8949.pdf` |
| `f8958` | Form 8958 - Allocation of Tax Amounts Between Certain Individuals in Community Property States | `63` | yes | 202 | `forms-instructions-and-publications/forms/f8958.pdf` |
| `f8959` | Form 8959 - Additional Medicare Tax | `71` | yes | 26 | `forms-instructions-and-publications/forms/f8959.pdf` |
| `f8960` | Form 8960 - Net Investment Income Tax | `72` | yes | 38 | `forms-instructions-and-publications/forms/f8960.pdf` |
| `f8962` | Form 8962 - Premium Tax Credit | `73` | yes | 141 | `forms-instructions-and-publications/forms/f8962.pdf` |
| `f8994` | Form 8994 - Employer Credit for Paid Family and Medical Leave | `None` | yes | 13 | `forms-instructions-and-publications/forms/f8994.pdf` |
| `f8995` | Form 8995 - Qualified Business Income Deduction Simplified Computation | `55` | yes | 33 | `forms-instructions-and-publications/forms/f8995.pdf` |
| `f8995a` | Form 8995-A - Qualified Business Income Deduction | `55` | yes | 111 | `forms-instructions-and-publications/forms/f8995a.pdf` |
| `f9000` | Form 9000 - Alternative Media Preference | `77` | yes | 14 | `forms-instructions-and-publications/forms/f9000.pdf` |
| `f9465` | Form 9465 - Installment Agreement Request | `None` | yes | 66 | `forms-instructions-and-publications/forms/f9465.pdf` |
| `f982` | Form 982 - Reduction of Tax Attributes Due to Discharge of Indebtedness | `None` | yes | 27 | `forms-instructions-and-publications/forms/f982.pdf` |
| `fss4` | Form SS-4 - Application for Employer Identification Number | `None` | yes | 89 | `forms-instructions-and-publications/forms/fss4.pdf` |
| `fw4` | Form W-4 - Employee's Withholding Certificate | `None` | yes | 48 | `forms-instructions-and-publications/forms/fw4.pdf` |

## Forms Missing Preview PDFs

| Form ID | Name | Filing sequence | Fillable | Field count | PDF source |
| --- | --- | --- | --- | ---: | --- |
| `f1040_Federal_Info_Worksheet` | Form 1040 - Federal Information Worksheet | `None` | no | 0 | `None` |
| `f1040_Line_12e_Standard_Deduction_Dependents` | Form 1040 - Standard Deduction Worksheet for Dependents (Line 12e) | `None` | no | 0 | `None` |
| `f1040_Line_16_Foreign_Earned_Income_Tax` | Form 1040 - Foreign Earned Income Tax Worksheet (Line 16) | `None` | no | 0 | `None` |
| `f1040_Line_16_Qualified_Dividends_Capital_Gain_Tax` | Form 1040 - Qualified Dividends and Capital Gain Tax Worksheet (Line 16) | `None` | no | 0 | `None` |
| `f1040_Line_27a_EIC_Worksheet_A` | Form 1040 - EIC Worksheet A (Line 27a) | `None` | no | 0 | `None` |
| `f1040_Line_27a_EIC_Worksheet_B` | Form 1040 - EIC Worksheet B (Line 27a) | `None` | no | 0 | `None` |
| `f1040_Line_27a_EIC_Worksheet_B_Continued` | Form 1040 - EIC Worksheet B (Continued) | `None` | no | 0 | `None` |
| `f1040_Lines_5a_and_5b` | Form 1040 - Simplified Method Worksheet (Lines 5a and 5b) | `None` | no | 0 | `None` |
| `f1040_Lines_6a_and_6b` | Form 1040 - Social Security Benefits Worksheet (Lines 6a and 6b) | `None` | no | 0 | `None` |
| `f1040_Multiple_Trades_Or_Businesses` | Form 1040 - Multiple Trades or Businesses Worksheet | `None` | no | 0 | `None` |
| `f1040_Qualified_Overtime_More_Than_One_Employer` | Form 1040 - Qualified Overtime Compensation From More Than One Employer Worksheet | `None` | no | 0 | `None` |
| `f1040_Qualified_Overtime_More_Than_One_Payor` | Form 1040 - Qualified Overtime Compensation From More Than One Payor Worksheet | `None` | no | 0 | `None` |
| `f1040_Qualified_Tips_More_Than_One_Employer` | Form 1040 - Qualified Tips From More Than One Employer Worksheet | `None` | no | 0 | `None` |
| `f1040_Schedule_1_Line_17_Self_Employed_Health_Insurance` | Schedule 1 (Form 1040) - Self-Employed Health Insurance Deduction Worksheet (Line 17) | `None` | no | 0 | `None` |
| `f1040_Schedule_1_Line_1_State_Local_Tax_Refund` | Schedule 1 (Form 1040) - State and Local Income Tax Refund Worksheet (Line 1) | `None` | no | 0 | `None` |
| `f1040_Schedule_1_Line_20_IRA_Deduction` | Schedule 1 (Form 1040) - IRA Deduction Worksheet (Line 20) | `None` | no | 0 | `None` |
| `f1040_Schedule_1_Line_20_IRA_Deduction_Continued` | Schedule 1 (Form 1040) - IRA Deduction Worksheet (Continued) | `None` | no | 0 | `None` |
| `f1040_Schedule_1_Line_21_Student_Loan_Interest` | Schedule 1 (Form 1040) - Student Loan Interest Deduction Worksheet (Line 21) | `None` | no | 0 | `None` |
| `f1040_Schedule_3_Line_6l_Negative_Form_8978` | Schedule 3 (Form 1040) - Negative Form 8978 Adjustment Worksheet (Line 6l) | `None` | no | 0 | `None` |
| `f1040_Tax_Computation` | Form 1040 - Tax Computation Worksheet | `None` | no | 0 | `None` |
| `f1040sd_28_Rate_Gain` | Schedule D (Form 1040) - 28% Rate Gain Worksheet (Line 18) | `None` | no | 0 | `None` |
| `f1040sd_Capital_Loss_Carryover` | Schedule D (Form 1040) - Capital Loss Carryover Worksheet (Lines 6 and 14) | `None` | no | 0 | `None` |
| `f1040sd_Schedule_D_Tax` | Schedule D (Form 1040) - Tax Worksheet | `None` | no | 0 | `None` |
| `f1040sd_Unrecaptured_Section_1250_Gain` | Schedule D (Form 1040) - Unrecaptured Section 1250 Gain Worksheet (Line 19) | `None` | no | 0 | `None` |
| `f1040sr_schedule_r` | Schedule R (Form 1040) - Credit for the Elderly or the Disabled | `16` | no | 0 | `None` |
| `f8812_Additional_Medicare_Tax_and_RRTA_Tax_Worksheet` | Schedule 8812 (Form 1040) - Additional Medicare Tax and RRTA Tax Worksheet (Line 21) | `None` | no | 0 | `None` |
| `f8812_Earned_Income_Worksheet` | Schedule 8812 (Form 1040) - Earned Income Worksheet / Credit Limit Worksheet B | `None` | no | 0 | `None` |
| `f8910` | Form 8910 - Alternative Motor Vehicle Credit | `None` | no | 0 | `None` |
| `f8936a` | Form 8936-A - Qualified Commercial Clean Vehicle Credit | `None` | no | 0 | `None` |

## Filled Preview Ready Blocks

| Block | Description | Fillable | Field count | PDF source |
| --- | --- | --- | ---: | --- |
| `f1040.1098` | Form(s) 1098 | no | 0 | `forms-instructions-and-publications/information-returns/f1098.pdf` |
| `f1040.1099_div` | Form(s) 1099-DIV | no | 0 | `forms-instructions-and-publications/information-returns/f1099div.pdf` |
| `f1040.1099_int` | Form(s) 1099-INT | no | 0 | `forms-instructions-and-publications/information-returns/f1099int.pdf` |
| `f1040.1099_r` | Form(s) 1099-R | no | 0 | `forms-instructions-and-publications/information-returns/f1099r.pdf` |
| `f1040.w2` | Form(s) W-2 | no | 0 | `forms-instructions-and-publications/information-returns/fw2.pdf` |

## Raw Preview Only Blocks

| Block | Description | Fillable | Field count | PDF source |
| --- | --- | --- | ---: | --- |
| `f1040.1095_a` | Form(s) 1095-A | yes | 81 | `forms-instructions-and-publications/information-returns/f1095a.pdf` |
| `f1040.1098_c` | Form(s) 1098-C | yes | 79 | `forms-instructions-and-publications/information-returns/f1098c.pdf` |
| `f1040.1098_e` | Form(s) 1098-E | no | 0 | `forms-instructions-and-publications/information-returns/f1098e.pdf` |
| `f1040.1098_t` | Form(s) 1098-T | no | 0 | `forms-instructions-and-publications/information-returns/f1098t.pdf` |
| `f1040.1099_a` | Form(s) 1099-A | yes | 31 | `forms-instructions-and-publications/information-returns/f1099a.pdf` |
| `f1040.1099_b` | Form(s) 1099-B | yes | 163 | `forms-instructions-and-publications/information-returns/f1099b--2025.pdf` |
| `f1040.1099_g` | Form(s) 1099-G | no | 0 | `forms-instructions-and-publications/information-returns/f1099g.pdf` |
| `f1040.1099_k` | Form(s) 1099-K | no | 0 | `forms-instructions-and-publications/information-returns/f1099k.pdf` |
| `f1040.1099_misc` | Form(s) 1099-MISC | no | 0 | `forms-instructions-and-publications/information-returns/f1099msc.pdf` |
| `f1040.1099_nec` | Form(s) 1099-NEC | no | 0 | `forms-instructions-and-publications/information-returns/f1099nec.pdf` |
| `f1040.1099_oid` | Form(s) 1099-OID | yes | 111 | `forms-instructions-and-publications/information-returns/f1099oid.pdf` |
| `f1040.1099_s` | Form(s) 1099-S | no | 0 | `forms-instructions-and-publications/information-returns/f1099s.pdf` |
| `f1040.2439` | Form(s) 2439 | yes | 64 | `forms-instructions-and-publications/information-returns/f2439.pdf` |
| `f1040.k1_1041` | Form(s) Schedule K-1 (Form 1041) | yes | 74 | `forms-instructions-and-publications/information-returns/f1041sk1.pdf` |
| `f1040.k1_1065` | Form(s) Schedule K-1 (Form 1065) | yes | 111 | `forms-instructions-and-publications/information-returns/f1065sk1.pdf` |
| `f1040.k1_1120s` | Form(s) Schedule K-1 (Form 1120-S) | yes | 114 | `forms-instructions-and-publications/information-returns/f1120ssk.pdf` |
| `f1040.k3_1065` | Form(s) Schedule K-3 (Form 1065) | yes | 2862 | `forms-instructions-and-publications/information-returns/f1065sk3.pdf` |
| `f1040.k3_1120s` | Form(s) Schedule K-3 (Form 1120-S) | yes | 2116 | `forms-instructions-and-publications/information-returns/f1120sk3.pdf` |
| `f1040.rrta_w2` | RRTA amounts from Form(s) W-2 box 14 | no | 0 | `forms-instructions-and-publications/information-returns/fw2.pdf` |
| `f1040.w2g` | Form(s) W-2G | no | 0 | `forms-instructions-and-publications/information-returns/fw2g.pdf` |
| `f1040.w2pr_499r2` | Puerto Rico Form(s) 499R-2/W-2PR | no | 0 | `forms-instructions-and-publications/information-returns/fw2.pdf` |

## Blocks Missing Preview PDFs

| Block | Description | Fillable | Field count | PDF source |
| --- | --- | --- | ---: | --- |
| `f1040.1099_da` | Form(s) 1099-DA | no | 0 | `None` |
| `f1040.ct2` | Form(s) CT-2 | no | 0 | `None` |
| `f1040.dependents` | Dependents | no | 0 | `None` |
| `f1040.estimated_tax_payments_detail` | Estimated tax payment details | no | 0 | `None` |
| `f1040.foreign_tax_credit_items` | Foreign tax credit source items | no | 0 | `None` |
| `f1040.investment_expenses` | Investment expense items other than interest | no | 0 | `None` |
| `f1040.investment_interest_expense` | Investment interest expense items | no | 0 | `None` |
| `f1040.investment_property_dispositions` | Investment-property dispositions for Form 4952 | no | 0 | `None` |
| `f1040.rrb_1099` | Form(s) RRB-1099 | no | 0 | `None` |
| `f1040.ssa_1099` | Form(s) SSA-1099 | no | 0 | `None` |
| `f1040sei.qualifying_children` | Qualifying children | no | 0 | `None` |
| `f1116sb.carryover_reconciliation` | Schedule B carryover reconciliation rows | no | 0 | `None` |
| `f1116sc.decrease_redeterminations` | Decrease redetermination entries | no | 0 | `None` |
| `f1116sc.increase_redeterminations` | Increase redetermination entries | no | 0 | `None` |
| `f1116sc.redetermination_summary` | Redetermination summary rows | no | 0 | `None` |
| `f8949.carryforward_records` | Carryforward records | no | 0 | `None` |
| `f8949.lt_box_d` | Long-term Box D transactions | no | 0 | `None` |
| `f8949.lt_box_e` | Long-term Box E transactions | no | 0 | `None` |
| `f8949.lt_box_f` | Long-term Box F transactions | no | 0 | `None` |
| `f8949.lt_box_j` | Long-term Box J transactions | no | 0 | `None` |
| `f8949.lt_box_k` | Long-term Box K transactions | no | 0 | `None` |
| `f8949.lt_box_l` | Long-term Box L transactions | no | 0 | `None` |
| `f8949.st_box_a` | Short-term Box A transactions | no | 0 | `None` |
| `f8949.st_box_b` | Short-term Box B transactions | no | 0 | `None` |
| `f8949.st_box_c` | Short-term Box C transactions | no | 0 | `None` |
| `f8949.st_box_g` | Short-term Box G transactions | no | 0 | `None` |
| `f8949.st_box_h` | Short-term Box H transactions | no | 0 | `None` |
| `f8949.st_box_i` | Short-term Box I transactions | no | 0 | `None` |

## Current Gaps

- Many top-level forms now have explicit local PDFs, but only a small subset currently have mapping files for filled previews.
- Most missing top-level preview PDFs are true worksheets/helper sheets rather than printable IRS forms.
- Several source-document blocks have usable raw PDFs without mappings; those are good candidates for later filled-preview work.
- The report is driven by explicit JSON metadata first, so keeping `pdf_source_path`, `fillable_form`, and `pdf_field_count` current is now the audit-critical maintenance task.
