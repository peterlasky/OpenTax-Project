#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "federal_1040_2025.json"
JURISDICTION_KEY = "Federal 2025"
OUTPUT_PDF_DIR = PROJECT_ROOT / "forms-instructions-and-publications" / "generated-worksheets"
OUTPUT_MAP_DIR = PROJECT_ROOT / "reference-data" / "federal" / "2025" / "pdf_field_maps"
MANIFEST_PATH = OUTPUT_PDF_DIR / "manifest.json"

PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 42.0
RIGHT_MARGIN = 42.0
TOP_MARGIN = 42.0
BOTTOM_MARGIN = 42.0
LABEL_FONT = "Helvetica-Bold"
BODY_FONT = "Helvetica"
MONO_FONT = "Courier"
TITLE_COLOR = colors.black
SUBTITLE_COLOR = colors.HexColor("#333333")
SECTION_FILL = colors.HexColor("#E9ECEF")
LINE_COLOR = colors.HexColor("#4A4A4A")
SECTION_BAR_HEIGHT = 14.0
SECTION_CONTENT_GAP = 42.0
TEXT_ROW_GAP = 18.0
CHECKBOX_ROW_HEIGHT = 34.0


@dataclass
class WorksheetField:
    cell_id: str
    label: str
    source: str
    widget_type: str
    format_code: str
    explanation: str
    page: int = 1
    rect: tuple[float, float, float, float] | None = None
    font_size: float | None = None


def load_model() -> dict[str, Any]:
    payload = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    jurisdiction = payload.get(JURISDICTION_KEY)
    if not isinstance(jurisdiction, dict):
        raise RuntimeError(f"Missing jurisdiction {JURISDICTION_KEY!r} in {MODEL_PATH}")
    return payload


def is_worksheet(form_id: str, form_data: dict[str, Any]) -> bool:
    meta = form_data.get("_meta") or {}
    name = str(meta.get("name", "")).lower()
    return "worksheet" in form_id.lower() or "worksheet" in name


def iter_worksheets(jurisdiction: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    results: list[tuple[str, dict[str, Any]]] = []
    for form_id, form_data in jurisdiction.items():
        if not isinstance(form_data, dict):
            continue
        if is_worksheet(form_id, form_data):
            results.append((form_id, form_data))
    return results


def cell_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[float, str]:
    cell_id, cell = item
    order = cell.get("order", 10**9)
    if not isinstance(order, (int, float)):
        order = 10**9
    return float(order), cell_id


def format_code_for_cell(cell: dict[str, Any]) -> str:
    raw = str(cell.get("format", "text"))
    if raw in {"0", "0.00", "0.00%"}:
        return "amount"
    return "text"


def label_for_cell(cell_id: str, cell: dict[str, Any]) -> str:
    description = str(cell.get("description") or "").strip()
    if description:
        return description
    return cell_id.replace("_", " ").title()


def flatten_worksheet_cells(form_data: dict[str, Any]) -> list[WorksheetField]:
    fields: list[WorksheetField] = []
    cells = form_data.get("cells") or {}
    for cell_id, cell in sorted(
        [(cell_id, cell) for cell_id, cell in cells.items() if isinstance(cell, dict)],
        key=cell_sort_key,
    ):
        raw_format = str(cell.get("format", "text"))
        fields.append(
            WorksheetField(
                cell_id=cell_id,
                label=label_for_cell(cell_id, cell),
                source=cell_id,
                widget_type="button" if raw_format == "boolean" else "text",
                format_code=format_code_for_cell(cell),
                explanation=str(cell.get("explanation") or "").strip(),
            )
        )
    return fields


def draw_page_header(pdf: canvas.Canvas, title: str, subtitle: str, page_number: int) -> None:
    pdf.setStrokeColor(LINE_COLOR)
    pdf.setFillColor(TITLE_COLOR)
    pdf.setFont(LABEL_FONT, 16)
    pdf.drawString(LEFT_MARGIN, PAGE_HEIGHT - TOP_MARGIN + 4, title)
    pdf.setFont(BODY_FONT, 9)
    pdf.setFillColor(SUBTITLE_COLOR)
    pdf.drawString(LEFT_MARGIN, PAGE_HEIGHT - TOP_MARGIN - 12, subtitle)
    pdf.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - TOP_MARGIN + 4, f"Page {page_number}")
    pdf.line(LEFT_MARGIN, PAGE_HEIGHT - TOP_MARGIN - 18, PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - TOP_MARGIN - 18)


def draw_section_bar(pdf: canvas.Canvas, y_top: float, title: str) -> None:
    pdf.setFillColor(SECTION_FILL)
    pdf.setStrokeColor(LINE_COLOR)
    pdf.rect(
        LEFT_MARGIN,
        y_top - SECTION_BAR_HEIGHT,
        PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
        SECTION_BAR_HEIGHT,
        stroke=0,
        fill=1,
    )
    pdf.setFillColor(colors.black)
    pdf.setFont(LABEL_FONT, 9)
    pdf.drawString(LEFT_MARGIN + 4, y_top - 10.5, title)


def usable_font(field: WorksheetField) -> str:
    if "ssn" in field.cell_id.lower():
        return MONO_FONT
    return BODY_FONT


def text_field_dimensions(field: WorksheetField, max_width: float) -> tuple[float, float]:
    if field.format_code == "amount":
        return 120.0, 18.0
    if any(token in field.cell_id.lower() for token in ("address", "name", "explanation", "city", "country")):
        return max_width, 18.0
    return min(240.0, max_width), 18.0


