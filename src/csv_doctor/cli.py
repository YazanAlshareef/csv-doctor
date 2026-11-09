"""Command line: csv-doctor profile data.csv, csv-doctor clean data.csv -o clean.csv."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import pandas as pd
import typer

from .analyze import analyze
from .clean import clean as run_clean
from .report import clean_markdown, profile_markdown

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
    return df.fillna("")


def _refuse_input(src: Path, *targets: Path) -> None:
    for t in targets:
        if t.resolve() == src.resolve():
            typer.echo(f"Refusing to overwrite the input file: {src}", err=True)
            raise typer.Exit(2)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
) -> None:
    """Write a cleaned copy of PATH, plus <output>.changes.csv (every change) and <output>.report.md."""
    out = output or path.with_name(f"{path.stem}.clean.csv")
    log_path = out.with_suffix(".changes.csv")
    report_path = out.with_suffix(".report.md")
    _refuse_input(path, out, log_path, report_path)

    df = _read(path)
    before = analyze(df, dayfirst)
    cleaned, log = run_clean(df, dayfirst)
    after = analyze(cleaned, dayfirst)

    out.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(out, index=False, encoding="utf-8")
    log.to_csv(log_path, index=False, encoding="utf-8")
    report = clean_markdown(before, after, log, path.name, out.name, log_path.name, dayfirst)
    _write(report_path, report)
    typer.echo(report)
    typer.echo(f"Wrote {out}, {log_path}, {report_path}")
