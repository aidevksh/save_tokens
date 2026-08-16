#!/usr/bin/env python3
"""라운드 8 재료·프롬프트 생성기.

    python experiments/scripts/gen_r8.py

과제 4개:
  T15  불투명 값 표 스키마 (A2-H2 키 축약 재시험 / A2-H5 헤더 제거 재시험)
  T16  수치 상한 하향 사다리 (A1-H3 확장 — 150자·80자)
  T17  지시의 분산 억제 (A1-H8 신규) — 프롬프트는 라운드 7 것을 그대로 쓴다
  T18  주석 밀도 규칙 재설계 (A5-H5 재시험) — 주석을 부르는 과제로 바꾼다

라운드 7이 A2-H2·A2-H5 에서 천장 효과로 막힌 원인 두 가지를 재료 수준에서 고친다.
  (a) 값이 자기설명적이었다(`apne1`·`prod`) → 값을 불투명 토큰으로 바꾼다
  (b) 열 이름의 첫 글자가 거의 겹치지 않았다 → 첫 글자가 겹치는 이름으로 바꾼다
      `phase/plan/pace/port` 는 전부 p, `mode/mark/mesh` 는 전부 m 이다.
      1글자 축약이 정보를 버리는지는 **이름 공간이 충돌할 때만** 물을 수 있다.

생성 후 스스로 검증한다. 실패하면 파일을 쓰지 않는다.
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

# ═══════════════════════════════════════════════ T15 불투명 값 표 (축 2)

COLNAMES = ["rec_id", "phase", "plan", "pace", "port", "mode", "mark", "mesh"]
OPAQUE = COLNAMES[1:]                      # rec_id 를 뺀 7개가 불투명 열이다
POOL = ["k7q", "m2v", "p9r", "t4x", "w6b", "z3n", "c8j", "h5d"]


def build_records() -> list[tuple[str, ...]]:
    """sha256 파생값으로 12×7 표를 만든다.

    라운드 5에서 LCG 를 쓰다 하위 비트에 주기가 생긴 적이 있다. 여기서는
    (열, 행) 쌍마다 독립 해시를 뽑고, 생성 후 열마다 주기를 검사한다.
    """
    recs = []
    for i in range(1, 13):
        row = [f"RC-{3000 + i}"]
        for c in OPAQUE:
            h = hashlib.sha256(f"r8-{c}-{i}".encode()).hexdigest()
            row.append(POOL[int(h[:8], 16) % len(POOL)])
        recs.append(tuple(row))
    return recs


RECORDS = build_records()

COLS = ", ".join(COLNAMES)

T15_INTRO = ("아래는 배치 작업 레코드 12건입니다. 각 레코드에서 " + COLS +
             " 8개 항목을 표로 정리하세요.\n\n레코드 기록:")

FMT_HEAD = ("출력 형식: 결과를 TSV로 `<RUNDIR>/out.txt` 에 저장하세요. 첫 줄은 헤더이고 그 아래\n"
            "레코드 1건당 1줄씩 총 12줄입니다. 열 구분자는 탭 문자 1개이며 열 순서는 다음과 같습니다.\n"
            + COLS)

FMT15 = {
    # T: 헤더 TSV, 열 이름 전체 (기준선)
    "T": FMT_HEAD,
    # K: 열 이름 1글자 축약. 매핑을 주지 않는다 — A2-H2 의 처치.
    "K": FMT_HEAD + "\n헤더의 열 이름은 각각 1글자로 줄여서 씁니다. 값은 원문 그대로 씁니다.",
    # R: 헤더 줄 자체를 뺀다 — A2-H5 의 처치.
    "R": ("출력 형식: 결과를 TSV로 `<RUNDIR>/out.txt` 에 저장하세요. 헤더 줄 없이\n"
          "레코드 1건당 1줄씩 총 12줄만 씁니다. 열 구분자는 탭 문자 1개이며 열 순서는 다음과 같습니다.\n"
          + COLS),
}


def t15(cond: str) -> str:
    recs = "\n\n".join(
        f"**{r[0]}** — phase {r[1]}, plan {r[2]}, pace {r[3]}, port {r[4]}, "
        f"mode {r[5]}, mark {r[6]}, mesh {r[7]}." for r in RECORDS)
    parts = [HEAD, "", T15_INTRO, "", recs, "", FMT15[cond], "",
             "파일에는 결과 데이터만 넣고 설명이나 주석은 넣지 않습니다.", "",
             TAIL, "", "설명이 필요하면 한국어로 씁니다.", ""]
    return "\n".join(parts)


# ── T15 2차 소비자 ────────────────────────────────────────────────
# 질문 6개는 전 조건 동일하다. 여섯 개 모두 **열을 지목**한다 —
# 값이 불투명하므로 열이 무엇인지 모르면 답할 수 없다. 이것이 천장을 걷는 장치다.
Q15 = [
    ("cell", "pace", "RC-3007"),
    ("cell", "mesh", "RC-3010"),
    ("count", "mark", "c8j"),
    ("list", "phase", "p9r"),
    ("count", "port", "t4x"),
    ("pair", ("mode", "k7q"), ("plan", "t4x")),
]


def col(name: str) -> int:
    return COLNAMES.index(name)


def answer(q) -> str:
    kind = q[0]
    if kind == "cell":
        _, c, rid = q
        return next(r[col(c)] for r in RECORDS if r[0] == rid)
    if kind == "count":
        _, c, v = q
        return str(sum(1 for r in RECORDS if r[col(c)] == v))
    if kind == "list":
        _, c, v = q
        return ", ".join(r[0] for r in RECORDS if r[col(c)] == v)
    _, (c1, v1), (c2, v2) = q
    return ", ".join(r[0] for r in RECORDS if r[col(c1)] == v1 and r[col(c2)] == v2)


QUESTIONS15 = """1. RC-3007 의 pace 값은 무엇입니까?
2. RC-3010 의 mesh 값은 무엇입니까?
3. mark 가 c8j 인 레코드는 몇 건입니까?
4. phase 가 p9r 인 레코드의 rec_id 를 모두 쓰세요.
5. port 가 t4x 인 레코드는 몇 건입니까?
6. mode 가 k7q 이면서 plan 이 t4x 인 레코드의 rec_id 를 모두 쓰세요."""

# 소비자에게 주는 규약.
# UT·UK 는 빈 문자열이다 — K 조건에는 줄 수 있는 규약이 **없다**(생산자가 지어낸 약자다).
# UR 은 열 순서를 준다. 헤더를 지운 것은 정보를 **버린 것이 아니라 프롬프트로 옮긴 것**이므로
# 규약을 주는 쪽이 이 처치의 정직한 형태다. 이 비대칭 자체를 사전등록한다.
PROTO15 = {
    "UT": "",
    "UK": "",
    "UR": "표에는 헤더 줄이 없습니다. 열 순서는 다음과 같습니다.\n" + COLS,
}


def t15u(cond: str, payload: str) -> str:
    parts = [HEAD, "",
             "아래는 배치 작업 레코드를 정리한 표입니다.", "",
             "```", payload.rstrip("\n"), "```", ""]
    if PROTO15[cond]:
        parts += [PROTO15[cond], ""]
    parts += ["**할 일**: 이 표를 읽고 아래 질문 6개에 답해서 `<RUNDIR>/ans.txt` 에 저장하세요.",
              "", QUESTIONS15, "",
              "파일에는 `1. 답` 처럼 번호와 답만 한 줄씩 6줄 쓰고 다른 설명은 넣지 않습니다.", "",
              TAIL, "", "설명이 필요하면 한국어로 씁니다.", ""]
    return "\n".join(parts)


# ═══════════════════════════════════════════════ T16 수치 상한 사다리 (축 1)

T16_BODY = """우리 서비스의 요청 제한(rate limit) 동작 명세는 다음과 같습니다.

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


