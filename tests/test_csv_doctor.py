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


def test_word_like_date_in_name_is_not_a_date_column():
    # "candidate" contains "date" but is not a date; 2 of 10 values look like dates
    vals = ["2024-01-01", "2024-01-02"] + ["Ann", "Bo", "Cy", "Di", "Ed", "Flo", "Gus", "Hal"]
    for name in ["candidate", "update", "validate"]:
        c = analyze(frame(**{name: vals})).columns[0]
        assert c.facts.kind == "text"
    cleaned, log = clean(frame(candidate=vals))
    assert cleaned["candidate"].tolist() == vals and log.empty
    assert analyze(frame(order_date=vals)).columns[0].facts.kind == "text"  # 20% is below the 30% bar
    assert analyze(frame(startDate=["2024-01-01", "2024-01-02", "2024-01-03", "Ann", "Bo", "Cy", "Di", "Ed"])).columns[0].facts.kind == "date"


def test_id_like_columns_get_no_outlier_flags():
    spread = [str(x) for x in [1, 2, 3, 4, 5, 6, 7, 8, 9, 5000]]
    assert analyze(frame(score=spread)).counts()["outliers (flagged only)"] == 1
    assert analyze(frame(user_id=spread)).counts()["outliers (flagged only)"] == 0
    zeros = ["007", "012", "013", "014", "015", "016", "017", "018", "019", "9999"]
    assert analyze(frame(code=zeros)).counts()["outliers (flagged only)"] == 0
    seq = [str(x) for x in range(1000, 1010)]
    assert analyze(frame(n=seq)).counts()["outliers (flagged only)"] == 0


def test_formula_cells_are_escaped_but_numbers_are_not():
    df = frame(note=["=1+1", "+cmd", "@SUM(A1)", "-hello", "fine"], amt=["-5", "3", "4", "5", "6"])
    cleaned, log = clean(df)
    assert cleaned["note"].tolist() == ["'=1+1", "'+cmd", "'@SUM(A1)", "'-hello", "fine"]
    assert cleaned["amt"].tolist() == ["-5", "3", "4", "5", "6"]
    assert (log["step"] == "escape_formula").sum() == 4
    raw, raw_log = clean(df, safe=False)
    assert raw["note"].tolist()[0] == "=1+1" and raw_log.empty


def test_cli_output_names_for_odd_paths(tmp_path):
    src = tmp_path / "data.csv"
    src.write_bytes(SAMPLE.read_bytes())
    r = runner.invoke(app, ["clean", str(src), "-o", str(tmp_path / "v1.2.csv")])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "v1.2.changes.csv").exists() and (tmp_path / "v1.2.report.md").exists()
    r = runner.invoke(app, ["clean", str(src), "-o", str(tmp_path / "result")])  # no extension
    assert r.exit_code == 0, r.output
    assert (tmp_path / "result").is_file() and (tmp_path / "result.changes.csv").is_file()
