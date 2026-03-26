# PDF Field Maps

This directory contains the intermediate PDF widget catalog for each modeled fillable federal 2025 form with `pdf_field_count > 1`.

Each `<form_id>.json` file is separate from the master tax-logic JSON and records:

- `source_pdf`: the local IRS PDF used for preview/fill work
- `pdf_field_count`: the fillable field count captured in the master model
- `widget_count`: the number of extracted PDF widgets
- `mapped_widget_count`: widgets that already have a known `source`
- `renderable_widget_count`: widgets that can currently be rendered by the app
- `widgets`: one entry per PDF widget, including page, rectangle, widget type, and any known `source`, `cell_ref`, `render_mode`, and formatting metadata

The app prefers these files when rendering filled previews. If a form has a field map but no renderable widget mappings yet, the app falls back to the raw PDF preview.

Regenerate the directory with:

```bash
.venv/bin/python forms-instructions-and-publications/forms/build_pdf_field_maps.py
```
