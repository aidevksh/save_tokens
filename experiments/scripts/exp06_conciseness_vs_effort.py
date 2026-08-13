"""
실험 06 — 간결성 프롬프트 vs effort: 응답문(visible) 길이를 줄이는 진짜 레버는 무엇인가.

검증 가설
---------
H3-7 [API 필요] / [proxy 검증 가능]
  Claude Opus 5 에서 **visible 출력 토큰**을 줄이는 데는 effort 하향보다
  간결성 시스템 프롬프트가 더 효과적이다. effort 는 thinking 토큰을 줄인다.
  둘은 서로 다른 토큰 풀을 건드리므로 **가산적(additive)** 이어야 한다.
  근거: "The effort parameter controls how much the model thinks rather than how
  much it says: lowering effort can reduce thinking volume without reliably
  shortening the visible response. To control response length, prompt for it explicitly."
  https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#response-length-and-verbosity

  → 참이면 축 1(프롬프트) 과 축 3(파라미터) 은 경쟁 관계가 아니라 **곱해서 쓰는**
    직교 레버다. 이게 이 실험의 실무적 결론.

측정 (2×3 요인설계)
------------------
  요인 1 — 시스템 프롬프트: {none, concise}
    concise 는 공식 문서가 제시한 문구를 그대로 쓴다 (자작 문구로 바꾸지 말 것.
    출처 문구를 쓰는 것이 재현 가능성의 조건):
      "Keep responses focused, brief, and concise. Keep disclaimers and caveats
       short, and spend most of the response on the main answer. When asked to
       explain something, give a high-level summary unless an in-depth explanation
       is specifically requested."
  요인 2 — effort: {low, medium, high}

  종속변수를 반드시 **분해**해서 본다:
    - output_tokens        (총 과금)
    - thinking_tokens      (effort 가 움직여야 하는 값)
    - visible_tokens_approx(프롬프트가 움직여야 하는 값)

  기대 패턴 (H3-7 이 참일 때):
    thinking_tokens : effort 에 따라 크게 변함, 프롬프트에 거의 무반응
    visible_tokens  : 프롬프트에 따라 크게 변함, effort 에 거의 무반응
    output_tokens   : 두 효과의 합. concise + low 조합이 최저.

품질 기준
--------
  간결성 프롬프트가 정보를 잘라먹었는지 확인해야 한다. 판정 에이전트가
  각 응답에 대해 과제별 "필수 논점 체크리스트"를 채점한다.
  토큰이 40% 줄었는데 필수 논점 2/5 가 빠졌다면 절감이 아니라 품질 저하다.

proxy 대체 (API 없이)
--------------------
  이 실험의 요인 1(프롬프트) 만은 naive 서브에이전트로 대리 검증 가능하다.
  프로토콜은 research/03-api-parameters.md §4.2 참조. 요인 2(effort) 는 불가.

실행법
------
    export ANTHROPIC_API_KEY=sk-ant-...
    python experiments/scripts/exp06_conciseness_vs_effort.py --trials 4

예상 비용 (Opus 5): 2 × 3 × 6과제 × 4시행 = 144 요청, max_tokens=8000 ≈ $10 이내

결과: experiments/results/exp06_conciseness_vs_effort.jsonl
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

import common
from tasks import TASKS

RESULT_FILE = "exp06_conciseness_vs_effort.jsonl"

# 출처: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
# 문구를 임의로 바꾸지 말 것. 바꾸면 다른 실험이 된다.
CONCISE_SYSTEM = (
    "Keep responses focused, brief, and concise. Keep disclaimers and caveats "
    "short, and spend most of the response on the main answer. When asked to "
    "explain something, give a high-level summary unless an in-depth explanation "
    "is specifically requested."
)

PROMPT_CONDITIONS = [("none", None), ("concise", CONCISE_SYSTEM)]
EFFORT_CONDITIONS = ["low", "medium", "high"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--trials", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--summarize-only", action="store_true")
    args = ap.parse_args()

    if args.summarize_only:
        factorial_table()
        return 0

    cli = common.client()
    # medium + hard 만 사용. easy 과제는 원래 짧아서 효과가 안 보인다.
    tasks = [(tid, d, p) for tid, d, p in TASKS if d in ("medium", "hard")]

    total = len(PROMPT_CONDITIONS) * len(EFFORT_CONDITIONS) * len(tasks) * args.trials
    print(f"model={args.model} 2x{len(EFFORT_CONDITIONS)} 요인 × {len(tasks)}과제 "
          f"× {args.trials}시행 -> {total} 요청\n")

    done = 0
    for prompt_name, system in PROMPT_CONDITIONS:
        for effort in EFFORT_CONDITIONS:
            for task_id, difficulty, prompt in tasks:
                for trial in range(args.trials):
                    base = {
                        "experiment": "exp06_conciseness_vs_effort",
                        "model": args.model,
                        "system_condition": prompt_name,
                        "effort": effort,
                        "task_id": task_id,
                        "difficulty": difficulty,
                        "trial": trial,
                        "max_tokens": args.max_tokens,
                    }

                    def call(system=system, effort=effort, prompt=prompt):
                        kwargs = {
                            "model": args.model,
                            "max_tokens": args.max_tokens,
                            "output_config": {"effort": effort},
                            "messages": [{"role": "user", "content": prompt}],
                        }
                        if system is not None:
                            kwargs["system"] = system
                        return cli.messages.create(**kwargs)

                    resp = common.run_and_log(RESULT_FILE, base, call)
                    done += 1
                    if resp is None:
                        continue
                    u = common.extract_usage(resp)
                    text = common.extract_text(resp)
                    common.append_jsonl(
                        RESULT_FILE + ".detail",
                        {**base, **u, "text_len_chars": len(text), "text": text},
                    )
                    print(
                        f"[{done}/{total}] sys={prompt_name:<8} effort={effort:<7} "
                        f"{task_id:<12} out={u['output_tokens']:<6} "
                        f"think={u['thinking_tokens']} vis={u['visible_tokens_approx']}"
                    )

    factorial_table()
    return 0


def factorial_table() -> None:
    import json

    path = common.RESULTS_DIR / RESULT_FILE
    if not path.exists():
        print("(no results)")
        return
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("ok") and r.get("output_tokens")]
    if not rows:
        return

    agg = defaultdict(lambda: {"out": [], "think": [], "vis": []})
    for r in rows:
        k = (r["system_condition"], r["effort"])
        agg[k]["out"].append(r["output_tokens"])
        if r.get("thinking_tokens") is not None:
            agg[k]["think"].append(r["thinking_tokens"])
        if r.get("visible_tokens_approx") is not None:
            agg[k]["vis"].append(r["visible_tokens_approx"])

    def m(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    print("\n=== 2×3 요인표 (평균 토큰) ===")
    print("system   | effort  |   n | output | thinking | visible")
    print("-" * 62)
    baseline = None
    for key in sorted(agg):
        d = agg[key]
        n = len(d["out"])
        if key == ("none", "high"):
            baseline = m(d["out"])
        print(
            f"{key[0]:<8} | {key[1]:<7} | {n:>3} | {m(d['out']):>6.0f} | "
            f"{m(d['think']):>8.0f} | {m(d['vis']):>7.0f}"
        )

    if baseline:
        print(f"\n기준선 = (system=none, effort=high) output {baseline:.0f} 토큰")
        for key in sorted(agg):
            v = m(agg[key]["out"])
            print(f"  {key[0]:<8} × {key[1]:<7} : {100*(1-v/baseline):+.1f}% (상대)")
    print(
        "\n판정 포인트:\n"
        "  1) effort 열을 따라 thinking 은 크게 변하고 visible 은 평평한가?\n"
        "  2) system 행을 따라 visible 은 크게 변하고 thinking 은 평평한가?\n"
        "  둘 다 참이면 H3-7 채택: 두 레버는 직교하며 함께 써야 한다.\n"
        "  ※ 절감률 보고 전에 품질 채점을 먼저 붙일 것. 수치만 보고 채택 금지."
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        common.fatal_hint()
        sys.exit(1)