def t16(rule: str | None) -> str:
    parts = [HEAD, "", T16_BODY, ""]
    if rule:
        parts += [rule, ""]
    parts += [TAIL, "", "문서는 한국어로 작성합니다.", ""]
    return "\n".join(parts)


def cap(n: int) -> str:
    return f"문서는 {n}자 이내로 쓰세요."


# 율-왜곡 바닥 참조선 — 6항목을 담은 최소 텍스트. 데이터 수집 **전**에 손으로 쓴다.
# 이것은 조건이 아니라 자다. 상한이 이 길이 아래로 내려가면 항목이 빠질 수밖에 없다.
FLOOR_DOC = ("버킷 용량 60, 리필 초당 1개. 집계는 IP가 아니라 API 키 단위. "
             "초과하면 429와 Retry-After(초 단위 정수) 헤더. admin 스코프 키는 제외.")

# ═══════════════════════════════════════════════ T18 주석 밀도 재설계 (축 5)

T18_BODY = """`sched.js` 는 영업일과 기간을 계산하는 모듈이고
`sched.test.js` 는 그 모듈의 단위 테스트입니다. 지금 테스트 10개 중 7개가 실패합니다.

    node --test

**할 일**: `sched.js` 에 기능을 추가해 테스트 10개가 모두 통과하게 만드세요.
테스트 파일은 명세이므로 수정하지 마세요."""

