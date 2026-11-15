# Column logic

## How a column is classified

How `inspect_column` picks a column kind and what it flags. Empty cells are skipped. Shares are over non-empty cells.

```mermaid
flowchart TD
    s["non-empty cells"] --> e{"any cells?"}
    e -->|no| empty["kind: empty"]
    e -->|yes| d{"date-like share >= 0.5<br/>or name has 'date' and share >= 0.3"}
    d -->|yes| date["kind: date<br/>bad_dates, dates"]
    d -->|no| n{"number share >= 0.5"}
    n -->|yes| num["kind: numeric<br/>conflicts, outliers by IQR"]
    n -->|no| txt["kind: text<br/>conflicts, case_map"]
```

## What clean does to each column

Steps `clean` applies per column, in order, then to whole rows. Each change goes to the log.

```mermaid
flowchart TD
    a["null token to empty<br/>missing_value"] --> b["squash whitespace<br/>trim_whitespace"]
    b --> c["inspect_column"]
    c --> d["bad dates emptied: bad_date<br/>dates to ISO: fix_date"]
    d --> e["numeric column: non-numbers emptied<br/>bad_number"]
    e --> f["variants to common spelling<br/>fix_case"]
    f --> g{"safe?"}
    g -->|yes| h["prefix ' on formula-like text<br/>escape_formula"]
    g -->|no| i["next column"]
    h --> i
    i --> j["after all columns: drop repeat rows<br/>drop_duplicate"]
```

Outliers are flagged only and never changed.

Sources: [analyze.py](../../src/csv_doctor/analyze.py), [clean.py](../../src/csv_doctor/clean.py).
