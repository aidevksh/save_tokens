#!/usr/bin/env python3
"""라운드 1 품질 게이트 채점 (H1 추출 / H2 패치).

사전등록: experiments/round1-plan.md §5.1, §5.2
길이는 재지 않는다 — 길이는 tools/measure.py 전담.

사용법:
    python experiments/scripts/score_r1.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
R = Path("C:/Users/FORYOUCOM/AppData/Local/Temp/st-r1")
GT = REPO / "experiments/data/02-tickets-groundtruth.tsv"
ORIG = REPO / "experiments/data/02-deploy-original.yaml"
EXPECTED = REPO / "experiments/data/02-patch-expected.yaml"

COLS = ["ticket_id", "date", "tier", "product", "category", "priority", "resolved", "response_hours"]
H1_A = {"t01": "out.json", "t08": "out.json", "t13": "out.json", "t20": "out.json"}
H1_B = {"t02": "out.tsv", "t07": "out.tsv", "t14": "out.tsv", "t19": "out.tsv"}
H2_A = {"t03": "out.yaml", "t10": "out.yaml", "t15": "out.yaml", "t22": "out.yaml"}
H2_B = {"t04": "out.diff", "t09": "out.diff", "t16": "out.diff", "t21": "out.diff"}


def load_gt() -> list[dict[str, str]]:
    lines = GT.read_text(encoding="utf-8").strip().split("\n")
    header = lines[0].split("\t")
    assert header == COLS, f"정답키 열 순서 불일치: {header}"
    return [dict(zip(COLS, ln.split("\t"))) for ln in lines[1:]]


def norm(field: str, value: object) -> str:
    """§5.1 Q5 정규화 규칙."""
    s = str(value).strip()
    if field == "response_hours":
        try:
            return f"{float(s):.6g}"          # 0.5 == .5 == 0.50
        except ValueError:
            return s.lower()
    if field == "resolved":
        return s.lower()                       # true/false
    return s.lower()                           # 나머지는 대소문자 무시


def score_h1(trial: str, fname: str, cond: str, gt: list[dict]) -> dict:
    p = R / trial / fname
    res: dict = {"trial": trial, "cond": cond, "gates": {}, "notes": []}
    if not p.exists() or p.stat().st_size == 0:
        res["gates"]["Q1_exists"] = False
        res["verdict"] = "무효"
        return res
    res["gates"]["Q1_exists"] = True
    text = p.read_text(encoding="utf-8")

    # Q2 파싱
    rows: list[dict] = []
    try:
        if cond == "A":
            data = json.loads(text)
            assert isinstance(data, list)
            rows = [{k: r.get(k) for k in COLS} for r in data]
            res["gates"]["Q4_fields"] = all(set(COLS) <= set(r.keys()) for r in data)
        else:
            lines = [ln for ln in text.split("\n") if ln.strip()]
            head = lines[0].split("\t")
            res["gates"]["Q4_fields"] = head == COLS
            rows = [dict(zip(COLS, ln.split("\t"))) for ln in lines[1:]]
            if not all(len(ln.split("\t")) == 8 for ln in lines[1:]):
                raise ValueError("탭 8열 아님")
        res["gates"]["Q2_parse"] = True
    except Exception as e:                       # noqa: BLE001
        res["gates"]["Q2_parse"] = False
        res["notes"].append(f"파싱 실패: {e}")
        res["verdict"] = "무효"
        return res

    res["gates"]["Q3_count"] = len(rows) == 12

    # Q5 셀 정확도 / Q6 레코드 정확도
    by_id = {norm("ticket_id", r["ticket_id"]): r for r in rows}
    cells_ok = 0
    recs_ok = 0
    wrong: list[str] = []
    for g in gt:
        got = by_id.get(norm("ticket_id", g["ticket_id"]))
        if got is None:
            wrong.append(f"{g['ticket_id']}: 레코드 없음")
            continue
        rec_ok = True
        for f in COLS:
            if norm(f, got.get(f)) == norm(f, g[f]):
                cells_ok += 1
            else:
                rec_ok = False
                wrong.append(f"{g['ticket_id']}.{f}: got={got.get(f)!r} want={g[f]!r}")
        recs_ok += rec_ok
    res["cell_accuracy"] = round(cells_ok / 96, 4)
    res["record_accuracy"] = recs_ok
    res["gates"]["Q5_cell>=0.99"] = res["cell_accuracy"] >= 0.99
    if wrong:
        res["notes"].append("불일치: " + "; ".join(wrong[:10]))

    # Q7 데이터 외 텍스트 (게이트 아님)
    res["Q7_extra_text"] = "```" in text or (cond == "A" and not text.lstrip().startswith("["))

    core = ["Q1_exists", "Q2_parse", "Q3_count", "Q4_fields", "Q5_cell>=0.99"]
    res["verdict"] = "통과" if all(res["gates"].get(k) for k in core) else "게이트 실패"
    return res


def score_h2(trial: str, fname: str, cond: str) -> dict:
    p = R / trial / fname
    res: dict = {"trial": trial, "cond": cond, "gates": {}, "notes": []}
    if not p.exists() or p.stat().st_size == 0:
        res["gates"]["Q1_exists"] = False
        res["verdict"] = "무효"
        return res
    res["gates"]["Q1_exists"] = True
    text = p.read_text(encoding="utf-8")
    expected = EXPECTED.read_text(encoding="utf-8").replace("\r\n", "\n")

    if cond == "A":
        # Q2 형식: 30줄 전체, 축약 없음
        lines = [ln for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]
        res["gates"]["Q2_format"] = len(lines) == 30 and "생략" not in text and "..." not in text
        res["gates"]["Q3_apply"] = True          # 적용 단계 없음
        final = text.replace("\r\n", "\n")
    else:
        # Q2 형식: unified diff 헤더
        res["gates"]["Q2_format"] = all(m in text for m in ("--- a/deploy.yaml", "+++ b/deploy.yaml", "@@"))
        # Q3 기계 적용
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            (work / "deploy.yaml").write_bytes(ORIG.read_bytes())
            dp = work / "p.diff"
            dp.write_bytes(p.read_bytes())
            applied = False
            for args in (["-p1"], ["-p0"], ["--recount", "-p1"]):
                r = subprocess.run(
                    ["git", "apply", *args, str(dp)],
                    cwd=work, capture_output=True, text=True,
                )
                if r.returncode == 0:
                    applied = True
                    res["notes"].append(f"적용 성공: git apply {' '.join(args)}")
                    break
            res["gates"]["Q3_apply"] = applied
            final = (work / "deploy.yaml").read_text(encoding="utf-8").replace("\r\n", "\n") if applied else ""

    # Q4 완전 일치 / Q5 요청 반영 / Q6 부수 손상
    res["gates"]["Q4_exact"] = final.strip("\n") == expected.strip("\n")
    exp_lines = expected.strip("\n").split("\n")
    got_lines = final.strip("\n").split("\n") if final else []
    changed_rows = {1, 4, 15, 16, 19, 27}        # 0-indexed: 2,5,16,17,20,28행
    if len(got_lines) == len(exp_lines) == 30:
        res["gates"]["Q5_requested_6of6"] = all(got_lines[i] == exp_lines[i] for i in changed_rows)
        collateral = [i + 1 for i in range(30) if i not in changed_rows and got_lines[i] != exp_lines[i]]
        res["gates"]["Q6_no_collateral"] = not collateral
        if collateral:
            res["notes"].append(f"부수 손상 행: {collateral}")
    else:
        res["gates"]["Q5_requested_6of6"] = False
        res["gates"]["Q6_no_collateral"] = False
        res["notes"].append(f"줄 수 불일치: got={len(got_lines)} want=30")

    core = ["Q1_exists", "Q2_format", "Q3_apply", "Q4_exact", "Q5_requested_6of6", "Q6_no_collateral"]
    res["verdict"] = "통과" if all(res["gates"].get(k) for k in core) else "게이트 실패"
    return res


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    gt = load_gt()
    assert len(gt) == 12, f"정답키 레코드 수 {len(gt)}"

    out: dict[str, list] = {}
    for name, spec, cond, fn in (
        ("H1-A", H1_A, "A", score_h1), ("H1-B", H1_B, "B", score_h1),
        ("H2-A", H2_A, "A", score_h2), ("H2-B", H2_B, "B", score_h2),
    ):
        rows = [fn(t, f, cond, gt) if fn is score_h1 else fn(t, f, cond) for t, f in spec.items()]
        out[name] = rows
        passed = sum(r["verdict"] == "통과" for r in rows)
        print(f"\n## {name} — 통과 {passed}/{len(rows)}")
        for r in rows:
            extra = ""
            if "cell_accuracy" in r:
                extra = f"  셀정확도={r['cell_accuracy']} 레코드정확도={r['record_accuracy']}/12"
            print(f"  {r['trial']}  {r['verdict']}{extra}")
            failed = [k for k, v in r["gates"].items() if not v]
            if failed:
                print(f"      실패 게이트: {', '.join(failed)}")
            for n in r["notes"]:
                print(f"      {n}")

    dest = REPO / "experiments/raw/r1-quality.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n원시 채점 결과 -> {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
