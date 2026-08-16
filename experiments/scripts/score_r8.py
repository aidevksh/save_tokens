#!/usr/bin/env python3
"""라운드 8 채점기.

    ST_R8_ROOT=/path/to/st-r8 python experiments/scripts/score_r8.py

사전등록 §3 종속 변수를 계산해 `experiments/raw/r8-scores.json` / `.tsv` 로 쓴다.
길이는 `tools/measure.py` 를 그대로 쓴다 — 손으로 세지 않는다.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "experiments/scripts"))

from measure import measure                          # noqa: E402
from score_r6 import comment_chars                   # noqa: E402  라운드 6 상태 기계 재사용

R8 = Path(os.environ.get("ST_R8_ROOT", Path(tempfile.gettempdir()) / "st-r8"))
DATA = REPO / "experiments/data"
RAW = REPO / "experiments/raw"
FIXTURE = REPO / "experiments/fixtures/task-d-schedule"

COND = {
    "t01": "T", "t04": "T", "t02": "K", "t05": "K", "t03": "R", "t06": "R",
    "t07": "UT", "t10": "UT", "t08": "UK", "t11": "UK", "t09": "UR", "t12": "UR",
    "t13": "CN150", "t15": "CN150", "t17": "CN150",
    "t14": "CN80", "t16": "CN80", "t18": "CN80",
    "t19": "WN", "t21": "WN", "t23": "WN",
    "t20": "WT", "t22": "WT", "t24": "WT",
    "t25": "DB", "t26": "DB", "t27": "DB",
    "t28": "DS", "t29": "DS", "t30": "DS",
}
TASK = {**{c: "T15" for c in ("T", "K", "R", "UT", "UK", "UR")},
        **{c: "T16" for c in ("CN150", "CN80")},
        **{c: "T17" for c in ("WN", "WT")},
        **{c: "T18" for c in ("DB", "DS")}}
CAP = {"CN150": 150, "CN80": 80}
OUTFILE = {"T15": "out.txt", "T16": "doc.txt", "T17": "doc.txt", "T18": "sched.js"}

# ── 커버리지 ────────────────────────────────────────────────────────
# `적용받지\s*않` 추가 — 라운드 6에서 「적용**받**지 않습니다」를 놓쳐 거짓 음성이 났다.
# 사전등록 §3 의 이행이다. 라운드 3–7 은 전 조건 만점이라 소급 영향이 없다.
COV16 = {
    "cap60": (re.compile(r"(?<!\d)60(?!\d)"), None),
    "refill": (re.compile(r"초당\s*1|1\s*(개|회|토큰)\s*/?\s*초|초에\s*1|1초에\s*(1|한)"), None),
    "apikey": (re.compile(r"API\s*키"), re.compile(r"IP")),
    "code429": (re.compile(r"(?<!\d)429(?!\d)"), None),
    "header": (re.compile(r"Retry-?After", re.I), None),
    "admin": (re.compile(r"admin"), re.compile(r"제외|면제|적용되지\s*않|적용받지\s*않|예외|우회")),
}

# T17 웹훅 명세 10항목
COV17 = {
    "retry": re.compile(r"(?<!\d)5\s*회|최대\s*5"),
    "backoff": re.compile(r"백오프|2배|64\s*초"),
    "sign": re.compile(r"X-?Signature|HMAC", re.I),
    "timeout": re.compile(r"10\s*초"),
    "dup": re.compile(r"at-?least-?once|멱등", re.I),
    "order": re.compile(r"occurred_at|순서"),
    "size": re.compile(r"256\s*KB|payload_url", re.I),
    "types": re.compile(r"order\.created"),
    "disable": re.compile(r"100\s*회|7\s*일|비활성"),
    "redeliver": re.compile(r"redeliver|재전송", re.I),
}


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def norm(s: str) -> str:
    """소비자 답 정규화 — `3건`/`3`, 구분자 차이를 흡수한다."""
    s = s.strip().rstrip(".")
    s = re.sub(r"^\s*\d+\.\s*", "", s)
    s = s.replace("건", "").replace("개", "")
    s = re.sub(r"[·/]", ",", s)
    parts = [x.strip() for x in s.split(",") if x.strip()]
    return "|".join(sorted(parts)) if len(parts) > 1 else (parts[0] if parts else "")


def score_answers(text: str, key: list[str]) -> int:
    lines = [ln for ln in text.split("\n") if ln.strip()]
    hit = 0
    for i, want in enumerate(key):
        got = lines[i] if i < len(lines) else ""
        if norm(got) == norm(want):
            hit += 1
    return hit


def run_tests(d: Path) -> int:
    try:
        # 테스트 이름이 한국어라 시스템 코덱(cp949)으로 디코딩하면 깨진다. 바이트로 받는다.
        r = subprocess.run(["node", "--test"], cwd=d, capture_output=True, timeout=120)
    except Exception:
        return -1
    m = re.search(r"^# pass (\d+)", r.stdout.decode("utf-8", "replace"), re.M)
    return int(m.group(1)) if m else -1


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    key = [ln.split("\t", 1)[1] for ln in
           read(DATA / "r8-answers.tsv").rstrip("\n").split("\n")]
    truth = read(DATA / "r8-records.tsv").rstrip("\n").split("\n")[1:]
    base_cmt = comment_chars(read(FIXTURE / "sched.js"))
    orig_test = (FIXTURE / "sched.test.js").read_bytes()

    rows = []
    for trial in sorted(COND):
        cond = COND[trial]
        task = TASK[cond]
        d = R8 / trial
        out = read(d / OUTFILE[task]) if task != "T15" or not cond.startswith("U") \
            else read(d / "ans.txt")
        rep = read(d / "report.txt")
        m_out, m_rep = measure(out), measure(rep)
        row = {
            "trial": trial, "cond": cond, "task": task,
            "L_file": m_out["chars"], "gz_file": m_out["bytes_gz"],
            "L_report": m_rep["chars"], "hangul": m_out["hangul_ratio"],
        }

        if task == "T15" and not cond.startswith("U"):
            lines = [ln for ln in out.rstrip("\n").split("\n") if ln.strip()]
            body = lines[1:] if cond in ("T", "K") else lines
            row["rows_ok"] = int(len(body) == 12)
            row["cells_ok"] = int([ln.rstrip("\r") for ln in body] == truth)
        elif cond.startswith("U"):
            row["acc_q"] = score_answers(out, key)
        elif task == "T16":
            row["cov"] = sum(1 for p, x in COV16.values()
                             if p.search(out) and (x is None or x.search(out)))
            row["cap"] = CAP[cond]
            row["cap_ok"] = int(m_out["chars"] <= CAP[cond])
            row["fill"] = round(m_out["chars"] / CAP[cond], 3)
        elif task == "T17":
            row["cov"] = sum(1 for p in COV17.values() if p.search(out))
        else:
            row["cmt"] = comment_chars(out)
            row["cmt_add"] = row["cmt"] - base_cmt
            row["pass"] = run_tests(d)
            row["test_intact"] = int((d / "sched.test.js").read_bytes() == orig_test)
        rows.append(row)

    (RAW / "r8-scores.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    cols = ["trial", "cond", "task", "L_file", "gz_file", "L_report", "hangul",
            "rows_ok", "cells_ok", "acc_q", "cov", "cap", "cap_ok", "fill",
            "cmt", "cmt_add", "pass", "test_intact"]
    lines = ["\t".join(cols)]
    for r in rows:
        lines.append("\t".join(str(r.get(c, "")) for c in cols))
    (RAW / "r8-scores.tsv").write_text("\n".join(lines) + "\n",
                                       encoding="utf-8", newline="\n")

    for r in rows:
        extra = " ".join(f"{k}={r[k]}" for k in
                         ("rows_ok", "cells_ok", "acc_q", "cov", "cap_ok", "fill",
                          "cmt_add", "pass", "test_intact") if k in r)
        print(f"{r['trial']}  {r['cond']:6} L={r['L_file']:5} gz={r['gz_file']:5} "
              f"rep={r['L_report']:4}  {extra}")
    print(f"\n원본 주석 {base_cmt}자 · 시행 {len(rows)}건 -> raw/r8-scores.tsv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
