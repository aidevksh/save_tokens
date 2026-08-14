#!/usr/bin/env python3
"""라운드 4 채점 — 품질 게이트 + 길이 + 압축 후 크기 (사전등록 §4, §5, §6).

사용법:
    ST_R4_ROOT=/path/to/st-r4 python experiments/scripts/score_r4.py

시행 디렉터리는 저장소 밖에 둔다 — 저장소 안에서 돌리면 피험 에이전트가
정답 키와 사전등록 문서를 보게 되어 naive 조건이 깨진다.

K0/K1 은 라운드 3 B/P 를 재사용한다(프롬프트 바이트 동일, 생성기 검증).
그쪽은 저장소에 보존된 experiments/runs/r3 에서 읽는다.
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

R4 = Path(os.environ.get("ST_R4_ROOT", Path(tempfile.gettempdir()) / "st-r4"))
R3 = REPO / "experiments/runs/r3"
PROMPTS = REPO / "experiments/prompts"
DATA = REPO / "experiments/data"
FIX = REPO / "experiments/fixtures/task-a-bugfix"
DEST = REPO / "experiments/raw"

# 사전등록 §2 조건표
NEW = {"t01": "K2", "t08": "K2", "t18": "K2",
       "t04": "K3", "t12": "K3", "t23": "K3",
       "t15": "K0R",
       "t02": "B2", "t09": "B2", "t17": "B2",
       "t05": "X2", "t13": "X2", "t20": "X2",
       "t03": "SLT", "t14": "SLT",
       "t06": "SLF", "t16": "SLF",
       "t07": "SHT", "t19": "SHT",
       "t10": "SHF", "t21": "SHF",
       "t11": "CB", "t22": "CB"}
# 라운드 3 재사용분 (사전등록 §2)
REUSE = {"t01": "K0", "t09": "K0", "t16": "K0",
         "t04": "K1", "t10": "K1", "t15": "K1"}

PROMPT_OF = {"K0": "r4-K0.txt", "K0R": "r4-K0.txt", "K1": "r4-K1.txt",
             "K2": "r4-K2.txt", "K3": "r4-K3.txt",
             "B2": "r4-B2.txt", "X2": "r4-X2.txt",
             "SLT": "r4-SLT.txt", "SLF": "r4-SLF.txt", "SHT": "r4-SHT.txt",
             "SHF": "r4-SHF.txt", "CB": "r4-CB.txt"}
T1 = {"K0", "K0R", "K1", "K2", "K3"}
T2 = {"B2", "X2"}
T3 = {"SLT", "SLF", "SHT", "SHF", "CB"}

# --- 커버리지 정규식: 라운드 3 사전등록에서 그대로 가져온다 (변경 금지) -----
COV = {
    "cap60": (re.compile(r"(?<!\d)60(?!\d)"), None),
    "refill": (re.compile(r"초당\s*1|1\s*(개|회|토큰)\s*/?\s*초|초에\s*1|1초에\s*(1|한)"), None),
    "apikey": (re.compile(r"API\s*키"), re.compile(r"IP")),
    "code429": (re.compile(r"(?<!\d)429(?!\d)"), None),
    "header": (re.compile(r"Retry-?After", re.I), None),
    "admin": (re.compile(r"admin"), re.compile(r"제외|면제|적용되지\s*않|예외|우회")),
}

COLS = ["asset_id", "region", "env", "role", "os", "tier", "cpu", "status"]
CODE_COLS = ["a", "r", "e", "o", "s", "t", "c", "u"]
CODE = {
    "r": ["apne1", "apne2", "usea1", "euwe1"],
    "e": ["prod", "stage", "dev"],
    "o": ["web", "api", "batch", "cache"],
    "s": ["ubuntu22", "ubuntu24", "debian12", "alpine3"],
    "t": ["small", "medium", "large"],
    "u": ["active", "drained", "halted"],
}


def cov(text: str) -> int:
    n = 0
    for pos, extra in COV.values():
        if pos.search(text) and (extra is None or extra.search(text)):
            n += 1
    return n


def gt(kind: str) -> list[list[str]]:
    p = DATA / f"r4-assets-{kind}.tsv"
    return [ln.split("\t") for ln in p.read_text(encoding="utf-8").strip().split("\n")[1:]]


def fold(rows: list[list[str]]) -> list[list[str]]:
    out = [list(rows[0])]
    for i in range(1, len(rows)):
        out.append([rows[i][j] if rows[i][j] != rows[i - 1][j] else "^"
                    for j in range(len(COLS))])
    return out


def encode(rows: list[list[str]]) -> list[list[str]]:
    out = []
    for r in rows:
        out.append([r[0].replace("AS-", "")]
                   + [str(CODE[c].index(r[j]) + 1) if c in CODE else r[j]
                      for j, c in enumerate(CODE_COLS) if j > 0])
    return out


def parse(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n") if ln.strip() != ""]
    if not lines:
        return [], []
    return lines[0].split("\t"), [ln.split("\t") for ln in lines[1:]]


def decode_fold(body: list[list[str]]) -> list[list[str]]:
    out: list[list[str]] = []
    for i, row in enumerate(body):
        cur = []
        for j, v in enumerate(row):
            if v.strip() == "^" and out:
                cur.append(out[-1][j])
            else:
                cur.append(v.strip())
        out.append(cur)
    return out


def decode_code(body: list[list[str]]) -> list[list[str]]:
    out = []
    for row in body:
        cur = []
        for j, v in enumerate(row):
            v = v.strip()
            c = CODE_COLS[j] if j < len(CODE_COLS) else "?"
            if j == 0:
                cur.append(f"AS-{v}" if not v.startswith("AS-") else v)
            elif c in CODE:
                try:
                    cur.append(CODE[c][int(v) - 1])
                except (ValueError, IndexError):
                    cur.append(v)
            else:
                cur.append(v)
        out.append(cur)
    return out


def accuracy(truth: list[list[str]], got: list[list[str]]) -> float:
    hit = 0
    for i in range(len(truth)):
        for j in range(len(COLS)):
            if i < len(got) and j < len(got[i]) and got[i][j].strip() == truth[i][j]:
                hit += 1
    return round(hit / (len(truth) * len(COLS)), 4)


def run_tests(d: Path) -> int:
    """통과한 테스트 수. 실행 자체가 실패하면 0."""
    try:
        p = subprocess.run([sys.executable, "-m", "unittest", "-v"], cwd=d,
                           capture_output=True, text=True, timeout=120)
    except Exception:
        return 0
    out = p.stdout + p.stderr
    m = re.search(r"Ran (\d+) tests?", out)
    if not m:
        return 0
    total = int(m.group(1))
    bad = 0
    for kind in ("failures", "errors"):
        mm = re.search(rf"{kind}=(\d+)", out)
        if mm:
            bad += int(mm.group(1))
    return total - bad


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows: list[dict] = []

    orig_stats = (FIX / "stats.py").read_text(encoding="utf-8")
    test_sha = hashlib.sha1((FIX / "test_stats.py").read_bytes()).hexdigest()

    plan = [(R4 / t, t, c, "r4") for t, c in sorted(NEW.items())]
    plan += [(R3 / t, t, c, "r3") for t, c in sorted(REUSE.items())]

    for d, trial, condm, src in plan:
        rec: dict = {"trial": f"{src}:{trial}", "condition": condm, "task":
                     "T1" if condm in T1 else "T2" if condm in T2 else "T3"}
        prompt_raw = (PROMPTS / PROMPT_OF[condm]).read_text(encoding="utf-8")
        prompt = prompt_raw.replace("<RUNDIR>", d.as_posix())

        rep_p = d / "report.txt"
        rep = rep_p.read_text(encoding="utf-8") if rep_p.exists() else ""
        rec["L_report"] = len(rep)
        if rep:
            cx, cy = M.gz(prompt), M.gz(rep)
            cxy = M.gz(prompt + "\n" + rep)
            rec["ncd"] = round((cxy - min(cx, cy)) / max(cx, cy), 3)

        if rec["task"] == "T2":
            f = d / "stats.py"
            rec["gate_q1"] = bool(rep)
            rec["gate_q2"] = hashlib.sha1((d / "test_stats.py").read_bytes()).hexdigest() == test_sha
            cur = f.read_text(encoding="utf-8")
            dif = "".join(difflib.unified_diff(orig_stats.splitlines(keepends=True),
                                               cur.splitlines(keepends=True),
                                               "a/stats.py", "b/stats.py", n=3))
            rec["L_diff"] = len(dif)
            rec["L_file"] = len(cur)
            rec["pass"] = run_tests(d)
            rec["valid"] = rec["gate_q1"] and rec["gate_q2"]
        else:
            name = "doc.txt" if rec["task"] == "T1" else "out.txt"
            f = d / name
            if not f.exists() or f.stat().st_size == 0:
                rec["gate_q1"] = False
                rec["valid"] = False
                rows.append(rec)
                continue
            text = f.read_text(encoding="utf-8")
            m = M.measure(text)
            rec["gate_q1"] = True
            rec["L_file"] = m["chars"]
            rec["G_file"] = m["bytes_gz"]
            rec["redundancy"] = m["redundancy"]

            if rec["task"] == "T1":
                rec["hangul"], rec["latin"] = m["hangul"], m["latin"]
                rec["hangul_ratio"] = m["hangul_ratio"]
                rec["gate_q2"] = m["hangul"] > m["latin"]
                rec["cov"] = cov(text)
                rec["gate_q3"] = rec["cov"] == 6
                rec["valid"] = rec["gate_q1"] and rec["gate_q2"] and rec["gate_q3"]
            else:
                kind = "hi" if condm in ("SHT", "SHF") else "lo"
                truth = gt(kind)
                head, body = parse(text)
                rec["gate_q2"] = (len(body) == 12 and len(head) == 8
                                  and all(len(r) == 8 for r in body))
                if condm in ("SLF", "SHF"):
                    got = decode_fold(body)
                elif condm == "CB":
                    got = decode_code(body)
                else:
                    got = [[c.strip() for c in r] for r in body]
                rec["acc"] = accuracy(truth, got) if body else 0.0
                rec["valid"] = rec["gate_q1"] and rec["gate_q2"]
                # 방출 하한: 정답 키를 그 형식으로 낸 최소 텍스트
                if condm in ("SLF", "SHF"):
                    ideal = [COLS] + fold(truth)
                elif condm == "CB":
                    ideal = [CODE_COLS] + encode(truth)
                else:
                    ideal = [COLS] + truth
                rec["L_min"] = len("\n".join("\t".join(r) for r in ideal) + "\n")
        rows.append(rec)

    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "r4-scores.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    hdr = ["trial", "condition", "task", "valid", "L_file", "G_file", "L_report",
           "L_diff", "cov", "pass", "acc", "L_min", "ncd"]
    out = ["\t".join(hdr)]
    for r in rows:
        out.append("\t".join(str(r.get(k, "")) for k in hdr))
    (DEST / "r4-scores.tsv").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
