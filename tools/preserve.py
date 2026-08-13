#!/usr/bin/env python3
"""시행 산출물을 저장소에 보존한다 (CLAUDE.md 산출물 보존 규칙).

시행 **작업** 디렉터리는 저장소 밖에 둔다 — 저장소 안에서 돌리면 피험
에이전트가 정답 키(`experiments/data/*-groundtruth.*`)와 사전등록 문서를
읽을 수 있어 naive 조건이 깨진다. 그래서 실행이 끝난 뒤 여기로 복사한다.

    python tools/preserve.py --import <작업루트> --round r3
    python tools/preserve.py --manifest            # 전 라운드 목록 갱신

복사 시 실행 환경의 절대 경로를 `<RUNDIR>` 로 치환한다. 저장소가 공개라
로컬 사용자명이 그대로 올라가면 안 된다.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "experiments/runs"

TEXT_SUFFIX = {".txt", ".md", ".json", ".tsv", ".yaml", ".yml", ".diff", ".py", ".js"}
# 절대 경로처럼 생긴 것을 잡는다. 드라이브 문자 / 유닉스 경로 양쪽.
ABS = re.compile(r"(?:[A-Za-z]:[\\/]|/)(?:[^\s\"'`<>|]*[\\/])*[^\s\"'`<>|]*", re.I)


def anonymize(text: str, live_root: Path) -> str:
    """작업 루트 경로를 <RUNDIR> 로 바꾼다. 표기 흔들림(\\, /, ~1)을 모두 처리."""
    forms = {str(live_root), str(live_root).replace("\\", "/"), live_root.as_posix()}
    for f in sorted(forms, key=len, reverse=True):
        text = text.replace(f, "<RUNDIR>")
        text = text.replace(f.replace("/", "\\"), "<RUNDIR>")
    return text


def import_run(live_root: Path, rnd: str) -> int:
    dest_root = RUNS / rnd
    dest_root.mkdir(parents=True, exist_ok=True)
    n = 0
    for d in sorted(live_root.glob("t*")):
        if not d.is_dir():
            continue
        dest = dest_root / d.name
        dest.mkdir(exist_ok=True)
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() in TEXT_SUFFIX:
                raw = f.read_text(encoding="utf-8", errors="replace")
                out = anonymize(raw, live_root / d.name)
                out = anonymize(out, live_root)
                (dest / f.name).write_text(out, encoding="utf-8", newline="\n")
            else:
                shutil.copy2(f, dest / f.name)
            n += 1
    print(f"{rnd}: 파일 {n}개 보존 -> {dest_root.relative_to(REPO)}")
    return n


def leak_check() -> list[str]:
    """보존된 파일에 실행 환경 절대 경로가 남았는지 본다."""
    bad: list[str] = []
    for f in RUNS.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in TEXT_SUFFIX:
            continue
        t = f.read_text(encoding="utf-8", errors="replace")
        for m in ABS.finditer(t):
            s = m.group(0)
            if "Users" in s or "AppData" in s or "home/" in s:
                bad.append(f"{f.relative_to(REPO)}: {s[:70]}")
                break
    return bad


def manifest() -> None:
    for rnd_dir in sorted(p for p in RUNS.iterdir() if p.is_dir()):
        cond_file = rnd_dir / "conditions.tsv"
        cond: dict[str, str] = {}
        if cond_file.exists():
            for ln in cond_file.read_text(encoding="utf-8").strip().split("\n")[1:]:
                t, c = ln.split("\t")[:2]
                cond[t] = c
        rows = ["trial\tcondition\tfile\tbytes\tsha256_12"]
        for d in sorted(p for p in rnd_dir.iterdir() if p.is_dir()):
            for f in sorted(d.iterdir()):
                if not f.is_file():
                    continue
                b = f.read_bytes()
                rows.append(
                    f"{d.name}\t{cond.get(d.name, '-')}\t{f.name}\t{len(b)}"
                    f"\t{hashlib.sha256(b).hexdigest()[:12]}"
                )
        dest = rnd_dir / "manifest.tsv"
        dest.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
        print(f"{dest.relative_to(REPO)}  {len(rows)-1}행")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--import", dest="src", help="시행 작업 루트 (저장소 밖)")
    ap.add_argument("--round", dest="rnd", help="r1, r2, r3 …")
    ap.add_argument("--manifest", action="store_true", help="목록만 갱신")
    a = ap.parse_args()

    if a.src:
        if not a.rnd:
            ap.error("--import 에는 --round 가 필요하다")
        src = Path(a.src)
        if not src.is_dir():
            ap.error(f"작업 루트 없음: {src}")
        if REPO in src.resolve().parents or src.resolve() == REPO:
            ap.error("작업 루트가 저장소 안에 있다 — naive 조건이 깨진다")
        import_run(src, a.rnd)

    manifest()

    leaks = leak_check()
    if leaks:
        print("\n경로 노출 발견 — 커밋하지 말 것:", file=sys.stderr)
        for x in leaks[:20]:
            print("  " + x, file=sys.stderr)
        return 2
    print("\n경로 노출 0건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
