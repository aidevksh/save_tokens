# Handover: stats.py bug fixes

All 11 tests in `test_stats.py` pass (`python -m unittest`). `test_stats.py` was not modified.

## Fixes in `stats.py`

- **`mean`** used integer division (`//`), truncating fractional averages. Changed to `/`.
- **`median`** returned the element at the middle index of the *unsorted* input. It now sorts a copy first (the caller's list is left untouched).
- **`median`** returned a single element for even-length inputs. It now averages the two middle values.
- **`mode`** was non-deterministic on ties — it kept whichever tied value dict iteration reached first. It now breaks ties toward the smallest value.

`variance` and `summary` were already correct; `variance` is population variance (divides by `n`), which matches the test.

## Notes for whoever is next

- Empty input is only defined for `mode` (returns `None`). `mean`, `median`, and `variance` raise on `[]` (`ZeroDivisionError` / `IndexError`). No test covers this, so the intended behavior is unspecified — worth confirming with the reporting-pipeline callers before hardening.
- The tie-break in `mode` compares `v < best`, which is safe only because the first iteration always takes the `c > best_count` branch (any count is `> 0`). If the loop's initialization changes, add an explicit `best is None` guard.
- `mode` assumes values are mutually comparable and hashable.
