#!/usr/bin/env python3
"""라운드 7 재료·프롬프트 생성기.

    python experiments/scripts/gen_r7.py

과제 4개:
  T11  표 스키마 사다리 (A2-H2 키 축약 / A2-H3 enum 코드화 / A2-H5 positional)
  T12  2차 소비자 복원 (T11 산출물을 받아 질문 6개에 답한다) — 정확도 측정
  T13  긍정형 간결성 지시 3명제 요인 분해 (A1-H4 서론·맺음말 억제)
  T14  긴 프롬프트에서의 지시 위치 (A1-H2 말미 리마인더)

생성 후 스스로 검증한다. 실패하면 파일을 쓰지 않는다.
  - T11 각 조건이 출력 형식 문단을 뺀 공통부에서 바이트 동일
  - T11 T 조건이 라운드 4 SLT 와 바이트 동일 (재사용 전제)
  - T13 C0 == 라운드 4 K0, CK == 라운드 4 K1 (재사용 전제)
  - T13 CC/CI/CR 세 처치 줄을 이으면 CK 처치 줄과 바이트 동일 (요인 분해 전제)
  - T14 네 조건이 지시 줄을 뺀 공통부에서 바이트 동일
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

# ═══════════════════════════════════════════════ T11 표 스키마 사다리 (축 2)

ASSETS = [
    ("AS-2001", "apne1", "prod", "web", "ubuntu22", "small", "2", "active"),
    ("AS-2002", "apne2", "stage", "api", "ubuntu24", "medium", "2", "drained"),
    ("AS-2003", "usea1", "dev", "batch", "ubuntu24", "large", "4", "halted"),
    ("AS-2004", "euwe1", "dev", "cache", "debian12", "small", "8", "halted"),
    ("AS-2005", "apne1", "prod", "web", "alpine3", "small", "16", "active"),
    ("AS-2006", "apne2", "stage", "web", "ubuntu22", "medium", "2", "drained"),
    ("AS-2007", "apne2", "dev", "api", "ubuntu24", "large", "4", "drained"),
    ("AS-2008", "usea1", "prod", "batch", "debian12", "large", "8", "halted"),
    ("AS-2009", "euwe1", "stage", "batch", "alpine3", "small", "16", "active"),
    ("AS-2010", "euwe1", "dev", "cache", "ubuntu22", "medium", "16", "drained"),
    ("AS-2011", "apne1", "prod", "web", "ubuntu22", "large", "2", "halted"),
    ("AS-2012", "apne2", "prod", "api", "ubuntu24", "small", "4", "halted"),
]

T11_INTRO = ("아래는 서버 자산 대장 12건입니다. 각 자산에서 asset_id, region, env, role, "
             "os, tier, cpu, status 8개 항목을 표로 정리하세요.\n\n자산 기록:")

COLS = "asset_id, region, env, role, os, tier, cpu, status"

# 조건 공통 앞머리 — 여기까지는 네 조건이 바이트 동일하다.
FMT_HEAD = ("출력 형식: 결과를 TSV로 `<RUNDIR>/out.txt` 에 저장하세요. 첫 줄은 헤더이고 그 아래\n"
            "자산 1건당 1줄씩 총 12줄입니다. 열 구분자는 탭 문자 1개이며 열 순서는 다음과 같습니다.\n"
            + COLS)

# 값 코드표. E 와 P 가 같은 문자열을 쓴다 — 두 조건의 차이는 헤더 유무 하나뿐이다.
VALCODE = """값은 아래 코드표대로 정수로 바꿔 씁니다. asset_id 와 cpu 는 원문 그대로 씁니다.

