#!/usr/bin/env python3
"""라운드 4 재료·프롬프트 생성기.

    python experiments/scripts/gen_r4.py

손으로 쓰면 조건 간 공통부에 의도치 않은 차이가 섞인다. 공통부를 한 곳에서
만들고 처치 문단만 갈아 끼운다. 생성 후 다음을 스스로 검증한다.

  - T1 사다리의 처치 줄 3개가 **문자 수 동일** (지시 길이가 아니라 지시 개수의 효과를 보려면 필요)
  - T1/T2/T3 각 과제 안에서 처치를 뺀 공통부가 **바이트 동일**
  - T3 재료의 행 방향 반복률 r 이 목표값과 일치

산출:
  experiments/prompts/r4-*.txt        피험자 프롬프트 (<RUNDIR> 치환 전)
  experiments/data/r4-assets-*.tsv    T3 정답 키
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROMPTS = REPO / "experiments/prompts"
DATA = REPO / "experiments/data"

HEAD = ("작업 디렉터리는 <RUNDIR> 입니다. 이 디렉터리는 다른 팀이 관리하는 독립 프로젝트이고, "
        "아래 지시가 이 작업의 유일한 명세입니다. 다른 위치의 파일이나 규약은 참조하지 마세요.")
TAIL = "도구 호출이 거부되면 다른 수단으로 우회하지 말고, 거부되었다는 사실을 보고하고 중단합니다."

# ─────────────────────────────────────────────────────────── T1 산문 사다리

# 라운드 3 P 조건의 처치 줄. K1 은 라운드 3 P 와 바이트 동일해야 한다.
L1 = "핵심만 간결히 쓰세요. 본문부터 시작해 본문으로 끝내세요. 각 내용은 한 번만 쓰세요."
# 사다리 2단: 내용 범위를 좁힌다. 극성은 L1 과 같은 긍정형으로 맞춘다.
L2 = "설명은 명세에 있는 사실로만 쓰세요. 예시는 하나까지만 쓰세요. 문장은 짧게 끊으세요."
# 사다리 3단: 수치 상한.
L3 = "각 항목은 두 문장 이내로 쓰세요. 표현은 평서문으로 쓰세요. 수식어는 하나만 쓰세요."

T1_BODY = """우리 서비스의 요청 제한(rate limit) 동작 명세는 다음과 같습니다.

| 항목 | 값 |
|---|---|
| 버킷 용량 | 60 |
| 리필 속도 | 초당 1개 |
| 집계 단위 | API 키 (IP 주소가 아님) |
| 초과 시 상태 코드 | 429 |
| 재시도 안내 헤더 | `Retry-After` (초 단위 정수) |
| 예외 | `admin` 스코프 키는 제한에서 제외 |

**할 일**: 이 명세를 처음 보는 신입 백엔드 개발자를 위한 설명 문서를 작성해서
`<RUNDIR>/doc.txt` 에 저장하세요.

문서에는 위 6개 항목이 **모두** 설명되어 있어야 합니다."""


def t1(rungs: list[str]) -> str:
    parts = [HEAD, "", T1_BODY, ""]
    if rungs:
        parts += ["\n".join(rungs), ""]
    parts += [TAIL, "", "문서는 한국어로 작성합니다.", ""]
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────── T2 코딩 루프

T2_BODY = """`<RUNDIR>/stats.py` 는 리포팅 파이프라인이 쓰는 기술통계 도우미 모듈이고
`<RUNDIR>/test_stats.py` 는 그 모듈의 단위 테스트입니다. 지금 테스트가 실패합니다.

    cd <RUNDIR> && python -m unittest

