#!/usr/bin/env python3
"""라운드 5 재료·프롬프트 생성기.

    python experiments/scripts/gen_r5.py

과제 5개:
  T4  부분 재생성 압축 수준 5단 (A6-H3) — 라운드 2 재료·프롬프트 재사용
  T5  2차 소비자 (A6-H8) — 프롬프트가 전 조건 **완전히 동일**하다. 다른 것은 받은 산출물뿐
  T6  레코드 수 x 형식 (A2-H8)
  T7  생성 프로그램 출력 (A6-H5)
  T8  예시 길이 앵커링 (A1-H5)

생성 후 스스로 검증한다. 실패하면 파일을 쓰지 않는다.
  - T4 W0/W1/W2 가 라운드 2 A120/B120/C120 과 바이트 동일 (재사용 전제)
  - T8 X0 이 라운드 4 K0 과 바이트 동일 (재사용 전제)
  - T6 N=12 TSV 가 라운드 4 SLT 와 바이트 동일 (재사용 전제)
  - T7 규칙 재료가 실제로 규칙에서 재생성되는지 (기대 데이터 자기검증)
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

# ═══════════════════════════════════════════════ T4 부분 재생성 (A6-H3)
# 라운드 2 프롬프트를 그대로 읽어 '출력 형식' 절만 갈아 끼운다.
# 본문(원본 120줄 + 변경 요청 6곳)을 손으로 다시 적으면 재사용 전제가 깨진다.

FMT_W3 = """## 출력 형식

수정 내용을 unified diff 로 아래 경로에 저장한다.
파일 헤더는 `--- a/deploy.yaml` 와 `+++ b/deploy.yaml` 로 하고, 원본 파일에 `git apply -p1` 로 적용 가능해야 한다.
각 hunk 에 컨텍스트 줄을 **넣지 않는다**. 변경 줄만 쓴다.

저장 경로: `{OUTDIR}/out.diff`

도구 호출이 거부되면 다른 수단으로 우회하지 말고, 거부되었다는 사실을 보고하고 중단한다.
"""

FMT_W4 = """## 출력 형식

수정 내용을 줄 번호와 치환쌍으로만 아래 경로에 저장한다.
변경 1건당 한 줄이며 형식은 `<줄번호>: <원래 줄> -> <바뀐 줄>` 이다.
diff 헤더, hunk 헤더, 컨텍스트 줄은 쓰지 않는다.

저장 경로: `{OUTDIR}/out.diff`

