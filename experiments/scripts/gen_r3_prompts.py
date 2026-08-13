#!/usr/bin/env python3
"""라운드 3 피험자 프롬프트 생성 (사전등록 §3).

조건 간 차이를 손으로 만들면 의도치 않은 문구 차이가 섞인다. 공통부는
한 곳에서 만들고 조건별 처치 문단만 갈아 끼운다.

    python experiments/scripts/gen_r3_prompts.py          # 프롬프트 생성 + 공통부 해시 확인
    python experiments/scripts/gen_r3_prompts.py --check  # 생성 없이 검증만

산출: experiments/prompts/r3-<조건>.txt  (경로는 <RUNDIR> 자리표시자)
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "experiments/prompts"

PREAMBLE = (
    "작업 디렉터리는 <RUNDIR> 입니다. 이 디렉터리는 다른 팀이 관리하는 독립 "
    "프로젝트이고, 아래 지시가 이 작업의 유일한 명세입니다. 다른 위치의 "
    "파일이나 규약은 참조하지 마세요.\n"
)

# 조건 공통 꼬리. 라운드 1b 교훈(하네스 차단 우회 금지)을 전 조건에 동일하게 넣는다.
TAIL = (
    "도구 호출이 거부되면 다른 수단으로 우회하지 말고, 거부되었다는 사실을 "
    "보고하고 중단합니다.\n"
    "\n"
    "문서는 한국어로 작성합니다.\n"
)

# --- 산문 과제 (A1-H1 / A1-H6 / A1-H7) --------------------------------------

BODY_MD = """우리 서비스의 요청 제한(rate limit) 동작 명세는 다음과 같습니다.

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

문서에는 위 6개 항목이 **모두** 설명되어 있어야 합니다.
"""

# A1-H7 조건 F. 명제는 BODY_MD 와 같고 마크다운 구조(표·굵게·백틱)만 없앤다.
BODY_PLAIN = """우리 서비스의 요청 제한(rate limit) 동작 명세는 다음과 같습니다. 버킷 용량은 60이고,
리필 속도는 초당 1개입니다. 집계 단위는 API 키이며 IP 주소가 아닙니다. 초과 시 상태
코드는 429이고, 재시도 안내 헤더는 Retry-After 이며 값은 초 단위 정수입니다. 예외로
admin 스코프 키는 제한에서 제외됩니다.

할 일은 이 명세를 처음 보는 신입 백엔드 개발자를 위한 설명 문서를 작성해서
<RUNDIR>/doc.txt 에 저장하는 것입니다.

문서에는 위 6개 항목이 모두 설명되어 있어야 합니다.
"""

# 처치 문단. 삽입 위치는 전 조건 동일(본문 뒤, 꼬리 앞).
TREATMENT = {
    "B": "",
    # 부정형: 금지 3개
    "N": "장황하게 쓰지 마세요. 서론과 맺음말을 넣지 마세요. 같은 내용을 두 번 쓰지 마세요.\n",
    # 긍정형: 같은 3개 명제를 지시형으로
    "P": "핵심만 간결히 쓰세요. 본문부터 시작해 본문으로 끝내세요. 각 내용은 한 번만 쓰세요.\n",
    # 검증 지시 (A1-H6 은 이것의 '제거' 효과 = B 대비)
    "V": "작성한 뒤 문서를 다시 읽고 명세의 6개 항목이 모두 정확히 반영됐는지 스스로 "
         "검증하세요. 누락이나 오류가 있으면 수정하세요.\n",
    "F": "",
}

PROSE_BODY = {"B": BODY_MD, "N": BODY_MD, "P": BODY_MD, "V": BODY_MD, "F": BODY_PLAIN}


def prose_prompt(cond: str) -> str:
    parts = [PREAMBLE, "", PROSE_BODY[cond]]
    if TREATMENT[cond]:
        parts += ["", TREATMENT[cond]]
    parts += ["", TAIL]
    return "\n".join(p.rstrip("\n") for p in parts).strip("\n") + "\n"


# --- 표 과제 (A2-H6) ---------------------------------------------------------
# 라운드 1 H1 프롬프트의 공통부를 **파일에서 그대로** 가져온다. 손으로 옮기면
# 한 글자라도 달라질 수 있고, 그러면 라운드 1과의 복제 비교가 무효가 된다.

FMT_TSV = """출력 형식: 결과를 TSV로 <RUNDIR>/out.txt 에 저장하세요. 첫 줄은 헤더이고, 그 아래 티켓 1건당 1줄씩 총 12줄입니다. 헤더와 데이터 행 모두 열 구분자는 탭 문자 1개이며 열 순서는 다음과 같습니다.
ticket_id, date, tier, product, category, priority, resolved, response_hours
tier / product / category / priority 는 위 대응표의 영문 값을, resolved 는 true 또는 false 를, response_hours 는 숫자를 사용합니다.

