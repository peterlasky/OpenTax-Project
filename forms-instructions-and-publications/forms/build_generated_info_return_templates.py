#!/usr/bin/env python3
from __future__ import annotations

import json
import math
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
OUTPUT_PDF_DIR = PROJECT_ROOT / "forms-instructions-and-publications" / "generated-information-returns"
OUTPUT_MAP_DIR = PROJECT_ROOT / "reference-data" / "federal" / "2025" / "pdf_field_maps"
MANIFEST_PATH = OUTPUT_PDF_DIR / "manifest.json"

PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 42.0
RIGHT_MARGIN = 42.0
TOP_MARGIN = 42.0
BOTTOM_MARGIN = 42.0
COLUMN_GAP = 24.0
COLUMN_WIDTH = (PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - COLUMN_GAP) / 2.0
LABEL_FONT = "Helvetica-Bold"
BODY_FONT = "Helvetica"
MONO_FONT = "Courier"
TITLE_COLOR = colors.black
SUBTITLE_COLOR = colors.HexColor("#333333")
SECTION_FILL = colors.HexColor("#E9ECEF")
LINE_COLOR = colors.HexColor("#4A4A4A")
SECTION_BAR_HEIGHT = 14.0
SECTION_CONTENT_GAP = 42.0
CHECKBOX_ROW_HEIGHT = 34.0

COMMON_FIELDS = [
    ("recipient_name", "Recipient name", "text", "Recipient from the federal information worksheet."),
    ("recipient_ssn", "Recipient SSN", "text", "Recipient SSN from the federal information worksheet."),
    ("recipient_address_line", "Recipient address", "text", "Recipient street address from the federal information worksheet."),
    ("recipient_city_state_zip", "Recipient city/state/ZIP", "text", "Recipient city, state, and ZIP from the federal information worksheet."),
]


@dataclass
class TemplateField:
    field_name: str
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


