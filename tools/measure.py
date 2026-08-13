#!/usr/bin/env python3
"""산출물 길이 측정기 (토큰 proxy).

이 저장소에는 ANTHROPIC_API_KEY 가 없어 usage.output_tokens 를 쓸 수 없다.
대신 문자/단어/줄 수를 측정해 **조건 간 상대 비교**에만 사용한다.
절대 토큰 수로 해석하지 말 것. CLAUDE.md '측정 제약' 참조.

사용법:
    python tools/measure.py <파일...>                 # 개별 측정
    python tools/measure.py --json <파일...>          # JSON 출력
    python tools/measure.py --ab A.txt B.txt          # A 대비 B 상대 절감률
    cat out.txt | python tools/measure.py -           # stdin

측정 항목:
    chars       전체 문자 수
    chars_nows  공백 제외 문자 수 (언어 무관 비교에 더 안정적)
    words       공백 기준 토막 수 (한국어에서는 어절 수)
    lines       줄 수 (마지막 빈 줄 제외)
    code_chars  ``` 펜스 안 문자 수
    prose_chars chars - code_chars
    hangul      한글 음절 수 (언어 구성 고정 확인용)
    latin       ASCII 영문자 수 (언어 구성 고정 확인용)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^\s*```")
HANGUL = re.compile(r"[가-힣]")
LATIN = re.compile(r"[A-Za-z]")


def measure(text: str) -> dict[str, int | float]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    code_chars = 0
    in_code = False
    prose_lines: list[str] = []
    for line in lines:
        if FENCE.match(line):
            in_code = not in_code
            code_chars += len(line) + 1
            continue
        if in_code:
            code_chars += len(line) + 1
        else:
            prose_lines.append(line)

    # 언어 구성은 산문만으로 잰다. 코드 블록은 항상 영문이라
    # 전체 기준으로 재면 산문이 짧아질 때마다 영문 비율이 올라가 오탐이 난다.
    prose_text = "\n".join(prose_lines)
    hangul = len(HANGUL.findall(prose_text))
    latin = len(LATIN.findall(prose_text))
    script_total = hangul + latin

    return {
        "chars": len(text),
        "chars_nows": len("".join(text.split())),
        "words": len(text.split()),
        "lines": len(lines),
        "code_chars": code_chars,
        "prose_chars": len(text) - code_chars,
        "hangul": hangul,
        "latin": latin,
        # 조건 간 언어 구성이 흔들리면 문자↔토큰 비율이 깨진다.
        # 이 값이 조건 A/B 사이에서 크게 다르면 비교 자체가 무효.
        "hangul_ratio": round(hangul / script_total, 3) if script_total else 0.0,
    }


def read(spec: str) -> str:
    if spec == "-":
        return sys.stdin.read()
    return Path(spec).read_text(encoding="utf-8")


def ab(a_path: str, b_path: str) -> dict:
    a, b = measure(read(a_path)), measure(read(b_path))
    delta = {}
    for k in ("chars", "chars_nows", "words", "lines", "prose_chars"):
        delta[k] = {
            "a": a[k],
            "b": b[k],
            # 음수 = B 가 짧아짐 = 절감
            "pct": round((b[k] - a[k]) / a[k] * 100, 1) if a[k] else None,
        }
    warn = None
    if abs(a["hangul_ratio"] - b["hangul_ratio"]) > 0.10:
        warn = (
            f"언어 구성 불일치: hangul_ratio A={a['hangul_ratio']} B={b['hangul_ratio']}. "
            "문자 수 비교가 토큰 비교를 대변하지 못한다. 조건을 다시 맞출 것."
        )
    return {"a_file": a_path, "b_file": b_path, "delta": delta, "warning": warn}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # 윈도 콘솔 기본 코드페이지에서 한글 깨짐 방지
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+", help="측정할 파일 ('-' 는 stdin)")
    p.add_argument("--json", action="store_true", help="JSON 으로 출력")
    p.add_argument("--ab", action="store_true", help="파일 2개를 A/B 비교")
    args = p.parse_args()

    if args.ab:
        if len(args.files) != 2:
            p.error("--ab 는 파일 2개가 필요하다")
        result = ab(args.files[0], args.files[1])
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"A={result['a_file']}  B={result['b_file']}")
            for k, v in result["delta"].items():
                sign = "" if v["pct"] is None or v["pct"] < 0 else "+"
                print(f"  {k:12} {v['a']:>8} -> {v['b']:>8}  ({sign}{v['pct']}%)")
            if result["warning"]:
                print(f"\n[경고] {result['warning']}", file=sys.stderr)
                return 2
        return 0

    out = {f: measure(read(f)) for f in args.files}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for f, m in out.items():
            print(f"{f}")
            for k, v in m.items():
                print(f"  {k:14} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
