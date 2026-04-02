#!/usr/bin/env python3
'''
Qt desktop editor for the OpenTax master JSON.

This module owns the main application window, the live tax-calculation
engine used by the editor, and the PDF preview wiring that maps JSON cells
to rendered tax forms and information returns.
'''

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
import re
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    QPlainTextEdit,
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
    from pypdf import PdfReader, PdfWriter
except Exception:  # pragma: no cover - runtime dependency availability varies
    PdfReader = None
    PdfWriter = None

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
REQUIRED_BACKGROUND = QColor("#fee2e2")
FILED_FORM_BACKGROUND = QColor("#dcfce7")
FAINT_METADATA_TEXT = QColor("#6b7280")
INVALID_TEXT = QColor("#ff0000")
INCOMPLETE_SHEET_TEXT = QColor("#b91c1c")
SOURCE_SHEET_FLASH_BACKGROUND = QColor("#fde047")
TRI_STATE_BOOLEAN_FORMAT = "tri_state_boolean"
RETURN_TEMPLATE_FILENAME = "federal_1040_2025.json"
MASTER_QUESTIONNAIRE_FORM_TRIGGERS: dict[str, tuple[str, ...]] = {
    "has_foreign_income": ("f2555", "f1116_Questionnaire"),
    "paid_foreign_taxes": ("f1116_Questionnaire",),
    "prior_year_foreign_tax_carryovers": ("f1116_Questionnaire",),
    "may_itemize_deductions": ("f1040sa", "f1040sa_Questionnaire"),
    "received_marketplace_coverage": ("f8962",),
    "paid_child_or_dependent_care": ("f2441",),
    "received_dependent_care_benefits": ("f2441",),
    "sold_capital_assets": ("f1040sd", "f8949"),
    "has_self_employment_income_or_expenses": ("f1040sc",),
    "has_rental_royalty_or_passthrough_income": ("f1040se",),
    "has_medical_or_dental_expenses": ("f1040sa", "f1040sa_Questionnaire", "f1040sa_Medical_Expense_Qualification_Worksheet"),
    "has_noncash_charitable_contributions": ("f1040sa", "f1040sa_Questionnaire", "f8283"),
    "has_casualty_or_theft_losses": ("f1040sa", "f1040sa_Questionnaire", "f4684"),
    "has_investment_interest_expense": ("f1040sa", "f1040sa_Questionnaire", "f4952"),
    "has_education_expenses": ("f8863",),
    "has_hsa_activity": ("f8889",),
}
F8949_SHORT_TERM_BLOCK_IDS = ("st_box_a", "st_box_b", "st_box_c", "st_box_g", "st_box_h", "st_box_i")
F8949_LONG_TERM_BLOCK_IDS = ("lt_box_d", "lt_box_e", "lt_box_f", "lt_box_j", "lt_box_k", "lt_box_l")
SCHEDULE_A_QUESTIONNAIRE_FORM_TRIGGERS: dict[str, tuple[str, ...]] = {
    "itemizing_likely": ("f1040sa",),
    "has_state_and_local_tax_deduction": ("f1040sa",),
    "has_home_mortgage_interest": ("f1040sa",),
    "has_cash_charitable_contributions": ("f1040sa",),
    "has_medical_or_dental_expenses": ("f1040sa", "f1040sa_Medical_Expense_Qualification_Worksheet"),
    "has_noncash_charitable_contributions": ("f1040sa", "f8283"),
    "has_casualty_or_theft_losses": ("f1040sa", "f4684"),
    "has_investment_interest_expense": ("f1040sa", "f4952"),
}
F1116_CATEGORY_QUESTION_MAP: dict[str, str] = {
    "category_passive": "has_passive_category_income",
    "category_general": "has_general_category_income",
    "category_section_951A": "has_section_951a_category_income",
    "category_foreign_branch": "has_foreign_branch_category_income",
    "category_section_901j": "has_section_901j_income",
    "category_resourced_by_treaty": "has_resourced_by_treaty_income",
    "category_lump_sum": "has_lump_sum_distribution_income",
}
F1116_CATEGORY_DEFINITIONS: tuple[dict[str, str], ...] = (
    {
        "suffix": "passive",
        "label": "Passive Category",
        "question_cell": "has_passive_category_income",
        "category_cell": "category_passive",
    },
    {
        "suffix": "general",
        "label": "General Category",
        "question_cell": "has_general_category_income",
        "category_cell": "category_general",
    },
    {
        "suffix": "section_951a",
        "label": "Section 951A Category",
        "question_cell": "has_section_951a_category_income",
        "category_cell": "category_section_951A",
    },
    {
        "suffix": "foreign_branch",
        "label": "Foreign Branch Category",
        "question_cell": "has_foreign_branch_category_income",
        "category_cell": "category_foreign_branch",
    },
    {
        "suffix": "section_901j",
        "label": "Section 901(j) Category",
        "question_cell": "has_section_901j_income",
        "category_cell": "category_section_901j",
    },
    {
        "suffix": "resourced_by_treaty",
        "label": "Resourced by Treaty Category",
        "question_cell": "has_resourced_by_treaty_income",
        "category_cell": "category_resourced_by_treaty",
    },
    {
        "suffix": "lump_sum",
        "label": "Lump-Sum Distribution Category",
        "question_cell": "has_lump_sum_distribution_income",
        "category_cell": "category_lump_sum",
    },
)
F1116_COPY_BASE_IDS: dict[str, str] = {
    "f1116": "f1116",
    "f1116sb": "f1116sb",
    "f1116sc": "f1116sc",
}
F8949_ROWS_PER_COPY = 11
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
LOCAL_BLOCK_WILDCARD_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.\*\.[A-Za-z0-9_]+\b")
LOCAL_BLOCK_INDEX_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.\d+\.[A-Za-z0-9_]+\b")
FORM_BLOCK_FUNCTION_PATTERN = re.compile(
    r'\b(?:block_has_entries|crossblocksum_match|crossblockcount_match|crossblocksum_date_range)\("([^"]+)"\s*,\s*"([^"]+)"'
)


def _jurisdictions(data: dict[str, Any]) -> list[str]:
    '''Return the top-level jurisdiction objects from a loaded JSON bundle.'''
    return [key for key, value in data.items() if key not in RESERVED_KEYS and isinstance(value, dict)]


def _form_sort_key(item: tuple[str, Any]) -> tuple[float, str]:
    '''Sort forms by authored rank, then by ID as a stable fallback.'''
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
    '''Sort cells by explicit order metadata when present.'''
    cell_id, cell = item
    if isinstance(cell, dict):
        try:
            return (int(cell.get("order")), str(cell_id))
        except (TypeError, ValueError):
            pass
    return (float("inf"), str(cell_id))


def _form_label(form_id: str, form_data: dict[str, Any]) -> str:
    '''Build the user-facing sheet label for a form.'''
    meta = form_data.get("_meta") or {}
    title = meta.get("name") or form_id
    return f"{title} ({form_id})"


def _compact_form_title(form_id: str, form_data: dict[str, Any]) -> str:
    '''Build a concise navigator label for a form or worksheet.'''
    meta = form_data.get("_meta") or {}
    short_name = str(meta.get("short_name") or "").strip()
    if short_name:
        return short_name

    title = str(meta.get("name") or form_id).strip()
    if form_id == "f1040_Federal_Info_Worksheet":
        return "Federal Info"
    if title == "Master Questionnaire Worksheet":
        return "Master Questionnaire"
    if title == "Schedule A Questionnaire Worksheet":
        return "Sch A Questionnaire"
    if title == "Foreign Tax Credit Questionnaire Worksheet":
        return "FTC Questionnaire"
    if form_id.startswith("f1116sb"):
        return "1116 Sch B"
    if form_id.startswith("f1116sc"):
        return "1116 Sch C"
    if form_id.startswith("f1116"):
        return "1116"

    form_match = re.match(r"Form\s+([0-9A-Za-z]+)\b", title)
    if form_match:
        return form_match.group(1)

    schedule_match = re.match(r"Schedule\s+([A-Za-z0-9]+)\b", title)
    if schedule_match:
        return f"Sch {schedule_match.group(1)}"

    compact = title.split(" - ", 1)[0].strip()
    compact = compact.replace("Worksheet", "Wksht")
    return compact


def _display_cell_value(cell: dict[str, Any]) -> str:
    '''Format a raw JSON cell value for display in the table.'''
    value = cell.get("value")
    format_code = str(cell.get("format", "text"))
    if value is None:
        return ""
    if format_code == TRI_STATE_BOOLEAN_FORMAT:
        return "yes" if value is True else "no" if value is False else ""
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
    '''Parse edited table text back into the JSON cell type.'''
    text = raw_text.strip()
    if format_code == TRI_STATE_BOOLEAN_FORMAT:
        if text == "":
            return None
        lowered = text.lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
        if lowered in {"null", "none", "unknown", "unanswered", "?"}:
            return None
        raise ValueError("Use yes/no for tri-state fields, or leave blank for unanswered.")
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
    '''Strip a string down to digits for SSN and EIN style fields.'''
    return "".join(ch for ch in value if ch.isdigit())