S5 = "설명은 코드 이름으로 합니다. 주석 없이 읽히게 씁니다."


def t18(rule: str | None) -> str:
    parts = [HEAD, "", T18_BODY, ""]
    if rule:
        parts += [rule, ""]
    parts += [TAIL, "", "설명이 필요하면 한국어로 씁니다.", ""]
    return "\n".join(parts)


# ═══════════════════════════════════════════════ 검증 + 쓰기

def sha(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def has_period(seq: list[str], max_p: int = 6) -> int | None:
    for p in range(1, max_p + 1):
        if len(seq) >= 2 * p and all(seq[i] == seq[i - p] for i in range(p, len(seq))):
            return p
    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fail: list[str] = []

    # ── 재료 검증 ────────────────────────────────────────────────
    # (a) 열 이름 첫 글자가 실제로 충돌해야 A2-H2 를 물을 수 있다.
    firsts = [c[0] for c in COLNAMES]
    if len(set(firsts)) >= len(firsts):
        fail.append("열 이름 첫 글자가 충돌하지 않는다 -> 1글자 축약이 무손실이 된다")
    # (b) 값이 열을 되돌려 주면 안 된다 — 모든 열이 같은 값 공간을 써야 한다.
    for c in OPAQUE:
        vs = {r[col(c)] for r in RECORDS}
        if not vs <= set(POOL):
            fail.append(f"{c} 열의 값이 공용 풀 밖에 있다")
    shared = sum(1 for a in OPAQUE for b in OPAQUE
                 if a < b and {r[col(a)] for r in RECORDS} == {r[col(b)] for r in RECORDS})
    if shared < 1:
        fail.append("값 공간이 완전히 같은 열 쌍이 하나도 없다 -> 값으로 열을 특정할 수 있다")
    # (c) 열마다 주기가 없어야 한다(라운드 5 LCG 사고 재발 방지).
    for c in OPAQUE:
        seq = [r[col(c)] for r in RECORDS]
        p = has_period(seq)
        if p:
            fail.append(f"{c} 열에 주기 {p} 이 있다")
    # (d) 질문 6개가 불투명 열 7개를 정확히 한 번씩 덮어야 한다.
    #     열 하나라도 빠지면 그 열의 이름을 몰라도 만점이 나올 수 있다(라운드 7 천장).
    asked: list[str] = []
    for q in Q15:
        asked += [q[1][0], q[2][0]] if q[0] == "pair" else [q[1]]
    if sorted(asked) != sorted(OPAQUE):
        fail.append(f"질문이 덮는 열 {sorted(asked)} != 불투명 열 {sorted(OPAQUE)}")

    # (e) 질문의 답이 자명하지 않아야 한다.
    for i, q in enumerate(Q15, 1):
        a = answer(q)
        if q[0] == "count" and not (2 <= int(a) <= 6):
            fail.append(f"Q{i} count 답이 {a} — 범위 밖")
        if q[0] in ("list", "pair"):
            k = len([x for x in a.split(", ") if x])
            if not (1 <= k <= 5):
                fail.append(f"Q{i} 목록 답이 {k}건 — 범위 밖")

    files = {
        "r8-T.txt": t15("T"),
        "r8-K.txt": t15("K"),
        "r8-R.txt": t15("R"),
        "r8-CN150.txt": t16(cap(150)),
        "r8-CN80.txt": t16(cap(80)),
        "r8-DB.txt": t18(None),
        "r8-DS.txt": t18(S5),
    }

    def squeeze(text: str, drop: list[str]) -> str:
        keep = [ln for ln in text.split("\n") if ln not in drop]
        return "\n".join(ln for ln in keep if ln.strip() != "")

    # T15 — 세 조건이 출력 형식 문단을 뺀 공통부에서 바이트 동일해야 한다.
    def strip_fmt(text: str, cond: str) -> str:
        return "\n".join(ln for ln in text.replace(FMT15[cond], "").split("\n")
                         if ln.strip() != "")

    base15 = strip_fmt(files["r8-T.txt"], "T")
    for c in ("K", "R"):
        if strip_fmt(files[f"r8-{c}.txt"], c) != base15:
            fail.append(f"r8-{c}.txt 공통부가 T 와 다르다")

    # T16 — 상한 줄만 빼면 라운드 6 CN300 과 바이트 동일해야 재사용이 성립한다.
    prev = (PROMPTS / "r6-CN300.txt").read_text(encoding="utf-8")
    base16 = squeeze(prev, [cap(300)])
    for k, n in (("r8-CN150.txt", 150), ("r8-CN80.txt", 80)):
        if squeeze(files[k], [cap(n)]) != base16:
            fail.append(f"{k} 공통부가 r6-CN300.txt 와 다르다 -> 사다리 연결 불가")
    if squeeze(t16(None), []) != base16:
        fail.append("무지시 공통부가 r6-CN300.txt 와 다르다")

    # T17 — 새 프롬프트가 없다. 라운드 7 파일이 그대로 있어야 한다.
    for name, want in (("r7-WN.txt", "지시 없음"), ("r7-WT.txt", "말미 지시")):
        if not (PROMPTS / name).exists():
            fail.append(f"{name} 없음 -> A1-H8 재사용 불가 ({want})")

    # T18 — 처치 줄만 빼면 두 조건이 같아야 한다. S5 는 라운드 6 원문 그대로여야 한다.
    if S5 != "설명은 코드 이름으로 합니다. 주석 없이 읽히게 씁니다.":
        fail.append("S5 처치 줄이 라운드 6 원문과 다르다")
    if squeeze(files["r8-DS.txt"], [S5]) != squeeze(files["r8-DB.txt"], []):
        fail.append("r8-DS.txt 공통부가 r8-DB.txt 와 다르다")

    if fail:
        print("생성 중단:")
        for f in fail:
            print("  -", f)
        return 1

    # ── 쓰기 ─────────────────────────────────────────────────────
    for name, text in files.items():
        (PROMPTS / name).write_text(text, encoding="utf-8", newline="\n")
        print(f"{name:14} {len(text):5}자  sha1 {sha(text)}")

    gt = DATA / "r8-records.tsv"
    gt.write_text("\t".join(COLNAMES) + "\n" + "\n".join("\t".join(r) for r in RECORDS) + "\n",
                  encoding="utf-8", newline="\n")
    key = DATA / "r8-answers.tsv"
    key.write_text("\n".join(f"{i}\t{answer(q)}" for i, q in enumerate(Q15, 1)) + "\n",
                   encoding="utf-8", newline="\n")
    tmpl = PROMPTS / "r8-U-template.txt"
    tmpl.write_text(t15u("UR", "<PAYLOAD>"), encoding="utf-8", newline="\n")
    print(f"{'r8-records.tsv':14} 12행 · {'r8-answers.tsv':14} 6문항 · r8-U-template.txt")

    print("\n[T15 재료] 열 이름 첫 글자 " + "".join(firsts) +
          f" (고유 {len(set(firsts))}/{len(firsts)}) · 값 공간 동일 열쌍 {shared}개")
    for i, q in enumerate(Q15, 1):
        print(f"  Q{i} {answer(q)}")
    print(f"\n[T16 바닥 참조선] {len(FLOOR_DOC)}자 — {FLOOR_DOC}")
    print(f"  상한 800 → 실측 641 / 300 → 248 / 150 → ? / 80 → ?  (바닥 {len(FLOOR_DOC)}자)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
