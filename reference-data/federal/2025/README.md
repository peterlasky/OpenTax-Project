# Federal 2025 Reference Data

This directory holds year-specific federal lookup data that should not be hardcoded into individual forms or worksheets.

Use this directory for three kinds of artifacts:

- Lookup tables: discrete IRS tables where the answer comes from a published row or range.
- Rate schedules: bracket/rate data used by tax-computation worksheets.
- Worksheet parameter tables: small reference tables or constants used by worksheets.

Current inventory:

- `ordinary_income_tax.json`
  Form 1040 line 16 ordinary-income tax data. This includes the Tax Table and the higher-income rate-schedule data used when the table no longer applies.

- `earned_income_credit.json`
  EIC lookup data used by the 2025 EIC worksheets and Form 1040 line 27a.

- `simplified_method_tables.json`
  Table 1 and Table 2 inputs for the Simplified Method Worksheet for Form 1040 lines 5a and 5b.

- `capital_gain_parameters.json`
  Filing-status thresholds and related constants used by the Qualified Dividends and Capital Gain Tax Worksheet and the Schedule D Tax Worksheet.

- `manifest.json`
  Machine-readable inventory of the datasets in this directory, including status, source documents, and which forms currently depend on them.

Rules:

- Keep the data versioned by tax year.
- Do not bury lookup tables inside `federal_1040_2025.json`.
- Do not encode IRS lookup tables as ad hoc `if` ladders inside worksheet equations.
- If a value comes from a published table, capture the table here and let the evaluator read from it.
- If a value comes from a worksheet or bracket schedule, store the supporting schedule data here when that is cleaner than hardcoding constants into form logic.
