#!/usr/bin/env python3
"""라운드 6 판정 — 사전등록 §5 부등식을 그대로 계산한다.

    python experiments/scripts/judge_r6.py

입력: experiments/raw/r6-scores.json
출력: experiments/raw/r6-verdicts.tsv, r6-condition-means.tsv
"""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "experiments/raw"
TIE = 5.0  # % — 전 과제 동일 (둘 다 분산이 있는 과제다)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = json.loads((RAW / "r6-scores.json").read_text(encoding="utf-8"))
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

    order = ["B", "S3", "S4", "S5", "ALL", "C0", "CK", "CN800", "CN300"]
    means = ["condition\tn\tL_diff\tsd_diff\tL_report\tT\tcmt\textra\tpass\tL_file\tcov"]
    for c in order:
        g = by[c]
        has = lambda k: k in g[0]  # noqa: E731
        means.append("\t".join([
            c, str(len(g)),
            f"{m(c,'L_diff'):.1f}" if has("L_diff") else "",
            f"{sd(c,'L_diff'):.1f}" if has("L_diff") else "",
            f"{m(c,'L_report'):.1f}",
            f"{m(c,'T'):.1f}" if has("T") else "",
            f"{m(c,'cmt'):.4f}" if has("cmt") else "",
            f"{m(c,'extra'):.1f}" if has("extra") else "",
            f"{m(c,'pass'):.1f}" if has("pass") else "",
            f"{m(c,'L_file'):.1f}",
            f"{m(c,'cov'):.2f}" if has("cov") else "",
        ]))
    (RAW / "r6-condition-means.tsv").write_text("\n".join(means) + "\n",
                                                encoding="utf-8", newline="\n")

    v: list[tuple[str, str, str]] = []

    # ── A5-H3 마지막 요약 규칙 ───────────────────────────────────────────
    rb, r3 = m("B", "L_report"), m("S3", "L_report")
    v.append(("H3a", "채택" if (r3 < rb and abs(pct(rb, r3)) > TIE) else "기각",
              f"L_report {rb:.0f} -> {r3:.0f} ({pct(rb,r3):+.1f}%)"))
    v.append(("H3b", "채택" if m("S3", "pass") >= m("B", "pass") else "기각",
              f"pass {m('B','pass'):.1f} -> {m('S3','pass'):.1f} (9 만점)"))
    tb, t3 = m("B", "T"), m("S3", "T")
    v.append(("H3c", "채택" if (t3 < tb and abs(pct(tb, t3)) > TIE) else "기각",
              f"총출력 T {tb:.0f} -> {t3:.0f} ({pct(tb,t3):+.1f}%)"))

    # ── A5-H4 범위 제한 ─────────────────────────────────────────────────
    db, d4 = m("B", "L_diff"), m("S4", "L_diff")
    v.append(("H4a", "채택" if (d4 < db and abs(pct(db, d4)) > TIE) else "기각",
              f"L_diff {db:.0f} -> {d4:.0f} ({pct(db,d4):+.1f}%) · 표준편차 B={sd('B','L_diff'):.0f} S4={sd('S4','L_diff'):.0f}"))
    eb, e4 = m("B", "extra"), m("S4", "extra")
    v.append(("H4b", "판정 불가" if eb == 0 else ("채택" if e4 < eb else "기각"),
              f"extra {eb:.1f} -> {e4:.1f} — 기준 조건이 0이면 바닥 효과로 판정 불가(사전등록 §5)"))
    v.append(("H4c", "채택" if m("S4", "pass") >= m("B", "pass") else "기각",
              f"pass {m('B','pass'):.1f} -> {m('S4','pass'):.1f}"))

    # ── A5-H5 주석 밀도 ─────────────────────────────────────────────────
    cb, c5 = m("B", "cmt"), m("S5", "cmt")
    v.append(("H5a", "채택" if (c5 < cb and (cb - c5) > 0.02) else "기각",
              f"주석 비율 {cb:.4f} -> {c5:.4f} (절대 차 {cb-c5:+.4f}, 기준 0.02) · "
              f"추가된 주석 문자 B={m('B','cmt_chars'):.0f} S5={m('S5','cmt_chars'):.0f} "
              "(둘 다 원본 그대로 = 아무도 주석을 더하지 않았다)"))
    v.append(("H5b", "채택" if m("S5", "pass") >= m("B", "pass") else "기각",
              f"pass {m('B','pass'):.1f} -> {m('S5','pass'):.1f}"))

    # ── A5-H7 하위가산성 (동반 판정) ────────────────────────────────────
    d_i = [tb - m(c, "T") for c in ("S3", "S4", "S5")]
    d_all = tb - m("ALL", "T")
    v.append(("H7a", "채택" if (d_all < sum(d_i) and abs(pct(sum(d_i), d_all)) > TIE) else "기각",
              f"개별 절감 합 {sum(d_i):.0f} (S3 {d_i[0]:.0f} + S4 {d_i[1]:.0f} + S5 {d_i[2]:.0f}) "
              f"vs 묶음 {d_all:.0f} → 묶음이 합의 {d_all/sum(d_i)*100:.1f}%"))

    # ── A1-H3 수치 상한 ─────────────────────────────────────────────────
    for c in ("CN800", "CN300"):
        ok = sum(1 for x in by[c] if x.get("under_cap"))
        v.append((f"Q1-{c}", "채택" if ok >= 2 else "기각",
                  f"상한 {by[c][0]['cap']}자 준수 {ok}/{len(by[c])} · 평균 {m(c,'L_file'):.0f}자"))
    lk, l3 = m("CK", "L_file"), m("CN300", "L_file")
    v.append(("Q2", "채택" if (l3 < lk and abs(pct(lk, l3)) > TIE) else "기각",
              f"간결성 지시 {lk:.0f} vs 300자 상한 {l3:.0f} ({pct(lk,l3):+.1f}%)"))
    cv = m("CN300", "cov")
    v.append(("Q3", "채택" if cv < 6.0 else "기각",
              f"cov(CN300) = {cv:.2f} (6.0 미만이면 충족도 하락) "
              "⚠ 손으로 확인한 결과 거짓 음성 — 본문 §5 참조"))
    v.append(("Q4", "산출",
              f"C0 {m('C0','L_file'):.0f} · CK {lk:.0f} · CN800 {m('CN800','L_file'):.0f} · "
              f"CN300 {l3:.0f} (판정 대상 아님)"))

    got = {k: s for k, s, _ in v}
    hyp = [
        ("A5-H3", "채택" if all(got[k] == "채택" for k in ("H3a", "H3b", "H3c")) else "기각",
         "H3a ∧ H3b ∧ H3c"),
        ("A5-H4", "채택" if got["H4a"] == "채택" and got["H4c"] == "채택" else "기각",
         "H4a ∧ H4c (H4b는 바닥 효과로 판정 불가)"),
        ("A5-H5", "채택" if got["H5a"] == "채택" and got["H5b"] == "채택" else "기각",
         "H5a ∧ H5b"),
        ("A5-H7", got["H7a"], "H7a — 라운드 1 판정 불가를 대체"),
        ("A1-H3", "채택" if got["Q2"] == "채택" and got["Q3"] == "채택" else "기각",
         "Q2 ∧ Q3 (사전등록대로. Q3의 계측 결함은 본문에 고지)"),
    ]

    out = ["kind\tid\tverdict\tdetail"]
    for k, s, det in v:
        out.append(f"예측\t{k}\t{s}\t{det}")
    for k, s, det in hyp:
        out.append(f"가설\t{k}\t{s}\t{det}")
    (RAW / "r6-verdicts.tsv").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
