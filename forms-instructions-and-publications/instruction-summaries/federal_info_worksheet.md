# Federal Info Worksheet

Source file: `forms-instructions-and-publications/worksheets/Federal Info Worksheet.pdf`

Role in the tax program:

- intake root for personal identity, address, filing status, age-adjacent facts, disability flags, and dependent-of-another facts
- upstream source for many top-of-form `1040` identity and status fields

Important source cues visible on the worksheet face:

- includes `Date of birth`
- includes `Age as of 1-1-2026`
- includes filing status selection
- includes disability, dependent-of-another, and presidential-election-fund facts
- includes explicit spouse / taxpayer split for many facts

Implementation implications:

- if DOB is collected, age as of `1-1-2026` should normally be computed rather than left manual or defaulted
- filing status should remain one-hot and should flow into `f1040`
- address and phone presentation choices belong here and should flow upward to the return display

Audit cues:

- any field whose label is an obvious transformation of another captured fact should be checked for a formula before accepting a manual/default-only implementation
- this worksheet is a strong candidate for recurring source-based audits because it sits at the root of many downstream branches