def draw_text_field(pdf: canvas.Canvas, field: WorksheetField, x: float, y: float, width: float, height: float) -> None:
    font_name = usable_font(field)
    font_size = 9.0 if field.format_code != "amount" else 10.0
    pdf.setFont(LABEL_FONT, 7.5)
    pdf.setFillColor(colors.black)
    pdf.drawString(x, y + height + 3.5, field.label)
    pdf.acroForm.textfield(
        name=field.cell_id,
        x=x,
        y=y,
        width=width,
        height=height,
        fontName=font_name,
        fontSize=font_size,
        borderStyle="solid",
        borderWidth=0.8,
        borderColor=LINE_COLOR,
        textColor=colors.black,
        fillColor=colors.white,
        forceBorder=True,
    )
    field.font_size = font_size
    field.rect = (x, y, x + width, y + height)


def draw_checkbox_field(pdf: canvas.Canvas, field: WorksheetField, x: float, y: float) -> None:
    size = 11.0
    pdf.setFont(BODY_FONT, 8.5)
    pdf.drawString(x + size + 6, y + 1.5, field.label)
    pdf.acroForm.checkbox(
        name=field.cell_id,
        x=x,
        y=y,
        size=size,
        borderColor=LINE_COLOR,
        fillColor=colors.white,
        textColor=colors.black,
        buttonStyle="check",
        checked=False,
    )
    field.rect = (x, y, x + size, y + size)


def generate_template_pdf(form_id: str, form_data: dict[str, Any]) -> tuple[str, list[WorksheetField], int]:
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{form_id}_worksheet.pdf"
    output_path = OUTPUT_PDF_DIR / filename
    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    title = str((form_data.get("_meta") or {}).get("name") or form_id)
    subtitle = f"OpenTax generated worksheet template for {form_id}"
    fields = flatten_worksheet_cells(form_data)

    page_number = 1
    draw_page_header(pdf, title, subtitle, page_number)
    y_cursor = PAGE_HEIGHT - TOP_MARGIN - 42.0
    draw_section_bar(pdf, y_cursor, "Worksheet Fields")
    y_cursor -= SECTION_CONTENT_GAP

    def next_page() -> None:
        nonlocal page_number, y_cursor
        pdf.showPage()
        page_number += 1
        draw_page_header(pdf, title, subtitle, page_number)
        y_cursor = PAGE_HEIGHT - TOP_MARGIN - 42.0
        draw_section_bar(pdf, y_cursor, "Worksheet Fields")
        y_cursor -= SECTION_CONTENT_GAP

    max_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    for field in fields:
        if field.widget_type == "button":
            needed = CHECKBOX_ROW_HEIGHT
        else:
            _, height = text_field_dimensions(field, max_width)
            needed = height + TEXT_ROW_GAP
        if y_cursor - needed < BOTTOM_MARGIN:
            next_page()
        if field.widget_type == "button":
            draw_checkbox_field(pdf, field, LEFT_MARGIN, y_cursor)
            y_cursor -= CHECKBOX_ROW_HEIGHT
            continue
        width, height = text_field_dimensions(field, max_width)
        draw_text_field(pdf, field, LEFT_MARGIN, y_cursor, width, height)
        y_cursor -= height + TEXT_ROW_GAP

    pdf.save()
    field_count = len(PdfReader(str(output_path)).get_fields() or {})
    return str(output_path.relative_to(PROJECT_ROOT)), fields, field_count


def build_field_map(relative_pdf_path: str, fields: list[WorksheetField]) -> dict[str, Any]:
    widgets: list[dict[str, Any]] = []
    for field in fields:
        widget = {
            "field": field.cell_id,
            "source": field.source,
            "cell_ref": field.cell_id,
            "render_mode": "checkbox" if field.widget_type == "button" else "field_text",
            "widget_type": "button" if field.widget_type == "button" else "text",
            "format": field.format_code,
            "mapping_method": "generated_worksheet_template",
        }
        if field.rect is not None:
            widget["page"] = field.page
            widget["rect"] = [round(value, 3) for value in field.rect]
        if field.font_size is not None:
            widget["font_size"] = field.font_size
        widgets.append(widget)
    return {"source_pdf": relative_pdf_path, "widgets": widgets}


def main() -> None:
    payload = load_model()
    jurisdiction = payload[JURISDICTION_KEY]
    OUTPUT_MAP_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []

    for form_id, form_data in iter_worksheets(jurisdiction):
        relative_pdf_path, fields, field_count = generate_template_pdf(form_id, form_data)
        field_map = build_field_map(relative_pdf_path, fields)
        (OUTPUT_MAP_DIR / f"{form_id}.json").write_text(json.dumps(field_map, indent=2) + "\n", encoding="utf-8")
        meta = form_data.setdefault("_meta", {})
        meta["fillable_form"] = True
        meta["pdf_source_path"] = relative_pdf_path
        meta["pdf_field_count"] = field_count
        manifest.append(
            {
                "form_id": form_id,
                "pdf_source_path": relative_pdf_path,
                "pdf_field_count": field_count,
            }
        )

    MODEL_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps({"generated_worksheets": manifest}, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(manifest)} worksheet templates in {OUTPUT_PDF_DIR}")


if __name__ == "__main__":
    main()
