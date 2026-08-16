#!/usr/bin/env python3
"""라운드 7 채점 — 품질 게이트 + 길이 + 압축 후 크기 + 정확도 (사전등록 §3, §4).

    ST_R7_ROOT=/path/to/st-r7 python experiments/scripts/score_r7.py

시행 작업 디렉터리는 저장소 밖에 둔다 — 저장소 안에서 돌리면 피험 에이전트가
정답 키와 사전등록 문서를 보게 되어 naive 조건이 깨진다.

재사용분은 저장소에 보존된 experiments/runs 에서 읽는다.
  T (표 기준선)  = 라운드 4 SLT  (r4/t03, r4/t14)
  C0 (산문 무처치) = 라운드 3 B   (r3/t01, r3/t09, r3/t16)
  CK (산문 3명제)  = 라운드 3 P   (r3/t04, r3/t10, r3/t15)
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import measure as M  # noqa: E402

R7 = Path(os.environ.get("ST_R7_ROOT", Path(tempfile.gettempdir()) / "st-r7"))
R4 = REPO / "experiments/runs/r4"
R3 = REPO / "experiments/runs/r3"
DATA = REPO / "experiments/data"
DEST = REPO / "experiments/raw"

# ── 사전등록 §1 조건표 ────────────────────────────────────────────────
NEW = {"t01": "K", "t05": "K", "t02": "E", "t06": "E", "t03": "P", "t07": "P",
       "t08": "UT", "t12": "UT", "t09": "UK", "t13": "UK",
       "t10": "UE", "t14": "UE", "t11": "UP", "t15": "UP",
       "t16": "CC", "t20": "CC", "t24": "CC",
       "t17": "CI", "t21": "CI", "t25": "CI",
       "t18": "CR", "t22": "CR", "t26": "CR",
       "t04": "WN", "t19": "WN", "t23": "WN",
       "t27": "WF", "t30": "WF", "t33": "WF",
       "t28": "WT", "t31": "WT", "t34": "WT",
       "t29": "WB", "t32": "WB", "t35": "WB"}
REUSE_R4 = {"t03": "T", "t14": "T"}
REUSE_R3 = {"t01": "C0", "t09": "C0", "t16": "C0",
            "t04": "CK", "t10": "CK", "t15": "CK"}

TAB = {"T", "K", "E", "P"}          # T11 생산자
CONS = {"UT", "UK", "UE", "UP"}     # T12 소비자
PROSE6 = {"C0", "CC", "CI", "CR", "CK"}   # T13
PROSE10 = {"WN", "WF", "WT", "WB"}        # T14

# ── 커버리지 (T13) — 라운드 3 정규식 + 라운드 6에서 확인된 거짓 음성 보정 ──
# `admin` 패턴에 `적용받지\s*않` 을 추가한다 (사전등록 §3). 나머지는 그대로.
COV6 = {
    "cap60": (re.compile(r"(?<!\d)60(?!\d)"), None),
    "refill": (re.compile(r"초당\s*1|1\s*(개|회|토큰)\s*/?\s*초|초에\s*1|1초에\s*(1|한)"), None),
    "apikey": (re.compile(r"API\s*키"), re.compile(r"IP")),
    "code429": (re.compile(r"(?<!\d)429(?!\d)"), None),
    "header": (re.compile(r"Retry-?After", re.I), None),
    "admin": (re.compile(r"admin"),
              re.compile(r"제외|면제|적용되지\s*않|적용받지\s*않|예외|우회")),
}

# ── 커버리지 (T14) — 10항목 ──────────────────────────────────────────
COV10 = {
    "retry": (re.compile(r"최대\s*5|5\s*회"), None),
    "backoff": (re.compile(r"지수|백오프|backoff", re.I), re.compile(r"(?<!\d)64(?!\d)")),
    "sig": (re.compile(r"X-Signature|HMAC|서명", re.I), None),
    "timeout": (re.compile(r"10\s*초|타임아웃"), None),
    "dup": (re.compile(r"at-least-once|중복|멱등|event_id", re.I), None),
    "order": (re.compile(r"순서"), re.compile(r"보장하지|보장되지|보장\s*안|무관|없|occurred_at")),
    "size": (re.compile(r"256\s*KB|payload_url", re.I), None),
    "type": (re.compile(r"order\.\w+|이벤트\s*타입"), None),
    "disable": (re.compile(r"100\s*회|7\s*일"), re.compile(r"비활성|자동")),
    "redeliver": (re.compile(r"redeliver|재전송|30\s*일", re.I), None),
}

SUMSEC = re.compile(r"^\s*(#+\s*)?(요약|정리|마무리|결론|맺음말|한눈에)", re.M)


def cov(text: str, table: dict) -> int:
    n = 0
    for pos, extra in table.values():
        if pos.search(text) and (extra is None or extra.search(text)):
            n += 1
    return n


def pre_chars(text: str, table: dict) -> int:
    """첫 명세 항목이 언급되기 전까지의 문자 수 = 서론 길이."""
    starts = []
    for pos, _ in table.values():
        m = pos.search(text)
        if m:
            starts.append(m.start())
    return min(starts) if starts else len(text)


def rep_count(text: str, table: dict) -> int:
    """명세 항목이 언급된 총 횟수 = 반복도."""
    return sum(len(pos.findall(text)) for pos, _ in table.values())


# ── 표 정확도 ─────────────────────────────────────────────────────────
COLS = ["asset_id", "region", "env", "role", "os", "tier", "cpu", "status"]
CODE = {
    "region": ["apne1", "apne2", "usea1", "euwe1"],
    "env": ["prod", "stage", "dev"],
    "role": ["web", "api", "batch", "cache"],
    "os": ["ubuntu22", "ubuntu24", "debian12", "alpine3"],
    "tier": ["small", "medium", "large"],
    "status": ["active", "drained", "halted"],
}


def truth() -> list[list[str]]:
    p = DATA / "r4-assets-lo.tsv"
    return [ln.split("\t") for ln in p.read_text(encoding="utf-8").strip().split("\n")[1:]]


def rows_of(text: str, cond: str) -> list[list[str]]:
    """산출물을 정답 키와 같은 표기로 되돌린다. 규약대로 복호할 뿐 추측하지 않는다."""
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n") if ln.strip() != ""]
    body = lines if cond == "P" else lines[1:]          # P 만 헤더가 없다
    coded = cond in ("E", "P")
    out = []
    for ln in body:
        cells = ln.split("\t")
        cur = []
        for j, v in enumerate(cells):
            v = v.strip()
            name = COLS[j] if j < len(COLS) else "?"
            if coded and name in CODE:
                try:
                    cur.append(CODE[name][int(v) - 1])
                except (ValueError, IndexError):
                    cur.append(v)
            else:
                cur.append(v)
        out.append(cur)
    return out


def acc_cell(got: list[list[str]]) -> float:
    tr = truth()
    hit = 0
    for i in range(len(tr)):
        for j in range(len(COLS)):
            if i < len(got) and j < len(got[i]) and got[i][j] == tr[i][j]:
                hit += 1
    return round(hit / (len(tr) * len(COLS)), 4)


# ── 소비자 정확도 ─────────────────────────────────────────────────────
ANSWERS = {
    1: {"kind": "value", "want": "large"},
    2: {"kind": "value", "want": "ubuntu22"},
    3: {"kind": "count", "want": 5},
    4: {"kind": "ids", "want": {"2001", "2005", "2011"}},
    5: {"kind": "count", "want": 3},
    6: {"kind": "ids", "want": {"2009"}},
}


def acc_q(text: str) -> int:
    lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
    got = {}
    for ln in lines:
        m = re.match(r"^(\d+)\s*[.)]\s*(.+)$", ln)
        if m:
            got[int(m.group(1))] = m.group(2)
    n = 0
    for q, spec in ANSWERS.items():
        a = got.get(q, "")
        if not a:
            continue
        if spec["kind"] == "value":
            if spec["want"] in a:
                n += 1
        elif spec["kind"] == "count":
            m = re.search(r"(?<!\d)(\d+)(?!\d)", a)
            if m and int(m.group(1)) == spec["want"]:
                n += 1
        else:
            ids = set(re.findall(r"(?:AS-)?(\d{4})", a))
            if ids == spec["want"]:
                n += 1
    return n


# ── 수집 ──────────────────────────────────────────────────────────────
def read(p: Path) -> str | None:
    return p.read_text(encoding="utf-8") if p.exists() else None


def score(trial: str, cond: str, d: Path) -> dict | None:
    rec: dict = {"trial": trial, "condition": cond}
    rep = read(d / "report.txt")
    rec["L_report"] = M.measure(rep)["chars"] if rep else 0

    if cond in TAB:
        out = read(d / "out.txt")
        if out is None:
            rec["gate"] = "no out.txt"
            return rec
        s = M.measure(out)
        rows = rows_of(out, cond)
        rec.update(L_out=s["chars"], gz_out=s["bytes_gz"],
                   rows=len(rows), acc_cell=acc_cell(rows))
        # Q1 12행 / Q2 설명문 없음(한글 음절 0)
        rec["gate"] = "" if (len(rows) == 12 and s["hangul"] == 0) else "표 형식 위반"
        return rec

    if cond in CONS:
        ans = read(d / "ans.txt")
        if ans is None:
            rec["gate"] = "no ans.txt"
            return rec
        lines = [ln for ln in ans.strip().split("\n") if ln.strip()]
        rec.update(acc_q=acc_q(ans), ans_lines=len(lines),
                   L_ans=M.measure(ans)["chars"])
        rec["gate"] = "" if len(lines) == 6 else "6줄 아님"
        return rec

    doc = read(d / "doc.txt")
    if doc is None:
        rec["gate"] = "no doc.txt"
        return rec
    s = M.measure(doc)
    table = COV6 if cond in PROSE6 else COV10
    rec.update(L_file=s["chars"], gz_file=s["bytes_gz"],
               cov=cov(doc, table), pre=pre_chars(doc, table),
               rep=rep_count(doc, table), sumsec=int(bool(SUMSEC.search(doc))))
    rec["T"] = rec["L_file"] + rec["L_report"]
    rec["gate"] = "" if s["hangul"] > s["latin"] else "언어 구성 위반"
    return rec


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows: list[dict] = []
    for t, c in sorted(NEW.items()):
        r = score(t, c, R7 / t)
        r["source"] = "r7"
        rows.append(r)
    for t, c in sorted(REUSE_R4.items()):
        r = score(f"r4/{t}", c, R4 / t)
        r["source"] = "r4"
        rows.append(r)
    for t, c in sorted(REUSE_R3.items()):
        r = score(f"r3/{t}", c, R3 / t)
        r["source"] = "r3"
        rows.append(r)

    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "r7-scores.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    keys = ["trial", "condition", "source", "gate", "L_out", "gz_out", "acc_cell",
            "acc_q", "L_file", "gz_file", "cov", "pre", "rep", "sumsec",
            "L_report", "T"]
    lines = ["\t".join(keys)]
    for r in rows:
        lines.append("\t".join(str(r.get(k, "")) for k in keys))
    (DEST / "r7-scores.tsv").write_text("\n".join(lines) + "\n",
                                        encoding="utf-8", newline="\n")
    print("\n".join(lines))
    bad = [r["trial"] for r in rows if r.get("gate")]
    print(f"\n게이트 탈락 {len(bad)}건: {bad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
