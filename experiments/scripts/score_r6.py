#!/usr/bin/env python3
"""라운드 6 채점 — 억제 지시 요인 분해 (사전등록 §3, §4, §5).

    ST_R6_ROOT=/path/to/st-r6 python experiments/scripts/score_r6.py

C0 은 라운드 4 K0(= 라운드 3 B), CK 는 라운드 4 K1(= 라운드 3 P)을 재사용한다
(프롬프트 바이트 동일, gen_r6.py 검증).
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import measure as M  # noqa: E402

R6 = Path(os.environ.get("ST_R6_ROOT", Path(tempfile.gettempdir()) / "st-r6"))
RUNS = REPO / "experiments/runs"
FIX = REPO / "experiments/fixtures/task-c-feature"
DEST = REPO / "experiments/raw"

NEW = {"t01": "B", "t08": "B", "t15": "B",
       "t03": "S3", "t09": "S3", "t16": "S3",
       "t04": "S4", "t11": "S4", "t18": "S4",
       "t06": "S5", "t12": "S5", "t19": "S5",
       "t07": "ALL", "t13": "ALL", "t20": "ALL",
       "t02": "CN800", "t10": "CN800", "t17": "CN800",
       "t05": "CN300", "t14": "CN300", "t21": "CN300"}
REUSE = {("r3", "t01"): "C0", ("r3", "t09"): "C0", ("r3", "t16"): "C0",
         ("r3", "t04"): "CK", ("r3", "t10"): "CK", ("r3", "t15"): "CK"}

T9 = {"B", "S3", "S4", "S5", "ALL"}
T10 = {"C0", "CK", "CN800", "CN300"}
CAP = {"CN800": 800, "CN300": 300}
KEEP = {"todo.js", "todo.test.js", "report.txt"}

COV = {
    "cap60": (re.compile(r"(?<!\d)60(?!\d)"), None),
    "refill": (re.compile(r"초당\s*1|1\s*(개|회|토큰)\s*/?\s*초|초에\s*1|1초에\s*(1|한)"), None),
    "apikey": (re.compile(r"API\s*키"), re.compile(r"IP")),
    "code429": (re.compile(r"(?<!\d)429(?!\d)"), None),
    "header": (re.compile(r"Retry-?After", re.I), None),
    "admin": (re.compile(r"admin"), re.compile(r"제외|면제|적용되지\s*않|예외|우회")),
}


def cov(t: str) -> int:
    return sum(1 for p, x in COV.values() if p.search(t) and (x is None or x.search(t)))


def comment_chars(src: str) -> int:
    """문자열 리터럴 밖의 `//` 줄 주석과 `/* */` 블록 주석 문자 수.

    정규식 하나로는 못 센다 — 문자열 안의 `//` 를 주석으로 오인하기 때문이다.
    (`'http://x'` 같은 값이 흔하다). 그래서 상태 기계로 훑는다.
    """
    n, i, total = len(src), 0, 0
    while i < n:
        c = src[i]
        if c in "'\"`":                      # 문자열/템플릿 리터럴 건너뛰기
            q, i = c, i + 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j == -1 else j
            total += j - i
            i = j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            total += j - i
            i = j
            continue
        i += 1
    return total


def run_tests(d: Path) -> int:
    try:
        p = subprocess.run(["node", "--test"], cwd=d, capture_output=True,
                           text=True, timeout=120, shell=(os.name == "nt"))
    except Exception:
        return -1
    m = re.search(r"^# pass (\d+)", p.stdout + p.stderr, re.M)
    return int(m.group(1)) if m else -1


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    orig = (FIX / "todo.js").read_text(encoding="utf-8")
    test_sha = hashlib.sha1((FIX / "todo.test.js").read_bytes()).hexdigest()
    rows: list[dict] = []

    plan = [(R6 / t, f"r6:{t}", c) for t, c in sorted(NEW.items())]
    plan += [(RUNS / r / t, f"{r}:{t}", c) for (r, t), c in sorted(REUSE.items())]

    for d, tag, cond in plan:
        task = "T9" if cond in T9 else "T10"
        rec: dict = {"trial": tag, "condition": cond, "task": task}
        rep_p = d / "report.txt"
        rep = rep_p.read_text(encoding="utf-8") if rep_p.exists() else ""
        rec["L_report"] = len(rep)

        if task == "T9":
            f = d / "todo.js"
            rec["gate_q1"] = bool(rep)
            rec["gate_q2"] = (hashlib.sha1((d / "todo.test.js").read_bytes()).hexdigest()
                              == test_sha)
            cur = f.read_text(encoding="utf-8")
            dif = "".join(difflib.unified_diff(orig.splitlines(keepends=True),
                                               cur.splitlines(keepends=True),
                                               "a/todo.js", "b/todo.js", n=3))
            rec["L_diff"] = len(dif)
            rec["L_file"] = len(cur)
            cc = comment_chars(cur)
            rec["cmt_chars"] = cc
            rec["cmt"] = round(cc / len(cur), 4) if cur else 0.0
            rec["extra"] = len([p for p in d.iterdir() if p.is_file() and p.name not in KEEP])
            rec["pass"] = run_tests(d)
            rec["T"] = rec["L_report"] + rec["L_diff"]
            rec["valid"] = rec["gate_q1"] and rec["gate_q2"]
        else:
            f = d / "doc.txt"
            if not f.exists() or f.stat().st_size == 0:
                rec.update(gate_q1=False, valid=False)
                rows.append(rec)
                continue
            text = f.read_text(encoding="utf-8")
            m = M.measure(text)
            rec["gate_q1"] = True
            rec["L_file"] = m["chars"]
            rec["G_file"] = m["bytes_gz"]
            rec["hangul"], rec["latin"] = m["hangul"], m["latin"]
            rec["gate_q2"] = m["hangul"] > m["latin"]
            rec["cov"] = cov(text)
            if cond in CAP:
                rec["cap"] = CAP[cond]
                rec["under_cap"] = m["chars"] <= CAP[cond]
            rec["valid"] = rec["gate_q1"] and rec["gate_q2"]
        rows.append(rec)

    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "r6-scores.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="\n")
    hdr = ["trial", "condition", "task", "valid", "L_file", "L_diff", "L_report", "T",
           "cmt", "cmt_chars", "extra", "pass", "cov", "cap", "under_cap"]
    out = ["\t".join(hdr)]
    for r in rows:
        out.append("\t".join(str(r.get(k, "")) for k in hdr))
    (DEST / "r6-scores.tsv").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
