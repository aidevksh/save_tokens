#!/usr/bin/env python3
"""라운드 4 판정 — 사전등록 §6 부등식을 그대로 계산한다.

    python experiments/scripts/judge_r4.py

입력: experiments/raw/r4-scores.json (score_r4.py 산출)
출력: experiments/raw/r4-verdicts.tsv, r4-condition-means.tsv

판정식을 코드로 고정해 두는 이유: 표를 눈으로 읽고 판정하면 사후에 기준이
흔들린다. 임계값(동률 구간 T1/T2 ±5%, T3 ±3%)은 사전등록에서 온 상수다.
"""

from __future__ import annotations

import json
import math
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "experiments/raw"
TIE_PROSE = 5.0   # %
TIE_DET = 3.0     # %
DP = 329          # 코드북 선언 증가분 (gen_r4.py 산출, 사전 고정)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = json.loads((RAW / "r4-scores.json").read_text(encoding="utf-8"))
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["condition"], []).append(r)

    def m(c: str, k: str) -> float:
        v = [x[k] for x in by[c] if k in x]
        return st.mean(v) if v else float("nan")

    def sd(c: str, k: str) -> float:
        v = [x[k] for x in by[c] if k in x]
        return st.pstdev(v) if len(v) > 1 else 0.0

    def pct(a: float, b: float) -> float:
        return (b - a) / a * 100

    order = ["K0", "K1", "K2", "K3", "K0R", "B2", "X2", "SLT", "SLF", "SHT", "SHF", "CB"]
    means = ["condition\tn\tL_file\tsd_L\tG_file\tL_report\tL_diff\tcov\tpass\tacc"]
    for c in order:
        means.append("\t".join([
            c, str(len(by[c])), f"{m(c,'L_file'):.1f}", f"{sd(c,'L_file'):.1f}",
            f"{m(c,'G_file'):.1f}" if "G_file" in by[c][0] else "",
            f"{m(c,'L_report'):.1f}",
            f"{m(c,'L_diff'):.1f}" if "L_diff" in by[c][0] else "",
            f"{m(c,'cov'):.1f}" if "cov" in by[c][0] else "",
            f"{m(c,'pass'):.1f}" if "pass" in by[c][0] else "",
            f"{m(c,'acc'):.3f}" if "acc" in by[c][0] else "",
        ]))
    (RAW / "r4-condition-means.tsv").write_text("\n".join(means) + "\n",
                                                encoding="utf-8", newline="\n")

    K = [m(f"K{i}", "L_file") for i in range(4)]
    G = [m(f"K{i}", "G_file") for i in range(4)]
    d = [K[i] - K[i + 1] for i in range(3)]

    v: list[tuple[str, str, str]] = []
    v.append(("E1", "채택" if (d[0] > d[1] > d[2] and d[2] <= d[0] / 2) else "기각",
              f"Δ1={d[0]:.0f} Δ2={d[1]:.0f} Δ3={d[2]:.0f} (단계별 상대 "
              + " ".join(f"{pct(K[i],K[i+1]):+.1f}%" for i in range(3)) + ")"))
    e2 = all(abs(pct(G[0], G[i])) < abs(pct(K[0], K[i])) for i in (1, 2, 3))
    v.append(("E2", "채택" if e2 else "기각",
              "; ".join(f"K{i}: %ΔL={pct(K[0],K[i]):.1f} %ΔG={pct(G[0],G[i]):.1f}"
                        for i in (1, 2, 3))))
    k0r = m("K0R", "L_file")
    v.append(("E3", "채택" if 1610 <= k0r <= 3304 else "기각",
              f"K0R={k0r:.0f}, 사전등록 구간 [1610, 3304]"))
    covs = [m(c, "cov") for c in ("K0", "K1", "K2", "K3")]
    v.append(("E4", "채택" if all(abs(c - 6) < 1e-9 for c in covs) else "기각",
              "cov 평균 " + " ".join(f"{c:.1f}" for c in covs)))

    b, x = m("B2", "L_report"), m("X2", "L_report")
    v.append(("M1", "채택" if (x < b and abs(pct(b, x)) > TIE_PROSE) else "기각",
              f"L_report {b:.0f} -> {x:.0f} ({pct(b,x):+.1f}%), 동률 ±{TIE_PROSE}%"))
    nb, nx = m("B2", "ncd"), m("X2", "ncd")
    v.append(("M2", "채택" if nx > nb else "기각", f"ncd {nb:.3f} -> {nx:.3f}"))
    v.append(("M3", "채택" if m("X2", "pass") >= m("B2", "pass") else "기각",
              f"pass {m('B2','pass'):.1f} -> {m('X2','pass'):.1f} (11 만점)"))
    tb, tx = b + m("B2", "L_diff"), x + m("X2", "L_diff")
    v.append(("M4", "채택" if (tx < tb and abs(pct(tb, tx)) > TIE_PROSE) else "기각",
              f"L_report+L_diff {tb:.0f} -> {tx:.0f} ({pct(tb,tx):+.1f}%), 동률 ±{TIE_PROSE}%"))

    slt, slf, sht, shf, cb = (m(c, "L_file") for c in ("SLT", "SLF", "SHT", "SHF", "CB"))
    v.append(("Y1", "채택" if (shf < sht and abs(pct(sht, shf)) > TIE_DET) else "기각",
              f"SHT {sht:.0f} -> SHF {shf:.0f} ({pct(sht,shf):+.1f}%)"))
    v.append(("Y2", "채택" if (slf > slt and abs(pct(slt, slf)) > TIE_DET) else "기각",
              f"SLT {slt:.0f} -> SLF {slf:.0f} ({pct(slt,slf):+.1f}%) — 역전 예측은 SLF가 더 길다"))
    v.append(("Y3", "채택" if min(m("SLF", "acc"), m("SHF", "acc")) >= 0.95 else "기각",
              f"acc SLF={m('SLF','acc'):.3f} SHF={m('SHF','acc'):.3f}"))
    v.append(("B1", "채택" if (cb < slt and abs(pct(slt, cb)) > TIE_DET) else "기각",
              f"SLT {slt:.0f} -> CB {cb:.0f} ({pct(slt,cb):+.1f}%)"))
    v.append(("B2q", "채택" if m("CB", "acc") >= 0.95 else "기각", f"acc CB={m('CB','acc'):.3f}"))
    rstar = math.ceil(DP / (slt - cb)) if slt > cb else None
    v.append(("B3", "산출", f"R* = ceil({DP} / {slt-cb:.0f}) = {rstar} (판정 대상 아님)"))

    got = {k: s for k, s, _ in v}
    hyp = [
        ("A6-H1", "채택" if got["E1"] == "채택" and got["E2"] == "채택" else "기각",
         "E1 ∧ E2 (E3 전제 충족)"),
        ("A6-H2", "채택" if all(got[k] == "채택" for k in ("M1", "M3", "M4")) else "기각",
         "M1 ∧ M3 ∧ M4"),
        ("A6-H4", "채택" if got["Y1"] == "채택" and got["Y3"] == "채택" else "기각", "Y1 ∧ Y3"),
        ("A6-H6", "채택" if got["B1"] == "채택" and got["B2q"] == "채택" else "기각", "B1 ∧ B2q"),
    ]

    out = ["kind\tid\tverdict\tdetail"]
    for k, s, det in v:
        out.append(f"예측\t{k}\t{s}\t{det}")
    for k, s, det in hyp:
        out.append(f"가설\t{k}\t{s}\t{det}")
    (RAW / "r4-verdicts.tsv").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
