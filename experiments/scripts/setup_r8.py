#!/usr/bin/env python3
"""라운드 8 시행 디렉터리 준비.

    ST_R8_ROOT=/path/to/st-r8 python experiments/scripts/setup_r8.py
    ...                       python experiments/scripts/setup_r8.py --consumers

각 시행 디렉터리를 만들고 `<RUNDIR>` 를 실제 절대 경로로 치환한 프롬프트를
`<시행>/prompt.txt` 로 둔다. T15 소비자(t07–t12)는 생산자 산출물이 나온 뒤에
`--consumers` 로 만든다. T18(t25–t30)은 픽스처 두 파일을 함께 복사한다.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROMPTS = REPO / "experiments/prompts"
FIXTURE = REPO / "experiments/fixtures/task-d-schedule"
R8 = Path(os.environ.get("ST_R8_ROOT", Path(tempfile.gettempdir()) / "st-r8"))

# 사전등록 §1 조건표 — 소비자 6건(t07–t12)을 뺀 24건
PROD = {
    "t01": "T", "t04": "T",
    "t02": "K", "t05": "K",
    "t03": "R", "t06": "R",
    "t13": "CN150", "t15": "CN150", "t17": "CN150",
    "t14": "CN80", "t16": "CN80", "t18": "CN80",
    "t19": "WN", "t21": "WN", "t23": "WN",
    "t20": "WT", "t22": "WT", "t24": "WT",
    "t25": "DB", "t26": "DB", "t27": "DB",
    "t28": "DS", "t29": "DS", "t30": "DS",
}

# 라운드 7 프롬프트를 그대로 쓰는 조건 (A1-H8 풀링 전제)
PROMPT_FILE = {"WN": "r7-WN.txt", "WT": "r7-WT.txt"}

# 픽스처가 필요한 조건
NEEDS_FIXTURE = {"DB", "DS"}

# T15 소비자 — 어느 생산자 시행의 산출물을 받는가 (사전등록 §1)
CONS = {
    "t07": ("UT", "t01"), "t10": ("UT", "t04"),
    "t08": ("UK", "t02"), "t11": ("UK", "t05"),
    "t09": ("UR", "t03"), "t12": ("UR", "t06"),
}

PILOT = ("t25", "t26")


def write(trial: str, text: str) -> Path:
    d = R8 / trial
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.txt").write_text(text.replace("<RUNDIR>", str(d).replace("\\", "/")),
                                  encoding="utf-8", newline="\n")
    return d


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    if "--consumers" in sys.argv:
        sys.path.insert(0, str(REPO / "experiments/scripts"))
        import gen_r8 as G
        n = 0
        for trial, (cond, src) in sorted(CONS.items()):
            p = R8 / src / "out.txt"
            if not p.exists():
                print(f"  ! {trial} <- {p} 없음 (생산자 미완료)")
                continue
            write(trial, G.t15u(cond, p.read_text(encoding="utf-8")))
            print(f"{trial}  {cond:3} <- {src}/out.txt")
            n += 1
        print(f"\n소비자 {n}/{len(CONS)} 준비")
        return 0

    only = [a for a in sys.argv[1:] if a.startswith("t")]
    todo = {k: v for k, v in PROD.items() if not only or k in only}

    for trial, cond in sorted(todo.items()):
        name = PROMPT_FILE.get(cond, f"r8-{cond}.txt")
        src = PROMPTS / name
        d = write(trial, src.read_text(encoding="utf-8"))
        if cond in NEEDS_FIXTURE:
            for f in ("sched.js", "sched.test.js"):
                shutil.copy2(FIXTURE / f, d / f)
        print(f"{trial}  {cond:6} <- {src.name}"
              + ("  + 픽스처 2파일" if cond in NEEDS_FIXTURE else ""))
    print(f"\n{len(todo)}시행 준비: {R8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
