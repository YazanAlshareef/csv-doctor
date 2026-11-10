# Walkthrough

Plain-English tour of each file, so you can explain it in an interview.

## The idea

Two commands. `profile` reads a CSV and reports problems. `clean` fixes what can be fixed safely, logs each fix, and writes a new file. The input is never touched.

All data is read as text (`dtype=str`). If pandas guessed types on load, it would hide problems: `NA` would silently become NaN and `007` would become `7`.

## Files

**`src/csv_doctor/analyze.py`** finds problems. `inspect_column` looks at one column and decides its kind:
- date, if at least half the values look like dates (or the name has the whole word "date" and 30% do, so `candidate` does not count)
- numeric, if at least half look like numbers
- text otherwise

Then it lists the problems for that kind: values of the wrong type, bad dates, spellings that differ only by case, and outliers. Outliers use the IQR rule, and ID-like columns (name has `id`, leading zeros, evenly spaced unique integers) are skipped: below Q1 - 1.5 x IQR or above Q3 + 1.5 x IQR. `analyze` runs that over every column and also finds duplicate rows (exact, and "near" where only case, spaces or null spelling differ).

**`src/csv_doctor/clean.py`** fixes problems. For each column it trims whitespace, turns null words into empty cells, then uses the same `inspect_column` result to fix dates, empty non-numbers and unify casing, and put a leading `'` on text cells that start with `=`, `+`, `-` or `@` (formula injection, `--no-safe` turns it off). Last, it drops duplicate rows. Each fix adds a log line: row, column, step, old value, new value. Sharing `inspect_column` means profile and clean always agree on what a problem is.

**`src/csv_doctor/report.py`** turns results into Markdown: issue counts, a per-column table, and a few examples. The clean report adds a before/after table and counts per step.

**`src/csv_doctor/cli.py`** is the command line, built with typer. It reads the file, calls analyze and clean, writes the files, and refuses to write over the input path. Bad files (empty, broken rows) exit with code 2 and a message.

**`src/csv_doctor/__main__.py`** lets you run `python -m csv_doctor` too.

**`examples/messy_orders_synthetic.csv`** is made-up data with planted problems. Not real.

**`tests/test_csv_doctor.py`** has the pytest tests: date parsing, each check, outliers flagged but not changed, the log matches the changes, cleaning twice changes nothing the second time, the input file is byte-identical after `clean`, the CLI refuses to overwrite the input, date-like words in column names, ID columns, formula escaping, and output names like `v1.2.csv`.

**`pyproject.toml`** says how to install: dependencies (pandas, typer), the `csv-doctor` command, and pytest as a dev extra.

**`.gitignore`, `LICENSE`**: ignore the virtual environment and output; MIT licence.

## Questions you might get

- **Why read everything as text?** To avoid silent guessing and to see the raw values that cause problems.
- **Why not delete outliers?** A big number can be a typo or a real event. The tool flags it and leaves the decision to a person.
- **How do you handle dates in different formats?** Check each value against a few date shapes, parse with pandas, write ISO `YYYY-MM-DD`. Impossible dates like 30 February are blanked and logged. Ambiguous ones follow a flag, day first by default.
- **How do you know it did not damage data?** Every change is logged with the old value. Cleaning an already-cleaned file gives an empty log (tested).
- **What would you do next?** Currency and thousands separators, a dry-run mode, column-type overrides.
