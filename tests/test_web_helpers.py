import pandas as pd
import pytest

import web_helpers as wh


def write(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_sample_loads_and_cleans():
    o = wh.run_sample()
    assert o.cleaned_path and o.log_path
    assert o.status == "25 rows in, 23 rows out, 37 changes."
    assert "order_date" in o.profile_md
    assert len(pd.read_csv(o.cleaned_path)) == 23
    assert len(pd.read_csv(o.log_path)) == 37


def test_size_cap_real_limit():
    with pytest.raises(wh.InputError, match="5 MB"):
        wh.parse_csv_bytes(b"a\n" + b"x" * (wh.MAX_BYTES + 1))


def test_row_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(wh, "MAX_ROWS", 3)
    with pytest.raises(wh.InputError, match="more than 3 rows"):
        wh.parse_csv_bytes(b"a\n1\n2\n3\n4\n")
    assert len(wh.parse_csv_bytes(b"a\n1\n2\n3\n")) == 3  # exactly at the cap is fine


def test_not_csv_extension(tmp_path):
    o = wh.run(write(tmp_path, "notes.txt", b"a,b\n1,2\n"))
    assert "not a .csv" in o.status and o.cleaned_path is None


def test_garbled_input(tmp_path):
    assert "binary" in wh.run(write(tmp_path, "x.csv", b"\x89PNG\r\n\x1a\n\x00\x00junk")).status
    assert "UTF-8" in wh.run(write(tmp_path, "y.csv", b"a,b\n\xff\xfe,2\n")).status


def test_empty_file(tmp_path):
    assert "empty" in wh.run(write(tmp_path, "e.csv", b"")).status
    assert "empty" in wh.run(write(tmp_path, "w.csv", b"  \n")).status
    assert "no data rows" in wh.run(write(tmp_path, "h.csv", b"a,b\n")).status


def test_ragged_rows_rejected(tmp_path):
    assert "more fields" in wh.run(write(tmp_path, "r.csv", b"a,b\n1,2,3\n4,5,6\n")).status


def test_no_file_and_missing_file(tmp_path):
    assert "Choose" in wh.run(None).status
    assert "Could not read" in wh.run(tmp_path / "gone.csv").status


def test_formulas_escaped_in_download(tmp_path):
    o = wh.run(write(tmp_path, "f.csv", b"a,b\n=1+1,x\n"))
    assert "'=1+1" in open(o.cleaned_path, encoding="utf-8").read()
