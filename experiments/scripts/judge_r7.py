#!/usr/bin/env python3
"""라운드 7 판정 — 사전등록 §5 예측을 채점 결과에 기계적으로 적용한다.

    python experiments/scripts/judge_r7.py

입력: experiments/raw/r7-scores.json (score_r7.py 산출)
출력: experiments/raw/r7-judgment.json + 표준출력 요약

판정 기준은 사전등록에서 그대로 옮긴 것이고 여기서 바꾸지 않는다.
"""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "experiments/raw"

TIE_TAB = 0.02      # T11·T12 동률 구간 (결정적 과제)
TIE_PROSE = 0.05    # T13·T14 동률 구간


def agg(rows: list[dict], cond: str, key: str) -> dict:
    vals = [r[key] for r in rows if r["condition"] == cond and key in r and not r.get("gate")]
    if not vals:
        return {"n": 0}
    return {"n": len(vals), "mean": round(st.mean(vals), 1), "min": min(vals), "max": max(vals),
            "sd": round(st.pstdev(vals), 1), "vals": vals}


def rel(a: float, b: float) -> float:
    """a 대비 b 의 상대 변화율 (음수 = 줄었다)."""
    return round((b - a) / a * 100, 1)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = json.loads((RAW / "r7-scores.json").read_text(encoding="utf-8"))

    A = {}
    for c in ("T", "K", "E", "P"):
        A[c] = {"L_out": agg(rows, c, "L_out"), "gz_out": agg(rows, c, "gz_out"),
                "acc_cell": agg(rows, c, "acc_cell")}
    for c in ("UT", "UK", "UE", "UP"):
        A[c] = {"acc_q": agg(rows, c, "acc_q")}
    for c in ("C0", "CC", "CI", "CR", "CK", "WN", "WF", "WT", "WB"):
        A[c] = {k: agg(rows, c, k) for k in
                ("L_file", "gz_file", "cov", "pre", "rep", "sumsec", "L_report", "T")}

    L = lambda c: A[c]["L_out"]["mean"]
    F = lambda c: A[c]["L_file"]["mean"]
    Q = lambda c: A[c]["acc_q"]["mean"]

    v: dict[str, dict] = {}

    # ── 축 2 사다리 ──────────────────────────────────────────────────
    d = rel(L("T"), L("K"))
    v["K1"] = {"주장": "키 축약이 줄인다", "값": f"L_out(K) {L('K')} vs T {L('T')} = {d}%",
               "판정": "채택" if d < -TIE_TAB * 100 else "기각"}
    v["K2"] = {"주장": "키 축약이 정확도를 깎는다",
               "값": f"acc_q(UK) {Q('UK')} vs UT {Q('UT')}",
               "판정": "채택" if Q("UK") < Q("UT") else "기각"}
    d = rel(L("T"), L("E"))
    v["E1"] = {"주장": "코드화가 줄인다", "값": f"L_out(E) {L('E')} vs T {L('T')} = {d}%",
               "판정": "채택" if d < -TIE_TAB * 100 else "기각"}
    v["E2"] = {"주장": "코드화의 손실이 키 축약보다 작다",
               "값": f"acc_q(UE) {Q('UE')} vs UK {Q('UK')}",
               "판정": "채택" if Q("UE") >= Q("UK") else "기각"}
    v["P1"] = {"주장": "positional 이 가장 짧다",
               "값": f"L_out(P) {L('P')} vs E {L('E')} vs K {L('K')}",
               "판정": "채택" if L("P") < L("E") and L("P") < L("K") else "기각"}
    v["P2"] = {"주장": "positional 의 손실이 가장 크다",
               "값": f"acc_q(UP) {Q('UP')} vs UE {Q('UE')} vs UK {Q('UK')}",
               "판정": "채택" if Q("UP") < Q("UE") and Q("UP") <= Q("UK") else "기각"}

    # ── 축 1 요인 분해 ───────────────────────────────────────────────
    d = rel(F("C0"), F("CI"))
    v["I1"] = {"주장": "서론·맺음말 억제가 줄인다",
               "값": f"L_file(CI) {F('CI')} vs C0 {F('C0')} = {d}%",
               "판정": "채택" if d < -TIE_PROSE * 100 else "기각"}
    v["I2"] = {"주장": "품질 유지", "값": f"cov(CI) {A['CI']['cov']['mean']}",
               "판정": "채택" if A["CI"]["cov"]["mean"] == 6.0 else "기각"}
    pre_ok = A["CI"]["pre"]["mean"] < A["C0"]["pre"]["mean"]
    sum_ok = A["CI"]["sumsec"]["mean"] < A["C0"]["sumsec"]["mean"]
    v["I3"] = {"주장": "표적에 맞았다",
               "값": (f"pre(CI) {A['CI']['pre']['mean']} vs C0 {A['C0']['pre']['mean']} / "
                      f"sumsec(CI) {A['CI']['sumsec']['mean']} vs C0 {A['C0']['sumsec']['mean']}"),
               "판정": "참" if (pre_ok and sum_ok) else "거짓 — 처치가 표적을 안 건드렸다"}
    order = sorted(("CC", "CI", "CR"), key=F)
    v["I4"] = {"주장": "(산출) 세 명제의 기여 순위",
               "값": " < ".join(f"{c} {F(c)}" for c in order), "판정": "산출"}
    di = {c: round(F("C0") - F(c), 1) for c in ("CC", "CI", "CR")}
    s = round(sum(di.values()), 1)
    dk = round(F("C0") - F("CK"), 1)
    v["I5"] = {"주장": "(산출) 하위가산성",
               "값": (f"d(CK) {dk} vs Σd_i {s} ({', '.join(f'{k} {x}' for k, x in di.items())}) "
                      f"= {round(dk / s * 100, 1)}%"), "판정": "산출"}

    # ── 축 1 지시 위치 ───────────────────────────────────────────────
    d = rel(F("WN"), F("WF"))
    v["W1"] = {"주장": "지시가 긴 프롬프트에서도 듣는다",
               "값": f"L_file(WF) {F('WF')} vs WN {F('WN')} = {d}%",
               "판정": "채택" if d < -TIE_PROSE * 100 else "기각"}
    d = rel(F("WF"), F("WB"))
    v["W2"] = {"주장": "앞+말미가 앞보다 더 줄인다",
               "값": f"L_file(WB) {F('WB')} vs WF {F('WF')} = {d}%",
               "판정": "채택" if d < -TIE_PROSE * 100 else "기각"}
    d = rel(F("WF"), F("WT"))
    v["W3"] = {"주장": "위치 효과", "값": f"L_file(WT) {F('WT')} vs WF {F('WF')} = {d}%",
               "판정": "위치가 작동" if abs(d) > TIE_PROSE * 100 else "위치는 무관"}
    lo = min(A[c]["cov"]["mean"] for c in ("WN", "WF", "WT", "WB"))
    v["W4"] = {"주장": "품질 유지", "값": f"min cov {lo} (10항목 중)",
               "판정": "채택" if lo >= 9.0 else "기각"}

    # ── 가설 매핑 (사전등록 §5) ──────────────────────────────────────
    def ok(k: str) -> bool:
        return v[k]["판정"] == "채택"

    hyp = {
        "A2-H2": ("채택" if ok("K1") and ok("K2") else
                  "부분 채택" if ok("K1") else "기각"),
        "A2-H3": "채택" if ok("E1") and ok("E2") else "기각",
        "A2-H5": ("채택" if ok("P1") and ok("P2") else
                  "부분 채택" if ok("P1") else "기각"),
        "A1-H4": "채택" if ok("I1") and ok("I2") else "기각",
        "A1-H2": ("판정 불가" if not ok("W1") else "채택" if ok("W2") else "기각"),
    }

    out = {"conditions": A, "predictions": v, "hypotheses": hyp}
    (RAW / "r7-judgment.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    keys = ["L_out", "gz_out", "acc_cell", "acc_q", "L_file", "gz_file",
            "cov", "pre", "rep", "sumsec", "L_report", "T"]
    lines = ["condition\tn\t" + "\t".join(f"{k}\t{k}_sd" for k in keys)]
    for c, m in A.items():
        n = max((s.get("n", 0) for s in m.values()), default=0)
        cells = []
        for k in keys:
            s = m.get(k, {})
            cells += [str(s.get("mean", "")), str(s.get("sd", ""))]
        lines.append(f"{c}\t{n}\t" + "\t".join(cells))
    (RAW / "r7-condition-means.tsv").write_text("\n".join(lines) + "\n",
                                                encoding="utf-8", newline="\n")

    vl = ["prediction\tverdict\tvalue\tclaim"]
    vl += [f"{k}\t{r['판정']}\t{r['값']}\t{r['주장']}" for k, r in v.items()]
    vl += [f"{k}\t{s}\t\t가설 판정" for k, s in hyp.items()]
    (RAW / "r7-verdicts.tsv").write_text("\n".join(vl) + "\n",
                                         encoding="utf-8", newline="\n")

    print("조건 요약 (mean / sd / n)")
    for c, m in A.items():
        bits = [f"{k} {s['mean']}±{s['sd']}(n={s['n']})" for k, s in m.items() if s["n"]]
        print(f"  {c:3} {'  '.join(bits)}")
    print("\n예측 판정")
    for k, r in v.items():
        print(f"  {k:3} {r['판정']:28} {r['값']}   — {r['주장']}")
    print("\n가설")
    for k, s in hyp.items():
        print(f"  {k} {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
