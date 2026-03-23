import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.tax_qt_app import TaxSheetEditor


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
        entry_number = editor._append_blank_block_entry("f1040", block_id)
        self.assertIsNotNone(entry_number)
        entry_index = int(entry_number) - 1
        for field_id, value in values.items():
            editor._commit_block_value("f1040", block_id, entry_index, field_id, value)

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

    def test_sample_return_regression(self) -> None:
        editor = TaxSheetEditor()
        editor.load_json(Path("returns/john_jane_doe_sample.json"))

        self.assertEqual(editor._get_form_cell("f1040_Federal_Info_Worksheet", "taxpayer_age_1_1_2026")["value"], 43)
        self.assertEqual(editor._get_form_cell("f1040_Federal_Info_Worksheet", "spouse_age_1_1_2026")["value"], 41)
        self.assertEqual(editor._get_form_cell("f1040", "1a")["value"], 141100.0)
        self.assertEqual(editor._get_form_cell("f1040", "5a")["value"], 12500.0)
        self.assertIn("block:f1040:w2", editor.visible_sheet_ids)
        self.assertIn("form:f1040sa", editor.visible_sheet_ids)


if __name__ == "__main__":
    unittest.main()
