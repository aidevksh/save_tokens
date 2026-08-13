"""
실험 02 — thinking disabled vs adaptive+low effort: 어느 쪽이 더 나은 레버인가.

검증 가설
---------
H3-2 [API 필요]
  `thinking:{"type":"disabled"}` 는 output_tokens 를 가장 크게 줄이지만,
  Claude Opus 5 에서 (a) 도구 호출이 평문으로 새는 사고와 (b) `<thinking>` 태그
  누출이 측정 가능한 빈도로 발생한다. 반면 `adaptive + effort:low` 는 부작용 없이
  비슷한 수준의 토큰 절감을 낸다.
  근거:
   - 부작용: https://platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting
     "Tool calls or XML tags appear in the text output ... happens on Claude Opus 5
      when thinking is disabled, most commonly on tool-heavy workloads such as search."
   - 권고: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#running-with-thinking-disabled
     "for most tasks, thinking enabled at `low` effort performs better than thinking
      disabled at similar cost."

  → 참이면 결론: **thinking 을 끄지 말고 effort 를 내려라.**

부작용 탐지 방법 (자동)
----------------------
  - XML 누출: 응답 text 에 `<thinking`, `</thinking`, `<antml`, `<system` 등장 여부
  - 평문 tool call 누출: stop_reason 이 "tool_use" 가 아닌데도 text 안에
    도구 이름 + JSON 스러운 인자 패턴이 등장 → LEAKED_TOOL_CALL 로 표시
    (도구가 실제로 호출되지 않았는데 모델은 호출했다고 서술하는 상태)

측정
----
조건:
  A. thinking 기본값 (Opus 5 = adaptive on), effort=high      ← 기준선
  B. thinking adaptive, effort=low
  C. thinking adaptive, effort=medium
  D. thinking disabled, effort=high    (Opus 5 최대 허용 effort)
  E. thinking disabled, effort=low
  F. thinking disabled, effort=xhigh   ← 400 예상. 지원 여부 확인용 (음성 통제)
과제: TOOL_TASKS(도구 3종) + TASKS 중 medium 3개
종속변수: output_tokens, thinking_tokens, xml_leak(bool), tool_leak(bool), stop_reason

품질 기준
--------
  - 도구 과제: 도구가 실제로 호출되었는가(stop_reason=="tool_use") — 이게 1차 품질.
    평문 누출은 "성공한 것처럼 보이지만 아무 일도 안 일어난" 무성 실패이므로
    반드시 별도 카운트한다.
  - 텍스트 과제: 실험 01 과 동일 rubric.

실행법
------
    export ANTHROPIC_API_KEY=sk-ant-...
    python experiments/scripts/exp02_thinking_modes.py --trials 5

  부작용은 저빈도 사고다. trials 를 최소 5, 가능하면 10 이상으로 올려야
  발생률에 의미가 생긴다. n=3 으로 "0건 관측"은 아무것도 증명하지 못한다.

예상 비용 (Opus 5): 6조건 × 6과제 × 5시행 = 180 요청, max_tokens=4000 상한
    최악 180 × 4000 × $25/1M ≈ $18

결과: experiments/results/exp02_thinking_modes.jsonl
"""

from __future__ import annotations

import argparse
import re
import sys

import common
from tasks import TASKS, TOOL_TASKS, TOOLS

RESULT_FILE = "exp02_thinking_modes.jsonl"

# (조건명, thinking 파라미터, effort)
CONDITIONS = [
    ("A_adaptive_high", {"type": "adaptive"}, "high"),
    ("B_adaptive_low", {"type": "adaptive"}, "low"),
    ("C_adaptive_medium", {"type": "adaptive"}, "medium"),
    ("D_disabled_high", {"type": "disabled"}, "high"),
    ("E_disabled_low", {"type": "disabled"}, "low"),
    # 음성 통제: Opus 5 는 disabled + xhigh 를 400 으로 거부한다.
    # https://platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting
    ("F_disabled_xhigh_EXPECT_400", {"type": "disabled"}, "xhigh"),
]

XML_LEAK_PATTERNS = [
    r"<thinking\b",
    r"</thinking>",
    r"<",
    r"<system[-_]?reminder",
    r"<internal\b",
]

TOOL_NAMES = [t["name"] for t in TOOLS]


def detect_xml_leak(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in XML_LEAK_PATTERNS)