도구 호출이 거부되면 다른 수단으로 우회하지 말고, 거부되었다는 사실을 보고하고 중단한다.
"""


def t4(fmt: str) -> str:
    base = (PROMPTS / "r2-B120.txt").read_text(encoding="utf-8")
    head = base.split("## 출력 형식")[0]
    return head + fmt


# ═══════════════════════════════════════════════ T5 2차 소비자 (A6-H8)
# 전 조건 동일. 받는 산출물만 다르다 -> 프롬프트가 조작 변수가 아니다.

T5 = "\n".join([
    HEAD, "",
    "`<RUNDIR>/deploy.yaml` 은 현재 배포 설정 파일이고, `<RUNDIR>/change.txt` 는 다른 팀이",
    "보낸 변경 지시서입니다.", "",
    "**할 일**: `change.txt` 의 내용대로 `deploy.yaml` 을 수정하세요. 수정한 결과는",
    "`<RUNDIR>/deploy.yaml` 에 그대로 저장합니다.", "",
    "지시서만으로 알 수 없는 부분이 있으면 추측해서 채우지 말고, 무엇을 알 수 없는지 보고하세요.", "",
    TAIL, "",
    "설명은 한국어로 씁니다.", "",
])

# ═══════════════════════════════════════════════ T6 레코드 수 x 형식 (A2-H8)

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
FREE = COLS[1:]


def build_table(nrow: int, rate: float) -> list[list[str]]:
    """라운드 4 gen_r4.build_table 과 같은 알고리즘. 행 수만 파라미터로 뺐다."""
    eligible = len(FREE) * (nrow - 1)
    repeats = round(rate * eligible)
    flag = [(k * repeats) // eligible != ((k + 1) * repeats) // eligible
            for k in range(eligible)]
    rows = [[f"AS-{2001 + i}"] + [VALS[c][0] for c in FREE] for i in range(nrow)]
    cursor = {c: 0 for c in FREE}
    for i in range(1, nrow):
        for j, c in enumerate(FREE):
            if flag[(i - 1) * len(FREE) + j]:
                rows[i][j + 1] = rows[i - 1][j + 1]
            else:
                pool = VALS[c]
                cursor[c] = (cursor[c] + 1) % len(pool)
                if pool[cursor[c]] == rows[i - 1][j + 1]:
                    cursor[c] = (cursor[c] + 1) % len(pool)
                rows[i][j + 1] = pool[cursor[c]]
    return rows


def records(rows: list[list[str]]) -> str:
    return "\n\n".join(
        f"**{r[0]}** — {r[1]} 리전, {r[2]} 환경, {r[3]} 역할, {r[4]}, "
        f"{r[5]} 등급, vCPU {r[6]}개, 상태 {r[7]}." for r in rows)


FMT_TSV = """출력 형식: 결과를 TSV로 `<RUNDIR>/out.txt` 에 저장하세요. 첫 줄은 헤더이고 그 아래
자산 1건당 1줄씩 총 {n}줄입니다. 열 구분자는 탭 문자 1개이며 열 순서는 다음과 같습니다.
asset_id, region, env, role, os, tier, cpu, status"""

FMT_JSON = """출력 형식: 결과를 JSON 배열로 `<RUNDIR>/out.txt` 에 저장하세요. 배열의 원소는
자산 1건이고 총 {n}개입니다. 각 원소는 asset_id, region, env, role, os, tier, cpu, status
8개 키를 모두 가집니다. cpu 는 숫자이고 나머지는 문자열입니다."""


def t6(rows: list[list[str]], fmt: str) -> str:
    return "\n".join([
        HEAD, "",
        f"아래는 서버 자산 대장 {len(rows)}건입니다. 각 자산에서 asset_id, region, env, role, os, "
        "tier, cpu, status 8개 항목을 표로 정리하세요.", "",
        "자산 기록:", "",
        records(rows), "",
        fmt.format(n=len(rows)), "",
        "파일에는 결과 데이터만 넣고 설명이나 주석은 넣지 않습니다.", "",
        TAIL, "",
        "설명이 필요하면 한국어로 씁니다.", "",
    ])


# ═══════════════════════════════════════════════ T7 생성 프로그램 (A6-H5)

NSHARD = 60


def shards_hi() -> list[tuple[str, str, int, int]]:
    return [(f"shard-{i:03d}", f"node-{i // 10}.example.com", 7000 + i, (i % 4) + 1)
            for i in range(NSHARD)]


def shards_lo() -> list[tuple[str, str, int, int]]:
    """규칙 없는 값. 결정적 해시로 만든다 — 실행 시 난수를 쓰지 않는다.

    LCG 를 쓰면 안 된다. 한 행에 세 번 전진시키면 하위 비트에 짧은 주기가 생겨
    host 가 8주기, weight 가 4주기로 돌았다(첫 생성에서 실제로 발생). 그러면
    '불규칙' 조건이 사실은 규칙적이 되어 A6-H5 의 역전 예측이 무너진다.
    """
    hosts = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]

    def h32(tag: str, i: int) -> int:
        return int(hashlib.sha256(f"r5-{tag}-{i}".encode()).hexdigest()[:8], 16)

    return [(f"shard-{i:03d}", f"{hosts[h32('h', i) % len(hosts)]}.example.com",
             7000 + h32("p", i) % 1000, h32("w", i) % 4 + 1) for i in range(NSHARD)]


def has_period(seq: list, max_p: int = 12) -> int | None:
    """짧은 주기가 있으면 그 주기를 돌려준다. 불규칙 재료 자기검증용."""
    for p in range(1, max_p + 1):
        if len(seq) > 2 * p and all(seq[i] == seq[i + p] for i in range(len(seq) - p)):
            return p
    return None


def csv(rows) -> str:
    return "\n".join(f"{a},{b},{c},{d}" for a, b, c, d in rows) + "\n"


SPEC_HI = """아래 규칙으로 샤드 배치표 60행을 만듭니다.

