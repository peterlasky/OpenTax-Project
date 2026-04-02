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
TITLE_FONT = "Helvetica-Bold"
SUBTITLE_FONT = "Helvetica"
LABEL_FONT = "Helvetica-Bold"
BODY_FONT = "Helvetica"
MONO_FONT = "Courier"
TITLE_COLOR = colors.black
SUBTITLE_COLOR = colors.HexColor("#333333")
LINE_COLOR = colors.HexColor("#1F2937")
TITLE_SIZE = 14.0
SUBTITLE_SIZE = 8.5
LABEL_SIZE = 7.5
BODY_SIZE = 9.5
PAGE_HEADER_LINE_Y = PAGE_HEIGHT - TOP_MARGIN - 18.0
PAGE_CONTENT_TOP = PAGE_HEIGHT - TOP_MARGIN - 34.0
TEXT_ROW_GAP = 22.0
CHECKBOX_ROW_HEIGHT = 24.0


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


def draw_page_header(
    pdf: canvas.Canvas,
    title: str,
    subtitle: str,
    page_number: int,
    total_pages: int,
) -> None:
    pdf.setStrokeColor(LINE_COLOR)
    pdf.setFillColor(TITLE_COLOR)
    pdf.setFont(TITLE_FONT, TITLE_SIZE)
    pdf.drawString(LEFT_MARGIN, PAGE_HEIGHT - TOP_MARGIN + 4, title)
    pdf.setFont(SUBTITLE_FONT, SUBTITLE_SIZE)
    pdf.setFillColor(SUBTITLE_COLOR)
    pdf.drawString(LEFT_MARGIN, PAGE_HEIGHT - TOP_MARGIN - 11, subtitle)
    pdf.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - TOP_MARGIN + 2, f"Page {page_number} of {total_pages}")
    pdf.line(LEFT_MARGIN, PAGE_HEADER_LINE_Y, PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEADER_LINE_Y)


def usable_font(field: WorksheetField) -> str:
    if "ssn" in field.cell_id.lower():
        return MONO_FONT
    return BODY_FONT


def text_field_dimensions(field: WorksheetField, max_width: float) -> tuple[float, float]:
    if field.format_code == "amount":
        return 120.0, 14.0
    if any(token in field.cell_id.lower() for token in ("address", "name", "explanation", "city", "country")):
        return max_width, 14.0
    return min(260.0, max_width), 14.0


def draw_text_field(pdf: canvas.Canvas, field: WorksheetField, x: float, y: float, width: float, height: float) -> None:
    font_name = usable_font(field)
    font_size = BODY_SIZE if field.format_code != "amount" else 10.0
    pdf.setFont(LABEL_FONT, LABEL_SIZE)
    pdf.setFillColor(colors.black)
    pdf.drawString(x, y + height + 4.0, field.label)
    pdf.acroForm.textfield(
        name=field.cell_id,
        x=x,
        y=y,
        width=width,
        height=height,
        fontName=font_name,
        fontSize=font_size,
        borderStyle="underlined",
        borderWidth=0,
        borderColor=colors.white,
        textColor=colors.black,
        fillColor=colors.white,
        forceBorder=False,
    )
    pdf.setStrokeColor(LINE_COLOR)
    pdf.setLineWidth(0.8)
    pdf.line(x, y + 1.0, x + width, y + 1.0)
    field.font_size = font_size
    field.rect = (x, y, x + width, y + height)


def draw_checkbox_field(pdf: canvas.Canvas, field: WorksheetField, x: float, y: float) -> None:
    size = 10.0
    pdf.setFont(BODY_FONT, BODY_SIZE)
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


def paginate_fields(fields: list[WorksheetField], max_width: float) -> list[list[WorksheetField]]:
    pages: list[list[WorksheetField]] = [[]]
    remaining_height = PAGE_CONTENT_TOP
    for field in fields:
        needed = CHECKBOX_ROW_HEIGHT if field.widget_type == "button" else text_field_dimensions(field, max_width)[1] + TEXT_ROW_GAP
        if pages[-1] and remaining_height - needed < BOTTOM_MARGIN:
            pages.append([])
            remaining_height = PAGE_CONTENT_TOP
        pages[-1].append(field)
        remaining_height -= needed
    return pages


def generate_template_pdf(form_id: str, form_data: dict[str, Any]) -> tuple[str, list[WorksheetField], int]:
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{form_id}_worksheet.pdf"
    output_path = OUTPUT_PDF_DIR / filename
    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    title = str((form_data.get("_meta") or {}).get("name") or form_id)
    subtitle = "Tax Year 2025"
    fields = flatten_worksheet_cells(form_data)
    max_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    pages = paginate_fields(fields, max_width)
    total_pages = len(pages)
    for page_number, page_fields in enumerate(pages, start=1):
        if page_number > 1:
            pdf.showPage()
        draw_page_header(pdf, title, subtitle, page_number, total_pages)
        y_cursor = PAGE_CONTENT_TOP
        for field in page_fields:
            field.page = page_number
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
