"""Command line: csv-doctor profile data.csv, csv-doctor clean data.csv -o clean.csv."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Annotated, Optional

import pandas as pd
import typer

from . import __version__
from .analyze import analyze
from .clean import clean as run_clean, escape_formula
from .report import clean_markdown, profile_markdown

def _version(show: bool) -> None:
    if show:
        typer.echo(f"csv-doctor {__version__}")
        raise typer.Exit()


app = typer.Typer(help="Profile and clean messy CSV files. The input file is never modified.", no_args_is_help=True)

InputFile = Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True, help="CSV file to read.")]
DayFirst = Annotated[
    bool, typer.Option("--dayfirst/--monthfirst", help="How to read ambiguous dates like 03/04/2024.")
]


def _read(path: Path) -> pd.DataFrame:
    try:
        # Read everything as text: no silent type guessing, no silent "NA" -> NaN.
        df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[], encoding="utf-8-sig")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as e:
        typer.echo(f"Cannot read {path}: {e}", err=True)
        raise typer.Exit(2)
    if not isinstance(df.index, pd.RangeIndex):
        # Every row has extra fields: pandas hid the leading ones in the index. Put them back.
        cols = list(df.columns)
        extra = ["extra_field"] + [f"extra_field_{i}" for i in range(2, df.index.nlevels + 1)]
        typer.echo(f"Warning: rows have more fields than the header; the extra last fields are kept as {', '.join(repr(e) for e in extra)}.", err=True)
        df = df.reset_index(drop=False)
        df.columns = [*cols, *extra]
    _warn_renamed_headers(path, df)
    return df.fillna("")


def _warn_renamed_headers(path: Path, df: pd.DataFrame) -> None:
    """pandas renames blank or repeated headers (b, b.1, Unnamed: 2). Say so instead of doing it silently."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f), [])
    for old, new in zip(header, df.columns):
        if old != new:
            typer.echo(f"Warning: header {old!r} was renamed to {new!r} on read.", err=True)


def _refuse_input(src: Path, *targets: Path) -> None:
    for t in targets:
        if t.resolve() == src.resolve():
            typer.echo(f"Refusing to overwrite the input file: {src}", err=True)
            raise typer.Exit(2)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@app.callback()
def main(
    version: Annotated[bool, typer.Option("--version", callback=_version, is_eager=True, help="Show version and exit.")] = False,
) -> None:
    pass


@app.command()
def profile(
    path: InputFile,
    output: Annotated[Optional[Path], typer.Option("-o", "--output", help="Also save the report here (.md).")] = None,
    dayfirst: DayFirst = True,
) -> None:
    """Print a Markdown report of problems found in PATH. Changes nothing."""
    if output:
        _refuse_input(path, output)
    report = profile_markdown(analyze(_read(path), dayfirst), path.name)
    typer.echo(report)
    if output:
        _write(output, report)


@app.command()
def clean(
    path: InputFile,
    output: Annotated[
        Optional[Path], typer.Option("-o", "--output", help="Cleaned CSV. Default: <name>.clean.csv next to the input.")
    ] = None,
    dayfirst: DayFirst = True,
    safe: Annotated[
        bool, typer.Option("--safe/--no-safe", help="Prefix ' on text cells starting with = + - @ so Excel will not run them.")
    ] = True,
) -> None:
    """Write a cleaned copy of PATH, plus <output>.changes.csv (every change) and <output>.report.md."""
    out = output or path.with_name(f"{path.stem}.clean.csv")
    base = out.stem if out.suffix.lower() == ".csv" else out.name  # v1.2.csv -> v1.2, "clean" -> clean
    log_path = out.with_name(f"{base}.changes.csv")
    report_path = out.with_name(f"{base}.report.md")
    _refuse_input(path, out, log_path, report_path)

    df = _read(path)
    before = analyze(df, dayfirst)
    cleaned, log = run_clean(df, dayfirst, safe)
    after = analyze(cleaned, dayfirst)

    out.parent.mkdir(parents=True, exist_ok=True)
    if safe:  # headers are cells too, and the log holds old values and column names
        cleaned = cleaned.rename(columns=escape_formula)
        log = log.assign(**{c: log[c].map(escape_formula) for c in ("column", "old", "new")})
    cleaned.to_csv(out, index=False, encoding="utf-8")
    log.to_csv(log_path, index=False, encoding="utf-8")
    report = clean_markdown(before, after, log, path.name, out.name, log_path.name, dayfirst)
    _write(report_path, report)
    typer.echo(report)
    typer.echo(f"Wrote {out}, {log_path}, {report_path}")
