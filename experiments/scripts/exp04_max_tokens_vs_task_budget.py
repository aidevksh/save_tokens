"""
실험 04 — max_tokens(하드캡, 모델 비인지) vs task_budget(어드바이저리, 모델 인지).

검증 가설
---------
H3-4 [API 필요]
  `max_tokens` 를 낮추면 output_tokens 는 확실히 내려가지만, 그 절감의 상당 비율이
  `stop_reason == "max_tokens"` (=잘림) 으로 얻어진 것이다. 즉 max_tokens 는
  **절감 기법이 아니라 손실 기법**이다. 모델이 값을 인지하지 못하므로
  마무리 문장을 만들지 못하고 문장 중간에서 끊긴다.
  근거: "Note that our models may stop before reaching this maximum. This parameter
  only specifies the absolute maximum number of tokens to generate."
  https://platform.claude.com/docs/en/api/messages/create
  그리고 thinking 이 max_tokens 를 잠식한다:
  https://platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting#stopped-at-max-tokens

H3-5 [API 필요]
  같은 토큰 예산을 `task_budget` 으로 주면 (모델이 카운트다운을 봄) 에이전트 루프
  총 출력 토큰이 무제한 조건보다 감소하되, 잘림 없이 `end_turn` 으로 종료한다.
  즉 **동일 예산에서 완결률이 높다.**
  근거: "Claude sees a budget-countdown marker injected server-side ... uses it to
  pace itself and finish gracefully"
  https://platform.claude.com/docs/en/build-with-claude/task-budgets

  단, task_budget 은 하드캡이 아니다("soft hint, not a hard cap") 이므로
  예산 초과 사례도 카운트한다.

중요한 지원 제약 (문서 확인, 캐시된 표와 불일치 주의)
----------------------------------------------------
  task_budget 지원: Opus 5, Fable 5, Mythos 5, Opus 4.8, Opus 4.7
  **Sonnet 5 는 미지원** (문서 Feature support 표에 "Not supported")
  최소 total = 20,000 토큰. 미만이면 400.
  beta header: task-budgets-2026-03-13
  스트리밍 권장 (큰 max_tokens 로 HTTP 타임아웃 회피)

측정
----
Part A (max_tokens 하드캡):
  조건: max_tokens ∈ {512, 1024, 2048, 4096, 16000} × TASKS(medium+hard 6개)
  종속변수: output_tokens, stop_reason, truncated(bool), 문장완결성
  → "절감률" 옆에 반드시 truncation_rate 를 병기한다. 이게 이 실험의 핵심.

Part B (task_budget, 에이전트 루프):
  조건: task_budget ∈ {없음, 20000, 40000, 80000} × TOOL_TASKS
  루프: tool_use 가 나오면 스텁 결과를 돌려주고 end_turn 까지 반복 (최대 12턴)
  종속변수: 루프 전체 누적 output_tokens, 턴 수, 최종 stop_reason, 완결 여부

품질 기준
--------
  - Part A: 응답이 문장/코드블록 중간에서 끊겼는가 (자동: stop_reason + 말미 문자)
            + 판정 에이전트가 "사용 가능한 답변인가" 이진 판정
  - Part B: 과제가 실제로 완료되었는가 (도구를 필요한 만큼 호출하고 결론을 냈는가)

실행법
------
    export ANTHROPIC_API_KEY=sk-ant-...
    python experiments/scripts/exp04_max_tokens_vs_task_budget.py --part A
    python experiments/scripts/exp04_max_tokens_vs_task_budget.py --part B
    python experiments/scripts/exp04_max_tokens_vs_task_budget.py --part both

예상 비용 (Opus 5): Part A 5×6×3=90 요청(대부분 상한에서 끊김) ≈ $6
                    Part B 4×3×3=36 루프 × 최대 12턴 ≈ $30+ (루프라 비쌈)
    Part B 는 --trials 1 로 먼저 돌릴 것.

결과: experiments/results/exp04_max_tokens.jsonl,
      experiments/results/exp04_task_budget.jsonl
"""

from __future__ import annotations

import argparse
import sys

import common
from tasks import TASKS, TOOL_TASKS, TOOLS, fake_tool_result

RESULT_A = "exp04_max_tokens.jsonl"
RESULT_B = "exp04_task_budget.jsonl"

