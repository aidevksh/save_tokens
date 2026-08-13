#!/usr/bin/env python3
"""라운드 2 채점 — 품질 게이트 + 길이 + 기전 변수 (사전등록 §4, §5).

사용법:
    ST_R2_ROOT=/path/to/st-r2 python experiments/scripts/score_r2.py

시행 산출물 경로는 ST_R2_ROOT 로 지정한다. 생략하면 <임시디렉터리>/st-r2.
시행 디렉터리는 저장소 밖에 둔다 — 저장소 안에서 돌리면 피험 에이전트가
프로젝트 규약과 정답 키를 보게 되어 naive 조건이 깨진다.
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
R = Path(os.environ.get("ST_R2_ROOT", Path(tempfile.gettempdir()) / "st-r2"))
DATA = REPO / "experiments/data"

FX = {
    "30": (DATA / "02-deploy-original.yaml", DATA / "02-patch-expected.yaml"),
    "120": (DATA / "r2-deploy120-original.yaml", DATA / "r2-deploy120-expected.yaml"),
}

# 사전등록 §2 조건표. 시행 -> (조건, N)
TRIALS = {
    "t01": ("A", "30"), "t08": ("A", "30"),
    "t02": ("B", "30"), "t12": ("B", "30"),
    "t03": ("C", "30"), "t10": ("C", "30"),
    "t04": ("A", "120"), "t11": ("A", "120"),
    "t05": ("B", "120"), "t09": ("B", "120"),
    "t06": ("C", "120"), "t07": ("C", "120"),
}

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", re.M)


def changed_rows(orig: str, exp: str) -> set[int]:
    o, e = orig.rstrip("\n").split("\n"), exp.rstrip("\n").split("\n")
    return {i for i, (a, b) in enumerate(zip(o, e)) if a != b}


def context_lines(diff: str) -> list[int]:
    """hunk 별 컨텍스트 줄 수(변경 줄 앞뒤 ' ' 줄의 최댓값)를 센다."""
    out: list[int] = []
    cur: list[str] | None = None
    for ln in diff.split("\n"):
        if HUNK.match(ln):
            if cur is not None:
                out.append(_ctx_of(cur))
            cur = []
        elif cur is not None:
            cur.append(ln)
    if cur is not None:
        out.append(_ctx_of(cur))
    return out


def _ctx_of(body: list[str]) -> int:
    body = [b for b in body if b[:1] in (" ", "+", "-", "")]
    lead = 0
    for b in body:
        if b.startswith(" "):
            lead += 1
        else:
            break
    return lead


def score(trial: str, cond: str, n: str) -> dict:
    orig_p, exp_p = FX[n]
    orig = orig_p.read_text(encoding="utf-8").replace("\r\n", "\n")
    exp = exp_p.read_text(encoding="utf-8").replace("\r\n", "\n")
    fname = "out.yaml" if cond == "A" else "out.diff"
    p = R / trial / fname
    res: dict = {"trial": trial, "cond": f"{cond}{n}", "N": int(n), "gates": {}, "notes": []}

    if not p.exists() or p.stat().st_size == 0:
        res["gates"]["Q1_exists"] = False
        res["verdict"] = "무효"
        return res
    res["gates"]["Q1_exists"] = True

    raw = p.read_bytes()
    text = raw.decode("utf-8").replace("\r\n", "\n")
    res["chars"] = len(text)
    res["bytes"] = len(raw)
    res["lines"] = len(text.rstrip("\n").split("\n"))

    if cond == "A":
        lines = [ln for ln in text.rstrip("\n").split("\n") if ln.strip()]
        res["gates"]["Q2_format"] = (
            len(lines) == int(n) and "생략" not in text and "..." not in text and "```" not in text
        )
        res["gates"]["Q3_apply"] = True          # 적용 단계 없음
        res["k_obs"] = None
        res["ctx_obs"] = None
        final = text
    else:
        res["gates"]["Q2_format"] = all(
            m in text for m in ("--- a/deploy.yaml", "+++ b/deploy.yaml", "@@")
        )
        res["k_obs"] = len(HUNK.findall(text))
        ctx = context_lines(text)
        res["ctx_obs"] = max(ctx) if ctx else None
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            (work / "deploy.yaml").write_text(orig, encoding="utf-8", newline="\n")
            dp = work / "p.diff"
            dp.write_bytes(raw)
            applied, how = False, None
            for args in (["-p1"], ["-p0"], ["--recount", "-p1"], ["--unidiff-zero", "-p1"]):
                r = subprocess.run(
                    ["git", "apply", *args, str(dp)], cwd=work, capture_output=True, text=True
                )
                if r.returncode == 0:
                    applied, how = True, " ".join(args)
                    break
            res["gates"]["Q3_apply"] = applied
            res["apply_args"] = how
            if applied and how != "-p1":
                res["notes"].append(f"표준 -p1 실패, {how} 로만 적용됨")
            final = (
                (work / "deploy.yaml").read_text(encoding="utf-8").replace("\r\n", "\n")
                if applied else ""
            )

    res["gates"]["Q4_exact"] = final.rstrip("\n") == exp.rstrip("\n")
    got = final.rstrip("\n").split("\n") if final else []
    want = exp.rstrip("\n").split("\n")
    tgt = changed_rows(orig, exp)
    if len(got) == len(want):
        res["gates"]["Q5_requested"] = all(got[i] == want[i] for i in tgt)
        coll = [i + 1 for i in range(len(want)) if i not in tgt and got[i] != want[i]]
        res["gates"]["Q6_no_collateral"] = not coll
        if coll:
            res["notes"].append(f"부수 손상 행: {coll[:10]}")
    else:
        res["gates"]["Q5_requested"] = False
        res["gates"]["Q6_no_collateral"] = False
        res["notes"].append(f"줄 수 불일치: got={len(got)} want={len(want)}")

    core = ["Q1_exists", "Q2_format", "Q3_apply", "Q4_exact", "Q5_requested", "Q6_no_collateral"]
    res["verdict"] = "통과" if all(res["gates"].get(k) for k in core) else "게이트 실패"
    return res


def baseline(n: str, cond: str) -> int:
    """이상적 방출기 기준선 (사전등록 §2)."""
    orig_p, exp_p = FX[n]
    if cond == "A":
        return len(exp_p.read_text(encoding="utf-8").replace("\r\n", "\n"))
    c = "3" if cond == "B" else "1"
    r = subprocess.run(
        ["git", "diff", "--no-index", f"-U{c}", "--", str(orig_p), str(exp_p)],
        capture_output=True, text=True, cwd=REPO,
    )
    # git diff --no-index 는 헤더에 넘겨준 경로를 그대로 박는다. 절대 경로를 쓰면
    # 기준선이 경로 길이만큼 부풀어 오버헤드 H 가 음수로 나온다. 피험자가 실제로
    # 쓰는 표기(a/deploy.yaml, b/deploy.yaml)로 정규화한 뒤 센다.
    lines = []
    for ln in r.stdout.split("\n")[2:]:
        if ln.startswith("--- "):
            ln = "--- a/deploy.yaml"
        elif ln.startswith("+++ "):
            ln = "+++ b/deploy.yaml"
        lines.append(ln)
    return len("\n".join(lines))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = [score(t, c, n) for t, (c, n) in sorted(TRIALS.items())]

    by_cond: dict[str, list[dict]] = {}
    for r in rows:
        by_cond.setdefault(r["cond"], []).append(r)

    print(f"시행 루트: {R}\n")
    print(f"{'시행':<5} {'조건':<6} {'판정':<10} {'문자':>6} {'줄':>4} {'hunk':>5} {'ctx':>4}  비고")
    for r in rows:
        print(
            f"{r['trial']:<5} {r['cond']:<6} {r['verdict']:<10} "
            f"{r.get('chars', 0):>6} {r.get('lines', 0):>4} "
            f"{str(r.get('k_obs') or '-'):>5} {str(r.get('ctx_obs') if r.get('ctx_obs') is not None else '-'):>4}  "
            f"{r.get('apply_args') or ''}"
        )
        for k, v in r["gates"].items():
            if not v:
                print(f"        실패 게이트: {k}")
        for nt in r["notes"]:
            print(f"        {nt}")

    print("\n## 조건별 집계 (게이트 통과 시행만 길이 집계)")
    print(f"{'조건':<6} {'유효':>4} {'평균문자':>9} {'분산0':>6} {'기준선':>7} {'오버헤드H':>10} {'적용실패q':>10}")
    agg: dict[str, dict] = {}
    for cond, rs in sorted(by_cond.items()):
        ok = [r for r in rs if r["verdict"] == "통과"]
        c, n = cond[0], cond[1:]
        base = baseline(n, c)
        q = sum(1 for r in rs if r["gates"].get("Q3_apply") is False)
        if ok:
            mean = sum(r["chars"] for r in ok) / len(ok)
            same = len({r["chars"] for r in ok}) == 1 and len(ok) > 1
            h = (mean - base) / base
            agg[cond] = {"n_valid": len(ok), "mean_chars": round(mean, 1), "baseline": base,
                         "H": round(h, 4), "q_fail": q, "zero_var": same}
            print(f"{cond:<6} {len(ok):>4} {mean:>9.1f} {'예' if same else '아니오':>6} "
                  f"{base:>7} {h:>+9.1%} {q:>10}")
        else:
            agg[cond] = {"n_valid": 0, "q_fail": q, "baseline": base}
            print(f"{cond:<6} {0:>4} {'-':>9} {'-':>6} {base:>7} {'-':>10} {q:>10}")

    print("\n## 사전등록 §6 예측 대조")
    def rel(a: str, b: str) -> float | None:
        if agg.get(a, {}).get("n_valid") and agg.get(b, {}).get("n_valid"):
            return (agg[b]["mean_chars"] - agg[a]["mean_chars"]) / agg[a]["mean_chars"]
        return None

    checks = [
        ("P1 복제  F30: B 가 A 보다 김", rel("A30", "B30"), lambda d: d > 0.03),
        ("P2 역전  F120: B 가 A 대비 40%↓", rel("A120", "B120"), lambda d: d <= -0.40),
        ("P3a 컨텍스트 F30: C < B", rel("B30", "C30"), lambda d: d < -0.03),
        ("P3b 컨텍스트 F120: C < B", rel("B120", "C120"), lambda d: d < -0.03),
        ("P4 교차점 F30: C <= A", rel("A30", "C30"), lambda d: d <= 0.03),
    ]
    for label, d, ok in checks:
        if d is None:
            print(f"  {label:<34} 판정 불가 (유효 시행 부족)")
        else:
            print(f"  {label:<34} {d:>+8.1%}   {'충족' if ok(d) else '미충족'}")

    q_b = sum(agg.get(c, {}).get("q_fail", 0) for c in ("B30", "B120"))
    q_c = sum(agg.get(c, {}).get("q_fail", 0) for c in ("C30", "C120"))
    print(f"  {'P5 H/q 결합: C 적용실패 > B':<34} B={q_b} C={q_c}   "
          f"{'충족' if q_c > q_b else '미충족'}")

    dest = REPO / "experiments/raw/r2-scores.json"
    dest.write_text(
        json.dumps({"trials": rows, "conditions": agg}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n원시 채점 -> {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
