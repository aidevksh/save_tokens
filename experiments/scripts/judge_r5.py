#!/usr/bin/env python3
"""라운드 5 판정 — 사전등록 §6 부등식을 그대로 계산한다.

    python experiments/scripts/judge_r5.py

입력: experiments/raw/r5-scores.json
출력: experiments/raw/r5-verdicts.tsv, r5-condition-means.tsv
"""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "experiments/raw"
TIE_SOFT = 5.0   # 산문·에이전트 과제
TIE_DET = 3.0    # 결정적 과제


def linfit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    a = sxy / sxx
    b = my - a * mx
    ss_res = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return a, b, 1 - ss_res / ss_tot if ss_tot else 1.0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = json.loads((RAW / "r5-scores.json").read_text(encoding="utf-8"))
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

    order = ["W0", "W1", "W2", "W3", "W4", "W1R", "RW0", "RW1", "RW2", "RW3", "RW4",
             "J3", "T3", "J12", "T12", "J24", "T24",
             "GhiD", "GhiP", "GloD", "GloP", "X0", "X1", "X2"]
    means = ["condition\tn\tL_file\tsd_L\tG_file\tL_report\tacc\tcov\td\task\texec"]
    for c in order:
        g = by[c]
        means.append("\t".join([
            c, str(len(g)), f"{m(c,'L_file'):.1f}", f"{sd(c,'L_file'):.1f}",
            f"{m(c,'G_file'):.1f}", f"{m(c,'L_report'):.1f}",
            f"{m(c,'acc'):.3f}" if "acc" in g[0] else "",
            f"{m(c,'cov'):.1f}" if "cov" in g[0] else "",
            f"{m(c,'d'):.2f}" if "d" in g[0] else "",
            f"{m(c,'ask'):.2f}" if "ask" in g[0] else "",
            f"{sum(1 for x in g if x.get('exec'))}/{len(g)}" if "exec" in g[0] else "",
        ]))
    (RAW / "r5-condition-means.tsv").write_text("\n".join(means) + "\n",
                                                encoding="utf-8", newline="\n")

    v: list[tuple[str, str, str]] = []

    # ── A6-H3 율-왜곡 문턱 ────────────────────────────────────────────────
    W = ["W0", "W1", "W2", "W3", "W4"]
    RW = ["RW0", "RW1", "RW2", "RW3", "RW4"]
    L1st = [m(w, "L_file") for w in W]
    c_rate = [1 - x / L1st[0] for x in L1st]
    dist = [m(r, "d") for r in RW]
    slopes = []
    for i in range(4):
        dc = c_rate[i + 1] - c_rate[i]
        slopes.append((dist[i + 1] - dist[i]) / dc if dc else 0.0)
    zero_runs, run = 0, 0
    for i in range(4):
        if dist[i] == 0 and dist[i + 1] == 0:
            run += 1
            zero_runs = max(zero_runs, run)
        else:
            run = 0
    if all(x == 0 for x in dist):
        r1 = "기각"
        r1d = "전 구간 d=0 — 이 압축 범위에서 문턱이 나타나지 않았다"
    else:
        others = [s for s in slopes if s != max(slopes)]
        avg = sum(others) / len(others) if others else 0.0
        r1 = "채택" if (zero_runs >= 2 and (avg == 0 or max(slopes) / avg >= 3)) else "기각"
        r1d = f"d={dist}, 기울기={[round(s,3) for s in slopes]}, 연속 0구간={zero_runs}"
    v.append(("R1", r1, r1d + f" · 압축률={[round(x,3) for x in c_rate]}"))
    v.append(("R2", "채택" if (dist[0] == dist[1] == dist[2] == 0 and dist[3] > 0) else "기각",
              f"W2까지 d=0 그리고 W3부터 d>0 을 기대. 실측 d={dist}"))
    w1r, w1 = m("W1R", "L_file"), m("W1", "L_file")
    v.append(("R3", "채택" if abs(pct(w1, w1r)) <= 10 else "기각",
              f"W1R={w1r:.0f} vs 라운드2 W1={w1:.0f} ({pct(w1,w1r):+.1f}%), 허용 ±10%"))

    # ── A6-H8 재요청 왕복 ────────────────────────────────────────────────
    asks = [m(r, "ask") for r in RW]
    nondec = all(asks[i + 1] >= asks[i] for i in range(4))
    v.append(("T1p", "채택" if (nondec and asks[-1] > asks[0]) else "기각",
              f"ask 평균={asks} (비감소이고 최소 한 구간 증가여야 함)"))
    total = [L1st[i] + m(RW[i], "L_report") for i in range(5)]
    rev = [i for i in range(1, 5) if total[i] > total[i - 1]]
    v.append(("T2p", "채택" if rev else "기각",
              "왕복 합계=" + str([round(x) for x in total])
              + (f" · {W[rev[0]-1]}→{W[rev[0]]} 에서 역전" if rev else " · 끝까지 단조 감소")))

    # ── A2-H8 레코드 수 종속성 ───────────────────────────────────────────
    Ns = [3, 12, 24]
    js = [m(c, "L_file") for c in ("J3", "J12", "J24")]
    ts = [m(c, "L_file") for c in ("T3", "T12", "T24")]
    D = [j - t for j, t in zip(js, ts)]
    a, b, r2 = linfit([float(n) for n in Ns], D)
    v.append(("L1", "채택" if r2 >= 0.99 else "기각",
              f"D(N)={[round(x) for x in D]} · 적합 D≈{a:.1f}N+{b:.1f} · R²={r2:.5f}"))
    p = [d / j for d, j in zip(D, js)]
    v.append(("L2", "채택" if p[0] < p[1] < p[2] else "기각",
              f"절감률 p(N)={[round(x,4) for x in p]} (단조 증가 기대)"))
    t12, t12ref = m("T12", "L_file"), 625.0
    v.append(("L3", "채택" if abs(pct(t12ref, t12)) <= TIE_DET else "기각",
              f"T12={t12:.0f} vs 라운드4 SLT={t12ref:.0f} ({pct(t12ref,t12):+.1f}%)"))

    # ── A6-H5 생성 프로그램 ──────────────────────────────────────────────
    ghd, ghp = m("GhiD", "L_file"), m("GhiP", "L_file")
    gld, glp = m("GloD", "L_file"), m("GloP", "L_file")
    v.append(("P1p", "채택" if (ghp < ghd and abs(pct(ghd, ghp)) > TIE_DET) else "기각",
              f"규칙적: 나열 {ghd:.0f} → 코드 {ghp:.0f} ({pct(ghd,ghp):+.1f}%)"))
    v.append(("P2p", "채택" if (glp > gld and abs(pct(gld, glp)) > TIE_DET) else "기각",
              f"불규칙: 나열 {gld:.0f} → 코드 {glp:.0f} ({pct(gld,glp):+.1f}%) — 역전 기대"))
    ex = [x for c in ("GhiP", "GloP") for x in by[c]]
    v.append(("P3p", "채택" if all(x.get("exec") for x in ex) else "기각",
              f"실행 대조 {sum(1 for x in ex if x.get('exec'))}/{len(ex)} 통과"))

    # ── A1-H5 예시 길이 앵커링 ───────────────────────────────────────────
    x0, x1, x2 = (m(c, "L_file") for c in ("X0", "X1", "X2"))
    v.append(("N1", "채택" if (x1 < x2 and abs(pct(x2, x1)) > TIE_SOFT) else "기각",
              f"짧은 예시 {x1:.0f} vs 긴 예시 {x2:.0f} ({pct(x2,x1):+.1f}%)"))
    v.append(("N2", "채택" if (x1 < x0 and abs(pct(x0, x1)) > TIE_SOFT) else "기각",
              f"예시 없음 {x0:.0f} → 짧은 예시 {x1:.0f} ({pct(x0,x1):+.1f}%)"))
    v.append(("N3", "채택" if min(m("X1", "cov"), m("X2", "cov")) >= 6 else "기각",
              f"cov X1={m('X1','cov'):.1f} X2={m('X2','cov'):.1f}"))
    v.append(("N4", "산출", f"예시 길이 대비 산출물 배율 — 짧은 {x1/148:.2f}배, 긴 {x2/805:.2f}배 "
                            "(판정 대상 아님)"))

    got = {k: s for k, s, _ in v}
    hyp = [
        ("A6-H3", got["R1"], "R1 (R3 전제 충족)"),
        ("A6-H8", "채택" if got["T1p"] == "채택" and got["T2p"] == "채택" else "기각",
         "T1' ∧ T2'"),
        ("A2-H8", "채택" if got["L1"] == "채택" and got["L2"] == "채택"
         else "부분 채택" if got["L1"] == "채택" else "기각", "L1 ∧ L2"),
        ("A6-H5", "채택" if got["P1p"] == "채택" and got["P3p"] == "채택" else "기각",
         "P1' ∧ P3'"),
        ("A1-H5", "채택" if got["N1"] == "채택" and got["N3"] == "채택" else "기각",
         "N1 ∧ N3"),
    ]

    out = ["kind\tid\tverdict\tdetail"]
    for k, s, det in v:
        out.append(f"예측\t{k}\t{s}\t{det}")
    for k, s, det in hyp:
        out.append(f"가설\t{k}\t{s}\t{det}")
    (RAW / "r5-verdicts.tsv").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