MAX_TOKENS_LEVELS = [512, 1024, 2048, 4096, 16000]
TASK_BUDGETS = [None, 20_000, 40_000, 80_000]  # 20k 가 문서상 최소값
TASK_BUDGET_BETA = "task-budgets-2026-03-13"

# task_budget 지원 모델. 출처:
# https://platform.claude.com/docs/en/build-with-claude/task-budgets#feature-support
TASK_BUDGET_MODELS = {
    "claude-opus-5",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
}


def looks_truncated(text: str, stop_reason: str | None) -> bool:
    if stop_reason == "max_tokens":
        return True
    if not text:
        return False
    tail = text.rstrip()
    # 종결부호 없이 끝나면 잘림 의심
    return bool(tail) and tail[-1] not in ".!?\"')`}]:\n"


def part_a(args, cli) -> None:
    tasks = [(tid, p) for tid, diff, p in TASKS if diff in ("medium", "hard")]
    total = len(MAX_TOKENS_LEVELS) * len(tasks) * args.trials
    print(f"\n### Part A: max_tokens 하드캡 ({total} 요청)\n")
    done = 0
    for mt in MAX_TOKENS_LEVELS:
        for task_id, prompt in tasks:
            for trial in range(args.trials):
                base = {
                    "experiment": "exp04_max_tokens",
                    "model": args.model,
                    "max_tokens": mt,
                    "effort": args.effort,
                    "task_id": task_id,
                    "trial": trial,
                }

                def call(mt=mt, prompt=prompt):
                    return cli.messages.create(
                        model=args.model,
                        max_tokens=mt,
                        output_config={"effort": args.effort},
                        messages=[{"role": "user", "content": prompt}],
                    )

                resp = common.run_and_log(RESULT_A, base, call)
                done += 1
                if resp is None:
                    continue
                text = common.extract_text(resp)
                sr = getattr(resp, "stop_reason", None)
                trunc = looks_truncated(text, sr)
                u = common.extract_usage(resp)
                common.append_jsonl(
                    RESULT_A + ".detail",
                    {
                        **base,
                        **u,
                        "stop_reason": sr,
                        "truncated": trunc,
                        "text_len_chars": len(text),
                        "text_tail": text[-200:],
                    },
                )
                print(
                    f"[{done}/{total}] max_tokens={mt:<6} {task_id:<12} "
                    f"out={u['output_tokens']:<6} stop={sr:<12} "
                    f"{'TRUNCATED' if trunc else ''}"
                )

    common.summarize(RESULT_A, ["model", "max_tokens"])
    report_truncation()


def report_truncation() -> None:
    import json

    path = common.RESULTS_DIR / (RESULT_A + ".detail")
    if not path.exists():
        return
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    groups: dict[int, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["max_tokens"], []).append(r)
    print("\n=== max_tokens 별 잘림률 ===")
    print("max_tokens |   n | out_mean | stop=max_tokens | truncated_heuristic")
    print("-" * 70)
    for mt in sorted(groups):
        g = groups[mt]
        outs = [r["output_tokens"] for r in g if r.get("output_tokens")]
        hit = sum(1 for r in g if r.get("stop_reason") == "max_tokens")
        tr = sum(1 for r in g if r.get("truncated"))
        n = len(g)
        print(
            f"{mt:>10} | {n:>3} | {(sum(outs)/len(outs) if outs else 0):>8.0f} | "
            f"{hit:>3}/{n} ({100*hit/n:>3.0f}%) | {tr}/{n} ({100*tr/n:.0f}%)"
        )
    print(
        "\n판정 포인트: max_tokens 를 내려서 얻은 out_mean 감소분 중\n"
        "stop=max_tokens 비율이 높다면 그건 절감이 아니라 잘림이다 -> H3-4 채택."
    )


