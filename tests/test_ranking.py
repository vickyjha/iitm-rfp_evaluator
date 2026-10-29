"""Deterministic scoring, benchmark, PPI and tie-break tests (no LLM involved)."""
import random

import pytest

from conftest import make_supplier
from rfp.tools import ranking_tool


def test_absolute_score_formula(criteria):
    s = make_supplier("A", [8, 6, 10, 5, 0], criteria_defs=criteria)
    out = ranking_tool.compute_absolute_scores([s], criteria)[0]
    # 0.8*30 + 0.6*20 + 1.0*20 + 0.5*20 + 0*10 = 24 + 12 + 20 + 10 + 0
    assert out["absolute_score"] == pytest.approx(66.0)
    assert [r["weighted_points"] for r in out["criteria_results"]] == [24.0, 12.0, 20.0, 10.0, 0.0]


def test_benchmark_gap_relative_and_ppi(criteria):
    a = make_supplier("A", [8, 9, 5, 9, 7], criteria_defs=criteria)
    b = make_supplier("B", [6, 9, 10, 3, 7], criteria_defs=criteria)
    res = ranking_tool.run_all([a, b], criteria)
    bench = res["benchmarks"]
    assert [bench[i]["benchmark_score"] for i in range(1, 6)] == [8, 9, 10, 9, 7]
    assert bench[2]["leaders"] == ["A", "B"]          # shared benchmark
    ranked = {r["supplier_name"]: r for r in res["ranked"]}
    gaps_b = [r["gap"] for r in ranked["B"]["criteria_results"]]
    assert gaps_b == [-2, 0, 0, -6, 0]
    rel_a = [r["relative_pct"] for r in ranked["A"]["criteria_results"]]
    assert rel_a == pytest.approx([100, 100, 50, 100, 100])
    # PPI(A) = (100*30 + 100*20 + 50*20 + 100*20 + 100*10) / 100 = 90
    assert ranked["A"]["ppi"] == pytest.approx(90.0)
    # PPI(B) = (75*30 + 100*20 + 100*20 + 33.333*20 + 100*10) / 100
    assert ranked["B"]["ppi"] == pytest.approx(round((75 * 30 + 2000 + 2000 + 100 / 3 * 20 + 1000) / 100, 4))
    assert ranked["A"]["final_rank"] == 1


def test_zero_benchmark_gives_100_percent(criteria):
    a = make_supplier("A", [5, 5, 0, 5, 5], criteria_defs=criteria)
    b = make_supplier("B", [4, 4, 0, 4, 4], criteria_defs=criteria)
    res = ranking_tool.run_all([a, b], criteria)
    for r in res["ranked"]:
        commercial = r["criteria_results"][2]
        assert commercial["benchmark_score"] == 0
        assert commercial["relative_pct"] == 100
        assert commercial["gap"] == 0


def _ranks(suppliers, criteria):
    return [r["supplier_name"] for r in ranking_tool.run_all(suppliers, criteria)["ranked"]]


def test_tie_break_submission_date(criteria):
    a = make_supplier("Alpha", [7] * 5, "2026-10-12", 90, criteria)
    b = make_supplier("Beta", [7] * 5, "2026-10-09", 10, criteria)
    res = ranking_tool.run_all([a, b], criteria)
    assert [r["supplier_name"] for r in res["ranked"]] == ["Beta", "Alpha"]
    assert res["tie_breaks"][0]["deciding_rule"] == 2


def test_tie_break_experience(criteria):
    a = make_supplier("Alpha", [7] * 5, "2026-10-10", 60, criteria)
    b = make_supplier("Beta", [7] * 5, "2026-10-10", 80, criteria)
    res = ranking_tool.run_all([a, b], criteria)
    assert [r["supplier_name"] for r in res["ranked"]] == ["Beta", "Alpha"]
    assert res["tie_breaks"][0]["deciding_rule"] == 3


def test_tie_break_name(criteria):
    a = make_supplier("zeta corp", [7] * 5, "2026-10-10", 60, criteria)
    b = make_supplier("Alpha", [7] * 5, "2026-10-10", 60, criteria)
    res = ranking_tool.run_all([a, b], criteria)
    assert [r["supplier_name"] for r in res["ranked"]] == ["Alpha", "zeta corp"]  # case-insensitive A-Z
    assert res["tie_breaks"][0]["deciding_rule"] == 4


def test_ppi_beats_absolute_score_and_ranks_are_sequential(criteria):
    # Same PPI can come from different absolute scores; ranks must still be 1..N with no gaps
    sups = [make_supplier(f"S{i}", [i % 10, 5, 5, 5, 5], "2026-10-10", 50, criteria) for i in range(6)]
    ranked = ranking_tool.run_all(sups, criteria)["ranked"]
    assert [r["final_rank"] for r in ranked] == list(range(1, 7))
    ppis = [r["ppi"] for r in ranked]
    assert ppis == sorted(ppis, reverse=True)


def test_ordering_is_independent_of_input_order(criteria):
    sups = [
        make_supplier("A", [7] * 5, "2026-10-10", 50, criteria),
        make_supplier("B", [7] * 5, "2026-10-10", 50, criteria),
        make_supplier("C", [7] * 5, "2026-10-09", 50, criteria),
        make_supplier("D", [9, 7, 7, 7, 7], "2026-10-15", 10, criteria),
        make_supplier("E", [7] * 5, "2026-10-10", 70, criteria),
    ]
    expected = _ranks(sups, criteria)
    assert expected == ["D", "C", "E", "A", "B"]
    rng = random.Random(7)
    for _ in range(20):
        shuffled = sups[:]
        rng.shuffle(shuffled)
        assert _ranks(shuffled, criteria) == expected


def test_float_noise_does_not_break_ties(criteria):
    # 0.1+0.2 style float noise must not separate two suppliers whose PPI is mathematically equal
    crit = [{"criterion_id": 1, "name": "X", "description": "x", "weight": 100 / 3, "max_score": 10},
            {"criterion_id": 2, "name": "Y", "description": "y", "weight": 100 / 3, "max_score": 10},
            {"criterion_id": 3, "name": "Z", "description": "z", "weight": 100 / 3, "max_score": 10}]
    a = make_supplier("Late", [3, 6, 9], "2026-10-12", 50, crit)
    b = make_supplier("Early", [9, 6, 3], "2026-10-01", 50, crit)
    res = ranking_tool.run_all([a, b], crit)
    assert res["ranked"][0]["ppi"] == res["ranked"][1]["ppi"]
    assert [r["supplier_name"] for r in res["ranked"]] == ["Early", "Late"]
