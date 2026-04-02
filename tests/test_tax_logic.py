import os
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional in some runtimes
    PdfReader = None

from src.main import INCOMPLETE_SHEET_TEXT, REQUIRED_BACKGROUND, SOURCE_SHEET_FLASH_BACKGROUND, TaxSheetEditor
from src.pdf_preview import FormPdfPreviewEngine


def get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TaxLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = get_app()

    def make_editor(self) -> TaxSheetEditor:
        editor = TaxSheetEditor()
        editor.new_return()
        return editor

    def add_block_entry(self, editor: TaxSheetEditor, block_id: str, values: dict) -> None:
        self.add_block_entry_on_form(editor, "f1040", block_id, values)

    def add_block_entry_on_form(self, editor: TaxSheetEditor, parent_form_id: str, block_id: str, values: dict) -> None:
        entry_number = editor._append_blank_block_entry(parent_form_id, block_id)
        self.assertIsNotNone(entry_number)
        entry_index = int(entry_number) - 1
        for field_id, value in values.items():
            editor._commit_block_value(parent_form_id, block_id, entry_index, field_id, value)

    def find_first_row_for_entry(self, editor: TaxSheetEditor, entry_number: int) -> int:
        prefix = f"{entry_number}."
        for row_idx in range(editor.table.rowCount()):
            row_item = editor.table.item(row_idx, 0)
            if row_item is not None and row_item.text().startswith(prefix):
                return row_idx
        self.fail(f"Could not find table row for block entry {entry_number}.")

    def test_age_fields_compute_from_dob(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Federal_Info_Worksheet", "taxpayer_dob", "1982-04-12")
        editor._commit_cell_value("f1040_Federal_Info_Worksheet", "spouse_dob", "1984-09-03")

        self.assertEqual(editor._get_form_cell("f1040_Federal_Info_Worksheet", "taxpayer_age_1_1_2026")["value"], 43)
        self.assertEqual(editor._get_form_cell("f1040_Federal_Info_Worksheet", "spouse_age_1_1_2026")["value"], 41)

    def test_date_range_payment_equations_with_quoted_dates(self) -> None:
        editor = self.make_editor()
        for payment_date, amount in [
            ("2025-03-15", 100.0),
            ("2025-05-20", 200.0),
            ("2025-10-01", 300.0),
            ("2026-01-10", 400.0),
        ]:
            self.add_block_entry(
                editor,
                "estimated_tax_payments_detail",
                {"recipient": "taxpayer", "payment_date": payment_date, "amount": amount, "payment_type": "estimated"},
            )

        self.assertEqual(editor._get_form_cell("f1040", "26")["value"], 600.0)
        self.assertEqual(editor._get_form_cell("f2210", "estimated_payment_period_a")["value"], 100.0)
        self.assertEqual(editor._get_form_cell("f2210", "estimated_payment_period_b")["value"], 200.0)
        self.assertEqual(editor._get_form_cell("f2210", "estimated_payment_period_c")["value"], 0.0)
        self.assertEqual(editor._get_form_cell("f2210", "estimated_payment_period_d")["value"], 700.0)

    def test_salt_cap_standard_mfj_case(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040", "11b", 400000.0)
        editor._commit_cell_value("f1040sa", "5a", 18000.0)
        editor._commit_cell_value("f1040sa", "5b", 17000.0)
        editor._commit_cell_value("f1040sa", "5c", 15000.0)

        self.assertEqual(editor._get_form_cell("f1040sa", "5d")["value"], 50000.0)
        self.assertEqual(editor._get_form_cell("f1040sa", "5e")["value"], 40000.0)

    def test_salt_phaseout_with_excluded_income(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040", "11b", 480000.0)
        editor._commit_cell_value("f1040s1a", "2a", 50000.0)
        editor._commit_cell_value("f1040sa", "5a", 25000.0)
        editor._commit_cell_value("f1040sa", "5b", 15000.0)
        editor._commit_cell_value("f1040sa", "5c", 10000.0)

        self.assertEqual(editor._get_form_cell("f1040s1a", "3")["value"], 530000.0)
        self.assertEqual(editor._get_form_cell("f1040sa", "5e")["value"], 31000.0)

    def test_salt_phaseout_mfs_uses_half_of_post_floor_result(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Federal_Info_Worksheet", "filing_status_married_separately", True)
        editor._commit_cell_value("f1040", "11b", 300000.0)
        editor._commit_cell_value("f1040sa", "5a", 18000.0)
        editor._commit_cell_value("f1040sa", "5b", 12000.0)
        editor._commit_cell_value("f1040sa", "5c", 5000.0)

        self.assertEqual(editor._get_form_cell("f1040sa", "5d")["value"], 35000.0)
        self.assertEqual(editor._get_form_cell("f1040sa", "5e")["value"], 12500.0)

    def test_schedule_1a_line_2b_flows_from_form_2555(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f2555", "foreign_earned_income_exclusion", 12345.0)

        self.assertEqual(editor._get_form_cell("f1040s1a", "2b")["value"], 12345.0)
        self.assertEqual(editor._get_form_cell("f1040s1a", "2e")["value"], 12345.0)

    def test_clearing_override_restores_formula_value(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040sa", "5a", 18000.0)
        editor._commit_cell_value("f1040sa", "5b", 17000.0)
        editor._commit_cell_value("f1040sa", "5c", 15000.0)
        self.assertEqual(editor._get_form_cell("f1040sa", "5e")["value"], 40000.0)

        editor._commit_cell_value("f1040sa", "5e", 12345.0)
        self.assertIn(("f1040sa", "5e"), editor.overridden_cells)
        self.assertEqual(editor._get_form_cell("f1040sa", "5e")["value"], 12345.0)

        editor._clear_override_value("f1040sa", "5e")
        self.assertNotIn(("f1040sa", "5e"), editor.overridden_cells)
        self.assertEqual(editor._get_form_cell("f1040sa", "5e")["value"], 40000.0)

    def test_1099r_gross_flows_to_ira_and_pension_lines(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1099_r",
            {"recipient": "taxpayer", "payer_name": "IRA Custodian", "box_1": 10000.0, "ira_sep_simple": True},
        )
        self.add_block_entry(
            editor,
            "1099_r",
            {"recipient": "spouse", "payer_name": "Pension Plan", "box_1": 12000.0, "ira_sep_simple": False},
        )

        self.assertEqual(editor._get_form_cell("f1040", "4a")["value"], 10000.0)
        self.assertEqual(editor._get_form_cell("f1040", "5a")["value"], 12000.0)

    def test_f4952_line_4g_defaults_election_from_4e_then_4b(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1099_div",
            {"recipient": "taxpayer", "payer_name": "Fund", "box_1a": 1000.0, "box_1b": 300.0, "box_2a": 200.0},
        )
        editor._commit_cell_value("f4952", "line_4g_total_elected", 350.0)

        self.assertEqual(editor._get_form_cell("f4952", "4b")["value"], 300.0)
        self.assertEqual(editor._get_form_cell("f4952", "4e")["value"], 200.0)
        self.assertEqual(editor._get_form_cell("f4952", "line_4g_default_from_4e")["value"], 200.0)
        self.assertEqual(editor._get_form_cell("f4952", "line_4g_default_from_4b")["value"], 150.0)
        self.assertEqual(editor._get_form_cell("f4952", "4g")["value"], 350.0)
        self.assertEqual(editor._get_form_cell("f1040sd_Schedule_D_Tax", "3")["value"], 350.0)

    def test_f4952_line_4g_manual_split_overrides_default_allocation(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1099_div",
            {"recipient": "taxpayer", "payer_name": "Fund", "box_1a": 1000.0, "box_1b": 300.0, "box_2a": 200.0},
        )
        editor._commit_cell_value("f4952", "line_4g_total_elected", 350.0)
        editor._commit_cell_value("f4952", "line_4g_use_manual_split", True)
        editor._commit_cell_value("f4952", "line_4g_elected_from_4e", 50.0)
        editor._commit_cell_value("f4952", "line_4g_elected_from_4b", 250.0)

        self.assertEqual(editor._get_form_cell("f4952", "line_4g_default_from_4e")["value"], 200.0)
        self.assertEqual(editor._get_form_cell("f4952", "line_4g_default_from_4b")["value"], 150.0)
        self.assertEqual(editor._get_form_cell("f4952", "4g")["value"], 300.0)
        self.assertEqual(editor._get_form_cell("f1040sd_Schedule_D_Tax", "3")["value"], 300.0)

    def test_f4952_filing_exception_matches_interest_and_dividend_rule(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "investment_interest_expense",
            {"recipient": "taxpayer", "lender_name": "Broker", "description": "Margin interest", "amount": 100.0},
        )
        self.add_block_entry(
            editor,
            "1099_int",
            {"recipient": "taxpayer", "payer_name": "Bank", "box_1": 250.0},
        )
        self.add_block_entry(
            editor,
            "1099_div",
            {"recipient": "taxpayer", "payer_name": "Fund", "box_1a": 100.0, "box_1b": 20.0},
        )

        self.assertEqual(editor._get_form_cell("f4952", "filing_exception_interest_and_dividend_income")["value"], 330.0)
        self.assertTrue(editor._get_form_cell("f4952", "filing_exception_met")["value"])
        self.assertNotIn("f4952", editor._filed_form_ids())

    def test_f4952_filing_exception_does_not_count_passive_1099_misc_royalties(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "investment_interest_expense",
            {"recipient": "taxpayer", "lender_name": "Broker", "description": "Margin interest", "amount": 100.0},
        )
        self.add_block_entry(
            editor,
            "1099_misc",
            {"recipient": "taxpayer", "payer_name": "Royalty Payor", "box_2": 1000.0},
        )
        editor._commit_cell_value("f1040_Federal_Info_Worksheet", "include_passive_1099_misc_box_2_in_f4952_line_4a", True)

        self.assertEqual(editor._get_form_cell("f4952", "4a")["value"], 1000.0)
        self.assertEqual(editor._get_form_cell("f4952", "filing_exception_interest_and_dividend_income")["value"], 0.0)
        self.assertFalse(editor._get_form_cell("f4952", "filing_exception_met")["value"])
        self.assertIn("f4952", editor._filed_form_ids())

    def test_f4952_carryforward_records_only_count_prior_tax_year(self) -> None:
        editor = self.make_editor()
        self.add_block_entry_on_form(
            editor,
            "f8949",
            "carryforward_records",
            {"recipient": "taxpayer", "tax_year": "2024", "target_form": "f4952", "target_line": "7", "amount": 125.0},
        )
        self.add_block_entry_on_form(
            editor,
            "f8949",
            "carryforward_records",
            {"recipient": "taxpayer", "tax_year": "2025", "target_form": "f4952", "target_line": "7", "amount": 999.0},
        )

        self.assertEqual(editor._get_form_cell("f4952", "carryforward_records_line_2_total")["value"], 125.0)
        self.assertEqual(editor._get_form_cell("f4952", "2")["value"], 125.0)

    def test_f1116_carryforward_records_only_count_prior_tax_year(self) -> None:
        editor = self.make_editor()
        self.add_block_entry_on_form(
            editor,
            "f8949",
            "carryforward_records",
            {"recipient": "taxpayer", "tax_year": "2024", "target_form": "f1116", "target_line": "10", "category": "passive", "amount": 60.0},
        )
        self.add_block_entry_on_form(
            editor,
            "f8949",
            "carryforward_records",
            {"recipient": "taxpayer", "tax_year": "2025", "target_form": "f1116", "target_line": "10", "category": "passive", "amount": 500.0},
        )
        editor._commit_cell_value("f1116", "elect_credit_without_form_1116", False)

        self.assertEqual(editor._get_form_cell("f1116", "category_carryforward_records_total")["value"], 60.0)
        self.assertEqual(editor._get_form_cell("f1116", "10")["value"], 60.0)

    def test_f1116_requires_exactly_one_category_for_category_math(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "k1_1041",
            {
                "recipient": "taxpayer",
                "payer_name": "Family Trust",
                "category": "passive",
                "foreign_source_income": 100.0,
                "foreign_tax_paid": 8.0,
            },
        )
        self.add_block_entry(
            editor,
            "k3_1065",
            {
                "recipient": "taxpayer",
                "payer_name": "Global Partnership",
                "category": "general",
                "foreign_source_income": 200.0,
                "foreign_tax_paid": 14.0,
            },
        )

        editor._commit_cell_value("f1116", "category_general", True)
        editor._commit_cell_value("f1116", "24", 50.0)

        self.assertEqual(editor._get_form_cell("f1116", "category_selection_count")["value"], 2)
        self.assertFalse(editor._get_form_cell("f1116", "category_selection_valid")["value"])
        self.assertEqual(editor._get_form_cell("f1116", "category_gross_income_from_source_block")["value"], 0.0)
        self.assertEqual(editor._get_form_cell("f1116", "category_foreign_tax_from_source_block")["value"], 0.0)
        self.assertEqual(editor._get_form_cell("f1116", "27")["value"], 0.0)
        self.assertEqual(editor._get_form_cell("f1116", "28")["value"], 0.0)

        editor._commit_cell_value("f1116", "category_passive", False)

        self.assertEqual(editor._get_form_cell("f1116", "category_selection_count")["value"], 1)
        self.assertTrue(editor._get_form_cell("f1116", "category_selection_valid")["value"])
        self.assertEqual(editor._get_form_cell("f1116", "category_gross_income_from_source_block")["value"], 200.0)
        self.assertEqual(editor._get_form_cell("f1116", "category_foreign_tax_from_source_block")["value"], 14.0)
        self.assertEqual(editor._get_form_cell("f1116", "28")["value"], 50.0)

    def test_f1116_line_18_and_20_adjustment_buckets_flow_into_limitation(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040", "15", 10000.0)
        editor._commit_cell_value("f1040", "16", 1500.0)
        editor._commit_cell_value("f1040", "17", 200.0)
        editor._commit_cell_value("f1116", "15", 3000.0)
        editor._commit_cell_value("f2555", "foreign_earned_income_exclusion", 1000.0)
        editor._commit_cell_value("f1116", "line_18_limitation_adjustments", -500.0)
        editor._commit_cell_value("f1116", "line_20_limitation_adjustments", 25.0)

        self.assertTrue(editor._get_form_cell("f1116", "special_limitation_adjustments_likely")["value"])
        self.assertEqual(editor._get_form_cell("f1116", "line_18_base_form_1040")["value"], 10000.0)
        self.assertEqual(editor._get_form_cell("f1116", "18")["value"], 9500.0)
        self.assertEqual(editor._get_form_cell("f1116", "line_20_base_form_1040")["value"], 1700.0)
        self.assertEqual(editor._get_form_cell("f1116", "20")["value"], 1725.0)
        self.assertAlmostEqual(editor._get_form_cell("f1116", "19")["value"], 3000.0 / 9500.0, places=6)
        self.assertAlmostEqual(editor._get_form_cell("f1116", "21")["value"], 1725.0 * (3000.0 / 9500.0), places=6)

    def test_required_tri_state_question_counts_false_as_answered(self) -> None:
        editor = self.make_editor()
        cell = editor._get_form_cell("f1040_Return_Intake_Questions", "has_foreign_income")

        self.assertTrue(editor._should_highlight_required_value("f1040_Return_Intake_Questions", "has_foreign_income", cell))

        editor._commit_cell_value("f1040_Return_Intake_Questions", "has_foreign_income", False)
        cell = editor._get_form_cell("f1040_Return_Intake_Questions", "has_foreign_income")

        self.assertFalse(editor._should_highlight_required_value("f1040_Return_Intake_Questions", "has_foreign_income", cell))
        self.assertTrue(editor._has_present_value("f1040_Return_Intake_Questions", "has_foreign_income", cell))

    def test_foreign_tax_questionnaire_activates_from_general_intake_answer(self) -> None:
        editor = self.make_editor()

        self.assertFalse(editor._form_is_activated_now("f1116_Questionnaire", editor._current_jurisdiction()["f1116_Questionnaire"]))

        editor._commit_cell_value("f1040_Return_Intake_Questions", "has_foreign_income", True)

        self.assertTrue(editor._form_is_activated_now("f1116_Questionnaire", editor._current_jurisdiction()["f1116_Questionnaire"]))

    def test_master_questionnaire_sits_under_federal_info(self) -> None:
        editor = self.make_editor()

        entries = dict(editor._sheet_list_entries(editor._auto_visible_sheet_ids()))

        self.assertEqual(entries["form:f1040_Federal_Info_Worksheet"], 0)
        self.assertEqual(entries["form:f1040_Return_Intake_Questions"], 1)

    def test_master_questionnaire_answers_surface_major_work_areas(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Return_Intake_Questions", "received_marketplace_coverage", True)
        editor._commit_cell_value("f1040_Return_Intake_Questions", "has_self_employment_income_or_expenses", True)

        auto_visible_sheet_ids = editor._auto_visible_sheet_ids()

        self.assertIn("form:f8962", auto_visible_sheet_ids)
        self.assertIn("form:f1040sc", auto_visible_sheet_ids)

    def test_schedule_a_questionnaire_surfaces_from_master_itemize_trigger(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Return_Intake_Questions", "may_itemize_deductions", True)

        auto_visible_sheet_ids = editor._auto_visible_sheet_ids()

        self.assertIn("form:f1040sa_Questionnaire", auto_visible_sheet_ids)
        self.assertIn("form:f1040sa", auto_visible_sheet_ids)

    def test_schedule_a_questionnaire_answers_surface_child_forms(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Return_Intake_Questions", "may_itemize_deductions", True)
        editor._commit_cell_value("f1040sa_Questionnaire", "has_investment_interest_expense", True)

        auto_visible_sheet_ids = editor._auto_visible_sheet_ids()

        self.assertIn("form:f1040sa", auto_visible_sheet_ids)
        self.assertIn("form:f4952", auto_visible_sheet_ids)

    def test_f1116_questionnaire_syncs_categories_when_form_boxes_untouched(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1116_Questionnaire", "has_passive_category_income", False)
        editor._commit_cell_value("f1116_Questionnaire", "has_general_category_income", True)

        self.assertFalse(editor._get_form_cell("f1116", "category_passive")["value"])
        self.assertTrue(editor._get_form_cell("f1116", "category_general")["value"])
        self.assertEqual(editor._get_form_cell("f1116", "category_selection_count")["value"], 1)

    def test_f1116_questionnaire_surfaces_category_copy_forms(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Return_Intake_Questions", "has_foreign_income", True)
        editor._commit_cell_value("f1116_Questionnaire", "has_passive_category_income", True)
        editor._commit_cell_value("f1116_Questionnaire", "has_general_category_income", True)

        auto_visible_sheet_ids = editor._auto_visible_sheet_ids()

        self.assertIn("form:f1116_passive", auto_visible_sheet_ids)
        self.assertIn("form:f1116_general", auto_visible_sheet_ids)

    def test_f1116_questionnaire_does_not_surface_schedule_b_for_reserved_section_951a_box(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Return_Intake_Questions", "has_foreign_income", True)
        editor._commit_cell_value("f1116_Questionnaire", "has_section_951a_category_income", True)
        editor._commit_cell_value("f1116_Questionnaire", "has_prior_year_carryovers", True)

        self.assertNotIn("form:f1116sb_section_951a", editor._auto_visible_sheet_ids())

    def test_f1116_does_not_file_without_foreign_income_facts(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Return_Intake_Questions", "has_foreign_income", False)
        editor._commit_cell_value("f1040_Return_Intake_Questions", "paid_foreign_taxes", True)
        editor._commit_cell_value("f1040_Return_Intake_Questions", "prior_year_foreign_tax_carryovers", True)
        editor._commit_cell_value("f1116_Questionnaire", "has_prior_year_carryovers", True)
        editor._commit_cell_value("f1116", "elect_credit_without_form_1116", False)

        self.assertFalse(editor._should_file_form_now("f1116", editor._current_jurisdiction()["f1116"]))

    def test_f1116_and_schedule_b_file_from_foreign_income_and_carryover_facts(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Return_Intake_Questions", "has_foreign_income", True)
        editor._commit_cell_value("f1040_Return_Intake_Questions", "paid_foreign_taxes", True)
        editor._commit_cell_value("f1116_Questionnaire", "has_passive_category_income", True)
        editor._commit_cell_value("f1116_Questionnaire", "has_prior_year_carryovers", True)
        self.add_block_entry(
            editor,
            "foreign_tax_credit_items",
            {
                "recipient": "taxpayer",
                "category": "passive",
                "country_or_territory": "Canada",
                "gross_income": 1200.0,
                "foreign_tax_paid": 180.0,
                "qualified_payee_statement": False,
            },
        )

        self.assertTrue(editor._should_file_form_now("f1116_passive", editor._current_jurisdiction()["f1116_passive"]))
        self.assertIn("form:f1116sb_passive", editor._auto_visible_sheet_ids())

    def test_schedule3_foreign_tax_credit_sums_1116_copy_forms(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1116_passive", "35", 10.0)
        editor._commit_cell_value("f1116_general", "35", 12.5)

        self.assertEqual(editor._get_form_cell("f1040s3", "1")["value"], 22.5)

    def test_f1116sb_matrix_subtotals_and_totals_compute(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1116sb_passive", "1i", 10.0)
        editor._commit_cell_value("f1116sb_passive", "1ii", 5.0)
        editor._commit_cell_value("f1116sb_passive", "1ix", 7.0)

        self.assertEqual(editor._get_form_cell("f1116sb_passive", "1vii")["value"], 15.0)
        self.assertEqual(editor._get_form_cell("f1116sb_passive", "1viii")["value"], 15.0)
        self.assertEqual(editor._get_form_cell("f1116sb_passive", "1xiv")["value"], 22.0)

    def test_f1116sb_matrix_line3_and_line8_compute(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1116sb_passive", "1i", 100.0)
        editor._commit_cell_value("f1116sb_passive", "2ai", -20.0)
        editor._commit_cell_value("f1116sb_passive", "2bi", 5.0)
        editor._commit_cell_value("f1116sb_passive", "4i", -40.0)
        editor._commit_cell_value("f1116sb_passive", "5i", -10.0)
        editor._commit_cell_value("f1116sb_passive", "6i", 60.0)
        editor._commit_cell_value("f1116sb_passive", "7i", -15.0)

        self.assertEqual(editor._get_form_cell("f1116sb_passive", "3i")["value"], 85.0)
        self.assertEqual(editor._get_form_cell("f1116sb_passive", "8i")["value"], 80.0)

    def test_f1116_copy_line10_uses_schedule_b_matrix_total(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1116sb_passive", "1ix", 50.0)
        editor._commit_cell_value("f1116sb_passive", "2aix", -10.0)

        self.assertEqual(editor._get_form_cell("f1116sb_passive", "3xiv")["value"], 40.0)
        self.assertEqual(editor._get_form_cell("f1116_passive", "10")["value"], 40.0)

    def test_sample_return_regression(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        self.assertEqual(editor._get_form_cell("f1040_Federal_Info_Worksheet", "taxpayer_age_1_1_2026")["value"], 43)
        self.assertEqual(editor._get_form_cell("f1040_Federal_Info_Worksheet", "spouse_age_1_1_2026")["value"], 41)
        self.assertEqual(editor._get_form_cell("f1040", "1a")["value"], 141100.0)
        self.assertEqual(editor._get_form_cell("f1040", "5a")["value"], 12500.0)
        self.assertIn("block:f1040:w2", editor.visible_sheet_ids)
        self.assertIn("form:f1040sa", editor.visible_sheet_ids)

    def test_sample_return_filed_forms_regression(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        self.assertEqual(editor._filed_form_ids(), ["f1040", "f1040sa", "f8812"])

    def test_filing_sequence_metadata_distinguishes_attachments_from_helpers(self) -> None:
        editor = self.make_editor()

        self.assertEqual(editor._current_jurisdiction()["f1040sa"]["_meta"]["filing_sequence"], "07")
        self.assertIsNone(editor._current_jurisdiction()["f7206"]["_meta"]["filing_sequence"])

    def test_activation_rule_surfaces_1040sr_when_print_variant_is_requested(self) -> None:
        editor = self.make_editor()

        self.assertNotIn("form:f1040sr", editor.visible_sheet_ids)

        editor._commit_cell_value("f1040_Federal_Info_Worksheet", "print_1040_sr", True)

        self.assertIn("form:f1040sr", editor.visible_sheet_ids)

    def test_block_activation_rule_can_seed_required_blank_entry(self) -> None:
        editor = self.make_editor()
        w2_block = editor._current_jurisdiction()["f1040"]["blocks"]["w2"]
        w2_block["activation_rule"] = "f1040sj.elect_to_use_schedule_j"
        w2_block["activated_min_entries"] = 1
        editor.recalculate_all()

        self.assertFalse(editor._block_has_entries("f1040", "w2"))
        self.assertNotIn("block:f1040:w2", editor.visible_sheet_ids)

        editor._commit_cell_value("f1040sj", "elect_to_use_schedule_j", True)

        self.assertTrue(editor._block_has_entries("f1040", "w2"))
        self.assertIn("block:f1040:w2", editor.visible_sheet_ids)

    def test_info_return_candidates_only_include_local_previewable_blocks(self) -> None:
        editor = self.make_editor()
        candidate_ids = {(parent_form_id, block_id) for _, parent_form_id, block_id in editor._block_candidates()}

        self.assertIn(("f1040", "w2"), candidate_ids)
        self.assertIn(("f1040", "1099_int"), candidate_ids)
        self.assertIn(("f1040", "1099_oid"), candidate_ids)
        self.assertIn(("f1040", "k1_1041"), candidate_ids)
        self.assertIn(("f1040", "1095_a"), candidate_ids)
        self.assertIn(("f1040", "1099_b"), candidate_ids)
        self.assertNotIn(("f1040", "investment_property_dispositions"), candidate_ids)

    def test_1099_oid_and_k1_sources_flow_into_existing_lines(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1099_oid",
            {"recipient": "taxpayer", "payer_name": "Treasury Desk", "box_1": 50.0, "box_2": 7.0, "box_4": 3.0},
        )
        self.add_block_entry(
            editor,
            "k1_1065",
            {
                "recipient": "taxpayer",
                "payer_name": "Partnership LP",
                "interest_income": 25.0,
                "ordinary_dividends": 40.0,
                "qualified_dividends": 10.0,
                "collectibles_gain": 2.0,
                "unrecaptured_section_1250_gain": 1.0,
                "investment_income_adjustment": 6.0,
                "investment_expense": 4.0,
            },
        )

        self.assertEqual(editor._get_form_cell("f1040", "2b")["value"], 75.0)
        self.assertEqual(editor._get_form_cell("f1040", "3a")["value"], 10.0)
        self.assertEqual(editor._get_form_cell("f1040", "3b")["value"], 40.0)
        self.assertEqual(editor._get_form_cell("f1040sb", "1")["value"], 75.0)
        self.assertEqual(editor._get_form_cell("f1040sb", "4")["value"], 40.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "18")["value"], 7.0)
        self.assertEqual(editor._get_form_cell("f1040", "federal_withholding_from_information_returns_total")["value"], 3.0)
        self.assertEqual(editor._get_form_cell("f1040", "collectibles_gain_distributions_total")["value"], 2.0)
        self.assertEqual(editor._get_form_cell("f1040", "unrecaptured_section_1250_distributions_total")["value"], 1.0)
        self.assertEqual(editor._get_form_cell("f4952", "obvious_1099_investment_income")["value"], 71.0)
        self.assertEqual(editor._get_form_cell("f4952", "obvious_qualified_dividends")["value"], 10.0)
        self.assertEqual(editor._get_form_cell("f4952", "5")["value"], 4.0)

    def test_schedule_b_lists_interest_payers_and_taxable_amounts_from_sample(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        self.assertEqual(editor._get_form_cell("f1040sb", "line_1_payer_1")["value"], "First National Bank")
        self.assertEqual(editor._get_form_cell("f1040sb", "line_1_amount_1")["value"], 392.56)
        self.assertEqual(editor._get_form_cell("f1040sb", "line_1_payer_2")["value"], "Midwest Credit Union")
        self.assertEqual(editor._get_form_cell("f1040sb", "line_1_amount_2")["value"], 210.45)
        self.assertEqual(editor._get_form_cell("f1040sb", "line_1_payer_3")["value"], "")
        self.assertEqual(editor._get_form_cell("f1040sb", "line_1_amount_3")["value"], "")
        self.assertEqual(editor._get_form_cell("f1040sb", "1")["value"], 603.01)
        self.assertEqual(editor._get_form_cell("f1040", "2b")["value"], 603.01)

    def test_k1_and_k3_sources_feed_schedule_d_and_form_1116(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "k1_1041",
            {
                "recipient": "taxpayer",
                "payer_name": "Family Trust",
                "category": "passive",
                "short_term_capital_gain": 11.0,
                "long_term_capital_gain": 22.0,
                "foreign_source_income": 100.0,
                "foreign_tax_paid": 8.0,
                "qualified_payee_statement": True,
                "passive_income_for_election": True,
            },
        )
        self.add_block_entry(
            editor,
            "k3_1065",
            {
                "recipient": "taxpayer",
                "payer_name": "Global Partnership",
                "category": "general",
                "foreign_source_income": 200.0,
                "foreign_tax_paid": 14.0,
            },
        )

        self.assertEqual(editor._get_form_cell("f1040sd", "5")["value"], 11.0)
        self.assertEqual(editor._get_form_cell("f1040sd", "12")["value"], 22.0)
        self.assertEqual(editor._get_form_cell("f1116", "category_gross_income_from_source_block")["value"], 100.0)
        self.assertEqual(editor._get_form_cell("f1116", "category_foreign_tax_from_source_block")["value"], 8.0)
        self.assertEqual(editor._get_form_cell("f1116", "direct_election_total_foreign_tax")["value"], 8.0)

        editor._commit_cell_value("f1116", "category_passive", False)
        editor._commit_cell_value("f1116", "category_general", True)

        self.assertEqual(editor._get_form_cell("f1116", "category_gross_income_from_source_block")["value"], 200.0)
        self.assertEqual(editor._get_form_cell("f1116", "category_foreign_tax_from_source_block")["value"], 14.0)

    def test_new_scaffold_forms_feed_schedule_dependencies(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f2106", "employee_business_expense_deduction", 12.0)
        editor._commit_cell_value("f8824", "schedule_d_4", 9.0)
        editor._commit_cell_value("f8824", "schedule_d_11", 13.0)
        editor._commit_cell_value("f1040sa", "12_manual_component", 1.0)
        editor._commit_cell_value("f8936", "schedule2_1b", 1.0)
        editor._commit_cell_value("f8936", "schedule2_1c", 2.0)
        editor._commit_cell_value("f5405", "annual_installment_repayment", 3.0)
        editor._commit_cell_value("f5405", "accelerated_repayment_amount", 4.0)
        editor._commit_cell_value("f8283", "other_noncash_contributions", 8.0)
        editor._commit_cell_value("f8936", "schedule3_6f", 3.0)
        editor._commit_cell_value("f8936", "schedule3_6m", 4.0)
        editor._commit_cell_value("f4255", "schedule2_1d", 5.0)
        editor._commit_cell_value("f4255", "schedule2_1e", 6.0)
        editor._commit_cell_value("f4255", "schedule2_1f", 7.0)
        editor._commit_cell_value("f4136", "schedule3_12", 8.0)
        editor._commit_cell_value("f8880", "schedule3_4", 9.0)
        editor._commit_cell_value("f8853", "schedule1_8e", 10.0)
        editor._commit_cell_value("f8853", "schedule2_17e", 11.0)
        editor._commit_cell_value("f8853", "schedule2_17f", 12.0)
        editor._commit_cell_value("f3468", "general_business_credit_component", 2.0)
        editor._commit_cell_value("f8586", "general_business_credit_component", 3.0)
        editor._commit_cell_value("f8881", "general_business_credit_component", 4.0)
        editor._commit_cell_value("f8936a", "general_business_credit_component", 5.0)
        editor._commit_cell_value("f8941", "general_business_credit_component", 6.0)
        editor._commit_cell_value("f8994", "general_business_credit_component", 7.0)
        editor._commit_cell_value("f3800", "manual_other_business_credit_adjustments", 1.0)

        self.assertEqual(editor._get_form_cell("f1040s1", "12")["value"], 12.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "8e")["value"], 10.0)
        self.assertEqual(editor._get_form_cell("f1040sd", "4")["value"], 9.0)
        self.assertEqual(editor._get_form_cell("f1040sd", "11")["value"], 13.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "1b")["value"], 1.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "1c")["value"], 2.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "1d")["value"], 5.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "1e")["value"], 6.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "1f")["value"], 7.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "10")["value"], 7.0)
        self.assertEqual(editor._get_form_cell("f1040sa", "12")["value"], 9.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "17e")["value"], 11.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "17f")["value"], 12.0)
        self.assertEqual(editor._get_form_cell("f3800", "component_credit_total")["value"], 27.0)
        self.assertEqual(editor._get_form_cell("f3800", "schedule3_6a")["value"], 28.0)
        self.assertEqual(editor._get_form_cell("f1040s3", "4")["value"], 9.0)
        self.assertEqual(editor._get_form_cell("f1040s3", "6a")["value"], 28.0)
        self.assertEqual(editor._get_form_cell("f1040s3", "6f")["value"], 3.0)
        self.assertEqual(editor._get_form_cell("f1040s3", "6m")["value"], 4.0)
        self.assertEqual(editor._get_form_cell("f1040s3", "12")["value"], 8.0)

    def test_form_5405_flows_through_schedule_2_total_tax(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f5405", "annual_installment_repayment", 10.0)
        editor._commit_cell_value("f5405", "accelerated_repayment_amount", 15.0)

        self.assertEqual(editor._get_form_cell("f5405", "schedule2_10")["value"], 25.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "10")["value"], 25.0)
        self.assertEqual(editor._get_form_cell("f1040s2", "21")["value"], 25.0)
        self.assertEqual(editor._get_form_cell("f1040", "23")["value"], 25.0)
        self.assertEqual(editor._get_form_cell("f1040", "24")["value"], 25.0)
        self.assertIn("f5405", set(editor._filed_form_ids()))

    def test_form_8283_flows_to_schedule_a_and_files_over_threshold(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040sa", "12_manual_component", 200.0)
        self.add_block_entry(
            editor,
            "1098_c",
            {
                "recipient": "taxpayer",
                "donee_name": "Helping Hands",
                "claimed_deduction_amount": 450.0,
            },
        )
        editor._commit_cell_value("f8283", "other_noncash_contributions", 100.0)

        self.assertEqual(editor._get_form_cell("f8283", "noncash_contributions_from_1098c")["value"], 450.0)
        self.assertEqual(editor._get_form_cell("f8283", "schedule_a_12")["value"], 550.0)
        self.assertTrue(editor._get_form_cell("f8283", "required_to_file_likely")["value"])
        self.assertFalse(editor._get_form_cell("f8283", "section_b_required_likely")["value"])
        self.assertEqual(editor._get_form_cell("f1040sa", "12")["value"], 750.0)
        self.assertEqual(editor._get_form_cell("f1040sa", "14")["value"], 750.0)
        self.assertIn("f8283", set(editor._filed_form_ids()))

    def test_form_8283_section_b_flag_trips_over_5000(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f8283", "other_noncash_contributions", 6001.0)

        self.assertTrue(editor._get_form_cell("f8283", "required_to_file_likely")["value"])
        self.assertTrue(editor._get_form_cell("f8283", "section_b_required_likely")["value"])

    def test_form_8283_item_rows_pull_from_1098c_entries(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1098_c",
            {
                "recipient": "taxpayer",
                "donee_name": "Helping Hands",
                "vehicle_description": "2012 Subaru Outback",
                "contribution_date": "2025-06-15",
                "claimed_deduction_amount": 450.0,
            },
        )
        self.add_block_entry(
            editor,
            "1098_c",
            {
                "recipient": "taxpayer",
                "donee_name": "City Mission",
                "vehicle_description": "1986 Cessna",
                "contribution_date": "2025-07-01",
                "claimed_deduction_amount": 6000.0,
            },
        )

        self.assertEqual(editor._get_form_cell("f8283", "section_a_item_1_description")["value"], "2012 Subaru Outback")
        self.assertEqual(editor._get_form_cell("f8283", "section_a_item_1_donee_name")["value"], "Helping Hands")
        self.assertEqual(editor._get_form_cell("f8283", "section_a_item_1_claimed_amount")["value"], 450.0)
        self.assertEqual(editor._get_form_cell("f8283", "section_a_item_2_description")["value"], "1986 Cessna")
        self.assertEqual(editor._get_form_cell("f8283", "section_a_item_2_contribution_date")["value"], "2025-07-01")
        self.assertTrue(editor._get_form_cell("f8283", "section_a_item_2_section_b_candidate")["value"])

    def test_remaining_missing_forms_now_exist_and_key_hooks_work(self) -> None:
        editor = self.make_editor()
        for form_id in [
            "f1040sr",
            "f1040sj",
            "f1040es",
            "f1040v",
            "f1040x",
            "f4835",
            "f7203",
            "f8862",
            "f8888",
            "f9465",
        ]:
            self.assertIn(form_id, editor._current_jurisdiction())

        editor._commit_cell_value("f1040_Federal_Info_Worksheet", "print_1040_sr", True)
        editor._commit_cell_value("f1040", "36", 100.0)
        editor._commit_cell_value("f1040", "37", 250.0)
        editor._commit_cell_value("f1040", "38", 10.0)
        editor._commit_cell_value("f1040sj", "elect_to_use_schedule_j", True)
        editor._commit_cell_value("f1040sj", "line23_tax", 123.0)
        editor._commit_cell_value("f4835", "gross_farm_rental_income", 1000.0)
        editor._commit_cell_value("f4835", "expenses_total", 400.0)
        editor._commit_cell_value("f7203", "schedule_e_basis_adjustment", 250.0)
        editor._commit_cell_value("f8862", "eic_recertification", True)
        editor._commit_cell_value("f1040", "35a", 500.0)
        editor._commit_cell_value("f8888", "allocation_account_1", 200.0)
        editor._commit_cell_value("f8888", "allocation_account_2", 300.0)
        editor._commit_cell_value("f9465", "requested_monthly_payment", 50.0)
        editor._commit_cell_value("f1040x", "amended_return_needed", True)

        self.assertTrue(editor._get_form_cell("f1040sr", "selected_for_print")["value"])
        self.assertEqual(editor._get_form_cell("f1040es", "carryforward_credit_from_current_return")["value"], 100.0)
        self.assertEqual(editor._get_form_cell("f1040v", "voucher_amount_due")["value"], 260.0)
        self.assertEqual(editor._get_form_cell("f1040sj", "line23_tax")["value"], 123.0)
        self.assertEqual(editor._get_form_cell("f1040", "tax_before_form_8615")["value"], 123.0)
        self.assertEqual(editor._get_form_cell("f1040", "16")["value"], 123.0)
        self.assertEqual(editor._get_form_cell("f4835", "schedule_e_40")["value"], 600.0)
        self.assertEqual(editor._get_form_cell("f1040se", "21")["value"], 600.0)
        self.assertEqual(editor._get_form_cell("f1040se", "28")["value"], 250.0)
        self.assertEqual(editor._get_form_cell("f1040se", "41")["value"], 850.0)
        self.assertTrue(editor._get_form_cell("f8862", "required_to_file_likely")["value"])
        self.assertEqual(editor._get_form_cell("f8888", "available_refund")["value"], 500.0)
        self.assertEqual(editor._get_form_cell("f8888", "allocation_total")["value"], 500.0)
        self.assertEqual(editor._get_form_cell("f8888", "allocation_difference")["value"], 0.0)
        self.assertEqual(editor._get_form_cell("f9465", "amount_owed_reference")["value"], 260.0)

        filed = set(editor._filed_form_ids())
        self.assertIn("f1040sj", filed)
        self.assertIn("f4835", filed)
        self.assertNotIn("f7203", filed)
        self.assertNotIn("f8862", filed)
        self.assertIn("f8888", filed)
        self.assertNotIn("f9465", filed)
        self.assertIn("form:f8862", editor.visible_sheet_ids)
        self.assertIn("form:f7203", editor.visible_sheet_ids)
        self.assertIn("form:f9465", editor.visible_sheet_ids)

    def test_schedule_c_stack_flows_to_schedule_1_and_files_forms(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1099_nec",
            {"recipient": "taxpayer", "payer_name": "Client Co", "box_1": 5000.0, "not_self_employment_income": False},
        )
        editor._commit_cell_value("f1040sc", "gross_receipts_manual_adjustments", 200.0)
        editor._commit_cell_value("f1040sc", "6", 50.0)
        editor._commit_cell_value("f1040sc", "8", 1000.0)
        editor._commit_cell_value("f4562", "schedule_c_depreciation", 300.0)
        editor._commit_cell_value("f8829", "primary_amount", 200.0)
        editor._commit_cell_value("f6198", "schedule_c_adjustment", -100.0)

        self.assertEqual(editor._get_form_cell("f1040sc", "1")["value"], 5200.0)
        self.assertEqual(editor._get_form_cell("f1040sc", "13")["value"], 300.0)
        self.assertEqual(editor._get_form_cell("f1040sc", "30")["value"], 200.0)
        self.assertEqual(editor._get_form_cell("f1040sc", "31")["value"], 3650.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "3")["value"], 3650.0)
        self.assertEqual(editor._get_form_cell("f8812_Earned_Income_Worksheet", "2b_schedule_c_component")["value"], 3650.0)

        filed = set(editor._filed_form_ids())
        self.assertIn("f1040sc", filed)
        self.assertIn("f4562", filed)
        self.assertNotIn("f8829", filed)
        self.assertIn("f6198", filed)
        self.assertIn("form:f8829", editor.visible_sheet_ids)

    def test_schedule_e_stack_flows_to_schedule_1_and_files_forms(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "k1_1065",
            {
                "recipient": "taxpayer",
                "payer_name": "Rental Partnership",
                "schedule_e_income_or_loss": 400.0,
                "qbi_income_or_loss": 300.0,
                "passive_credit_amount": 25.0,
            },
        )
        editor._commit_cell_value("f1040se", "21", 250.0)
        editor._commit_cell_value("f1040se", "passthrough_adjustments", -20.0)
        editor._commit_cell_value("f1040se", "rental_qbi_adjustments", 50.0)
        editor._commit_cell_value("f6198", "schedule_e_adjustment", -30.0)
        editor._commit_cell_value("f8582", "schedule_e_adjustment", -100.0)
        editor._commit_cell_value("f8582cr", "passive_credit_carryforward", 25.0)

        self.assertEqual(editor._get_form_cell("f1040se", "28_k1_income_total")["value"], 400.0)
        self.assertEqual(editor._get_form_cell("f1040se", "28")["value"], 380.0)
        self.assertEqual(editor._get_form_cell("f1040se", "32")["value"], 630.0)
        self.assertEqual(editor._get_form_cell("f1040se", "41")["value"], 500.0)
        self.assertEqual(editor._get_form_cell("f1040se", "qbi_income_total")["value"], 350.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "5")["value"], 500.0)

        filed = set(editor._filed_form_ids())
        self.assertIn("f1040se", filed)
        self.assertIn("f6198", filed)
        self.assertIn("f8582", filed)
        self.assertNotIn("f8582cr", filed)
        self.assertIn("form:f8582cr", editor.visible_sheet_ids)

    def test_schedule_e_property_columns_and_passthrough_rows(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "k1_1065",
            {
                "recipient": "taxpayer",
                "payer_name": "Rental Partnership",
                "category": "passive",
                "schedule_e_income_or_loss": 400.0,
                "qbi_income_or_loss": 300.0,
            },
        )
        self.add_block_entry(
            editor,
            "k1_1120s",
            {
                "recipient": "taxpayer",
                "payer_name": "Operating S Corp",
                "category": "nonpassive",
                "schedule_e_income_or_loss": -50.0,
                "qbi_income_or_loss": -25.0,
            },
        )
        editor._commit_cell_value("f1040se", "property_1_rents_received", 1000.0)
        editor._commit_cell_value("f1040se", "property_1_repairs", 200.0)
        editor._commit_cell_value("f1040se", "property_1_taxes", 100.0)
        editor._commit_cell_value("f1040se", "property_2_royalties_received", 200.0)
        editor._commit_cell_value("f1040se", "property_2_utilities", 50.0)

        self.assertEqual(editor._get_form_cell("f1040se", "property_1_line21")["value"], 700.0)
        self.assertEqual(editor._get_form_cell("f1040se", "property_2_line21")["value"], 150.0)
        self.assertEqual(editor._get_form_cell("f1040se", "21")["value"], 850.0)
        self.assertEqual(editor._get_form_cell("f1040se", "passthrough_1_name")["value"], "Rental Partnership")
        self.assertEqual(editor._get_form_cell("f1040se", "passthrough_1_income_or_loss")["value"], 400.0)
        self.assertEqual(editor._get_form_cell("f1040se", "passthrough_2_name")["value"], "Operating S Corp")
        self.assertTrue(editor._get_form_cell("f1040se", "passthrough_2_nonpassive")["value"])
        self.assertEqual(editor._get_form_cell("f1040se", "28_k1_income_total")["value"], 350.0)
        self.assertEqual(editor._get_form_cell("f1040se", "32")["value"], 1200.0)
        self.assertEqual(editor._get_form_cell("f1040se", "41")["value"], 1200.0)

    def test_form_2441_part_iii_benefits_flow_to_line_12_and_1040_line_1e(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "w2",
            {
                "recipient": "taxpayer",
                "employer_name": "Employer Co",
                "box_1": 40000.0,
                "box_10": 5000.0,
            },
        )
        editor._commit_cell_value("f2441", "qualifying_person_1_name", "Alex Doe")
        editor._commit_cell_value("f2441", "qualifying_person_1_care_expenses", 3200.0)
        editor._commit_cell_value("f2441", "provider_1_name", "Daycare One")
        editor._commit_cell_value("f2441", "provider_1_amount_paid", 2800.0)
        editor._commit_cell_value("f2441", "provider_2_name", "Camp Two")
        editor._commit_cell_value("f2441", "provider_2_amount_paid", 400.0)

        self.assertEqual(editor._get_form_cell("f2441", "12")["value"], 5000.0)
        self.assertEqual(editor._get_form_cell("f2441", "15")["value"], 5000.0)
        self.assertEqual(editor._get_form_cell("f2441", "26")["value"], 1800.0)
        self.assertEqual(editor._get_form_cell("f1040", "1e")["value"], 1800.0)

    def test_form_2441_excluded_benefits_reduce_credit_base(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "w2",
            {
                "recipient": "taxpayer",
                "employer_name": "Employer Co",
                "box_1": 40000.0,
                "box_10": 2000.0,
            },
        )
        self.add_block_entry(
            editor,
            "w2",
            {
                "recipient": "spouse",
                "employer_name": "Spouse Employer Co",
                "box_1": 35000.0,
            },
        )

        editor._commit_cell_value("f2441", "qualifying_person_1_name", "Alex Doe")
        editor._commit_cell_value("f2441", "qualifying_person_1_care_expenses", 6000.0)

        self.assertEqual(editor._get_form_cell("f2441", "12")["value"], 2000.0)
        self.assertEqual(editor._get_form_cell("f2441", "25")["value"], 2000.0)
        self.assertEqual(editor._get_form_cell("f2441", "30")["value"], 1000.0)
        self.assertEqual(editor._get_form_cell("f2441", "31")["value"], 1000.0)
        self.assertEqual(editor._get_form_cell("f2441", "3")["value"], 1000.0)
        self.assertEqual(editor._get_form_cell("f2441", "26")["value"], 0.0)

    def test_f8949_selected_block_drives_preview_values_and_checkboxes(self) -> None:
        editor = self.make_editor()
        self.add_block_entry_on_form(
            editor,
            "f8949",
            "st_box_b",
            {
                "recipient": "taxpayer",
                "description_of_property": "100 sh. XYZ Co.",
                "date_acquired": "2025-01-05",
                "date_sold": "2025-07-15",
                "proceeds": 1500.0,
                "basis": 900.0,
                "adjustment_code": "W",
                "adjustment_amount": 50.0,
                "gain_loss": 650.0,
            },
        )
        editor._sync_visible_sheets_from_usage(select_sheet_id="block:f8949:st_box_b", preserve_existing=False)

        self.assertEqual(editor._mapped_preview_id("block", "f8949", "st_box_b"), "f8949")
        self.assertEqual(
            editor._resolve_pdf_mapping_source(
                "f8949",
                'f8949_preview_row_value("short", 1, "description_of_property")',
            ),
            "100 sh. XYZ Co.",
        )
        self.assertEqual(
            editor._resolve_pdf_mapping_source("f8949", 'f8949_preview_total("short", "h")'),
            650.0,
        )
        self.assertFalse(editor._resolve_pdf_mapping_source("f8949", 'f8949_preview_checkbox("st_box_a")'))
        self.assertTrue(editor._resolve_pdf_mapping_source("f8949", 'f8949_preview_checkbox("st_box_b")'))

    def test_f8949_block_cells_map_to_preview_highlight_sources(self) -> None:
        editor = self.make_editor()

        self.assertEqual(
            editor._preview_mapping_sources_for_cell_ref(
                ("block", "f8949", "st_box_h", 0, "gain_loss")
            ),
            {'f8949_preview_row_value("short", 1, "gain_loss")'},
        )

    def test_f8949_selected_entry_switches_to_the_matching_copy_chunk(self) -> None:
        editor = self.make_editor()
        for entry_number in range(1, 13):
            self.add_block_entry_on_form(
                editor,
                "f8949",
                "st_box_a",
                {
                    "recipient": "taxpayer",
                    "description_of_property": f"Lot {entry_number}",
                    "date_acquired": "2025-01-01",
                    "date_sold": "2025-02-01",
                    "proceeds": float(entry_number * 100),
                    "basis": float(entry_number * 40),
                    "adjustment_code": "",
                    "adjustment_amount": 0.0,
                    "gain_loss": float(entry_number * 60),
                },
            )
        editor._sync_visible_sheets_from_usage(select_sheet_id="block:f8949:st_box_a", preserve_existing=False)

        twelfth_entry_row = self.find_first_row_for_entry(editor, 12)
        editor.table.setCurrentCell(twelfth_entry_row, 2)

        self.assertEqual(
            editor._resolve_pdf_mapping_source(
                "f8949",
                'f8949_preview_row_value("short", 1, "description_of_property")',
            ),
            "Lot 12",
        )
        self.assertEqual(
            editor._resolve_pdf_mapping_source("f8949", 'f8949_preview_total("short", "h")'),
            720.0,
        )

    def test_questionnaire_tri_state_rows_use_yes_no_checkboxes_and_required_red_background(self) -> None:
        editor = self.make_editor()
        editor.populate_form("f1040_Return_Intake_Questions")

        target_row = next(
            row_idx
            for row_idx in range(editor.table.rowCount())
            if editor.table.item(row_idx, 0) is not None and editor.table.item(row_idx, 0).text() == "has_foreign_income"
        )
        widget = editor.table.cellWidget(target_row, 2)

        self.assertIsNotNone(widget)
        self.assertEqual(len(widget.findChildren(QCheckBox)), 2)
        self.assertIn(REQUIRED_BACKGROUND.name(), widget.styleSheet())

        editor._on_tri_state_checkbox_changed("f1040_Return_Intake_Questions", "has_foreign_income", True, True)
        self.assertIs(editor._get_form_cell("f1040_Return_Intake_Questions", "has_foreign_income")["value"], True)

        editor._on_tri_state_checkbox_changed("f1040_Return_Intake_Questions", "has_foreign_income", True, False)
        self.assertIsNone(editor._get_form_cell("f1040_Return_Intake_Questions", "has_foreign_income")["value"])

    def test_remove_info_return_reindexes_remaining_entries(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(editor, "1099_int", {"payer_name": "First National Bank", "box_1": 10.0})
        self.add_block_entry(editor, "1099_int", {"payer_name": "Midwest Credit Union", "box_1": 20.0})
        editor._sync_visible_sheets_from_usage(select_sheet_id="block:f1040:1099_int", preserve_existing=False)
        editor.populate_block_sheet("f1040", "1099_int")

        first_entry_row = self.find_first_row_for_entry(editor, 1)
        editor.table.setCurrentCell(first_entry_row, 2)
        editor.remove_info_return()

        entries = ((editor._current_jurisdiction().get("f1040") or {}).get("blocks") or {}).get("1099_int", {}).get("entries", [])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["payer_name"], "Midwest Credit Union")
        self.assertEqual(editor.table.item(0, 0).text(), "1.recipient")

    def test_form_8962_monthly_1095a_entries_flow_into_monthly_grid(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1095_a",
            {
                "recipient": "taxpayer",
                "marketplace_name": "Exchange",
                "policy_number": "POL-1",
                "month_01_enrollment_premiums": 1200.0,
                "month_01_slcsp": 1000.0,
                "month_01_advance_ptc": 500.0,
                "month_02_enrollment_premiums": 1200.0,
                "month_02_slcsp": 1000.0,
                "month_02_advance_ptc": 900.0,
            },
        )
        editor._commit_cell_value("f8962", "monthly_contribution_base", 200.0)

        self.assertTrue(editor._get_form_cell("f8962", "monthly_data_present")["value"])
        self.assertEqual(editor._get_form_cell("f8962", "month_01_enrollment_premiums")["value"], 1200.0)
        self.assertEqual(editor._get_form_cell("f8962", "month_01_assistance_amount")["value"], 800.0)
        self.assertEqual(editor._get_form_cell("f8962", "month_01_ptc")["value"], 800.0)
        self.assertEqual(editor._get_form_cell("f8962", "monthly_ptc_total")["value"], 1600.0)
        self.assertEqual(editor._get_form_cell("f8962", "24")["value"], 1600.0)
        self.assertEqual(editor._get_form_cell("f8962", "25")["value"], 1400.0)
        self.assertEqual(editor._get_form_cell("f8962", "26")["value"], 200.0)
        self.assertEqual(editor._get_form_cell("f8962", "29")["value"], 0.0)

    def test_form_8962_annual_calculation_uses_1095a_annual_totals(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1095_a",
            {
                "recipient": "taxpayer",
                "marketplace_name": "Exchange",
                "policy_number": "POL-ANN",
                "annual_enrollment_premiums": 12000.0,
                "annual_slcsp": 9000.0,
                "annual_advance_ptc": 7000.0,
            },
        )
        editor._commit_cell_value("f8962", "use_annual_calculation", True)
        editor._commit_cell_value("f8962", "annual_contribution_amount", 3000.0)

        self.assertEqual(editor._get_form_cell("f8962", "annual_assistance_amount")["value"], 6000.0)
        self.assertEqual(editor._get_form_cell("f8962", "annual_ptc")["value"], 6000.0)
        self.assertEqual(editor._get_form_cell("f8962", "24")["value"], 6000.0)
        self.assertEqual(editor._get_form_cell("f8962", "25")["value"], 7000.0)
        self.assertEqual(editor._get_form_cell("f8962", "27")["value"], 1000.0)
        self.assertEqual(editor._get_form_cell("f8962", "29")["value"], 1000.0)

    def test_form_8962_policy_allocation_reduces_monthly_totals_and_populates_part_iv(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1095_a",
            {
                "recipient": "taxpayer",
                "marketplace_name": "Exchange",
                "policy_number": "SHARED-1",
                "multiple_tax_family_allocation": True,
                "allocation_other_taxpayer_ssn": "123-45-6789",
                "allocation_start_month": 1,
                "allocation_stop_month": 2,
                "allocation_premium_pct": 50.0,
                "allocation_slcsp_pct": 60.0,
                "allocation_advance_ptc_pct": 70.0,
                "month_01_enrollment_premiums": 1000.0,
                "month_01_slcsp": 900.0,
                "month_01_advance_ptc": 800.0,
                "month_02_enrollment_premiums": 1000.0,
                "month_02_slcsp": 900.0,
                "month_02_advance_ptc": 800.0,
            },
        )

        self.assertTrue(editor._get_form_cell("f8962", "has_marketplace_policy_allocations")["value"])
        self.assertTrue(editor._get_form_cell("f8962", "has_policy_allocation_or_alternative_calc")["value"])
        self.assertEqual(editor._get_form_cell("f8962", "month_01_enrollment_premiums")["value"], 500.0)
        self.assertEqual(editor._get_form_cell("f8962", "month_01_slcsp")["value"], 540.0)
        self.assertEqual(editor._get_form_cell("f8962", "month_01_advance_ptc")["value"], 560.0)
        self.assertEqual(editor._get_form_cell("f8962", "allocation_1_policy_number")["value"], "SHARED-1")
        self.assertEqual(editor._get_form_cell("f8962", "allocation_1_other_taxpayer_ssn")["value"], "123-45-6789")
        self.assertEqual(editor._get_form_cell("f8962", "allocation_1_premium_pct")["value"], 50.0)
        self.assertEqual(editor._get_form_cell("f8962", "allocation_1_slcsp_pct")["value"], 60.0)
        self.assertEqual(editor._get_form_cell("f8962", "allocation_1_advance_ptc_pct")["value"], 70.0)

    def test_form_8962_alternative_marriage_monthly_contribution_overrides_base(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f8962", "alternative_calculation_for_marriage", True)
        editor._commit_cell_value("f8962", "monthly_contribution_base", 300.0)
        editor._commit_cell_value("f8962", "alternative_taxpayer_monthly_contribution_amount", 150.0)
        editor._commit_cell_value("f8962", "alternative_taxpayer_start_month", 1)
        editor._commit_cell_value("f8962", "alternative_taxpayer_stop_month", 3)

        self.assertEqual(editor._get_form_cell("f8962", "month_01_contribution_amount")["value"], 150.0)
        self.assertEqual(editor._get_form_cell("f8962", "month_04_contribution_amount")["value"], 300.0)

    def test_form_7206_can_drive_schedule_1_line_17(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Schedule_1_Line_17_Self_Employed_Health_Insurance", "2", 400.0)
        editor._commit_cell_value("f7206", "primary_amount", 650.0)

        self.assertEqual(editor._get_form_cell("f7206", "schedule1_17_deduction")["value"], 650.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "17")["value"], 650.0)
        self.assertNotIn("f7206", set(editor._filed_form_ids()))
        self.assertIn("form:f7206", editor.visible_sheet_ids)

    def test_form_1098e_feeds_student_loan_interest_worksheet(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1098_e",
            {"recipient": "taxpayer", "lender_name": "Loan Servicer", "box_1": 1800.0},
        )
        editor._commit_cell_value("f1098e", "phaseout_reduction", 300.0)

        self.assertEqual(editor._get_form_cell("f1098e", "reported_interest_total")["value"], 1800.0)
        self.assertEqual(editor._get_form_cell("f1098e", "1")["value"], 1800.0)
        self.assertEqual(editor._get_form_cell("f1098e", "2")["value"], 1500.0)
        self.assertEqual(editor._get_form_cell("f1040_Schedule_1_Line_21_Student_Loan_Interest", "1")["value"], 1800.0)
        self.assertEqual(editor._get_form_cell("f1040_Schedule_1_Line_21_Student_Loan_Interest", "2")["value"], 1500.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "21")["value"], 1500.0)
        self.assertNotIn("f1098e", set(editor._filed_form_ids()))

    def test_schedule_r_feeds_schedule_3_and_credit_limit_chain(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Federal_Info_Worksheet", "taxpayer_retired_disability", True)
        editor._commit_cell_value("f1040sr_schedule_r", "credit_before_limits", 600.0)

        self.assertTrue(editor._get_form_cell("f1040sr_schedule_r", "taxpayer_qualifying")["value"])
        self.assertEqual(editor._get_form_cell("f1040sr_schedule_r", "eligible_person_count")["value"], 1)
        self.assertEqual(editor._get_form_cell("f1040sr_schedule_r", "schedule3_6d")["value"], 600.0)
        self.assertEqual(editor._get_form_cell("f1040s3", "6d")["value"], 600.0)
        self.assertEqual(editor._get_form_cell("f8812", "credit_limit_worksheet_a_2")["value"], 600.0)
        self.assertIn("f1040sr_schedule_r", set(editor._filed_form_ids()))

    def test_form_8615_overrides_form_1040_line_16_when_required(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Federal_Info_Worksheet", "taxpayer_dob", "2010-06-15")
        editor._commit_cell_value("f1040", "12a", True)
        self.add_block_entry(
            editor,
            "1099_int",
            {"recipient": "taxpayer", "payer_name": "Custodial Bank", "box_1": 20000.0},
        )
        editor._commit_cell_value("f8615", "child_required_to_file_return", True)
        editor._commit_cell_value("f8615", "parent_taxable_income_input", 100000.0)

        self.assertTrue(editor._get_form_cell("f8615", "required_to_file")["value"])
        self.assertEqual(editor._get_form_cell("f8615", "1")["value"], 20000.0)
        self.assertEqual(editor._get_form_cell("f8615", "5")["value"], 4250.0)
        self.assertEqual(editor._get_form_cell("f8615", "17")["value"], editor._get_form_cell("f1040", "tax_before_form_8615")["value"])
        self.assertEqual(editor._get_form_cell("f1040", "16")["value"], editor._get_form_cell("f8615", "18")["value"])
        self.assertGreater(editor._get_form_cell("f8615", "18")["value"], editor._get_form_cell("f8615", "17")["value"])
        self.assertIn("f8615", set(editor._filed_form_ids()))

    def test_form_8615_does_not_apply_after_age_limit(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040_Federal_Info_Worksheet", "taxpayer_dob", "2000-06-15")
        editor._commit_cell_value("f1040", "12a", True)
        self.add_block_entry(
            editor,
            "1099_int",
            {"recipient": "taxpayer", "payer_name": "Custodial Bank", "box_1": 20000.0},
        )
        editor._commit_cell_value("f8615", "child_required_to_file_return", True)
        editor._commit_cell_value("f8615", "parent_taxable_income_input", 100000.0)

        self.assertFalse(editor._get_form_cell("f8615", "required_to_file")["value"])
        self.assertEqual(editor._get_form_cell("f1040", "16")["value"], editor._get_form_cell("f1040", "tax_before_form_8615")["value"])
        self.assertNotIn("f8615", set(editor._filed_form_ids()))

    def test_schedule_f_and_form_8814_feed_schedule_1_and_f4952(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(
            editor,
            "1099_misc",
            {"recipient": "taxpayer", "payer_name": "Crop Insurer", "box_9": 100.0},
        )
        self.add_block_entry(
            editor,
            "1099_g",
            {"recipient": "taxpayer", "payer_name": "USDA", "box_7": 50.0},
        )
        editor._commit_cell_value("f1040sf", "other_farm_income_adjustments", 20.0)
        editor._commit_cell_value("f1040sf", "expenses_total", 30.0)
        editor._commit_cell_value("f1040s1", "8g_manual_component", 5.0)
        editor._commit_cell_value("f1040s1", "8z_manual_component", 10.0)
        editor._commit_cell_value("f8814", "schedule1_8g_alaska_dividends", 70.0)
        editor._commit_cell_value("f8814", "schedule1_8z_other_income", 200.0)
        editor._commit_cell_value("f8814", "investment_income_carryin", 50.0)

        self.assertEqual(editor._get_form_cell("f1040sf", "gross_farm_income_total")["value"], 170.0)
        self.assertEqual(editor._get_form_cell("f1040sf", "34")["value"], 140.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "6")["value"], 140.0)
        self.assertEqual(editor._get_form_cell("f8812_Earned_Income_Worksheet", "2c_schedule_f_component")["value"], 140.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "8g")["value"], 75.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "8z")["value"], 210.0)
        self.assertEqual(editor._get_form_cell("f1040s1", "9")["value"], 285.0)
        self.assertEqual(editor._get_form_cell("f4952", "4a")["value"], 50.0)

        filed = set(editor._filed_form_ids())
        self.assertIn("f1040sf", filed)
        self.assertIn("f8814", filed)

    def test_flat_return_roundtrip_preserves_block_entries(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        entry_number = editor._append_blank_block_entry("f1040", "1099_int")
        self.assertEqual(entry_number, 3)
        editor._commit_block_value("f1040", "1099_int", 2, "payer_name", "Test Bank")
        editor._commit_block_value("f1040", "1099_int", 2, "box_1", 1234.56)
        editor._commit_block_value("f1040", "1099_int", 2, "recipient", "spouse")

        payload = editor._serialize_flat_return_data()
        self.assertTrue(payload["f1040.1099_int.2.__entry__"])
        self.assertEqual(payload["f1040.1099_int.2.payer_name"], "Test Bank")
        self.assertEqual(payload["f1040.1099_int.2.box_1"], 1234.56)
        self.assertEqual(payload["f1040.1099_int.2.recipient"], "spouse")

        with TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "roundtrip.json"
            save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            roundtrip = TaxSheetEditor(save_path)
            entries = (
                (((roundtrip._current_jurisdiction().get("f1040") or {}).get("blocks") or {}).get("1099_int") or {}).get("entries")
                or []
            )
            self.assertGreaterEqual(len(entries), 3)
            self.assertEqual(entries[2]["payer_name"], "Test Bank")
            self.assertEqual(entries[2]["box_1"], 1234.56)
            self.assertEqual(entries[2]["recipient"], "spouse")

    def test_block_preview_mapping_uses_selected_entry(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        editor.populate_block_sheet("f1040", "1099_int")
        self.assertEqual(editor._current_block_preview_entry_index("f1040", "1099_int"), 0)
        self.assertEqual(editor._resolve_block_preview_source("f1040", "1099_int", "entry.payer_name"), "First National Bank")

        second_entry_row = self.find_first_row_for_entry(editor, 2)
        editor.table.setCurrentCell(second_entry_row, 2)

        self.assertEqual(editor._current_block_preview_entry_index("f1040", "1099_int"), 1)
        self.assertEqual(editor._resolve_block_preview_source("f1040", "1099_int", "entry.payer_name"), "Midwest Credit Union")
        self.assertEqual(editor._resolve_block_preview_source("f1040", "1099_int", "recipient_name"), "Jane Doe")

    def test_form_fillable_metadata_and_pdf_source_path_drive_preview_resolution(self) -> None:
        editor = self.make_editor()

        schedule_ai_meta = editor._current_jurisdiction()["f2210_Schedule_AI"]["_meta"]
        self.assertTrue(schedule_ai_meta["fillable_form"])
        self.assertEqual(
            schedule_ai_meta["pdf_source_path"],
            "forms-instructions-and-publications/forms/f2210.pdf",
        )
        preview_path = editor._raw_preview_source_path("form", "f2210_Schedule_AI", None)
        self.assertIsNotNone(preview_path)
        self.assertEqual(preview_path.name, "f2210.pdf")

        schedule_8812_meta = editor._current_jurisdiction()["f8812"]["_meta"]
        self.assertTrue(schedule_8812_meta["fillable_form"])
        self.assertEqual(
            schedule_8812_meta["pdf_source_path"],
            "forms-instructions-and-publications/forms/f1040s8.pdf",
        )

    def test_generated_pdf_field_map_exists_for_fillable_form_without_render_mappings(self) -> None:
        editor = self.make_editor()
        self.assertIsNotNone(editor.pdf_preview_engine)

        self.assertTrue(editor.pdf_preview_engine.has_mapping_for_form("f1040s1"))
        self.assertTrue(editor.pdf_preview_engine.has_render_mappings_for_form("f1040s1"))

        mapping = editor.pdf_preview_engine._load_mapping("f1040s1")
        self.assertEqual(
            mapping["source_pdf"],
            "forms-instructions-and-publications/forms/f1040s1.pdf",
        )
        self.assertGreater(len(mapping.get("widgets", [])), 1)
        renderable_widgets = [
            item
            for item in mapping.get("widgets", [])
            if isinstance(item, dict) and item.get("render_mode") == "field_text"
        ]
        self.assertGreater(len(renderable_widgets), 10)

    def test_cross_form_block_item_expression_resolves_for_preview_mappings(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        value = editor._resolve_pdf_mapping_source("f1040sb", "f1040.1099_int.0.payer_name")
        self.assertEqual(value, "First National Bank")

    def test_generated_pdf_field_map_preserves_render_mappings_for_existing_preview_form(self) -> None:
        editor = self.make_editor()
        self.assertIsNotNone(editor.pdf_preview_engine)

        self.assertTrue(editor.pdf_preview_engine.has_mapping_for_form("f1040"))
        self.assertTrue(editor.pdf_preview_engine.has_render_mappings_for_form("f1040"))

        mapping = editor.pdf_preview_engine._load_mapping("f1040")
        mapped_widgets = [
            item
            for item in mapping.get("widgets", [])
            if isinstance(item, dict) and isinstance(item.get("source"), str) and item.get("source").strip()
        ]
        self.assertGreater(len(mapped_widgets), 10)

    def test_structural_forms_now_have_render_mappings(self) -> None:
        editor = self.make_editor()
        self.assertIsNotNone(editor.pdf_preview_engine)

        for form_id in ["f2441", "f8962", "f8283", "f1040se", "f8949"]:
            self.assertTrue(editor.pdf_preview_engine.has_mapping_for_form(form_id))
            self.assertTrue(editor.pdf_preview_engine.has_render_mappings_for_form(form_id))

    def test_block_fillable_metadata_and_pdf_source_path_drive_preview_resolution(self) -> None:
        editor = self.make_editor()

        w2_block = editor._current_jurisdiction()["f1040"]["blocks"]["w2"]
        self.assertTrue(w2_block["fillable_form"])
        self.assertEqual(
            w2_block["pdf_source_path"],
            "forms-instructions-and-publications/generated-information-returns/f1040__w2_template.pdf",
        )
        w2_preview_path = editor._block_preview_source_path("f1040", "w2")
        self.assertIsNotNone(w2_preview_path)
        self.assertEqual(w2_preview_path.name, "f1040__w2_template.pdf")

        interest_block = editor._current_jurisdiction()["f1040"]["blocks"]["1099_int"]
        self.assertTrue(interest_block["fillable_form"])
        self.assertEqual(
            interest_block["pdf_source_path"],
            "forms-instructions-and-publications/generated-information-returns/f1040__1099_int_template.pdf",
        )
        interest_preview_path = editor._block_preview_source_path("f1040", "1099_int")
        self.assertIsNotNone(interest_preview_path)
        self.assertEqual(interest_preview_path.name, "f1040__1099_int_template.pdf")

    def test_generated_info_return_block_mapping_uses_generated_template(self) -> None:
        editor = self.make_editor()
        self.assertIsNotNone(editor.pdf_preview_engine)

        preview_id = editor._block_preview_mapping_id("f1040", "w2")
        self.assertTrue(editor.pdf_preview_engine.has_mapping_for_form(preview_id))
        self.assertTrue(editor.pdf_preview_engine.has_render_mappings_for_form(preview_id))
        self.assertEqual(editor.pdf_preview_engine.mapping_path_for_form(preview_id).parent.name, "pdf_field_maps")

        mapping = editor.pdf_preview_engine._load_mapping(preview_id)
        self.assertEqual(
            mapping["source_pdf"],
            "forms-instructions-and-publications/generated-information-returns/f1040__w2_template.pdf",
        )
        self.assertGreater(len(mapping.get("widgets", [])), 10)

    def test_generated_worksheet_metadata_and_preview_resolution(self) -> None:
        editor = self.make_editor()

        worksheet_meta = editor._current_jurisdiction()["f1040_Tax_Computation"]["_meta"]
        self.assertTrue(worksheet_meta["fillable_form"])
        self.assertEqual(
            worksheet_meta["pdf_source_path"],
            "forms-instructions-and-publications/generated-worksheets/f1040_Tax_Computation_worksheet.pdf",
        )
        worksheet_preview_path = editor._raw_preview_source_path("form", "f1040_Tax_Computation", None)
        self.assertIsNotNone(worksheet_preview_path)
        self.assertEqual(worksheet_preview_path.name, "f1040_Tax_Computation_worksheet.pdf")

        self.assertIsNotNone(editor.pdf_preview_engine)
        self.assertTrue(editor.pdf_preview_engine.has_mapping_for_form("f1040_Tax_Computation"))
        self.assertTrue(editor.pdf_preview_engine.has_render_mappings_for_form("f1040_Tax_Computation"))

    def test_non_document_block_is_not_marked_as_fillable_form(self) -> None:
        editor = self.make_editor()

        helper_block = editor._current_jurisdiction()["f1040"]["blocks"]["foreign_tax_credit_items"]
        self.assertFalse(helper_block["fillable_form"])
        self.assertIsNone(helper_block["pdf_source_path"])
        self.assertIsNone(editor._block_preview_source_path("f1040", "foreign_tax_credit_items"))

    @unittest.skipUnless(PdfReader is not None, "pypdf is required for preview-render tests")
    def test_info_return_preview_mapping_renders_pdf(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))
        self.assertIsNotNone(editor.pdf_preview_engine)
        self.assertTrue(editor.pdf_preview_engine.available())

        editor.populate_block_sheet("f1040", "w2")
        preview_id = editor._block_preview_mapping_id("f1040", "w2")
        self.assertTrue(editor.pdf_preview_engine.has_mapping_for_form(preview_id))

        output_path = editor.pdf_preview_engine.render_preview(
            form_id=preview_id,
            resolve_source=lambda source: editor._resolve_pdf_mapping_source(preview_id, source),
        )

        self.assertTrue(output_path.is_file())
        self.assertEqual(len(PdfReader(str(output_path)).pages), 2)

    @unittest.skipUnless(PdfReader is not None, "pypdf is required for preview-render tests")
    def test_heuristic_schedule_1_preview_mapping_renders_pdf(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))
        self.assertIsNotNone(editor.pdf_preview_engine)
        self.assertTrue(editor.pdf_preview_engine.available())
        self.assertTrue(editor.pdf_preview_engine.has_render_mappings_for_form("f1040s1"))

        output_path = editor.pdf_preview_engine.render_preview(
            form_id="f1040s1",
            resolve_source=lambda source: editor._resolve_pdf_mapping_source("f1040s1", source),
        )

        self.assertTrue(output_path.is_file())
        self.assertEqual(len(PdfReader(str(output_path)).pages), 2)

    @unittest.skipUnless(PdfReader is not None, "pypdf is required for preview-render tests")
    def test_generated_worksheet_preview_mapping_renders_pdf(self) -> None:
        editor = self.make_editor()
        self.assertIsNotNone(editor.pdf_preview_engine)
        self.assertTrue(editor.pdf_preview_engine.available())
        self.assertTrue(editor.pdf_preview_engine.has_render_mappings_for_form("f1040_Tax_Computation"))

        output_path = editor.pdf_preview_engine.render_preview(
            form_id="f1040_Tax_Computation",
            resolve_source=lambda source: editor._resolve_pdf_mapping_source("f1040_Tax_Computation", source),
        )

        self.assertTrue(output_path.is_file())
        self.assertEqual(len(PdfReader(str(output_path)).pages), 1)

    def test_schedule_a_medical_worksheet_flows_to_line_1_and_line_4(self) -> None:
        editor = self.make_editor()
        editor._commit_cell_value("f1040", "11b", 10000.0)
        editor._commit_cell_value("f1040sa_Medical_Expense_Qualification_Worksheet", "doctors_dentists_hospitals", 900.0)
        editor._commit_cell_value("f1040sa_Medical_Expense_Qualification_Worksheet", "prescription_drugs_insulin", 300.0)
        editor._commit_cell_value("f1040sa_Medical_Expense_Qualification_Worksheet", "reimbursed_expenses", 200.0)
        editor._commit_cell_value("f1040sa_Medical_Expense_Qualification_Worksheet", "employer_paid_or_pretax_premiums", 100.0)

        self.assertEqual(
            editor._get_form_cell("f1040sa_Medical_Expense_Qualification_Worksheet", "total_candidate_medical_expenses")["value"],
            1200.0,
        )
        self.assertEqual(
            editor._get_form_cell("f1040sa_Medical_Expense_Qualification_Worksheet", "total_reductions_and_exclusions")["value"],
            300.0,
        )
        self.assertEqual(
            editor._get_form_cell("f1040sa_Medical_Expense_Qualification_Worksheet", "schedule_a_line_1_medical_expenses")["value"],
            900.0,
        )
        self.assertEqual(editor._get_form_cell("f1040sa", "1")["value"], 900.0)
        self.assertEqual(editor._get_form_cell("f1040sa", "3")["value"], 750.0)
        self.assertEqual(editor._get_form_cell("f1040sa", "4")["value"], 150.0)

    def test_generated_schedule_a_medical_worksheet_metadata_and_preview_resolution(self) -> None:
        editor = self.make_editor()

        worksheet_meta = editor._current_jurisdiction()["f1040sa_Medical_Expense_Qualification_Worksheet"]["_meta"]
        self.assertTrue(worksheet_meta["fillable_form"])
        self.assertEqual(
            worksheet_meta["pdf_source_path"],
            "forms-instructions-and-publications/generated-worksheets/f1040sa_Medical_Expense_Qualification_Worksheet_worksheet.pdf",
        )
        worksheet_preview_path = editor._raw_preview_source_path(
            "form",
            "f1040sa_Medical_Expense_Qualification_Worksheet",
            None,
        )
        self.assertIsNotNone(worksheet_preview_path)
        self.assertEqual(
            worksheet_preview_path.name,
            "f1040sa_Medical_Expense_Qualification_Worksheet_worksheet.pdf",
        )
        self.assertIsNotNone(editor.pdf_preview_engine)
        self.assertTrue(
            editor.pdf_preview_engine.has_render_mappings_for_form("f1040sa_Medical_Expense_Qualification_Worksheet")
        )

    @unittest.skipUnless(PdfReader is not None, "pypdf is required for preview-render tests")
    def test_generated_schedule_a_medical_worksheet_preview_mapping_renders_pdf(self) -> None:
        editor = self.make_editor()
        self.assertIsNotNone(editor.pdf_preview_engine)
        self.assertTrue(editor.pdf_preview_engine.available())
        self.assertTrue(editor.pdf_preview_engine.has_render_mappings_for_form("f1040sa_Medical_Expense_Qualification_Worksheet"))

        output_path = editor.pdf_preview_engine.render_preview(
            form_id="f1040sa_Medical_Expense_Qualification_Worksheet",
            resolve_source=lambda source: editor._resolve_pdf_mapping_source(
                "f1040sa_Medical_Expense_Qualification_Worksheet",
                source,
            ),
        )

        self.assertTrue(output_path.is_file())
        self.assertEqual(len(PdfReader(str(output_path)).pages), 2)

    def test_filing_export_sheet_ids_include_filed_forms_only(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        filing_sheet_ids = editor._filing_export_sheet_ids()

        self.assertIn("form:f1040", filing_sheet_ids)
        self.assertIn("form:f1040sa", filing_sheet_ids)
        self.assertNotIn("block:f1040:w2", filing_sheet_ids)
        self.assertTrue(all(sheet_id.startswith("form:") for sheet_id in filing_sheet_ids))

    @unittest.skipUnless(PdfReader is not None, "pypdf is required for export-package tests")
    def test_build_pdf_package_merges_selected_sheets(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "filing_package.pdf"
            included_labels, missing_labels = editor._build_pdf_package(
                ["form:f1040", "form:f1040s1", "block:f1040:w2"],
                output_path,
            )

            self.assertTrue(output_path.is_file())
            self.assertEqual(missing_labels, [])
            self.assertEqual(len(included_labels), 3)
            self.assertGreaterEqual(len(PdfReader(str(output_path)).pages), 4)

    @unittest.skipUnless(PdfReader is not None, "pypdf is required for export-package tests")
    def test_f8949_build_pdf_package_expands_multiple_attachment_copies(self) -> None:
        editor = self.make_editor()
        for entry_number in range(1, 13):
            self.add_block_entry_on_form(
                editor,
                "f8949",
                "st_box_a",
                {
                    "recipient": "taxpayer",
                    "description_of_property": f"Lot {entry_number}",
                    "date_acquired": "2025-01-01",
                    "date_sold": "2025-02-01",
                    "proceeds": float(entry_number * 100),
                    "basis": float(entry_number * 50),
                    "adjustment_code": "",
                    "adjustment_amount": 0.0,
                    "gain_loss": float(entry_number * 50),
                },
            )

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "f8949_package.pdf"
            included_labels, missing_labels = editor._build_pdf_package(["form:f8949"], output_path)

            self.assertTrue(output_path.is_file())
            self.assertEqual(missing_labels, [])
            self.assertEqual(len(included_labels), 2)
            self.assertTrue(any("copy 1" in label for label in included_labels))
            self.assertTrue(any("copy 2" in label for label in included_labels))
            self.assertEqual(len(PdfReader(str(output_path)).pages), 4)

    def test_all_export_sheet_ids_put_non_filing_documents_at_end(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        all_sheet_ids = editor._all_export_sheet_ids()

        self.assertGreater(len(all_sheet_ids), 3)
        filing_statuses: list[bool] = []
        for sheet_id in all_sheet_ids:
            sheet_type, primary_id, _ = editor._parse_sheet_id(sheet_id)
            if sheet_type != "form":
                filing_statuses.append(False)
                continue
            form_data = editor._current_jurisdiction().get(primary_id) or {}
            filing_statuses.append(editor._should_file_form_now(primary_id, form_data))

        first_non_filing = next((idx for idx, is_filing in enumerate(filing_statuses) if not is_filing), len(filing_statuses))
        self.assertTrue(all(filing_statuses[idx] for idx in range(first_non_filing)))
        self.assertTrue(all(not filing_statuses[idx] for idx in range(first_non_filing, len(filing_statuses))))
        self.assertIn("block:f1040:w2", all_sheet_ids[first_non_filing:])

    def test_sheet_list_entries_start_with_info_worksheet_then_1040(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        entries = editor._sheet_list_entries()
        ordered_sheet_ids = [sheet_id for sheet_id, _ in entries]

        self.assertGreaterEqual(len(entries), 3)
        self.assertEqual(entries[0], ("form:f1040_Federal_Info_Worksheet", 0))
        self.assertEqual(entries[1], ("form:f1040_Return_Intake_Questions", 1))
        self.assertIn("form:f1040", ordered_sheet_ids)
        self.assertLess(
            ordered_sheet_ids.index("form:f1040_Return_Intake_Questions"),
            ordered_sheet_ids.index("form:f1040"),
        )

    def test_navigator_marks_incomplete_required_forms_in_red(self) -> None:
        editor = self.make_editor()
        editor._refresh_sheet_list(select_sheet_id="form:f1040_Return_Intake_Questions")

        target_item = None
        for idx in range(editor.sheet_list.count()):
            item = editor.sheet_list.item(idx)
            if item is not None and item.data(Qt.UserRole) == "form:f1040_Return_Intake_Questions":
                target_item = item
                break

        self.assertIsNotNone(target_item)
        self.assertEqual(target_item.foreground().color().name(), INCOMPLETE_SHEET_TEXT.name())
        self.assertIn("Incomplete", target_item.toolTip())

    def test_navigator_uses_shorthand_and_copy_counts_for_info_returns(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(editor, "1099_int", {"payer_name": "First National Bank", "box_1": 10.0})
        self.add_block_entry(editor, "1099_int", {"payer_name": "Midwest Credit Union", "box_1": 20.0})
        editor._sync_visible_sheets_from_usage(select_sheet_id="block:f1040:1099_int", preserve_existing=False)

        target_item = None
        for idx in range(editor.sheet_list.count()):
            item = editor.sheet_list.item(idx)
            if item is not None and item.data(Qt.UserRole) == "block:f1040:1099_int":
                target_item = item
                break

        self.assertIsNotNone(target_item)
        self.assertIn("1099-INT x2", target_item.text())

    def test_navigator_labels_show_1116_category_suffix(self) -> None:
        editor = self.make_editor()
        self.assertEqual(editor._sheet_navigator_label("form:f1116_passive"), "1116 (passive)")
        self.assertEqual(editor._sheet_navigator_label("form:f1116sb_general"), "1116 Sch B (general)")

    def test_sheet_list_entries_indent_attached_forms_blocks_and_worksheets(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        entries = editor._sheet_list_entries()
        indent_by_sheet_id = {sheet_id: indent_level for sheet_id, indent_level in entries}
        ordered_sheet_ids = [sheet_id for sheet_id, _ in entries]

        self.assertEqual(indent_by_sheet_id["form:f1040sa"], 1)
        self.assertEqual(indent_by_sheet_id["block:f1040:w2"], 1)
        self.assertEqual(indent_by_sheet_id["form:f1040_Tax_Computation"], 1)
        self.assertLess(ordered_sheet_ids.index("form:f1040"), ordered_sheet_ids.index("form:f1040sa"))
        self.assertLess(ordered_sheet_ids.index("form:f1040"), ordered_sheet_ids.index("block:f1040:w2"))
        self.assertLess(ordered_sheet_ids.index("form:f1040"), ordered_sheet_ids.index("form:f1040_Tax_Computation"))

    def test_table_hides_metadata_columns(self) -> None:
        editor = self.make_editor()

        self.assertTrue(editor.table.isColumnHidden(0))
        self.assertTrue(editor.table.isColumnHidden(3))
        self.assertTrue(editor.table.isColumnHidden(4))
        self.assertTrue(editor.table.isColumnHidden(5))
        self.assertTrue(editor.table.isColumnHidden(6))

    def test_metadata_popup_text_includes_form_cell_structure(self) -> None:
        editor = self.make_editor()

        popup_text = editor._metadata_popup_text(("form", "f1040_Federal_Info_Worksheet", "taxpayer_first_name"))

        self.assertIn("Summary", popup_text)
        self.assertIn("Sheet Type: Form Cell", popup_text)
        self.assertIn("Form: f1040_Federal_Info_Worksheet", popup_text)
        self.assertIn("Cell: taxpayer_first_name", popup_text)
        self.assertIn("Cell Schema", popup_text)

    def test_metadata_popup_text_includes_block_field_structure(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(editor, "w2", {"employer_name": "Example Co"})

        popup_text = editor._metadata_popup_text(("block", "f1040", "w2", 0, "employer_name"))

        self.assertIn("Summary", popup_text)
        self.assertIn("Sheet Type: Block Field", popup_text)
        self.assertIn("Parent Form: f1040", popup_text)
        self.assertIn("Block: w2", popup_text)
        self.assertIn("Field: employer_name", popup_text)
        self.assertIn("Current Value: Example Co", popup_text)
        self.assertIn("Field Schema", popup_text)

    def test_source_sheet_ids_include_referenced_blocks(self) -> None:
        editor = self.make_editor()

        self.assertEqual(editor._source_sheet_ids_for_cell_ref(("form", "f2441", "12")), {"block:f1040:w2"})
        self.assertEqual(editor._source_sheet_ids_for_cell_ref(("form", "f8962", "1095_a_enrollment_premiums_total")), {"block:f1040:1095_a"})

    def test_preview_mapping_sources_for_cell_refs(self) -> None:
        editor = self.make_editor()

        self.assertEqual(editor._preview_mapping_sources_for_cell_ref(("form", "f2441", "12")), {"12"})
        self.assertEqual(
            editor._preview_mapping_sources_for_cell_ref(("block", "f1040", "w2", 0, "employer_name")),
            {"entry.employer_name"},
        )

    def test_selection_drives_preview_highlight_sources(self) -> None:
        editor = self.make_editor()
        editor.populate_form("f2441")

        target_row = next(
            row_idx
            for row_idx in range(editor.table.rowCount())
            if editor.table.item(row_idx, 0) is not None and editor.table.item(row_idx, 0).text() == "12"
        )
        editor.table.setCurrentCell(target_row, 2)

        self.assertEqual(editor._preview_highlight_sources, {"12"})

    def test_hiding_metadata_popup_does_not_clear_selection_preview_highlight(self) -> None:
        editor = self.make_editor()
        editor.populate_form("f2441")

        target_row = next(
            row_idx
            for row_idx in range(editor.table.rowCount())
            if editor.table.item(row_idx, 0) is not None and editor.table.item(row_idx, 0).text() == "12"
        )
        editor.table.setCurrentCell(target_row, 2)
        editor._show_value_cell_info_popup(("form", "f2441", "12"), None)
        editor._hide_value_cell_info_popup()

        self.assertEqual(editor._preview_highlight_sources, {"12"})

    def test_pdf_preview_engine_collects_highlight_overlay_items(self) -> None:
        engine = FormPdfPreviewEngine(Path("."))
        overlays = engine._collect_highlight_overlay_items(
            [
                {"field": "field.one", "source": "8", "render_mode": "field_text"},
                {"field": "field.two", "source": "entry.employer_name", "render_mode": "field_text"},
                {"field": "field.three", "source": "8", "render_mode": "checkbox"},
            ],
            {
                "field.one": (0, (10.0, 20.0, 30.0, 40.0)),
                "field.two": (1, (50.0, 60.0, 70.0, 80.0)),
                "field.three": (0, (10.0, 20.0, 30.0, 40.0)),
            },
            {"8", "entry.employer_name"},
        )

        self.assertEqual(
            overlays,
            {
                0: [{"kind": "highlight", "rect": (10.0, 20.0, 30.0, 40.0)}],
                1: [{"kind": "highlight", "rect": (50.0, 60.0, 70.0, 80.0)}],
            },
        )

    def test_right_click_flash_highlights_source_sheets_until_hidden(self) -> None:
        editor = self.make_editor()
        self.add_block_entry(editor, "w2", {"employer_name": "Example Co", "box_10": 1200.0})
        editor._sync_visible_sheets_from_usage(select_sheet_id="form:f2441", preserve_existing=False)

        editor._show_value_cell_info_popup(("form", "f2441", "12"), None)

        highlighted_item = None
        for idx in range(editor.sheet_list.count()):
            item = editor.sheet_list.item(idx)
            if item is not None and item.data(Qt.UserRole) == "block:f1040:w2":
                highlighted_item = item
                break
        self.assertIsNotNone(highlighted_item)
        self.assertEqual(highlighted_item.data(Qt.BackgroundRole), SOURCE_SHEET_FLASH_BACKGROUND)

        editor._hide_value_cell_info_popup()

        self.assertIsNone(highlighted_item.data(Qt.BackgroundRole))


if __name__ == "__main__":
    unittest.main()
