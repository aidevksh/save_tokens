#!/usr/bin/env python3
"""라운드 3 채점 — 품질 게이트 + 길이 + 마크업 비율 (사전등록 §4, §5, §6).

사용법:
    ST_R3_ROOT=/path/to/st-r3 python experiments/scripts/score_r3.py

시행 디렉터리는 저장소 밖에 둔다 — 저장소 안에서 돌리면 피험 에이전트가
정답 키와 사전등록 문서를 보게 되어 naive 조건이 깨진다.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import measure as M  # noqa: E402

R = Path(os.environ.get("ST_R3_ROOT", Path(tempfile.gettempdir()) / "st-r3"))
DATA = REPO / "experiments/data"
GT = DATA / "02-tickets-groundtruth.tsv"

# 사전등록 §2 조건표
TRIALS = {
    "t01": "B", "t09": "B", "t16": "B",
    "t02": "N", "t08": "N", "t18": "N",
    "t04": "P", "t10": "P", "t15": "P",
    "t05": "V", "t12": "V", "t17": "V",
    "t06": "F", "t11": "F", "t19": "F",
    "t03": "T", "t13": "T",
    "t07": "M", "t14": "M",
}
PROSE = {"B", "N", "P", "V", "F"}
TABLE = {"T", "M"}
OUTNAME = {"B": "doc.txt", "N": "doc.txt", "P": "doc.txt", "V": "doc.txt",
           "F": "doc.txt", "T": "out.txt", "M": "out.txt"}

# --- 사전등록 §5 커버리지 정규식 (실행 후 변경 금지) ------------------------
COV = {
    "cap60": (re.compile(r"(?<!\d)60(?!\d)"), None),
    "refill": (re.compile(r"초당\s*1|1\s*(개|회|토큰)\s*/?\s*초|초에\s*1|1초에\s*(1|한)"), None),
    "apikey": (re.compile(r"API\s*키"), re.compile(r"IP")),
    "code429": (re.compile(r"(?<!\d)429(?!\d)"), None),
    "header": (re.compile(r"Retry-?After", re.I), None),
    "admin": (re.compile(r"admin"), re.compile(r"제외|면제|적용되지\s*않|예외|우회")),
}

# 마크다운 구조 문자: 줄머리 헤딩/목록/인용, 표 파이프, 강조, 백틱
MU_LINE = re.compile(r"^\s*(#{1,6}\s|[-*+]\s|\d+\.\s|>\s)")
MU_INLINE = re.compile(r"\*\*|__|`+|\|")


def markup_ratio(text: str) -> tuple[float, int]:
    """마크다운 구조에 쓰인 문자 수 / 전체 문자 수."""
    n = 0
    for ln in text.split("\n"):
        m = MU_LINE.match(ln)
        if m:
            n += len(m.group(1).strip()) + 1  # 마커 + 뒤 공백 1
        n += sum(len(x.group(0)) for x in MU_INLINE.finditer(ln))
    total = len(text)
    return (round(n / total, 4) if total else 0.0), n


def coverage(text: str) -> tuple[int, list[str]]:
    hit, miss = 0, []
    for name, (a, b) in COV.items():
        ok = bool(a.search(text)) and (b is None or bool(b.search(text)))
        if ok:
            hit += 1
        else:
            miss.append(name)
    return hit, miss


# --- T2 표 파싱 --------------------------------------------------------------
def gt_cells() -> list[list[str]]:
    rows = GT.read_text(encoding="utf-8").strip("\n").split("\n")
    return [r.split("\t") for r in rows[1:]]


def parse_tsv(text: str) -> tuple[list[list[str]], list[str]]:
    lines = [l for l in text.strip("\n").split("\n") if l.strip()]
    notes = []
    if len(lines) != 13:
        notes.append(f"줄 수 {len(lines)} (기대 13)")
    body = [l.split("\t") for l in lines[1:]]
    return body, notes


def parse_md(text: str) -> tuple[list[list[str]], list[str]]:
    lines = [l for l in text.strip("\n").split("\n") if l.strip()]
    notes = []
    sep = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")
    rows = []
    for i, l in enumerate(lines):
        if sep.match(l):
            continue
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        rows.append(cells)
    if len(rows) != 13:
        notes.append(f"데이터+헤더 행 {len(rows)} (기대 13)")
    if not any(sep.match(l) for l in lines):
        notes.append("구분 행 없음")
    return rows[1:], notes


def norm(v: str) -> str:
    v = v.strip()
    try:
        f = float(v)
        return f"{f:g}"
    except ValueError:
        return v


def accuracy(body: list[list[str]]) -> tuple[float, int, int]:
    gt = gt_cells()
    ok = 0
    total = sum(len(r) for r in gt)
    by_id = {r[0]: r for r in body if r}
    for g in gt:
        got = by_id.get(g[0])
        if not got:
            continue
        for j, want in enumerate(g):
            if j < len(got) and norm(got[j]) == norm(want):
                ok += 1
    return (ok / total if total else 0.0), ok, total


# --- 시행 채점 ---------------------------------------------------------------
def score(trial: str, cond: str) -> dict:
    d = R / trial
    out = d / OUTNAME[cond]
    rep = d / "report.txt"
    row: dict = {"trial": trial, "cond": cond, "gates": {}, "notes": []}

    blocked = d / "blocked.txt"
    if blocked.exists():
        row["notes"].append("차단 사건 기록 있음: " + blocked.read_text(encoding="utf-8").strip()[:120])
        row["blocked"] = True

    if not out.exists() or out.stat().st_size == 0:
        row["gates"]["Q1_exists"] = False
        row["verdict"] = "무효"
        return row
    row["gates"]["Q1_exists"] = True

    text = out.read_text(encoding="utf-8")
    m = M.measure(text)
    row["chars"] = m["chars"]
    row["chars_nows"] = m["chars_nows"]
    row["lines"] = m["lines"]
    row["hangul_ratio"] = m["hangul_ratio"]
    if rep.exists():
        row["report_chars"] = M.measure(rep.read_text(encoding="utf-8"))["chars"]

    if cond in PROSE:
        row["gates"]["Q2_lang"] = m["hangul"] > m["latin"]
        cov, miss = coverage(text)
        row["cov"] = cov
        row["gates"]["Q3_cov"] = cov == 6
        if miss:
            row["notes"].append("미충족 항목: " + ",".join(miss))
        mr, mc = markup_ratio(text)
        row["markup"] = mr
        row["markup_chars"] = mc
    else:
        body, notes = (parse_tsv(text) if cond == "T" else parse_md(text))
        row["notes"] += notes
        widths = {len(r) for r in body}
        row["gates"]["Q2_format"] = (not notes) and widths == {8}
        if widths != {8}:
            row["notes"].append(f"열 수 {sorted(widths)} (기대 8)")
        acc, ok, tot = accuracy(body)
        row["acc"] = round(acc, 4)
        row["cells"] = f"{ok}/{tot}"
        row["gates"]["Q3_acc"] = acc >= 0.95

    row["verdict"] = "통과" if all(row["gates"].values()) else "게이트실패"
    return row


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rows = [score(t, c) for t, c in sorted(TRIALS.items())]
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["cond"], []).append(r)

    print(f"시행 루트: {R}\n")
    print(f"{'시행':<5} {'조건':<4} {'판정':<10} {'문자':>6} {'줄':>4} {'cov':>4} "
          f"{'markup':>7} {'acc':>6} {'보고':>6}  비고")
    for r in rows:
        print(f"{r['trial']:<5} {r['cond']:<4} {r['verdict']:<10} {r.get('chars', 0):>6} "
              f"{r.get('lines', 0):>4} {str(r.get('cov', '-')):>4} "
              f"{str(r.get('markup', '-')):>7} {str(r.get('acc', '-')):>6} "
              f"{str(r.get('report_chars', '-')):>6}")
        for k, v in r["gates"].items():
            if not v:
                print(f"       실패 게이트: {k}")
        for nt in r["notes"]:
            print(f"       {nt}")

    print("\n## 조건별 집계 (게이트 통과 시행만)")
    print(f"{'조건':<4} {'유효':>4} {'평균문자':>9} {'표준편차':>8} {'분산0':>6} "
          f"{'평균cov':>8} {'평균markup':>11} {'평균보고':>9}")
    agg: dict[str, dict] = {}
    for cond in ["B", "N", "P", "V", "F", "T", "M"]:
        rs = by.get(cond, [])
        ok = [r for r in rs if r["verdict"] == "통과"]
        inval = sum(1 for r in rs if r["verdict"] == "무효")
        blk = sum(1 for r in rs if r.get("blocked"))
        if not ok:
            agg[cond] = {"n_valid": 0, "n_invalid": inval, "n_blocked": blk}
            print(f"{cond:<4} {0:>4} {'-':>9} {'-':>8} {'-':>6} {'-':>8} {'-':>11} {'-':>9}")
            continue
        cs = [r["chars"] for r in ok]
        mean = sum(cs) / len(cs)
        sd = (sum((c - mean) ** 2 for c in cs) / len(cs)) ** 0.5
        covs = [r["cov"] for r in ok if "cov" in r]
        mus = [r["markup"] for r in ok if "markup" in r]
        reps = [r["report_chars"] for r in ok if "report_chars" in r]
        agg[cond] = {
            "n_valid": len(ok), "n_invalid": inval, "n_blocked": blk,
            "mean_chars": round(mean, 1), "sd_chars": round(sd, 1),
            "zero_var": len(set(cs)) == 1 and len(cs) > 1,
            "chars": cs,
            "mean_cov": round(sum(covs) / len(covs), 2) if covs else None,
            "mean_markup": round(sum(mus) / len(mus), 4) if mus else None,
            "mean_report": round(sum(reps) / len(reps), 1) if reps else None,
            "mean_acc": round(sum(r["acc"] for r in ok) / len(ok), 4) if cond in TABLE else None,
        }
        a = agg[cond]
        print(f"{cond:<4} {len(ok):>4} {mean:>9.1f} {sd:>8.1f} "
              f"{'예' if a['zero_var'] else '아니오':>6} "
              f"{str(a['mean_cov'] or '-'):>8} {str(a['mean_markup'] or '-'):>11} "
              f"{str(a['mean_report'] or '-'):>9}")

    def rel(a: str, b: str, key: str = "mean_chars") -> float | None:
        """a 대비 b 의 상대 변화. 음수 = b 가 짧다."""
        if agg.get(a, {}).get("n_valid") and agg.get(b, {}).get("n_valid"):
            va, vb = agg[a].get(key), agg[b].get(key)
            if va:
                return (vb - va) / va
        return None

    print("\n## 사전등록 §6 예측 대조")
    checks = [
        ("P1  검증 지시 비용  V 대비 B", rel("V", "B"), lambda d: d < -0.05),
        ("P2a 간결성  B 대비 N", rel("B", "N"), lambda d: d < -0.05),
        ("P2b 간결성  B 대비 P", rel("B", "P"), lambda d: d < -0.05),
        ("P3  긍정형 우위  N 대비 P", rel("N", "P"), lambda d: d < -0.05),
        ("P4  마크업 전이  B 대비 F", rel("B", "F", "mean_markup"), lambda d: d < -0.05),
        ("P5  길이 전이  B 대비 F", rel("B", "F"), lambda d: d < -0.05),
        ("P6  마크다운 표 비용  T 대비 M", rel("T", "M"), lambda d: d > 0.03),
    ]
    for label, d, ok in checks:
        if d is None:
            print(f"  {label:<30} 판정 불가 (유효 시행 부족)")
        else:
            print(f"  {label:<30} {d:>+8.1%}   {'충족' if ok(d) else '미충족'}")

    cb, cv = agg.get("B", {}).get("mean_cov"), agg.get("V", {}).get("mean_cov")
    if cb is not None and cv is not None:
        print(f"  {'P1q 품질 무손실  cov(B) >= cov(V)':<30} "
              f"B={cb} V={cv}   {'충족' if cb >= cv else '미충족'}")

    # P7·P8 — 라운드 1 산출물과의 대조
    r1 = REPO / "experiments/runs/r1"
    j = sorted(r1.glob("t01/out.json")) + sorted(r1.glob("*/out.json"))
    tsv = sorted(r1.glob("t02/out.tsv")) + sorted(r1.glob("*/out.tsv"))
    if j and agg.get("M", {}).get("n_valid"):
        lj = M.measure(j[0].read_text(encoding="utf-8"))["chars"]
        d = (agg["M"]["mean_chars"] - lj) / lj
        print(f"  {'P7  JSON 대비 M':<30} {d:>+8.1%}   {'충족' if d < 0 else '미충족'} "
              f"(라운드1 JSON {lj}자)")
    if tsv and agg.get("T", {}).get("n_valid"):
        lt = M.measure(tsv[0].read_text(encoding="utf-8"))["chars"]
        d = (agg["T"]["mean_chars"] - lt) / lt
        print(f"  {'P8  복제  라운드1 TSV 대비 T':<30} {d:>+8.1%}   "
              f"{'충족' if abs(d) <= 0.03 else '미충족'} (라운드1 TSV {lt}자)")

    print("\n## 언어 구성 확인 (산문 조건, hangul_ratio)")
    for cond in ["B", "N", "P", "V", "F"]:
        rs = [r for r in by.get(cond, []) if "hangul_ratio" in r]
        if rs:
            print(f"  {cond}: {[r['hangul_ratio'] for r in rs]}")

    dest = REPO / "experiments/raw/r3-scores.json"
    dest.write_text(json.dumps({"trials": rows, "conditions": agg}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(f"\n원시 채점 -> {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