def iter_info_return_blocks(jurisdiction: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    results: list[tuple[str, str, dict[str, Any]]] = []
    for form_id, form_data in jurisdiction.items():
        if not isinstance(form_data, dict):
            continue
        for block_id, block in (form_data.get("blocks") or {}).items():
            if not isinstance(block, dict):
                continue
            source_path = block.get("pdf_source_path")
            if isinstance(source_path, str) and "information-returns/" in source_path:
                results.append((form_id, block_id, block))
    return results


def infer_format_code(cell: dict[str, Any]) -> str:
    format_code = str(cell.get("format", "text"))
    if format_code in {"0", "0.00", "0.00%"}:
        return "amount"
    return "text"


def label_for_field(field_id: str, cell: dict[str, Any]) -> str:
    description = str(cell.get("description") or "").strip()
    if description:
        return description
    return field_id.replace("_", " ").title()


def flatten_block_fields(block: dict[str, Any]) -> list[TemplateField]:
    fields: list[TemplateField] = []
    fields.append(
        TemplateField(
            field_name="entry.recipient",
            label="Entry recipient",
            source="entry.recipient",
            widget_type="text",
            format_code="text",
            explanation="Whose source document entry this is, typically taxpayer or spouse.",
        )
    )
    for field_name, label, format_code, explanation in COMMON_FIELDS:
        fields.append(
            TemplateField(
                field_name=field_name,
                label=label,
                source=field_name,
                widget_type="text",
                format_code=format_code,
                explanation=explanation,
            )
        )

    for item_id, cell in (block.get("item_cells") or {}).items():
        if not isinstance(cell, dict):
            continue
        if cell.get("type") == "repeating":
            subcells = cell.get("item_cells") or {}
            repeat_count = cell.get("max_entries")
            if not isinstance(repeat_count, int) or repeat_count <= 0:
                repeat_count = 4
            repeat_count = min(repeat_count, 4)
            for index in range(repeat_count):
                for sub_id, subcell in subcells.items():
                    if not isinstance(subcell, dict):
                        continue
                    fields.append(
                        TemplateField(
                            field_name=f"entry.{item_id}.{index}.{sub_id}",
                            label=f"{label_for_field(item_id, cell)} {index + 1} {label_for_field(sub_id, subcell)}",
                            source=f"entry.{item_id}.{index}.{sub_id}",
                            widget_type="text" if str(subcell.get("format", "text")) != "boolean" else "button",
                            format_code=infer_format_code(subcell),
                            explanation=str(subcell.get("explanation") or cell.get("explanation") or "").strip(),
                        )
                    )
            continue

        format_code = str(cell.get("format", "text"))
        fields.append(
            TemplateField(
                field_name=f"entry.{item_id}",
                label=label_for_field(item_id, cell),
                source=f"entry.{item_id}",
                widget_type="button" if format_code == "boolean" else "text",
                format_code=infer_format_code(cell),
                explanation=str(cell.get("explanation") or "").strip(),
            )
        )
    return fields


def usable_font(field: TemplateField) -> str:
    if "ssn" in field.field_name.lower() or "ein" in field.field_name.lower():
        return MONO_FONT
    return BODY_FONT


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


def text_field_dimensions(field: TemplateField, column_width: float) -> tuple[float, float]:
    if field.format_code == "amount":
        return min(96.0, column_width), 18.0
    if "address" in field.field_name.lower() or "name" in field.field_name.lower() or "policy" in field.field_name.lower():
        return column_width, 18.0
    return min(156.0, column_width), 18.0


def draw_text_field(pdf: canvas.Canvas, field: TemplateField, x: float, y: float, width: float, height: float) -> None:
    font_name = usable_font(field)
    font_size = 9.0 if field.format_code != "amount" else 10.0
    pdf.setFont(LABEL_FONT, 7.5)
    pdf.setFillColor(colors.black)
    pdf.drawString(x, y + height + 3.5, field.label)
    pdf.acroForm.textfield(
        name=field.field_name,
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


def draw_checkbox_field(pdf: canvas.Canvas, field: TemplateField, x: float, y: float) -> None:
    size = 11.0
    pdf.setFont(BODY_FONT, 8.5)
    pdf.drawString(x + size + 6, y + 1.5, field.label)
    pdf.acroForm.checkbox(
        name=field.field_name,
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


def generate_template_pdf(form_id: str, block_id: str, block: dict[str, Any]) -> tuple[str, list[TemplateField], int]:
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{form_id}__{block_id}_template.pdf"
    output_path = OUTPUT_PDF_DIR / filename
    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    title = str(block.get("description") or block_id)
    subtitle = f"OpenTax generated information-return template for {form_id}.{block_id}"
    fields = flatten_block_fields(block)

    page_number = 1
    draw_page_header(pdf, title, subtitle, page_number)
    y_cursor = PAGE_HEIGHT - TOP_MARGIN - 42.0
    draw_section_bar(pdf, y_cursor, "Return Context")
    y_cursor -= SECTION_CONTENT_GAP

    context_fields = fields[: 1 + len(COMMON_FIELDS)]
    entry_fields = fields[1 + len(COMMON_FIELDS) :]

    def next_page(section_title: str) -> None:
        nonlocal page_number, y_cursor
        pdf.showPage()
        page_number += 1
        draw_page_header(pdf, title, subtitle, page_number)
        y_cursor = PAGE_HEIGHT - TOP_MARGIN - 42.0
        draw_section_bar(pdf, y_cursor, section_title)
        y_cursor -= SECTION_CONTENT_GAP

    for index, field in enumerate(context_fields):
        column = index % 2
        row = index // 2
        x = LEFT_MARGIN + (COLUMN_WIDTH + COLUMN_GAP) * column
        width, height = text_field_dimensions(field, COLUMN_WIDTH - 8.0)
        y = y_cursor - (row * 34.0)
        draw_text_field(pdf, field, x, y, width, height)
    y_cursor -= (math.ceil(len(context_fields) / 2) * 34.0) + 14.0
    draw_section_bar(pdf, y_cursor, "Entry Fields")
    y_cursor -= SECTION_CONTENT_GAP

    for field in entry_fields:
        if field.widget_type == "button":
            needed = CHECKBOX_ROW_HEIGHT
        else:
            _, height = text_field_dimensions(field, COLUMN_WIDTH)
            needed = height + 18.0
        if y_cursor - needed < BOTTOM_MARGIN:
            next_page("Entry Fields")
        if field.widget_type == "button":
            draw_checkbox_field(pdf, field, LEFT_MARGIN, y_cursor)
            y_cursor -= CHECKBOX_ROW_HEIGHT
            continue

        width, height = text_field_dimensions(field, PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN)
        draw_text_field(pdf, field, LEFT_MARGIN, y_cursor, width, height)
        y_cursor -= height + 18.0

    pdf.save()
    field_count = len(PdfReader(str(output_path)).get_fields() or {})
    return str(output_path.relative_to(PROJECT_ROOT)), fields, field_count


def build_field_map(relative_pdf_path: str, fields: list[TemplateField]) -> dict[str, Any]:
    widgets: list[dict[str, Any]] = []
    for field in fields:
        widget = {
            "field": field.field_name,
            "source": field.source,
            "cell_ref": None,
            "render_mode": "checkbox" if field.widget_type == "button" else "field_text",
            "widget_type": "button" if field.widget_type == "button" else "text",
            "format": field.format_code,
            "mapping_method": "generated_info_return_template",
        }
        if field.rect is not None:
            widget["page"] = field.page
            widget["rect"] = [round(value, 3) for value in field.rect]
        if field.font_size is not None:
            widget["font_size"] = field.font_size
        widgets.append(widget)
    return {
        "source_pdf": relative_pdf_path,
        "widgets": widgets,
    }


def main() -> None:
    payload = load_model()
    jurisdiction = payload[JURISDICTION_KEY]
    OUTPUT_MAP_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    for form_id, block_id, block in iter_info_return_blocks(jurisdiction):
        relative_pdf_path, fields, field_count = generate_template_pdf(form_id, block_id, block)
        field_map = build_field_map(relative_pdf_path, fields)
        mapping_id = f"block__{form_id}__{block_id}"
        (OUTPUT_MAP_DIR / f"{mapping_id}.json").write_text(json.dumps(field_map, indent=2) + "\n", encoding="utf-8")
        manifest.append(
            {
                "form_id": form_id,
                "block_id": block_id,
                "pdf_source_path": relative_pdf_path,
                "pdf_field_count": field_count,
                "mapping_id": mapping_id,
            }
        )

    MANIFEST_PATH.write_text(json.dumps({"generated_templates": manifest}, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(manifest)} information-return templates in {OUTPUT_PDF_DIR}")


if __name__ == "__main__":
    main()
