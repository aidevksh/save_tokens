"""
실험 01 — effort 스윕: effort 가 출력 토큰을 얼마나 줄이는가.

검증 가설
---------
H3-1 [API 필요]
  effort 를 낮추면 `usage.output_tokens` 는 단조 감소한다. 그러나 감소분의
  대부분은 `thinking_tokens` 이고, Claude Opus 5 에서 visible(=output-thinking)
  토큰은 유의미하게 줄지 않는다.
  근거: "lowering effort can reduce thinking volume without reliably shortening
  the visible response"
  https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#response-length-and-verbosity

  → 이게 참이면, "출력 토큰 절감"을 목표로 할 때 effort 는 **thinking 절감 레버**이지
    **응답문 절감 레버가 아니다**. 응답문은 프롬프트로 줄여야 한다(실험 06).

측정
----
조건: effort ∈ {low, medium, high, xhigh, max} × TASKS(9개) × n_trials
종속변수: output_tokens, thinking_tokens, visible_tokens_approx, output_cost_usd
층화: difficulty(easy/medium/hard) 별로도 나눠 본다.

품질 기준 (별도 판정 에이전트가 수행)
------------------------------------
각 조건의 응답을 익명화해 쌍으로 제시하고, 과제별 rubric 으로 채점:
  - easy: 정답 여부 (binary)
  - medium: 핵심 논점 누락 개수
  - hard: 정답성 + 근거 타당성 (1-5)
토큰이 줄어도 품질이 유지되는 최저 effort 가 그 워크로드의 정답이다.

실행법
------
    export ANTHROPIC_API_KEY=sk-ant-...
    python experiments/scripts/exp01_effort_sweep.py
    # 특정 모델만:
    python experiments/scripts/exp01_effort_sweep.py --model claude-sonnet-5
    # 시행 횟수 조정 (기본 3):
    python experiments/scripts/exp01_effort_sweep.py --trials 5

예상 비용 (Opus 5, 기본 설정: 5 effort × 9 task × 3 trial = 135 요청)
    high/xhigh/max 구간에서 요청당 output 이 수천 토큰까지 갈 수 있다.
    max_tokens=8000 상한 기준 최악 135 × 8000 × $25/1M ≈ $27.
    먼저 --trials 1 --difficulty easy 로 감을 잡고 확대할 것.

결과: experiments/results/exp01_effort_sweep.jsonl
"""

from __future__ import annotations

import argparse
import sys

import common
from tasks import TASKS

RESULT_FILE = "exp01_effort_sweep.jsonl"

EFFORT_LEVELS = ["low", "medium", "high", "xhigh", "max"]

# effort 레벨 지원 모델. 출처:
# https://platform.claude.com/docs/en/build-with-claude/effort#effort-levels
EFFORT_SUPPORT = {
    "claude-opus-5": ["low", "medium", "high", "xhigh", "max"],
    "claude-fable-5": ["low", "medium", "high", "xhigh", "max"],
    "claude-opus-4-8": ["low", "medium", "high", "xhigh", "max"],
    "claude-opus-4-7": ["low", "medium", "high", "xhigh", "max"],
    "claude-sonnet-5": ["low", "medium", "high", "xhigh", "max"],
    "claude-sonnet-4-6": ["low", "medium", "high", "max"],  # xhigh 없음
    "claude-opus-4-6": ["low", "medium", "high", "max"],
    "claude-haiku-4-5": [],  # effort 미지원 -> 400
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument(
        "--difficulty",
        default="all",
        choices=["all", "easy", "medium", "hard"],
        help="난이도 층화 실행",
    )
    ap.add_argument(
        "--summarize-only",
        action="store_true",
        help="API 호출 없이 기존 jsonl 만 집계",
    )
    args = ap.parse_args()

    if args.summarize_only:
        common.summarize(RESULT_FILE, ["model", "effort"])
        common.summarize(RESULT_FILE, ["model", "difficulty", "effort"])
        return 0

    levels = EFFORT_SUPPORT.get(args.model, EFFORT_LEVELS)
    if not levels:
        print(f"{args.model} 은 effort 파라미터를 지원하지 않는다 (400 예상). 중단.")
        return 1

    tasks = [t for t in TASKS if args.difficulty in ("all", t[1])]
    cli = common.client()

    total = len(levels) * len(tasks) * args.trials
    print(f"model={args.model} levels={levels} tasks={len(tasks)} trials={args.trials}")
    print(f"총 요청 수: {total}\n")

    done = 0
    for effort in levels:
        for task_id, difficulty, prompt in tasks:
            for trial in range(args.trials):
                base = {
                    "experiment": "exp01_effort_sweep",
                    "model": args.model,
                    "effort": effort,
                    "task_id": task_id,
                    "difficulty": difficulty,
                    "trial": trial,
                    "max_tokens": args.max_tokens,
                    # 조건 간 유일한 차이가 effort 이도록 나머지는 전부 고정
                    "thinking": "default",
                }

                def call(effort=effort, prompt=prompt):
                    return cli.messages.create(
                        model=args.model,
                        max_tokens=args.max_tokens,
                        output_config={"effort": effort},
                        messages=[{"role": "user", "content": prompt}],
                    )

                resp = common.run_and_log(RESULT_FILE, base, call)
                done += 1
                if resp is not None:
                    u = common.extract_usage(resp)
                    print(
                        f"[{done}/{total}] {effort:<7} {task_id:<14} "
                        f"out={u['output_tokens']:<6} think={u['thinking_tokens']} "
                        f"vis={u['visible_tokens_approx']}"
                    )

    common.summarize(RESULT_FILE, ["model", "effort"])
    common.summarize(RESULT_FILE, ["model", "difficulty", "effort"])
    print(
        "\n판정 포인트: out_mean 이 낮은 effort 에서 줄어드는 폭 대비 "
        "vis_mean 이 얼마나 줄었는가.\n"
        "vis_mean 이 거의 평평하면 H3-1 채택 (effort 는 thinking 레버일 뿐)."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        common.fatal_hint()
        sys.exit(1)
