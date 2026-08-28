"""A single-organ calibration run must not delete the other organs' results.

Found 2026-08-28 by running `--organ kidney` and diffing the report: five rows
disappeared. CLAUDE.md records the softer version of this ("run-center-
calibration.py defaults to --organ lung, so five of six organs were never
recomputed"), but the rows were not merely stale — `write_report` rebuilt the
table from the current run's results alone, so they were gone, and what
remained still read as a complete report for the organ you happened to run.

Merging alone would trade a visible deletion for an invisible staleness, so
rows carried over from an earlier run are marked with a dagger and the fresh
ones are dated. Both halves are pinned here: nothing is dropped, and nothing
carried over is passed off as freshly computed.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run-center-calibration.py"
REPORT = REPO / "docs" / "center-calibration-report.md"
ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]

ROW = re.compile(r"^\|\s*([a-z]+)(†?)\s*\|")


def _rows(text):
    out = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m and m.group(1) in ORGANS:
            out[m.group(1)] = bool(m.group(2))
    return out


@pytest.fixture(scope="module")
def mod():
    sys.path.insert(0, str(REPO / "scripts"))
    sys.path.insert(0, str(REPO / "backend"))
    try:
        spec = importlib.util.spec_from_file_location("run_cal", SCRIPT)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        sys.path.remove(str(REPO / "scripts"))
        sys.path.remove(str(REPO / "backend"))


def _fake_result(organ, n=200):
    return {
        "organ": organ,
        "matched_centers": n,
        "stats": {
            "spearman_p12_vs_txrate": {"rho": 0.5, "p_value": 0.001},
            "spearman_wait_vs_txrate": {"rho": -0.5, "p_value": 0.001},
        },
    }


def test_the_committed_report_covers_every_organ():
    """The premise: if the shipped report is already partial, the merge below
    is preserving a hole rather than preventing one."""
    rows = _rows(REPORT.read_text(encoding="utf-8"))
    assert set(rows) == set(ORGANS), f"report is missing {set(ORGANS) - set(rows)}"


def test_a_single_organ_run_keeps_the_other_five(mod, tmp_path, monkeypatch):
    report = tmp_path / "center-calibration-report.md"
    report.write_text(REPORT.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(mod, "REPORT_PATH", report)

    mod.write_report([_fake_result("kidney", 229)])

    rows = _rows(report.read_text(encoding="utf-8"))
    assert set(rows) == set(ORGANS), (
        f"a kidney-only run dropped {set(ORGANS) - set(rows)} from the report"
    )
    assert rows["kidney"] is False, "the organ just computed must not be marked stale"
    for organ in ORGANS:
        if organ != "kidney":
            assert rows[organ] is True, (
                f"{organ} was carried over from a previous run but is not marked — "
                "it reads as freshly computed"
            )


def test_an_all_organ_run_marks_nothing_stale(mod, tmp_path, monkeypatch):
    report = tmp_path / "center-calibration-report.md"
    report.write_text(REPORT.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(mod, "REPORT_PATH", report)

    mod.write_report([_fake_result(o) for o in ORGANS])

    rows = _rows(report.read_text(encoding="utf-8"))
    assert set(rows) == set(ORGANS)
    assert not any(rows.values()), "a full run should leave no organ marked stale"
    assert "†" not in report.read_text(encoding="utf-8")


def test_repeated_single_organ_runs_do_not_accumulate_daggers(mod, tmp_path, monkeypatch):
    report = tmp_path / "center-calibration-report.md"
    report.write_text(REPORT.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(mod, "REPORT_PATH", report)

    for _ in range(3):
        mod.write_report([_fake_result("kidney", 229)])

    text = report.read_text(encoding="utf-8")
    assert "††" not in text, "the stale marker is being re-applied to already-marked rows"
    assert set(_rows(text)) == set(ORGANS)


def test_every_row_has_the_full_column_count(mod, tmp_path, monkeypatch):
    """A row one cell short renders with a silently missing date rather than
    an obviously absent one.

    Built from a LEGACY 6-column report on purpose. Using the current report
    as the fixture proves nothing: it already carries the date column, so the
    padding never engages and the test passes with the padding deleted.
    """
    legacy = "\n".join([
        "| Organ | Centers | ρ (p12 vs tx-rate) | p | ρ (wait vs tx-rate) | p |",
        "|-------|---------|--------------------|---|---------------------|---|",
        *[f"| {o} | 100 | 0.5 | <0.001 | -0.5 | <0.001 |" for o in ORGANS],
        "",
    ])
    report = tmp_path / "center-calibration-report.md"
    report.write_text(legacy, encoding="utf-8")
    monkeypatch.setattr(mod, "REPORT_PATH", report)

    mod.write_report([_fake_result("kidney", 229)])

    text = report.read_text(encoding="utf-8")
    header = next(l for l in text.splitlines() if l.startswith("| Organ |"))
    want = len(header.strip().strip("|").split("|"))
    assert want == 7
    for line in text.splitlines():
        if ROW.match(line) and ROW.match(line).group(1) in ORGANS:
            got = len(line.strip().strip("|").split("|"))
            assert got == want, f"ragged row ({got} of {want} cells): {line}"


class _FakeCenter:
    def __init__(self, code):
        self.center_code = code
        self.center_name = code
        self.p_transplant_12mo = 0.5
        self.median_wait_months = 12.0


class _FakeResult:
    def __init__(self, codes):
        self.cities = [_FakeCenter(c) for c in codes]


@pytest.mark.parametrize("organ", ORGANS)
def test_calibration_refuses_a_shrunken_ground_truth(mod, tmp_path, monkeypatch, organ):
    """Behavioural, not a source grep.

    The join skips centers absent from the observed file, so a truncated
    ground truth narrows the cohort instead of failing — and still yields a
    respectable rho. Every organ needs its own floor: a missing key falls back
    to 10, which no realistic truncation would trip.
    """
    import json
    observed = json.loads(
        (REPO / "data" / "srtr-observed-rates.json").read_text(encoding="utf-8"))
    codes = list(observed[organ]["centers"])

    thin = {organ: {"centers": dict(list(observed[organ]["centers"].items())[:5])}}
    path = tmp_path / "srtr-observed-rates.json"
    path.write_text(json.dumps(thin), encoding="utf-8")
    monkeypatch.setattr(mod, "OBSERVED_PATH", path)
    monkeypatch.setattr(mod, "simulate", lambda *a, **k: _FakeResult(codes))

    with pytest.raises(SystemExit) as exc:
        mod.calibrate(organ)
    assert "REFUSING to report" in str(exc.value)


@pytest.mark.parametrize("organ", ORGANS)
def test_calibration_still_runs_on_the_real_ground_truth(mod, monkeypatch, organ):
    """The counterweight. A floor set too high would block every real run,
    and the margin on intestine (17 centers) is thin enough to matter."""
    import json
    observed = json.loads(
        (REPO / "data" / "srtr-observed-rates.json").read_text(encoding="utf-8"))
    codes = list(observed[organ]["centers"])
    monkeypatch.setattr(mod, "simulate", lambda *a, **k: _FakeResult(codes))

    res = mod.calibrate(organ)
    assert res["matched_centers"] == len(codes)