region: apne1=1, apne2=2, usea1=3, euwe1=4
env: prod=1, stage=2, dev=3
role: web=1, api=2, batch=3, cache=4
os: ubuntu22=1, ubuntu24=2, debian12=3, alpine3=4
tier: small=1, medium=2, large=3
status: active=1, drained=2, halted=3"""

FMT = {
    # T: 헤더 TSV, 열 이름 전체, 값 원문 (= 라운드 4 SLT, 재사용 기준선)
    "T": FMT_HEAD,
    # K: 키 축약. 매핑을 주지 않는다 — 이것이 A2-H2 의 처치다.
    "K": FMT_HEAD + "\n헤더의 열 이름은 각각 1글자로 줄여서 씁니다. 값은 원문 그대로 씁니다.",
    # E: 값만 코드화. 열 이름은 그대로 둔다.
    "E": FMT_HEAD + "\n열 이름은 그대로 씁니다. " + VALCODE,
    # P: E 에서 헤더 줄만 뺀다.
    "P": ("출력 형식: 결과를 TSV로 `<RUNDIR>/out.txt` 에 저장하세요. 헤더 줄 없이\n"
          "자산 1건당 1줄씩 총 12줄만 씁니다. 열 구분자는 탭 문자 1개이며 열 순서는 다음과 같습니다.\n"
          + COLS + "\n" + VALCODE),
}


def t11(cond: str) -> str:
    recs = "\n\n".join(
        f"**{a[0]}** — {a[1]} 리전, {a[2]} 환경, {a[3]} 역할, {a[4]}, {a[5]} 등급, "
        f"vCPU {a[6]}개, 상태 {a[7]}." for a in ASSETS)
    parts = [HEAD, "", T11_INTRO, "", recs, "", FMT[cond], "",
             "파일에는 결과 데이터만 넣고 설명이나 주석은 넣지 않습니다.", "",
             TAIL, "", "설명이 필요하면 한국어로 씁니다.", ""]
    return "\n".join(parts)


# ═══════════════════════════════════════════════ T12 2차 소비자 (축 2 정확도)

# 질문 6개는 전 조건 동일하다. 답은 정답 키에서 기계로 채점한다.
QUESTIONS = """1. AS-2007 의 tier 는 무엇입니까?
2. AS-2010 의 os 는 무엇입니까?
3. status 가 halted 인 자산은 몇 건입니까?
4. region 이 apne1 인 자산의 asset_id 를 모두 쓰세요.
5. cpu 가 16 인 자산은 몇 건입니까?
6. env 가 stage 이면서 role 이 batch 인 자산의 asset_id 를 모두 쓰세요."""

# 조건별로 소비자에게 주는 프로토콜 설명.
# T·K 는 빈 문자열이다 — K 에는 줄 수 있는 규약 자체가 없다(생산자가 지어낸 약자다).
# 이 비대칭이 A2-H2 의 처치이고, 비대칭 자체를 사전등록한다.
PROTO = {
    "UT": "",
    "UK": "",
    "UE": "표의 값은 아래 코드표로 정수화되어 있습니다.\n\n" + VALCODE.split("\n\n", 1)[1],
    "UP": ("표에는 헤더 줄이 없습니다. 열 순서는 다음과 같습니다.\n" + COLS
           + "\n\n표의 값은 아래 코드표로 정수화되어 있습니다.\n\n" + VALCODE.split("\n\n", 1)[1]),
}


def t12(cond: str, payload: str) -> str:
    parts = [HEAD, "",
             "아래는 서버 자산 대장을 정리한 표입니다.", "",
             "```", payload.rstrip("\n"), "```", ""]
    if PROTO[cond]:
        parts += [PROTO[cond], ""]
    parts += ["**할 일**: 이 표를 읽고 아래 질문 6개에 답해서 `<RUNDIR>/ans.txt` 에 저장하세요.",
              "", QUESTIONS, "",
              "파일에는 `1. 답` 처럼 번호와 답만 한 줄씩 6줄 쓰고 다른 설명은 넣지 않습니다.", "",
              TAIL, "", "설명이 필요하면 한국어로 씁니다.", ""]
    return "\n".join(parts)


# ═══════════════════════════════════════════════ T13 지시 요인 분해 (축 1)

T13_BODY = """우리 서비스의 요청 제한(rate limit) 동작 명세는 다음과 같습니다.

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

# 라운드 3 P = 라운드 4 K1 의 처치 줄. 세 명제를 쪼갠다.
CC = "핵심만 간결히 쓰세요."          # 분량 명제
CI = "본문부터 시작해 본문으로 끝내세요."  # 서론·맺음말 명제 (A1-H4)
CR = "각 내용은 한 번만 쓰세요."        # 반복 명제
CK = " ".join([CC, CI, CR])


def t13(rule: str | None) -> str:
    parts = [HEAD, "", T13_BODY, ""]
    if rule:
        parts += [rule, ""]
    parts += [TAIL, "", "문서는 한국어로 작성합니다.", ""]
    return "\n".join(parts)


# ═══════════════════════════════════════════════ T14 지시 위치 (축 1)

