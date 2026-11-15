# Walkthrough

A tour of each file, so I can explain the project out loud.

## The idea

There are two commands. `profile` reads a CSV and reports problems. `clean` fixes what can be fixed safely, logs each fix, and writes a new file. The input is never touched.

Everything is read as text (`dtype=str`). If pandas guessed types on load, it would hide the problems I am looking for: `NA` would quietly become NaN and `007` would become `7`.

## Files

**`src/csv_doctor/analyze.py`** finds problems. `inspect_column` looks at one column and decides its kind:
- date, if half the values look like dates, or 30% when the column name has the whole word "date" (so `candidate` does not count)
- numeric, if half look like numbers
- text, otherwise

Then it lists what is wrong for that kind: wrong-type values, bad dates, spellings that differ only by case, and outliers. Outliers use the IQR rule, below Q1 - 1.5 x IQR or above Q3 + 1.5 x IQR. ID-like columns are skipped, because an outlier check on an ID means nothing. `analyze` runs this over every column and also finds duplicate rows, exact ones and "near" ones that differ only by case, spaces or null spelling.

**`src/csv_doctor/clean.py`** fixes problems. For each column it trims whitespace and turns null words into empty cells. Then it uses the same `inspect_column` result to fix dates, empty the non-numbers and unify casing. Text cells that start with `=`, `+`, `-` or `@` get a leading `'` so Excel does not run them as formulas (`--no-safe` turns that off). Duplicate rows are dropped last. Every fix adds a log line: row, column, step, old value, new value. Because profile and clean share `inspect_column`, they always agree on what counts as a problem.

**`src/csv_doctor/report.py`** turns results into Markdown: issue counts, a table per column, a few examples. The clean report adds the before and after table and a count per step.

**`src/csv_doctor/cli.py`** is the command line, built with typer. It reads the file, calls analyze and clean, writes the files, and refuses to write over the input. It also has `--version`. Files that cannot be read (empty, broken rows) exit with code 2 and a message. If pandas renamed a blank or repeated header, it prints a warning. The change log goes through the same formula escaping as the cleaned file.

**`src/csv_doctor/__main__.py`** lets `python -m csv_doctor` work too.

**`examples/messy_orders_synthetic.csv`** is made-up data with planted problems. It is not real.

**`tests/test_csv_doctor.py`** has 16 pytest tests. They cover date parsing, each check, outliers flagged but not changed, the log matching the changes, cleaning twice changing nothing the second time, the input file staying byte-identical, and the CLI refusing to overwrite it. The rest cover date-like words in column names, ID columns, formula escaping (file and log), output names like `v1.2.csv`, renamed headers, and `--version`.

**`pyproject.toml`** holds the install info: dependencies (pandas, typer), the `csv-doctor` command, pytest as a dev extra, and the package metadata.

**`.github/workflows/ci.yml`** installs the package and runs pytest on Python 3.10 and 3.12, then runs `clean` on the sample file. I have not seen it run on GitHub yet.

**`.gitignore`, `LICENSE`** ignore the virtual environment and output, and set the MIT licence.

## Questions I might get

- **Why read everything as text?** To avoid silent guessing and to see the raw values that cause the trouble.
- **Why not delete outliers?** A big number can be a typo or a real event. The tool flags it and leaves the call to a person.
- **How are dates in different formats handled?** Each value is checked against a few date shapes, parsed with pandas, and written as `YYYY-MM-DD`. Impossible dates like 30 February are blanked and logged. Ambiguous ones follow a flag, day first by default.
- **How do I know it did not damage data?** Every change is logged with the old value, and cleaning an already clean file gives an empty log. A test checks that.
- **What would I do next?** Currency and thousands separators, a dry-run mode, column-type overrides.
