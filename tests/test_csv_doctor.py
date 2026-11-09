from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from csv_doctor.analyze import analyze, parse_date
from csv_doctor.clean import clean
from csv_doctor.cli import app

SAMPLE = Path(__file__).parent.parent / "examples" / "messy_orders_synthetic.csv"
runner = CliRunner()


def frame(**cols):
    return pd.DataFrame(cols, dtype=str)


def test_parse_date_formats():
    assert parse_date("2024-02-05", dayfirst=True) == "2024-02-05"  # ISO is never day-first
    assert parse_date("05/02/2024", dayfirst=True) == "2024-02-05"
    assert parse_date("05/02/2024", dayfirst=False) == "2024-05-02"
    assert parse_date("Jan 20 2024", dayfirst=True) == "2024-01-20"
    assert parse_date("2024-02-30", dayfirst=True) is None
    assert parse_date("hello", dayfirst=True) is None


def test_analyze_finds_each_problem():
    df = frame(
        city=["Sydney", "sydney", " Perth", "N/A", "Sydney", "Sydney"],
        n=["1", "2", "3", "4", "abc", "5"],
        d=["2024-01-01", "01/02/2024", "x", "2024-01-04", "2024-01-05", "2024-01-06"],
    )
    c = analyze(df).counts()
    assert c["missing values"] == 1
    assert c["inconsistent casing cells"] == 1
    assert c["extra whitespace cells"] == 1
    assert c["mixed-type values"] == 1
    assert c["bad dates"] == 1


def test_outlier_flagged_not_changed():
    vals = [str(x) for x in [10, 11, 12, 13, 14, 15, 16, 17, 18, 5000]]
    df = frame(v=vals)
    assert analyze(df).counts()["outliers (flagged only)"] == 1
    cleaned, log = clean(df)
    assert cleaned["v"].tolist() == vals
    assert log.empty


def test_clean_fixes_and_logs_everything():
    df = frame(a=["x ", "X", "x", "NA"], b=["1", "2", "3", "4"])
    cleaned, log = clean(df)
    assert cleaned["a"].tolist() == ["x", "x", "x", ""]  # one spelling wins; "NA" becomes empty
    assert set(log["step"]) <= {"trim_whitespace", "fix_case", "missing_value", "drop_duplicate"}
    assert (log["step"] == "missing_value").sum() == 1
    assert len(df) - len(cleaned) == (log["step"] == "drop_duplicate").sum()


def test_clean_is_idempotent():
    df = pd.read_csv(SAMPLE, dtype=str, keep_default_na=False)
    once, log1 = clean(df)
    twice, log2 = clean(once)
    assert not log1.empty
    assert log2.empty
    assert once.equals(twice)


def test_cli_never_touches_input(tmp_path):
    src = tmp_path / "data.csv"
    src.write_bytes(SAMPLE.read_bytes())
    before = src.read_bytes()
    out = tmp_path / "clean.csv"
    r = runner.invoke(app, ["clean", str(src), "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert src.read_bytes() == before
    assert out.exists() and out.with_suffix(".changes.csv").exists() and out.with_suffix(".report.md").exists()


def test_cli_refuses_to_overwrite_input(tmp_path):
    src = tmp_path / "data.csv"
    src.write_bytes(SAMPLE.read_bytes())
    before = src.read_bytes()
    r = runner.invoke(app, ["clean", str(src), "-o", str(src)])
    assert r.exit_code == 2
    assert src.read_bytes() == before
    r = runner.invoke(app, ["profile", str(src), "-o", str(src)])
    assert r.exit_code == 2
    assert src.read_bytes() == before


def test_cli_profile_prints_report():
    r = runner.invoke(app, ["profile", str(SAMPLE)])
    assert r.exit_code == 0
    assert "Issue counts" in r.output and "bad dates" in r.output


def test_cli_empty_file(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("")
    assert runner.invoke(app, ["profile", str(p)]).exit_code == 2
