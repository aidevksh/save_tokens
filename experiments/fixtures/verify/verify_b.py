"""Judge-side verification for task B. NOT given to the subject agent.

Usage:  python verify_b.py <trial_dir>
"""
import subprocess
import sys
from pathlib import Path


def main(trial_dir: str) -> int:
    d = Path(trial_dir).resolve()
    src = (d / "ingest.py").read_text()
    checks = []

    r = subprocess.run(
        [sys.executable, "-m", "unittest", "test_ingest"],
        cwd=d, capture_output=True, text=True,
    )
    checks.append(("supplied suite passes", r.returncode == 0))

    original = (Path(__file__).parent.parent / "task-b-refactor" / "test_ingest.py").read_text()
    checks.append(("test_ingest.py unmodified", (d / "test_ingest.py").read_text() == original))

    # duplication actually removed: the field-count message must exist once
    checks.append(("field-count check deduplicated", src.count("expected") <= 1))
    checks.append(("empty-field check deduplicated", src.count("empty field") <= 1))

    # behaviour preserved on inputs the subject never saw
    probe = r"""
import sys
sys.path.insert(0, %r)
from ingest import load_users, load_orders, load_products
assert load_users(["   ", "#x", "3, Bo, B@X.COM"]) == [
    {"id": 3, "name": "Bo", "email": "b@x.com"}], "users"
assert load_orders(["12, 3, zz-9, 7"]) == [
    {"id": 12, "user_id": 3, "sku": "ZZ-9", "qty": 7}], "orders"
assert load_products(["zz-9, Thing, 0.5"]) == [
    {"sku": "ZZ-9", "title": "Thing", "price_cents": 50}], "products"
for bad in (["1,2"], ["1,2,3,4"]):
    try:
        load_users(bad); raise AssertionError("no raise")
    except ValueError:
        pass
try:
    load_products(["a, , 1.0"]); raise AssertionError("no raise on empty")
except ValueError:
    pass
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
    print("ingest.py lines: %d (baseline 68)" % len(src.splitlines()))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
