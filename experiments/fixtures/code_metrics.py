"""Code-artifact metrics for the coding-agent experiments.

역할 분리 (round1-plan.md §4 결정):
  * 산출물 **길이(문자/단어/줄)** 계측은 `tools/measure.py` 하나로 통일한다.
    이 스크립트로 길이를 재지 않는다.
  * 이 스크립트는 **코드 산출물의 구조 지표**(줄 수, 주석 밀도) 전용이다.
    파일명이 `measure.py` 였을 때 tools/measure.py 와 역할이 혼동되어
    `code_metrics.py` 로 이름을 갈랐다.

Two subcommands:

  python code_metrics.py code <trial_dir> <baseline_dir> [ext ...]
      Emit code-artifact metrics: added lines, comment lines, comment density.
      라운드 1에서 쓰는 것은 이 모드뿐이다.

  python code_metrics.py transcript <run.ndjson>
      Parse a `claude -p --output-format stream-json --verbose` transcript.
      **라운드 2 전용.** 라운드 1의 실행 수단은 Agent 툴 서브에이전트뿐이라
      stream-json 트랜스크립트가 존재하지 않는다. 이 모드가 세는 문자 수는
      트랜스크립트 전용이며 파일 산출물 길이 계측에 쓰지 않는다.

Output is one `key=value` line per metric, so trials can be appended to a TSV.
"""
import json
import sys
from pathlib import Path

COMMENT_PREFIX = {".py": "#", ".js": "//", ".ts": "//", ".md": None}


def transcript(path: str) -> None:
    final_chars = 0
    inter_chars = 0
    inter_blocks = 0
    tool_calls = 0
    subagent_calls = 0
    assistant_msgs = 0

    events = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    # Index of the last assistant message that requested no tool: that is the
    # final user-facing answer. Everything earlier is inter-tool narration.
    last_answer_idx = -1
    for i, ev in enumerate(events):
        if ev.get("type") != "assistant":
            continue
        blocks = ev.get("message", {}).get("content", [])
        if not any(b.get("type") == "tool_use" for b in blocks):
            last_answer_idx = i

    for i, ev in enumerate(events):
        if ev.get("type") != "assistant":
            continue
        assistant_msgs += 1
        blocks = ev.get("message", {}).get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        for b in blocks:
            if b.get("type") == "tool_use":
                tool_calls += 1
                if b.get("name") in ("Task", "Agent"):
                    subagent_calls += 1
        if i == last_answer_idx:
            final_chars += len(text)
        elif text.strip():
            inter_chars += len(text)
            inter_blocks += 1

    print("final_response_chars=%d" % final_chars)
    print("interstitial_chars=%d" % inter_chars)
    print("interstitial_blocks=%d" % inter_blocks)
    print("user_facing_chars_total=%d" % (final_chars + inter_chars))
    print("tool_calls=%d" % tool_calls)
    print("subagent_calls=%d" % subagent_calls)
    print("assistant_messages=%d" % assistant_msgs)


def code(trial: str, baseline: str, exts) -> None:
    t, b = Path(trial), Path(baseline)
    exts = exts or [".py", ".js"]
    added = 0
    comment_lines = 0
    code_lines = 0
    base_total = 0
    for f in sorted(t.rglob("*")):
        if not f.is_file() or f.suffix not in exts:
            continue
        if "test" in f.name:
            continue
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        prefix = COMMENT_PREFIX.get(f.suffix)
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            code_lines += 1
            if prefix and s.startswith(prefix):
                comment_lines += 1
        peer = b / f.relative_to(t)
        if peer.is_file():
            base_total += len(peer.read_text(encoding="utf-8", errors="replace").splitlines())
        added += len(lines)
    print("nonblank_code_lines=%d" % code_lines)
    print("comment_lines=%d" % comment_lines)
    print("comment_density=%.3f" % (comment_lines / code_lines if code_lines else 0.0))
    print("total_lines=%d" % added)
    print("baseline_lines=%d" % base_total)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] == "transcript":
        transcript(sys.argv[2])
    elif sys.argv[1] == "code":
        code(sys.argv[2], sys.argv[3], sys.argv[4:])
    else:
        print(__doc__)
        sys.exit(2)