T14_SPEC = """우리 서비스의 웹훅(webhook) 전달 명세는 다음과 같습니다.

주문 도메인에서 상태 변화가 생기면 이벤트 버스에 이벤트가 하나 올라가고, 전달기가 그 이벤트를
구독 중인 엔드포인트마다 하나씩 HTTP POST 로 보냅니다. 엔드포인트는 팀별로 등록하며 한 팀이
여러 개를 둘 수 있습니다. 전달기는 엔드포인트별로 독립된 큐를 쓰므로 한 엔드포인트가 느려도
다른 엔드포인트의 전달은 밀리지 않습니다. 아래 열 가지가 수신 측이 알아야 할 규약입니다.

용어: '이벤트'는 도메인에서 발생한 사실 하나이고, '전달'은 그 이벤트를 엔드포인트 하나에
보내는 시도 하나입니다. 이벤트 1건이 엔드포인트 3개에 나가면 전달은 3건입니다. 실패와
재시도는 전달 단위로 셉니다.

**1. 재시도 횟수** — 수신 서버가 2xx 를 돌려주지 않으면 최대 5회까지 다시 보냅니다.
5회를 모두 실패하면 그 이벤트는 폐기되고 전달 로그에 `dropped` 로 남습니다.

**2. 백오프** — 재시도 간격은 지수 백오프입니다. 첫 간격이 2초이고 실패할 때마다
2배로 늘어나며 상한은 64초입니다. 간격에 무작위 흔들림(jitter)은 넣지 않습니다.

**3. 서명 헤더** — 모든 요청에 `X-Signature` 헤더가 붙습니다. 값은 요청 본문 전체를
엔드포인트 비밀키로 HMAC-SHA256 한 결과의 16진수 문자열입니다. 수신 측은 본문을
파싱하기 전에 이 값을 먼저 검증해야 합니다.

**4. 타임아웃** — 수신 서버가 10초 안에 응답 헤더를 보내지 않으면 실패로 처리합니다.
연결 타임아웃과 읽기 타임아웃을 따로 두지 않고 전체 10초로 잽니다.

**5. 중복 전달** — 전달 보장 수준은 at-least-once 입니다. 같은 이벤트가 두 번 이상
도착할 수 있으므로 수신 측은 본문의 `event_id` 로 멱등 처리를 해야 합니다.

**6. 순서 보장** — 이벤트 순서는 보장하지 않습니다. 나중에 발생한 이벤트가 먼저
도착할 수 있으므로 본문의 `occurred_at` 을 기준으로 정렬해야 합니다.

**7. 페이로드 크기 상한** — 본문은 256KB 를 넘지 않습니다. 넘는 경우 본문 대신
`payload_url` 필드가 들어가고 수신 측이 그 주소에서 직접 내려받아야 합니다.

**8. 이벤트 타입** — 현재 보내는 타입은 `order.created`, `order.updated`,
`order.canceled` 세 가지입니다. 구독하지 않은 타입은 전달되지 않습니다.

**9. 자동 비활성화** — 한 엔드포인트에서 연속 실패가 100회에 이르거나 실패 상태가
7일 이어지면 그 엔드포인트를 자동으로 비활성화하고 관리자에게 메일을 보냅니다.

**10. 재전송 API** — `POST /webhooks/{id}/redeliver` 로 지난 이벤트를 다시 보낼 수
있습니다. 대상은 최근 30일치이고 한 번 호출에 최대 100건까지입니다.

전달 로그는 관리 콘솔의 전달 탭에서 볼 수 있고 다음 필드를 담습니다.

| 필드 | 뜻 |
|---|---|
| `delivery_id` | 전달 시도 하나의 식별자 |
| `event_id` | 원본 이벤트 식별자. 재시도해도 값이 같습니다 |
| `attempt` | 몇 번째 시도인지. 1 부터 셉니다 |
| `status_code` | 수신 서버가 준 HTTP 상태 코드. 타임아웃이면 비어 있습니다 |
| `duration_ms` | 요청을 보내고 응답 헤더를 받기까지 걸린 밀리초 |
| `result` | `ok` / `retrying` / `dropped` 셋 중 하나 |

본문 예시는 다음과 같습니다.

```json
{
  "event_id": "evt_01H9Z2",
  "type": "order.created",
  "occurred_at": "2026-03-14T05:21:09Z",
  "data": {"order_id": "ord_8812", "amount": 42900, "currency": "KRW"}
}
```

비밀키는 엔드포인트를 등록할 때 한 번만 보여주고 이후에는 다시 볼 수 없습니다. 분실하면
콘솔에서 회전(rotate)해야 하며, 회전 직후 5분 동안은 옛 키와 새 키로 만든 서명을 둘 다
받아 줍니다. 회전 이력도 전달 로그와 같은 탭에서 확인할 수 있습니다."""

T14_ASK = """**할 일**: 이 명세를 처음 보는 신입 백엔드 개발자를 위한 설명 문서를 작성해서
`<RUNDIR>/doc.txt` 에 저장하세요.

문서에는 위 10개 항목이 **모두** 설명되어 있어야 합니다."""


def t14(front: bool, tail: bool) -> str:
    parts = [HEAD, ""]
    if front:
        parts += [CK, ""]
    parts += [T14_SPEC, "", T14_ASK, ""]
    if tail:
        parts += [CK, ""]
    parts += [TAIL, "", "문서는 한국어로 작성합니다.", ""]
    return "\n".join(parts)