**할 일**: `stats.py` 를 고쳐 테스트 11개가 모두 통과하게 만드세요.
테스트 파일은 명세이므로 수정하지 마세요."""

# 상호정보량 제거 처치. 간결성 지시가 아니라 '입력에서 복원 가능한 것'만 겨냥한다.
# 극성은 긍정형으로 맞춘다 (라운드 3 A1-H1).
T2_X = ("보고에는 새로 알게 된 것만 적습니다. 요청 내용과 파일 내용은 읽는 사람이 이미 "
        "가지고 있습니다.")


def t2(treat: str | None) -> str:
    parts = [HEAD, "", T2_BODY, ""]
    if treat:
        parts += [treat, ""]
    parts += [TAIL, "", "설명은 한국어로 씁니다.", ""]
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────── T3 표 직렬화

COLS = ["asset_id", "region", "env", "role", "os", "tier", "cpu", "status"]
VALS = {
    "region": ["apne1", "apne2", "usea1", "euwe1"],
    "env": ["prod", "stage", "dev"],
    "role": ["web", "api", "batch", "cache"],
    "os": ["ubuntu22", "ubuntu24", "debian12", "alpine3"],
    "tier": ["small", "medium", "large"],
    "cpu": ["2", "4", "8", "16"],
    "status": ["active", "drained", "halted"],
}
NROW = 12
FREE = COLS[1:]  # asset_id 는 고유값이라 반복 대상이 아니다
ELIGIBLE = len(FREE) * (NROW - 1)  # 77 칸


def build_table(repeats: int) -> list[list[str]]:
    """행 방향 반복이 정확히 `repeats` 칸인 12x8 표를 결정적으로 만든다.

    Bresenham 으로 77칸에 고르게 뿌린다. 난수를 쓰지 않으므로 재실행하면
    같은 표가 나온다 — 재료가 흔들리면 조건 간 비교가 무효다.
    """
    flag = [(k * repeats) // ELIGIBLE != ((k + 1) * repeats) // ELIGIBLE
            for k in range(ELIGIBLE)]
    rows = [[f"AS-{2001 + i}"] + [VALS[c][0] for c in FREE] for i in range(NROW)]
    cursor = {c: 0 for c in FREE}
    for i in range(1, NROW):
        for j, c in enumerate(FREE):
            if flag[(i - 1) * len(FREE) + j]:
                rows[i][j + 1] = rows[i - 1][j + 1]
            else:
                pool = VALS[c]
                cursor[c] = (cursor[c] + 1) % len(pool)
                if pool[cursor[c]] == rows[i - 1][j + 1]:  # 반드시 달라야 한다
                    cursor[c] = (cursor[c] + 1) % len(pool)
                rows[i][j + 1] = pool[cursor[c]]
    return rows


def rate(rows: list[list[str]]) -> float:
    same = sum(rows[i][j] == rows[i - 1][j]
               for i in range(1, NROW) for j in range(1, len(COLS)))
    return same / ELIGIBLE


def records(rows: list[list[str]]) -> str:
    out = []
    for r in rows:
        out.append(f"**{r[0]}** — {r[1]} 리전, {r[2]} 환경, {r[3]} 역할, {r[4]}, "
                   f"{r[5]} 등급, vCPU {r[6]}개, 상태 {r[7]}.")
    return "\n\n".join(out)


T3_FMT_T = """출력 형식: 결과를 TSV로 `<RUNDIR>/out.txt` 에 저장하세요. 첫 줄은 헤더이고 그 아래
자산 1건당 1줄씩 총 12줄입니다. 열 구분자는 탭 문자 1개이며 열 순서는 다음과 같습니다.
asset_id, region, env, role, os, tier, cpu, status"""

T3_FMT_F = """출력 형식: 결과를 TSV로 `<RUNDIR>/out.txt` 에 저장하세요. 첫 줄은 헤더이고 그 아래
자산 1건당 1줄씩 총 12줄입니다. 열 구분자는 탭 문자 1개이며 열 순서는 다음과 같습니다.
asset_id, region, env, role, os, tier, cpu, status
바로 윗줄과 값이 같은 칸은 값 대신 `^` 한 글자만 씁니다. 첫 데이터 줄에는 `^` 를 쓰지
않습니다. 값이 다른 칸에는 값을 그대로 씁니다."""

T3_FMT_C = """출력 형식: 결과를 TSV로 `<RUNDIR>/out.txt` 에 저장하세요. 첫 줄은 헤더이고 그 아래
자산 1건당 1줄씩 총 12줄입니다. 열 구분자는 탭 문자 1개입니다.
열 이름과 값은 아래 코드표대로 줄여서 씁니다.

