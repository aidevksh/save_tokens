"""
축 3 실험용 고정 과제 세트.

설계 원칙
---------
- 조건 간 **과제를 고정**한다. 파라미터만 바꾼다.
- 언어를 고정한다(전부 영어). 한국어/영어 혼합은 문자↔토큰 비율을 깨뜨린다.
- 난이도 3단계로 나눈다. effort 의 효과는 난이도에 따라 다르므로 층화해서 봐야 한다.
- 각 과제는 "출력 길이가 모델 재량에 달린" 열린 과제여야 한다.
  정답 길이가 고정된 과제(예: "2+2는?")는 effort 차이를 드러내지 못한다.
"""

from __future__ import annotations

# (task_id, difficulty, prompt)
TASKS: list[tuple[str, str, str]] = [
    # --- easy: 단순 추출/분류. 절감 여지가 가장 큰 구간 ---
    (
        "easy_classify",
        "easy",
        "Classify the sentiment of this review as positive, negative, or neutral: "
        "\"The battery lasts about a day, which is fine, but the charging cable "
        "broke after two weeks and support never replied.\"",
    ),
    (
        "easy_extract",
        "easy",
        "Extract the company name, the funding round, and the amount from this text: "
        "\"Helio Systems, a Boston-based grid-analytics startup, closed a $42 million "
        "Series B led by Ardent Capital, with participation from existing investors.\"",
    ),
    (
        "easy_rewrite",
        "easy",
        "Rewrite this sentence so a non-technical reader can understand it: "
        "\"The service degrades gracefully under partial partition by falling back "
        "to eventually-consistent reads from the nearest replica.\"",
    ),
    # --- medium: 설명/분석. 기본 verbosity 성향이 드러나는 구간 ---
    (
        "med_explain",
        "medium",
        "Explain the trade-offs between optimistic and pessimistic concurrency control "
        "for a multi-tenant SaaS database.",
    ),
    (
        "med_debug",
        "medium",
        "A Python service intermittently returns stale data after a deploy. The read "
        "path is: client -> CDN -> nginx -> gunicorn -> Redis cache -> Postgres. "
        "List the most likely causes in order of probability and how you would "
        "distinguish them.",
    ),
    (
        "med_design",
        "medium",
        "Design the data model for a feature-flag service that supports percentage "
        "rollouts, per-user overrides, and audit history. Describe the tables and "
        "the read path.",
    ),
    # --- hard: 다단계 추론. 낮은 effort 에서 품질 저하가 나타나는지 보는 구간 ---
    (
        "hard_algo",
        "hard",
        "Given a stream of integers, design a data structure that supports insert(x), "
        "delete(x), and median() in better than O(n) per operation. Prove the "
        "complexity of each operation and describe the failure modes of your approach.",
    ),
    (
        "hard_reason",
        "hard",
        "Three servers each report a different value for the same replicated counter: "
        "A=17, B=17, C=14. The replication protocol is quorum-based with W=2, R=2, and "
        "clocks are not synchronized. Enumerate every sequence of events that could "
        "produce this state, and say which ones represent data loss.",
    ),
    (
        "hard_review",
        "hard",
        "Review this function for correctness bugs:\n\n"
        "def dedupe_by_key(rows, key):\n"
        "    seen = {}\n"
        "    for r in rows:\n"
        "        k = r.get(key)\n"
        "        if k not in seen:\n"
        "            seen[k] = r\n"
        "        elif r['updated_at'] > seen[k]['updated_at']:\n"
        "            seen[k] = r\n"
        "    return list(seen.values())\n\n"
        "Assume rows may be missing 'updated_at', keys may be unhashable, and the "
        "caller depends on input order being preserved.",
    ),
]

# 도구 호출이 필요한 과제. effort 가 tool call 횟수에 미치는 영향, 그리고
# Opus 5 thinking-disabled 의 "평문 tool call 누출" 부작용을 유도하기 위한 세트.
TOOL_TASKS: list[tuple[str, str]] = [
    (
        "tool_lookup",
        "What is the current status of the payments service, and how many open "
        "incidents does it have? Use the tools available to find out.",
    ),
    (
        "tool_multi",
        "Compare the error rate of the payments service and the search service over "
        "the last hour, then tell me which one to page on.",
    ),
    (
        "tool_chain",
        "Find which service owns the 'checkout_v2' endpoint, then look up that "
        "service's status, then report whether it is safe to deploy.",
    ),
]

# 도구 정의 (클라이언트 실행, 실제 동작은 스텁)
TOOLS: list[dict] = [
    {
        "name": "get_service_status",
        "description": (
            "Get the current health status of a named service. Call this when the "
            "user asks about service health, uptime, or incidents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service name"},
            },
            "required": ["service"],
        },
    },
    {
        "name": "get_error_rate",
        "description": (
            "Get the error rate of a named service over a time window. Call this "
            "when the user asks about errors, failures, or reliability metrics."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "window_minutes": {"type": "integer"},
            },
            "required": ["service"],
        },
    },
    {
        "name": "lookup_endpoint_owner",
        "description": (
            "Find which service owns a given HTTP endpoint. Call this when the user "
            "asks who owns or is responsible for an endpoint."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"endpoint": {"type": "string"}},
            "required": ["endpoint"],
        },
    },
]


def fake_tool_result(name: str, tool_input: dict) -> str:
    """스텁 도구 실행기. 결정적 출력이어야 조건 간 비교가 성립한다."""
    if name == "get_service_status":
        svc = tool_input.get("service", "unknown")
        return f'{{"service": "{svc}", "status": "degraded", "open_incidents": 2}}'
    if name == "get_error_rate":
        svc = tool_input.get("service", "unknown")
        rate = "4.1%" if "payment" in svc.lower() else "0.3%"
        return f'{{"service": "{svc}", "error_rate": "{rate}", "window_minutes": 60}}'
    if name == "lookup_endpoint_owner":
        return '{"endpoint": "checkout_v2", "owner_service": "payments"}'
    return '{"error": "unknown tool"}'
