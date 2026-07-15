"""Tests for agent tools."""

import json

import pytest

from src.tools.reference import _search_database, _DATA_DIR


class TestSearchDatabase:
    def test_search_reagent_by_name(self):
        db_path = _DATA_DIR / "reagent_database.json"
        if not db_path.exists():
            pytest.skip("Reagent database not available")
        results = _search_database(db_path, "Tris")
        assert len(results) > 0
        names = [r["name"] for r in results]
        assert any("Tris" in name for name in names)

    def test_search_enzyme_by_name(self):
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        results = _search_database(db_path, "EcoRI")
        assert len(results) > 0
        assert results[0]["name"] == "EcoRI"

    @pytest.mark.parametrize(
        "query",
        (
            "miniprep",
            "QIAprep",
            "P1 buffer",
            "N3 buffer",
            "silica column",
            "QIAprep 2.0 silica-membrane spin column",
        ),
    )
    def test_miniprep_queries_rank_the_qiaprep_workflow_first(self, query):
        db_path = _DATA_DIR / "reagent_database.json"
        results = _search_database(db_path, query)

        assert results
        workflow = results[0]
        assert workflow["name"] == "QIAprep Spin Miniprep Workflow"
        contract = workflow["protocol_contract"]
        assert contract["lysis_buffer_sequence"] == ["P1", "P2", "N3"]
        assert contract["culture_volume_ml"] == {"min": 1, "max": 5}
        assert contract["elution_volume_ul"] == {"min": 50, "max": 100, "standard": 50}

    @pytest.mark.parametrize(
        "query",
        (
            "protein expression",
            "T7 expression",
            "IPTG induction",
            "BL21(DE3)",
            "His6-MBP-GFP",
            "expression_construct_his6_mbp_gfp_001",
        ),
    )
    def test_expression_queries_rank_the_t7_workflow_first(self, query):
        db_path = _DATA_DIR / "reagent_database.json"
        results = _search_database(db_path, query)

        assert results
        workflow = results[0]
        assert workflow["name"] == "T7 His6-MBP-GFP Expression Workflow"
        contract = workflow["protocol_contract"]
        assert contract["construct_id"] == "expression_construct_his6_mbp_gfp_001"
        assert contract["iptg_concentration_mm"] == {"min": 0.5, "max": 1.0}
        assert contract["induction_od600"] == {"min": 0.5, "max": 0.8}
        assert contract["native_lysis_ph"] == {"min": 7.5, "max": 8.0}
        assert {
            profile["name"]: profile["insoluble_fraction_calibration"]
            for profile in contract["induction_schedule_profiles"]
        } == {
            "low_temperature_extended": 0.08,
            "room_temperature_intermediate": 0.12,
            "30c_moderate": 0.18,
            "37c_standard": 0.25,
        }
        assert contract["benchmark_calibrations"]["out_of_contract_attempt"] == {
            "observed_yield_mg_per_l": 0,
            "lysate_prepared": False,
            "note": (
                "Deterministic benchmark state transition only; not a physical "
                "zero-yield claim."
            ),
        }

    @pytest.mark.parametrize(
        ("query", "expected_name"),
        (
            ("BsaI", "BsaI-HFv2"),
            ("BsmBI", "BsmBI-v2"),
            ("T4 DNA ligase", "T4 DNA ligase"),
        ),
    )
    def test_exact_enzyme_names_and_aliases_rank_before_content_matches(
        self, query, expected_name
    ):
        db_path = _DATA_DIR / "enzyme_database.json"
        results = _search_database(db_path, query)

        assert results
        assert results[0]["name"] == expected_name

    def test_generic_type_iis_search_exposes_distinct_enzyme_families(self):
        db_path = _DATA_DIR / "enzyme_database.json"
        results = _search_database(db_path, "Type IIS restriction enzyme")
        by_name = {entry["name"]: entry for entry in results}

        assert by_name["BsaI-HFv2"]["recognition_sequence"] == "GGTCTC"
        assert by_name["BsaI-HFv2"]["optimal_temperature_c"] == 37
        assert by_name["BsaI-HFv2"]["acceptable_temperature_range_c"] == [37, 37]
        assert by_name["BsaI-HFv2"]["golden_gate_final_digest_temperature_c"] == 60
        assert by_name["BsaI-HFv2"]["golden_gate_final_digest_time_min"] == 5
        assert by_name["BsaI-HFv2"]["golden_gate_cycle_count"] == 30
        assert by_name["BsaI-HFv2"]["golden_gate_one_pot_buffer"] == (
            "T4 DNA ligase reaction buffer"
        )
        assert by_name["BsmBI-v2"]["recognition_sequence"] == "CGTCTC"
        assert by_name["BsmBI-v2"]["optimal_temperature_c"] == 55
        assert "Esp3I" not in by_name["BsmBI-v2"]["aliases"]
        assert "Esp3I" in by_name["BsmBI-v2"]["isoschizomers"]

    def test_search_safety_by_name(self):
        db_path = _DATA_DIR / "safety_database.json"
        if not db_path.exists():
            pytest.skip("Safety database not available")
        results = _search_database(db_path, "phenol")
        assert len(results) > 0

    def test_no_results(self):
        db_path = _DATA_DIR / "reagent_database.json"
        if not db_path.exists():
            pytest.skip("Reagent database not available")
        results = _search_database(db_path, "nonexistent_xyz_reagent_12345")
        assert len(results) == 0

    def test_case_insensitive(self):
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        results_upper = _search_database(db_path, "ECORI")
        results_lower = _search_database(db_path, "ecori")
        assert len(results_upper) == len(results_lower)


class TestDatabaseContent:
    def test_reagent_database_not_empty(self):
        db_path = _DATA_DIR / "reagent_database.json"
        if not db_path.exists():
            pytest.skip("Reagent database not available")
        with open(db_path) as f:
            data = json.load(f)
        assert len(data) >= 50

    def test_enzyme_database_not_empty(self):
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        with open(db_path) as f:
            data = json.load(f)
        assert len(data) >= 30

    def test_safety_database_not_empty(self):
        db_path = _DATA_DIR / "safety_database.json"
        if not db_path.exists():
            pytest.skip("Safety database not available")
        with open(db_path) as f:
            data = json.load(f)
        assert len(data) >= 30

    def test_enzyme_has_required_fields(self):
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        with open(db_path) as f:
            data = json.load(f)
        for entry in data:
            assert "name" in entry
            assert "optimal_temperature_c" in entry or "optimal_temperature" in entry

    def test_t4_ligase_temperature(self):
        """The headline condition must fit cohesive-end cloning, not blunt-end ligation."""
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        results = _search_database(db_path, "T4 DNA Ligase")
        assert len(results) > 0
        assert results[0]["name"] == "T4 DNA ligase"
        assert results[0]["optimal_temperature_c"] == 16
        assert results[0]["room_temperature_ligation_c"] == 25
        assert results[0]["cohesive_end_room_temperature_range_c"] == [20, 25]
        assert results[0]["cohesive_end_room_temperature_time_min"] == 10
        assert "Golden Gate cohesive-end cycling" in results[0]["notes"]
