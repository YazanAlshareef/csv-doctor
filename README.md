# csv-doctor

Command line tool that finds problems in a messy CSV file, writes a Markdown report, and makes a cleaned copy. It logs every change and never overwrites your input file.

```
csv-doctor profile data.csv
csv-doctor clean data.csv -o clean.csv
```

No LLM and no network. It is plain pandas, typer and pytest.

## What it checks

| Check | How it is found | What `clean` does |
|---|---|---|
| Missing values | empty, `NA`, `N/A`, `null`, `none`, `nan`, `-`, `?` (any case) | writes an empty cell |
| Extra whitespace | spaces at the ends or doubled inside | trims and collapses to one space |
| Inconsistent casing | `Sydney`, `sydney`, `SYDNEY` in one text column | uses the most common spelling |
| Mixed types | a non-number in a number column, a number in a text column | number column: empties the cell. Text column: flags only |
| Bad dates | date columns with values that are not real dates (`2024-02-30`, `not a date`) | empties the cell |
| Mixed date formats | `16/01/2024`, `Jan 20 2024`, `2024-01-22` | rewrites to `YYYY-MM-DD` |
| Duplicates | exact repeats, and repeats that differ only by case, spaces or null spelling | keeps the first row, drops the rest |
| Outliers | numbers outside 1.5 x IQR (needs 8 or more numbers in the column) | flags only, never changes |

Row numbers in reports and logs are data rows, starting at 1, not counting the header.

## Install and run

Needs Python 3.10 or newer.

```
git clone https://github.com/YazanAlshareef/csv-doctor
cd csv-doctor
python -m venv .venv
.venv/Scripts/activate        # Windows. On Mac/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest
csv-doctor profile examples/messy_orders_synthetic.csv
csv-doctor clean examples/messy_orders_synthetic.csv -o out/clean.csv
```

`clean` writes three files next to the `-o` path: `clean.csv`, `clean.changes.csv` (one line per change: row, column, step, old value, new value) and `clean.report.md`. If you leave out `-o` it writes `<name>.clean.csv` next to the input. It refuses to run if any output path is the input file.

Ambiguous dates such as `03/04/2024` are read day first. Pass `--monthfirst` to change that. Dates starting with a year are always read as year-month-day.

## Example

The sample file `examples/messy_orders_synthetic.csv` is **synthetic**. I wrote it by hand with problems planted on purpose (duplicates, mixed date formats, bad dates, odd casing, blanks, an outlier). It holds no real people or orders.

This is the real report from `csv-doctor clean examples/messy_orders_synthetic.csv -o out/clean.csv`:

```markdown
# CSV clean report: messy_orders_synthetic.csv

- Input (not modified): `messy_orders_synthetic.csv`, 25 rows
- Cleaned output: `clean.csv`, 23 rows
- Change log: `clean.changes.csv`, 37 changes
- Ambiguous dates like 03/04/2024 read as day first

## Before and after

| Issue | Before | After |
|---|---|---|
| missing values | 6 | 10 |
| duplicate rows (exact) | 1 | 0 |
| duplicate rows (near) | 1 | 0 |
| extra whitespace cells | 3 | 0 |
| inconsistent casing cells | 14 | 0 |
| mixed-type values | 2 | 0 |
| bad dates | 3 | 0 |
| outliers (flagged only) | 5 | 4 |

## Changes by step

| Step | Changes |
|---|---|
| fix_case | 14 |
| fix_date | 9 |
| missing_value | 4 |
| trim_whitespace | 3 |
| bad_date | 3 |
| bad_number | 2 |
| drop_duplicate | 2 |

Outliers are flagged, not changed. Mixed-type values in a text column are flagged, not changed.

## What is still flagged in the cleaned file

- `amount` outliers outside 7.5 to 175.7 (1.5 x IQR): row 4: `210.00`, row 10: `99999.00`
- `quantity` outliers outside -0.5 to 3.5 (1.5 x IQR): row 7: `4`, row 13: `5`
```

In "missing values", the After count is higher because bad dates and non-numbers were emptied, not guessed. Each one is in the change log, for example `7,order_date,bad_date,2024-02-30,`.

Outliers stay in the cleaned file on purpose. Whether `99999.00` is a typo or a real big order is your call.

## How AI helped

I built this with an AI coding assistant. It wrote the first version of the code and tests from my brief, and I reviewed the logic and ran it. The tool itself uses no AI.

## What broke and how it was fixed

- Dates like `2024-02-05` came out as `2024-05-02`. I passed day-first to pandas for every date, and pandas then swapped month and day on year-first dates. The first sample run showed it. Fix: year-first dates skip the day-first flag. A test covers it.
- My first duplicate test failed because it used a single column, so the rows really were duplicates. The test data was wrong, not the code.

## Limits

- Everything is read as text. It does not guess currencies: `$1,200` counts as text, not a number.
- A real value of `none`, `-` or `?` is treated as missing.
- Ambiguous dates need the `--dayfirst/--monthfirst` choice. The tool cannot know which your file uses.
- Mixed types in a text column are flagged, not fixed.
- Case fixing picks the most common spelling. On a tie it prefers mixed case.
- The whole file is loaded into memory.
- Cells that start with `=` are kept as they were. If you open the output in Excel, check them.
- Tested on the synthetic sample and small test frames only, not on a range of real files.

## Files

See [WALKTHROUGH.md](WALKTHROUGH.md) for what each file does.

## License

MIT