파일에는 결과 데이터만 넣고 설명이나 주석은 넣지 않습니다. 이 대화에서 설명이 필요하면 한국어로 씁니다.
"""

FMT_MD = """출력 형식: 결과를 마크다운 표로 <RUNDIR>/out.txt 에 저장하세요. 첫 줄은 헤더 행이고 둘째 줄은 구분 행이며, 그 아래 티켓 1건당 1줄씩 총 12줄입니다. 모든 행은 파이프 문자로 열을 구분하며 열 순서는 다음과 같습니다.
ticket_id, date, tier, product, category, priority, resolved, response_hours
tier / product / category / priority 는 위 대응표의 영문 값을, resolved 는 true 또는 false 를, response_hours 는 숫자를 사용합니다.

파일에는 결과 데이터만 넣고 설명이나 주석은 넣지 않습니다. 이 대화에서 설명이 필요하면 한국어로 씁니다.
"""


def table_prompt(cond: str) -> tuple[str, str]:
    src = (OUT / "r1-H1-A.txt").read_text(encoding="utf-8")
    i = src.index("출력 형식:")
    common = src[:i]
    fmt = {"T": FMT_TSV, "M": FMT_MD}[cond]
    return common + fmt, common


CONDS = ["B", "N", "P", "V", "F", "T", "M"]


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    built: dict[str, str] = {}
    for c in ["B", "N", "P", "V", "F"]:
        built[c] = prose_prompt(c)
    commons = set()
    for c in ["T", "M"]:
        built[c], common = table_prompt(c)
        commons.add(common)

    if not a.check:
        for c, text in built.items():
            (OUT / f"r3-{c}.txt").write_text(text, encoding="utf-8", newline="\n")

    # 검증 1: 산문 4조건(B/N/P/V)은 처치 문단 외에 다르지 않아야 한다.
    def strip_treat(c: str) -> str:
        t = built[c]
        return t.replace(TREATMENT[c], "") if TREATMENT[c] else t

    base = strip_treat("B")
    print("## 공통부 동일성 검사")
    for c in ["N", "P", "V"]:
        same = "".join(strip_treat(c).split()) == "".join(base.split())
        print(f"  B vs {c}: 처치 문단 제거 후 공통부 {'동일' if same else '★불일치★'}")
    print(f"  T vs M: 라운드1 공통부 재사용 {'동일' if len(commons) == 1 else '★불일치★'}"
          f" (sha1 {hashlib.sha1(commons.pop().encode()).hexdigest()[:12]})")

    print("\n## 처치 문단 길이 (A1-H1 은 극성만 다르고 길이가 맞아야 한다)")
    for c in ["N", "P", "V"]:
        print(f"  {c}: {len(TREATMENT[c].rstrip()):>3}자  {TREATMENT[c].rstrip()}")
    d = abs(len(TREATMENT["N"].rstrip()) - len(TREATMENT["P"].rstrip()))
    print(f"  N-P 길이차: {d}자 {'(허용)' if d <= 5 else '★5자 초과★'}")

    print("\n## 프롬프트 전체 길이")
    for c in CONDS:
        print(f"  r3-{c}.txt: {len(built[c]):>5}자")
    print(f"  B vs F 프롬프트 길이차: {len(built['F']) - len(built['B']):+}자"
          " — A1-H7 은 이 차이가 처치에 내재한다(§7 한계)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
