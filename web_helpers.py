"""Helpers for the Gradio demo. No gradio import here, so tests run without it. Uploads are read once and never saved."""
from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from csv_doctor.analyze import analyze
from csv_doctor.clean import clean, escape_formula
from csv_doctor.report import profile_markdown

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 100_000
PREVIEW_ROWS = 200
LOG_PREVIEW_ROWS = 500
SAMPLE = Path(__file__).parent / "examples" / "messy_orders_synthetic.csv"


class InputError(ValueError):
    """The file cannot be used. The message is shown to the user as is."""


@dataclass
class Outcome:
    status: str
    profile_md: str = ""
    preview: pd.DataFrame = field(default_factory=pd.DataFrame)
    log_preview: pd.DataFrame = field(default_factory=pd.DataFrame)
    cleaned_path: str | None = None
    log_path: str | None = None


def parse_csv_bytes(data: bytes) -> pd.DataFrame:
    """Same read settings as the CLI (all text, no NA guessing), plus the demo limits."""
    if not data:
        raise InputError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise InputError(f"The file is {len(data) / 2**20:.1f} MB. The limit is {MAX_BYTES // 2**20} MB.")
    if b"\x00" in data[:8192]:
        raise InputError("This does not look like a text CSV (it has binary content).")
    try:
        df = pd.read_csv(
            io.BytesIO(data), dtype=str, keep_default_na=False, na_values=[], encoding="utf-8-sig", nrows=MAX_ROWS + 1
        )
    except UnicodeDecodeError:
        raise InputError("The file is not valid UTF-8 text. Save it as CSV (UTF-8) and try again.")
    except pd.errors.EmptyDataError:
        raise InputError("The file is empty.")
    except pd.errors.ParserError as e:
        raise InputError(f"Could not read this as a CSV: {e}")
    if not isinstance(df.index, pd.RangeIndex):
        raise InputError("Some rows have more fields than the header. Fix the file and try again.")
    if len(df) > MAX_ROWS:
        raise InputError(f"The file has more than {MAX_ROWS:,} rows. The limit is {MAX_ROWS:,}.")
    if df.empty:
        raise InputError("The file has a header but no data rows.")
    return df


def read_csv_file(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() != ".csv":
        raise InputError(f"{p.name} is not a .csv file. Upload a file that ends in .csv.")
    try:
        size = p.stat().st_size
        if size > MAX_BYTES:  # check before reading the bytes
            raise InputError(f"The file is {size / 2**20:.1f} MB. The limit is {MAX_BYTES // 2**20} MB.")
        return parse_csv_bytes(p.read_bytes())
    except OSError as e:
        raise InputError(f"Could not read the file: {e.strerror or e}")


def run(path: str | Path | None, dayfirst: bool = True) -> Outcome:
    """Profile and clean one CSV. Never raises for bad input: the problem goes in Outcome.status."""
    if not path:
        return Outcome("Choose a CSV file first, or load the sample.")
    name = Path(path).name
    try:
        df = read_csv_file(path)
        profile = analyze(df, dayfirst)
        cleaned, log = clean(df, dayfirst, True)
    except InputError as e:
        return Outcome(f"Rejected: {e}")
    except Exception as e:  # trust boundary: show a short message, not a traceback
        return Outcome(f"Could not process this file ({type(e).__name__}).")

    # same spreadsheet-formula escaping as `csv-doctor clean`
    cleaned = cleaned.rename(columns=escape_formula)
    log = log.assign(**{c: log[c].map(escape_formula) for c in ("column", "old", "new")})

    out_dir = Path(tempfile.mkdtemp(prefix="csv_doctor_"))  # temp only; the OS clears it
    stem = Path(name).stem
    cleaned_path, log_path = out_dir / f"{stem}.clean.csv", out_dir / f"{stem}.changes.csv"
    cleaned.to_csv(cleaned_path, index=False, encoding="utf-8")
    log.to_csv(log_path, index=False, encoding="utf-8")

    status = f"{len(df)} rows in, {len(cleaned)} rows out, {len(log)} changes."
    if len(cleaned) > PREVIEW_ROWS or len(log) > LOG_PREVIEW_ROWS:
        status += " Tables show the first rows only; the downloads have everything."
    return Outcome(
        status,
        profile_markdown(profile, name),
        cleaned.head(PREVIEW_ROWS),
        log.head(LOG_PREVIEW_ROWS),
        str(cleaned_path),
        str(log_path),
    )


def run_sample(dayfirst: bool = True) -> Outcome:
    return run(SAMPLE, dayfirst)
