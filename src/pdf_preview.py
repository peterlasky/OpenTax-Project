#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import datetime as dt
import math
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

try:
    from pypdf import PdfReader, PdfWriter
except Exception:  # pragma: no cover - dependency availability differs by runtime
    PdfReader = None
    PdfWriter = None

try:
    from reportlab.pdfgen import canvas
except Exception:  # pragma: no cover - dependency availability differs by runtime
    canvas = None


PAGE_PATTERN = re.compile(r"\.Page(\d+)\[")


class FormPdfPreviewEngine:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.field_map_dir = self.project_root / "reference-data" / "federal" / "2025" / "pdf_field_maps"
        self.mapping_dir = self.project_root / "reference-data" / "federal" / "2025" / "pdf_mappings"
        self.preview_dir = Path(tempfile.gettempdir()) / "opentax-pdf-preview"
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        self._mapping_cache: dict[str, dict[str, Any]] = {}
        self._mapping_mtime_ns: dict[str, int] = {}
        self._mapping_path_text: dict[str, str] = {}
        self._render_serial = 0

    def available(self) -> bool:
        return PdfReader is not None and PdfWriter is not None and canvas is not None

    def render_preview(
        self,
        *,
        form_id: str,
        resolve_source: Callable[[str], Any],
        highlight_sources: set[str] | None = None,
    ) -> Path:
        if not self.available():
            raise RuntimeError("PDF preview dependencies are not available.")

        mapping = self._load_mapping(form_id)
        source_pdf = self.project_root / mapping["source_pdf"]
        if not source_pdf.is_file():
            raise FileNotFoundError(f"Source PDF not found: {source_pdf}")

        reader = PdfReader(str(source_pdf))
        writer = PdfWriter()
        writer.append(reader)

        widget_lookup = self._build_widget_lookup(reader)

        field_mappings, overlay_mappings = self._render_mappings_from_mapping(mapping)

        overlay_items_by_page = self._collect_field_text_overlays(
            field_mappings,
            widget_lookup,
            resolve_source,
        )
        extra_overlay_items_by_page = self._collect_overlay_items(
            overlay_mappings,
            widget_lookup,
            resolve_source,
        )
        for page_index, overlay_items in extra_overlay_items_by_page.items():
            overlay_items_by_page.setdefault(page_index, []).extend(overlay_items)
        highlight_overlay_items_by_page = self._collect_highlight_overlay_items(
            field_mappings + overlay_mappings,
            widget_lookup,
            highlight_sources or set(),
        )
        for page_index, overlay_items in highlight_overlay_items_by_page.items():
            overlay_items_by_page[page_index] = overlay_items + overlay_items_by_page.get(page_index, [])

        for page_index, overlay_items in overlay_items_by_page.items():
            if not overlay_items:
                continue
            overlay_pdf = self._build_overlay_pdf(
                width=float(writer.pages[page_index].mediabox.width),
                height=float(writer.pages[page_index].mediabox.height),
                overlay_items=overlay_items,
            )
            writer.pages[page_index].merge_page(overlay_pdf.pages[0])

        try:
            writer.remove_annotations(subtypes="/Widget")
        except Exception:
            pass

        self._render_serial += 1
        output_path = self.preview_dir / f"{form_id}_preview_{self._render_serial}.pdf"
        with output_path.open("wb") as handle:
            writer.write(handle)
        return output_path

    def field_map_path_for_form(self, form_id: str) -> Path:
        return self.field_map_dir / f"{form_id}.json"

    def mapping_path_for_form(self, form_id: str) -> Path:
        field_map_path = self.field_map_path_for_form(form_id)
        if field_map_path.is_file():
            return field_map_path
        return self.mapping_dir / f"{form_id}.json"

    def has_mapping_for_form(self, form_id: str) -> bool:
        return self.field_map_path_for_form(form_id).is_file() or self.mapping_path_for_form(form_id).is_file()

    def has_render_mappings_for_form(self, form_id: str) -> bool:
        if not self.has_mapping_for_form(form_id):
            return False
        try:
            mapping = self._load_mapping(form_id)
        except Exception:
            return False
        field_mappings, overlay_mappings = self._render_mappings_from_mapping(mapping)
        return bool(field_mappings or overlay_mappings)

    def source_pdf_for_form(self, form_id: str) -> Path | None:
        if not self.has_mapping_for_form(form_id):
            return None
        try:
            mapping = self._load_mapping(form_id)
        except Exception:
            return None
        return self.project_root / str(mapping.get("source_pdf", ""))

    def _load_mapping(self, form_id: str) -> dict[str, Any]:
        mapping_path = self.mapping_path_for_form(form_id)
        mapping_path_text = str(mapping_path)
        current_mtime_ns = mapping_path.stat().st_mtime_ns
        cached = self._mapping_cache.get(form_id)
        if (
            cached is None
            or self._mapping_mtime_ns.get(form_id) != current_mtime_ns
            or self._mapping_path_text.get(form_id) != mapping_path_text
        ):
            cached = json.loads(mapping_path.read_text(encoding="utf-8"))
            self._mapping_cache[form_id] = cached
            self._mapping_mtime_ns[form_id] = current_mtime_ns
            self._mapping_path_text[form_id] = mapping_path_text
        return cached

    def _render_mappings_from_mapping(
        self,
        mapping: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        widgets = mapping.get("widgets")
        if isinstance(widgets, list):
            field_mappings: list[dict[str, Any]] = []
            overlay_mappings: list[dict[str, Any]] = []
            for raw_item in widgets:
                if not isinstance(raw_item, dict):
                    continue
                source = raw_item.get("source")
                render_mode = raw_item.get("render_mode")
                if not isinstance(source, str) or not source.strip() or not isinstance(render_mode, str):
                    continue
                item = dict(raw_item)
                if render_mode in {"field_text", "text"}:
                    field_mappings.append(item)
                elif render_mode == "checkbox":
                    item.setdefault("kind", "checkbox")
                    overlay_mappings.append(item)
            return field_mappings, overlay_mappings
        return list(mapping.get("field_mappings", [])), list(mapping.get("overlay_mappings", []))

    def _collect_field_updates(
        self,
        mappings: list[dict[str, Any]],
        resolve_source: Callable[[str], Any],
    ) -> dict[int, dict[str, str]]:
        updates_by_page: dict[int, dict[str, str]] = {}
        for item in mappings:
            try:
                value = resolve_source(item["source"])
            except Exception:
                continue
            formatted = self._format_value(item, value)
            page_index = self._page_index_for_field(item["field"])
            updates_by_page.setdefault(page_index, {})[item["field"]] = formatted
        return updates_by_page

    def _collect_overlay_items(
        self,
        mappings: list[dict[str, Any]],
        widget_lookup: dict[str, tuple[int, tuple[float, float, float, float]]],
        resolve_source: Callable[[str], Any],
    ) -> dict[int, list[dict[str, Any]]]:
        overlay_items_by_page: dict[int, list[dict[str, Any]]] = {}
        for item in mappings:
            try:
                value = resolve_source(item["source"])
            except Exception:
                continue
            if not self._is_truthy(value):
                continue
            location = self._resolve_overlay_location(item, widget_lookup)
            if location is None:
                continue
            page_index, rect = location
            overlay_item = {"kind": item.get("kind", "checkbox"), "rect": rect}
            if "text" in item:
                overlay_item["text"] = item["text"]
            overlay_items_by_page.setdefault(page_index, []).append(overlay_item)
        return overlay_items_by_page

    def _collect_field_text_overlays(
        self,
        mappings: list[dict[str, Any]],
        widget_lookup: dict[str, tuple[int, tuple[float, float, float, float]]],
        resolve_source: Callable[[str], Any],
    ) -> dict[int, list[dict[str, Any]]]:
        overlays_by_page: dict[int, list[dict[str, Any]]] = {}
        for item in mappings:
            try:
                value = resolve_source(item["source"])
            except Exception:
                continue
            formatted = self._format_value(item, value)
            if formatted == "":
                continue
            location = self._resolve_overlay_location(item, widget_lookup)
            if location is None:
                continue
            page_index, rect = location
            overlays_by_page.setdefault(page_index, []).append(
                {
                    "kind": "field_text",
                    "rect": rect,
                    "text": formatted,
                    "align": "right" if item.get("format") == "amount" else "left",
                    "font_size": item.get("font_size"),
                }
            )
        return overlays_by_page

    def _collect_highlight_overlay_items(
        self,
        mappings: list[dict[str, Any]],
        widget_lookup: dict[str, tuple[int, tuple[float, float, float, float]]],
        highlight_sources: set[str],
    ) -> dict[int, list[dict[str, Any]]]:
        if not highlight_sources:
            return {}
        overlays_by_page: dict[int, list[dict[str, Any]]] = {}
        seen_locations: set[tuple[int, tuple[float, float, float, float]]] = set()
        for item in mappings:
            source = item.get("source")
            if source not in highlight_sources:
                continue
            location = self._resolve_overlay_location(item, widget_lookup)
            if location is None or location in seen_locations:
                continue
            seen_locations.add(location)
            page_index, rect = location
            overlays_by_page.setdefault(page_index, []).append({"kind": "highlight", "rect": rect})
        return overlays_by_page

    def _resolve_overlay_location(
        self,
        item: dict[str, Any],
        widget_lookup: dict[str, tuple[int, tuple[float, float, float, float]]],
    ) -> tuple[int, tuple[float, float, float, float]] | None:
        field_name = item.get("field")
        if field_name and field_name in widget_lookup:
            return widget_lookup[field_name]
        page = item.get("page")
        rect = item.get("rect")
        if page is None or rect is None or len(rect) != 4:
            return None
        return int(page) - 1, tuple(float(part) for part in rect)

    def _build_widget_lookup(
        self,
        reader: Any,
    ) -> dict[str, tuple[int, tuple[float, float, float, float]]]:
        lookup: dict[str, tuple[int, tuple[float, float, float, float]]] = {}
        for page_index, page in enumerate(reader.pages):
            annots = page.get("/Annots") or []
            for annot_ref in annots:
                annot = annot_ref.get_object()
                if annot.get("/Subtype") != "/Widget":
                    continue
                full_name = self._full_widget_name(annot)
                rect = annot.get("/Rect")
                if not full_name or rect is None or len(rect) != 4:
                    continue
                lookup[full_name] = (
                    page_index,
                    tuple(float(value) for value in rect),
                )
        return lookup

    def _full_widget_name(self, annot: Any) -> str:
        parts: list[str] = []
        current = annot
        while current is not None:
            name = current.get("/T")
            if name:
                parts.append(str(name))
            parent = current.get("/Parent")
            current = parent.get_object() if parent is not None else None
        return ".".join(reversed(parts))

    def _page_index_for_field(self, field_name: str) -> int:
        match = PAGE_PATTERN.search(field_name)
        if match:
            return max(0, int(match.group(1)) - 1)
        return 0

    def _build_overlay_pdf(
        self,
        *,
        width: float,
        height: float,
        overlay_items: list[dict[str, Any]],
    ) -> Any:
        buffer = io.BytesIO()
        pdf_canvas = canvas.Canvas(buffer, pagesize=(width, height))
        for item in overlay_items:
            kind = item.get("kind")
            rect = item["rect"]
            if kind == "highlight":
                self._draw_highlight(pdf_canvas, rect)
            elif kind == "checkbox":
                self._draw_x_mark(pdf_canvas, rect)
            elif kind in {"text", "field_text"}:
                self._draw_text(
                    pdf_canvas,
                    rect,
                    str(item.get("text", "")),
                    align=str(item.get("align", "left")),
                    font_size=item.get("font_size"),
                )
        pdf_canvas.save()
        buffer.seek(0)
        return PdfReader(buffer)

    def _draw_highlight(self, pdf_canvas: Any, rect: tuple[float, float, float, float]) -> None:
        x0, y0, x1, y1 = rect
        width = max(0.0, x1 - x0)
        height = max(0.0, y1 - y0)
        if width <= 0.0 or height <= 0.0:
            return
        pdf_canvas.saveState()
        try:
            if hasattr(pdf_canvas, "setFillAlpha"):
                pdf_canvas.setFillAlpha(0.45)
            if hasattr(pdf_canvas, "setStrokeAlpha"):
                pdf_canvas.setStrokeAlpha(0.8)
        except Exception:
            pass
        pdf_canvas.setFillColorRGB(0.992, 0.906, 0.314)
        pdf_canvas.setStrokeColorRGB(0.925, 0.702, 0.0)
        pdf_canvas.setLineWidth(0.8)
        pdf_canvas.rect(x0, y0, width, height, stroke=1, fill=1)
        pdf_canvas.restoreState()

    def _draw_x_mark(self, pdf_canvas: Any, rect: tuple[float, float, float, float]) -> None:
        x0, y0, x1, y1 = rect
        inset = min((x1 - x0), (y1 - y0)) * 0.18
        pdf_canvas.setLineWidth(1.2)
        pdf_canvas.line(x0 + inset, y0 + inset, x1 - inset, y1 - inset)
        pdf_canvas.line(x0 + inset, y1 - inset, x1 - inset, y0 + inset)

    def _draw_text(
        self,
        pdf_canvas: Any,
        rect: tuple[float, float, float, float],
        text: str,
        *,
        align: str = "left",
        font_size: Any = None,
    ) -> None:
        if not text:
            return
        x0, y0, x1, y1 = rect
        size = float(font_size) if isinstance(font_size, (int, float)) else 9.0
        pdf_canvas.setFont("Helvetica", size)
        baseline = y0 + ((y1 - y0) / 2.0) - (size * 0.33)
        if align == "right":
            pdf_canvas.drawRightString(x1 - 1.5, baseline, text)
            return
        pdf_canvas.drawString(x0 + 1.5, baseline, text)

    def _format_value(self, item: dict[str, Any], value: Any) -> str:
        format_code = str(item.get("format", "text"))
        if value in (None, ""):
            return ""
        if format_code == "amount":
            text = self._format_amount(value)
        elif format_code == "ssn_digits":
            text = "".join(ch for ch in str(value) if ch.isdigit())[:9]
        elif format_code.startswith("date_"):
            text = self._format_date_part(value, format_code)
        elif isinstance(value, bool):
            text = "Yes" if value else "No"
        else:
            text = str(value)

        slice_start = item.get("slice_start")
        if isinstance(slice_start, int):
            slice_length = item.get("slice_length")
            if isinstance(slice_length, int):
                return text[slice_start : slice_start + slice_length]
            return text[slice_start:]
        return text

    def _format_amount(self, value: Any) -> str:
        if value in (None, ""):
            return ""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if not math.isfinite(number):
            return ""
        return f"{round(number):,}"

    def _format_date_part(self, value: Any, format_code: str) -> str:
        parsed = self._parse_date(value)
        if parsed is None:
            return ""
        if format_code == "date_mm":
            return f"{parsed.month:02d}"
        if format_code == "date_dd":
            return f"{parsed.day:02d}"
        if format_code == "date_yyyy":
            return f"{parsed.year:04d}"
        if format_code == "date_yy":
            return f"{parsed.year % 100:02d}"
        if format_code == "date_mmdd":
            return f"{parsed.month:02d}/{parsed.day:02d}"
        return parsed.isoformat()

    def _parse_date(self, value: Any) -> dt.date | None:
        if isinstance(value, dt.date):
            return value
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        for parser in (self._parse_iso_date, self._parse_slash_date):
            parsed = parser(text)
            if parsed is not None:
                return parsed
        return None

    def _parse_iso_date(self, text: str) -> dt.date | None:
        try:
            return dt.date.fromisoformat(text)
        except ValueError:
            return None

    def _parse_slash_date(self, text: str) -> dt.date | None:
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if not match:
            return None
        try:
            return dt.date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except ValueError:
            return None

    def _is_truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)


# Backward-compatible alias while the rest of the app migrates.
F1040PdfPreviewEngine = FormPdfPreviewEngine