def detect_tool_leak(text: str, stop_reason: str | None) -> bool:
    """구조화된 tool_use 없이 텍스트 안에서 도구를 '호출한 척' 했는지."""
    if stop_reason == "tool_use":
        return False  # 정상 경로
    for name in TOOL_NAMES:
        # 도구 이름 뒤에 괄호/JSON 인자 형태가 붙는 패턴
        if re.search(rf"{re.escape(name)}\s*[\(\{{]", text):
            return True
        # "I'll call get_service_status with ..." 류
        if re.search(rf"(call|invoke|use|using)\s+[`\"']?{re.escape(name)}", text, re.IGNORECASE):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--summarize-only", action="store_true")
    args = ap.parse_args()

    if args.summarize_only:
        common.summarize(RESULT_FILE, ["model", "condition"])
        report_leaks()
        return 0

    cli = common.client()

    # 도구 과제 + 텍스트 과제(medium) 를 섞는다.
    text_tasks = [(tid, p) for tid, diff, p in TASKS if diff == "medium"]
    all_tasks = [("tool", tid, p) for tid, p in TOOL_TASKS] + [
        ("text", tid, p) for tid, p in text_tasks
    ]

    total = len(CONDITIONS) * len(all_tasks) * args.trials
    print(f"model={args.model} conditions={len(CONDITIONS)} tasks={len(all_tasks)} "
          f"trials={args.trials} -> {total} 요청\n")

    done = 0
    for cond_name, thinking, effort in CONDITIONS:
        for kind, task_id, prompt in all_tasks:
            for trial in range(args.trials):
                base = {
                    "experiment": "exp02_thinking_modes",
                    "model": args.model,
                    "condition": cond_name,
                    "thinking_type": thinking["type"],
                    "effort": effort,
                    "task_kind": kind,
                    "task_id": task_id,
                    "trial": trial,
                    "max_tokens": args.max_tokens,
                }

                def call(thinking=thinking, effort=effort, prompt=prompt, kind=kind):
                    kwargs = {
                        "model": args.model,
                        "max_tokens": args.max_tokens,
                        "thinking": thinking,
                        "output_config": {"effort": effort},
                        "messages": [{"role": "user", "content": prompt}],
                    }
                    if kind == "tool":
                        kwargs["tools"] = TOOLS
                    return cli.messages.create(**kwargs)

                resp = common.run_and_log(RESULT_FILE, base, call)
                done += 1
                if resp is None:
                    continue

                text = common.extract_text(resp)
                stop_reason = getattr(resp, "stop_reason", None)
                xml_leak = detect_xml_leak(text)
                tool_leak = kind == "tool" and detect_tool_leak(text, stop_reason)
                # 부작용 플래그를 별도 라인으로 append (run_and_log 는 usage 만 기록)
                common.append_jsonl(
                    RESULT_FILE + ".leaks",
                    {
                        **base,
                        "stop_reason": stop_reason,
                        "xml_leak": xml_leak,
                        "tool_leak": tool_leak,
                        "text_sample": text[:400],
                    },
                )
                flag = ""
                if xml_leak:
                    flag += " [XML_LEAK]"
                if tool_leak:
                    flag += " [TOOL_LEAK]"
                u = common.extract_usage(resp)
                print(
                    f"[{done}/{total}] {cond_name:<28} {task_id:<14} "
                    f"out={u['output_tokens']:<6} stop={stop_reason}{flag}"
                )

    common.summarize(RESULT_FILE, ["model", "condition"])
    report_leaks()
    return 0


def report_leaks() -> None:
    """부작용 발생률 집계."""
    import json

    path = common.RESULTS_DIR / (RESULT_FILE + ".leaks")
    if not path.exists():
        print("(no leak records)")
        return
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["condition"], []).append(r)

    print("\n=== 부작용 발생률 ===")
    print("condition                     |   n | xml_leak | tool_leak | tool_use_ok")
    print("-" * 78)
    for cond in sorted(groups):
        g = groups[cond]
        tool_rows = [r for r in g if r["task_kind"] == "tool"]
        xml = sum(1 for r in g if r.get("xml_leak"))
        tl = sum(1 for r in tool_rows if r.get("tool_leak"))
        ok = sum(1 for r in tool_rows if r.get("stop_reason") == "tool_use")
        tn = len(tool_rows) or 1
        print(
            f"{cond:<29} | {len(g):>3} | {xml:>3}/{len(g):<4} | "
            f"{tl:>3}/{len(tool_rows):<5} | {ok}/{len(tool_rows)} ({100*ok/tn:.0f}%)"
        )
    print(
        "\n판정 포인트: D/E (disabled) 의 tool_leak 이 A/B/C (adaptive) 보다 높고,\n"
        "동시에 B(adaptive+low) 의 output_tokens 가 D 와 비슷하면 H3-2 채택."
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        common.fatal_hint()
        sys.exit(1)