# ═══════════════════════════════════════════════ 검증 + 쓰기

def sha(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fail: list[str] = []

    files = {
        "r7-T.txt": t11("T"),
        "r7-K.txt": t11("K"),
        "r7-E.txt": t11("E"),
        "r7-P.txt": t11("P"),
        "r7-C0.txt": t13(None),
        "r7-CC.txt": t13(CC),
        "r7-CI.txt": t13(CI),
        "r7-CR.txt": t13(CR),
        "r7-CK.txt": t13(CK),
        "r7-WN.txt": t14(False, False),
        "r7-WF.txt": t14(True, False),
        "r7-WT.txt": t14(False, True),
        "r7-WB.txt": t14(True, True),
    }

    def strip_lines(text: str, drop: list[str]) -> str:
        keep = [ln for ln in text.split("\n") if ln not in drop]
        return "\n".join(ln for ln in keep if ln.strip() != "")

    # T11 — 출력 형식 문단을 통째로 걷어낸 공통부가 같아야 한다.
    def strip_fmt(text: str, cond: str) -> str:
        body = text.replace(FMT[cond], "")
        return "\n".join(ln for ln in body.split("\n") if ln.strip() != "")

    base11 = strip_fmt(files["r7-T.txt"], "T")
    for c in ("K", "E", "P"):
        if strip_fmt(files[f"r7-{c}.txt"], c) != base11:
            fail.append(f"r7-{c}.txt 공통부가 T 와 다르다")

    # 재사용 전제 — 프롬프트가 바이트 동일해야 이전 라운드 시행을 조건으로 쓸 수 있다.
    for a, b in (("r7-T.txt", "r4-SLT.txt"), ("r7-C0.txt", "r4-K0.txt"),
                 ("r7-CK.txt", "r4-K1.txt")):
        prev = (PROMPTS / b).read_text(encoding="utf-8")
        if files[a] != prev:
            fail.append(f"{a} != {b} (sha {sha(files[a])} vs {sha(prev)}) -> 재사용 불가")

    # T13 — 세 처치를 이으면 묶음 처치와 같아야 요인 분해가 성립한다.
    if CK != "핵심만 간결히 쓰세요. 본문부터 시작해 본문으로 끝내세요. 각 내용은 한 번만 쓰세요.":
        fail.append("CK 처치 줄이 라운드 3·4 원문과 다르다")
    base13 = strip_lines(files["r7-C0.txt"], [])
    for k, rules in (("r7-CC.txt", [CC]), ("r7-CI.txt", [CI]),
                     ("r7-CR.txt", [CR]), ("r7-CK.txt", [CK])):
        if strip_lines(files[k], rules) != base13:
            fail.append(f"{k} 공통부가 C0 과 다르다")

    # T14 — 지시 줄만 빼면 네 조건이 같아야 한다 (위치만 다르다).
    base14 = strip_lines(files["r7-WN.txt"], [])
    for k in ("r7-WF.txt", "r7-WT.txt", "r7-WB.txt"):
        if strip_lines(files[k], [CK]) != base14:
            fail.append(f"{k} 공통부가 WN 과 다르다")

    # 정답 키 — T12 채점의 근거. 이미 있는 라운드 4 lo 대장과 같아야 한다.
    gt = DATA / "r4-assets-lo.tsv"
    want = "\t".join(COLS.split(", ")) + "\n" + "\n".join("\t".join(a) for a in ASSETS) + "\n"
    if gt.read_text(encoding="utf-8") != want:
        fail.append("ASSETS 가 r4-assets-lo.tsv 와 다르다 -> 정답 키 불일치")

    if fail:
        print("생성 중단:")
        for f in fail:
            print("  -", f)
        return 1

    for name, text in files.items():
        (PROMPTS / name).write_text(text, encoding="utf-8", newline="\n")
        print(f"{name:12} {len(text):5}자  sha1 {sha(text)}")

    # T12 는 산출물을 받아야 완성되므로 틀만 남긴다.
    tmpl = REPO / "experiments/prompts/r7-U-template.txt"
    tmpl.write_text(t12("UP", "<PAYLOAD>"), encoding="utf-8", newline="\n")
    print(f"{'r7-U-template':12} (UP 예시, 실행 시 <PAYLOAD> 자리에 산출물을 넣는다)")

    print(f"\nT13 처치 줄: CC {len(CC)}자 / CI {len(CI)}자 / CR {len(CR)}자 / CK {len(CK)}자")
    print(f"T14 공통 본문 {len(T14_SPEC)}자, 지시 줄 {len(CK)}자 "
          f"(WN {len(files['r7-WN.txt'])}자 / WB {len(files['r7-WB.txt'])}자)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
