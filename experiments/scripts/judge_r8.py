#!/usr/bin/env python3
"""라운드 8 판정기 — 사전등록 `experiments/round8-plan.md` §5 를 그대로 계산한다.

    python experiments/scripts/judge_r8.py

눈으로 보고 정하지 않는다. 기준식이 참/거짓을 내고 그 조합이 판정을 낸다.
결과는 `experiments/raw/r8-judgment.json` / `r8-verdicts.tsv` / `r8-condition-means.tsv`.
"""

from __future__ import annotations

import json
import math
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "experiments/raw"

# 라운드 7 재사용분 (A1-H8 풀링). 프롬프트가 바이트 동일해야만 쓸 수 있다.
R7_POOL = {"WN": [4445, 4889, 6103], "WT": [1585, 1662, 1721]}
# 라운드 6 재사용분 (A1-H3 사다리 연결)
R6_CAPS = {"CN800": (800, 641.0), "CN300": (300, 248.0)}

F_CRIT_5_5 = 5.050      # 단측 F(5,5), α=0.05
TIE = 0.05              # 동률 구간 ±5%


def load():
    rows = json.loads((RAW / "r8-scores.json").read_text(encoding="utf-8"))
    by = {}
    for r in rows:
        by.setdefault(r["cond"], []).append(r)
    return rows, by


def mean(v):
    return sum(v) / len(v)


