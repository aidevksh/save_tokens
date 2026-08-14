#!/usr/bin/env python3
"""라운드 5 채점 — 품질 게이트 + 길이 + 소비자 성공률 (사전등록 §4, §5, §6).

    ST_R5_ROOT=/path/to/st-r5 python experiments/scripts/score_r5.py

W0/W1/W2 는 라운드 2, T12 는 라운드 4, X0 은 라운드 4 K0 을 재사용한다
(프롬프트 바이트 동일, gen_r5.py 검증).
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
import measure as M  # noqa: E402

R5 = Path(os.environ.get("ST_R5_ROOT", Path(tempfile.gettempdir()) / "st-r5"))
RUNS = REPO / "experiments/runs"
DATA = REPO / "experiments/data"
PROMPTS = REPO / "experiments/prompts"
DEST = REPO / "experiments/raw"

NEW = {"t01": "W3", "t14": "W3", "t05": "W4", "t20": "W4", "t27": "W1R",
       "t02": "J3", "t16": "J3", "t06": "T3", "t21": "T3",
       "t03": "J12", "t17": "J12", "t07": "J24", "t22": "J24",
       "t10": "T24", "t25": "T24",
       "t04": "GhiD", "t18": "GhiD", "t08": "GhiP", "t23": "GhiP",
       "t11": "GloD", "t26": "GloD", "t13": "GloP", "t28": "GloP",
       "t09": "X1", "t19": "X1", "t29": "X1",
       "t12": "X2", "t15": "X2", "t24": "X2",
       "t30": "RW0", "t35": "RW0", "t31": "RW1", "t36": "RW1",
       "t32": "RW2", "t37": "RW2", "t33": "RW3", "t38": "RW3",
       "t34": "RW4", "t39": "RW4"}
# 이전 라운드 재사용 (round, trial) -> 조건
REUSE = {("r2", "t04"): "W0", ("r2", "t11"): "W0",
         ("r2", "t05"): "W1", ("r2", "t09"): "W1",
         ("r2", "t06"): "W2", ("r2", "t07"): "W2",
         ("r4", "t03"): "T12", ("r4", "t14"): "T12",
         ("r3", "t01"): "X0", ("r3", "t09"): "X0", ("r3", "t16"): "X0"}

T4 = {"W0", "W1", "W2", "W3", "W4", "W1R"}
T5 = {"RW0", "RW1", "RW2", "RW3", "RW4"}
T6 = {"J3", "T3", "J12", "T12", "J24", "T24"}
T7 = {"GhiD", "GhiP", "GloD", "GloP"}
T8 = {"X0", "X1", "X2"}
NREC = {"J3": 3, "T3": 3, "J12": 12, "T12": 12, "J24": 24, "T24": 24}
ARTIFACT = {"T4": "out.diff", "T5": "deploy.yaml", "T6": "out.txt", "T8": "doc.txt"}

COV = {
    "cap60": (re.compile(r"(?<!\d)60(?!\d)"), None),
    "refill": (re.compile(r"초당\s*1|1\s*(개|회|토큰)\s*/?\s*초|초에\s*1|1초에\s*(1|한)"), None),
    "apikey": (re.compile(r"API\s*키"), re.compile(r"IP")),
    "code429": (re.compile(r"(?<!\d)429(?!\d)"), None),
    "header": (re.compile(r"Retry-?After", re.I), None),
    "admin": (re.compile(r"admin"), re.compile(r"제외|면제|적용되지\s*않|예외|우회")),
}
# 사전등록 §4 재질의 정규식 (실행 후 변경 금지)
ASK = re.compile(r"추측|알 수 없|불명확|확인이 필요|모호|\?\s*$", re.M)

COLS = ["asset_id", "region", "env", "role", "os", "tier", "cpu", "status"]


def cov(t: str) -> int:
    return sum(1 for p, x in COV.values() if p.search(t) and (x is None or x.search(t)))


def norm(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


def task_of(c: str) -> str:
    return ("T4" if c in T4 else "T5" if c in T5 else "T6" if c in T6
            else "T7" if c in T7 else "T8")


def gt_assets(n: int) -> list[list[str]]:
    p = DATA / f"r5-assets-{n}.tsv"
    if not p.exists():                       # N=12 는 라운드 4 정답 키와 같다
        p = DATA / "r4-assets-lo.tsv"
    return [ln.split("\t") for ln in p.read_text(encoding="utf-8").strip().split("\n")[1:]]


def acc_table(cond: str, text: str) -> tuple[float, bool]:
    n = NREC[cond]
    truth = gt_assets(n)
    if cond.startswith("J"):
        try:
            data = json.loads(text)
        except Exception:
            return 0.0, False
        ok = isinstance(data, list) and len(data) == n and all(
            isinstance(r, dict) and set(r) == set(COLS) for r in data)
        hit = 0
        for i, row in enumerate(truth):
            if i < len(data) and isinstance(data[i], dict):
                for j, c in enumerate(COLS):
                    if str(data[i].get(c, "")).strip() == row[j]:
                        hit += 1
        return round(hit / (n * 8), 4), ok
    lines = [ln for ln in norm(text).split("\n") if ln.strip()]
    ok = len(lines) == n + 1 and all(len(ln.split("\t")) == 8 for ln in lines)
    body = [ln.split("\t") for ln in lines[1:]]
    hit = sum(1 for i, row in enumerate(truth) for j in range(8)
              if i < len(body) and j < len(body[i]) and body[i][j].strip() == row[j])
    return round(hit / (n * 8), 4), ok


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    expected_yaml = norm((DATA / "r2-deploy120-expected.yaml").read_text(encoding="utf-8"))
    rows: list[dict] = []

    plan = [(R5 / t, f"r5:{t}", c) for t, c in sorted(NEW.items())]
    plan += [(RUNS / r / t, f"{r}:{t}", c) for (r, t), c in sorted(REUSE.items())]

    for d, tag, cond in plan:
        task = task_of(cond)
        rec: dict = {"trial": tag, "condition": cond, "task": task}
        rep_p = d / "report.txt"
        rep = rep_p.read_text(encoding="utf-8") if rep_p.exists() else ""
        rec["L_report"] = len(rep)

        if task == "T7":
            src = d / ("out.py" if cond.endswith("P") else "out.txt")
            if not src.exists():
                rec.update(gate_q1=False, valid=False)
                rows.append(rec)
                continue
            text = src.read_text(encoding="utf-8")
            rec["L_file"] = len(text)
            rec["G_file"] = M.measure(text)["bytes_gz"]
            want = norm((DATA / ("r5-shards-hi.csv" if "hi" in cond else "r5-shards-lo.csv")
                         ).read_text(encoding="utf-8"))
            if cond.endswith("P"):
                try:
                    p = subprocess.run([sys.executable, str(src)], cwd=d, capture_output=True,
                                       text=True, timeout=60)
                    got, rec["run_ok"] = norm(p.stdout), p.returncode == 0
                except Exception:
                    got, rec["run_ok"] = "", False
            else:
                got, rec["run_ok"] = norm(text), True
            rec["exec"] = got == want
            rec["gate_q1"] = True
            rec["gate_q2"] = rec["run_ok"] if cond.endswith("P") else len(got.split("\n")) == 60
            rec["valid"] = rec["gate_q1"] and rec["gate_q2"]
            rows.append(rec)
            continue

        f = d / ARTIFACT[task]
        if task == "T4" and not f.exists():
            f = d / "out.yaml"                 # W0(전체 재출력)은 out.yaml 로 낸다
        if not f.exists() or f.stat().st_size == 0:
            rec.update(gate_q1=False, valid=False)
            rows.append(rec)
            continue
        text = f.read_text(encoding="utf-8")
        m = M.measure(text)
        rec["gate_q1"] = True
        rec["L_file"] = m["chars"]
        rec["G_file"] = m["bytes_gz"]

        if task == "T4":
            lines = norm(text).split("\n")
            if cond == "W4":
                rec["gate_q2"] = all(re.match(r"^\d+:\s", ln) for ln in lines if ln.strip())
            elif cond == "W0":
                rec["gate_q2"] = len(lines) == 120
            else:
                ctx = [ln for ln in lines if ln and ln[0] == " "]
                rec["ctx_lines"] = len(ctx)
                rec["gate_q2"] = (len(ctx) == 0) if cond == "W3" else True
            rec["valid"] = rec["gate_q1"] and rec["gate_q2"]

        elif task == "T5":
            rec["d"] = 0 if norm(text) == expected_yaml else 1
            rec["ask"] = 1 if ASK.search(rep) else 0
            rec["gate_q2"] = bool(rep)
            rec["valid"] = rec["gate_q1"] and rec["gate_q2"]
            src = {"RW0": "W0", "RW1": "W1", "RW2": "W2", "RW3": "W3", "RW4": "W4"}[cond]
            rec["source"] = src

        elif task == "T6":
            a, ok = acc_table(cond, text)
            rec["acc"], rec["gate_q2"] = a, ok
            rec["gate_q3"] = a >= 0.95
            rec["valid"] = all((rec["gate_q1"], ok, rec["gate_q3"]))

        else:  # T8
            rec["cov"] = cov(text)
            rec["hangul"], rec["latin"] = m["hangul"], m["latin"]
            rec["gate_q2"] = m["hangul"] > m["latin"]
            rec["gate_q3"] = rec["cov"] == 6
            rec["valid"] = all((rec["gate_q1"], rec["gate_q2"], rec["gate_q3"]))
        rows.append(rec)

    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "r5-scores.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="\n")
    hdr = ["trial", "condition", "task", "valid", "L_file", "G_file", "L_report",
           "acc", "cov", "d", "ask", "exec", "ctx_lines", "source"]
    out = ["\t".join(hdr)]
    for r in rows:
        out.append("\t".join(str(r.get(k, "")) for k in hdr))
    (DEST / "r5-scores.tsv").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
