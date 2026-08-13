"""
축 3 실험 공용 유틸.

실행법:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...   # 또는 `ant auth login`
    python experiments/scripts/<실험>.py

이 파일 자체는 실행하지 않는다. 각 실험 스크립트가 import 한다.

측정 원칙
---------
- 절대 기준은 `usage.output_tokens` (thinking + tool_use + text 전부 포함, 과금 기준).
- `usage.output_tokens_details.thinking_tokens` 로 thinking 몫을 분리한다.
  (출처: https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost#pricing)
  visible_tokens = output_tokens - thinking_tokens (근사치).
- 결과는 experiments/results/*.jsonl 에 append. 덮어쓰지 않는다.
"""

from __future__ import annotations

import json
import pathlib
import time
import traceback
from typing import Any

# `anthropic` 는 client() 안에서 지연 import 한다.
# 그래야 SDK 미설치 환경에서도 --help / --summarize-only 가 동작한다.

RESULTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "results"

# 출력 토큰 단가 (USD / 1M tokens). 출처:
# https://platform.claude.com/docs/en/about-claude/pricing  (2026-08-13 확인)
OUTPUT_PRICE_PER_MTOK = {
    "claude-fable-5": 50.0,
    "claude-opus-5": 25.0,
    "claude-opus-4-8": 25.0,
    "claude-opus-4-7": 25.0,
    "claude-sonnet-5": 10.0,
    "claude-sonnet-4-6": 15.0,
    "claude-haiku-4-5": 5.0,
}
INPUT_PRICE_PER_MTOK = {
    "claude-fable-5": 10.0,
    "claude-opus-5": 5.0,
    "claude-opus-4-8": 5.0,
    "claude-opus-4-7": 5.0,
    "claude-sonnet-5": 2.0,
    "claude-sonnet-4-6": 3.0,
    "claude-haiku-4-5": 1.0,
}


def client() -> Any:
    """ANTHROPIC_API_KEY 또는 `ant auth login` 프로필에서 자격증명을 해석한다.

    지연 import: SDK 가 없어도 --help / --summarize-only 는 돌아가야 한다.
    """
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "anthropic SDK 가 없습니다.  pip install -U anthropic  후 다시 실행하세요."
        ) from exc
    return anthropic.Anthropic()


def extract_usage(response: Any) -> dict:
    """응답에서 토큰 사용량을 평평한 dict 로 뽑는다.

    thinking_tokens 는 thinking 이 없는 모델/턴에서는 필드 자체가 없을 수 있으므로
    getattr 로 방어한다.
    """
    u = response.usage
    details = getattr(u, "output_tokens_details", None)
    thinking = getattr(details, "thinking_tokens", None) if details else None
    out = getattr(u, "output_tokens", None)
    visible = (out - thinking) if (out is not None and thinking is not None) else None
    return {
        "input_tokens": getattr(u, "input_tokens", None),
        "output_tokens": out,
        "thinking_tokens": thinking,
        "visible_tokens_approx": visible,
        "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", None),
        "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", None),
    }


def extract_text(response: Any) -> str:
    """text 블록만 이어붙인다."""
    parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


def output_cost_usd(model: str, output_tokens: int | None) -> float | None:
    price = OUTPUT_PRICE_PER_MTOK.get(model)
    if price is None or output_tokens is None:
        return None
    return output_tokens * price / 1_000_000


def append_jsonl(filename: str, record: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    record.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    path = RESULTS_DIR / filename
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def record_error(filename: str, base: dict, exc: BaseException) -> None:
    """400 등 에러도 결과다 (모델별 파라미터 지원 여부 검증에 필요)."""
    rec = dict(base)
    rec["ok"] = False
    rec["error_type"] = type(exc).__name__
    rec["error_message"] = str(exc)[:1000]
    status = getattr(exc, "status_code", None)
    if status is not None:
        rec["status_code"] = status
    append_jsonl(filename, rec)


def summarize(filename: str, group_keys: list[str]) -> None:
    """jsonl 을 읽어 조건별 output_tokens 평균/중앙값을 표로 출력한다."""
    path = RESULTS_DIR / filename
    if not path.exists():
        print(f"(no results at {path})")
        return
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows = [r for r in rows if r.get("ok") and r.get("output_tokens") is not None]
    if not rows:
        print("(no successful rows)")
        return

    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        key = tuple(str(r.get(k)) for k in group_keys)
        groups.setdefault(key, []).append(r)

    def _median(xs: list[float]) -> float:
        xs = sorted(xs)
        n = len(xs)
        return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2

    print(f"\n=== {filename} (n_rows={len(rows)}) ===")
    header = " | ".join(group_keys) + " | n | out_mean | out_median | think_mean | vis_mean"
    print(header)
    print("-" * len(header))
    baseline = None
    for key in sorted(groups):
        g = groups[key]
        outs = [r["output_tokens"] for r in g]
        thinks = [r["thinking_tokens"] for r in g if r.get("thinking_tokens") is not None]
        viss = [r["visible_tokens_approx"] for r in g if r.get("visible_tokens_approx") is not None]
        mean_out = sum(outs) / len(outs)
        if baseline is None:
            baseline = mean_out
        print(
            f"{' | '.join(key)} | {len(g)} | {mean_out:.0f} | {_median(outs):.0f} | "
            f"{(sum(thinks)/len(thinks)) if thinks else float('nan'):.0f} | "
            f"{(sum(viss)/len(viss)) if viss else float('nan'):.0f}"
        )
    print(
        "\n주의: 상대 비율만 보고할 것. 조건 간 과제/언어 구성을 고정했는지 확인."
    )


def run_and_log(
    filename: str,
    base_record: dict,
    call,
) -> Any | None:
    """call() 을 실행하고 usage 를 jsonl 에 append. 실패해도 기록하고 None 반환."""
    try:
        resp = call()
    except Exception as exc:  # noqa: BLE001 - 400 도 데이터다
        record_error(filename, base_record, exc)
        print(f"  ! {base_record} -> {type(exc).__name__}: {str(exc)[:160]}")
        return None
    rec = dict(base_record)
    rec["ok"] = True
    rec.update(extract_usage(resp))
    rec["stop_reason"] = getattr(resp, "stop_reason", None)
    rec["output_cost_usd"] = output_cost_usd(rec.get("model", ""), rec.get("output_tokens"))
    append_jsonl(filename, rec)
    return resp


def fatal_hint() -> None:
    print(
        "\n실행 실패 시 확인:\n"
        "  1) ANTHROPIC_API_KEY 설정 또는 `ant auth status`\n"
        "  2) pip install -U anthropic\n"
        "  3) 모델 접근 권한 (Fable 5 는 30일 데이터 보존 필요)\n"
    )
    traceback.print_exc()