def col(rs, k):
    return [r[k] for r in rs if k in r]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows, by = load()
    out = {}

    # ── 조건 평균표 ────────────────────────────────────────────────
    means = {}
    for cond, rs in by.items():
        m = {"n": len(rs), "L_file": round(mean(col(rs, "L_file")), 1),
             "gz": round(mean(col(rs, "gz_file")), 1),
             "L_report": round(mean(col(rs, "L_report")), 1)}
        for k in ("acc_q", "cov", "fill", "cmt_add", "pass"):
            v = col(rs, k)
            if v:
                m[k] = round(mean(v), 3)
        means[cond] = m

    # ── A2-H2 키 축약 재시험 ──────────────────────────────────────
    accT, accK, accR = means["UT"]["acc_q"], means["UK"]["acc_q"], means["UR"]["acc_q"]
    LT, LK, LR = means["T"]["L_file"], means["K"]["L_file"], means["R"]["L_file"]
    M0 = accT >= 5.0
    M1 = LK < LT
    M2 = accK <= accT - 1.0
    if not M0:
        v_h2 = "판정 불가"
    elif M1 and M2:
        v_h2 = "채택"
    elif M1:
        v_h2 = "기각(정확도 항)"
    else:
        v_h2 = "기각"
    out["A2-H2"] = {"M0": M0, "M1": M1, "M2": M2, "verdict": v_h2,
                    "L_T": LT, "L_K": LK, "dL": round((LK - LT) / LT * 100, 1),
                    "acc_UT": accT, "acc_UK": accK}

    # ── A2-H5 헤더 제거 재시험 ────────────────────────────────────
    M4 = LR < LT
    M5 = accR >= accT - 1.0
    if not M0:
        v_h5 = "판정 불가"
    elif M4 and M5:
        v_h5 = "기각(원 주장) → 조건부 채택(길이 항)"
    elif M4:
        v_h5 = "채택"
    else:
        v_h5 = "기각"
    out["A2-H5"] = {"M0": M0, "M4": M4, "M5": M5, "verdict": v_h5,
                    "L_R": LR, "dL": round((LR - LT) / LT * 100, 1), "acc_UR": accR}

    # ── 왕복 회계 (사전등록 아님 · 관측) ──────────────────────────
    trip = {c: round(means[c]["L_file"] + means[u]["L_report"], 1)
            for c, u in (("T", "UT"), ("K", "UK"), ("R", "UR"))}
    out["roundtrip"] = {**trip,
                        "dK": round((trip["K"] - trip["T"]) / trip["T"] * 100, 1),
                        "dR": round((trip["R"] - trip["T"]) / trip["T"] * 100, 1),
                        "note": "사전등록되지 않은 관측 — 라운드 5 왕복 회계 재현"}

    # ── A1-H3 수치 상한 하향 ──────────────────────────────────────
    fill150, fill80 = means["CN150"]["fill"], means["CN80"]["fill"]
    E1 = all(0.70 <= f <= 1.00 for f in (fill150, fill80))
    E2 = all(r["cap_ok"] == 1 for r in rows if r["task"] == "T16")
    cov150, cov80 = means["CN150"]["cov"], means["CN80"]["cov"]
    E3 = (cov150 == 6.0) and (cov80 < 6.0)
    if E2 and E3:
        v_h3 = "율-왜곡 문턱 관측"
    elif E2 and cov150 == 6.0 and cov80 == 6.0:
        v_h3 = "문턱 미관측"
    elif not E2:
        v_h3 = "A1-H3 재검토"
    else:
        # cov(CN150) < 6.0 인 경우가 §5 결정표에 없다 — 사전등록 결함이다.
        v_h3 = "판정 불가(사전등록 결함: cov(CN150)<6.0 분기 누락)"
    ladder = [(800, R6_CAPS["CN800"][1]), (300, R6_CAPS["CN300"][1]),
              (150, means["CN150"]["L_file"]), (80, means["CN80"]["L_file"])]
    out["A1-H3"] = {"E1": E1, "E2": E2, "E3": E3, "verdict": v_h3,
                    "cov_150": cov150, "cov_80": cov80,
                    "fill_150": fill150, "fill_80": fill80,
                    "ladder": [{"cap": c, "L": L, "fill": round(L / c, 3)}
                               for c, L in ladder],
                    "floor_ref": 93}

    # ── A1-H8 지시의 분산 억제 ────────────────────────────────────
    r8 = {c: col(by[c], "L_file") for c in ("WN", "WT")}
    pool = {c: r8[c] + R7_POOL[c] for c in ("WN", "WT")}
    lv = {c: st.variance([math.log(x) for x in v]) for c, v in pool.items()}
    F = lv["WN"] / lv["WT"]
    V1 = F >= F_CRIT_5_5
    lv8 = {c: st.variance([math.log(x) for x in r8[c]]) for c in ("WN", "WT")}
    V2 = lv8["WN"] > lv8["WT"]
    v_h8 = "채택" if (V1 and V2) else ("조건부 채택" if V1 else "기각")
    out["A1-H8"] = {
        "V1": V1, "V2": V2, "verdict": v_h8, "F": round(F, 3), "F_crit": F_CRIT_5_5,
        "var_lnWN": round(lv["WN"], 5), "var_lnWT": round(lv["WT"], 5),
        "F_r8only": round(lv8["WN"] / lv8["WT"], 3),
        "pool_WN": sorted(pool["WN"]), "pool_WT": sorted(pool["WT"]),
        "cv_WN": round(st.stdev(pool["WN"]) / mean(pool["WN"]) * 100, 1),
        "cv_WT": round(st.stdev(pool["WT"]) / mean(pool["WT"]) * 100, 1),
        "dMean": round((mean(pool["WT"]) - mean(pool["WN"])) / mean(pool["WN"]) * 100, 1),
    }

    # ── A5-H5 주석 밀도 재시험 ────────────────────────────────────
    pilot = [r["cmt_add"] for r in rows if r["trial"] in ("t25", "t26")]
    P0 = sum(pilot) > 0
    cB, cS = means["DB"]["cmt_add"], means["DS"]["cmt_add"]
    C1 = cS <= cB * 0.70
    C2 = all(r["pass"] == 10 for r in rows if r["task"] == "T18")
    if not P0:
        v_a5 = "판정 불가"
    elif C1 and C2:
        v_a5 = "채택"
    elif C1:
        v_a5 = "조건부 채택"
    else:
        v_a5 = "기각 확정"
    out["A5-H5"] = {"P0": P0, "C1": C1, "C2": C2, "verdict": v_a5,
                    "pilot": pilot, "cmt_DB": cB, "cmt_DS": cS,
                    "L_DB": means["DB"]["L_file"], "L_DS": means["DS"]["L_file"],
                    "dL": round((means["DS"]["L_file"] - means["DB"]["L_file"])
                                / means["DB"]["L_file"] * 100, 1),
                    "gz_DB": means["DB"]["gz"], "gz_DS": means["DS"]["gz"],
                    "dGz": round((means["DS"]["gz"] - means["DB"]["gz"])
                                 / means["DB"]["gz"] * 100, 1)}

    # ── 쓰기 ───────────────────────────────────────────────────────
    (RAW / "r8-judgment.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    ks = ["cond", "n", "L_file", "gz", "L_report", "acc_q", "cov", "fill", "cmt_add", "pass"]
    lines = ["\t".join(ks)]
    for c in ("T", "K", "R", "UT", "UK", "UR", "CN150", "CN80", "WN", "WT", "DB", "DS"):
        m = means[c]
        lines.append("\t".join([c] + [str(m.get(k, "")) for k in ks[1:]]))
    (RAW / "r8-condition-means.tsv").write_text("\n".join(lines) + "\n",
                                                encoding="utf-8", newline="\n")

    vt = ["가설\t판정\t근거"]
    for h in ("A2-H2", "A2-H5", "A1-H3", "A1-H8", "A5-H5"):
        d = out[h]
        flags = " ".join(f"{k}={'T' if v else 'F'}" for k, v in d.items()
                         if isinstance(v, bool))
        vt.append(f"{h}\t{d['verdict']}\t{flags}")
    (RAW / "r8-verdicts.tsv").write_text("\n".join(vt) + "\n",
                                         encoding="utf-8", newline="\n")

    for h in ("A2-H2", "A2-H5", "A1-H3", "A1-H8", "A5-H5"):
        d = out[h]
        print(f"\n■ {h}  →  {d['verdict']}")
        for k, v in d.items():
            if k != "verdict":
                print(f"    {k} = {v}")
    print("\n■ 왕복 회계(관측)", out["roundtrip"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