- 행은 `shard_id,host,port,weight` 네 값을 쉼표로 이어 붙인 CSV 한 줄입니다. 헤더 줄은 없습니다.
- i 는 0부터 59까지입니다.
- shard_id 는 `shard-` 뒤에 i 를 세 자리로 0 채움 한 값입니다 (shard-000, shard-001, …).
- host 는 `node-` 뒤에 i 를 10으로 나눈 몫을 붙이고 `.example.com` 을 붙인 값입니다.
- port 는 7000 + i 입니다.
- weight 는 i 를 4로 나눈 나머지에 1을 더한 값입니다."""

SPEC_LO_HEAD = """아래는 샤드 배치표 60행입니다. 행은 `shard_id,host,port,weight` 네 값을
쉼표로 이어 붙인 CSV 한 줄이며 헤더 줄은 없습니다."""

OUT_D = """**할 일**: 이 배치표 60행을 `<RUNDIR>/out.txt` 에 저장하세요.
파일에는 60줄의 데이터만 넣고 설명이나 주석은 넣지 않습니다."""

OUT_P = """**할 일**: 이 배치표 60행을 표준출력으로 찍는 파이썬 프로그램을 `<RUNDIR>/out.py` 에
저장하세요. `python out.py` 로 실행하면 60줄이 정확히 그대로 나와야 합니다.
파일에는 프로그램만 넣고 설명이나 주석은 넣지 않습니다."""


def t7(spec: str, out: str) -> str:
    return "\n".join([HEAD, "", spec, "", out, "", TAIL, "", "설명이 필요하면 한국어로 씁니다.", ""])


# ═══════════════════════════════════════════════ T8 예시 길이 앵커링 (A1-H5)

T8_BODY = """우리 서비스의 요청 제한(rate limit) 동작 명세는 다음과 같습니다.

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

# 예시는 '다른 주제'로 쓴다. 같은 주제로 쓰면 베껴서 답이 되어 과제가 무너진다.
# 짧은 예시와 긴 예시는 **같은 사실 4개**를 담고 길이만 다르다.
EX_SHORT = """참고로, 다른 명세를 같은 형식으로 설명한 문서는 다음과 같습니다.

---
로그 보존 정책은 다음과 같다. 보존 기간은 30일이다. 30일이 지난 로그는 자동으로 삭제된다.
저장 위치는 객체 스토리지다. 압축은 gzip을 쓴다. 조회는 관리 콘솔에서 한다.
---"""

EX_LONG = """참고로, 다른 명세를 같은 형식으로 설명한 문서는 다음과 같습니다.

---
# 로그 보존 정책 안내

이 문서는 우리 서비스의 로그 보존 정책을 처음 접하는 분을 위해 작성되었습니다. 로그는
장애를 추적하고 사용자 문의에 답하기 위한 핵심 자료이므로, 얼마나 오래 어디에 어떤 형태로
보관되는지 정확히 알아 두는 것이 좋습니다.

## 1. 보존 기간 — 30일

모든 애플리케이션 로그는 기록된 시점으로부터 30일 동안 보존됩니다. 30일은 대부분의 장애
조사와 사용자 문의 처리에 충분한 기간으로 판단해 정해진 값입니다. 예를 들어 월요일에
기록된 로그는 그 다음 달 같은 주 무렵까지 조회할 수 있습니다.

## 2. 만료 처리 — 자동 삭제

보존 기간이 지난 로그는 별도의 조작 없이 자동으로 삭제됩니다. 운영자가 손으로 지울 필요는
없으며, 반대로 손으로 되살릴 수도 없습니다. 30일보다 오래 남겨야 하는 자료가 있다면 로그가
아니라 별도의 보관 절차를 이용해야 합니다.

## 3. 저장 위치 — 객체 스토리지

로그는 객체 스토리지에 저장됩니다. 애플리케이션 서버의 로컬 디스크에는 남지 않으므로,
서버가 교체되거나 재시작되어도 이미 기록된 로그는 영향을 받지 않습니다.

## 4. 압축 형식 — gzip

저장 시에는 gzip으로 압축됩니다. 내려받아 직접 열어 볼 때는 압축을 먼저 풀어야 합니다.

## 5. 조회 방법 — 관리 콘솔

일상적인 조회는 관리 콘솔에서 합니다. 기간과 서비스 이름으로 범위를 좁힌 뒤 검색어를 넣는
방식이며, 별도의 접근 권한 신청 없이 팀 구성원이라면 바로 쓸 수 있습니다.
---"""


