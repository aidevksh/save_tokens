#!/usr/bin/env python3
"""라운드 7 시행 디렉터리 준비.

    ST_R7_ROOT=/path/to/st-r7 python experiments/scripts/setup_r7.py

각 시행 디렉터리를 만들고 `<RUNDIR>` 를 실제 절대 경로로 치환한 프롬프트를
`<시행>/prompt.txt` 로 둔다. T12(t08–t15)는 T11 산출물이 나온 뒤에 만든다
(`--consumers`).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROMPTS = REPO / "experiments/prompts"
R7 = Path(os.environ.get("ST_R7_ROOT", Path(tempfile.gettempdir()) / "st-r7"))

# 사전등록 §1 조건표 (신규 35시행 중 소비자 8건을 뺀 27건)
PROD = {
    "t01": "K", "t05": "K",
    "t02": "E", "t06": "E",
    "t03": "P", "t07": "P",
    "t16": "CC", "t20": "CC", "t24": "CC",
    "t17": "CI", "t21": "CI", "t25": "CI",
    "t18": "CR", "t22": "CR", "t26": "CR",
    "t04": "WN", "t19": "WN", "t23": "WN",
    "t27": "WF", "t30": "WF", "t33": "WF",
    "t28": "WT", "t31": "WT", "t34": "WT",
    "t29": "WB", "t32": "WB", "t35": "WB",
}

# T12 소비자 — 어느 생산자 시행의 산출물을 받는가 (사전등록 §1)
CONS = {
    "t08": ("UT", None), "t12": ("UT", None),      # T 는 라운드 4 재사용분
    "t09": ("UK", "t01"), "t13": ("UK", "t05"),
    "t10": ("UE", "t02"), "t14": ("UE", "t06"),
    "t11": ("UP", "t03"), "t15": ("UP", "t07"),
}
R4_SLT = REPO / "experiments/runs/r4"
R4_SRC = {"t08": "t03", "t12": "t14"}   # 라운드 4 SLT 두 시행


def write(trial: str, text: str) -> None:
    d = R7 / trial
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.txt").write_text(text.replace("<RUNDIR>", str(d).replace("\\", "/")),
                                  encoding="utf-8", newline="\n")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if "--consumers" in sys.argv:
        sys.path.insert(0, str(REPO / "experiments/scripts"))
        import gen_r7 as G
        n = 0
        for trial, (cond, src) in sorted(CONS.items()):
            if src is None:
                p = R4_SLT / R4_SRC[trial] / "out.txt"
            else:
                p = R7 / src / "out.txt"
            if not p.exists():
                print(f"  ! {trial} <- {p} 없음 (생산자 미완료)")
                continue
            write(trial, G.t12(cond, p.read_text(encoding="utf-8")))
            print(f"{trial}  {cond:3} <- {p}")
            n += 1
        print(f"\n소비자 {n}/8 준비")
        return 0

    for trial, cond in sorted(PROD.items()):
        src = PROMPTS / f"r7-{cond}.txt"
        write(trial, src.read_text(encoding="utf-8"))
        print(f"{trial}  {cond:3} <- {src.name}")
    print(f"\n생산자 {len(PROD)}시행 준비: {R7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
