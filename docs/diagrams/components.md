# Components

Modules in `src/csv_doctor` and what each one imports.

```mermaid
flowchart TD
    user["User: csv-doctor profile / clean"] --> cli["cli.py<br/>Typer app: profile, clean"]
    main["__main__.py"] --> cli
    cli --> analyze["analyze.py<br/>analyze, inspect_column"]
    cli --> clean["clean.py<br/>clean, escape_formula"]
    cli --> report["report.py<br/>profile_markdown, clean_markdown"]
    clean --> analyze
    report --> analyze
    cli -->|reads| infile[("input .csv<br/>never written")]
    cli -->|writes| outcsv[("cleaned .csv")]
    cli -->|writes| changes[("name.changes.csv")]
    cli -->|writes| rep[("name.report.md")]
```

Sources: [cli.py](../../src/csv_doctor/cli.py), [analyze.py](../../src/csv_doctor/analyze.py), [clean.py](../../src/csv_doctor/clean.py), [report.py](../../src/csv_doctor/report.py), [__main__.py](../../src/csv_doctor/__main__.py).

# Data classes

The dataclasses that `analyze` returns and `report` reads.

```mermaid
classDiagram
    class Profile {
        n_rows
        columns
        exact_duplicates
        near_duplicates
        counts()
    }
    class ColumnProfile {
        name
        facts
        n_null
        n_unique
        n_whitespace
        n_case_cells
    }
    class ColumnFacts {
        kind
        conflicts
        bad_dates
        dates
        case_map
        case_groups
        outliers
        bounds
    }
    Profile "1" *-- "many" ColumnProfile
    ColumnProfile "1" *-- "1" ColumnFacts
```

Source: [analyze.py](../../src/csv_doctor/analyze.py).
