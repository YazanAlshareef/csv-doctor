# Sequences

## profile command

The `profile` command reads, analyzes and prints. It writes a file only when `-o` is given.

```mermaid
sequenceDiagram
    actor U as User
    participant C as cli.profile
    participant A as analyze.analyze
    participant R as report.profile_markdown
    U->>C: csv-doctor profile data.csv
    C->>C: _read (all columns as text)
    C->>A: analyze(df, dayfirst)
    A-->>C: Profile
    C->>R: profile_markdown(profile, name)
    R-->>C: Markdown text
    C-->>U: print report
    opt -o given
        C->>C: _refuse_input, then _write
    end
```

## clean command

The `clean` command analyzes before and after cleaning, then writes three files.

```mermaid
sequenceDiagram
    actor U as User
    participant C as cli.clean
    participant A as analyze.analyze
    participant K as clean.clean
    participant R as report.clean_markdown
    U->>C: csv-doctor clean data.csv -o out.csv
    C->>C: _refuse_input (out, log, report paths)
    C->>C: _read
    C->>A: analyze(df)
    A-->>C: before
    C->>K: clean(df, dayfirst, safe)
    K-->>C: cleaned frame, change log
    C->>A: analyze(cleaned)
    A-->>C: after
    C->>C: write out.csv and name.changes.csv
    C->>R: clean_markdown(before, after, log, ...)
    R-->>C: Markdown text
    C->>C: write name.report.md
    C-->>U: print report and file paths
```

Sources: [cli.py](../../src/csv_doctor/cli.py), [analyze.py](../../src/csv_doctor/analyze.py), [clean.py](../../src/csv_doctor/clean.py), [report.py](../../src/csv_doctor/report.py).
