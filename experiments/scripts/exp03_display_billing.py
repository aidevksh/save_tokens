"""
실험 03 — thinking.display 는 과금에 영향이 없다 (반증 시도).

검증 가설
---------
H3-3 [API 필요]
  `display:"omitted"` 와 `display:"summarized"` 의 `usage.output_tokens` 는
  통계적으로 구분되지 않는다. display 는 **지연(latency) 레버이지 비용 레버가 아니다.**
  근거 (문서가 명시적으로 그렇게 말한다):
   - "What you're billed for is the same regardless of the `display` setting;
      only what you see changes."
     https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost#pricing
   - "You're still charged for the full thinking tokens. Omitting reduces latency,
      not cost."
     https://platform.claude.com/docs/en/build-with-claude/thinking#controlling-thinking-display

  → 이 실험은 **문서를 믿지 않고 확인하는** 절차다. 문서와 계측이 어긋나면
    그게 더 중요한 발견이다. 어긋나지 않으면 "display 로 토큰 아끼려는 시도는
    무의미"를 확정하고 기법 목록에서 제외한다.

이 실험이 필요한 이유
--------------------
  display:"omitted" 는 응답 body 에서 thinking 텍스트가 사라지므로,
  응답 크기만 보고 "토큰이 줄었다"고 **오측정하기 쉽다**.
  이 실험은 그 함정을 명시적으로 기록으로 남긴다:
  visible_thinking_chars (응답에 실제로 담긴 thinking 문자 수) 와
  thinking_tokens (과금된 thinking 토큰) 을 나란히 기록한다.

측정
----
조건: display ∈ {summarized, omitted} × effort ∈ {high} × TASKS(hard 3개)
종속변수: output_tokens, thinking_tokens, visible_thinking_chars, latency_ms
  - output_tokens: 차이 없어야 함 (귀무가설)
  - visible_thinking_chars: omitted 에서 0 이어야 함
  - latency_ms: omitted 가 더 짧을 수 있음 (스트리밍 시 TTFT 이득이 주효과)

부수 조건: display 는 `thinking.type:"disabled"` 와 함께 쓰면 400.
  (문서: "`display` is invalid with `thinking.type: \"disabled\"`")
  음성 통제로 1회 확인한다.

실행법
------
    export ANTHROPIC_API_KEY=sk-ant-...
    python experiments/scripts/exp03_display_billing.py --trials 8

  thinking 토큰량은 시행마다 크게 변한다. 동일 조건 내 분산이 크므로
  trials 를 8 이상으로 두고 **조건 간 평균 차이가 조건 내 분산보다 작은지**를 본다.
  분산이 크면 "차이 없음"을 주장하기 어려우므로, 판정은 중앙값 + 사분위로 한다.

예상 비용 (Opus 5): 2조건 × 3과제 × 8시행 = 48 요청, max_tokens=8000
    최악 48 × 8000 × $25/1M ≈ $9.6

결과: experiments/results/exp03_display_billing.jsonl
"""

from __future__ import annotations

import argparse
import sys
import time

import common
from tasks import TASKS

RESULT_FILE = "exp03_display_billing.jsonl"


def visible_thinking_chars(response) -> int:
    total = 0
    for block in response.content:
        if getattr(block, "type", None) == "thinking":
            total += len(getattr(block, "thinking", "") or "")
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--summarize-only", action="store_true")
    args = ap.parse_args()

    if args.summarize_only:
        common.summarize(RESULT_FILE, ["model", "display"])
        return 0

    cli = common.client()
    tasks = [(tid, p) for tid, diff, p in TASKS if diff == "hard"]

    total = 2 * len(tasks) * args.trials
    print(f"model={args.model} effort={args.effort} tasks={len(tasks)} "
          f"trials={args.trials} -> {total} 요청\n")

    done = 0
    for display in ("summarized", "omitted"):
        for task_id, prompt in tasks:
            for trial in range(args.trials):
                base = {
                    "experiment": "exp03_display_billing",
                    "model": args.model,
                    "display": display,
                    "effort": args.effort,
                    "task_id": task_id,
                    "trial": trial,
                    "max_tokens": args.max_tokens,
                }

                t0 = time.perf_counter()

                def call(display=display, prompt=prompt):
                    return cli.messages.create(
                        model=args.model,
                        max_tokens=args.max_tokens,
                        thinking={"type": "adaptive", "display": display},
                        output_config={"effort": args.effort},
                        messages=[{"role": "user", "content": prompt}],
                    )

                resp = common.run_and_log(RESULT_FILE, base, call)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                done += 1
                if resp is None:
                    continue

                u = common.extract_usage(resp)
                common.append_jsonl(
                    RESULT_FILE + ".detail",
                    {
                        **base,
                        **u,
                        "latency_ms": round(elapsed_ms),
                        "visible_thinking_chars": visible_thinking_chars(resp),
                    },
                )
                print(
                    f"[{done}/{total}] display={display:<11} {task_id:<12} "
                    f"out={u['output_tokens']:<6} think_billed={u['thinking_tokens']:<6} "
                    f"think_visible_chars={visible_thinking_chars(resp):<6} "
                    f"{elapsed_ms:.0f}ms"
                )

    # 음성 통제: disabled + display 는 400 이어야 한다.
    print("\n--- 음성 통제: thinking disabled + display (400 예상) ---")
    common.run_and_log(
        RESULT_FILE,
        {
            "experiment": "exp03_display_billing",
            "model": args.model,
            "display": "NEGATIVE_CONTROL_disabled_plus_display",
            "effort": "high",
            "task_id": "control",
            "trial": 0,
        },
        lambda: cli.messages.create(
            model=args.model,
            max_tokens=512,
            thinking={"type": "disabled", "display": "summarized"},
            output_config={"effort": "high"},
            messages=[{"role": "user", "content": "Say OK."}],
        ),
    )

    common.summarize(RESULT_FILE, ["model", "display"])
    print(
        "\n판정 포인트:\n"
        "  - out_mean / think_mean 이 두 display 조건에서 사실상 동일 -> H3-3 채택\n"
        "  - visible_thinking_chars 는 omitted 에서 0 이어야 함\n"
        "  - 만약 out_mean 이 omitted 에서 유의하게 낮다면 문서와 배치 -> 재현 후 보고\n"
        "  - latency_ms 차이는 비용이 아니라 UX 이득으로 별도 기록"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        common.fatal_hint()
        sys.exit(1)
