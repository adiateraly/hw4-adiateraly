"""Tests for the two tools. They do not need an API key or the internet."""

import json
import os
import sys
import time
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tools  # noqa: E402


# ---------------------------------------------------------------------------
# lookup
# ---------------------------------------------------------------------------

def test_lookup_finds_a_correct_2025_number():
    result = tools.lookup("Millbrook", "population_2025")
    assert result["value"] == 37203
    assert result["source"] == "NR-11"
    assert result["unit"] == "residents"


def test_lookup_misspelled_name_gives_a_helpful_error():
    result = tools.lookup("Ossbrige", "population_2025")
    assert "error" in result
    assert "Ossbridge" in result["error"]


def test_lookup_keeps_the_two_similar_names_apart():
    bridge = tools.lookup("Ossbridge", "population_2025")
    ford = tools.lookup("Ossford", "population_2025")
    assert bridge["value"] == 52904 and bridge["source"] == "NR-01"
    assert ford["value"] == 30982 and ford["source"] == "NR-02"
    # a short name that fits both is refused, not guessed
    unclear = tools.lookup("Oss", "population_2025")
    assert "error" in unclear
    assert "Ossbridge" in unclear["error"] and "Ossford" in unclear["error"]


def test_lookup_never_uses_an_archived_profile():
    tarnvale = tools.lookup("Tarnvale", "population_2025")
    assert tarnvale["value"] == 71388 and tarnvale["source"] == "NR-03"  # not 65,030 from NR-13
    kelmarsh = tools.lookup("Kelmarsh", "schools")
    assert kelmarsh["value"] == 11 and kelmarsh["source"] == "NR-04"     # not 10 from NR-14


def test_lookup_applies_the_correction_notice():
    result = tools.lookup("Brightwater", "area_km2")
    assert result["value"] == 921.4          # the profile says 912.4
    assert "NR-16" in result["source"]
    assert "NR-05" in result["source"]


def test_lookup_changes_cubic_metres_to_megalitres():
    result = tools.lookup("Lindenmoor", "water_use_megalitres")
    assert abs(result["value"] - 2151.4) < 1e-9
    assert result["unit"] == "megalitres"
    assert "cubic metres" in result["note"]


def test_lookup_unknown_field_and_bad_input_do_not_crash():
    assert "error" in tools.lookup("Millbrook", "mayor")
    assert "error" in tools.lookup(None, "population_2025")
    assert "error" in tools.lookup("Millbrook", 5)
    assert "error" in tools.lookup("x" * 5000, "population_2025")


def test_lookup_water_price_and_region():
    result = tools.lookup("region", "water_tariff_tenge_per_m3")
    assert result["value"] == 142.35 and result["source"] == "NR-15"
    assert "error" in tools.lookup("region", "population_2025")


def test_lookup_reads_every_fact_of_every_district():
    districts = ["Ossbridge", "Ossford", "Tarnvale", "Kelmarsh", "Brightwater", "Stonecairn",
                 "Harrowfield", "Lindenmoor", "Redfen", "Ashgrove", "Millbrook", "Coldharbour"]
    for district in districts:
        for field in tools.FIELDS:
            assert "error" not in tools.lookup(district, field), (district, field)


# ---------------------------------------------------------------------------
# calculate
# ---------------------------------------------------------------------------

def test_calculate_gets_the_right_number():
    result = tools.calculate("48317 * 1.0947")
    assert abs(result["result"] - 52892.6199) < 1e-6


def test_calculate_follows_the_order_of_operations():
    assert tools.calculate("2 + 3 * 4")["result"] == 14
    assert tools.calculate("(2 + 3) * 4")["result"] == 20
    assert tools.calculate("-3 + 10 / 4")["result"] == -0.5
    assert tools.calculate("2 ** 10")["result"] == 1024


def test_calculate_refuses_code_without_running_it():
    with mock.patch.object(os, "system") as fake_system:
        result = tools.calculate("__import__('os').system('echo hi')")
        fake_system.assert_not_called()
    assert "error" in result


def test_calculate_refuses_attribute_access():
    assert "error" in tools.calculate("(1).__class__")


def test_calculate_refuses_a_huge_power_fast():
    started = time.perf_counter()
    result = tools.calculate("9**9**9")
    assert "error" in result
    assert time.perf_counter() - started < 1.0   # it did not freeze
    assert "error" in tools.calculate("10 ** 400")
    assert "error" in tools.calculate("1e308 * 10")


def test_calculate_handles_division_by_zero():
    assert tools.calculate("5 / 0") == {"error": "division by zero"}
    assert "error" in tools.calculate("0 ** -1")


def test_calculate_refuses_other_strange_input():
    for text in ["", "   ", "x + 1", "'a' * 3", "True + 1", "1j", "1, 2", "abs(-1)",
                 "1 < 2", "[1, 2]", "2 +", "1,284.6 + 1", "1 // 2", "5 % 2", "(-8) ** 0.5",
                 "9" * 300, None, 42]:
        assert "error" in tools.calculate(text), text


# ---------------------------------------------------------------------------
# checking the request from the model (arguments arrive as a string)
# ---------------------------------------------------------------------------

def test_execute_tool_runs_a_good_request():
    result = tools.execute_tool("calculate", json.dumps({"expression": "44675 / 921.4"}))
    assert abs(result["result"] - 48.4859995659) < 1e-9
    result = tools.execute_tool("lookup", '{"district": "Redfen", "field": "schools"}')
    assert result["value"] == 10


def test_execute_tool_refuses_bad_requests_without_running_anything():
    assert "not valid JSON" in tools.execute_tool("calculate", "{expression: 1+1")["error"]
    assert "JSON object" in tools.execute_tool("calculate", "[1, 2]")["error"]
    assert "missing" in tools.execute_tool("lookup", '{"district": "Redfen"}')["error"]
    assert "unknown argument" in tools.execute_tool("calculate", '{"expression": "1", "x": "2"}')["error"]
    assert "must be a string" in tools.execute_tool("calculate", '{"expression": 5}')["error"]
    assert "unknown tool" in tools.execute_tool("delete_files", "{}")["error"]
    assert "error" in tools.execute_tool("calculate", None)