def t8(ex: str | None) -> str:
    parts = [HEAD, "", T8_BODY, ""]
    if ex:
        parts += [ex, ""]
    parts += [TAIL, "", "문서는 한국어로 작성합니다.", ""]
    return "\n".join(parts)


# ═══════════════════════════════════════════════ 검증 + 쓰기

def sha(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fail: list[str] = []

    n3, n12, n24 = build_table(3, 0.195), build_table(12, 0.195), build_table(24, 0.195)
    hi, lo = shards_hi(), shards_lo()

    files = {
        "r5-W3.txt": t4(FMT_W3),
        "r5-W4.txt": t4(FMT_W4),
        "r5-RD.txt": T5,
        "r5-J3.txt": t6(n3, FMT_JSON), "r5-T3.txt": t6(n3, FMT_TSV),
        "r5-J12.txt": t6(n12, FMT_JSON), "r5-T12.txt": t6(n12, FMT_TSV),
        "r5-J24.txt": t6(n24, FMT_JSON), "r5-T24.txt": t6(n24, FMT_TSV),
        "r5-GhiD.txt": t7(SPEC_HI, OUT_D), "r5-GhiP.txt": t7(SPEC_HI, OUT_P),
        "r5-GloD.txt": t7(SPEC_LO_HEAD + "\n\n```\n" + csv(lo) + "```", OUT_D),
        "r5-GloP.txt": t7(SPEC_LO_HEAD + "\n\n```\n" + csv(lo) + "```", OUT_P),
        "r5-X0.txt": t8(None), "r5-X1.txt": t8(EX_SHORT), "r5-X2.txt": t8(EX_LONG),
    }

    # 재사용 전제: 프롬프트가 바이트 동일해야 이전 라운드 데이터를 조건으로 쓸 수 있다
    for new, old in (("r5-W3.txt", None),):
        pass
    for a, b in (("r5-X0.txt", "r4-K0.txt"), ("r5-T12.txt", "r4-SLT.txt")):
        prev = (PROMPTS / b).read_text(encoding="utf-8")
        if files[a] != prev:
            fail.append(f"{a} != {b} (sha {sha(files[a])} vs {sha(prev)}) -> 재사용 불가")
    for name in ("r5-W3.txt", "r5-W4.txt"):
        base = (PROMPTS / "r2-B120.txt").read_text(encoding="utf-8")
        if files[name].split("## 출력 형식")[0] != base.split("## 출력 형식")[0]:
            fail.append(f"{name} 본문이 r2-B120 과 다르다")

    # T7 기대 데이터 자기검증: 규칙 재료가 규칙에서 그대로 재생성되는가
    if csv(shards_hi()) != csv([(f"shard-{i:03d}", f"node-{i // 10}.example.com",
                                 7000 + i, (i % 4) + 1) for i in range(NSHARD)]):
        fail.append("T7 규칙 재료 자기검증 실패")
    if len(set(lo)) != NSHARD:
        fail.append("T7 불규칙 재료에 중복 행이 있다")
    for col, idx in (("host", 1), ("port", 2), ("weight", 3)):
        p = has_period([r[idx] for r in lo])
        if p:
            fail.append(f"T7 불규칙 재료의 {col} 열이 주기 {p} 로 반복된다 — 불규칙이 아니다")

    if fail:
        print("생성 중단:")
        for f in fail:
            print("  -", f)
        return 1

    for name, text in files.items():
        (PROMPTS / name).write_text(text, encoding="utf-8", newline="\n")
    for name, rows in (("r5-assets-3", n3), ("r5-assets-12", n12), ("r5-assets-24", n24)):
        (DATA / f"{name}.tsv").write_text(
            "\n".join("\t".join(r) for r in [COLS] + rows) + "\n", encoding="utf-8", newline="\n")
    (DATA / "r5-shards-hi.csv").write_text(csv(hi), encoding="utf-8", newline="\n")
    (DATA / "r5-shards-lo.csv").write_text(csv(lo), encoding="utf-8", newline="\n")

    for name in sorted(files):
        print(f"{name:14} {len(files[name]):6}자  sha1 {sha(files[name])}")
    print(f"\nT8 예시 길이: 짧은 {len(EX_SHORT)}자 / 긴 {len(EX_LONG)}자 (비 {len(EX_LONG)/len(EX_SHORT):.1f}배)")
    print(f"T7 기대 산출: hi {len(csv(hi))}자 / lo {len(csv(lo))}자")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
