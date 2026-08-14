#!/usr/bin/env python3
"""산출물 길이 측정기 (토큰 proxy).

이 저장소에는 ANTHROPIC_API_KEY 가 없어 usage.output_tokens 를 쓸 수 없다.
대신 문자/단어/줄 수를 측정해 **조건 간 상대 비교**에만 사용한다.
절대 토큰 수로 해석하지 말 것. CLAUDE.md '측정 제약' 참조.

사용법:
    python tools/measure.py <파일...>                 # 개별 측정
    python tools/measure.py --json <파일...>          # JSON 출력
    python tools/measure.py --ab A.txt B.txt          # A 대비 B 상대 절감률
    python tools/measure.py --ncd 입력.txt 산출.txt   # 두 텍스트의 겹침 (재진술 대리 측정)
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
    bytes_utf8  UTF-8 바이트 수
    bytes_gz    zlib(level 9) 압축 후 바이트 수 — 잉여를 뺀 나머지의 대리 지표
    redundancy  1 - bytes_gz/bytes_utf8. 반복·서식 문자가 많을수록 1 에 가깝다

bytes_gz 를 왜 재는가: chars 는 '표현의 길이'이고 bytes_gz 는 '표현에서 반복을
걷어낸 뒤 남는 양'이다. 두 값이 같은 방향으로 줄면 실제 내용이 줄어든 것이고,
chars 만 줄고 bytes_gz 가 그대로면 걷어낸 것이 잉여(괘선·반복 키·들여쓰기)다.
라운드 3 A1-H7(괘선 문자 +824자)처럼 '길이는 늘었는데 내용은 그대로'인 경우를
문자 수만으로는 구분할 수 없었다.

bytes_gz 의 한계 (해석 전 반드시 읽을 것):
    - zlib 헤더·초기 사전 비용이 고정으로 붙는다. 1KB 미만 텍스트에서는
      비율이 불안정하다. 절대값을 쓰지 말고 **같은 과제 조건 간 비율**로만 본다.
    - 한국어는 UTF-8 에서 음절당 3바이트다. bytes_gz 는 chars 와 단위가 다르므로
      두 값을 나누거나 섞지 않는다.
    - gzip 은 토크나이저가 아니다. bytes_gz 절감률도 토큰 절감률이 아니다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from pathlib import Path

FENCE = re.compile(r"^\s*```")
HANGUL = re.compile(r"[가-힣]")
LATIN = re.compile(r"[A-Za-z]")


def gz(text: str) -> int:
    """zlib 최대 압축 후 바이트 수. 잉여를 걷어낸 나머지의 대리 지표."""
    return len(zlib.compress(text.encode("utf-8"), 9))


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

    nbytes = len(text.encode("utf-8"))
    ngz = gz(text)

    return {
        "chars": len(text),
        "chars_nows": len("".join(text.split())),
        "words": len(text.split()),
        "lines": len(lines),
        "code_chars": code_chars,
        "prose_chars": len(text) - code_chars,
        "hangul": hangul,
        "latin": latin,
        "bytes_utf8": nbytes,
        "bytes_gz": ngz,
        # 1 에 가까울수록 반복·서식이 많다는 뜻. 조건 간 비교용이지 절대 해석 금지.
        "redundancy": round(1 - ngz / nbytes, 3) if nbytes else 0.0,
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
    for k in ("chars", "chars_nows", "words", "lines", "prose_chars", "bytes_gz"):
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


def ncd(x_path: str, y_path: str) -> dict:
    """정규화 압축 거리 — Y 가 X 를 얼마나 되풀이했는지의 대리 측정.

    NCD(x,y) = (C(xy) - min(C(x),C(y))) / max(C(x),C(y))

    1 에 가까우면 두 텍스트가 서로 무관하고, 0 에 가까우면 한쪽이 다른 쪽에
    거의 들어 있다. X 를 요청 프롬프트, Y 를 산출물로 놓으면 낮은 NCD 는
    산출물이 요청을 되풀이했다는 뜻이다 (정보이론상 그 부분의 정보량은 0).

    한계: zlib 창은 32KB 다. 합친 길이가 그보다 길면 뒤쪽 겹침을 못 본다.
    또 두 텍스트 길이가 크게 다르면 값이 긴 쪽으로 눌린다 — 길이가 비슷한
    조건 사이에서만 비교한다.
    """
    x, y = read(x_path), read(y_path)
    cx, cy, cxy = gz(x), gz(y), gz(x + "\n" + y)
    val = (cxy - min(cx, cy)) / max(cx, cy) if max(cx, cy) else 0.0
    return {
        "x_file": x_path,
        "y_file": y_path,
        "c_x": cx,
        "c_y": cy,
        "c_xy": cxy,
        "ncd": round(val, 3),
        "window_exceeded": len((x + y).encode("utf-8")) > 32768,
    }


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
    p.add_argument("--ncd", action="store_true", help="파일 2개의 정규화 압축 거리 (X=입력, Y=산출물)")
    args = p.parse_args()

    if args.ncd:
        if len(args.files) != 2:
            p.error("--ncd 는 파일 2개가 필요하다 (X=입력, Y=산출물)")
        result = ncd(args.files[0], args.files[1])
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"X={result['x_file']}  Y={result['y_file']}")
            print(f"  C(x) {result['c_x']}  C(y) {result['c_y']}  C(xy) {result['c_xy']}")
            print(f"  NCD  {result['ncd']}   (0=완전 포함 / 1=무관)")
        if result["window_exceeded"]:
            print("\n[경고] 합친 길이가 zlib 창 32KB 를 넘는다. 겹침이 과소 측정된다.", file=sys.stderr)
            return 2
        return 0

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
