#!/usr/bin/env python3
"""
Minimal Qt editor for the tax JSON model.

Features:
- Left-hand sheet list for currently visible forms/worksheets
- Spreadsheet-like table for the selected form's cells
- Add/remove visible sheets without deleting them from the JSON
- Load JSON and Save As JSON

Initial visible sheets:
- f1040_Federal_Info_Worksheet
- f1040
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
except Exception:  # pragma: no cover - runtime dependency availability varies
    QPdfDocument = None
    QPdfView = None

try:
    from .pdf_preview import FormPdfPreviewEngine
except Exception:
    try:
        from pdf_preview import FormPdfPreviewEngine
    except Exception:  # pragma: no cover - runtime dependency availability varies
        FormPdfPreviewEngine = None


RESERVED_KEYS = frozenset({"_schema", "_format_codes", "_comments", "_user_entered_sources"})
PREFERRED_INITIAL_SHEETS = ["f1040_Federal_Info_Worksheet", "f1040"]
TABLE_HEADERS = ["Cell ID", "Description", "Value", "Format", "Equation", "Override\nAllowed", "Required Rule"]
CELL_ID_COLUMN_INDEX = 0
DESCRIPTION_COLUMN_INDEX = 1
VALUE_COLUMN_INDEX = 2
FORMAT_COLUMN_INDEX = 3
EQUATION_COLUMN_INDEX = 4
DEFAULT_VALUE_COLUMN_WIDTH = 360
OVERRIDE_ALLOWED_COLUMN_INDEX = 5
REQUIRED_RULE_COLUMN_INDEX = 6
DEFAULT_CELL_ID_COLUMN_WIDTH = 120
DEFAULT_DESCRIPTION_COLUMN_WIDTH = 520
DEFAULT_FORMAT_COLUMN_WIDTH = 90
DEFAULT_EQUATION_COLUMN_WIDTH = 260
DEFAULT_OVERRIDE_ALLOWED_COLUMN_WIDTH = 80
DEFAULT_REQUIRED_RULE_COLUMN_WIDTH = 200
FAINT_METADATA_COLUMN_INDICES = {3, 4, 5, 6}
READONLY_BACKGROUND = QColor("#f3f4f6")
OVERRIDE_TEXT = QColor("#b45309")
DIMMED_ROW_BACKGROUND = QColor("#f6f7f9")
DIMMED_ROW_TEXT = QColor("#9ca3af")
REQUIRED_BACKGROUND = QColor("#fff8d6")
FILED_FORM_BACKGROUND = QColor("#dcfce7")
FAINT_METADATA_TEXT = QColor("#6b7280")
INVALID_TEXT = QColor("#ff0000")
RETURN_TEMPLATE_FILENAME = "federal_1040_2025.json"
RETURNS_DIRNAME = "returns"
FLAT_RETURN_FORMAT = "opentax-flat-return-v1"
FLAT_RETURN_FORMAT_KEY = "_return_data_format"
FLAT_RETURN_TEMPLATE_KEY = "_template"
FLAT_RETURN_JURISDICTION_KEY = "_jurisdiction"
FLAT_RETURN_OVERRIDES_KEY = "_overrides"
FLAT_RETURN_ENTRY_MARKER = "__entry__"
BLOCK_PREVIEW_MAPPING_PREFIX = "block__"
FORM_SHEET_PREFIX = "form:"
BLOCK_SHEET_PREFIX = "block:"
REFERENCE_DATA_FILES = (
    "ordinary_income_tax",
    "earned_income_credit",
    "simplified_method_tables",
    "capital_gain_parameters",
)
ONE_HOT_PREFIXES = ("filing_status_", "category_")
PERSON_NAME_ID_PARTS = (
    "first_name",
    "last_name",
    "middle_initial",
    "suffix",
    "full_name",
    "child_name",
)
PERSON_NAME_LABEL_PARTS = (
    "first name",
    "last name",
    "middle initial",
    "full name",
    "child name",
)
FORM_REF_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z0-9_]+)\b")


def _jurisdictions(data: dict[str, Any]) -> list[str]:
    return [key for key, value in data.items() if key not in RESERVED_KEYS and isinstance(value, dict)]


def _form_sort_key(item: tuple[str, Any]) -> tuple[float, str]:
    form_id, form_data = item
    rank = float("inf")
    if isinstance(form_data, dict):
        meta = form_data.get("_meta") or {}
        try:
            rank = float(meta.get("rank"))
        except (TypeError, ValueError):
            pass
    return (rank, form_id)


def _cell_sort_key(item: tuple[str, Any]) -> tuple[int | float, str]:
    cell_id, cell = item
    if isinstance(cell, dict):
        try:
            return (int(cell.get("order")), str(cell_id))
        except (TypeError, ValueError):
            pass
    return (float("inf"), str(cell_id))


def _form_label(form_id: str, form_data: dict[str, Any]) -> str:
    meta = form_data.get("_meta") or {}
    title = meta.get("name") or form_id
    return f"{title} ({form_id})"


def _display_cell_value(cell: dict[str, Any]) -> str:
    value = cell.get("value")
    format_code = str(cell.get("format", "text"))
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if format_code == "0":
        try:
            number = int(value)
        except (TypeError, ValueError):
            return str(value)
        return f"{number:,}"
    if format_code in {"0.00", "0.00%"}:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        rounded = round(number)
        if abs(number - rounded) < 1e-9:
            return f"{int(rounded):,}"
        return f"{number:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _parse_value(raw_text: str, format_code: str, default_value: Any) -> Any:
    text = raw_text.strip()
    if format_code == "boolean":
        if text == "":
            return False
        lowered = text.lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
        raise ValueError("Use true/false for boolean fields.")
    if format_code == "0":
        if text == "":
            return default_value if default_value is not None else 0
        return int(text.replace(",", ""))
    if format_code == "0.00" or format_code == "0.00%":
        if text == "":
            return default_value if default_value is not None else 0
        return float(text.replace(",", ""))
    if format_code in {"date", "text"}:
        return text
    return text


def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


class TaxSheetEditor(QMainWindow):
    def __init__(self, json_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("OpenTax Qt Editor")
        self.resize(1280, 800)

        self.current_path: Path | None = None
        self.data: dict[str, Any] = {}
        self.jurisdiction_key: str | None = None
        self.visible_sheet_ids: list[str] = []
        self.overridden_cells: set[tuple[str, str]] = set()
        self.touched_input_cells: set[tuple[str, str]] = set()
        self.reference_data: dict[str, dict[str, Any]] = {}
        self._evaluation_cache: dict[tuple[str, str, bool], Any] = {}
        self._populating_table = False
        self.suggested_return_filename = self._default_return_filename()
        self.pdf_preview_engine = (
            FormPdfPreviewEngine(self._project_root())
            if FormPdfPreviewEngine is not None
            else None
        )
        self.pdf_document = None
        self.pdf_view = None
        self.pdf_stack = QStackedWidget()
        self.pdf_placeholder_label = QLabel()
        self.pdf_placeholder_label.setWordWrap(True)
        self.pdf_placeholder_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.pdf_status_label = QLabel()
        self.pdf_status_label.setWordWrap(True)

        self.sheet_list = QListWidget()
        self.sheet_list.currentItemChanged.connect(self._on_sheet_changed)

        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.horizontalHeader().setMinimumHeight(44)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(CELL_ID_COLUMN_INDEX, DEFAULT_CELL_ID_COLUMN_WIDTH)
        self.table.setColumnWidth(DESCRIPTION_COLUMN_INDEX, DEFAULT_DESCRIPTION_COLUMN_WIDTH)
        self.table.setColumnWidth(VALUE_COLUMN_INDEX, DEFAULT_VALUE_COLUMN_WIDTH)
        self.table.setColumnWidth(FORMAT_COLUMN_INDEX, DEFAULT_FORMAT_COLUMN_WIDTH)
        self.table.setColumnWidth(EQUATION_COLUMN_INDEX, DEFAULT_EQUATION_COLUMN_WIDTH)
        self.table.setColumnWidth(OVERRIDE_ALLOWED_COLUMN_INDEX, DEFAULT_OVERRIDE_ALLOWED_COLUMN_WIDTH)
        self.table.setColumnWidth(REQUIRED_RULE_COLUMN_INDEX, DEFAULT_REQUIRED_RULE_COLUMN_WIDTH)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)
        self.table.itemChanged.connect(self._on_item_changed)

        self.path_label = QLabel("No return loaded. Choose New Return or Import Return.")
        self.path_label.setWordWrap(True)

        new_return_button = QPushButton("New Return")
        new_return_button.clicked.connect(self.new_return)

        load_button = QPushButton("Import Return")
        load_button.clicked.connect(self.load_json_dialog)

        save_as_button = QPushButton("Save Return As")
        save_as_button.clicked.connect(self.save_as_dialog)

        add_form_button = QPushButton("Add Form")
        add_form_button.clicked.connect(self.add_form)

        add_info_return_button = QPushButton("Add Info Return")
        add_info_return_button.clicked.connect(self.add_info_return)

        remove_sheet_button = QPushButton("Remove Sheet")
        remove_sheet_button.clicked.connect(self.remove_sheet)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Visible Sheets"))
        left_layout.addWidget(self.sheet_list, stretch=1)
        left_layout.addWidget(add_form_button)
        left_layout.addWidget(add_info_return_button)
        left_layout.addWidget(remove_sheet_button)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.path_label)

        button_row = QHBoxLayout()
        button_row.addWidget(new_return_button)
        button_row.addWidget(load_button)
        button_row.addWidget(save_as_button)
        button_row.addStretch(1)
        right_layout.addLayout(button_row)
        right_layout.addWidget(self.table, stretch=1)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        preview_layout = QVBoxLayout()
        preview_layout.addWidget(QLabel("PDF Preview"))
        self.pdf_stack.addWidget(self.pdf_placeholder_label)
        if QPdfDocument is not None and QPdfView is not None:
            pdf_widget = QWidget()
            pdf_widget_layout = QVBoxLayout()
            pdf_widget_layout.setContentsMargins(0, 0, 0, 0)
            self.pdf_document = QPdfDocument(self)
            self.pdf_view = QPdfView()
            self.pdf_view.setDocument(self.pdf_document)
            self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            pdf_widget_layout.addWidget(self.pdf_status_label)
            pdf_widget_layout.addWidget(self.pdf_view, stretch=1)
            pdf_widget.setLayout(pdf_widget_layout)
            self.pdf_stack.addWidget(pdf_widget)
        preview_layout.addWidget(self.pdf_stack, stretch=1)
        preview_widget = QWidget()
        preview_widget.setLayout(preview_layout)

        root_splitter = QSplitter(Qt.Horizontal)
        root_splitter.addWidget(left_widget)
        root_splitter.addWidget(right_widget)
        root_splitter.addWidget(preview_widget)
        root_splitter.setStretchFactor(0, 1)
        root_splitter.setStretchFactor(1, 4)
        root_splitter.setStretchFactor(2, 3)

        self.setCentralWidget(root_splitter)

        self._clear_loaded_return()
        if json_path and json_path.is_file():
            self.load_json(json_path)
        else:
            self.statusBar().showMessage(
                "App starts with no return loaded. Use New Return or Import Return from the toolbar.",
                6000,
            )

    def _current_jurisdiction(self) -> dict[str, Any]:
        if not self.jurisdiction_key:
            return {}
        return self.data.get(self.jurisdiction_key, {})

    def _project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    def _returns_dir(self) -> Path:
        returns_dir = self._project_root() / RETURNS_DIRNAME
        returns_dir.mkdir(parents=True, exist_ok=True)
        return returns_dir

    def _template_path(self) -> Path:
        return self._project_root() / RETURN_TEMPLATE_FILENAME

    def _default_return_filename(self) -> str:
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"return_{timestamp}.json"

    def _load_template_data(self, failure_title: str) -> tuple[dict[str, Any], str] | None:
        template_path = self._template_path()
        if not template_path.is_file():
            QMessageBox.critical(
                self,
                failure_title,
                f"Return template not found:\n{template_path}",
            )
            return None

        try:
            template_data = json.loads(template_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - UI message path
            QMessageBox.critical(self, failure_title, f"Could not read template JSON:\n{exc}")
            return None

        jurisdictions = _jurisdictions(template_data)
        if not jurisdictions:
            QMessageBox.critical(
                self,
                failure_title,
                "The return template does not contain a jurisdiction object.",
            )
            return None

        return (template_data, jurisdictions[0])

    def _show_pdf_placeholder(self, message: str) -> None:
        self.pdf_placeholder_label.setText(message)
        self.pdf_stack.setCurrentIndex(0)

    def _forms_pdf_dir(self) -> Path:
        return self._project_root() / "forms-instructions-and-publications" / "forms"

    def _info_return_pdf_dir(self) -> Path:
        return self._project_root() / "forms-instructions-and-publications" / "information-returns"

    def _current_preview_sheet(self) -> tuple[str, str, str | None] | None:
        sheet_id = self._current_visible_sheet_id()
        if not sheet_id:
            return None
        return self._parse_sheet_id(sheet_id)

    def _block_preview_mapping_id(self, parent_form_id: str, block_id: str) -> str:
        return f"{BLOCK_PREVIEW_MAPPING_PREFIX}{parent_form_id}__{block_id}"

    def _parse_block_preview_mapping_id(self, mapping_id: str) -> tuple[str, str] | None:
        if not mapping_id.startswith(BLOCK_PREVIEW_MAPPING_PREFIX):
            return None
        payload = mapping_id[len(BLOCK_PREVIEW_MAPPING_PREFIX) :]
        if "__" not in payload:
            return None
        parent_form_id, block_id = payload.split("__", 1)
        if not parent_form_id or not block_id:
            return None
        return parent_form_id, block_id

    def _mapped_preview_id(self, sheet_type: str, primary_id: str, secondary_id: str | None) -> str | None:
        if sheet_type == "form":
            return primary_id
        if sheet_type == "block" and secondary_id:
            return self._block_preview_mapping_id(primary_id, secondary_id)
        return None

    def _mapped_preview_source_path(self, form_id: str) -> Path | None:
        if self.pdf_preview_engine is None:
            return None
        return self.pdf_preview_engine.source_pdf_for_form(form_id)

    def _local_form_pdf_path(self, form_id: str) -> Path | None:
        candidate = self._forms_pdf_dir() / f"{form_id}.pdf"
        return candidate if candidate.is_file() else None

    def _block_pdf_name_candidates(self, block_id: str, block: dict[str, Any]) -> list[str]:
        candidates: list[str] = []

        def add_candidate(name: str | None) -> None:
            if not name:
                return
            normalized = str(name).strip()
            if not normalized:
                return
            if normalized not in candidates:
                candidates.append(normalized)

        form_ref = block.get("_form_ref")
        if isinstance(form_ref, str) and form_ref.strip():
            basename = form_ref.rsplit("/", 1)[-1].split("?", 1)[0].strip()
            add_candidate(basename)
            add_candidate(re.sub(r"--\d{4}(?=\.pdf$)", "", basename))
            add_candidate(re.sub(r"-\d{4}(?=\.pdf$)", "", basename))

        compact_block_id = re.sub(r"[^a-z0-9]", "", block_id.lower())
        if compact_block_id:
            if compact_block_id.startswith("w2g"):
                add_candidate("fw2g.pdf")
            elif compact_block_id.startswith("w2"):
                add_candidate("fw2.pdf")
            elif compact_block_id.startswith(("1098", "1099")):
                add_candidate(f"f{compact_block_id}.pdf")

        description = str(block.get("description") or "")
        for token in re.findall(r"(?:W-2G|W-2|109[589]-[A-Z]+|109[589])", description, flags=re.IGNORECASE):
            compact_token = re.sub(r"[^a-z0-9]", "", token.lower())
            if compact_token == "w2g":
                add_candidate("fw2g.pdf")
            elif compact_token == "w2":
                add_candidate("fw2.pdf")
            else:
                add_candidate(f"f{compact_token}.pdf")

        return candidates

    def _block_preview_source_path_for_block(self, block_id: str, block: dict[str, Any]) -> Path | None:
        search_dirs = (self._info_return_pdf_dir(), self._forms_pdf_dir())
        for filename in self._block_pdf_name_candidates(block_id, block):
            for directory in search_dirs:
                candidate = directory / filename
                if candidate.is_file():
                    return candidate
        return None

    def _block_preview_source_path(self, parent_form_id: str, block_id: str) -> Path | None:
        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id)
        if not isinstance(block, dict):
            return None
        return self._block_preview_source_path_for_block(block_id, block)

    def _current_block_preview_entry_index(self, parent_form_id: str, block_id: str) -> int:
        current_row = self.table.currentRow()
        if 0 <= current_row < self.table.rowCount():
            row_item = self.table.item(current_row, 0)
            if row_item is not None:
                cell_ref = row_item.data(Qt.UserRole)
                if (
                    isinstance(cell_ref, tuple)
                    and len(cell_ref) >= 5
                    and cell_ref[0] == "block"
                    and cell_ref[1] == parent_form_id
                    and cell_ref[2] == block_id
                ):
                    return int(cell_ref[3])

        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id) or {}
        entries = block.get("entries") or []
        for entry_index, entry in enumerate(entries):
            if isinstance(entry, dict):
                return entry_index
        return 0

    def _block_entry_preview_value(self, entry: dict[str, Any], source: str) -> Any:
        if source == "entry":
            return entry
        if not source.startswith("entry."):
            return None
        current: Any = entry
        for part in source.split(".")[1:]:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if 0 <= index < len(current) else None
            else:
                return None
        return current

    def _block_recipient_context(self, entry: dict[str, Any]) -> dict[str, Any]:
        info_form = self._current_jurisdiction().get("f1040_Federal_Info_Worksheet") or {}
        info_cells = info_form.get("cells") or {}
        recipient_key = "spouse" if str(entry.get("recipient", "taxpayer")).strip().lower() == "spouse" else "taxpayer"
        first_name = str((info_cells.get(f"{recipient_key}_first_name") or {}).get("value", "") or "").strip()
        last_name = str((info_cells.get(f"{recipient_key}_last_name") or {}).get("value", "") or "").strip()
        middle_initial = str((info_cells.get(f"{recipient_key}_middle_initial") or {}).get("value", "") or "").strip()
        suffix = str((info_cells.get(f"{recipient_key}_suffix") or {}).get("value", "") or "").strip()
        name_parts = [first_name]
        if middle_initial:
            name_parts.append(middle_initial)
        if last_name:
            name_parts.append(last_name)
        if suffix:
            name_parts.append(suffix)
        city = str((info_cells.get("city") or {}).get("value", "") or "").strip()
        state = str((info_cells.get("state") or {}).get("value", "") or "").strip()
        zip_code = str((info_cells.get("zip_code") or {}).get("value", "") or "").strip()
        city_state_zip_parts = [part for part in (city, state, zip_code) if part]
        return {
            "recipient": recipient_key,
            "recipient_first_name": first_name,
            "recipient_last_name": last_name,
            "recipient_middle_initial": middle_initial,
            "recipient_suffix": suffix,
            "recipient_name": " ".join(part for part in name_parts if part).strip(),
            "recipient_ssn": str((info_cells.get(f"{recipient_key}_ssn") or {}).get("value", "") or "").strip(),
            "recipient_address_line": str((info_cells.get("address") or {}).get("value", "") or "").strip(),
            "recipient_city_state_zip": ", ".join(city_state_zip_parts[:2]) + (f" {city_state_zip_parts[2]}" if len(city_state_zip_parts) >= 3 else ""),
        }

    def _resolve_block_preview_source(self, parent_form_id: str, block_id: str, source: str) -> Any:
        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id) or {}
        entries = block.get("entries") or []
        entry_index = self._current_block_preview_entry_index(parent_form_id, block_id)
        entry = entries[entry_index] if 0 <= entry_index < len(entries) else {}
        if not isinstance(entry, dict):
            entry = {}

        expr = source.strip()
        if not expr:
            return None
        if expr.startswith("entry"):
            return self._block_entry_preview_value(entry, expr)
        if expr == "tax_year":
            match = re.search(r"(\d{4})", str(self.jurisdiction_key or ""))
            return match.group(1) if match else ""
        context = self._block_recipient_context(entry)
        if expr in context:
            return context[expr]
        return None

    def _raw_preview_source_path(self, sheet_type: str, primary_id: str, secondary_id: str | None) -> Path | None:
        if sheet_type == "form":
            mapped_source = self._mapped_preview_source_path(primary_id)
            if mapped_source and mapped_source.is_file():
                return mapped_source
            return self._local_form_pdf_path(primary_id)
        if sheet_type == "block" and secondary_id:
            return self._block_preview_source_path(primary_id, secondary_id)
        return None

    def _resolve_pdf_mapping_source(self, form_id: str, source: str) -> Any:
        block_mapping = self._parse_block_preview_mapping_id(form_id)
        if block_mapping is not None:
            parent_form_id, block_id = block_mapping
            return self._resolve_block_preview_source(parent_form_id, block_id, source)
        expr = source.strip()
        if not expr:
            return None
        return self._evaluate_equation(form_id, expr, set())

    def _load_pdf_into_view(self, pdf_path: Path, status_message: str) -> None:
        if self.pdf_document is None or self.pdf_view is None:
            self._show_pdf_placeholder(status_message)
            return
        self.pdf_status_label.setText(status_message)
        self.pdf_document.load(str(pdf_path))
        self.pdf_stack.setCurrentIndex(1)

    def _update_pdf_preview(self) -> None:
        preview_sheet = self._current_preview_sheet()
        if not preview_sheet:
            self._show_pdf_placeholder("PDF preview is blank until a sheet is selected.")
            return
        if not self.data or not self.jurisdiction_key:
            self._show_pdf_placeholder("Start a return to preview sheets.")
            return

        sheet_type, primary_id, secondary_id = preview_sheet
        sheet_label = self._sheet_label(self._current_visible_sheet_id() or "")
        preview_form_id = self._mapped_preview_id(sheet_type, primary_id, secondary_id)
        raw_pdf = self._raw_preview_source_path(sheet_type, primary_id, secondary_id)

        if preview_form_id is None or self.pdf_preview_engine is None:
            if raw_pdf and raw_pdf.is_file():
                self._load_pdf_into_view(raw_pdf, f"Raw {sheet_label} preview")
            else:
                self._show_pdf_placeholder(f"No local PDF is available yet for {sheet_label}.")
            return

        if not self.pdf_preview_engine.has_mapping_for_form(preview_form_id):
            if raw_pdf and raw_pdf.is_file():
                self._load_pdf_into_view(raw_pdf, f"Raw {sheet_label} preview")
            else:
                self._show_pdf_placeholder(f"No local PDF is available yet for {sheet_label}.")
            return

        if not self.pdf_preview_engine.available():
            if raw_pdf and raw_pdf.is_file():
                self._load_pdf_into_view(
                    raw_pdf,
                    f"Raw {sheet_label} preview (install PDF preview dependencies for filled previews)",
                )
            else:
                self._show_pdf_placeholder(
                    "Install the PDF preview dependencies from requirements.txt to enable this pane."
                )
            return

        try:
            preview_path = self.pdf_preview_engine.render_preview(
                form_id=preview_form_id,
                resolve_source=lambda source: self._resolve_pdf_mapping_source(preview_form_id, source),
            )
        except Exception as exc:
            if raw_pdf and raw_pdf.is_file():
                self._load_pdf_into_view(raw_pdf, f"Preview fallback: raw {sheet_label} ({exc})")
            else:
                self._show_pdf_placeholder(f"Could not render {sheet_label} preview: {exc}")
            return

        self._load_pdf_into_view(preview_path, f"Filled {sheet_label} preview")

    def _clear_loaded_return(self) -> None:
        self.data = {}
        self.current_path = None
        self.jurisdiction_key = None
        self.visible_sheet_ids = []
        self.overridden_cells.clear()
        self.touched_input_cells.clear()
        self.table.setRowCount(0)
        self.sheet_list.clear()
        self.path_label.setText("No return loaded. Choose New Return or Import Return.")
        self._show_pdf_placeholder("PDF preview is blank until a sheet is selected.")

    def _initialize_touched_input_cells(self) -> None:
        self.touched_input_cells.clear()
        for form_id, form_data in self._available_forms():
            cells = form_data.get("cells") or {}
            for cell_id, cell in cells.items():
                if not isinstance(cell, dict):
                    continue
                if not bool(cell.get("manual_entry", False)):
                    continue
                value = cell.get("value")
                default = cell.get("default")
                format_code = cell.get("format", "text")
                if format_code in {"text", "date"}:
                    if isinstance(value, str) and value.strip():
                        self.touched_input_cells.add((form_id, cell_id))
                elif value != default:
                    self.touched_input_cells.add((form_id, cell_id))

    def _load_reference_data(self) -> None:
        self.reference_data = {}
        ref_root = self._project_root() / "reference-data" / "federal" / "2025"
        for stem in REFERENCE_DATA_FILES:
            ref_path = ref_root / f"{stem}.json"
            if not ref_path.is_file():
                continue
            try:
                self.reference_data[stem] = json.loads(ref_path.read_text(encoding="utf-8"))
            except Exception:
                self.reference_data[stem] = {}

    def _available_forms(self) -> list[tuple[str, dict[str, Any]]]:
        jdata = self._current_jurisdiction()
        forms = []
        for form_id, form_data in jdata.items():
            if isinstance(form_data, dict) and isinstance(form_data.get("cells"), dict):
                forms.append((form_id, form_data))
        return sorted(forms, key=_form_sort_key)

    def _default_visible_forms(self) -> list[str]:
        form_ids = [form_id for form_id, _ in self._available_forms()]
        preferred = [form_id for form_id in PREFERRED_INITIAL_SHEETS if form_id in form_ids]
        if preferred:
            return preferred
        return form_ids[:2]

    def _form_sheet_id(self, form_id: str) -> str:
        return f"{FORM_SHEET_PREFIX}{form_id}"

    def _block_sheet_id(self, parent_form_id: str, block_id: str) -> str:
        return f"{BLOCK_SHEET_PREFIX}{parent_form_id}:{block_id}"

    def _parse_sheet_id(self, sheet_id: str) -> tuple[str, str, str | None]:
        if sheet_id.startswith(FORM_SHEET_PREFIX):
            return ("form", sheet_id[len(FORM_SHEET_PREFIX) :], None)
        if sheet_id.startswith(BLOCK_SHEET_PREFIX):
            payload = sheet_id[len(BLOCK_SHEET_PREFIX) :]
            if ":" in payload:
                parent_form_id, block_id = payload.split(":", 1)
                return ("block", parent_form_id, block_id)
        return ("form", sheet_id, None)

    def _is_worksheet(self, form_id: str) -> bool:
        form_data = self._current_jurisdiction().get(form_id) or {}
        meta = form_data.get("_meta") or {}
        title = str(meta.get("name", "")).lower()
        return "worksheet" in form_id.lower() or "worksheet" in title

    def _sheet_label(self, sheet_id: str) -> str:
        sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
        jdata = self._current_jurisdiction()
        if sheet_type == "block" and secondary_id:
            form_data = jdata.get(primary_id) or {}
            block = (form_data.get("blocks") or {}).get(secondary_id) or {}
            description = block.get("description") or secondary_id
            form_title = (form_data.get("_meta") or {}).get("name") or primary_id
            return f"{description} ({secondary_id} on {form_title})"
        form_data = jdata.get(primary_id) or {}
        return _form_label(primary_id, form_data) if isinstance(form_data, dict) else primary_id

    def _block_candidates(self) -> list[tuple[str, str, str]]:
        candidates: list[tuple[str, str, str]] = []
        for form_id, form_data in self._available_forms():
            blocks = form_data.get("blocks") or {}
            for block_id, block in blocks.items():
                if not isinstance(block, dict):
                    continue
                if not bool(block.get("user_entered", False)):
                    continue
                if not isinstance(block.get("item_cells"), dict):
                    continue
                description = block.get("description") or block_id
                description_lower = str(description).lower()
                if not (
                    block.get("_form_ref")
                    or "form" in description_lower
                    or "1099" in description_lower
                    or "1098" in description_lower
                    or "w-2" in description_lower
                    or "k-1" in description_lower
                ):
                    continue
                if self._block_preview_source_path_for_block(block_id, block) is None:
                    continue
                form_title = (form_data.get("_meta") or {}).get("name") or form_id
                candidates.append((f"{description} ({block_id} on {form_title})", form_id, block_id))
        return sorted(candidates)

    def _referenced_forms(self, form_id: str) -> list[str]:
        jdata = self._current_jurisdiction()
        form_data = jdata.get(form_id) or {}
        cells = form_data.get("cells") or {}
        refs: set[str] = set()
        for cell in cells.values():
            if not isinstance(cell, dict):
                continue
            equation = str(cell.get("equation", ""))
            for ref_form_id, _ in FORM_REF_PATTERN.findall(equation):
                if ref_form_id != form_id and ref_form_id in jdata:
                    refs.add(ref_form_id)
        return sorted(refs, key=lambda candidate_id: _form_sort_key((candidate_id, jdata.get(candidate_id) or {})))

    def _worksheet_dependencies(self, form_id: str) -> list[str]:
        return [candidate_id for candidate_id in self._referenced_forms(form_id) if self._is_worksheet(candidate_id)]

    def _ensure_visible_sheets(self, sheet_ids: list[str], *, select_sheet_id: str | None = None) -> None:
        for sheet_id in sheet_ids:
            if sheet_id not in self.visible_sheet_ids:
                self.visible_sheet_ids.append(sheet_id)
        self._refresh_sheet_list(select_sheet_id=select_sheet_id)

    def _sheet_exists(self, sheet_id: str) -> bool:
        sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
        jdata = self._current_jurisdiction()
        form_data = jdata.get(primary_id)
        if not isinstance(form_data, dict):
            return False
        if sheet_type == "form":
            return isinstance(form_data.get("cells"), dict)
        if sheet_type == "block" and secondary_id:
            return isinstance((form_data.get("blocks") or {}).get(secondary_id), dict)
        return False

    def _form_has_user_activity(self, form_id: str, form_data: dict[str, Any]) -> bool:
        del form_data
        if any(active_form_id == form_id for active_form_id, _ in self.touched_input_cells):
            return True
        if any(active_form_id == form_id for active_form_id, _ in self.overridden_cells):
            return True
        return False

    def _used_block_ids(self, form_data: dict[str, Any]) -> list[str]:
        used_block_ids: list[str] = []
        blocks = form_data.get("blocks") or {}
        for block_id, block in blocks.items():
            if not isinstance(block, dict):
                continue
            entries = block.get("entries") or []
            if any(isinstance(entry, dict) for entry in entries):
                used_block_ids.append(block_id)
        return used_block_ids

    def _form_filing_requirement(self, form_data: dict[str, Any]) -> str:
        meta = form_data.get("_meta") or {}
        return str(meta.get("filing_requirement", "")).strip()

    def _cell_has_meaningful_value(self, cell: dict[str, Any]) -> bool:
        value = cell.get("value")
        default = cell.get("default")
        format_code = str(cell.get("format", "text"))
        if format_code in {"text", "date"}:
            return isinstance(value, str) and value.strip() != ""
        if isinstance(value, bool):
            return value is True
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                return False
            return value != default and value != 0
        return value not in (None, "", default)

    def _form_has_meaningful_values(self, form_data: dict[str, Any]) -> bool:
        cells = form_data.get("cells") or {}
        for cell in cells.values():
            if isinstance(cell, dict) and self._cell_has_meaningful_value(cell):
                return True
        return False

    def _cell_value(self, form_id: str, cell_id: str) -> Any:
        cell = self._get_form_cell(form_id, cell_id)
        if not isinstance(cell, dict):
            return None
        return cell.get("value")

    def _cell_amount(self, form_id: str, cell_id: str) -> float:
        value = self._cell_value(form_id, cell_id)
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(number):
            return 0.0
        return number

    def _block_has_entries(self, parent_form_id: str, block_id: str) -> bool:
        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id) or {}
        entries = block.get("entries") or []
        return any(isinstance(entry, dict) for entry in entries)

    def _should_file_form_now(self, form_id: str, form_data: dict[str, Any]) -> bool:
        if self._form_filing_requirement(form_data) != "file_with_return":
            return False
        if form_id == "f1040":
            return True
        if form_id == "f1040sa":
            itemized = self._cell_amount("f1040sa", "itemized")
            line_12e = self._cell_amount("f1040", "12e")
            return itemized > 0.0 and abs(itemized - line_12e) < 0.01
        if form_id == "f1040sb":
            return (
                self._cell_amount("f1040sb", "3") > 1500.0
                or self._cell_amount("f1040sb", "6") > 1500.0
                or bool(self._cell_value("f1040sb", "7a"))
                or bool(self._cell_value("f1040sb", "8"))
            )
        if form_id == "f1040sf":
            return abs(self._cell_amount("f1040sf", "34")) > 0.009 or self._form_has_user_activity(form_id, form_data)
        if form_id == "f1040sc":
            return (
                abs(self._cell_amount("f1040sc", "31")) > 0.009
                or abs(self._cell_amount("f1040sc", "1")) > 0.009
                or self._form_has_user_activity(form_id, form_data)
            )
        if form_id == "f1040sd":
            return (
                self._block_has_entries("f1040", "1099_b")
                or self._block_has_entries("f1040", "1099_da")
                or self._block_has_entries("f1040", "1099_s")
                or (abs(self._cell_amount("f1040", "7a")) > 0.009 and not bool(self._cell_value("f1040", "7b")))
                or self._form_has_user_activity(form_id, form_data)
            )
        if form_id == "f1040se":
            return abs(self._cell_amount("f1040se", "41")) > 0.009 or self._form_has_user_activity(form_id, form_data)
        if form_id == "f8949":
            return (
                self._block_has_entries("f1040", "1099_b")
                or self._block_has_entries("f1040", "1099_da")
                or self._block_has_entries("f1040", "1099_s")
                or self._form_has_user_activity(form_id, form_data)
            )
        if form_id == "f4952":
            return self._cell_amount("f4952", "8") > 0.0 and not bool(self._cell_value("f4952", "filing_exception_met"))
        if form_id == "f1040sh":
            return bool(self._cell_value("f1040sh", "required_to_file_schedule_h")) or self._cell_amount("f1040sh", "schedule2_line9_output") > 0.0
        if form_id == "f1040sr_schedule_r":
            return abs(self._cell_amount("f1040sr_schedule_r", "schedule3_6d")) > 0.009 or self._form_has_user_activity(form_id, form_data)
        if form_id == "f1040s1":
            return abs(self._cell_amount("f1040", "8")) > 0.009 or abs(self._cell_amount("f1040", "10")) > 0.009
        if form_id == "f1040s2":
            return abs(self._cell_amount("f1040", "17")) > 0.009 or abs(self._cell_amount("f1040", "23")) > 0.009
        if form_id == "f1040s3":
            return abs(self._cell_amount("f1040", "20")) > 0.009 or abs(self._cell_amount("f1040", "31")) > 0.009
        if form_id == "f8812":
            return (
                self._cell_amount("f8812", "14") > 0.0
                or self._cell_amount("f8812", "27") > 0.0
                or self._cell_amount("f8812", "4") > 0.0
                or self._cell_amount("f8812", "6") > 0.0
            )
        if form_id == "f1116":
            direct_election_total = self._cell_amount("f1116", "direct_election_total_foreign_tax")
            direct_election_threshold = self._cell_amount("f1116", "direct_election_threshold")
            direct_election_likely_eligible = bool(self._cell_value("f1116", "direct_election_likely_eligible"))
            elected_without_form = bool(self._cell_value("f1116", "elect_credit_without_form_1116"))
            has_foreign_tax_facts = (
                direct_election_total > 0.0
                or self._cell_amount("f1116", "8") > 0.0
                or self._block_has_entries("f1040", "foreign_tax_credit_items")
            )
            if elected_without_form:
                return False
            if self._form_has_user_activity(form_id, form_data):
                return has_foreign_tax_facts
            if self._cell_amount("f1116", "35") > 0.0:
                return True
            if has_foreign_tax_facts and (not direct_election_likely_eligible or direct_election_total > direct_election_threshold):
                return True
            return False
        if form_id == "f1116sb":
            return self._should_file_form_now("f1116", self._current_jurisdiction().get("f1116") or {}) and (
                self._form_has_user_activity(form_id, form_data)
                or self._form_has_meaningful_values(form_data)
            )
        if form_id == "f1116sc":
            return self._should_file_form_now("f1116", self._current_jurisdiction().get("f1116") or {}) and (
                self._form_has_user_activity(form_id, form_data)
                or self._form_has_meaningful_values(form_data)
            )
        if form_id == "f2210":
            return (
                self._cell_amount("f2210", "19") > 0.0
                or bool(self._cell_value("f2210", "A"))
                or bool(self._cell_value("f2210", "B"))
                or bool(self._cell_value("f2210", "C"))
                or bool(self._cell_value("f2210", "D"))
            )
        if form_id == "f2210_Schedule_AI":
            return bool(self._cell_value("f2210", "C"))
        if form_id == "f4562":
            return (
                abs(self._cell_amount("f4562", "schedule_c_depreciation")) > 0.009
                or abs(self._cell_amount("f4562", "schedule_e_depreciation")) > 0.009
                or self._form_has_user_activity(form_id, form_data)
            )
        if form_id == "f6198":
            return (
                abs(self._cell_amount("f6198", "schedule_c_adjustment")) > 0.009
                or abs(self._cell_amount("f6198", "schedule_e_adjustment")) > 0.009
                or abs(self._cell_amount("f6198", "disallowed_loss_carryforward")) > 0.009
                or self._form_has_user_activity(form_id, form_data)
            )
        if form_id == "f8582":
            return (
                abs(self._cell_amount("f8582", "schedule_e_adjustment")) > 0.009
                or abs(self._cell_amount("f8582", "disallowed_passive_loss_carryforward")) > 0.009
                or self._form_has_user_activity(form_id, form_data)
            )
        if form_id == "f8582cr":
            return abs(self._cell_amount("f8582cr", "passive_credit_carryforward")) > 0.009 or self._form_has_user_activity(form_id, form_data)
        if form_id == "f8829":
            return abs(self._cell_amount("f8829", "deduction_to_schedule_c")) > 0.009 or self._form_has_user_activity(form_id, form_data)
        if form_id == "f7206":
            return abs(self._cell_amount("f7206", "schedule1_17_deduction")) > 0.009 or self._form_has_user_activity(form_id, form_data)
        if form_id == "f8814":
            return (
                abs(self._cell_amount("f8814", "schedule1_8g_alaska_dividends")) > 0.009
                or abs(self._cell_amount("f8814", "schedule1_8z_other_income")) > 0.009
                or abs(self._cell_amount("f8814", "investment_income_carryin")) > 0.009
                or self._form_has_user_activity(form_id, form_data)
            )
        return self._form_has_user_activity(form_id, form_data) or bool(self._used_block_ids(form_data))

    def _filed_form_ids(self) -> list[str]:
        filed_form_ids: list[str] = []
        for form_id, form_data in self._available_forms():
            if self._should_file_form_now(form_id, form_data):
                filed_form_ids.append(form_id)
        return filed_form_ids

    def _auto_visible_sheet_ids(self) -> list[str]:
        jdata = self._current_jurisdiction()
        if not jdata:
            return []

        base_form_ids = set(self._default_visible_forms())
        filed_form_ids = set(self._filed_form_ids())
        active_form_ids: set[str] = set()
        for form_id, form_data in self._available_forms():
            if self._form_has_user_activity(form_id, form_data):
                active_form_ids.add(form_id)
            if self._form_has_meaningful_values(form_data):
                active_form_ids.add(form_id)
            if self._used_block_ids(form_data):
                active_form_ids.add(form_id)

        expanded_form_ids = set(base_form_ids) | filed_form_ids | active_form_ids
        queue = list(filed_form_ids | active_form_ids)
        while queue:
            current_form_id = queue.pop(0)
            for dependency_id in self._worksheet_dependencies(current_form_id):
                if dependency_id in expanded_form_ids:
                    continue
                expanded_form_ids.add(dependency_id)
                queue.append(dependency_id)

        sheet_ids: list[str] = []
        ordered_filed_form_ids = [form_id for form_id, _ in self._available_forms() if form_id in filed_form_ids]
        for form_id, form_data in self._available_forms():
            if form_id not in ordered_filed_form_ids:
                continue
            sheet_ids.append(self._form_sheet_id(form_id))
            for block_id in self._used_block_ids(form_data):
                sheet_ids.append(self._block_sheet_id(form_id, block_id))
        for form_id, form_data in self._available_forms():
            if form_id in ordered_filed_form_ids or form_id not in expanded_form_ids:
                continue
            sheet_ids.append(self._form_sheet_id(form_id))
            for block_id in self._used_block_ids(form_data):
                sheet_ids.append(self._block_sheet_id(form_id, block_id))
        return sheet_ids

    def _sync_visible_sheets_from_usage(
        self,
        *,
        select_sheet_id: str | None = None,
        preserve_existing: bool = True,
    ) -> None:
        auto_sheet_ids = self._auto_visible_sheet_ids()
        if preserve_existing:
            merged_sheet_ids = [sheet_id for sheet_id in self.visible_sheet_ids if self._sheet_exists(sheet_id)]
            for sheet_id in auto_sheet_ids:
                if sheet_id not in merged_sheet_ids:
                    merged_sheet_ids.append(sheet_id)
            self.visible_sheet_ids = merged_sheet_ids
        else:
            self.visible_sheet_ids = auto_sheet_ids

        target_sheet_id = select_sheet_id or self._current_visible_sheet_id()
        if target_sheet_id not in self.visible_sheet_ids:
            target_sheet_id = self.visible_sheet_ids[0] if self.visible_sheet_ids else None
        self._refresh_sheet_list(select_sheet_id=target_sheet_id)

    def _blank_block_field_value(self, field: dict[str, Any]) -> Any:
        if field.get("type") == "repeating":
            return []
        return copy.deepcopy(field.get("default"))

    def _block_field_should_serialize(self, value: Any, field: dict[str, Any]) -> bool:
        if field.get("type") == "repeating":
            return isinstance(value, list) and len(value) > 0
        format_code = field.get("format", "text")
        default_value = self._blank_block_field_value(field)
        if format_code in {"text", "date"}:
            return isinstance(value, str) and value.strip() != ""
        if format_code == "boolean":
            return value != default_value
        return value not in (None, "") and value != default_value

    def _new_block_entry(self, block: dict[str, Any]) -> dict[str, Any]:
        entry: dict[str, Any] = {}
        item_cells = block.get("item_cells") or {}
        for field_id, field in item_cells.items():
            if isinstance(field, dict):
                entry[field_id] = self._blank_block_field_value(field)
        return entry

    def _append_blank_block_entry(self, parent_form_id: str, block_id: str) -> int | None:
        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id)
        if not isinstance(block, dict):
            return None
        entries = block.setdefault("entries", [])
        if not isinstance(entries, list):
            return None
        entries.append(self._new_block_entry(block))
        return len(entries)

    def _ensure_block_entry(self, parent_form_id: str, block_id: str, entry_index: int) -> dict[str, Any] | None:
        if entry_index < 0:
            return None
        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id)
        if not isinstance(block, dict):
            return None
        entries = block.setdefault("entries", [])
        if not isinstance(entries, list):
            return None
        while len(entries) <= entry_index:
            entries.append(self._new_block_entry(block))
        entry = entries[entry_index]
        if isinstance(entry, dict):
            return entry
        entries[entry_index] = self._new_block_entry(block)
        return entries[entry_index]

    def _refresh_sheet_list(self, select_sheet_id: str | None = None) -> None:
        self.sheet_list.clear()
        filed_form_ids = set(self._filed_form_ids())
        for sheet_id in self.visible_sheet_ids:
            item = QListWidgetItem(self._sheet_label(sheet_id))
            item.setData(Qt.UserRole, sheet_id)
            sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
            del secondary_id
            if sheet_type == "form" and primary_id in filed_form_ids:
                item.setBackground(FILED_FORM_BACKGROUND)
            self.sheet_list.addItem(item)

        if self.sheet_list.count() == 0:
            self.table.setRowCount(0)
            return

        target_sheet_id = select_sheet_id or self.visible_sheet_ids[0]
        for idx in range(self.sheet_list.count()):
            item = self.sheet_list.item(idx)
            if item.data(Qt.UserRole) == target_sheet_id:
                self.sheet_list.setCurrentRow(idx)
                break
        else:
            self.sheet_list.setCurrentRow(0)

    def load_json_dialog(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Import Saved Return",
            str(self.current_path.parent if self.current_path else self._returns_dir()),
            "JSON Files (*.json)",
        )
        if path_str:
            self.load_json(Path(path_str))

    def new_return(self) -> None:
        template_bundle = self._load_template_data("New Return Failed")
        if template_bundle is None:
            return
        template_data, jurisdiction_key = template_bundle

        self.data = copy.deepcopy(template_data)
        self.current_path = None
        self.jurisdiction_key = jurisdiction_key
        self.suggested_return_filename = self._default_return_filename()
        self._load_reference_data()
        self.overridden_cells.clear()
        self.touched_input_cells.clear()
        self.recalculate_all()
        self.path_label.setText(
            f"New return started from template: {self._template_path().name} (unsaved)"
        )
        self._sync_visible_sheets_from_usage(preserve_existing=False)
        self.statusBar().showMessage(
            f"Started a new return. Save it in {self._returns_dir()} when ready.",
            6000,
        )

    def _looks_like_flat_return_data(self, data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        if data.get(FLAT_RETURN_FORMAT_KEY) == FLAT_RETURN_FORMAT:
            return True
        if _jurisdictions(data):
            return False
        return any(isinstance(key, str) and "." in key for key in data)

    def _serialize_flat_return_data(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            FLAT_RETURN_FORMAT_KEY: FLAT_RETURN_FORMAT,
            FLAT_RETURN_TEMPLATE_KEY: RETURN_TEMPLATE_FILENAME,
            FLAT_RETURN_JURISDICTION_KEY: self.jurisdiction_key or "",
        }
        override_keys: list[str] = []

        for form_id, form_data in self._available_forms():
            cells = form_data.get("cells") or {}
            for cell_id, cell in cells.items():
                if not isinstance(cell, dict):
                    continue
                flat_key = f"{form_id}.{cell_id}"
                if cell.get("override_possible", False) and (form_id, cell_id) in self.overridden_cells:
                    payload[flat_key] = copy.deepcopy(cell.get("value"))
                    override_keys.append(flat_key)
                    continue
                if cell.get("manual_entry", False) and (form_id, cell_id) in self.touched_input_cells:
                    payload[flat_key] = copy.deepcopy(cell.get("value"))

            blocks = form_data.get("blocks") or {}
            for block_id, block in blocks.items():
                if not isinstance(block, dict):
                    continue
                item_cells = block.get("item_cells") or {}
                entries = block.get("entries") or []
                if not isinstance(entries, list):
                    continue
                for entry_index, entry in enumerate(entries):
                    if not isinstance(entry, dict):
                        continue
                    payload[f"{form_id}.{block_id}.{entry_index}.{FLAT_RETURN_ENTRY_MARKER}"] = True
                    for field_id, field in item_cells.items():
                        if not isinstance(field, dict):
                            continue
                        value = entry.get(field_id, self._blank_block_field_value(field))
                        if self._block_field_should_serialize(value, field):
                            payload[f"{form_id}.{block_id}.{entry_index}.{field_id}"] = copy.deepcopy(value)

        if override_keys:
            payload[FLAT_RETURN_OVERRIDES_KEY] = sorted(override_keys)
        return payload

    def _apply_flat_return_value(self, flat_key: str, value: Any, override_keys: set[str]) -> bool:
        parts = flat_key.split(".")
        if len(parts) == 2:
            form_id, cell_id = parts
            cell = self._get_form_cell(form_id, cell_id)
            if not isinstance(cell, dict):
                return False
            if cell.get("manual_entry", False):
                cell["value"] = copy.deepcopy(value)
                self.touched_input_cells.add((form_id, cell_id))
                return True
            if cell.get("override_possible", False) and flat_key in override_keys:
                cell["value"] = copy.deepcopy(value)
                self.overridden_cells.add((form_id, cell_id))
                return True
            return False

        if len(parts) >= 4 and parts[2].isdigit():
            parent_form_id, block_id = parts[0], parts[1]
            entry_index = int(parts[2])
            field_id = ".".join(parts[3:])
            entry = self._ensure_block_entry(parent_form_id, block_id, entry_index)
            if not isinstance(entry, dict):
                return False
            if field_id == FLAT_RETURN_ENTRY_MARKER:
                return True
            form_data = self._current_jurisdiction().get(parent_form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id) or {}
            field = (block.get("item_cells") or {}).get(field_id)
            if not isinstance(field, dict):
                return False
            entry[field_id] = copy.deepcopy(value)
            return True

        return False

    def _load_flat_return_data(self, path: Path, flat_data: dict[str, Any]) -> None:
        template_bundle = self._load_template_data("Load Failed")
        if template_bundle is None:
            return
        template_data, default_jurisdiction_key = template_bundle
        jurisdiction_key = str(flat_data.get(FLAT_RETURN_JURISDICTION_KEY) or default_jurisdiction_key)
        if jurisdiction_key not in _jurisdictions(template_data):
            jurisdiction_key = default_jurisdiction_key

        self.data = copy.deepcopy(template_data)
        self.current_path = path
        self.jurisdiction_key = jurisdiction_key
        self.suggested_return_filename = path.name
        self._load_reference_data()
        self.overridden_cells.clear()
        self.touched_input_cells.clear()

        raw_override_keys = flat_data.get(FLAT_RETURN_OVERRIDES_KEY, [])
        if isinstance(raw_override_keys, list):
            override_keys = {str(value) for value in raw_override_keys if isinstance(value, str)}
        else:
            override_keys = set()

        for flat_key, value in flat_data.items():
            if not isinstance(flat_key, str) or flat_key.startswith("_"):
                continue
            self._apply_flat_return_value(flat_key, value, override_keys)

        self.recalculate_all()
        self.path_label.setText(f"Imported return data: {path}")
        self._sync_visible_sheets_from_usage(preserve_existing=False)
        self.statusBar().showMessage(f"Loaded {path.name}", 4000)

    def load_json(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - UI message path
            QMessageBox.critical(self, "Load Failed", f"Could not load JSON:\n{exc}")
            return

        if self._looks_like_flat_return_data(data):
            self._load_flat_return_data(path, data)
            return

        jurisdictions = _jurisdictions(data)
        if not jurisdictions:
            QMessageBox.critical(self, "Load Failed", "JSON does not contain a jurisdiction object.")
            return

        self.data = data
        self.current_path = path
        self.jurisdiction_key = jurisdictions[0]
        self.suggested_return_filename = path.name
        self._load_reference_data()
        self.overridden_cells.clear()
        self._initialize_touched_input_cells()
        self.recalculate_all(detect_existing_overrides=True)
        self.path_label.setText(f"Imported return: {path}")
        self._sync_visible_sheets_from_usage(preserve_existing=False)
        self.statusBar().showMessage(f"Loaded {path.name}", 4000)

    def _filing_status_key(self) -> str:
        f1040 = self._current_jurisdiction().get("f1040") or {}
        cells = f1040.get("cells") or {}
        if (cells.get("filing_status_married_jointly") or {}).get("value"):
            return "married_filing_jointly"
        if (cells.get("filing_status_qss") or {}).get("value"):
            return "qualifying_surviving_spouse"
        if (cells.get("filing_status_married_separately") or {}).get("value"):
            return "married_filing_separately"
        if (cells.get("filing_status_hoh") or {}).get("value"):
            return "head_of_household"
        return "single"

    def _eic_status_group(self) -> str | None:
        filing_status = self._filing_status_key()
        if filing_status == "married_filing_jointly":
            return "married_filing_jointly"
        if filing_status == "married_filing_separately":
            info_form = self._current_jurisdiction().get("f1040_Federal_Info_Worksheet") or {}
            info_cells = info_form.get("cells") or {}
            if (info_cells.get("mfs_did_not_live_with_spouse") or {}).get("value"):
                return "single_head_of_household_qss_or_qualified_mfs"
            return None
        return "single_head_of_household_qss_or_qualified_mfs"

    def _lookup_tax(self, taxable_income: Any) -> Any:
        try:
            amount = int(float(taxable_income))
        except (TypeError, ValueError):
            return 0
        if amount <= 0:
            return 0
        tax_data = self.reference_data.get("ordinary_income_tax") or {}
        datasets = tax_data.get("datasets") or {}
        filing_status = self._filing_status_key()
        if amount < 100000:
            rows = ((datasets.get("tax_table") or {}).get("rows")) or []
            for row in rows:
                if row.get("at_least", 0) <= amount < row.get("but_less_than", 0):
                    return row.get(filing_status, 0)
            return 0

        brackets = (((datasets.get("tax_computation_schedule") or {}).get("brackets")) or {}).get(filing_status) or []
        amount_float = float(amount)
        for bracket in brackets:
            lower_ok = True
            upper_ok = True
            if "at_least" in bracket:
                lower_ok = amount_float >= float(bracket["at_least"])
            if "over" in bracket:
                lower_ok = amount_float > float(bracket["over"])
            if "not_over" in bracket:
                upper_ok = amount_float <= float(bracket["not_over"])
            if lower_ok and upper_ok:
                return amount_float * float(bracket.get("rate", 0)) - float(bracket.get("subtract", 0))
        return 0

    def _lookup_eic(self, lookup_amount: Any, qualifying_children_count: Any) -> Any:
        try:
            amount = int(float(lookup_amount))
        except (TypeError, ValueError):
            return 0
        try:
            qc_count = max(0, int(float(qualifying_children_count)))
        except (TypeError, ValueError):
            qc_count = 0
        if amount <= 0:
            return 0

        status_group = self._eic_status_group()
        if status_group is None:
            return 0
        qc_key = "3_or_more" if qc_count >= 3 else str(qc_count)
        eic_data = self.reference_data.get("earned_income_credit") or {}
        rows = ((((eic_data.get("datasets") or {}).get("eic_table")) or {}).get("rows")) or []
        for row in rows:
            if row.get("at_least", 0) <= amount < row.get("but_less_than", 0):
                return ((row.get(status_group) or {}).get(qc_key)) or 0
        return 0

    def _capital_gain_parameter(self, dataset_name: str, field_name: str) -> float:
        capital_gain_data = self.reference_data.get("capital_gain_parameters") or {}
        datasets = capital_gain_data.get("datasets") or {}
        dataset = datasets.get(dataset_name) or {}
        by_filing_status = dataset.get("by_filing_status") or {}
        filing_status_values = by_filing_status.get(self._filing_status_key()) or {}
        try:
            return float(filing_status_values.get(field_name) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _capital_loss_limit(self) -> float:
        return self._capital_gain_parameter(
            "schedule_d_tax_worksheet_thresholds",
            "capital_loss_limit",
        )

    def _capital_direct_schedule_d_total(self, schedule_line: str) -> Any:
        target_map = {
            "1a": {"1099_b": {"A"}, "1099_da": {"G"}},
            "8a": {"1099_b": {"D"}, "1099_da": {"J"}},
        }
        targets = target_map.get(schedule_line)
        if not targets:
            return 0

        f1040 = self._current_jurisdiction().get("f1040") or {}
        blocks = f1040.get("blocks") or {}
        total = 0.0

        for entry in ((blocks.get("1099_b") or {}).get("entries")) or []:
            if not isinstance(entry, dict):
                continue
            box = str(entry.get("applicable_8949_box", "")).strip().upper()
            if box not in targets["1099_b"]:
                continue
            if not bool(entry.get("basis_reported_to_irs")):
                continue
            try:
                adjustment_amount = float(entry.get("box_1g", 0) or 0)
                proceeds = float(entry.get("box_1d", 0) or 0)
                basis = float(entry.get("box_1e", 0) or 0)
            except (TypeError, ValueError):
                continue
            if adjustment_amount != 0:
                continue
            total += proceeds - basis

        for entry in ((blocks.get("1099_da") or {}).get("entries")) or []:
            if not isinstance(entry, dict):
                continue
            box = str(entry.get("applicable_8949_box", "")).strip().upper()
            if box not in targets["1099_da"]:
                continue
            if not bool(entry.get("basis_reported_to_irs")):
                continue
            try:
                adjustment_amount = float(entry.get("adjustment_amount", 0) or 0)
                proceeds = float(entry.get("proceeds", 0) or 0)
                basis = float(entry.get("basis", 0) or 0)
            except (TypeError, ValueError):
                continue
            if adjustment_amount != 0:
                continue
            total += proceeds - basis

        return total

    def save_as_dialog(self) -> None:
        if not self.data:
            QMessageBox.information(
                self,
                "Nothing to Save",
                "Start a new return or import an existing return first.",
            )
            return

        returns_dir = self._returns_dir()
        suggested_name = self.current_path.name if self.current_path else self.suggested_return_filename
        filename, ok = QInputDialog.getText(
            self,
            "Save Return As",
            f"Return filename in {returns_dir}:",
            text=suggested_name,
        )
        if not ok:
            return

        filename = filename.strip()
        if not filename:
            QMessageBox.information(self, "Save Cancelled", "Enter a filename to save the return.")
            return
        if not filename.endswith(".json"):
            filename = f"{filename}.json"

        out_path = returns_dir / filename
        if out_path.exists():
            answer = QMessageBox.question(
                self,
                "Overwrite Return?",
                f"{out_path.name} already exists in {returns_dir}.\nOverwrite it?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            payload = self._serialize_flat_return_data()
            out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except Exception as exc:  # pragma: no cover - UI message path
            QMessageBox.critical(self, "Save Failed", f"Could not save JSON:\n{exc}")
            return

        self.current_path = out_path
        self.suggested_return_filename = out_path.name
        self.path_label.setText(f"Working return: {out_path}")
        self.statusBar().showMessage(f"Saved {out_path.name}", 4000)

    def add_form(self) -> None:
        available = self._available_forms()
        candidate_items = [
            (_form_label(form_id, form_data), form_id)
            for form_id, form_data in available
            if self._form_sheet_id(form_id) not in self.visible_sheet_ids
        ]
        if not candidate_items:
            QMessageBox.information(self, "No More Sheets", "All included forms and worksheets are already visible.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Form")
        dialog.resize(700, 500)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select a form or worksheet to add:"))

        list_widget = QListWidget(dialog)
        for label, form_id in candidate_items:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, form_id)
            list_widget.addItem(item)
        list_widget.sortItems()
        if list_widget.count():
            list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        list_widget.itemDoubleClicked.connect(lambda _: dialog.accept())

        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = list_widget.currentItem()
            if item is None:
                return
            form_id = item.data(Qt.UserRole)
            sheet_ids = [self._form_sheet_id(dependency_id) for dependency_id in self._worksheet_dependencies(form_id)]
            sheet_ids.append(self._form_sheet_id(form_id))
            self._ensure_visible_sheets(sheet_ids, select_sheet_id=self._form_sheet_id(form_id))

    def add_info_return(self) -> None:
        candidate_items = self._block_candidates()
        if not candidate_items:
            QMessageBox.information(self, "No Info Returns", "No block-backed information returns are available.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Info Return")
        dialog.resize(700, 500)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select an information return to add:"))

        list_widget = QListWidget(dialog)
        for label, parent_form_id, block_id in candidate_items:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, (parent_form_id, block_id))
            list_widget.addItem(item)
        list_widget.sortItems()
        if list_widget.count():
            list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        list_widget.itemDoubleClicked.connect(lambda _: dialog.accept())

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        item = list_widget.currentItem()
        if item is None:
            return
        parent_form_id, block_id = item.data(Qt.UserRole)
        entry_number = self._append_blank_block_entry(parent_form_id, block_id)
        if entry_number is None:
            QMessageBox.warning(self, "Add Info Return Failed", "Could not create a new information return entry.")
            return
        self.recalculate_all()

        sheet_ids: list[str] = []
        if "f1040_Federal_Info_Worksheet" in self._current_jurisdiction():
            sheet_ids.append(self._form_sheet_id("f1040_Federal_Info_Worksheet"))
        sheet_ids.extend(self._form_sheet_id(form_id) for form_id in self._worksheet_dependencies(parent_form_id))
        sheet_ids.append(self._form_sheet_id(parent_form_id))
        target_sheet_id = self._block_sheet_id(parent_form_id, block_id)
        sheet_ids.append(target_sheet_id)
        self._ensure_visible_sheets(sheet_ids, select_sheet_id=target_sheet_id)
        self.statusBar().showMessage(f"Added {block_id} entry #{entry_number}", 4000)

    def remove_sheet(self) -> None:
        item = self.sheet_list.currentItem()
        if item is None:
            return
        sheet_id = item.data(Qt.UserRole)
        if sheet_id not in self.visible_sheet_ids:
            return
        self.visible_sheet_ids.remove(sheet_id)
        next_sheet_id = self.visible_sheet_ids[0] if self.visible_sheet_ids else None
        self._refresh_sheet_list(select_sheet_id=next_sheet_id)

    def _is_overridden(self, form_id: str, cell_id: str, cell: dict[str, Any]) -> bool:
        if not cell.get("equation") or not cell.get("override_possible", False):
            return False
        return (form_id, cell_id) in self.overridden_cells

    def _radio_group_members(self, form_id: str, cell_id: str) -> list[str]:
        form_data = self._current_jurisdiction().get(form_id) or {}
        cells = form_data.get("cells") or {}
        cell = cells.get(cell_id) or {}
        if not isinstance(cell, dict) or cell.get("format") != "boolean":
            return []

        for prefix in ONE_HOT_PREFIXES:
            if cell_id.startswith(prefix):
                members = [
                    candidate_id
                    for candidate_id, candidate_cell in cells.items()
                    if candidate_id.startswith(prefix)
                    and isinstance(candidate_cell, dict)
                    and candidate_cell.get("format") == "boolean"
                ]
                return sorted(members, key=lambda member_id: _cell_sort_key((member_id, cells.get(member_id))))

        if cell_id.endswith("_yes"):
            other_id = f"{cell_id[:-4]}_no"
        elif cell_id.endswith("_no"):
            other_id = f"{cell_id[:-3]}_yes"
        else:
            other_id = ""
        if other_id and isinstance(cells.get(other_id), dict) and (cells.get(other_id) or {}).get("format") == "boolean":
            members = [cell_id, other_id]
            return sorted(members, key=lambda member_id: _cell_sort_key((member_id, cells.get(member_id))))

        return []

    def _set_override_state(self, form_id: str, cell_id: str, parsed_value: Any) -> None:
        cell = self._get_form_cell(form_id, cell_id)
        if not isinstance(cell, dict):
            return
        if not (cell.get("equation") and cell.get("override_possible", False)):
            return
        formula_value = self._evaluate_cell(form_id, cell_id, set(), respect_overrides=False)
        if parsed_value == formula_value:
            self.overridden_cells.discard((form_id, cell_id))
        else:
            self.overridden_cells.add((form_id, cell_id))

    def _commit_cell_value(self, form_id: str, cell_id: str, parsed_value: Any, *, recalculate: bool = True) -> None:
        cell = self._get_form_cell(form_id, cell_id)
        if not isinstance(cell, dict):
            return
        self._set_override_state(form_id, cell_id, parsed_value)
        if cell.get("manual_entry", False) or cell.get("override_possible", False):
            self.touched_input_cells.add((form_id, cell_id))
        cell["value"] = parsed_value
        if recalculate:
            self.recalculate_all()

    def _clear_override_value(self, form_id: str, cell_id: str) -> None:
        cell = self._get_form_cell(form_id, cell_id)
        if not isinstance(cell, dict):
            return
        if not (cell.get("equation") and cell.get("override_possible", False)):
            return
        self.overridden_cells.discard((form_id, cell_id))
        self.touched_input_cells.discard((form_id, cell_id))
        formula_value = self._evaluate_cell(form_id, cell_id, set(), respect_overrides=False)
        if formula_value is None:
            formula_value = copy.deepcopy(cell.get("default"))
        cell["value"] = formula_value
        self.recalculate_all()

    def _on_boolean_widget_changed(self, form_id: str, cell_id: str, checked: bool) -> None:
        if self._populating_table:
            return
        radio_group = self._radio_group_members(form_id, cell_id)
        if radio_group:
            if not checked:
                return
            for member_id in radio_group:
                self._commit_cell_value(form_id, member_id, member_id == cell_id, recalculate=False)
            self.recalculate_all()
            return
        self._commit_cell_value(form_id, cell_id, checked)

    def _should_dim_choice_row(self, form_id: str, cell_id: str, cell: dict[str, Any]) -> bool:
        if cell.get("format") != "boolean":
            return False
        radio_group = self._radio_group_members(form_id, cell_id)
        if not radio_group:
            return False
        if bool(cell.get("value")):
            return False
        return any(
            bool((self._get_form_cell(form_id, member_id) or {}).get("value"))
            for member_id in radio_group
            if member_id != cell_id
        )

    def _is_required_now(self, form_id: str, cell_id: str, cell: dict[str, Any]) -> bool:
        required_rule = cell.get("required_rule", "optional")
        if required_rule in (None, "", "optional"):
            return False
        if required_rule == "always":
            return True
        if not isinstance(required_rule, str):
            return bool(required_rule)
        result = self._evaluate_equation(form_id, required_rule, set())
        if isinstance(result, bool):
            return result
        if result in (None, ""):
            return False
        if isinstance(result, (int, float)):
            return result != 0
        return bool(result)

    def _has_present_value(self, form_id: str, cell_id: str, cell: dict[str, Any]) -> bool:
        value = cell.get("value")
        format_code = cell.get("format", "text")
        key = (form_id, cell_id)

        if format_code in {"text", "date"}:
            return isinstance(value, str) and value.strip() != ""

        if format_code == "boolean":
            radio_group = self._radio_group_members(form_id, cell_id)
            if radio_group:
                return any(
                    bool((self._get_form_cell(form_id, member_id) or {}).get("value"))
                    for member_id in radio_group
                )
            if cell.get("manual_entry", False):
                return key in self.touched_input_cells or bool(value)
            return bool(value)

        if cell.get("manual_entry", False):
            return key in self.touched_input_cells or value != cell.get("default")

        return value not in (None, "")

    def _should_highlight_required_value(self, form_id: str, cell_id: str, cell: dict[str, Any]) -> bool:
        return self._is_required_now(form_id, cell_id, cell) and not self._has_present_value(form_id, cell_id, cell)

    def _format_validation_error(self, cell_id: str, cell: dict[str, Any]) -> str | None:
        value = cell.get("value")
        if value in (None, ""):
            return None
        if isinstance(value, str) and value.strip() == "":
            return None

        format_code = cell.get("format", "text")
        if format_code == "boolean":
            return None

        cell_id_lower = cell_id.lower()
        description = str(cell.get("description", "")).lower()
        explanation = str(cell.get("explanation", "")).lower()

        def is_person_name_field() -> bool:
            if any(part in cell_id_lower for part in PERSON_NAME_ID_PARTS):
                return True
            combined = f"{description} {explanation}"
            return any(part in combined for part in PERSON_NAME_LABEL_PARTS)

        # General rule: use explicit schema ids for narrow validators such as
        # middle-initial and suffix. Human-readable labels are often composite
        # ("first name and middle initial") and should not trigger a stricter
        # validator than the field actually represents.
        def is_suffix_field() -> bool:
            return "suffix" in cell_id_lower

        def is_middle_initial_field() -> bool:
            return "middle_initial" in cell_id_lower

        if "ssn" in cell_id_lower and "not_valid" not in cell_id_lower:
            if not isinstance(value, str) or not re.fullmatch(r"\d{3}-\d{2}-\d{4}", value.strip()):
                return "Use SSN format 123-45-6789."
            return None

        if "email" in cell_id_lower or "email" in description or "e-mail" in description:
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", value.strip()):
                return "Use a valid email address."
            return None

        if "phone_ext" in cell_id_lower or "phone ext" in description:
            if not isinstance(value, str) or not re.fullmatch(r"\d{1,10}", value.strip()):
                return "Use digits only for a phone extension."
            return None

        if ("phone" in cell_id_lower or "phone" in description) and format_code == "text":
            if not isinstance(value, str) or not re.fullmatch(r"[0-9()+.\- ]+", value.strip()):
                return "Use a phone number format such as 555-555-5555."
            digit_count = len(_digits_only(value))
            if digit_count < 7 or digit_count > 15:
                return "Use a phone number with 7 to 15 digits."
            return None

        if is_middle_initial_field():
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z]{1,3}", value.strip()):
                return "Use letters only for a middle initial."
            return None

        if is_suffix_field():
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9 .'\-]+", value.strip()):
                return "Use letters, numbers, spaces, periods, apostrophes, or hyphens for a suffix."
            return None

        if is_person_name_field():
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z '\-]*", value.strip()):
                return "Use letters, spaces, apostrophes, or hyphens for a name."
            return None

        return None

    def _current_visible_sheet_id(self) -> str | None:
        item = self.sheet_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _refresh_current_sheet(self) -> None:
        current_sheet_id = self._current_visible_sheet_id()
        if current_sheet_id:
            self.populate_sheet(current_sheet_id)

    def _get_form_cell(self, form_id: str, cell_id: str) -> dict[str, Any] | None:
        form_data = self._current_jurisdiction().get(form_id)
        if not isinstance(form_data, dict):
            return None
        cell = (form_data.get("cells") or {}).get(cell_id)
        if isinstance(cell, dict):
            return cell
        return None

    def _evaluate_equation(
        self,
        form_id: str,
        equation: str,
        stack: set[tuple[str, str]],
        *,
        respect_overrides: bool = True,
    ) -> Any:
        expr = equation.strip()
        if not expr:
            return None
        if "..." in expr:
            return None
        if " or " in expr:
            last_result = None
            for part in [piece.strip() for piece in expr.split(" or ")]:
                result = self._evaluate_equation(
                    form_id,
                    part,
                    set(stack),
                    respect_overrides=respect_overrides,
                )
                last_result = result
                if result:
                    return result
            return last_result

        expr = re.sub(
            r"sum\s*\(\s*(\w+)\.(\w+)\.\*\.(\w+)\s*\)",
            lambda m: f'__crossblocksum__("{m.group(1)}","{m.group(2)}","{m.group(3)}")',
            expr,
        )
        expr = re.sub(
            r"sum\s*\(\s*(\w+)\.\*\.(\w+)\s*\)",
            lambda m: f'__blocksum__("{m.group(1)}","{m.group(2)}")',
            expr,
        )
        expr = re.sub(
            r"\b(\w+)\.(\d+)\.(\w+)\b",
            lambda m: f'__blockitem__("{m.group(1)}",{m.group(2)},"{m.group(3)}")',
            expr,
        )
        expr = re.sub(
            r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z0-9_]+)\b",
            lambda m: f'__ref__("{m.group(1)}","{m.group(2)}")',
            expr,
        )

        form_cells = ((self._current_jurisdiction().get(form_id) or {}).get("cells") or {})
        valid_self_cell_ids = {
            cell_name
            for cell_name, cell in form_cells.items()
            if isinstance(cell, dict)
        }

        def replace_self_refs_outside_strings(source: str) -> str:
            parts = re.split(r'(\"[^\"]*\"|\'[^\']*\')', source)
            for idx, part in enumerate(parts):
                if idx % 2 == 1:
                    continue
                parts[idx] = re.sub(
                    r"(?<![A-Za-z0-9_\.\"'])(\d+[a-z]?)(?![A-Za-z0-9_\.\"'])",
                    lambda m: f'__self__("{m.group(1)}")' if m.group(1) in valid_self_cell_ids else m.group(1),
                    part,
                )
            return "".join(parts)

        expr = replace_self_refs_outside_strings(expr)

        identifier_names = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expr))
        reserved = {
            "age_on_date",
            "capital_gain_threshold",
            "capital_loss_limit",
            "__blocksum__",
            "__crossblocksum__",
            "__blockitem__",
            "__ref__",
            "__self__",
            "ceil",
            "crossblockcount_match",
            "crossblocksum_date_range",
            "capital_direct_schedule_d_total",
            "crossblocksum_match",
            "eic_lookup",
            "f2210_penalty",
            "floor",
            "max",
            "min",
            "max_zero",
            "standard_deduction_additional_amount",
            "standard_deduction_age_blind_count",
            "standard_deduction_amount",
            "standard_deduction_base_amount",
            "standard_deduction_dependent_amount",
            "standard_deduction_dependent_earned_income_amount",
            "tax_lookup",
            "True",
            "False",
        }
        local_context: dict[str, Any] = {}
        for name in identifier_names:
            if name in reserved:
                continue
            local_context[name] = self._evaluate_cell(
                form_id,
                name,
                set(stack),
                respect_overrides=respect_overrides,
            )

        def blocksum(block_id: str, field_name: str) -> Any:
            form_data = self._current_jurisdiction().get(form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id)
            if not isinstance(block, dict):
                return 0
            total = 0
            for entry in block.get("entries") or []:
                if isinstance(entry, dict):
                    value = entry.get(field_name, 0)
                    if isinstance(value, (int, float)):
                        total += value
            return total

        def crossblocksum(target_form_id: str, block_id: str, field_name: str) -> Any:
            form_data = self._current_jurisdiction().get(target_form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id)
            if not isinstance(block, dict):
                return 0
            total = 0
            for entry in block.get("entries") or []:
                if isinstance(entry, dict):
                    value = entry.get(field_name, 0)
                    if isinstance(value, (int, float)):
                        total += value
            return total

        def crossblocksum_match(
            target_form_id: str,
            block_id: str,
            field_name: str,
            *criteria: Any,
        ) -> Any:
            form_data = self._current_jurisdiction().get(target_form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id)
            if not isinstance(block, dict):
                return 0
            if len(criteria) % 2 != 0:
                return 0

            total = 0
            for entry in block.get("entries") or []:
                if not isinstance(entry, dict):
                    continue
                matched = True
                for idx in range(0, len(criteria), 2):
                    field = criteria[idx]
                    expected = criteria[idx + 1]
                    if entry.get(field) != expected:
                        matched = False
                        break
                if not matched:
                    continue
                value = entry.get(field_name, 0)
                if isinstance(value, (int, float)):
                    total += value
            return total

        def crossblockcount_match(
            target_form_id: str,
            block_id: str,
            *criteria: Any,
        ) -> Any:
            form_data = self._current_jurisdiction().get(target_form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id)
            if not isinstance(block, dict):
                return 0
            if len(criteria) % 2 != 0:
                return 0

            count = 0
            for entry in block.get("entries") or []:
                if not isinstance(entry, dict):
                    continue
                matched = True
                for idx in range(0, len(criteria), 2):
                    field = criteria[idx]
                    expected = criteria[idx + 1]
                    if entry.get(field) != expected:
                        matched = False
                        break
                if matched:
                    count += 1
            return count

        def crossblocksum_date_range(
            target_form_id: str,
            block_id: str,
            field_name: str,
            date_field: str,
            start_exclusive: str,
            end_inclusive: str,
        ) -> Any:
            form_data = self._current_jurisdiction().get(target_form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id)
            if not isinstance(block, dict):
                return 0

            total = 0
            for entry in block.get("entries") or []:
                if not isinstance(entry, dict):
                    continue
                date_value = entry.get(date_field)
                if not isinstance(date_value, str) or not date_value:
                    continue
                if start_exclusive and date_value <= start_exclusive:
                    continue
                if end_inclusive and date_value > end_inclusive:
                    continue
                value = entry.get(field_name, 0)
                if isinstance(value, (int, float)):
                    total += value
            return total

        def blockitem(block_id: str, index: int, field_name: str) -> Any:
            form_data = self._current_jurisdiction().get(form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id)
            if not isinstance(block, dict):
                return None
            entries = block.get("entries") or []
            if 0 <= index < len(entries) and isinstance(entries[index], dict):
                return entries[index].get(field_name)
            return None

        def ref(target_form_id: str, target_cell_id: str) -> Any:
            return self._evaluate_cell(
                target_form_id,
                target_cell_id,
                set(stack),
                respect_overrides=respect_overrides,
            )

        def self_ref(target_cell_id: str) -> Any:
            return self._evaluate_cell(
                form_id,
                target_cell_id,
                set(stack),
                respect_overrides=respect_overrides,
            )

        def tax_lookup(amount: Any) -> Any:
            return self._lookup_tax(amount)

        def eic_lookup(amount: Any, qualifying_children_count: Any) -> Any:
            return self._lookup_eic(amount, qualifying_children_count)

        def capital_gain_threshold(dataset_name: str, field_name: str) -> Any:
            return self._capital_gain_parameter(dataset_name, field_name)

        def capital_loss_limit() -> Any:
            return self._capital_loss_limit()

        def parse_date(value: Any) -> dt.date | None:
            if isinstance(value, dt.date):
                return value
            if not isinstance(value, str):
                return None
            text = value.strip()
            if not text:
                return None
            try:
                return dt.date.fromisoformat(text)
            except ValueError:
                pass
            match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
            if not match:
                return None
            try:
                return dt.date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
            except ValueError:
                return None

        def age_on_date(birth_value: Any, as_of_value: Any) -> Any:
            birth_date = parse_date(birth_value)
            as_of_date = parse_date(as_of_value)
            if birth_date is None or as_of_date is None:
                return 0
            years = as_of_date.year - birth_date.year
            if (as_of_date.month, as_of_date.day) < (birth_date.month, birth_date.day):
                years -= 1
            return max(0, years)

        def capital_direct_schedule_d_total(schedule_line: str) -> Any:
            return self._capital_direct_schedule_d_total(schedule_line)

        def f2210_penalty() -> Any:
            if form_id != "f2210":
                return 0

            def cell_amount(cell_name: str) -> float:
                value = self._evaluate_cell("f2210", cell_name, set(stack))
                try:
                    return float(value or 0)
                except (TypeError, ValueError):
                    return 0.0

            if bool(self._evaluate_cell("f2210", "safe_harbor_exception_met", set(stack))):
                return 0.0

            if bool(
                self._evaluate_cell(
                    "f1040_Federal_Info_Worksheet",
                    "defer_automated_form_2210_line_19",
                    set(stack),
                )
            ):
                return 0.0
            if bool(self._evaluate_cell("f2210", "A", set(stack))) or bool(
                self._evaluate_cell("f2210", "B", set(stack))
            ):
                return 0.0

            first_due = dt.date(2025, 4, 15)
            installments = [
                (first_due, cell_amount("17a")),
                (dt.date(2025, 6, 15), cell_amount("17b")),
                (dt.date(2025, 9, 15), cell_amount("17c")),
                (dt.date(2026, 1, 15), cell_amount("17d")),
            ]

            payments: list[tuple[dt.date, float]] = []
            f1040 = self._current_jurisdiction().get("f1040") or {}
            payment_block = (f1040.get("blocks") or {}).get("estimated_tax_payments_detail") or {}
            for entry in payment_block.get("entries") or []:
                if not isinstance(entry, dict):
                    continue
                payment_date = parse_date(entry.get("payment_date"))
                if payment_date is None:
                    continue
                try:
                    amount = float(entry.get("amount") or 0)
                except (TypeError, ValueError):
                    continue
                if amount > 0:
                    payments.append((payment_date, amount))

            annual_rate = 0.07
            end_date = dt.date(2026, 4, 15)
            unpaid: list[list[Any]] = []
            penalty = 0.0
            current_date = first_due

            if installments[0][1] > 0:
                unpaid.append([installments[0][0], installments[0][1]])

            def apply_payment_pool(pool: float) -> None:
                nonlocal unpaid
                remaining = pool
                for item in unpaid:
                    if remaining <= 0:
                        break
                    applied = min(item[1], remaining)
                    item[1] -= applied
                    remaining -= applied
                unpaid = [item for item in unpaid if item[1] > 0.0000001]

            early_estimated = sum(
                amt for pay_d, amt in payments if pay_d <= first_due
            )
            wh_a = cell_amount("withholding_payment_period_a")
            apply_payment_pool(early_estimated + wh_a)

            events: list[tuple[dt.date, int, str, float]] = []
            for payment_date, amount in payments:
                if payment_date > first_due and payment_date <= end_date:
                    events.append((payment_date, 0, "payment", amount))
            wh_schedule = [
                (dt.date(2025, 6, 15), cell_amount("withholding_payment_period_b")),
                (dt.date(2025, 9, 15), cell_amount("withholding_payment_period_c")),
                (dt.date(2026, 1, 15), cell_amount("withholding_payment_period_d")),
            ]
            for wh_date, wh_amt in wh_schedule:
                if wh_amt > 0 and wh_date <= end_date:
                    events.append((wh_date, 1, "withholding", wh_amt))
            for due_date, amount in installments[1:]:
                if due_date <= end_date:
                    events.append((due_date, 2, "installment", amount))
            events.sort()

            for event_date, _, event_type, amount in events:
                days = (event_date - current_date).days
                if days > 0:
                    penalty += sum(balance for _, balance in unpaid) * days * annual_rate / 365.0
                    current_date = event_date

                if event_type in ("payment", "withholding"):
                    remaining = amount
                    for item in unpaid:
                        if remaining <= 0:
                            break
                        applied = min(item[1], remaining)
                        item[1] -= applied
                        remaining -= applied
                    unpaid = [item for item in unpaid if item[1] > 0.0000001]
                elif amount > 0:
                    unpaid.append([event_date, amount])

            days = (end_date - current_date).days
            if days > 0:
                penalty += sum(balance for _, balance in unpaid) * days * annual_rate / 365.0

            return round(penalty, 2)

        def _cell_number(target_form_id: str, target_cell_id: str) -> float:
            value = self._evaluate_cell(
                target_form_id,
                target_cell_id,
                set(stack),
                respect_overrides=respect_overrides,
            )
            try:
                return float(value or 0)
            except (TypeError, ValueError):
                return 0.0

        def _cell_bool(target_form_id: str, target_cell_id: str) -> bool:
            return bool(
                self._evaluate_cell(
                    target_form_id,
                    target_cell_id,
                    set(stack),
                    respect_overrides=respect_overrides,
                )
            )

        def max_zero(value: Any) -> Any:
            try:
                return max(0.0, float(value or 0))
            except (TypeError, ValueError):
                return 0.0

        def standard_deduction_base_amount() -> float:
            if _cell_bool("f1040", "filing_status_married_jointly") or _cell_bool("f1040", "filing_status_qss"):
                return 31500.0
            if _cell_bool("f1040", "filing_status_hoh"):
                return 23625.0
            if _cell_bool("f1040", "filing_status_single") or _cell_bool("f1040", "filing_status_married_separately"):
                return 15750.0
            return 15750.0

        def standard_deduction_age_blind_count() -> int:
            count = 0
            if _cell_number("f1040_Federal_Info_Worksheet", "taxpayer_age_1_1_2026") >= 65:
                count += 1
            if _cell_bool("f1040_Federal_Info_Worksheet", "taxpayer_legally_blind"):
                count += 1
            if _cell_bool("f1040", "filing_status_married_jointly"):
                if _cell_number("f1040_Federal_Info_Worksheet", "spouse_age_1_1_2026") >= 65:
                    count += 1
                if _cell_bool("f1040_Federal_Info_Worksheet", "spouse_legally_blind"):
                    count += 1
            return count

        def standard_deduction_additional_amount() -> float:
            count = standard_deduction_age_blind_count()
            if count <= 0:
                return 0.0
            if _cell_bool("f1040", "filing_status_single") or _cell_bool("f1040", "filing_status_hoh"):
                return count * 2000.0
            return count * 1600.0

        def standard_deduction_dependent_earned_income_amount() -> float:
            return max(1350.0, _cell_number("f1040", "1z") + 450.0)

        def standard_deduction_dependent_amount() -> float:
            return min(
                standard_deduction_dependent_earned_income_amount(),
                standard_deduction_base_amount(),
            ) + standard_deduction_additional_amount()

        def standard_deduction_amount() -> float:
            if _cell_bool("f1040_Federal_Info_Worksheet", "taxpayer_claimed_on_other_return") or _cell_bool(
                "f1040_Federal_Info_Worksheet",
                "spouse_claimed_on_other_return",
            ):
                return standard_deduction_dependent_amount()
            return standard_deduction_base_amount() + standard_deduction_additional_amount()

        eval_globals = {
            "__builtins__": {},
            "__blocksum__": blocksum,
            "__crossblocksum__": crossblocksum,
            "__blockitem__": blockitem,
            "__ref__": ref,
            "__self__": self_ref,
            "age_on_date": age_on_date,
            "capital_gain_threshold": capital_gain_threshold,
            "capital_loss_limit": capital_loss_limit,
            "ceil": math.ceil,
            "capital_direct_schedule_d_total": capital_direct_schedule_d_total,
            "crossblockcount_match": crossblockcount_match,
            "crossblocksum_date_range": crossblocksum_date_range,
            "crossblocksum_match": crossblocksum_match,
            "eic_lookup": eic_lookup,
            "f2210_penalty": f2210_penalty,
            "floor": math.floor,
            "max_zero": max_zero,
            "min": min,
            "max": max,
            "standard_deduction_additional_amount": standard_deduction_additional_amount,
            "standard_deduction_age_blind_count": standard_deduction_age_blind_count,
            "standard_deduction_amount": standard_deduction_amount,
            "standard_deduction_base_amount": standard_deduction_base_amount,
            "standard_deduction_dependent_amount": standard_deduction_dependent_amount,
            "standard_deduction_dependent_earned_income_amount": standard_deduction_dependent_earned_income_amount,
            "tax_lookup": tax_lookup,
            "True": True,
            "False": False,
        }
        eval_globals.update(local_context)
        try:
            return eval(expr, eval_globals, {})
        except Exception:
            return None

    def _evaluate_cell(
        self,
        form_id: str,
        cell_id: str,
        stack: set[tuple[str, str]] | None = None,
        *,
        respect_overrides: bool = True,
    ) -> Any:
        if stack is None:
            stack = set()
        key = (form_id, cell_id)
        if key in stack:
            return None
        cache_key = (form_id, cell_id, respect_overrides)
        if cache_key in self._evaluation_cache:
            return self._evaluation_cache[cache_key]
        cell = self._get_form_cell(form_id, cell_id)
        if cell is None:
            return None
        if respect_overrides and cell.get("override_possible", False) and key in self.overridden_cells:
            result = cell.get("value", cell.get("default"))
            self._evaluation_cache[cache_key] = result
            return result
        if cell.get("manual_entry", False) and not cell.get("equation"):
            result = cell.get("value", cell.get("default"))
            self._evaluation_cache[cache_key] = result
            return result

        equation = cell.get("equation")
        if not equation:
            result = cell.get("value", cell.get("default"))
            self._evaluation_cache[cache_key] = result
            return result

        stack.add(key)
        try:
            result = self._evaluate_equation(
                form_id,
                equation,
                stack,
                respect_overrides=respect_overrides,
            )
        finally:
            stack.discard(key)
        if result is None:
            result = cell.get("default")
        self._evaluation_cache[cache_key] = result
        return result

    def recalculate_all(self, *, detect_existing_overrides: bool = False) -> None:
        if not self.jurisdiction_key:
            return
        self._evaluation_cache.clear()
        jdata = self._current_jurisdiction()
        for form_id, form_data in sorted(self._available_forms(), key=_form_sort_key):
            cells = form_data.get("cells") or {}
            for cell_id, cell in sorted(cells.items(), key=_cell_sort_key):
                if not isinstance(cell, dict) or not cell.get("equation"):
                    continue
                computed = self._evaluate_cell(form_id, cell_id, set())
                if detect_existing_overrides and cell.get("override_possible", False):
                    current_value = cell.get("value")
                    formula_result = self._evaluate_cell(
                        form_id,
                        cell_id,
                        set(),
                        respect_overrides=False,
                    )
                    if current_value not in (None, "", cell.get("default")) and current_value != formula_result:
                        self.overridden_cells.add((form_id, cell_id))
                if cell.get("override_possible", False) and (form_id, cell_id) in self.overridden_cells:
                    continue
                cell["value"] = computed
        self._sync_visible_sheets_from_usage()
        self._refresh_current_sheet()

    def _on_sheet_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        del previous
        if current is None:
            self.table.setRowCount(0)
            return
        sheet_id = current.data(Qt.UserRole)
        self.populate_sheet(sheet_id)

    def populate_sheet(self, sheet_id: str) -> None:
        sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
        if sheet_type == "block" and secondary_id:
            self.populate_block_sheet(primary_id, secondary_id)
        else:
            self.populate_form(primary_id)
        self._update_pdf_preview()

    def populate_form(self, form_id: str) -> None:
        jdata = self._current_jurisdiction()
        form_data = jdata.get(form_id) or {}
        cells = form_data.get("cells") or {}

        self._populating_table = True
        try:
            ordered_cells = sorted(cells.items(), key=_cell_sort_key)
            self.table.clearContents()
            self.table.setRowCount(len(ordered_cells))
            for row_idx, (cell_id, cell) in enumerate(ordered_cells):
                description = cell.get("description") or cell.get("explanation") or ""
                value_text = _display_cell_value(cell)
                format_code = cell.get("format", "text")
                equation = cell.get("equation", "")
                is_editable = bool(cell.get("manual_entry", False) or cell.get("override_possible", False))
                uses_boolean_widget = format_code == "boolean" and is_editable
                row_dimmed = self._should_dim_choice_row(form_id, cell_id, cell)
                value_required_highlight = self._should_highlight_required_value(form_id, cell_id, cell)
                validation_error = self._format_validation_error(cell_id, cell)
                displayed_value = value_text
                if format_code == "boolean" and not uses_boolean_widget:
                    displayed_value = "✓" if bool(cell.get("value")) else ""

                values = [
                    cell_id,
                    description,
                    "" if uses_boolean_widget else displayed_value,
                    format_code,
                    equation,
                    "yes" if cell.get("override_possible", False) else "no",
                    str(cell.get("required_rule", "optional")),
                ]
                for col_idx, text in enumerate(values):
                    item = QTableWidgetItem(str(text))
                    flags = Qt.ItemIsEnabled
                    if col_idx == VALUE_COLUMN_INDEX:
                        flags |= Qt.ItemIsSelectable
                    if col_idx == VALUE_COLUMN_INDEX and is_editable and not uses_boolean_widget:
                        flags |= Qt.ItemIsEditable
                    item.setFlags(flags)
                    if col_idx == VALUE_COLUMN_INDEX and value_required_highlight:
                        item.setBackground(REQUIRED_BACKGROUND)
                    elif row_dimmed:
                        item.setBackground(DIMMED_ROW_BACKGROUND)
                        item.setForeground(DIMMED_ROW_TEXT)
                    elif col_idx != VALUE_COLUMN_INDEX or not is_editable:
                        item.setBackground(READONLY_BACKGROUND)
                    if col_idx in FAINT_METADATA_COLUMN_INDICES and not row_dimmed:
                        item.setForeground(FAINT_METADATA_TEXT)
                    if col_idx == VALUE_COLUMN_INDEX and self._is_overridden(form_id, cell_id, cell):
                        item.setForeground(OVERRIDE_TEXT)
                    if col_idx == VALUE_COLUMN_INDEX and validation_error:
                        item.setForeground(INVALID_TEXT)
                        item.setToolTip(validation_error)
                    if col_idx == 0:
                        item.setData(Qt.UserRole, (form_id, cell_id))
                    self.table.setItem(row_idx, col_idx, item)

                if uses_boolean_widget:
                    widget_container = QWidget()
                    widget_layout = QHBoxLayout()
                    widget_layout.setContentsMargins(6, 0, 6, 0)
                    widget_layout.setAlignment(Qt.AlignCenter)

                    radio_group = self._radio_group_members(form_id, cell_id)
                    if radio_group:
                        control = QRadioButton()
                    else:
                        control = QCheckBox()
                    control.setChecked(bool(cell.get("value")))
                    control.setEnabled(is_editable)
                    if value_required_highlight:
                        widget_container.setStyleSheet(
                            f"background-color: {REQUIRED_BACKGROUND.name()};"
                        )
                    elif row_dimmed:
                        widget_container.setStyleSheet(
                            f"background-color: {DIMMED_ROW_BACKGROUND.name()}; color: {DIMMED_ROW_TEXT.name()};"
                        )
                    if is_editable:
                        control.toggled.connect(
                            lambda checked, current_form_id=form_id, current_cell_id=cell_id: self._on_boolean_widget_changed(
                                current_form_id,
                                current_cell_id,
                                checked,
                            )
                        )
                    widget_container.setFocusPolicy(Qt.StrongFocus)
                    widget_layout.addWidget(control)
                    widget_container.setLayout(widget_layout)
                    self.table.setCellWidget(row_idx, VALUE_COLUMN_INDEX, widget_container)
            self._focus_value_column()
        finally:
            self._populating_table = False

    def populate_block_sheet(self, parent_form_id: str, block_id: str) -> None:
        jdata = self._current_jurisdiction()
        form_data = jdata.get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id) or {}
        item_cells = block.get("item_cells") or {}
        entries = block.get("entries") or []
        # Block-backed information returns should follow the authored JSON order
        # unless/until they grow explicit `order` metadata. Alphabetic sorting
        # breaks natural tax-box sequences such as box_1, box_2, ..., box_10.
        ordered_fields = list(item_cells.items())

        rows: list[tuple[int, str, dict[str, Any], dict[str, Any]]] = []
        for entry_index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            for field_id, field in ordered_fields:
                if isinstance(field, dict):
                    rows.append((entry_index, field_id, field, entry))

        self._populating_table = True
        try:
            self.table.clearContents()
            self.table.setRowCount(len(rows))
            for row_idx, (entry_index, field_id, field, entry) in enumerate(rows):
                description = field.get("description") or field.get("explanation") or ""
                raw_value = entry.get(field_id, self._blank_block_field_value(field))
                working_cell = copy.deepcopy(field)
                working_cell["value"] = raw_value
                is_repeating = field.get("type") == "repeating"
                format_code = "repeating" if is_repeating else field.get("format", "text")
                if is_repeating:
                    displayed_value = f"{len(raw_value)} item(s)" if isinstance(raw_value, list) else ""
                else:
                    displayed_value = _display_cell_value(working_cell)
                is_editable = not is_repeating
                uses_boolean_widget = format_code == "boolean" and is_editable
                uses_taxpayer_spouse_widget = self._uses_taxpayer_spouse_widget(field_id, field, raw_value)
                value_required_highlight = self._is_required_now(parent_form_id, field_id, working_cell) and not self._block_has_present_value(raw_value, field)
                validation_error = self._format_validation_error(field_id, working_cell)

                values = [
                    f"{entry_index + 1}.{field_id}",
                    f"[{entry_index + 1}] {description}",
                    "" if (uses_boolean_widget or uses_taxpayer_spouse_widget) else displayed_value,
                    format_code,
                    "",
                    "no",
                    str(field.get("required_rule", "optional")),
                ]
                for col_idx, text in enumerate(values):
                    item = QTableWidgetItem(str(text))
                    flags = Qt.ItemIsEnabled
                    if col_idx == VALUE_COLUMN_INDEX:
                        flags |= Qt.ItemIsSelectable
                    if col_idx == VALUE_COLUMN_INDEX and is_editable and not uses_boolean_widget and not uses_taxpayer_spouse_widget:
                        flags |= Qt.ItemIsEditable
                    item.setFlags(flags)
                    if col_idx == VALUE_COLUMN_INDEX and value_required_highlight:
                        item.setBackground(REQUIRED_BACKGROUND)
                    elif col_idx != VALUE_COLUMN_INDEX or not is_editable:
                        item.setBackground(READONLY_BACKGROUND)
                    if col_idx in FAINT_METADATA_COLUMN_INDICES:
                        item.setForeground(FAINT_METADATA_TEXT)
                    if col_idx == VALUE_COLUMN_INDEX and validation_error:
                        item.setForeground(INVALID_TEXT)
                        item.setToolTip(validation_error)
                    if col_idx == 0:
                        item.setData(Qt.UserRole, ("block", parent_form_id, block_id, entry_index, field_id))
                    self.table.setItem(row_idx, col_idx, item)

                if uses_boolean_widget or uses_taxpayer_spouse_widget:
                    widget_container = QWidget()
                    widget_layout = QHBoxLayout()
                    widget_layout.setContentsMargins(6, 0, 6, 0)
                    widget_layout.setAlignment(Qt.AlignCenter)
                    widget_container.setFocusPolicy(Qt.StrongFocus)
                    if value_required_highlight:
                        widget_container.setStyleSheet(
                            f"background-color: {REQUIRED_BACKGROUND.name()};"
                        )
                    if uses_taxpayer_spouse_widget:
                        current_recipient = self._normalize_taxpayer_spouse_value(raw_value)
                        taxpayer_button = QRadioButton("T")
                        spouse_button = QRadioButton("S")
                        taxpayer_button.setChecked(current_recipient == "taxpayer")
                        spouse_button.setChecked(current_recipient == "spouse")
                        taxpayer_button.toggled.connect(
                            lambda checked, current_form_id=parent_form_id, current_block_id=block_id, current_entry_index=entry_index, current_field_id=field_id: self._on_block_taxpayer_spouse_widget_changed(
                                current_form_id,
                                current_block_id,
                                current_entry_index,
                                current_field_id,
                                "taxpayer",
                                checked,
                            )
                        )
                        spouse_button.toggled.connect(
                            lambda checked, current_form_id=parent_form_id, current_block_id=block_id, current_entry_index=entry_index, current_field_id=field_id: self._on_block_taxpayer_spouse_widget_changed(
                                current_form_id,
                                current_block_id,
                                current_entry_index,
                                current_field_id,
                                "spouse",
                                checked,
                            )
                        )
                        widget_layout.addWidget(taxpayer_button)
                        widget_layout.addWidget(spouse_button)
                    else:
                        control = QCheckBox()
                        control.setChecked(bool(raw_value))
                        control.toggled.connect(
                            lambda checked, current_form_id=parent_form_id, current_block_id=block_id, current_entry_index=entry_index, current_field_id=field_id: self._on_block_boolean_widget_changed(
                                current_form_id,
                                current_block_id,
                                current_entry_index,
                                current_field_id,
                                checked,
                            )
                        )
                        widget_layout.addWidget(control)
                    widget_container.setLayout(widget_layout)
                    self.table.setCellWidget(row_idx, VALUE_COLUMN_INDEX, widget_container)
            self._focus_value_column()
        finally:
            self._populating_table = False

    def _focus_value_column(self, preferred_row: int | None = None) -> None:
        if self.table.rowCount() <= 0:
            return
        if preferred_row is None or not (0 <= preferred_row < self.table.rowCount()):
            current_row = self.table.currentRow()
            preferred_row = current_row if 0 <= current_row < self.table.rowCount() else 0
        self.table.setCurrentCell(preferred_row, VALUE_COLUMN_INDEX)

    def _on_current_cell_changed(
        self,
        current_row: int,
        current_column: int,
        previous_row: int,
        previous_column: int,
    ) -> None:
        del previous_column
        if self._populating_table or current_row < 0:
            return
        current_sheet_id = self._current_visible_sheet_id()
        if current_sheet_id is not None:
            sheet_type, _, secondary_id = self._parse_sheet_id(current_sheet_id)
            if sheet_type == "block" and secondary_id and current_row != previous_row:
                self._update_pdf_preview()
        if current_column == VALUE_COLUMN_INDEX:
            return
        fallback_row = current_row
        if fallback_row < 0 <= previous_row < self.table.rowCount():
            fallback_row = previous_row
        if 0 <= fallback_row < self.table.rowCount():
            self._focus_value_column(fallback_row)

    def _block_has_present_value(self, value: Any, field: dict[str, Any]) -> bool:
        if field.get("type") == "repeating":
            return isinstance(value, list) and len(value) > 0
        format_code = field.get("format", "text")
        if format_code in {"text", "date"}:
            return isinstance(value, str) and value.strip() != ""
        if format_code == "boolean":
            return bool(value)
        return value not in (None, "", field.get("default"))

    def _uses_taxpayer_spouse_widget(self, field_id: str, field: dict[str, Any], value: Any) -> bool:
        if field_id != "recipient":
            return False
        allowed_values = {"taxpayer", "spouse"}
        default_value = field.get("default")
        if isinstance(default_value, str) and default_value.strip().lower() in allowed_values:
            return True
        if isinstance(value, str) and value.strip().lower() in allowed_values:
            return True
        combined = f"{field.get('description', '')} {field.get('explanation', '')}".lower()
        return "taxpayer" in combined and "spouse" in combined

    def _normalize_taxpayer_spouse_value(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        return "spouse" if text == "spouse" else "taxpayer"

    def _commit_block_value(
        self,
        parent_form_id: str,
        block_id: str,
        entry_index: int,
        field_id: str,
        parsed_value: Any,
    ) -> None:
        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id) or {}
        entries = block.get("entries") or []
        if not (0 <= entry_index < len(entries)):
            return
        entry = entries[entry_index]
        if not isinstance(entry, dict):
            return
        entry[field_id] = parsed_value
        self.recalculate_all()

    def _on_block_boolean_widget_changed(
        self,
        parent_form_id: str,
        block_id: str,
        entry_index: int,
        field_id: str,
        checked: bool,
    ) -> None:
        if self._populating_table:
            return
        self._commit_block_value(parent_form_id, block_id, entry_index, field_id, checked)

    def _on_block_taxpayer_spouse_widget_changed(
        self,
        parent_form_id: str,
        block_id: str,
        entry_index: int,
        field_id: str,
        selected_value: str,
        checked: bool,
    ) -> None:
        if self._populating_table or not checked:
            return
        self._commit_block_value(
            parent_form_id,
            block_id,
            entry_index,
            field_id,
            self._normalize_taxpayer_spouse_value(selected_value),
        )

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._populating_table or item.column() != VALUE_COLUMN_INDEX:
            return

        form_item = self.table.item(item.row(), 0)
        if form_item is None:
            return
        cell_ref = form_item.data(Qt.UserRole)
        if not cell_ref:
            return
        if cell_ref[0] == "block":
            _, parent_form_id, block_id, entry_index, field_id = cell_ref
            form_data = self._current_jurisdiction().get(parent_form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id) or {}
            entries = block.get("entries") or []
            item_cells = block.get("item_cells") or {}
            if not (0 <= entry_index < len(entries)):
                return
            field = item_cells.get(field_id)
            if not isinstance(field, dict):
                return
            try:
                parsed = _parse_value(item.text(), field.get("format", "text"), field.get("default"))
            except ValueError as exc:
                self._populating_table = True
                try:
                    current_value = entries[entry_index].get(field_id, self._blank_block_field_value(field))
                    temp_cell = copy.deepcopy(field)
                    temp_cell["value"] = current_value
                    item.setText(_display_cell_value(temp_cell))
                finally:
                    self._populating_table = False
                QMessageBox.warning(self, "Invalid Value", str(exc))
                return
            self._commit_block_value(parent_form_id, block_id, entry_index, field_id, parsed)
            return
        _, form_id, cell_id = ("form", *cell_ref) if len(cell_ref) == 2 else cell_ref
        jdata = self._current_jurisdiction()
        form_data = jdata.get(form_id) or {}
        cell = (form_data.get("cells") or {}).get(cell_id)
        if not isinstance(cell, dict):
            return

        if cell.get("equation") and cell.get("override_possible", False) and item.text().strip() == "":
            self._clear_override_value(form_id, cell_id)
            return

        try:
            parsed = _parse_value(item.text(), cell.get("format", "text"), cell.get("default"))
        except ValueError as exc:
            self._populating_table = True
            try:
                item.setText(_display_cell_value(cell))
            finally:
                self._populating_table = False
            QMessageBox.warning(self, "Invalid Value", str(exc))
            return

        self._commit_cell_value(form_id, cell_id, parsed)


def main(json_filename: str | Path | None = None) -> int:
    app = QApplication([])
    path = Path(json_filename) if json_filename else None
    window = TaxSheetEditor(path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenTax Qt editor for the tax JSON model.")
    parser.add_argument("-f", "--file", dest="filename", default=None, help="Path to tax JSON file")
    args = parser.parse_args()
    raise SystemExit(main(args.filename))
