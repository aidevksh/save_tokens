"""Judge-side verification for task A. NOT given to the subject agent.

Usage:  python verify_a.py <trial_dir>
Exit 0 = task complete. Prints one PASS/FAIL line per check.
"""
import subprocess
import sys
from pathlib import Path


def main(trial_dir: str) -> int:
    d = Path(trial_dir).resolve()
    checks = []

    # 1. the supplied suite must pass in full
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "test_stats"],
        cwd=d, capture_output=True, text=True,
    )
    checks.append(("supplied suite passes", r.returncode == 0))

    # 2. the supplied suite must be unmodified
    original = (Path(__file__).parent.parent / "task-a-bugfix" / "test_stats.py").read_text()
    checks.append(("test_stats.py unmodified", (d / "test_stats.py").read_text() == original))

    # 3. novel inputs the subject never saw (guards against test-fitting)
    probe = r"""
import sys
sys.path.insert(0, %r)
from stats import mean, median, mode, variance
assert abs(mean([10, 20, 25]) - 55/3) < 1e-9, "mean"
assert median([9, 1, 8, 2]) == 5.0, "median even unsorted"
assert median([4, 4, 4]) == 4, "median odd dup"
assert mode([]) is None, "mode empty"
assert mode([7, 7, 3, 3, 9]) == 3, "mode tie -> smallest"
assert abs(variance([2, 4, 4, 4, 5, 5, 7, 9]) - 4.0) < 1e-9, "variance"
print("novel-ok")
""" % str(d)
    r2 = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    checks.append(("novel inputs correct", r2.returncode == 0))
    if r2.returncode != 0:
        checks.append(("  detail: " + r2.stderr.strip().splitlines()[-1][:120], False))

    ok = True
    for name, passed in checks:
        print(("PASS " if passed else "FAIL ") + name)
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
