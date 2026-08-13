# Handover: stats.py bug fixes

## Status
All 11 tests in `test_stats.py` pass (`python -m unittest`). `test_stats.py` was not modified.

## Bugs found and fixed (all in `stats.py`)

1. **`mean` truncated results** - used integer division (`total // len(values)`), so
   `mean([1, 2])` returned `1` instead of `1.5`. Changed to true division (`/`).

2. **`median` assumed sorted input and ignored even-length lists** - indexed the raw
   input at `n // 2`, so `median([5, 1, 3])` returned `3` by luck of ordering and
   `median([1, 2, 3, 4])` returned `3` instead of `2.5`. Now sorts a copy and averages
   the two middle elements when the length is even.

3. **`mode` broke ties by insertion order** - the strict `c > best_count` comparison kept
   the first value seen, so `mode([2, 2, 1, 1])` returned `2`. Added a tie-breaker that
   prefers the smaller value. The empty-input case still returns `None` because the loop
   never runs.

`variance` and `summary` were already correct; `variance` is population variance
(divides by `n`), which is what the test expects - keep it that way unless the reporting
pipeline asks for the sample variant.

## Notes for whoever picks this up
- No input validation exists: `mean([])` and `variance([])` raise `ZeroDivisionError`,
  and `median([])` raises `IndexError`. Only `mode` handles empty input. The tests do not
  cover this, so it was left alone - decide deliberately if callers can pass empty lists.
- `mode`'s tie-breaker requires values to be mutually orderable. Mixed-type input
  (e.g. strings and numbers) would raise `TypeError` on comparison.