class TaxSheetEditor(QMainWindow):
    '''Main application window for browsing, editing, and previewing a return.'''

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
        self._flashing_source_sheet_ids: set[str] = set()
        self._preview_highlight_sources: set[str] = set()
        self._pdf_render_context: dict[str, Any] | None = None
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
        self.table.setColumnHidden(CELL_ID_COLUMN_INDEX, True)
        self.table.setColumnHidden(FORMAT_COLUMN_INDEX, True)
        self.table.setColumnHidden(EQUATION_COLUMN_INDEX, True)
        self.table.setColumnHidden(OVERRIDE_ALLOWED_COLUMN_INDEX, True)
        self.table.setColumnHidden(REQUIRED_RULE_COLUMN_INDEX, True)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.viewport().installEventFilter(self)

        self.value_cell_info_popup = QPlainTextEdit(self)
        self.value_cell_info_popup.setReadOnly(True)
        self.value_cell_info_popup.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.value_cell_info_popup.setWindowFlags(Qt.ToolTip)
        self.value_cell_info_popup.setStyleSheet(
            "QPlainTextEdit {"
            "background-color: #fffef7;"
            "border: 1px solid #9ca3af;"
            "padding: 6px;"
            "font-family: monospace;"
            "font-size: 12px;"
            "}"
        )
        self.value_cell_info_popup.hide()

        self.path_label = QLabel("No return loaded. Choose New Return or Import Return.")
        self.path_label.setWordWrap(True)

        new_return_button = QPushButton("New Return")
        new_return_button.clicked.connect(self.new_return)

        load_button = QPushButton("Import Return")
        load_button.clicked.connect(self.load_json_dialog)

        save_as_button = QPushButton("Save Return As")
        save_as_button.clicked.connect(self.save_as_dialog)

        print_button = QPushButton("Print / Export PDF")
        print_button.clicked.connect(self.print_export_dialog)

        add_form_button = QPushButton("Add Form")
        add_form_button.clicked.connect(self.add_form)

        add_info_return_button = QPushButton("Add Info Return")
        add_info_return_button.clicked.connect(self.add_info_return)

        remove_info_return_button = QPushButton("Remove Info Return")
        remove_info_return_button.clicked.connect(self.remove_info_return)

        remove_sheet_button = QPushButton("Remove Sheet")
        remove_sheet_button.clicked.connect(self.remove_sheet)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Visible Sheets"))
        left_layout.addWidget(self.sheet_list, stretch=1)
        left_layout.addWidget(add_form_button)
        left_layout.addWidget(add_info_return_button)
        left_layout.addWidget(remove_info_return_button)
        left_layout.addWidget(remove_sheet_button)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.path_label)

        button_row = QHBoxLayout()
        button_row.addWidget(new_return_button)
        button_row.addWidget(load_button)
        button_row.addWidget(save_as_button)
        button_row.addWidget(print_button)
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
        root_splitter.setStretchFactor(1, 3)
        root_splitter.setStretchFactor(2, 4)

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
        '''Load the master template and identify its sole jurisdiction payload.'''
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
        '''Show a friendly message when no previewable PDF is available.'''
        self.pdf_placeholder_label.setText(message)
        self.pdf_stack.setCurrentIndex(0)

    def _forms_pdf_dir(self) -> Path:
        return self._project_root() / "forms-instructions-and-publications" / "forms"

    def _info_return_pdf_dir(self) -> Path:
        return self._project_root() / "forms-instructions-and-publications" / "information-returns"

    def _generated_info_return_pdf_dir(self) -> Path:
        return self._project_root() / "forms-instructions-and-publications" / "generated-information-returns"

    def _current_preview_sheet(self) -> tuple[str, str, str | None] | None:
        sheet_id = self._current_visible_sheet_id()
        if not sheet_id:
            return None
        return self._parse_sheet_id(sheet_id)

    def _block_preview_mapping_id(self, parent_form_id: str, block_id: str) -> str:
        '''Convert a block sheet into the synthetic preview mapping ID it uses.'''
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
            return self._mapped_family_preview_form_id(primary_id)
        if sheet_type == "block" and secondary_id:
            if primary_id == "f8949" and secondary_id in (*F8949_SHORT_TERM_BLOCK_IDS, *F8949_LONG_TERM_BLOCK_IDS):
                return "f8949"
            return self._block_preview_mapping_id(primary_id, secondary_id)
        return None

    def _mapped_preview_source_path(self, form_id: str) -> Path | None:
        if self.pdf_preview_engine is None:
            return None
        return self.pdf_preview_engine.source_pdf_for_form(form_id)

    def _form_pdf_source_path_from_meta(self, form_id: str) -> Path | None:
        form_data = self._current_jurisdiction().get(form_id) or {}
        meta = form_data.get("_meta") or {}
        source_path = meta.get("pdf_source_path")
        if not isinstance(source_path, str):
            return None
        normalized = source_path.strip()
        if not normalized:
            return None
        candidate = self._project_root() / normalized
        return candidate if candidate.is_file() else None

    def _form_is_fillable_form(self, form_id: str) -> bool:
        form_data = self._current_jurisdiction().get(form_id) or {}
        meta = form_data.get("_meta") or {}
        return bool(meta.get("fillable_form"))

    def _local_form_pdf_path(self, form_id: str) -> Path | None:
        candidate = self._forms_pdf_dir() / f"{form_id}.pdf"
        return candidate if candidate.is_file() else None

    def _form_preview_source_path(self, form_id: str) -> Path | None:
        metadata_source = self._form_pdf_source_path_from_meta(form_id)
        if metadata_source is not None:
            return metadata_source
        mapped_source = self._mapped_preview_source_path(form_id)
        if mapped_source and mapped_source.is_file():
            return mapped_source
        return self._local_form_pdf_path(form_id)

    def _block_pdf_source_path_from_meta(self, block: dict[str, Any]) -> Path | None:
        source_path = block.get("pdf_source_path")
        if not isinstance(source_path, str):
            return None
        normalized = source_path.strip()
        if not normalized:
            return None
        candidate = self._project_root() / normalized
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
        metadata_source = self._block_pdf_source_path_from_meta(block)
        if metadata_source is not None:
            return metadata_source
        search_dirs = (self._generated_info_return_pdf_dir(), self._forms_pdf_dir())
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
            return self._form_preview_source_path(primary_id)
        if sheet_type == "block" and secondary_id:
            if primary_id == "f8949" and secondary_id in (*F8949_SHORT_TERM_BLOCK_IDS, *F8949_LONG_TERM_BLOCK_IDS):
                return self._form_preview_source_path("f8949")
            return self._block_preview_source_path(primary_id, secondary_id)
        return None

    def _resolve_pdf_mapping_source(self, form_id: str, source: str) -> Any:
        '''Resolve a PDF mapping source expression to the current live value.'''
        block_mapping = self._parse_block_preview_mapping_id(form_id)
        if block_mapping is not None:
            parent_form_id, block_id = block_mapping
            return self._resolve_block_preview_source(parent_form_id, block_id, source)
        expr = source.strip()
        if not expr:
            return None
        return self._evaluate_equation(form_id, expr, set())

    def _render_preview_with_context(
        self,
        *,
        preview_form_id: str,
        value_form_id: str,
        highlight_sources: set[str] | None = None,
        render_context: dict[str, Any] | None = None,
    ) -> Path:
        '''Render a filled PDF preview while temporarily applying copy-specific context.'''
        if self.pdf_preview_engine is None:
            raise RuntimeError("PDF preview engine is unavailable.")
        previous_context = self._pdf_render_context
        self._pdf_render_context = render_context
        try:
            return self.pdf_preview_engine.render_preview(
                form_id=preview_form_id,
                resolve_source=lambda source: self._resolve_pdf_mapping_source(value_form_id, source),
                highlight_sources=highlight_sources,
            )
        finally:
            self._pdf_render_context = previous_context

    def _load_pdf_into_view(self, pdf_path: Path, status_message: str) -> None:
        if self.pdf_document is None or self.pdf_view is None:
            self._show_pdf_placeholder(status_message)
            return
        self.pdf_status_label.setText(status_message)
        self.pdf_document.load(str(pdf_path))
        self.pdf_stack.setCurrentIndex(1)

    def _update_pdf_preview(self) -> None:
        '''Rebuild the right-hand PDF preview for the currently selected sheet.'''
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
        value_form_id = primary_id if sheet_type == "form" else preview_form_id
        raw_pdf = self._raw_preview_source_path(sheet_type, primary_id, secondary_id)

        if preview_form_id is None or self.pdf_preview_engine is None:
            if raw_pdf and raw_pdf.is_file():
                self._load_pdf_into_view(raw_pdf, f"Raw {sheet_label} preview")
            else:
                self._show_pdf_placeholder(f"No local PDF is available yet for {sheet_label}.")
            return

        if not self.pdf_preview_engine.has_render_mappings_for_form(preview_form_id):
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
            preview_path = self._render_preview_with_context(
                preview_form_id=preview_form_id,
                value_form_id=value_form_id or preview_form_id,
                highlight_sources=self._preview_highlight_sources,
                render_context=self._f8949_preview_render_context(sheet_type, primary_id, secondary_id)
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
        '''Load lookup tables used by equations such as tax and credit lookups.'''
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

    def _block_short_label(self, parent_form_id: str, block_id: str, block: dict[str, Any]) -> str:
        short_name = str(block.get("short_name") or "").strip()
        if short_name:
            return short_name
        description = str(block.get("description") or block_id).strip()
        for prefix in ("Form(s) ", "Form ", "Schedule(s) ", "Schedule "):
            if description.startswith(prefix):
                description = description[len(prefix) :].strip()
                break
        description = description.replace("Worksheet", "Wksht")
        if description and description != block_id:
            return description
        if block_id.lower() == "w2":
            return "W-2"
        if re.fullmatch(r"\d{4}_[a-z0-9]+", block_id.lower()):
            number, suffix = block_id.split("_", 1)
            return f"{number}-{suffix.upper()}"
        return block_id.replace("_", " ").title()

    def _form_category_suffix(self, form_id: str) -> str:
        category_definition = self._f1116_category_definition_for_form(form_id)
        if category_definition is None:
            return ""
        label = str(category_definition.get("label") or "").strip()
        label = label.replace(" Category", "").replace(" category", "")
        return f" ({label.lower()})" if label else ""

    def _form_copy_count_for_navigator(self, form_id: str) -> int:
        if form_id == "f8949":
            return len(self._f8949_copy_specs())
        return 1

    def _sheet_navigator_label(self, sheet_id: str) -> str:
        sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
        jdata = self._current_jurisdiction()
        if sheet_type == "block" and secondary_id:
            form_data = jdata.get(primary_id) or {}
            block = (form_data.get("blocks") or {}).get(secondary_id) or {}
            label = self._block_short_label(primary_id, secondary_id, block)
            entry_count = len([entry for entry in (block.get("entries") or []) if isinstance(entry, dict)])
            return f"{label} x{entry_count}" if entry_count > 1 else label
        form_data = jdata.get(primary_id) or {}
        if not isinstance(form_data, dict):
            return primary_id
        label = _compact_form_title(primary_id, form_data)
        copy_count = self._form_copy_count_for_navigator(primary_id)
        category_suffix = self._form_category_suffix(primary_id)
        if copy_count > 1:
            return f"{label}{category_suffix} x{copy_count}"
        return f"{label}{category_suffix}"

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

    def _sheet_missing_required_count(self, sheet_id: str) -> int:
        sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
        jdata = self._current_jurisdiction()
        if sheet_type == "form":
            form_data = jdata.get(primary_id) or {}
            cells = form_data.get("cells") or {}
            return sum(
                1
                for cell_id, cell in cells.items()
                if isinstance(cell, dict) and self._should_highlight_required_value(primary_id, cell_id, cell)
            )
        if sheet_type == "block" and secondary_id:
            form_data = jdata.get(primary_id) or {}
            block = (form_data.get("blocks") or {}).get(secondary_id) or {}
            item_cells = block.get("item_cells") or {}
            entries = block.get("entries") or []
            missing = 0
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                for field_id, field in item_cells.items():
                    if not isinstance(field, dict):
                        continue
                    value = entry.get(field_id, self._blank_block_field_value(field))
                    working_cell = copy.deepcopy(field)
                    working_cell["value"] = value
                    if self._is_required_now(primary_id, field_id, working_cell) and not self._block_has_present_value(value, field):
                        missing += 1
            return missing
        return 0

    def _apply_sheet_list_item_foreground(self, item: QListWidgetItem, sheet_id: str) -> None:
        missing_required_count = self._sheet_missing_required_count(sheet_id)
        if missing_required_count > 0:
            item.setData(Qt.ForegroundRole, INCOMPLETE_SHEET_TEXT)
            item.setToolTip(f"{self._sheet_label(sheet_id)}\nIncomplete: {missing_required_count} required field(s) missing.")
            return
        item.setData(Qt.ForegroundRole, None)
        item.setToolTip(f"{self._sheet_label(sheet_id)}\nComplete.")

    def _metadata_popup_section(self, title: str, body: Any) -> str:
        if isinstance(body, str):
            content = body
        else:
            content = json.dumps(body, indent=2, sort_keys=True)
        return f"{title}\n{'=' * len(title)}\n{content}".rstrip()

    def _metadata_popup_summary_lines(self, pairs: list[tuple[str, Any]]) -> str:
        lines = []
        for label, value in pairs:
            rendered = "" if value is None else str(value)
            lines.append(f"{label}: {rendered}")
        return "\n".join(lines).rstrip()

    def _metadata_popup_text(self, cell_ref: Any) -> str:
        '''Render the temporary right-click metadata popup for a cell or block field.'''
        if not cell_ref:
            return ""
        jdata = self._current_jurisdiction()
        if isinstance(cell_ref, tuple) and len(cell_ref) >= 5 and cell_ref[0] == "block":
            _, parent_form_id, block_id, entry_index, field_id = cell_ref
            form_data = jdata.get(parent_form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id) or {}
            entries = block.get("entries") or []
            entry = entries[entry_index] if isinstance(entry_index, int) and 0 <= entry_index < len(entries) else {}
            field = (block.get("item_cells") or {}).get(field_id) or {}
            entry_value = entry.get(field_id) if isinstance(entry, dict) else None
            summary = self._metadata_popup_summary_lines(
                [
                    ("Sheet Type", "Block Field"),
                    ("Parent Form", parent_form_id),
                    ("Block", block_id),
                    ("Entry", (entry_index + 1) if isinstance(entry_index, int) else entry_index),
                    ("Field", field_id),
                    ("Description", field.get("description") or ""),
                    ("Format", field.get("format", field.get("type", "text"))),
                    ("Current Value", entry_value),
                    ("Required Rule", field.get("required_rule", "optional")),
                ]
            )
            sections = [
                self._metadata_popup_section("Summary", summary),
                self._metadata_popup_section(
                    "Field Schema",
                    field,
                ),
                self._metadata_popup_section(
                    "Current Entry Value",
                    {"value": entry_value},
                ),
            ]
            return "\n\n".join(section for section in sections if section)
        if isinstance(cell_ref, tuple) and len(cell_ref) == 2:
            form_id, cell_id = cell_ref
        elif isinstance(cell_ref, tuple) and len(cell_ref) >= 3 and cell_ref[0] == "form":
            _, form_id, cell_id = cell_ref[:3]
        else:
            return ""

        form_data = jdata.get(form_id) or {}
        cell = (form_data.get("cells") or {}).get(cell_id) or {}
        summary = self._metadata_popup_summary_lines(
            [
                ("Sheet Type", "Form Cell"),
                ("Form", form_id),
                ("Cell", cell_id),
                ("Description", cell.get("description") or ""),
                ("Format", cell.get("format", "text")),
                ("Current Value", cell.get("value")),
                ("Manual Entry", cell.get("manual_entry", False)),
                ("Override Allowed", cell.get("override_possible", False)),
                ("Required Rule", cell.get("required_rule", "optional")),
                ("Equation", cell.get("equation", "")),
            ]
        )
        sections = [
            self._metadata_popup_section("Summary", summary),
            self._metadata_popup_section("Cell Schema", cell),
        ]
        return "\n\n".join(section for section in sections if section)

    def _popup_cell_ref_from_object(self, obj: Any) -> Any:
        current = obj
        while current is not None:
            if hasattr(current, "property"):
                cell_ref = current.property("cell_ref")
                if cell_ref:
                    return cell_ref
            current = current.parent() if hasattr(current, "parent") else None
        return None

    def _show_value_cell_info_popup(self, cell_ref: Any, global_pos: Any) -> None:
        popup_text = self._metadata_popup_text(cell_ref)
        if not popup_text:
            self._hide_value_cell_info_popup()
            return
        flashing_sheet_ids = self._source_sheet_ids_for_cell_ref(cell_ref)
        current_sheet_id = self._current_visible_sheet_id()
        if current_sheet_id is not None:
            flashing_sheet_ids.discard(current_sheet_id)
        self._set_flashing_source_sheet_ids(flashing_sheet_ids)
        self.value_cell_info_popup.setPlainText(popup_text)
        font_metrics = QFontMetrics(self.value_cell_info_popup.font())
        lines = popup_text.splitlines() or [""]
        widest_line = max(font_metrics.horizontalAdvance(line) for line in lines)
        line_height = font_metrics.lineSpacing()
        width = min(760, max(320, widest_line + 36))
        height = min(520, max(180, line_height * min(len(lines) + 2, 28) + 28))
        self.value_cell_info_popup.resize(width, height)
        if global_pos is not None:
            self.value_cell_info_popup.move(global_pos.x() + 16, global_pos.y() + 16)
        self.value_cell_info_popup.show()

    def _hide_value_cell_info_popup(self) -> None:
        self.value_cell_info_popup.hide()
        self._set_flashing_source_sheet_ids(set())

    def eventFilter(self, obj: Any, event: Any) -> bool:
        '''Handle press-and-hold metadata popups for value cells and widgets.'''
        if obj is self.table.viewport():
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.RightButton:
                index = self.table.indexAt(event.position().toPoint())
                if index.isValid() and index.column() == VALUE_COLUMN_INDEX:
                    form_item = self.table.item(index.row(), CELL_ID_COLUMN_INDEX)
                    cell_ref = form_item.data(Qt.UserRole) if form_item is not None else None
                    if cell_ref:
                        self._show_value_cell_info_popup(cell_ref, event.globalPosition().toPoint())
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.RightButton:
                self._hide_value_cell_info_popup()
        else:
            cell_ref = self._popup_cell_ref_from_object(obj)
            if cell_ref:
                if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.RightButton:
                    if hasattr(event, "globalPosition"):
                        self._show_value_cell_info_popup(cell_ref, event.globalPosition().toPoint())
                elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.RightButton:
                    self._hide_value_cell_info_popup()
        return super().eventFilter(obj, event)

    def _form_rank_value(self, form_id: str) -> float:
        form_data = self._current_jurisdiction().get(form_id) or {}
        meta = form_data.get("_meta") or {}
        try:
            return float(meta.get("rank"))
        except (TypeError, ValueError):
            return float("inf")

    def _display_order_value(self, form_id: str) -> float:
        form_data = self._current_jurisdiction().get(form_id) or {}
        meta = form_data.get("_meta") or {}
        try:
            return float(meta.get("display_order"))
        except (TypeError, ValueError):
            return float("inf")

    def _schedule_b_row_amount(self, entry: dict[str, Any], amount_fields: tuple[str, ...]) -> float:
        amount = 0.0
        for field_name in amount_fields:
            try:
                amount += float(entry.get(field_name) or 0.0)
            except (TypeError, ValueError):
                continue
        return amount

    def _schedule_b_source_rows(
        self,
        block_specs: list[tuple[str, tuple[str, ...]]],
        *,
        fallback_prefix: str,
    ) -> list[tuple[str, float]]:
        '''Build Schedule B payer rows from the underlying information-return blocks.'''
        form_data = self._current_jurisdiction().get("f1040") or {}
        blocks = form_data.get("blocks") or {}
        rows: list[tuple[str, float]] = []
        for block_id, amount_fields in block_specs:
            block = blocks.get(block_id) or {}
            entries = block.get("entries") or []
            for entry_index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                amount = self._schedule_b_row_amount(entry, amount_fields)
                if abs(amount) < 0.0000001:
                    continue
                payer_name = str(entry.get("payer_name") or "").strip()
                if not payer_name:
                    payer_name = f"{fallback_prefix} {entry_index + 1}"
                rows.append((payer_name, round(amount, 2)))
        return rows

    def _schedule_b_interest_rows(self) -> list[tuple[str, float]]:
        return self._schedule_b_source_rows(
            [
                ("1099_int", ("box_1", "box_3")),
                ("1099_oid", ("box_1", "box_3")),
                ("k1_1041", ("interest_income",)),
                ("k1_1065", ("interest_income",)),
                ("k1_1120s", ("interest_income",)),
                ("k3_1065", ("interest_income",)),
                ("k3_1120s", ("interest_income",)),
            ],
            fallback_prefix="Interest payer",
        )

    def _schedule_b_dividend_rows(self) -> list[tuple[str, float]]:
        return self._schedule_b_source_rows(
            [
                ("1099_div", ("box_1a",)),
                ("k1_1041", ("ordinary_dividends",)),
                ("k1_1065", ("ordinary_dividends",)),
                ("k1_1120s", ("ordinary_dividends",)),
                ("k3_1065", ("ordinary_dividends",)),
                ("k3_1120s", ("ordinary_dividends",)),
            ],
            fallback_prefix="Dividend payer",
        )

    def _schedule_b_row_name(self, row_kind: str, index: int) -> str:
        if index <= 0:
            return ""
        rows = self._schedule_b_interest_rows() if row_kind == "interest" else self._schedule_b_dividend_rows()
        if index > len(rows):
            return ""
        return rows[index - 1][0]

    def _schedule_b_row_value(self, row_kind: str, index: int) -> float:
        if index <= 0:
            return 0.0
        rows = self._schedule_b_interest_rows() if row_kind == "interest" else self._schedule_b_dividend_rows()
        if index > len(rows):
            return 0.0
        return rows[index - 1][1]

    def _schedule_b_row_display_value(self, row_kind: str, index: int) -> Any:
        if index <= 0:
            return ""
        rows = self._schedule_b_interest_rows() if row_kind == "interest" else self._schedule_b_dividend_rows()
        if index > len(rows):
            return ""
        return rows[index - 1][1]

    def _schedule_b_total(self, row_kind: str) -> float:
        rows = self._schedule_b_interest_rows() if row_kind == "interest" else self._schedule_b_dividend_rows()
        return round(sum(amount for _, amount in rows), 2)

    def _apply_sheet_list_item_background(self, item: QListWidgetItem, sheet_id: str) -> None:
        if sheet_id in self._flashing_source_sheet_ids:
            item.setData(Qt.BackgroundRole, SOURCE_SHEET_FLASH_BACKGROUND)
            return
        sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
        del secondary_id
        filed_form_ids = set(self._filed_form_ids())
        if sheet_type == "form" and primary_id in filed_form_ids:
            item.setData(Qt.BackgroundRole, FILED_FORM_BACKGROUND)
            return
        item.setData(Qt.BackgroundRole, None)

    def _set_flashing_source_sheet_ids(self, sheet_ids: set[str]) -> None:
        normalized_sheet_ids = {sheet_id for sheet_id in sheet_ids if sheet_id in self.visible_sheet_ids}
        if normalized_sheet_ids == self._flashing_source_sheet_ids:
            return
        self._flashing_source_sheet_ids = normalized_sheet_ids
        for idx in range(self.sheet_list.count()):
            item = self.sheet_list.item(idx)
            if item is None:
                continue
            sheet_id = item.data(Qt.UserRole)
            if isinstance(sheet_id, str):
                self._apply_sheet_list_item_background(item, sheet_id)

    def _set_preview_highlight_sources(self, sources: set[str], *, refresh_preview: bool = True) -> None:
        normalized_sources = {source for source in sources if isinstance(source, str) and source.strip()}
        if normalized_sources == self._preview_highlight_sources:
            return
        self._preview_highlight_sources = normalized_sources
        if refresh_preview:
            self._update_pdf_preview()

    def _sheet_ids_referenced_by_equation(self, form_id: str, equation: str) -> set[str]:
        '''Infer which visible sheets feed an equation so the UI can point to them.'''
        if not equation:
            return set()
        referenced_sheet_ids: set[str] = set()
        current_form_data = self._current_jurisdiction().get(form_id) or {}
        current_blocks = current_form_data.get("blocks") or {}
        for ref_form_id, ref_name in FORM_REF_PATTERN.findall(equation):
            target_form_data = self._current_jurisdiction().get(ref_form_id) or {}
            target_blocks = target_form_data.get("blocks") or {}
            target_cells = target_form_data.get("cells") or {}
            if ref_name in target_blocks:
                referenced_sheet_ids.add(self._block_sheet_id(ref_form_id, ref_name))
            elif ref_name in target_cells:
                referenced_sheet_ids.add(self._form_sheet_id(ref_form_id))
        for block_id in LOCAL_BLOCK_WILDCARD_PATTERN.findall(equation):
            if block_id in current_blocks:
                referenced_sheet_ids.add(self._block_sheet_id(form_id, block_id))
        for block_id in LOCAL_BLOCK_INDEX_PATTERN.findall(equation):
            if block_id in current_blocks:
                referenced_sheet_ids.add(self._block_sheet_id(form_id, block_id))
        for target_form_id, block_id in FORM_BLOCK_FUNCTION_PATTERN.findall(equation):
            target_form_data = self._current_jurisdiction().get(target_form_id) or {}
            target_blocks = target_form_data.get("blocks") or {}
            if block_id in target_blocks:
                referenced_sheet_ids.add(self._block_sheet_id(target_form_id, block_id))
        return referenced_sheet_ids

    def _special_source_sheet_ids_for_form_cell(self, form_id: str, cell_id: str) -> set[str]:
        if form_id == "f1040sb":
            if re.fullmatch(r"line_1_(payer|amount)_\d+", cell_id) or cell_id == "1":
                return {
                    self._block_sheet_id("f1040", block_id)
                    for block_id in ("1099_int", "1099_oid", "k1_1041", "k1_1065", "k1_1120s", "k3_1065", "k3_1120s")
                }
            if re.fullmatch(r"line_4_(payer|amount)_\d+", cell_id) or cell_id == "4":
                return {
                    self._block_sheet_id("f1040", block_id)
                    for block_id in ("1099_div", "k1_1041", "k1_1065", "k1_1120s", "k3_1065", "k3_1120s")
                }
        if form_id == "f1040se" and re.fullmatch(r"passthrough_\d+_(name|category|income_or_loss|nonpassive|qbi_income_or_loss)", cell_id):
            return {
                self._block_sheet_id("f1040", block_id)
                for block_id in ("k1_1041", "k1_1065", "k1_1120s", "k3_1065", "k3_1120s")
            }
        if form_id == "f8283" and re.fullmatch(
            r"section_a_item_\d+_(description|donee_name|contribution_date|claimed_amount|section_b_candidate)",
            cell_id,
        ):
            return {self._block_sheet_id("f1040", "1098_c")}
        if form_id == "f8962" and (
            cell_id.startswith("1095_a_")
            or cell_id.startswith("allocation_")
            or cell_id in {
                "has_marketplace_policy_allocations",
                "has_policy_allocation_or_alternative_calc",
                "annual_enrollment_premiums",
                "annual_slcsp",
                "annual_advance_ptc",
            }
            or re.fullmatch(r"month_\d{2}_(enrollment_premiums|slcsp|advance_ptc)", cell_id)
        ):
            return {self._block_sheet_id("f1040", "1095_a")}
        return set()

    def _source_sheet_ids_for_cell_ref(self, cell_ref: Any) -> set[str]:
        '''Return the upstream sheet IDs that should flash during right-click help.'''
        if not cell_ref:
            return set()
        if isinstance(cell_ref, tuple) and len(cell_ref) >= 5 and cell_ref[0] == "block":
            return set()
        if isinstance(cell_ref, tuple) and len(cell_ref) == 2:
            form_id, cell_id = cell_ref
        elif isinstance(cell_ref, tuple) and len(cell_ref) >= 3 and cell_ref[0] == "form":
            _, form_id, cell_id = cell_ref[:3]
        else:
            return set()
        cell = self._get_form_cell(form_id, cell_id)
        if not isinstance(cell, dict):
            return set()
        source_sheet_ids = self._special_source_sheet_ids_for_form_cell(form_id, cell_id)
        equation = str(cell.get("equation") or "").strip()
        if equation:
            source_sheet_ids.update(self._sheet_ids_referenced_by_equation(form_id, equation))
        return source_sheet_ids

    def _preview_mapping_sources_for_cell_ref(self, cell_ref: Any) -> set[str]:
        '''Map the selected table cell to the PDF mapping source keys it renders into.'''
        if not cell_ref:
            return set()
        if isinstance(cell_ref, tuple) and len(cell_ref) >= 5 and cell_ref[0] == "block":
            _, parent_form_id, block_id, entry_index, field_id = cell_ref
            if (
                parent_form_id == "f8949"
                and isinstance(entry_index, int)
                and block_id in (*F8949_SHORT_TERM_BLOCK_IDS, *F8949_LONG_TERM_BLOCK_IDS)
            ):
                section = "short" if block_id in F8949_SHORT_TERM_BLOCK_IDS else "long"
                return {f'f8949_preview_row_value("{section}", {entry_index + 1}, "{field_id}")'}
            return {f"entry.{cell_ref[4]}"}
        if isinstance(cell_ref, tuple) and len(cell_ref) == 2:
            return {str(cell_ref[1])}
        if isinstance(cell_ref, tuple) and len(cell_ref) >= 3 and cell_ref[0] == "form":
            return {str(cell_ref[2])}
        return set()

    def _current_selected_cell_ref(self) -> Any:
        current_row = self.table.currentRow()
        if not (0 <= current_row < self.table.rowCount()):
            return None
        value_item = self.table.item(current_row, VALUE_COLUMN_INDEX)
        if value_item is not None:
            cell_ref = value_item.data(Qt.UserRole)
            if cell_ref:
                return cell_ref
        current_widget = self.table.cellWidget(current_row, VALUE_COLUMN_INDEX)
        return self._popup_cell_ref_from_object(current_widget)

    def _sync_preview_highlight_to_selection(self) -> None:
        '''Keep the PDF highlight aligned with the currently selected table value cell.'''
        self._set_preview_highlight_sources(
            self._preview_mapping_sources_for_cell_ref(self._current_selected_cell_ref()),
            refresh_preview=False,
        )

    def _f1040_block_entries(self, block_id: str) -> list[dict[str, Any]]:
        form_data = self._current_jurisdiction().get("f1040") or {}
        block = (form_data.get("blocks") or {}).get(block_id) or {}
        entries = block.get("entries") or []
        return [entry for entry in entries if isinstance(entry, dict)]

    def _schedule_e_passthrough_rows(self) -> list[dict[str, Any]]:
        '''Assemble Schedule E Part II rows from K-1 and K-3 style source blocks.'''
        block_specs = [
            ("k1_1041", "K-1 1041"),
            ("k1_1065", "K-1 1065"),
            ("k1_1120s", "K-1 1120-S"),
            ("k3_1065", "K-3 1065"),
            ("k3_1120s", "K-3 1120-S"),
        ]
        rows: list[dict[str, Any]] = []
        for block_id, fallback_prefix in block_specs:
            for entry_index, entry in enumerate(self._f1040_block_entries(block_id)):
                try:
                    income_or_loss = round(float(entry.get("schedule_e_income_or_loss") or 0.0), 2)
                except (TypeError, ValueError):
                    income_or_loss = 0.0
                try:
                    qbi_income_or_loss = round(float(entry.get("qbi_income_or_loss") or 0.0), 2)
                except (TypeError, ValueError):
                    qbi_income_or_loss = 0.0
                payer_name = str(entry.get("payer_name") or "").strip() or f"{fallback_prefix} {entry_index + 1}"
                category = str(entry.get("category") or "").strip()
                if not payer_name and abs(income_or_loss) < 0.0000001 and abs(qbi_income_or_loss) < 0.0000001:
                    continue
                rows.append(
                    {
                        "name": payer_name,
                        "category": category,
                        "income_or_loss": income_or_loss,
                        "qbi_income_or_loss": qbi_income_or_loss,
                        "nonpassive": bool(category) and category.lower() != "passive",
                    }
                )
        return rows

    def _schedule_e_passthrough_row_value(self, index: int, field_name: str) -> Any:
        if index <= 0:
            return "" if field_name != "nonpassive" else False
        rows = self._schedule_e_passthrough_rows()
        if index > len(rows):
            return "" if field_name != "nonpassive" else False
        value = rows[index - 1].get(field_name)
        if field_name in {"income_or_loss", "qbi_income_or_loss"} and abs(float(value or 0.0)) < 0.0000001:
            return ""
        return value

    def _form_8283_rows(self) -> list[dict[str, Any]]:
        '''Assemble Form 8283 Section A rows from 1098-C style source data.'''
        rows: list[dict[str, Any]] = []
        for entry_index, entry in enumerate(self._f1040_block_entries("1098_c")):
            try:
                claimed_amount = round(float(entry.get("claimed_deduction_amount") or 0.0), 2)
            except (TypeError, ValueError):
                claimed_amount = 0.0
            description = str(entry.get("vehicle_description") or "").strip() or f"Donated property {entry_index + 1}"
            donee_name = str(entry.get("donee_name") or "").strip()
            contribution_date = entry.get("contribution_date") or ""
            if not description and not donee_name and abs(claimed_amount) < 0.0000001:
                continue
            rows.append(
                {
                    "description": description,
                    "donee_name": donee_name,
                    "contribution_date": contribution_date,
                    "claimed_amount": claimed_amount,
                    "section_b_candidate": claimed_amount > 5000.0,
                }
            )
        return rows

    def _form_8283_row_value(self, index: int, field_name: str) -> Any:
        if index <= 0:
            return "" if field_name != "section_b_candidate" else False
        rows = self._form_8283_rows()
        if index > len(rows):
            return "" if field_name != "section_b_candidate" else False
        value = rows[index - 1].get(field_name)
        if field_name == "claimed_amount" and abs(float(value or 0.0)) < 0.0000001:
            return ""
        return value

    def _referencing_form_ids(
        self,
        target_form_id: str,
        candidate_form_ids: set[str] | None = None,
    ) -> list[str]:
        referencing_ids: list[str] = []
        for form_id, _ in self._available_forms():
            if form_id == target_form_id:
                continue
            if candidate_form_ids is not None and form_id not in candidate_form_ids:
                continue
            if target_form_id in self._referenced_forms(form_id):
                referencing_ids.append(form_id)
        return referencing_ids

    def _display_owner_hint_form_ids(self, form_id: str, visible_form_ids: set[str]) -> list[str]:
        form_data = self._current_jurisdiction().get(form_id) or {}
        meta = form_data.get("_meta") or {}
        title = str(meta.get("name", "")).strip()
        if not title:
            return []

        owner_prefix = title.split(" - ", 1)[0].strip()
        hinted_ids: list[str] = []
        if owner_prefix == "Form 1040" and form_id != "f1040" and "f1040" in visible_form_ids:
            hinted_ids.append("f1040")

        for candidate_id in visible_form_ids:
            if candidate_id == form_id or self._is_worksheet(candidate_id):
                continue
            candidate_data = self._current_jurisdiction().get(candidate_id) or {}
            candidate_title = str((candidate_data.get("_meta") or {}).get("name", "")).strip()
            if candidate_title == owner_prefix or candidate_title.startswith(f"{owner_prefix} -"):
                hinted_ids.append(candidate_id)

        ordered_ids: list[str] = []
        seen: set[str] = set()
        for candidate_id in hinted_ids:
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            ordered_ids.append(candidate_id)
        return ordered_ids

    def _display_parent_form_id(
        self,
        form_id: str,
        visible_form_ids: set[str],
        filed_form_ids: set[str],
    ) -> str | None:
        if form_id in {"f1040_Federal_Info_Worksheet", "f1040"}:
            return None

        form_data = self._current_jurisdiction().get(form_id) or {}
        meta = form_data.get("_meta") or {}
        explicit_parent = meta.get("display_parent")
        if isinstance(explicit_parent, str) and explicit_parent in visible_form_ids and explicit_parent != form_id:
            return explicit_parent

        candidate_priorities: dict[str, int] = {}
        for candidate_id in self._referencing_form_ids(form_id, visible_form_ids):
            candidate_priorities[candidate_id] = min(candidate_priorities.get(candidate_id, 99), 0)
        for candidate_id in self._display_owner_hint_form_ids(form_id, visible_form_ids):
            candidate_priorities[candidate_id] = min(candidate_priorities.get(candidate_id, 99), 1)

        if self._form_filing_sequence(form_data) is not None and "f1040" in visible_form_ids:
            candidate_priorities["f1040"] = min(candidate_priorities.get("f1040", 99), 2)

        if not candidate_priorities:
            return None

        return min(
            candidate_priorities,
            key=lambda candidate_id: (
                candidate_priorities[candidate_id],
                0 if not self._is_worksheet(candidate_id) else 1,
                0 if candidate_id in filed_form_ids or candidate_id == "f1040" else 1,
                self._filing_sequence_sort_key(
                    candidate_id,
                    self._current_jurisdiction().get(candidate_id) or {},
                ),
                self._form_rank_value(candidate_id),
                candidate_id,
            ),
        )

    def _child_display_form_sort_key(
        self,
        child_form_id: str,
        filed_form_ids: set[str],
    ) -> tuple[int, tuple[int, int | str, str], float, str]:
        child_data = self._current_jurisdiction().get(child_form_id) or {}
        if self._is_worksheet(child_form_id):
            category = 3
        elif self._form_filing_sequence(child_data) is not None and child_form_id in filed_form_ids:
            category = 0
        elif self._form_filing_sequence(child_data) is not None:
            category = 1
        else:
            category = 2
        return (
            category,
            self._filing_sequence_sort_key(child_form_id, child_data),
            self._display_order_value(child_form_id),
            self._form_rank_value(child_form_id),
            child_form_id,
        )

    def _root_display_form_sort_key(
        self,
        form_id: str,
        filed_form_ids: set[str],
    ) -> tuple[int, tuple[int, int | str, str], float, str]:
        if form_id == "f1040_Federal_Info_Worksheet":
            category = 0
        elif form_id == "f1040":
            category = 1
        elif self._is_worksheet(form_id):
            category = 4
        elif form_id in filed_form_ids:
            category = 2
        else:
            category = 3
        return (
            category,
            self._filing_sequence_sort_key(form_id, self._current_jurisdiction().get(form_id) or {}),
            self._display_order_value(form_id),
            self._form_rank_value(form_id),
            form_id,
        )

    def _sheet_list_entries(self, sheet_ids: list[str] | None = None) -> list[tuple[str, int]]:
        '''Build the hierarchical left-pane sheet list with indentation levels.'''
        ordered_sheet_ids = self._deduplicate_sheet_ids(sheet_ids or self.visible_sheet_ids)
        visible_form_ids = {
            primary_id
            for sheet_id in ordered_sheet_ids
            for sheet_type, primary_id, _ in [self._parse_sheet_id(sheet_id)]
            if sheet_type == "form"
        }
        visible_block_ids_by_parent: dict[str, list[str]] = {}
        for sheet_id in ordered_sheet_ids:
            sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
            if sheet_type != "block" or secondary_id is None:
                continue
            visible_block_ids_by_parent.setdefault(primary_id, [])
            if secondary_id not in visible_block_ids_by_parent[primary_id]:
                visible_block_ids_by_parent[primary_id].append(secondary_id)

        filed_form_ids = {
            form_id
            for form_id in visible_form_ids
            if self._should_file_form_now(form_id, self._current_jurisdiction().get(form_id) or {})
        }
        parent_by_form_id = {
            form_id: self._display_parent_form_id(form_id, visible_form_ids, filed_form_ids)
            for form_id in visible_form_ids
        }
        child_form_ids_by_parent: dict[str, list[str]] = {}
        for form_id, parent_form_id in parent_by_form_id.items():
            if parent_form_id is None or parent_form_id == form_id:
                continue
            child_form_ids_by_parent.setdefault(parent_form_id, []).append(form_id)

        entries: list[tuple[str, int]] = []
        appended_sheet_ids: set[str] = set()

        def append_form_tree(form_id: str, indent_level: int, stack: set[str]) -> None:
            if form_id in stack:
                return
            form_sheet_id = self._form_sheet_id(form_id)
            if form_sheet_id in ordered_sheet_ids and form_sheet_id not in appended_sheet_ids:
                entries.append((form_sheet_id, indent_level))
                appended_sheet_ids.add(form_sheet_id)

            child_form_ids = sorted(
                child_form_ids_by_parent.get(form_id, []),
                key=lambda child_id: self._child_display_form_sort_key(child_id, filed_form_ids),
            )
            child_non_worksheets = [child_id for child_id in child_form_ids if not self._is_worksheet(child_id)]
            child_worksheets = [child_id for child_id in child_form_ids if self._is_worksheet(child_id)]

            next_stack = set(stack)
            next_stack.add(form_id)
            for child_id in child_non_worksheets:
                append_form_tree(child_id, indent_level + 1, next_stack)

            for block_id in visible_block_ids_by_parent.get(form_id, []):
                block_sheet_id = self._block_sheet_id(form_id, block_id)
                if block_sheet_id in appended_sheet_ids:
                    continue
                entries.append((block_sheet_id, indent_level + 1))
                appended_sheet_ids.add(block_sheet_id)

            for child_id in child_worksheets:
                append_form_tree(child_id, indent_level + 1, next_stack)

        root_form_ids = sorted(
            [form_id for form_id in visible_form_ids if parent_by_form_id.get(form_id) is None],
            key=lambda form_id: self._root_display_form_sort_key(form_id, filed_form_ids),
        )
        for form_id in root_form_ids:
            append_form_tree(form_id, 0, set())

        for form_id in sorted(visible_form_ids, key=lambda candidate_id: self._root_display_form_sort_key(candidate_id, filed_form_ids)):
            append_form_tree(form_id, 0, set())

        for sheet_id in ordered_sheet_ids:
            if sheet_id not in appended_sheet_ids:
                entries.append((sheet_id, 0))
                appended_sheet_ids.add(sheet_id)

        return entries

    def _ordered_sheet_ids_for_display(self, sheet_ids: list[str] | None = None) -> list[str]:
        return [sheet_id for sheet_id, _ in self._sheet_list_entries(sheet_ids)]

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
        self.visible_sheet_ids = self._ordered_sheet_ids_for_display(self.visible_sheet_ids)
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

    def _form_filing_sequence(self, form_data: dict[str, Any]) -> str | None:
        meta = form_data.get("_meta") or {}
        sequence = meta.get("filing_sequence")
        if sequence is None:
            legacy_requirement = str(meta.get("filing_requirement", "")).strip()
            return "__legacy_filed__" if legacy_requirement == "file_with_return" else None
        text = str(sequence).strip()
        if not text or text.lower() in {"none", "null"}:
            return None
        return text

    def _coerce_rule_result_to_bool(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                return False
            return float(value) != 0.0
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized not in {"", "0", "false", "none", "null"}
        return bool(value)

    def _evaluate_activation_rule(self, form_id: str, rule: Any) -> bool | None:
        '''Evaluate activation metadata, returning None when no usable rule exists.'''
        if not isinstance(rule, str):
            return None
        expr = rule.strip()
        if not expr:
            return None
        result = self._evaluate_equation(form_id, expr, set())
        if result is None:
            return None
        return self._coerce_rule_result_to_bool(result)

    def _form_activation_rule_result(self, form_id: str, form_data: dict[str, Any]) -> bool | None:
        meta = form_data.get("_meta") or {}
        return self._evaluate_activation_rule(form_id, meta.get("activation_rule"))

    def _form_is_activated_now(self, form_id: str, form_data: dict[str, Any]) -> bool:
        result = self._form_activation_rule_result(form_id, form_data)
        if result is not None:
            return result
        return False

    def _block_activation_rule_result(self, parent_form_id: str, block: dict[str, Any]) -> bool | None:
        return self._evaluate_activation_rule(parent_form_id, block.get("activation_rule"))

    def _block_is_activated_now(self, parent_form_id: str, block: dict[str, Any]) -> bool:
        result = self._block_activation_rule_result(parent_form_id, block)
        if result is not None:
            return result
        return False

    def _visible_block_ids(self, parent_form_id: str, form_data: dict[str, Any]) -> list[str]:
        visible_block_ids = list(self._used_block_ids(form_data))
        blocks = form_data.get("blocks") or {}
        for block_id, block in blocks.items():
            if not isinstance(block, dict):
                continue
            if block_id in visible_block_ids:
                continue
            if self._block_is_activated_now(parent_form_id, block):
                visible_block_ids.append(block_id)
        return visible_block_ids

    def _ensure_activated_block_entries(self) -> None:
        for form_id, form_data in self._available_forms():
            blocks = form_data.get("blocks") or {}
            for block_id, block in blocks.items():
                if not isinstance(block, dict):
                    continue
                if not self._block_is_activated_now(form_id, block):
                    continue
                try:
                    minimum_entries = int(block.get("activated_min_entries", 0) or 0)
                except (TypeError, ValueError):
                    minimum_entries = 0
                if minimum_entries <= 0:
                    continue
                entries = block.setdefault("entries", [])
                if not isinstance(entries, list):
                    continue
                while len([entry for entry in entries if isinstance(entry, dict)]) < minimum_entries:
                    entries.append(self._new_block_entry(block))

    def _cell_has_meaningful_value(self, cell: dict[str, Any]) -> bool:
        value = cell.get("value")
        default = cell.get("default")
        format_code = str(cell.get("format", "text"))
        manual_entry = bool(cell.get("manual_entry", False))
        if format_code in {"text", "date"}:
            return manual_entry and isinstance(value, str) and value.strip() != ""
        if format_code == TRI_STATE_BOOLEAN_FORMAT:
            return manual_entry and value is not None
        if isinstance(value, bool):
            return manual_entry and value is True
        if isinstance(value, (int, float)):
            if not manual_entry:
                return False
            if not math.isfinite(float(value)):
                return False
            return value != default and value != 0
        return manual_entry and value not in (None, "", default)

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

    def _cell_is_yes(self, form_id: str, cell_id: str) -> bool:
        return self._cell_value(form_id, cell_id) is True

    def _cell_is_no(self, form_id: str, cell_id: str) -> bool:
        return self._cell_value(form_id, cell_id) is False

    def _cell_is_answered(self, form_id: str, cell_id: str) -> bool:
        return self._cell_value(form_id, cell_id) is not None

    def _block_numeric_total(self, parent_form_id: str, block_id: str, field_name: str) -> float:
        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id) or {}
        total = 0.0
        for entry in block.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            try:
                total += float(entry.get(field_name) or 0.0)
            except (TypeError, ValueError):
                continue
        return round(total, 2)

    def _f8962_1095_a_entries(self) -> list[dict[str, Any]]:
        form_data = self._current_jurisdiction().get("f1040") or {}
        block = (form_data.get("blocks") or {}).get("1095_a") or {}
        entries = block.get("entries") or []
        return [entry for entry in entries if isinstance(entry, dict)]

    def _f8962_entry_amount(self, entry: dict[str, Any], field_name: str) -> float:
        try:
            number = float(entry.get(field_name) or 0.0)
        except (TypeError, ValueError):
            return 0.0
        return number if math.isfinite(number) else 0.0

    def _f8962_month_field_name(self, month_number: Any, suffix: str) -> str:
        try:
            month = int(month_number)
        except (TypeError, ValueError):
            month = 1
        month = max(1, min(12, month))
        return f"month_{month:02d}_{suffix}"

    def _f8962_has_allocation_percentages(self, entry: dict[str, Any]) -> bool:
        return any(
            abs(self._f8962_entry_amount(entry, field_name)) > 0.0000001
            for field_name in ("allocation_premium_pct", "allocation_slcsp_pct", "allocation_advance_ptc_pct")
        )

    def _f8962_entry_has_policy_allocation(self, entry: dict[str, Any]) -> bool:
        return bool(entry.get("multiple_tax_family_allocation")) or bool(
            str(entry.get("allocation_other_taxpayer_ssn") or "").strip()
        ) or self._f8962_has_allocation_percentages(entry)

    def _f8962_entry_month_in_allocation_range(self, entry: dict[str, Any], month_number: int) -> bool:
        if not self._f8962_entry_has_policy_allocation(entry):
            return False
        start_month = int(self._f8962_entry_amount(entry, "allocation_start_month"))
        stop_month = int(self._f8962_entry_amount(entry, "allocation_stop_month"))
        if start_month <= 0 or stop_month <= 0:
            return True
        start_month = max(1, min(12, start_month))
        stop_month = max(1, min(12, stop_month))
        if start_month > stop_month:
            start_month, stop_month = stop_month, start_month
        return start_month <= month_number <= stop_month

    def _f8962_entry_allocation_factor(self, entry: dict[str, Any], amount_kind: str, month_number: int) -> float:
        if not self._f8962_entry_has_policy_allocation(entry):
            return 1.0
        if not self._f8962_entry_month_in_allocation_range(entry, month_number):
            return 1.0
        if amount_kind == "enrollment_premiums":
            field_name = "allocation_premium_pct"
        elif amount_kind == "slcsp":
            field_name = "allocation_slcsp_pct"
        else:
            field_name = "allocation_advance_ptc_pct"
        if not self._f8962_has_allocation_percentages(entry):
            return 1.0
        percent = self._f8962_entry_amount(entry, field_name)
        if percent <= 0.0:
            return 0.0
        return percent / 100.0

    def _f8962_entry_has_monthly_detail(self, entry: dict[str, Any]) -> bool:
        for suffix in ("enrollment_premiums", "slcsp", "advance_ptc"):
            for month in range(1, 13):
                if abs(self._f8962_entry_amount(entry, self._f8962_month_field_name(month, suffix))) > 0.0000001:
                    return True
        return False

    def _f8962_policy_month_total(self, amount_kind: str, month_number: Any) -> float:
        try:
            month = int(month_number)
        except (TypeError, ValueError):
            return 0.0
        if month < 1 or month > 12:
            return 0.0
        field_name = self._f8962_month_field_name(month, amount_kind)
        total = 0.0
        for entry in self._f8962_1095_a_entries():
            amount = self._f8962_entry_amount(entry, field_name)
            total += amount * self._f8962_entry_allocation_factor(entry, amount_kind, month)
        return round(total, 2)

    def _f8962_policy_annual_total(self, amount_kind: str) -> float:
        annual_field_name = {
            "enrollment_premiums": "annual_enrollment_premiums",
            "slcsp": "annual_slcsp",
            "advance_ptc": "annual_advance_ptc",
        }[amount_kind]
        total = 0.0
        for entry in self._f8962_1095_a_entries():
            if self._f8962_entry_has_monthly_detail(entry):
                total += sum(
                    self._f8962_entry_amount(entry, self._f8962_month_field_name(month, amount_kind))
                    * self._f8962_entry_allocation_factor(entry, amount_kind, month)
                    for month in range(1, 13)
                )
                continue
            total += self._f8962_entry_amount(entry, annual_field_name)
        return round(total, 2)

    def _f8962_policy_monthly_data_present(self) -> bool:
        return any(self._f8962_entry_has_monthly_detail(entry) for entry in self._f8962_1095_a_entries())

    def _f8962_has_policy_allocations(self) -> bool:
        return any(self._f8962_entry_has_policy_allocation(entry) for entry in self._f8962_1095_a_entries())

    def _f8962_allocation_entries(self) -> list[dict[str, Any]]:
        return [entry for entry in self._f8962_1095_a_entries() if self._f8962_entry_has_policy_allocation(entry)]

    def _f8962_allocation_row_value(self, row_number: Any, field_name: str) -> Any:
        try:
            index = int(row_number) - 1
        except (TypeError, ValueError):
            return ""
        entries = self._f8962_allocation_entries()
        if index < 0 or index >= len(entries):
            return "" if field_name in {"policy_number", "other_taxpayer_ssn"} else 0
        entry = entries[index]
        direct_fields = {
            "policy_number": "policy_number",
            "other_taxpayer_ssn": "allocation_other_taxpayer_ssn",
            "start_month": "allocation_start_month",
            "stop_month": "allocation_stop_month",
            "premium_pct": "allocation_premium_pct",
            "slcsp_pct": "allocation_slcsp_pct",
            "advance_ptc_pct": "allocation_advance_ptc_pct",
        }
        source_field = direct_fields.get(field_name)
        if source_field is None:
            return ""
        if field_name in {"policy_number", "other_taxpayer_ssn"}:
            return str(entry.get(source_field) or "")
        amount = self._f8962_entry_amount(entry, source_field)
        return int(amount) if field_name in {"start_month", "stop_month"} else round(amount, 2)

    def _f8962_allocation_rows_fit_on_form(self) -> bool:
        return len(self._f8962_allocation_entries()) <= 4

    def _f8962_monthly_contribution_amount(self, month_number: Any) -> float:
        try:
            month = int(month_number)
        except (TypeError, ValueError):
            return 0.0
        if month < 1 or month > 12:
            return 0.0
        base_amount = round(self._cell_amount("f8962", "monthly_contribution_base"), 2)
        if not self._cell_value("f8962", "alternative_calculation_for_marriage"):
            return base_amount
        total = 0.0
        used_alternative = False
        for prefix in ("taxpayer", "spouse"):
            contribution_amount = self._cell_amount("f8962", f"alternative_{prefix}_monthly_contribution_amount")
            if contribution_amount <= 0.0:
                continue
            start_month = int(self._cell_amount("f8962", f"alternative_{prefix}_start_month"))
            stop_month = int(self._cell_amount("f8962", f"alternative_{prefix}_stop_month"))
            if start_month <= 0 or stop_month <= 0:
                continue
            start_month = max(1, min(12, start_month))
            stop_month = max(1, min(12, stop_month))
            if start_month > stop_month:
                start_month, stop_month = stop_month, start_month
            if start_month <= month <= stop_month:
                total += contribution_amount
                used_alternative = True
        return round(total if used_alternative else base_amount, 2)

    def _f2441_qualifying_person_rows(self) -> list[dict[str, Any]]:
        '''Collect the currently entered qualifying-person rows for Form 2441.'''
        rows: list[dict[str, Any]] = []
        for row in range(1, 4):
            name = str(self._cell_value("f2441", f"qualifying_person_{row}_name") or "").strip()
            tin = str(self._cell_value("f2441", f"qualifying_person_{row}_tin") or "").strip()
            try:
                expenses = round(float(self._cell_value("f2441", f"qualifying_person_{row}_care_expenses") or 0.0), 2)
            except (TypeError, ValueError):
                expenses = 0.0
            if not name and not tin and abs(expenses) < 0.0000001:
                continue
            rows.append({"name": name, "tin": tin, "expenses": expenses})
        return rows

    def _f2441_qualifying_person_count(self) -> int:
        return len(self._f2441_qualifying_person_rows())

    def _f2441_qualified_expenses_total(self) -> float:
        return round(sum(row["expenses"] for row in self._f2441_qualifying_person_rows()), 2)

    def _f2441_expense_limit(self) -> float:
        count = self._f2441_qualifying_person_count()
        if count <= 0:
            return 0.0
        if count == 1:
            return 3000.0
        return 6000.0

    def _f2441_deemed_income_amount(self) -> float:
        return 500.0 if self._f2441_qualifying_person_count() >= 2 else 250.0

    def _f2441_deemed_income(self, recipient: str) -> float:
        months_cell_id = (
            "taxpayer_student_or_disabled_months"
            if recipient == "taxpayer"
            else "spouse_student_or_disabled_months"
        )
        try:
            months = int(self._cell_value("f2441", months_cell_id) or 0)
        except (TypeError, ValueError):
            months = 0
        months = max(0, min(months, 12))
        return round(months * self._f2441_deemed_income_amount(), 2)

    def _f2441_w2_earned_income(self, recipient: str) -> float:
        total = 0.0
        for entry in self._f1040_block_entries("w2"):
            if str(entry.get("recipient") or "taxpayer").strip() != recipient:
                continue
            try:
                total += float(entry.get("box_1") or 0.0)
            except (TypeError, ValueError):
                continue
        return round(total, 2)

    def _f2441_earned_income(self, recipient: str) -> float:
        base_amount = self._f2441_w2_earned_income(recipient)
        adjustment_cell_id = (
            "taxpayer_earned_income_adjustments"
            if recipient == "taxpayer"
            else "spouse_earned_income_adjustments"
        )
        try:
            base_amount += float(self._cell_value("f2441", adjustment_cell_id) or 0.0)
        except (TypeError, ValueError):
            pass
        return round(max(base_amount, self._f2441_deemed_income(recipient)), 2)

    def _f2441_applicable_percentage(self) -> float:
        try:
            agi = float(self._cell_value("f2441", "7") or 0.0)
        except (TypeError, ValueError):
            agi = 0.0
        if agi <= 15000.0:
            return 0.35
        reduction_steps = int((agi - 15000.0) // 2000.0) + 1
        return round(max(0.20, 0.35 - (0.01 * reduction_steps)), 2)

    def _f8949_preview_block_ids(self, section: str) -> tuple[str, ...]:
        if section == "short":
            return F8949_SHORT_TERM_BLOCK_IDS
        if section == "long":
            return F8949_LONG_TERM_BLOCK_IDS
        return ()

    def _f8949_block_entries(self, block_id: str) -> list[dict[str, Any]]:
        form_data = self._current_jurisdiction().get("f8949") or {}
        block = ((form_data.get("blocks") or {}).get(block_id) or {})
        return [entry for entry in (block.get("entries") or []) if isinstance(entry, dict)]

    def _f8949_copy_specs(
        self,
        *,
        block_id: str | None = None,
        section: str | None = None,
    ) -> list[dict[str, Any]]:
        '''Build Form 8949 attachment copies by checkbox family and 11-row chunks.'''
        if block_id is not None:
            block_ids = (block_id,)
        else:
            block_ids: tuple[str, ...] = ()
            if section in {None, "short"}:
                block_ids += F8949_SHORT_TERM_BLOCK_IDS
            if section in {None, "long"}:
                block_ids += F8949_LONG_TERM_BLOCK_IDS
        specs: list[dict[str, Any]] = []
        for current_block_id in block_ids:
            entries = self._f8949_block_entries(current_block_id)
            if not entries:
                continue
            current_section = "short" if current_block_id in F8949_SHORT_TERM_BLOCK_IDS else "long"
            for copy_index, row_offset in enumerate(range(0, len(entries), F8949_ROWS_PER_COPY), start=1):
                specs.append(
                    {
                        "block_id": current_block_id,
                        "section": current_section,
                        "copy_index": copy_index,
                        "row_offset": row_offset,
                        "entries": entries[row_offset : row_offset + F8949_ROWS_PER_COPY],
                    }
                )
        return specs

    def _f8949_copy_label(self, spec: dict[str, Any]) -> str:
        block_id = str(spec.get("block_id") or "")
        section = str(spec.get("section") or "")
        copy_index = int(spec.get("copy_index") or 1)
        box_letter = block_id.split("_")[-1].upper() if block_id else "?"
        section_label = "Short-term" if section == "short" else "Long-term"
        total_copies = len(self._f8949_copy_specs(block_id=block_id))
        if total_copies > 1:
            return f"{section_label} Box {box_letter} copy {copy_index}"
        return f"{section_label} Box {box_letter}"

    def _f8949_preview_copy_spec(self, section: str) -> dict[str, Any] | None:
        render_context = self._pdf_render_context or {}
        spec = render_context.get("f8949_copy_spec")
        if isinstance(spec, dict) and spec.get("section") == section:
            return spec
        current_sheet = self._current_visible_sheet_id()
        if current_sheet:
            sheet_type, primary_id, secondary_id = self._parse_sheet_id(current_sheet)
            if (
                sheet_type == "block"
                and primary_id == "f8949"
                and secondary_id in self._f8949_preview_block_ids(section)
            ):
                copy_specs = self._f8949_copy_specs(block_id=secondary_id)
                if copy_specs:
                    entry_index = self._current_block_preview_entry_index("f8949", secondary_id)
                    copy_index = max(0, min(entry_index // F8949_ROWS_PER_COPY, len(copy_specs) - 1))
                    return copy_specs[copy_index]
        copy_specs = self._f8949_copy_specs(section=section)
        return copy_specs[0] if copy_specs else None

    def _f8949_preview_checkbox(self, block_id: str) -> bool:
        section = "short" if block_id in F8949_SHORT_TERM_BLOCK_IDS else "long" if block_id in F8949_LONG_TERM_BLOCK_IDS else ""
        if not section:
            return False
        spec = self._f8949_preview_copy_spec(section)
        return bool(spec) and str(spec.get("block_id")) == block_id

    def _f8949_preview_row_value(self, section: str, row_number: Any, field_name: str) -> Any:
        spec = self._f8949_preview_copy_spec(section)
        if not spec:
            return ""
        try:
            row_index = int(row_number) - 1
        except (TypeError, ValueError):
            return ""
        if row_index < 0:
            return ""
        entries = spec.get("entries") or []
        if row_index >= len(entries):
            return ""
        value = entries[row_index].get(field_name) if isinstance(entries[row_index], dict) else ""
        if field_name in {"proceeds", "basis", "adjustment_amount", "gain_loss"}:
            try:
                return round(float(value or 0.0), 2)
            except (TypeError, ValueError):
                return 0.0
        return value or ""

    def _f8949_preview_total(self, section: str, column: str) -> Any:
        spec = self._f8949_preview_copy_spec(section)
        if not spec:
            return ""
        field_name = {
            "d": "proceeds",
            "e": "basis",
            "g": "adjustment_amount",
            "h": "gain_loss",
        }.get(column)
        if field_name is None:
            return ""
        entries = spec.get("entries") or []
        if not entries:
            return ""
        total = 0.0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                total += float(entry.get(field_name) or 0.0)
            except (TypeError, ValueError):
                continue
        return round(total, 2)

    def _f8949_copy_specs_for_sheet(self, sheet_type: str, primary_id: str, secondary_id: str | None) -> list[dict[str, Any]]:
        if sheet_type == "form" and primary_id == "f8949":
            return self._f8949_copy_specs()
        if (
            sheet_type == "block"
            and primary_id == "f8949"
            and isinstance(secondary_id, str)
            and secondary_id in (*F8949_SHORT_TERM_BLOCK_IDS, *F8949_LONG_TERM_BLOCK_IDS)
        ):
            return self._f8949_copy_specs(block_id=secondary_id)
        return []

    def _f8949_preview_render_context(self, sheet_type: str, primary_id: str, secondary_id: str | None) -> dict[str, Any] | None:
        copy_specs = self._f8949_copy_specs_for_sheet(sheet_type, primary_id, secondary_id)
        if not copy_specs:
            return None
        if (
            sheet_type == "block"
            and primary_id == "f8949"
            and isinstance(secondary_id, str)
            and secondary_id in (*F8949_SHORT_TERM_BLOCK_IDS, *F8949_LONG_TERM_BLOCK_IDS)
        ):
            entry_index = self._current_block_preview_entry_index("f8949", secondary_id)
            copy_index = max(0, min(entry_index // F8949_ROWS_PER_COPY, len(copy_specs) - 1))
            return {"f8949_copy_spec": copy_specs[copy_index]}
        return {"f8949_copy_spec": copy_specs[0]}

    def _cell_uses_custom_evaluation(self, form_id: str, cell_id: str) -> bool:
        '''Identify cells whose values come from Python helpers instead of JSON equations.'''
        if form_id == "f8615" and cell_id in {"age_support_test_met", "required_to_file"}:
            return True
        if form_id == "f1040" and cell_id in {"2b", "3b"}:
            return True
        if form_id == "f1040sb":
            return bool(
                cell_id in {"1", "4"}
                or re.fullmatch(r"line_[14]_(payer|amount)_\d+", cell_id)
            )
        if form_id == "f1040se":
            return bool(re.fullmatch(r"passthrough_(\d+)_(name|category|income_or_loss|nonpassive|qbi_income_or_loss)", cell_id))
        if form_id == "f8283":
            return bool(
                re.fullmatch(
                    r"section_a_item_(\d+)_(description|donee_name|contribution_date|claimed_amount|section_b_candidate)",
                    cell_id,
                )
            )
        return False

    def _questionnaire_triggered_form_ids(self) -> set[str]:
        triggered_form_ids: set[str] = set()
        for cell_id, form_ids in MASTER_QUESTIONNAIRE_FORM_TRIGGERS.items():
            if not self._cell_is_yes("f1040_Return_Intake_Questions", cell_id):
                continue
            triggered_form_ids.update(form_ids)
        for cell_id, form_ids in SCHEDULE_A_QUESTIONNAIRE_FORM_TRIGGERS.items():
            if not self._cell_is_yes("f1040sa_Questionnaire", cell_id):
                continue
            triggered_form_ids.update(form_ids)
        for category in F1116_CATEGORY_DEFINITIONS:
            if not self._cell_is_yes("f1116_Questionnaire", category["question_cell"]):
                continue
            suffix = category["suffix"]
            triggered_form_ids.add(f"f1116_{suffix}")
            if suffix != "section_951a" and (
                self._cell_is_yes("f1116_Questionnaire", "has_prior_year_carryovers")
                or self._cell_is_yes(
                "f1116_Questionnaire",
                "expects_current_year_carryover_activity",
                )
            ):
                triggered_form_ids.add(f"f1116sb_{suffix}")
            if self._cell_is_yes("f1116_Questionnaire", "has_foreign_tax_redeterminations"):
                triggered_form_ids.add(f"f1116sc_{suffix}")
        return triggered_form_ids

    def _f1116_category_definition_for_form(self, form_id: str) -> dict[str, str] | None:
        for prefix in ("f1116sb_", "f1116sc_", "f1116_"):
            if not form_id.startswith(prefix):
                continue
            suffix = form_id[len(prefix):]
            for category in F1116_CATEGORY_DEFINITIONS:
                if category["suffix"] == suffix:
                    return category
        return None

    def _mapped_family_preview_form_id(self, form_id: str) -> str:
        if form_id in F1116_COPY_BASE_IDS:
            return F1116_COPY_BASE_IDS[form_id]
        for family_prefix, base_id in (("f1116sb_", "f1116sb"), ("f1116sc_", "f1116sc"), ("f1116_", "f1116")):
            if form_id.startswith(family_prefix):
                return base_id
        return form_id

    def _f1116_category_cells_touched(self) -> bool:
        return any(("f1116", cell_id) in self.touched_input_cells for cell_id in F1116_CATEGORY_QUESTION_MAP)

    def _sync_f1116_category_from_questionnaire(self) -> None:
        if self._f1116_category_cells_touched():
            return
        form_data = self._current_jurisdiction().get("f1116") or {}
        cells = form_data.get("cells") or {}
        answered = False
        updated = False
        for category_cell_id, question_cell_id in F1116_CATEGORY_QUESTION_MAP.items():
            cell = cells.get(category_cell_id)
            if not isinstance(cell, dict):
                continue
            question_value = self._cell_value("f1116_Questionnaire", question_cell_id)
            if question_value is None:
                continue
            answered = True
            mapped_value = question_value is True
            if cell.get("value") != mapped_value:
                cell["value"] = mapped_value
                updated = True
        if answered and updated:
            self._evaluation_cache.clear()

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

    def _f8615_age_support_test_met(self) -> bool:
        age = self._cell_amount("f8615", "taxpayer_age_end_of_2025")
        earned_income_more_than_half_support = bool(self._cell_value("f8615", "earned_income_more_than_half_support"))
        full_time_student = bool(self._cell_value("f8615", "taxpayer_full_time_student"))
        if age < 18:
            return True
        if age == 18:
            return not earned_income_more_than_half_support
        if 18 < age < 24:
            return full_time_student and not earned_income_more_than_half_support
        return False

    def _f8615_required_to_file(self) -> bool:
        return (
            bool(self._cell_value("f8615", "child_required_to_file_return"))
            and self._cell_amount("f8615", "1") > 2700.0
            and bool(self._cell_value("f8615", "parent_alive_at_year_end"))
            and not bool(self._cell_value("f8615", "child_files_joint_return"))
            and self._f8615_age_support_test_met()
        )

    def _block_has_entries(self, parent_form_id: str, block_id: str) -> bool:
        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id) or {}
        entries = block.get("entries") or []
        return any(isinstance(entry, dict) for entry in entries)

    def _should_file_form_now(self, form_id: str, form_data: dict[str, Any]) -> bool:
        '''Decide whether a form belongs in the active filed-return set right now.'''
        if form_id == "f1040":
            return True
        if self._form_filing_sequence(form_data) is None:
            return False
        activation_rule_result = self._form_activation_rule_result(form_id, form_data)
        if activation_rule_result is not None:
            return activation_rule_result
        category_definition = self._f1116_category_definition_for_form(form_id)
        if category_definition is not None and form_id.startswith("f1116_"):
            has_foreign_income_facts = (
                self._cell_is_yes("f1040_Return_Intake_Questions", "has_foreign_income")
                or self._cell_is_yes("f1116_Questionnaire", category_definition["question_cell"])
                or self._cell_amount(form_id, "1a") > 0.0
            )
            has_foreign_tax_facts = (
                self._cell_is_yes("f1040_Return_Intake_Questions", "paid_foreign_taxes")
                or self._cell_amount(form_id, "8") > 0.0
            )
            has_carryover_facts = (
                self._cell_is_yes("f1040_Return_Intake_Questions", "prior_year_foreign_tax_carryovers")
                or self._cell_is_yes("f1116_Questionnaire", "has_prior_year_carryovers")
                or self._cell_amount(form_id, "10") > 0.0
            )
            if self._form_has_user_activity(form_id, form_data):
                return has_foreign_income_facts and (has_foreign_tax_facts or has_carryover_facts)
            if not has_foreign_income_facts:
                return False
            if self._cell_amount(form_id, "35") > 0.0:
                return True
            return has_foreign_tax_facts or has_carryover_facts
        if category_definition is not None and form_id.startswith("f1116sb_"):
            if category_definition["suffix"] == "section_951a":
                return False
            return self._should_file_form_now(f"f1116_{category_definition['suffix']}", self._current_jurisdiction().get(f"f1116_{category_definition['suffix']}") or {}) and (
                self._cell_is_yes("f1116_Questionnaire", "has_prior_year_carryovers")
                or self._cell_is_yes("f1116_Questionnaire", "expects_current_year_carryover_activity")
                or self._form_has_user_activity(form_id, form_data)
                or self._form_has_meaningful_values(form_data)
            )
        if category_definition is not None and form_id.startswith("f1116sc_"):
            return self._should_file_form_now(f"f1116_{category_definition['suffix']}", self._current_jurisdiction().get(f"f1116_{category_definition['suffix']}") or {}) and (
                self._cell_is_yes("f1116_Questionnaire", "has_foreign_tax_redeterminations")
                or self._form_has_user_activity(form_id, form_data)
                or self._form_has_meaningful_values(form_data)
            )
        if form_id == "f1116":
            direct_election_total = self._cell_amount("f1116", "direct_election_total_foreign_tax")
            direct_election_threshold = self._cell_amount("f1116", "direct_election_threshold")
            direct_election_likely_eligible = bool(self._cell_value("f1116", "direct_election_likely_eligible"))
            elected_without_form = bool(self._cell_value("f1116", "elect_credit_without_form_1116"))
            questionnaire_foreign_income = self._cell_is_yes("f1040_Return_Intake_Questions", "has_foreign_income")
            questionnaire_foreign_taxes = self._cell_is_yes("f1040_Return_Intake_Questions", "paid_foreign_taxes")
            questionnaire_prior_carryovers = self._cell_is_yes(
                "f1040_Return_Intake_Questions",
                "prior_year_foreign_tax_carryovers",
            ) or self._cell_is_yes("f1116_Questionnaire", "has_prior_year_carryovers")
            foreign_source_income_total = self._block_numeric_total("f1040", "foreign_tax_credit_items", "gross_income")
            foreign_tax_paid_total = self._block_numeric_total("f1040", "foreign_tax_credit_items", "foreign_tax_paid")
            has_foreign_income_facts = (
                questionnaire_foreign_income
                or foreign_source_income_total > 0.0
                or self._cell_amount("f1116", "1a") > 0.0
            )
            has_foreign_tax_facts = (
                questionnaire_foreign_taxes
                or direct_election_total > 0.0
                or self._cell_amount("f1116", "8") > 0.0
                or foreign_tax_paid_total > 0.0
            )
            has_carryover_facts = questionnaire_prior_carryovers or self._cell_amount("f1116", "10") > 0.0
            if elected_without_form:
                return False
            if self._form_has_user_activity(form_id, form_data):
                return has_foreign_income_facts and (has_foreign_tax_facts or has_carryover_facts)
            if self._cell_amount("f1116", "35") > 0.0:
                return has_foreign_income_facts
            if not has_foreign_income_facts:
                return False
            if has_foreign_tax_facts and (not direct_election_likely_eligible or direct_election_total > direct_election_threshold):
                return True
            if has_carryover_facts:
                return True
            return False
        if form_id == "f1116sb":
            return self._should_file_form_now("f1116", self._current_jurisdiction().get("f1116") or {}) and (
                self._cell_is_yes("f1116_Questionnaire", "has_prior_year_carryovers")
                or self._cell_is_yes("f1116_Questionnaire", "expects_current_year_carryover_activity")
                or self._form_has_user_activity(form_id, form_data)
                or self._form_has_meaningful_values(form_data)
            )
        if form_id == "f1116sc":
            return self._should_file_form_now("f1116", self._current_jurisdiction().get("f1116") or {}) and (
                self._cell_is_yes("f1116_Questionnaire", "has_foreign_tax_redeterminations")
                or self._form_has_user_activity(form_id, form_data)
                or self._form_has_meaningful_values(form_data)
            )
        return self._form_has_user_activity(form_id, form_data) or bool(self._used_block_ids(form_data))

    def _filed_form_ids(self) -> list[str]:
        filed_form_ids: list[str] = []
        for form_id, form_data in self._available_forms():
            if self._should_file_form_now(form_id, form_data):
                filed_form_ids.append(form_id)
        return filed_form_ids

    def _auto_visible_sheet_ids(self) -> list[str]:
        '''Compute the sheets that should appear automatically from current usage.'''
        jdata = self._current_jurisdiction()
        if not jdata:
            return []

        base_form_ids = set(self._default_visible_forms())
        filed_form_ids = set(self._filed_form_ids())
        active_form_ids: set[str] = set()
        for form_id, form_data in self._available_forms():
            if self._form_is_activated_now(form_id, form_data):
                active_form_ids.add(form_id)
            if self._form_has_user_activity(form_id, form_data):
                active_form_ids.add(form_id)
            if self._form_has_meaningful_values(form_data):
                active_form_ids.add(form_id)
            if self._used_block_ids(form_data):
                active_form_ids.add(form_id)
        active_form_ids.update(self._questionnaire_triggered_form_ids())

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
            for block_id in self._visible_block_ids(form_id, form_data):
                sheet_ids.append(self._block_sheet_id(form_id, block_id))
        for form_id, form_data in self._available_forms():
            if form_id in ordered_filed_form_ids or form_id not in expanded_form_ids:
                continue
            sheet_ids.append(self._form_sheet_id(form_id))
            for block_id in self._visible_block_ids(form_id, form_data):
                sheet_ids.append(self._block_sheet_id(form_id, block_id))
        return self._ordered_sheet_ids_for_display(sheet_ids)

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
            self.visible_sheet_ids = self._ordered_sheet_ids_for_display(merged_sheet_ids)
        else:
            self.visible_sheet_ids = self._ordered_sheet_ids_for_display(auto_sheet_ids)

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
        if format_code == TRI_STATE_BOOLEAN_FORMAT:
            return value is not None
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
        display_entries = self._sheet_list_entries(self.visible_sheet_ids)
        for sheet_id, indent_level in display_entries:
            indent = "    " * max(indent_level, 0)
            item = QListWidgetItem(f"{indent}{self._sheet_navigator_label(sheet_id)}")
            item.setData(Qt.UserRole, sheet_id)
            self._apply_sheet_list_item_background(item, sheet_id)
            self._apply_sheet_list_item_foreground(item, sheet_id)
            self.sheet_list.addItem(item)

        if self.sheet_list.count() == 0:
            self.table.setRowCount(0)
            return

        ordered_sheet_ids = [sheet_id for sheet_id, _ in display_entries]
        target_sheet_id = select_sheet_id or (ordered_sheet_ids[0] if ordered_sheet_ids else None)
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

    def _export_pdf_dir(self) -> Path:
        export_dir = Path(tempfile.gettempdir()) / "opentax-exported-pdfs"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir

    def _deduplicate_sheet_ids(self, sheet_ids: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for sheet_id in sheet_ids:
            if sheet_id in seen:
                continue
            seen.add(sheet_id)
            ordered.append(sheet_id)
        return ordered

    def _filing_sequence_sort_key(self, form_id: str, form_data: dict[str, Any]) -> tuple[int, int | str, str]:
        if form_id == "f1040":
            return (0, 0, form_id)
        sequence = self._form_filing_sequence(form_data)
        if sequence is None:
            return (2, form_id, form_id)
        match = re.fullmatch(r"(\d+)([A-Za-z]*)", sequence)
        if match:
            return (1, int(match.group(1)), match.group(2) or form_id)
        return (1, sequence, form_id)

    def _filing_export_sheet_ids(self) -> list[str]:
        filed_form_ids = [
            form_id
            for form_id, form_data in self._available_forms()
            if self._should_file_form_now(form_id, form_data) and self._sheet_exists(self._form_sheet_id(form_id))
        ]
        filed_form_ids.sort(
            key=lambda form_id: self._filing_sequence_sort_key(
                form_id,
                self._current_jurisdiction().get(form_id) or {},
            )
        )
        return [self._form_sheet_id(form_id) for form_id in filed_form_ids]

    def _all_export_sheet_ids(self) -> list[str]:
        visible_sheet_ids = [sheet_id for sheet_id in self.visible_sheet_ids if self._sheet_exists(sheet_id)]
        filing_sheet_ids = self._filing_export_sheet_ids()
        filing_set = set(filing_sheet_ids)
        trailing_sheet_ids = [sheet_id for sheet_id in visible_sheet_ids if sheet_id not in filing_set]
        return self._deduplicate_sheet_ids(filing_sheet_ids + trailing_sheet_ids)

    def _sheet_pdf_export_items(self, sheet_id: str) -> tuple[list[tuple[Path, str]], list[str]]:
        sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
        sheet_label = self._sheet_label(sheet_id)
        preview_form_id = self._mapped_preview_id(sheet_type, primary_id, secondary_id)
        value_form_id = primary_id if sheet_type == "form" else preview_form_id
        raw_pdf = self._raw_preview_source_path(sheet_type, primary_id, secondary_id)

        if preview_form_id == "f8949":
            copy_specs = self._f8949_copy_specs_for_sheet(sheet_type, primary_id, secondary_id)
            if (
                copy_specs
                and self.pdf_preview_engine is not None
                and self.pdf_preview_engine.available()
                and self.pdf_preview_engine.has_render_mappings_for_form(preview_form_id)
            ):
                included_items: list[tuple[Path, str]] = []
                missing_labels: list[str] = []
                for spec in copy_specs:
                    copy_label = f"{sheet_label} ({self._f8949_copy_label(spec)})"
                    try:
                        pdf_path = self._render_preview_with_context(
                            preview_form_id=preview_form_id,
                            value_form_id=value_form_id or preview_form_id,
                            render_context={"f8949_copy_spec": spec},
                        )
                    except Exception:
                        pdf_path = None
                    if pdf_path is None or not pdf_path.is_file():
                        missing_labels.append(copy_label)
                        continue
                    included_items.append((pdf_path, copy_label))
                if included_items or missing_labels:
                    return included_items, missing_labels

        if (
            preview_form_id is not None
            and self.pdf_preview_engine is not None
            and self.pdf_preview_engine.available()
            and self.pdf_preview_engine.has_render_mappings_for_form(preview_form_id)
        ):
            try:
                pdf_path = self._render_preview_with_context(
                    preview_form_id=preview_form_id,
                    value_form_id=value_form_id or preview_form_id,
                )
                if pdf_path.is_file():
                    return [(pdf_path, sheet_label)], []
            except Exception:
                pass

        if raw_pdf and raw_pdf.is_file():
            return [(raw_pdf, sheet_label)], []
        return [], [sheet_label]

    def _build_pdf_package(self, sheet_ids: list[str], output_path: Path) -> tuple[list[str], list[str]]:
        if PdfReader is None or PdfWriter is None:
            raise RuntimeError("PDF export dependencies are not available.")

        writer = PdfWriter()
        included_labels: list[str] = []
        missing_labels: list[str] = []

        for sheet_id in self._deduplicate_sheet_ids(sheet_ids):
            export_items, export_missing_labels = self._sheet_pdf_export_items(sheet_id)
            missing_labels.extend(export_missing_labels)
            for pdf_path, label in export_items:
                if not pdf_path.is_file():
                    missing_labels.append(label)
                    continue
                writer.append(PdfReader(str(pdf_path)))
                included_labels.append(label)

        if not included_labels:
            return [], missing_labels

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as handle:
            writer.write(handle)
        return included_labels, missing_labels

    def _open_pdf_with_default_viewer(self, pdf_path: Path) -> bool:
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path.resolve())))

    def print_export_dialog(self) -> None:
        if not self.data or not self.jurisdiction_key:
            QMessageBox.information(
                self,
                "Nothing to Print",
                "Start a new return or import an existing return first.",
            )
            return
        if PdfReader is None or PdfWriter is None:
            QMessageBox.warning(
                self,
                "PDF Export Unavailable",
                "Install the PDF dependencies from requirements.txt to assemble printable PDF packages.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Print / Export PDF")
        dialog.resize(760, 520)

        layout = QVBoxLayout(dialog)
        instructions = QLabel(
            "Choose which documents to assemble into one PDF. "
            "The app will open the merged PDF in your default system PDF viewer."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        filing_radio = QRadioButton("1040 for filing")
        filing_radio.setChecked(True)
        all_radio = QRadioButton("All documents")
        custom_radio = QRadioButton("Select forms...")
        layout.addWidget(filing_radio)
        layout.addWidget(all_radio)
        layout.addWidget(custom_radio)

        list_label = QLabel("Select one or more documents:")
        layout.addWidget(list_label)

        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        custom_sheet_ids = self._all_export_sheet_ids()
        for sheet_id in custom_sheet_ids:
            item = QListWidgetItem(self._sheet_label(sheet_id))
            item.setData(Qt.UserRole, sheet_id)
            list_widget.addItem(item)
        list_widget.setEnabled(False)
        list_label.setEnabled(False)
        layout.addWidget(list_widget, stretch=1)

        def sync_custom_state() -> None:
            enabled = custom_radio.isChecked()
            list_widget.setEnabled(enabled)
            list_label.setEnabled(enabled)

        filing_radio.toggled.connect(sync_custom_state)
        all_radio.toggled.connect(sync_custom_state)
        custom_radio.toggled.connect(sync_custom_state)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        package_kind = "filing"
        if all_radio.isChecked():
            sheet_ids = self._all_export_sheet_ids()
            package_kind = "all_documents"
        elif custom_radio.isChecked():
            sheet_ids = [item.data(Qt.UserRole) for item in list_widget.selectedItems() if item.data(Qt.UserRole)]
            package_kind = "custom_selection"
            if not sheet_ids:
                QMessageBox.information(self, "No Documents Selected", "Select one or more forms or documents to export.")
                return
        else:
            sheet_ids = self._filing_export_sheet_ids()

        if not sheet_ids:
            QMessageBox.information(self, "No Documents Available", "There are no documents available for that print option yet.")
            return

        base_name = self.current_path.stem if self.current_path is not None else "opentax_return"
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self._export_pdf_dir() / f"{base_name}_{package_kind}_{timestamp}.pdf"

        try:
            included_labels, missing_labels = self._build_pdf_package(sheet_ids, output_path)
        except Exception as exc:
            QMessageBox.critical(self, "PDF Export Failed", f"Could not assemble the PDF package:\n{exc}")
            return

        if not included_labels:
            QMessageBox.information(
                self,
                "No PDFs Available",
                "None of the selected documents currently have a printable PDF source.",
            )
            return

        opened = self._open_pdf_with_default_viewer(output_path)
        if opened:
            self.statusBar().showMessage(f"Opened {output_path.name} in the default PDF viewer.", 5000)
        else:
            self.statusBar().showMessage(f"Saved PDF package to {output_path}", 5000)

        if missing_labels:
            missing_preview = "\n".join(f"- {label}" for label in missing_labels[:12])
            more_note = ""
            if len(missing_labels) > 12:
                more_note = f"\n...and {len(missing_labels) - 12} more."
            QMessageBox.information(
                self,
                "PDF Package Created With Omissions",
                f"The merged PDF was created at:\n{output_path}\n\n"
                f"Some selected documents were skipped because no printable PDF source is available:\n{missing_preview}{more_note}",
            )
            return

        if not opened:
            QMessageBox.information(
                self,
                "PDF Package Created",
                f"The merged PDF was created at:\n{output_path}\n\n"
                "The default PDF viewer could not be opened automatically.",
            )

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

    def _remove_block_entry(self, parent_form_id: str, block_id: str, entry_index: int) -> bool:
        form_data = self._current_jurisdiction().get(parent_form_id) or {}
        block = (form_data.get("blocks") or {}).get(block_id) or {}
        entries = block.get("entries") or []
        if not isinstance(entries, list) or not (0 <= entry_index < len(entries)):
            return False
        entries.pop(entry_index)
        return True

    def remove_info_return(self) -> None:
        sheet_id = self._current_visible_sheet_id()
        if not sheet_id:
            return
        sheet_type, parent_form_id, block_id = self._parse_sheet_id(sheet_id)
        if sheet_type != "block" or block_id is None:
            QMessageBox.information(
                self,
                "Remove Info Return",
                "Select an information-return sheet first, then choose the entry to remove.",
            )
            return

        entry_index = self._current_block_preview_entry_index(parent_form_id, block_id)
        if not self._remove_block_entry(parent_form_id, block_id, entry_index):
            QMessageBox.information(self, "Remove Info Return", "There is no selected information-return entry to remove.")
            return

        self.recalculate_all()
        self._refresh_sheet_list(select_sheet_id=sheet_id)
        self._refresh_current_sheet()
        self.statusBar().showMessage(f"Removed {block_id} entry #{entry_index + 1}", 4000)

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
        '''Store a form-cell edit, update override state, and recalculate if needed.'''
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

    def _on_tri_state_widget_changed(self, form_id: str, cell_id: str, selected_value: Any, checked: bool) -> None:
        if self._populating_table or not checked:
            return
        self._commit_cell_value(form_id, cell_id, selected_value)

    def _on_tri_state_checkbox_changed(self, form_id: str, cell_id: str, selected_value: Any, checked: bool) -> None:
        if self._populating_table:
            return
        current_value = (self._get_form_cell(form_id, cell_id) or {}).get("value")
        if checked:
            self._commit_cell_value(form_id, cell_id, selected_value)
            return
        if current_value is selected_value:
            self._commit_cell_value(form_id, cell_id, None)

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

        if format_code == TRI_STATE_BOOLEAN_FORMAT:
            return value is not None

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
        if format_code in {"boolean", TRI_STATE_BOOLEAN_FORMAT}:
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
        '''Evaluate the project equation language inside a controlled helper sandbox.'''
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
            r"\b(\w+)\.(\w+)\.(\d+)\.(\w+)\b",
            lambda m: f'__crossblockitem__("{m.group(1)}","{m.group(2)}",{m.group(3)},"{m.group(4)}")',
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
            "abs",
            "age_on_date",
            "block_has_entries",
            "capital_gain_threshold",
            "capital_loss_limit",
            "__blocksum__",
            "__crossblocksum__",
            "__crossblockitem__",
            "__blockitem__",
            "__ref__",
            "__self__",
            "ceil",
            "crossblockcount_match",
            "crossblocksum_date_range",
            "capital_direct_schedule_d_total",
            "crossblocksum_match",
            "eic_lookup",
            "f8949_preview_checkbox",
            "f8949_preview_row_value",
            "f8949_preview_total",
            "f2441_applicable_percentage",
            "f2441_earned_income",
            "f2441_expense_limit",
            "f2441_qualified_expenses_total",
            "f2441_qualifying_person_count",
            "f8962_allocation_row_value",
            "f8962_allocation_rows_fit_on_form",
            "f8962_has_policy_allocations",
            "f8962_monthly_contribution_amount",
            "f8962_policy_annual_total",
            "f8962_policy_month_total",
            "f8962_policy_monthly_data_present",
            "f1116_total_credit",
            "f2210_penalty",
            "floor",
            "form_has_meaningful_values",
            "form_has_user_activity",
            "is_answered",
            "is_no",
            "is_yes",
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

        def crossblockitem(target_form_id: str, block_id: str, index: int, field_name: str) -> Any:
            form_data = self._current_jurisdiction().get(target_form_id) or {}
            block = (form_data.get("blocks") or {}).get(block_id)
            if not isinstance(block, dict):
                return None
            entries = block.get("entries") or []
            if not isinstance(index, int) or index < 0 or index >= len(entries):
                return None
            entry = entries[index]
            if not isinstance(entry, dict):
                return None
            return entry.get(field_name)

        def block_has_entries(target_form_id: str, block_id: str) -> bool:
            return self._block_has_entries(target_form_id, block_id)

        def form_has_user_activity(target_form_id: str) -> bool:
            target_form = self._current_jurisdiction().get(target_form_id) or {}
            return self._form_has_user_activity(target_form_id, target_form)

        def form_has_meaningful_values(target_form_id: str) -> bool:
            target_form = self._current_jurisdiction().get(target_form_id) or {}
            return self._form_has_meaningful_values(target_form)

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

        def f8962_policy_month_total(amount_kind: str, month_number: Any) -> float:
            if amount_kind not in {"enrollment_premiums", "slcsp", "advance_ptc"}:
                return 0.0
            return self._f8962_policy_month_total(amount_kind, month_number)

        def f8962_policy_annual_total(amount_kind: str) -> float:
            if amount_kind not in {"enrollment_premiums", "slcsp", "advance_ptc"}:
                return 0.0
            return self._f8962_policy_annual_total(amount_kind)

        def f8962_policy_monthly_data_present() -> bool:
            return self._f8962_policy_monthly_data_present()

        def f8962_has_policy_allocations() -> bool:
            return self._f8962_has_policy_allocations()

        def f8962_allocation_row_value(row_number: Any, field_name: str) -> Any:
            return self._f8962_allocation_row_value(row_number, field_name)

        def f8962_allocation_rows_fit_on_form() -> bool:
            return self._f8962_allocation_rows_fit_on_form()

        def f8962_monthly_contribution_amount(month_number: Any) -> float:
            return self._f8962_monthly_contribution_amount(month_number)

        def f2441_qualifying_person_count() -> int:
            return self._f2441_qualifying_person_count()

        def f2441_qualified_expenses_total() -> float:
            return self._f2441_qualified_expenses_total()

        def f2441_expense_limit() -> float:
            return self._f2441_expense_limit()

        def f2441_earned_income(recipient: str) -> float:
            return self._f2441_earned_income(str(recipient))

        def f2441_applicable_percentage() -> float:
            return self._f2441_applicable_percentage()

        def f8949_preview_checkbox(block_id: str) -> bool:
            return self._f8949_preview_checkbox(str(block_id))

        def f8949_preview_row_value(section: str, row_number: Any, field_name: str) -> Any:
            return self._f8949_preview_row_value(str(section), row_number, str(field_name))

        def f8949_preview_total(section: str, column: str) -> Any:
            return self._f8949_preview_total(str(section), str(column))

        def f1116_total_credit() -> float:
            if bool(self._cell_value("f1116", "elect_credit_without_form_1116")):
                try:
                    return float(self._evaluate_cell("f1116", "35", set(stack), respect_overrides=respect_overrides) or 0.0)
                except (TypeError, ValueError):
                    return 0.0
            total = 0.0
            for category in F1116_CATEGORY_DEFINITIONS:
                try:
                    total += float(
                        self._evaluate_cell(
                            f"f1116_{category['suffix']}",
                            "35",
                            set(stack),
                            respect_overrides=respect_overrides,
                        )
                        or 0.0
                    )
                except (TypeError, ValueError):
                    continue
            return round(total, 2)

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

        def is_yes(value: Any) -> bool:
            return value is True

        def is_no(value: Any) -> bool:
            return value is False

        def is_answered(value: Any) -> bool:
            return value is not None

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

        def schedule_b_interest_name(index: Any) -> str:
            try:
                return self._schedule_b_row_name("interest", int(index))
            except (TypeError, ValueError):
                return ""

        def schedule_b_interest_amount(index: Any) -> float:
            try:
                return self._schedule_b_row_value("interest", int(index))
            except (TypeError, ValueError):
                return 0.0

        def schedule_b_interest_auto_total() -> float:
            return self._schedule_b_total("interest")

        def schedule_b_dividend_name(index: Any) -> str:
            try:
                return self._schedule_b_row_name("dividend", int(index))
            except (TypeError, ValueError):
                return ""

        def schedule_b_dividend_amount(index: Any) -> float:
            try:
                return self._schedule_b_row_value("dividend", int(index))
            except (TypeError, ValueError):
                return 0.0

        def schedule_b_dividend_auto_total() -> float:
            return self._schedule_b_total("dividend")

        eval_globals = {
            "__builtins__": {},
            "__blocksum__": blocksum,
            "__crossblocksum__": crossblocksum,
                "__crossblockitem__": crossblockitem,
            "__blockitem__": blockitem,
            "__ref__": ref,
            "__self__": self_ref,
            "abs": abs,
            "age_on_date": age_on_date,
            "block_has_entries": block_has_entries,
            "capital_gain_threshold": capital_gain_threshold,
            "capital_loss_limit": capital_loss_limit,
            "ceil": math.ceil,
            "capital_direct_schedule_d_total": capital_direct_schedule_d_total,
            "crossblockcount_match": crossblockcount_match,
            "crossblocksum_date_range": crossblocksum_date_range,
            "crossblocksum_match": crossblocksum_match,
            "eic_lookup": eic_lookup,
            "f8949_preview_checkbox": f8949_preview_checkbox,
            "f8949_preview_row_value": f8949_preview_row_value,
            "f8949_preview_total": f8949_preview_total,
            "f2441_applicable_percentage": f2441_applicable_percentage,
            "f2441_earned_income": f2441_earned_income,
            "f2441_expense_limit": f2441_expense_limit,
            "f2441_qualified_expenses_total": f2441_qualified_expenses_total,
            "f2441_qualifying_person_count": f2441_qualifying_person_count,
            "f8962_allocation_row_value": f8962_allocation_row_value,
            "f8962_allocation_rows_fit_on_form": f8962_allocation_rows_fit_on_form,
            "f8962_has_policy_allocations": f8962_has_policy_allocations,
            "f8962_monthly_contribution_amount": f8962_monthly_contribution_amount,
            "f8962_policy_annual_total": f8962_policy_annual_total,
            "f8962_policy_month_total": f8962_policy_month_total,
            "f8962_policy_monthly_data_present": f8962_policy_monthly_data_present,
            "f1116_total_credit": f1116_total_credit,
            "f2210_penalty": f2210_penalty,
            "floor": math.floor,
            "form_has_meaningful_values": form_has_meaningful_values,
            "form_has_user_activity": form_has_user_activity,
            "is_answered": is_answered,
            "is_no": is_no,
            "is_yes": is_yes,
            "max_zero": max_zero,
            "min": min,
            "max": max,
            "schedule_b_dividend_amount": schedule_b_dividend_amount,
            "schedule_b_dividend_auto_total": schedule_b_dividend_auto_total,
            "schedule_b_dividend_name": schedule_b_dividend_name,
            "schedule_b_interest_amount": schedule_b_interest_amount,
            "schedule_b_interest_auto_total": schedule_b_interest_auto_total,
            "schedule_b_interest_name": schedule_b_interest_name,
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
        '''Resolve one cell value, including overrides and form-specific shortcuts.'''
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
        if form_id == "f8615" and cell_id == "age_support_test_met":
            result = self._f8615_age_support_test_met()
            self._evaluation_cache[cache_key] = result
            return result
        if form_id == "f8615" and cell_id == "required_to_file":
            result = self._f8615_required_to_file()
            self._evaluation_cache[cache_key] = result
            return result
        if form_id == "f1040" and cell_id == "2b":
            adjustment = self._cell_amount("f1040sb", "2")
            result = round(self._schedule_b_total("interest") + adjustment, 2)
            self._evaluation_cache[cache_key] = result
            return result
        if form_id == "f1040" and cell_id == "3b":
            adjustment = self._cell_amount("f1040sb", "5")
            result = round(self._schedule_b_total("dividend") + adjustment, 2)
            self._evaluation_cache[cache_key] = result
            return result
        if form_id == "f1040sb":
            interest_name_match = re.fullmatch(r"line_1_payer_(\d+)", cell_id)
            if interest_name_match:
                result = self._schedule_b_row_name("interest", int(interest_name_match.group(1)))
                self._evaluation_cache[cache_key] = result
                return result
            interest_amount_match = re.fullmatch(r"line_1_amount_(\d+)", cell_id)
            if interest_amount_match:
                result = self._schedule_b_row_display_value("interest", int(interest_amount_match.group(1)))
                self._evaluation_cache[cache_key] = result
                return result
            dividend_name_match = re.fullmatch(r"line_4_payer_(\d+)", cell_id)
            if dividend_name_match:
                result = self._schedule_b_row_name("dividend", int(dividend_name_match.group(1)))
                self._evaluation_cache[cache_key] = result
                return result
            dividend_amount_match = re.fullmatch(r"line_4_amount_(\d+)", cell_id)
            if dividend_amount_match:
                result = self._schedule_b_row_display_value("dividend", int(dividend_amount_match.group(1)))
                self._evaluation_cache[cache_key] = result
                return result
            if cell_id == "1":
                result = self._schedule_b_total("interest")
                self._evaluation_cache[cache_key] = result
                return result
            if cell_id == "4":
                result = self._schedule_b_total("dividend")
                self._evaluation_cache[cache_key] = result
                return result
        if form_id == "f1040se":
            passthrough_match = re.fullmatch(
                r"passthrough_(\d+)_(name|category|income_or_loss|nonpassive|qbi_income_or_loss)",
                cell_id,
            )
            if passthrough_match:
                result = self._schedule_e_passthrough_row_value(
                    int(passthrough_match.group(1)),
                    passthrough_match.group(2),
                )
                self._evaluation_cache[cache_key] = result
                return result
        if form_id == "f8283":
            item_match = re.fullmatch(
                r"section_a_item_(\d+)_(description|donee_name|contribution_date|claimed_amount|section_b_candidate)",
                cell_id,
            )
            if item_match:
                result = self._form_8283_row_value(
                    int(item_match.group(1)),
                    item_match.group(2),
                )
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
        '''Recompute formula-backed cells, then refresh visible sheets and UI state.'''
        if not self.jurisdiction_key:
            return
        self._evaluation_cache.clear()
        self._sync_f1116_category_from_questionnaire()
        jdata = self._current_jurisdiction()
        for form_id, form_data in sorted(self._available_forms(), key=_form_sort_key):
            cells = form_data.get("cells") or {}
            for cell_id, cell in sorted(cells.items(), key=_cell_sort_key):
                if not isinstance(cell, dict):
                    continue
                uses_custom_evaluation = self._cell_uses_custom_evaluation(form_id, cell_id)
                if not cell.get("equation") and not uses_custom_evaluation:
                    continue
                computed = self._evaluate_cell(form_id, cell_id, set())
                if detect_existing_overrides and cell.get("override_possible", False) and cell.get("equation"):
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
        self._ensure_activated_block_entries()
        self._evaluation_cache.clear()
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
        '''Load one visible sheet into the table and refresh the PDF preview.'''
        self._hide_value_cell_info_popup()
        sheet_type, primary_id, secondary_id = self._parse_sheet_id(sheet_id)
        if sheet_type == "block" and secondary_id:
            self.populate_block_sheet(primary_id, secondary_id)
        else:
            self.populate_form(primary_id)
        self._sync_preview_highlight_to_selection()
        self._update_pdf_preview()

    def populate_form(self, form_id: str) -> None:
        '''Render a normal form sheet as one row per cell in authored order.'''
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
                uses_tri_state_widget = format_code == TRI_STATE_BOOLEAN_FORMAT and is_editable
                uses_choice_widget = uses_boolean_widget or uses_tri_state_widget
                row_dimmed = self._should_dim_choice_row(form_id, cell_id, cell)
                value_required_highlight = self._should_highlight_required_value(form_id, cell_id, cell)
                validation_error = self._format_validation_error(cell_id, cell)
                displayed_value = value_text
                if format_code == "boolean" and not uses_boolean_widget:
                    displayed_value = "✓" if bool(cell.get("value")) else ""

                values = [
                    cell_id,
                    description,
                    "" if uses_choice_widget else displayed_value,
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
                    if col_idx == VALUE_COLUMN_INDEX and is_editable and not uses_choice_widget:
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
                    if col_idx == VALUE_COLUMN_INDEX:
                        item.setData(Qt.UserRole, ("form", form_id, cell_id))
                    self.table.setItem(row_idx, col_idx, item)

                if uses_choice_widget:
                    widget_container = QWidget()
                    widget_layout = QHBoxLayout()
                    widget_layout.setContentsMargins(6, 0, 6, 0)
                    widget_layout.setAlignment(Qt.AlignCenter)

                    if value_required_highlight:
                        widget_container.setStyleSheet(
                            f"background-color: {REQUIRED_BACKGROUND.name()}; border: 1px solid {INCOMPLETE_SHEET_TEXT.name()}; border-radius: 4px;"
                        )
                    elif row_dimmed:
                        widget_container.setStyleSheet(
                            f"background-color: {DIMMED_ROW_BACKGROUND.name()}; color: {DIMMED_ROW_TEXT.name()};"
                        )
                    widget_container.setFocusPolicy(Qt.StrongFocus)
                    widget_container.setProperty("cell_ref", ("form", form_id, cell_id))
                    widget_container.installEventFilter(self)
                    if uses_tri_state_widget:
                        current_value = cell.get("value")
                        for label, selected_value in (("Yes", True), ("No", False)):
                            control = QCheckBox(label)
                            control.setChecked(current_value is selected_value)
                            control.setEnabled(is_editable)
                            if is_editable:
                                control.toggled.connect(
                                    lambda checked, current_form_id=form_id, current_cell_id=cell_id, current_value=selected_value: self._on_tri_state_checkbox_changed(
                                        current_form_id,
                                        current_cell_id,
                                        current_value,
                                        checked,
                                    )
                                )
                            control.setProperty("cell_ref", ("form", form_id, cell_id))
                            control.installEventFilter(self)
                            widget_layout.addWidget(control)
                    else:
                        radio_group = self._radio_group_members(form_id, cell_id)
                        control = QCheckBox()
                        control.setChecked(bool(cell.get("value")))
                        control.setEnabled(is_editable)
                        if is_editable:
                            control.toggled.connect(
                                lambda checked, current_form_id=form_id, current_cell_id=cell_id: self._on_boolean_widget_changed(
                                    current_form_id,
                                    current_cell_id,
                                    checked,
                                )
                            )
                        control.setProperty("cell_ref", ("form", form_id, cell_id))
                        control.installEventFilter(self)
                        widget_layout.addWidget(control)
                    widget_container.setLayout(widget_layout)
                    self.table.setCellWidget(row_idx, VALUE_COLUMN_INDEX, widget_container)
            self._focus_value_column()
        finally:
            self._populating_table = False

    def populate_block_sheet(self, parent_form_id: str, block_id: str) -> None:
        '''Render a repeating information-return block as entry-indexed table rows.'''
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
                    if col_idx == VALUE_COLUMN_INDEX:
                        item.setData(Qt.UserRole, ("block", parent_form_id, block_id, entry_index, field_id))
                    self.table.setItem(row_idx, col_idx, item)

                if uses_boolean_widget or uses_taxpayer_spouse_widget:
                    cell_ref = ("block", parent_form_id, block_id, entry_index, field_id)
                    widget_container = QWidget()
                    widget_layout = QHBoxLayout()
                    widget_layout.setContentsMargins(6, 0, 6, 0)
                    widget_layout.setAlignment(Qt.AlignCenter)
                    widget_container.setFocusPolicy(Qt.StrongFocus)
                    widget_container.setProperty("cell_ref", cell_ref)
                    widget_container.installEventFilter(self)
                    if value_required_highlight:
                        widget_container.setStyleSheet(
                            f"background-color: {REQUIRED_BACKGROUND.name()};"
                        )
                    if uses_taxpayer_spouse_widget:
                        current_recipient = self._normalize_taxpayer_spouse_value(raw_value)
                        taxpayer_button = QRadioButton("T")
                        spouse_button = QRadioButton("S")
                        taxpayer_button.setProperty("cell_ref", cell_ref)
                        spouse_button.setProperty("cell_ref", cell_ref)
                        taxpayer_button.installEventFilter(self)
                        spouse_button.installEventFilter(self)
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
                        control.setProperty("cell_ref", cell_ref)
                        control.installEventFilter(self)
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
        if current_column == VALUE_COLUMN_INDEX:
            self._sync_preview_highlight_to_selection()
            self._update_pdf_preview()
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
        if format_code == TRI_STATE_BOOLEAN_FORMAT:
            return value is not None
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
        '''Store one block-field edit and recalculate dependent form values.'''
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
    '''Launch the Qt editor, optionally preloading a return file.'''
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