열 이름: asset_id=a, region=r, env=e, role=o, os=s, tier=t, cpu=c, status=u
열 순서: a, r, e, o, s, t, c, u
a: `AS-` 접두사를 떼고 숫자만 (AS-2001 -> 2001)
r: apne1=1, apne2=2, usea1=3, euwe1=4
e: prod=1, stage=2, dev=3
o: web=1, api=2, batch=3, cache=4
s: ubuntu22=1, ubuntu24=2, debian12=3, alpine3=4
t: small=1, medium=2, large=3
u: active=1, drained=2, halted=3
c: 숫자를 그대로 씁니다"""

T3_FOOT = "파일에는 결과 데이터만 넣고 설명이나 주석은 넣지 않습니다."


def t3(rows: list[list[str]], fmt: str) -> str:
    return "\n".join([
        HEAD, "",
        "아래는 서버 자산 대장 12건입니다. 각 자산에서 asset_id, region, env, role, os, "
        "tier, cpu, status 8개 항목을 표로 정리하세요.", "",
        "자산 기록:", "",
        records(rows), "",
        fmt, "",
        T3_FOOT, "",
        TAIL, "",
        "설명이 필요하면 한국어로 씁니다.", "",
    ])


# ─────────────────────────────────────────────────────────── 검증 + 쓰기

def sha(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fail: list[str] = []

    # 처치 줄 길이가 같아야 '지시 개수' 효과를 '지시 길이' 효과와 분리할 수 있다
    lens = [len(L1), len(L2), len(L3)]
    if len(set(lens)) != 1:
        fail.append(f"T1 처치 줄 길이 불일치: {lens}")

    lo = build_table(15)   # 목표 r = 15/77 = 0.195
    hi = build_table(62)   # 목표 r = 62/77 = 0.805
    for name, rows, want in (("lo", lo, 15), ("hi", hi, 62)):
        got = round(rate(rows) * ELIGIBLE)
        if got != want:
            fail.append(f"T3-{name} 반복 칸 수 {got} != {want}")

    files = {
        "r4-K0.txt": t1([]),
        "r4-K1.txt": t1([L1]),
        "r4-K2.txt": t1([L1, L2]),
        "r4-K3.txt": t1([L1, L2, L3]),
        "r4-B2.txt": t2(None),
        "r4-X2.txt": t2(T2_X),
        "r4-SLT.txt": t3(lo, T3_FMT_T),
        "r4-SLF.txt": t3(lo, T3_FMT_F),
        "r4-SHT.txt": t3(hi, T3_FMT_T),
        "r4-SHF.txt": t3(hi, T3_FMT_F),
        "r4-CB.txt": t3(lo, T3_FMT_C),
    }

    # K0 은 라운드 3 B 와, K1 은 라운드 3 P 와 바이트 동일해야 한다.
    # 다르면 라운드 3 데이터를 K0/K1 으로 재사용할 수 없다.
    for new, old in (("r4-K0.txt", "r3-B.txt"), ("r4-K1.txt", "r3-P.txt")):
        prev = (PROMPTS / old).read_text(encoding="utf-8")
        if files[new] != prev:
            fail.append(f"{new} != {old} (sha {sha(files[new])} vs {sha(prev)}) "
                        "-> 라운드 3 재사용 불가")

    # 과제별 공통부 동일성: 처치 줄만 빼면 같아야 한다
    def strip(text: str, rungs: list[str]) -> str:
        keep = [ln for ln in text.split("\n") if ln not in rungs]
        return "\n".join(ln for ln in keep if ln.strip() != "")

    base = strip(files["r4-K0.txt"], [])
    for k, rungs in (("r4-K1.txt", [L1]), ("r4-K2.txt", [L1, L2]), ("r4-K3.txt", [L1, L2, L3])):
        if strip(files[k], rungs) != base:
            fail.append(f"{k} 공통부가 K0 과 다르다")
    if strip(files["r4-X2.txt"], [T2_X]) != strip(files["r4-B2.txt"], []):
        fail.append("r4-X2 공통부가 B2 와 다르다")

    if fail:
        print("생성 중단:")
        for f in fail:
            print("  -", f)
        return 1

    PROMPTS.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (PROMPTS / name).write_text(text, encoding="utf-8", newline="\n")
        print(f"{name:14} {len(text):5}자  sha1 {sha(text)}")

    for name, rows in (("lo", lo), ("hi", hi)):
        p = DATA / f"r4-assets-{name}.tsv"
        p.write_text("\n".join("\t".join(r) for r in [COLS] + rows) + "\n",
                     encoding="utf-8", newline="\n")
        print(f"{p.name:20} r={rate(rows):.3f}")

    print(f"\nT1 처치 줄 {lens[0]}자 x 3 (동일)")
    print(f"T3 코드북 선언 증가분 dP = {len(T3_FMT_C) - len(T3_FMT_T)}자")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