def part_b(args, cli) -> None:
    if args.model not in TASK_BUDGET_MODELS:
        print(
            f"\n!! {args.model} 은 task_budget 미지원 (문서 Feature support 표).\n"
            f"   지원 모델: {sorted(TASK_BUDGET_MODELS)}\n"
            f"   음성 통제로 1회만 호출해 400 을 기록한다."
        )
        common.run_and_log(
            RESULT_B,
            {
                "experiment": "exp04_task_budget",
                "model": args.model,
                "task_budget": 20_000,
                "task_id": "NEGATIVE_CONTROL_unsupported_model",
                "trial": 0,
            },
            lambda: cli.beta.messages.create(
                model=args.model,
                max_tokens=4096,
                output_config={"effort": args.effort,
                               "task_budget": {"type": "tokens", "total": 20_000}},
                betas=[TASK_BUDGET_BETA],
                messages=[{"role": "user", "content": "Say OK."}],
            ),
        )
        return

    total = len(TASK_BUDGETS) * len(TOOL_TASKS) * args.trials
    print(f"\n### Part B: task_budget 에이전트 루프 ({total} 루프)\n")
    done = 0
    for budget in TASK_BUDGETS:
        for task_id, prompt in TOOL_TASKS:
            for trial in range(args.trials):
                done += 1
                label = str(budget) if budget else "none"
                res = run_agent_loop(
                    cli, args, prompt, budget, max_turns=args.max_turns
                )
                rec = {
                    "experiment": "exp04_task_budget",
                    "model": args.model,
                    "task_budget": budget,
                    "effort": args.effort,
                    "task_id": task_id,
                    "trial": trial,
                    "ok": res["ok"],
                    **res,
                }
                common.append_jsonl(RESULT_B, rec)
                print(
                    f"[{done}/{total}] budget={label:<7} {task_id:<12} "
                    f"turns={res['turns']:<3} total_out={res['output_tokens']:<7} "
                    f"final_stop={res['final_stop_reason']} "
                    f"{'OVER_BUDGET' if res.get('over_budget') else ''}"
                )

    common.summarize(RESULT_B, ["model", "task_budget"])
    print(
        "\n판정 포인트:\n"
        "  - budget 이 낮을수록 누적 output_tokens 가 감소하는가\n"
        "  - 그러면서도 final_stop_reason 이 end_turn 을 유지하는가 (잘리지 않음)\n"
        "  - over_budget 비율 (task_budget 은 하드캡이 아님)\n"
        "  둘 다 참이면 H3-5 채택: task_budget 은 max_tokens 와 달리 '손실 없는' 레버."
    )


def run_agent_loop(cli, args, prompt: str, budget: int | None, max_turns: int) -> dict:
    """tool_use 를 스텁으로 처리하며 end_turn 까지 루프. 누적 usage 를 반환."""
    messages: list[dict] = [{"role": "user", "content": prompt}]
    total_out = 0
    total_in = 0
    total_think = 0
    turns = 0
    final_stop = None

    output_config: dict = {"effort": args.effort}
    kwargs_extra: dict = {}
    if budget is not None:
        output_config["task_budget"] = {"type": "tokens", "total": budget}
        kwargs_extra["betas"] = [TASK_BUDGET_BETA]

    try:
        for _ in range(max_turns):
            turns += 1
            create = cli.beta.messages.create if budget is not None else cli.messages.create
            resp = create(
                model=args.model,
                max_tokens=args.max_tokens,
                output_config=output_config,
                messages=messages,
                tools=TOOLS,
                **kwargs_extra,
            )
            u = common.extract_usage(resp)
            total_out += u["output_tokens"] or 0
            total_in += u["input_tokens"] or 0
            total_think += u["thinking_tokens"] or 0
            final_stop = getattr(resp, "stop_reason", None)

            if final_stop != "tool_use":
                break

            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if getattr(block, "type", None) == "tool_use":
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": fake_tool_result(block.name, block.input),
                        }
                    )
            if not results:
                break
            messages.append({"role": "user", "content": results})
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "turns": turns,
            "output_tokens": total_out,
            "input_tokens": total_in,
            "thinking_tokens": total_think,
            "final_stop_reason": "ERROR",
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:500],
        }

    return {
        "ok": True,
        "turns": turns,
        "output_tokens": total_out,
        "input_tokens": total_in,
        "thinking_tokens": total_think,
        "final_stop_reason": final_stop,
        "over_budget": bool(budget and total_out > budget),
        "output_cost_usd": common.output_cost_usd(args.model, total_out),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--max-tokens", type=int, default=16000,
                    help="Part B 루프의 요청당 상한")
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--part", default="both", choices=["A", "B", "both"])
    ap.add_argument("--summarize-only", action="store_true")
    args = ap.parse_args()

    if args.summarize_only:
        common.summarize(RESULT_A, ["model", "max_tokens"])
        report_truncation()
        common.summarize(RESULT_B, ["model", "task_budget"])
        return 0

    cli = common.client()
    if args.part in ("A", "both"):
        part_a(args, cli)
    if args.part in ("B", "both"):
        part_b(args, cli)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        common.fatal_hint()
        sys.exit(1)
