"""Fix what analyze finds. Every change goes into a log. Outliers are flagged, never changed."""
from __future__ import annotations

import pandas as pd

from .analyze import inspect_column, is_null, is_number, squash

LOG_COLUMNS = ["row", "column", "step", "old", "new"]


FORMULA_STARTS = ('=', '+', '-', '@', '＠', '＝')  # includes full-width @ and =


def clean(df: pd.DataFrame, dayfirst: bool = True, safe: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (cleaned frame, change log). Row numbers are 1-based data rows, header not counted."""
    out = df.copy()
    log: list[tuple[int, str, str, str, str]] = []

    def change(i: int, col: str, step: str, old: str, new: str) -> None:
        log.append((i + 1, col, step, old, new))

    for col in out.columns:
        name = str(col)
        cells = []
        for i, v in enumerate(out[col].tolist()):
            if is_null(v):
                new = ""
                if v != "":
                    change(i, name, "missing_value", v, "")
            else:
                new = squash(v)
                if new != v:
                    change(i, name, "trim_whitespace", v, new)
            cells.append(new)

        facts = inspect_column(name, cells, dayfirst)
        for i, v in facts.bad_dates:
            cells[i] = ""
            change(i, name, "bad_date", v, "")
        for i, iso in facts.dates.items():
            if cells[i] != iso:
                change(i, name, "fix_date", cells[i], iso)
                cells[i] = iso
        if facts.kind == "numeric":
            for i, v in facts.conflicts:
                cells[i] = ""
                change(i, name, "bad_number", v, "")
        for i, v in enumerate(cells):
            if v in facts.case_map:
                change(i, name, "fix_case", v, facts.case_map[v])
                cells[i] = facts.case_map[v]
        if safe:  # Excel and Sheets run cells that start with these. Negative numbers are fine.
            for i, v in enumerate(cells):
                if v.startswith(FORMULA_STARTS) and not is_number(v):
                    cells[i] = "'" + v
                    change(i, name, "escape_formula", v, cells[i])
        out[col] = cells

    seen: dict[tuple, int] = {}
    drop = []
    for i, row in enumerate(out.itertuples(index=False, name=None)):
        if row in seen:
            drop.append(i)
            change(i, "", "drop_duplicate", "(whole row)", f"same as row {seen[row] + 1}")
        else:
            seen[row] = i
    out = out.drop(index=drop).reset_index(drop=True)

    log_df = pd.DataFrame(log, columns=LOG_COLUMNS).sort_values(["row"], kind="stable", ignore_index=True)
    return out, log_df
