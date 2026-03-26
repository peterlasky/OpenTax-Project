#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "federal_1040_2025.json"
OUTPUT_DIR = PROJECT_ROOT / "reference-data" / "federal" / "2025" / "pdf_field_maps"
LEGACY_MAPPING_DIR = PROJECT_ROOT / "reference-data" / "federal" / "2025" / "pdf_mappings"
JURISDICTION_KEY = "Federal 2025"
SIMPLE_SOURCE_PATTERN = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*$")
FIELD_TYPE_NAMES = {
    "/Btn": "button",
    "/Ch": "choice",
    "/Sig": "signature",
    "/Tx": "text",
}
NUMERIC_FORMATS = {"0", "0.00", "0.00%"}
STANDARD_NAME_SOURCE = (
    'f1040.first_name + " " + f1040.last_name + '
    '((f1040.filing_status_married_jointly > 0.0) * (" & " + f1040.spouse_first_name + " " + f1040.spouse_last_name))'
)
STANDARD_SSN_SOURCE = "f1040.ssn"


def load_model_forms() -> dict[str, dict[str, Any]]:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    jurisdiction = model.get(JURISDICTION_KEY)
    if not isinstance(jurisdiction, dict):
        raise RuntimeError(f"Missing jurisdiction '{JURISDICTION_KEY}' in {MODEL_PATH}")
    return jurisdiction


