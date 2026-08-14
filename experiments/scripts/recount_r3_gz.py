#!/usr/bin/env python3
"""라운드 3 산출물을 압축 후 크기로 재측정한다 (사후 탐색).

    python experiments/scripts/recount_r3_gz.py   ->  experiments/raw/r3-gz-recount.tsv

재실험이 아니다. 보존된 산출물은 그대로이고 지표만 추가한 것이라 라운드 3의
사전등록 판정(문자 기준 L_file)은 손대지 않는다. 이 표는 A6-H1/A6-H7 을 세우는
근거로만 쓴다.

왜 재는가: 문자 수는 '서식이 부풀었다'와 '내용이 늘었다'를 구분하지 못한다.
bytes_gz 는 반복을 걷어낸 나머지의 대리 지표라 그 둘을 가른다.
"""

from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import measure  # noqa: E402

RUNS = REPO / "experiments/runs/r3"
DEST = REPO / "experiments/raw/r3-gz-recount.tsv"
COLS = ("chars", "bytes_utf8", "bytes_gz", "redundancy")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    # 시행 -> 조건 대응은 보존된 conditions.tsv 가 유일한 출처다. 손으로 적지 않는다.
    rows = [ln.split("\t") for ln in
            (RUNS / "conditions.tsv").read_text(encoding="utf-8").strip().split("\n")[1:]]
    by_cond: dict[str, list[dict]] = {}
    for trial, cond, _prompt, task in rows:
        if task != "T1":  # 산문 과제만. T2 는 형식이 달라 같은 축에 놓을 수 없다.
            continue
        m = measure.measure((RUNS / trial / "doc.txt").read_text(encoding="utf-8"))
        by_cond.setdefault(cond, []).append(m)

    base = None
    out = ["condition\tn\t" + "\t".join(COLS) + "\tpct_chars\tpct_bytes_gz"]
    for cond in ("B", "N", "P", "V", "F"):
        ms = by_cond[cond]
        avg = {k: st.mean(m[k] for m in ms) for k in COLS}
        if base is None:
            base = avg
        pc = (avg["chars"] - base["chars"]) / base["chars"] * 100
        pg = (avg["bytes_gz"] - base["bytes_gz"]) / base["bytes_gz"] * 100
        out.append(f"{cond}\t{len(ms)}\t{avg['chars']:.0f}\t{avg['bytes_utf8']:.0f}\t"
                   f"{avg['bytes_gz']:.0f}\t{avg['redundancy']:.3f}\t{pc:+.1f}\t{pg:+.1f}")

    DEST.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))
    print(f"\n-> {DEST.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
