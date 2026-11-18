# Improvement log

## 2026-11-15, cycle 1

Baseline: 16 tests pass on main (1582e2f), run with the project's `.venv` python. No linter or type checker is configured.

### Done this cycle (branches awaiting review, not merged)

Every branch below changes behaviour.

| Item | Branch | Commit | Result |
|---|---|---|---|
| Rows longer than the header lost alignment. Extra fields are now kept and named `extra_field`, `extra_field_2`, and so on. On main, rows with two extra fields were silently misaligned. Rows of mixed length still exit 2 with a clear message, same as main. | fix/extra-field-columns | 91f2803 | 18 tests pass |
| Version numbers were read as dates. A dotted `dd.mm.yy` with a valid day and month still parses as a date. Versions like `1.2.3` and `1.10.0` stay text. `1.2.24` is now text. `10.12.24` would still read as a date. | fix/version-not-date | 604735f | 18 tests pass |
| Header names were not escaped under `--safe`. Now the cleaned file and the change log escape them, and the markdown report shows the escaped names. | fix/escape-header-log | 73e3bc5 | 17 tests pass |

Each branch holds one commit on top of main. The test counts are per branch, not combined.

### Known limit

A header already named `extra_field` would collide with the new names.

### Backlog, top 5 not yet done

1. Timestamps in a date column are blanked as bad dates (src/csv_doctor/analyze.py:15-19, :61-62, src/csv_doctor/clean.py:42-44). Effort M, risk medium. Touches the same lines as the version fix, so do it after that branch lands.
2. Scientific notation is not read as a number, so cells like `1e5` are emptied (src/csv_doctor/analyze.py:14). Effort S for the exponent, M for separators. Risk low.
3. Output write errors give a raw traceback and exit 1 (src/csv_doctor/cli.py:107-113 and :57-59, other read errors use exit 2 at :34-37). Effort S, risk low.
4. Missing tests for duplicates, `--monthfirst`, `--no-safe`, non-UTF-8 input, header-only files and more (tests/test_csv_doctor.py:27-38, :50-56, :59-65). Effort M, risk low.
5. Type and lint problems, and no lint or type step (src/csv_doctor/report.py:67, src/csv_doctor/cli.py:16, :64, :36, :53). Found by reading, not by running a linter. Effort S, risk low.

### Diagrams

Diagrams live on the `docs/diagrams` branch, in `docs/diagrams/` (column-logic.md, components.md, sequences.md). They are not on main.

### Lessons

- Run the tests with the project's `.venv` python. The system python has neither typer nor the package, so collection fails there.
- The date fix is a rule, not a full answer. `10.12.24` is ambiguous and still reads as a date.
- Fixing extra fields by naming them adds a naming rule, and that rule can collide with a real header.

### Not verified

- Linting and type checks (no tools configured).
- Behaviour on real exports beyond the sample files and the test cases.

### Status

All branches are local. Nothing is pushed or merged. They await the owner's approval.
