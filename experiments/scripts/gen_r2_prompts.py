#!/usr/bin/env python3
"""라운드 2 피험자 프롬프트 생성 (사전등록 §3).

조건 간 차이가 '출력 형식 지시' 한 문단뿐임을 손이 아니라 코드로 보장한다.
생성 후 공통부 해시를 출력하니, 6개 조건의 해시가 모두 같은지 확인할 것.

사용법:  python experiments/scripts/gen_r2_prompts.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "experiments/data"
OUT = REPO / "experiments/prompts"

FIXTURES = {
    "30": DATA / "02-deploy-original.yaml",
    "120": DATA / "r2-deploy120-original.yaml",
}

CHANGES = """## 변경 요청 (6곳)

1. `replicas` 를 3에서 6으로 변경
2. `env` 를 `staging` 에서 `production` 으로 변경
3. `logging.level` 을 `debug` 에서 `info` 로 변경
4. `logging.format` 을 `text` 에서 `json` 으로 변경
5. `autoscale.enabled` 를 `false` 에서 `true` 로 변경
6. `database.ssl` 을 `false` 에서 `true` 로 변경

그 외의 줄은 변경하지 않는다."""

# 조건별로 달라지는 유일한 부분. 여기 말고 어디서도 조건 분기를 하지 않는다.
FORMATS = {
    "A": (
        "out.yaml",
        "## 출력 형식\n\n"
        "수정된 `deploy.yaml` 전체를 아래 경로에 저장한다.\n"
        "{n}줄 전부 쓴다. 생략·축약·`...` 표기를 쓰지 않는다.",
    ),
    "B": (
        "out.diff",
        "## 출력 형식\n\n"
        "수정 내용을 unified diff 로 아래 경로에 저장한다.\n"
        "파일 헤더는 `--- a/deploy.yaml` 와 `+++ b/deploy.yaml` 로 하고, "
        "원본 파일에 `git apply -p1` 로 적용 가능해야 한다.",
    ),
    "C": (
        "out.diff",
        "## 출력 형식\n\n"
        "수정 내용을 unified diff 로 아래 경로에 저장한다.\n"
        "파일 헤더는 `--- a/deploy.yaml` 와 `+++ b/deploy.yaml` 로 하고, "
        "원본 파일에 `git apply -p1` 로 적용 가능해야 한다.\n"
        "각 hunk 의 컨텍스트 줄은 변경 줄 위아래 **1줄씩**으로 한다.",
    ),
}

# 조건 A/B/C 에 동일하게 들어간다 -> 조작 변수가 아니다 (라운드 1b 교훈 선반영).
NO_BYPASS = (
    "도구 호출이 거부되면 다른 수단으로 우회하지 말고, "
    "거부되었다는 사실을 보고하고 중단한다."
)

TEMPLATE = """설정 파일 `deploy.yaml` 을 아래 요청대로 수정한다.

## 원본 `deploy.yaml` ({n}줄)

```
{numbered}
```

{changes}

{fmt}

저장 경로: `{{OUTDIR}}/{fname}`

{nobypass}
"""


def numbered(path: Path) -> tuple[str, int]:
    lines = path.read_text(encoding="utf-8").rstrip("\n").split("\n")
    w = len(str(len(lines)))
    body = "\n".join(f"{i:>{w}}  {ln}" for i, ln in enumerate(lines, 1))
    return body, len(lines)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}

    for n, fx in FIXTURES.items():
        body, count = numbered(fx)
        assert str(count) == n, f"{fx.name}: 줄 수 {count} != {n}"
        for cond, (fname, fmt) in FORMATS.items():
            text = TEMPLATE.format(
                n=count,
                numbered=body,
                changes=CHANGES,
                fmt=fmt.format(n=count),
                fname=fname,
                nobypass=NO_BYPASS,
            )
            dest = OUT / f"r2-{cond}{n}.txt"
            dest.write_text(text, encoding="utf-8", newline="\n")
            # 공통부 = 형식 지시 문단과 저장 경로 줄을 뺀 나머지
            common = text.replace(fmt.format(n=count), "").replace(fname, "")
            digests[f"{cond}{n}"] = hashlib.sha256(common.encode()).hexdigest()[:12]
            print(f"{dest.name:>14}  {len(text):>6} chars")

    print("\n공통부 해시 (같은 N 안에서 A/B/C 가 일치해야 한다):")
    for n in FIXTURES:
        hs = {c: digests[f"{c}{n}"] for c in FORMATS}
        ok = len(set(hs.values())) == 1
        print(f"  N={n:>3}: {hs}  ->  {'일치' if ok else '불일치 (설계 오류)'}")
        if not ok:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
