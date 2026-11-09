"""Turn a Profile into Markdown."""
from __future__ import annotations

import pandas as pd

from .analyze import Profile

EXAMPLES = 5


def _md(v: object) -> str:
    return "`" + str(v).replace("|", "\\|").replace("`", "'") + "`"


def _rows(items: list[tuple[int, str]]) -> str:
    shown = ", ".join(f"row {i + 1}: {_md(v)}" for i, v in items[:EXAMPLES])
    more = len(items) - EXAMPLES
    return shown + (f" (+{more} more)" if more > 0 else "")


def profile_markdown(p: Profile, source: str, title: str = "CSV profile") -> str:
    out = [f"# {title}: {source}", "", f"{p.n_rows} rows, {len(p.columns)} columns.", ""]
    out += ["## Issue counts", "", "| Issue | Count |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in p.counts().items()]
    out += ["", "## Columns", "", "| Column | Type | Missing | Unique | Issues |", "|---|---|---|---|---|"]
    for c in p.columns:
        f = c.facts
        issues = []
        if c.n_whitespace:
            issues.append(f"{c.n_whitespace} whitespace")
        if c.n_case_cells:
            issues.append(f"{c.n_case_cells} casing")
        if f.conflicts:
            issues.append(f"{len(f.conflicts)} mixed-type")
        if f.bad_dates:
            issues.append(f"{len(f.bad_dates)} bad date")
        if f.outliers:
            issues.append(f"{len(f.outliers)} outlier")
        out.append(f"| {_md(c.name)} | {f.kind} | {c.n_null} | {c.n_unique} | {', '.join(issues) or 'none'} |")

    detail = _details(p)
    if detail:
        out += ["", "## Details (first few examples)", ""] + detail
    return "\n".join(out) + "\n"


def _details(p: Profile) -> list[str]:
    detail = []
    if p.exact_duplicates:
        detail.append(f"- Exact duplicate rows: {', '.join(str(i + 1) for i in p.exact_duplicates[:10])}")
    if p.near_duplicates:
        detail.append(
            f"- Near-duplicate rows (differ only by case, spaces or missing-value spelling): "
            f"{', '.join(str(i + 1) for i in p.near_duplicates[:10])}"
        )
    for c in p.columns:
        f = c.facts
        for g in f.case_groups:
            variants = ", ".join(f"{_md(v)} x{n}" for v, n in g.items())
            detail.append(f"- {_md(c.name)} casing: {variants}")
        if f.conflicts:
            what = "not a number" if f.kind == "numeric" else "number in a text column"
            detail.append(f"- {_md(c.name)} mixed types ({what}): {_rows(f.conflicts)}")
        if f.bad_dates:
            detail.append(f"- {_md(c.name)} bad dates: {_rows(f.bad_dates)}")
        if f.outliers:
            lo, hi = f.bounds
            detail.append(
                f"- {_md(c.name)} outliers outside {lo:g} to {hi:g} (1.5 x IQR): {_rows(f.outliers)}"
            )
    return detail


def clean_markdown(
    before: Profile, after: Profile, log: pd.DataFrame, source: str, output: str, log_path: str, dayfirst: bool
) -> str:
    b, a = before.counts(), after.counts()
    out = [
        f"# CSV clean report: {source}",
        "",
        f"- Input (not modified): {_md(source)}, {before.n_rows} rows",
        f"- Cleaned output: {_md(output)}, {after.n_rows} rows",
        f"- Change log: {_md(log_path)}, {len(log)} changes",
        f"- Ambiguous dates like 03/04/2024 read as {'day first' if dayfirst else 'month first'}",
        "",
        "## Before and after",
        "",
        "| Issue | Before | After |",
        "|---|---|---|",
    ]
    out += [f"| {k} | {b[k]} | {a[k]} |" for k in b]
    out += ["", "## Changes by step", "", "| Step | Changes |", "|---|---|"]
    steps = log["step"].value_counts()
    out += [f"| {s} | {n} |" for s, n in steps.items()] or ["| (none) | 0 |"]
    out += [
        "",
        "Outliers are flagged, not changed. Mixed-type values in a text column are flagged, not changed.",
        "",
        "## What is still flagged in the cleaned file",
        "",
    ]
    out += _details(after) or ["Nothing."]
    return "\n".join(out) + "\n"
