import os
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional in some runtimes
    PdfReader = None

from src.main import TaxSheetEditor


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

    def test_helper_worksheet_is_not_marked_as_fillable_form(self) -> None:
        editor = self.make_editor()

        worksheet_meta = editor._current_jurisdiction()["f1040_Tax_Computation"]["_meta"]
        self.assertFalse(worksheet_meta["fillable_form"])
        self.assertIsNone(worksheet_meta["pdf_source_path"])
        self.assertIsNone(editor._raw_preview_source_path("form", "f1040_Tax_Computation", None))

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


if __name__ == "__main__":
    unittest.main()
