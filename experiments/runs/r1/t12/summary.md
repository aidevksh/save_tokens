# Handover: stats.py bug fixes

## Status
Done. All 11 tests in `test_stats.py` pass (`python -m unittest`). `test_stats.py` was not modified.

## Bugs found and fixed (all in `stats.py`)

1. **`mean` used integer division.** `total // len(values)` truncated toward negative
   infinity, so `mean([1, 2])` returned `1` instead of `1.5` and `mean([-3, 3, 1])`
   returned `0` instead of `1/3`. Changed to true division (`/`).

2. **`median` did not sort its input.** It indexed the caller's list as-is, so
   `median([5, 1, 3])` returned `1`. Now sorts via `sorted()`, which also leaves the
   caller's list unmutated (verified: `median([5,1,3])` leaves the argument intact).

3. **`median` had no even-length branch.** It always returned the upper-middle element,
   so `median([1, 2, 3, 4])` returned `3`. Now averages the two middle elements for even
   lengths, returning `2.5`.

4. **`mode` did not break ties deterministically.** With a strict `c > best_count`
   comparison the winner depended on dict insertion order, so `mode([2, 2, 1, 1])`
   returned `2`. The condition is now
   `c > best_count or (c == best_count and v < best)`, which returns the smallest value
   among tied counts.

`variance` itself was correct -- it was only wrong because it calls `mean`. Fixing bug 1
brought `variance([1, 2, 3, 4])` to the expected population variance of `1.25`.
`summary` needed no change.

## Notes for whoever picks this up

- `variance` is the **population** variance (divides by `n`, not `n - 1`); the test
  `test_population_variance` pins that behaviour. Don't switch it to sample variance
  without updating expectations elsewhere in the reporting pipeline.
- `mean` and `variance` still raise `ZeroDivisionError` on an empty list. Only `mode`
  handles the empty case (returns `None`). No test covers empty input for the others, so
  this was left as-is rather than guessed at -- worth confirming the intended contract
  with the pipeline owners.
- The tie-breaking rule in `mode` assumes values are mutually comparable with `<`. That
  holds for the numeric and string data in the tests, but a mixed-type list would raise
  a `TypeError`.