def iter_fillable_forms(jurisdiction: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    forms: list[tuple[str, dict[str, Any]]] = []
    for form_id, form_data in jurisdiction.items():
        if not isinstance(form_data, dict) or form_id.startswith("_"):
            continue
        meta = form_data.get("_meta")
        if not isinstance(meta, dict):
            continue
        if meta.get("fillable_form") is not True:
            continue
        field_count = meta.get("pdf_field_count")
        if not isinstance(field_count, int) or field_count <= 1:
            continue
        source_pdf = meta.get("pdf_source_path")
        if not isinstance(source_pdf, str) or not source_pdf.strip():
            continue
        forms.append((form_id, form_data))
    return forms


def full_widget_name(annot: Any) -> str:
    parts: list[str] = []
    current = annot
    while current is not None:
        name = current.get("/T")
        if name:
            parts.append(str(name))
        parent = current.get("/Parent")
        current = parent.get_object() if parent is not None else None
    return ".".join(reversed(parts))


def widget_type_name(annot: Any) -> str:
    field_type = annot.get("/FT")
    if field_type is None:
        parent = annot.get("/Parent")
        if parent is not None:
            field_type = parent.get_object().get("/FT")
    return FIELD_TYPE_NAMES.get(str(field_type), "unknown")


def simple_cell_ref(source: Any) -> str | None:
    if not isinstance(source, str):
        return None
    text = source.strip()
    if not text or not SIMPLE_SOURCE_PATTERN.fullmatch(text):
        return None
    return text


def load_legacy_mapping(form_id: str) -> dict[str, Any]:
    path = LEGACY_MAPPING_DIR / f"{form_id}.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def legacy_widget_mapping(legacy_mapping: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    by_field: dict[str, tuple[str, dict[str, Any]]] = {}
    for item in legacy_mapping.get("field_mappings", []):
        if isinstance(item, dict) and isinstance(item.get("field"), str):
            by_field[item["field"]] = ("field_text", item)
    for item in legacy_mapping.get("overlay_mappings", []):
        if not isinstance(item, dict) or not isinstance(item.get("field"), str):
            continue
        render_mode = "checkbox" if item.get("kind", "checkbox") == "checkbox" else "text"
        by_field[item["field"]] = (render_mode, item)
    return by_field


def apply_legacy_mapping(widget: dict[str, Any], render_mode: str, legacy_item: dict[str, Any]) -> None:
    widget["source"] = legacy_item.get("source")
    widget["cell_ref"] = simple_cell_ref(legacy_item.get("source"))
    widget["render_mode"] = render_mode
    widget["mapping_method"] = "legacy_manual"
    for key in ("format", "slice_start", "slice_length", "font_size", "kind", "text"):
        if key in legacy_item:
            widget[key] = legacy_item[key]


def apply_widget_mapping(
    widget: dict[str, Any],
    *,
    source: str,
    render_mode: str,
    method: str,
    format_code: str | None = None,
    kind: str | None = None,
) -> None:
    if isinstance(widget.get("source"), str) and str(widget["source"]).strip():
        return
    widget["source"] = source
    widget["cell_ref"] = simple_cell_ref(source)
    widget["render_mode"] = render_mode
    widget["mapping_method"] = method
    if format_code:
        widget["format"] = format_code
    if kind:
        widget["kind"] = kind


def cell_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[float, str]:
    cell_id, cell = item
    order = cell.get("order", 10**9)
    if not isinstance(order, (int, float)):
        order = 10**9
    return float(order), cell_id


def ordered_form_cells(form_data: dict[str, Any], *, format_filter: set[str] | None = None) -> list[tuple[str, dict[str, Any]]]:
    cells = form_data.get("cells") or {}
    ordered = [
        (cell_id, cell)
        for cell_id, cell in cells.items()
        if isinstance(cell, dict) and (format_filter is None or cell.get("format") in format_filter)
    ]
    return sorted(ordered, key=cell_sort_key)


def line_tokens_for_field(field_name: str) -> list[str]:
    return [token.lower() for token in re.findall(r"Line(\d+[A-Za-z]?)", field_name)]


def render_format_for_cell(cell: dict[str, Any]) -> str:
    format_code = str(cell.get("format", "text"))
    if format_code in NUMERIC_FORMATS:
        return "amount"
    return "text"


def standard_header_widget_candidates(widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        widget
        for widget in widgets
        if widget.get("widget_type") == "text"
        and not widget.get("source")
        and widget.get("page") == 1
        and "Line" not in str(widget.get("field"))
    ][:2]


def map_standard_header(widgets: list[dict[str, Any]]) -> None:
    header_widgets = standard_header_widget_candidates(widgets)
    if len(header_widgets) < 2:
        return
    apply_widget_mapping(
        header_widgets[0],
        source=STANDARD_NAME_SOURCE,
        render_mode="field_text",
        method="heuristic_standard_header",
        format_code="text",
    )
    apply_widget_mapping(
        header_widgets[1],
        source=STANDARD_SSN_SOURCE,
        render_mode="field_text",
        method="heuristic_standard_header",
        format_code="ssn_digits",
    )


def infer_generic_text_mappings(form_data: dict[str, Any], widgets: list[dict[str, Any]]) -> None:
    mapped_cell_refs = {
        widget.get("cell_ref")
        for widget in widgets
        if isinstance(widget.get("cell_ref"), str) and widget.get("cell_ref")
    }
    ordered_non_boolean_cells = [
        (cell_id, cell)
        for cell_id, cell in ordered_form_cells(form_data)
        if cell.get("format") != "boolean" and cell_id not in mapped_cell_refs
    ]
    remaining_by_id = {cell_id: cell for cell_id, cell in ordered_non_boolean_cells}
    unmapped_text_widgets = [
        widget
        for widget in widgets
        if widget.get("widget_type") == "text" and not widget.get("source")
    ]

    for widget in unmapped_text_widgets:
        for token in line_tokens_for_field(str(widget.get("field", ""))):
            cell = remaining_by_id.pop(token, None)
            if cell is None:
                continue
            apply_widget_mapping(
                widget,
                source=token,
                render_mode="field_text",
                method="heuristic_line_token",
                format_code=render_format_for_cell(cell),
            )
            break

    ordered_remaining_cells = [(cell_id, remaining_by_id[cell_id]) for cell_id, _ in ordered_non_boolean_cells if cell_id in remaining_by_id]
    remaining_widgets = [
        widget
        for widget in widgets
        if widget.get("widget_type") == "text" and not widget.get("source")
    ]
    for (cell_id, cell), widget in zip(ordered_remaining_cells, remaining_widgets):
        apply_widget_mapping(
            widget,
            source=cell_id,
            render_mode="field_text",
            method="heuristic_cell_order",
            format_code=render_format_for_cell(cell),
        )


def button_group_key(field_name: str) -> str:
    return re.sub(r"\[\d+\]$", "", field_name)


def infer_boolean_mappings(form_data: dict[str, Any], widgets: list[dict[str, Any]]) -> None:
    mapped_cell_refs = {
        widget.get("cell_ref")
        for widget in widgets
        if isinstance(widget.get("cell_ref"), str) and widget.get("cell_ref")
    }
    ordered_boolean_cells = [
        (cell_id, cell)
        for cell_id, cell in ordered_form_cells(form_data, format_filter={"boolean"})
        if cell_id not in mapped_cell_refs
    ]
    remaining_by_id = {cell_id: cell for cell_id, cell in ordered_boolean_cells}
    groups: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = []
    current_key = ""
    for widget in widgets:
        if widget.get("widget_type") != "button" or widget.get("source"):
            continue
        group_key = button_group_key(str(widget.get("field", "")))
        if group_key != current_key:
            if current_group:
                groups.append(current_group)
            current_group = [widget]
            current_key = group_key
        else:
            current_group.append(widget)
    if current_group:
        groups.append(current_group)

    def map_boolean_group(group: list[dict[str, Any]], cell_id: str, method: str) -> None:
        if not group:
            return
        apply_widget_mapping(
            group[0],
            source=cell_id,
            render_mode="checkbox",
            method=method,
            kind="checkbox",
        )
        if len(group) >= 2:
            apply_widget_mapping(
                group[1],
                source=f"not {cell_id}",
                render_mode="checkbox",
                method=method,
                kind="checkbox",
            )

    for group in groups:
        field_name = str(group[0].get("field", ""))
        matched_cell_id = None
        for token in line_tokens_for_field(field_name):
            if token in remaining_by_id:
                matched_cell_id = token
                break
        if matched_cell_id is None:
            continue
        remaining_by_id.pop(matched_cell_id, None)
        map_boolean_group(group, matched_cell_id, "heuristic_boolean_line_token")

    remaining_boolean_cells = [cell_id for cell_id, _ in ordered_boolean_cells if cell_id in remaining_by_id]
    remaining_groups = [group for group in groups if not group[0].get("source")]
    for cell_id, group in zip(remaining_boolean_cells, remaining_groups):
        map_boolean_group(group, cell_id, "heuristic_boolean_order")


def text_heuristics_safe_to_apply(form_data: dict[str, Any], widgets: list[dict[str, Any]]) -> bool:
    text_widget_count = sum(1 for widget in widgets if widget.get("widget_type") == "text")
    non_boolean_cell_count = len(
        [1 for _, cell in ordered_form_cells(form_data) if cell.get("format") != "boolean"]
    )
    return text_widget_count <= non_boolean_cell_count + 8


def boolean_heuristics_safe_to_apply(form_data: dict[str, Any], widgets: list[dict[str, Any]]) -> bool:
    button_widget_count = sum(1 for widget in widgets if widget.get("widget_type") == "button")
    boolean_cell_count = len(ordered_form_cells(form_data, format_filter={"boolean"}))
    return boolean_cell_count > 0 and button_widget_count <= (boolean_cell_count * 2) + 6


def build_widgets(pdf_path: Path, legacy_mapping: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    reader = PdfReader(str(pdf_path))
    by_field = legacy_widget_mapping(legacy_mapping)
    widgets: list[dict[str, Any]] = []
    seen_fields: set[str] = set()

    for page_index, page in enumerate(reader.pages):
        annots = page.get("/Annots") or []
        for annot_ref in annots:
            annot = annot_ref.get_object()
            if annot.get("/Subtype") != "/Widget":
                continue
            field_name = full_widget_name(annot)
            rect = annot.get("/Rect")
            if not field_name or rect is None or len(rect) != 4 or field_name in seen_fields:
                continue
            seen_fields.add(field_name)

            widget = {
                "field": field_name,
                "page": page_index + 1,
                "rect": [float(value) for value in rect],
                "widget_type": widget_type_name(annot),
                "source": None,
                "cell_ref": None,
                "render_mode": None,
            }
            legacy_item = by_field.pop(field_name, None)
            if legacy_item is not None:
                render_mode, item = legacy_item
                apply_legacy_mapping(widget, render_mode, item)
            widgets.append(widget)

    unresolved_legacy_fields = sorted(by_field.keys())
    return widgets, unresolved_legacy_fields


def build_field_map(form_id: str, form_data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    meta = form_data["_meta"]
    source_pdf = PROJECT_ROOT / str(meta["pdf_source_path"])
    legacy_mapping = load_legacy_mapping(form_id)
    widgets, unresolved_legacy_fields = build_widgets(source_pdf, legacy_mapping)
    if not legacy_mapping:
        if text_heuristics_safe_to_apply(form_data, widgets):
            map_standard_header(widgets)
            infer_generic_text_mappings(form_data, widgets)
        if boolean_heuristics_safe_to_apply(form_data, widgets):
            infer_boolean_mappings(form_data, widgets)
    mapped_widget_count = sum(1 for item in widgets if isinstance(item.get("source"), str) and item["source"].strip())
    renderable_widget_count = sum(
        1
        for item in widgets
        if isinstance(item.get("source"), str)
        and item["source"].strip()
        and isinstance(item.get("render_mode"), str)
        and item["render_mode"]
    )
    return (
        {
            "form_id": form_id,
            "source_pdf": meta["pdf_source_path"],
            "pdf_field_count": meta["pdf_field_count"],
            "fillable_form": True,
            "widget_count": len(widgets),
            "mapped_widget_count": mapped_widget_count,
            "renderable_widget_count": renderable_widget_count,
            "widgets": widgets,
        },
        unresolved_legacy_fields,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    forms = iter_fillable_forms(load_model_forms())
    manifest: list[dict[str, Any]] = []
    unresolved: dict[str, list[str]] = {}

    for form_id, form_data in sorted(forms):
        field_map, unresolved_fields = build_field_map(form_id, form_data)
        output_path = OUTPUT_DIR / f"{form_id}.json"
        output_path.write_text(json.dumps(field_map, indent=2) + "\n", encoding="utf-8")
        manifest.append(
            {
                "form_id": form_id,
                "source_pdf": field_map["source_pdf"],
                "pdf_field_count": field_map["pdf_field_count"],
                "widget_count": field_map["widget_count"],
                "mapped_widget_count": field_map["mapped_widget_count"],
                "renderable_widget_count": field_map["renderable_widget_count"],
            }
        )
        if unresolved_fields:
            unresolved[form_id] = unresolved_fields

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "jurisdiction": JURISDICTION_KEY,
                "generated_form_count": len(manifest),
                "forms": manifest,
                "unresolved_legacy_fields": unresolved,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Generated {len(manifest)} PDF field maps in {OUTPUT_DIR}")
    if unresolved:
        print("Legacy fields not found in extracted widgets:")
        for form_id, fields in sorted(unresolved.items()):
            print(f"- {form_id}: {len(fields)}")


if __name__ == "__main__":
    main()
