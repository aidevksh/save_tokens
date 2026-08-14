#!/usr/bin/env python3
"""라운드 6 재료·프롬프트 생성기.

    python experiments/scripts/gen_r6.py

과제 2개:
  T9   기능 추가 코딩 루프 (A5-H3 / A5-H4 / A5-H5 요인 분해 + A5-H7 묶음)
  T10  산문 수치 상한 (A1-H3)

생성 후 스스로 검증한다. 실패하면 파일을 쓰지 않는다.
  - T9 각 조건이 처치 줄을 뺀 공통부에서 바이트 동일
  - T10 C0 이 라운드 4 K0 과, CK 가 라운드 4 K1 과 바이트 동일 (재사용 전제)
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROMPTS = REPO / "experiments/prompts"

HEAD = ("작업 디렉터리는 <RUNDIR> 입니다. 이 디렉터리는 다른 팀이 관리하는 독립 프로젝트이고, "
        "아래 지시가 이 작업의 유일한 명세입니다. 다른 위치의 파일이나 규약은 참조하지 마세요.")
TAIL = "도구 호출이 거부되면 다른 수단으로 우회하지 말고, 거부되었다는 사실을 보고하고 중단합니다."

# ═══════════════════════════════════════════════ T9 기능 추가 (축 5)

T9_BODY = """`<RUNDIR>/todo.js` 는 할 일 목록을 메모리에 담는 모듈이고
`<RUNDIR>/todo.test.js` 는 그 모듈의 단위 테스트입니다. 지금 테스트 9개 중 5개가 실패합니다.

    cd <RUNDIR> && node --test

**할 일**: `todo.js` 에 기능을 추가해 테스트 9개가 모두 통과하게 만드세요.
테스트 파일은 명세이므로 수정하지 마세요."""

# 세 처치는 각각 다른 팽창원을 겨냥한다. 극성은 셋 다 긍정형으로 맞춘다
# (라운드 3 A1-H1 — 부정형은 같은 명제라도 절감이 작다).
S3 = "마지막 보고는 무엇을 바꿨는지 세 줄 이내로 씁니다."          # 대화 보고문
S4 = "요청한 것만 만듭니다. 파일·함수·테스트는 통과에 필요한 만큼만 더합니다."  # 범위
S5 = "설명은 코드 이름으로 합니다. 주석 없이 읽히게 씁니다."        # 주석 밀도


def t9(rules: list[str]) -> str:
    parts = [HEAD, "", T9_BODY, ""]
    if rules:
        parts += ["\n".join(rules), ""]
    parts += [TAIL, "", "설명은 한국어로 씁니다.", ""]
    return "\n".join(parts)


# ═══════════════════════════════════════════════ T10 수치 상한 (축 1)

T10_BODY = """우리 서비스의 요청 제한(rate limit) 동작 명세는 다음과 같습니다.

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

CK = "핵심만 간결히 쓰세요. 본문부터 시작해 본문으로 끝내세요. 각 내용은 한 번만 쓰세요."
# 상한을 두 수준으로 잡는다. 한 수준만 잡으면 그 값이 결론을 결정해 순환 논증이 된다.
# 800자는 라운드 4 K1 실측 평균(744자)보다 느슨하고, 300자는 그보다 빡빡하다.
CN800 = "문서는 800자 이내로 쓰세요."
CN300 = "문서는 300자 이내로 쓰세요."


def t10(rule: str | None) -> str:
    parts = [HEAD, "", T10_BODY, ""]
    if rule:
        parts += [rule, ""]
    parts += [TAIL, "", "문서는 한국어로 작성합니다.", ""]
    return "\n".join(parts)


# ═══════════════════════════════════════════════ 검증 + 쓰기

def sha(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fail: list[str] = []

    files = {
        "r6-B.txt": t9([]),
        "r6-S3.txt": t9([S3]),
        "r6-S4.txt": t9([S4]),
        "r6-S5.txt": t9([S5]),
        "r6-ALL.txt": t9([S3, S4, S5]),
        "r6-C0.txt": t10(None),
        "r6-CK.txt": t10(CK),
        "r6-CN800.txt": t10(CN800),
        "r6-CN300.txt": t10(CN300),
    }

    def strip(text: str, rules: list[str]) -> str:
        keep = [ln for ln in text.split("\n") if ln not in rules]
        return "\n".join(ln for ln in keep if ln.strip() != "")

    base9 = strip(files["r6-B.txt"], [])
    for k, rules in (("r6-S3.txt", [S3]), ("r6-S4.txt", [S4]), ("r6-S5.txt", [S5]),
                     ("r6-ALL.txt", [S3, S4, S5])):
        if strip(files[k], rules) != base9:
            fail.append(f"{k} 공통부가 B 와 다르다")
    base10 = strip(files["r6-C0.txt"], [])
    for k, rules in (("r6-CK.txt", [CK]), ("r6-CN800.txt", [CN800]), ("r6-CN300.txt", [CN300])):
        if strip(files[k], rules) != base10:
            fail.append(f"{k} 공통부가 C0 과 다르다")

    for a, b in (("r6-C0.txt", "r4-K0.txt"), ("r6-CK.txt", "r4-K1.txt")):
        prev = (PROMPTS / b).read_text(encoding="utf-8")
        if files[a] != prev:
            fail.append(f"{a} != {b} (sha {sha(files[a])} vs {sha(prev)}) -> 재사용 불가")

    if fail:
        print("생성 중단:")
        for f in fail:
            print("  -", f)
        return 1

    for name, text in files.items():
        (PROMPTS / name).write_text(text, encoding="utf-8", newline="\n")
        print(f"{name:14} {len(text):5}자  sha1 {sha(text)}")
    print(f"\nT9 처치 줄 길이: S3 {len(S3)}자 / S4 {len(S4)}자 / S5 {len(S5)}자")
    print(f"T10 처치 줄 길이: CK {len(CK)}자 / CN800 {len(CN800)}자 / CN300 {len(CN300)}자")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
