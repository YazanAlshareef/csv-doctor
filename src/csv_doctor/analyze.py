"""Find problems in a CSV. Every cell is read as text so nothing is guessed away."""
from __future__ import annotations

import re
import warnings
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

# Text that means "no value". Limit: a real value of "none" or "-" is treated as missing.
NULL_TOKENS = {"", "na", "n/a", "#n/a", "null", "none", "nan", "-", "?"}

NUMBER = re.compile(r"^[-+]?(\d+(\.\d*)?|\.\d+)$")
DATE_LIKE = [
    re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$"),  # 2024-01-15, 15/01/2024
    re.compile(r"^\d{1,2} [A-Za-z]{3,9},? \d{4}$"),  # 15 Jan 2024
    re.compile(r"^[A-Za-z]{3,9} \d{1,2},? \d{4}$"),  # Jan 15 2024
]
MIN_OUTLIER_VALUES = 8


def squash(v: str) -> str:
    """Trim the ends and collapse runs of whitespace to one space."""
    return " ".join(v.split())


def is_null(v: str) -> bool:
    return v.strip().casefold() in NULL_TOKENS


def is_number(v: str) -> bool:
    return bool(NUMBER.match(v))


def is_date_like(v: str) -> bool:
    return any(p.match(v) for p in DATE_LIKE)


def parse_date(v: str, dayfirst: bool) -> str | None:
    """Return an ISO date (YYYY-MM-DD) or None if v is not a real date."""
    if not is_date_like(v):
        return None
    if re.match(r"^\d{4}\D", v):
        dayfirst = False  # year first (2024-02-05) is never day-first; pandas would swap month and day
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ts = pd.to_datetime(v, dayfirst=dayfirst, errors="coerce", format="mixed")
    return None if pd.isna(ts) else ts.strftime("%Y-%m-%d")


@dataclass
class ColumnFacts:
    """What we learned about one column. Row numbers are 0-based here."""

    kind: str = "empty"  # empty | numeric | date | text
    conflicts: list[tuple[int, str]] = field(default_factory=list)  # wrong type for the column
    bad_dates: list[tuple[int, str]] = field(default_factory=list)
    dates: dict[int, str] = field(default_factory=dict)  # row -> ISO date
    case_map: dict[str, str] = field(default_factory=dict)  # variant -> canonical spelling
    case_groups: list[dict[str, int]] = field(default_factory=list)
    outliers: list[tuple[int, str]] = field(default_factory=list)
    bounds: tuple[float, float] | None = None


def inspect_column(name: str, cells: list[str], dayfirst: bool = True) -> ColumnFacts:
    """cells must already be trimmed, with "" for missing."""
    facts = ColumnFacts()
    present = [(i, v) for i, v in enumerate(cells) if v]
    if not present:
        return facts

    n = len(present)
    date_share = sum(is_date_like(v) for _, v in present) / n
    num_share = sum(is_number(v) for _, v in present) / n

    if date_share >= 0.5 or ("date" in name.lower() and date_share >= 0.2):
        facts.kind = "date"
        for i, v in present:
            iso = parse_date(v, dayfirst)
            if iso is None:
                facts.bad_dates.append((i, v))
            else:
                facts.dates[i] = iso
    elif num_share >= 0.5:
        facts.kind = "numeric"
        facts.conflicts = [(i, v) for i, v in present if not is_number(v)]
        nums = [(i, v) for i, v in present if is_number(v)]
        if len(nums) >= MIN_OUTLIER_VALUES:
            s = pd.Series([float(v) for _, v in nums])
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                facts.bounds = (float(lo), float(hi))
                facts.outliers = [(i, v) for (i, v), x in zip(nums, s) if x < lo or x > hi]
    else:
        facts.kind = "text"
        facts.conflicts = [(i, v) for i, v in present if is_number(v)]
        groups: dict[str, Counter] = {}
        for _, v in present:
            groups.setdefault(v.casefold(), Counter())[v] += 1
        for variants in groups.values():
            if len(variants) > 1:
                # Most common spelling wins. On a tie prefer mixed case ("Sydney") over ALL or none.
                best = min(variants, key=lambda v: (-variants[v], v.isupper() or v.islower(), v))
                facts.case_groups.append(dict(variants))
                facts.case_map.update({v: best for v in variants if v != best})
    return facts


@dataclass
class ColumnProfile:
    name: str
    facts: ColumnFacts
    n_null: int
    n_unique: int
    n_whitespace: int

    @property
    def n_case_cells(self) -> int:
        return sum(sum(g.values()) - max(g.values()) for g in self.facts.case_groups)


@dataclass
class Profile:
    n_rows: int
    columns: list[ColumnProfile]
    exact_duplicates: list[int]  # 0-based rows that repeat an earlier row exactly
    near_duplicates: list[int]  # repeat an earlier row once case/whitespace/nulls are ignored

    def counts(self) -> dict[str, int]:
        cols = self.columns
        return {
            "missing values": sum(c.n_null for c in cols),
            "duplicate rows (exact)": len(self.exact_duplicates),
            "duplicate rows (near)": len(self.near_duplicates),
            "extra whitespace cells": sum(c.n_whitespace for c in cols),
            "inconsistent casing cells": sum(c.n_case_cells for c in cols),
            "mixed-type values": sum(len(c.facts.conflicts) for c in cols),
            "bad dates": sum(len(c.facts.bad_dates) for c in cols),
            "outliers (flagged only)": sum(len(c.facts.outliers) for c in cols),
        }


def _norm_row(row: tuple[str, ...]) -> tuple[str, ...]:
    return tuple("" if is_null(v) else squash(v).casefold() for v in row)


def analyze(df: pd.DataFrame, dayfirst: bool = True) -> Profile:
    """df must hold only strings (read with dtype=str, keep_default_na=False)."""
    columns = []
    for name in df.columns:
        raw = df[name].tolist()
        n_ws = sum(1 for v in raw if not is_null(v) and v != squash(v))
        cells = ["" if is_null(v) else squash(v) for v in raw]
        facts = inspect_column(str(name), cells, dayfirst)
        columns.append(
            ColumnProfile(
                name=str(name),
                facts=facts,
                n_null=sum(1 for v in raw if is_null(v)),
                n_unique=len({c for c in cells if c}),
                n_whitespace=n_ws,
            )
        )

    exact_seen, norm_seen = set(), set()
    exact_dups, near_dups = [], []
    for i, row in enumerate(df.itertuples(index=False, name=None)):
        if row in exact_seen:
            exact_dups.append(i)
        elif _norm_row(row) in norm_seen:
            near_dups.append(i)
        exact_seen.add(row)
        norm_seen.add(_norm_row(row))
    return Profile(len(df), columns, exact_dups, near_dups)
