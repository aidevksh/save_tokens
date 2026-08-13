"""
실험 05 — 모델 티어별 출력 길이 성향 × 단가: 라우팅으로 얼마나 절감되는가.

검증 가설
---------
H3-6 [API 필요] / [proxy 검증 가능]
  동일 과제·동일 프롬프트에서 모델별 `output_tokens` 는 다르며, 그 차이는
  단가 차이와 **같은 방향이 아니다**. 즉 비용 = tokens × price 이므로
  "싼 모델이 항상 싸다"가 자명하지 않다.
  구체적으로: Claude Opus 5 는 기본 응답이 이전 Opus 보다 길다
  ("Claude Opus 5's default user-facing responses run longer than prior Opus models'")
  https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#response-length-and-verbosity
  → 단가 5배 차이(Opus 5 $25 vs Haiku 4.5 $5)에 출력 길이 배수가 곱해진다.
    실측 비용비를 구해야 라우팅 손익분기가 나온다.

  proxy 대체 측정: API 없이도 naive 서브에이전트에 동일 과제를 주고
  산출물의 문자 수를 비교하면 **상대 길이 성향**은 근사할 수 있다.
  단 토큰화기가 모델군마다 다르므로(4.7 이후 tokenizer 는 같은 텍스트에 약 30% 더 많은
  토큰을 낸다: https://platform.claude.com/docs/en/about-claude/pricing) 문자→토큰
  환산은 하지 말 것. 이 스크립트가 절대 기준이다.

측정
----
조건: model ∈ {opus-5, sonnet-5, haiku-4-5} × TASKS(9개) × trials
  - Haiku 4.5 는 effort/adaptive thinking 미지원 → 파라미터를 빼고 호출한다.
    (문서 표: Haiku 4.5 = Extended only, `"adaptive"` 는 400)
  - Opus 5 / Sonnet 5 는 effort 를 맞춰 비교한다 (기본 high). 공정성을 위해
    --effort low 로도 한 번 더 돌려 라우팅 실무 조건을 재현한다.
종속변수: output_tokens, output_cost_usd, (thinking_tokens)
파생: 모델 간 tokens 비, cost 비, 손익분기 지점

품질 기준
--------
  판정 에이전트가 동일 과제의 3모델 응답을 익명·무작위 순서로 받아
  과제별 rubric 으로 채점한다. "Haiku 로 충분한 과제"의 경계를 찾는 것이 목적이며,
  난이도(easy/medium/hard)별로 그 경계가 다를 것으로 예상한다.

실행법
------
    export ANTHROPIC_API_KEY=sk-ant-...
    python experiments/scripts/exp05_model_tier.py --trials 3
    python experiments/scripts/exp05_model_tier.py --trials 3 --effort low

예상 비용: 3모델 × 9과제 × 3시행 = 81 요청. Opus 5 몫이 지배적, 대략 $5 이내.

결과: experiments/results/exp05_model_tier.jsonl
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

import common
from tasks import TASKS

RESULT_FILE = "exp05_model_tier.jsonl"

DEFAULT_MODELS = ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"]

# effort / adaptive thinking 미지원 모델 (문서 per-model 표 기준)
NO_EFFORT = {"claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"}
NO_ADAPTIVE = {"claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--summarize-only", action="store_true")
    args = ap.parse_args()

    if args.summarize_only:
        common.summarize(RESULT_FILE, ["model", "effort_applied"])
        cost_table()
        return 0

    cli = common.client()
    total = len(args.models) * len(TASKS) * args.trials
    print(f"models={args.models} tasks={len(TASKS)} trials={args.trials} -> {total} 요청\n")

    done = 0
    for model in args.models:
        supports_effort = model not in NO_EFFORT
        for task_id, difficulty, prompt in TASKS:
            for trial in range(args.trials):
                base = {
                    "experiment": "exp05_model_tier",
                    "model": model,
                    "effort_applied": args.effort if supports_effort else "n/a",
                    "task_id": task_id,
                    "difficulty": difficulty,
                    "trial": trial,
                    "max_tokens": args.max_tokens,
                }

                def call(model=model, prompt=prompt, supports_effort=supports_effort):
                    kwargs = {
                        "model": model,
                        "max_tokens": args.max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                    if supports_effort:
                        kwargs["output_config"] = {"effort": args.effort}
                    # Haiku 4.5 등은 adaptive 미지원. thinking 파라미터를 아예 안 보낸다.
                    return cli.messages.create(**kwargs)

                resp = common.run_and_log(RESULT_FILE, base, call)
                done += 1
                if resp is not None:
                    u = common.extract_usage(resp)
                    cost = common.output_cost_usd(model, u["output_tokens"])
                    print(
                        f"[{done}/{total}] {model:<20} {task_id:<14} "
                        f"out={u['output_tokens']:<6} ${cost:.5f}"
                    )

    common.summarize(RESULT_FILE, ["model", "difficulty"])
    cost_table()
    return 0


def cost_table() -> None:
    """모델별 평균 출력 토큰·평균 비용·상대비를 낸다."""
    import json

    path = common.RESULTS_DIR / RESULT_FILE
    if not path.exists():
        print("(no results)")
        return
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("ok") and r.get("output_tokens")]
    if not rows:
        return

    agg = defaultdict(lambda: {"out": [], "cost": []})
    for r in rows:
        k = (r["model"], r.get("difficulty", "?"))
        agg[k]["out"].append(r["output_tokens"])
        agg[k]["cost"].append(r.get("output_cost_usd") or 0.0)

    print("\n=== 모델 × 난이도: 출력 토큰과 출력 비용 ===")
    print("model                | diff   |   n | out_mean | $/req(out) | $/1M out")
    print("-" * 78)
    for (model, diff) in sorted(agg):
        d = agg[(model, diff)]
        n = len(d["out"])
        print(
            f"{model:<20} | {diff:<6} | {n:>3} | {sum(d['out'])/n:>8.0f} | "
            f"{sum(d['cost'])/n:>10.5f} | "
            f"{common.OUTPUT_PRICE_PER_MTOK.get(model, float('nan')):>8.2f}"
        )
    print(
        "\n판정 포인트:\n"
        "  단가비(Opus5:Sonnet5:Haiku = 25:10:5 = 5:2:1) 와\n"
        "  실측 출력토큰비를 곱한 것이 진짜 비용비다.\n"
        "  Opus 5 가 Haiku 보다 토큰을 2배 쓴다면 실질 비용비는 10:2:1 이 된다.\n"
        "  난이도별로 품질이 유지되는 최저 티어를 찾으면 그게 라우팅 규칙."
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        common.fatal_hint()
        sys.exit(1)
