# 축 3 — API 파라미터

**조사일:** 2026-08-13 / **출처:** platform.claude.com 공식 문서 직접 fetch (WebFetch 성공, WebSearch 대체 불필요)
**한 줄 결론:** 출력 토큰은 **thinking 몫**과 **응답문 몫**으로 나뉘며, `effort`는 앞의 것만, 프롬프트는 뒤의 것만 움직인다. 두 레버는 직교한다.

가장 중요한 계측 도구부터: **`usage.output_tokens_details.thinking_tokens`**. 이 필드가 있어야 절감이 thinking에서 왔는지 응답문에서 왔는지 구분된다. 이 축의 모든 실험은 `output_tokens` 하나가 아니라 `(output_tokens, thinking_tokens, output_tokens − thinking_tokens)` 3개 값을 기록한다.

참조 URL (전부 직접 확인):
- effort — https://platform.claude.com/docs/en/build-with-claude/effort
- thinking (개요) — https://platform.claude.com/docs/en/build-with-claude/thinking
- thinking 조종·비용·과금 — https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost
- thinking 트러블슈팅 (모델별 표) — https://platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting
- extended thinking (budget_tokens) — https://platform.claude.com/docs/en/build-with-claude/extended-thinking
- task budgets — https://platform.claude.com/docs/en/build-with-claude/task-budgets
- 마이그레이션 가이드 — https://platform.claude.com/docs/en/about-claude/models/migration-guide
- Opus 5 프롬프팅 — https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- 가격 — https://platform.claude.com/docs/en/about-claude/pricing
- 모델 개요 — https://platform.claude.com/docs/en/about-claude/models/overview
- Messages API 레퍼런스 — https://platform.claude.com/docs/en/api/messages/create

> `adaptive-thinking.md`, `pricing.md` 두 URL은 404/리다이렉트. 각각 `thinking-steering-and-cost`, `about-claude/pricing` 로 해결됨.

---

## 1. 파라미터 정리표

| 파라미터 | 위치·형태 | 출력 토큰에 미치는 영향 | 품질 트레이드오프 | 함정 |
|---|---|---|---|---|
| `output_config.effort` | `output_config: {effort: "low"\|"medium"\|"high"\|"xhigh"\|"max"}`. 기본값 `high` (= 생략과 완전히 동일) | **응답의 모든 토큰**에 작용: 응답문, 도구 호출, thinking. 낮추면 도구 호출 수 자체가 줄어든다. 단 **Opus 5에서는 visible 응답문을 확실히 줄이지 못한다** — thinking 볼륨만 줄어듦 | `low`는 "일부 능력 저하를 감수한 최대 효율". Opus 4.7 이후 모델은 낮은 effort에서 요청 범위를 넘는 일을 하지 않음 → 다단계 추론 과제에서 under-thinking 위험 | ① **`effort` 값이 프롬프트에 렌더링되므로 값을 바꾸면 프롬프트 캐시가 깨진다.** 대화 중간에 바꾸지 말 것 ② `"adaptive"`는 effort 값이 아님(thinking 모드) — 넣으면 오류 ③ 토큰 예산이 아니라 **행동 신호**. 낮은 effort에서도 어려운 문제엔 여전히 생각함 ④ `xhigh`/`max`에서는 `max_tokens`를 64k 이상으로 |
| `thinking: {type:"adaptive"}` | 최상위. `{type:"adaptive", display:...}` | thinking 토큰은 **출력 토큰으로 과금**되고 `max_tokens`를 잠식한다. adaptive는 모델이 요청마다 생각 여부·깊이를 결정 → 쉬운 요청에서 thinking 블록이 아예 안 나올 수 있음 | 켜는 쪽이 품질에 유리. 도구 호출 사이 interleaved thinking이 헤더 없이 자동 동작 | 모델별로 **생략 시 기본값이 다르다**(§2). Opus 4.8/4.7은 생략=off, Opus 5/Sonnet 5는 생략=on. 4.8→5 이관 시 아무것도 안 바꿔도 토큰이 늘어난다 |
| `thinking: {type:"disabled"}` | 최상위 | thinking 토큰 0 → 출력 토큰 최대 절감 | **Opus 5에서 알려진 부작용 2종** (아래 별도 절) | Fable 5/Mythos 5/Mythos Preview는 **400**. Opus 5는 effort `high` 이하에서만 허용, `xhigh`/`max`와 조합 시 **400** (요청마다 독립 검사) |
| `thinking.display` | `{type:"adaptive", display:"omitted"\|"summarized"}` | **과금에 영향 없음.** 문서 명시: "You're still charged for the full thinking tokens. Omitting reduces latency, not cost." 응답 body에서 thinking 텍스트만 사라짐 | 없음 (가시성만 바뀜) | ① **오측정 함정**: `omitted`면 응답이 짧아 보여 "토큰이 줄었다"고 착각하기 쉬움. 과금은 동일 ② `type:"disabled"`와 함께 쓰면 **invalid** ③ 실이득은 스트리밍 TTFT 단축 ④ 모델별 기본값이 다름(§2) |
| `max_tokens` | 최상위, 필수 | **하드캡.** thinking + 응답문 합계 상한. 초과 시 `stop_reason:"max_tokens"`로 잘림 | **절감이 아니라 손실.** 모델이 값을 인지하지 못하므로 마무리를 못 하고 문장 중간에서 끊김 | ① thinking이 예산을 잠식 → thinking 없던 시절 기준으로 잡은 값은 Opus 5에서 응답문이 잘림 ② `xhigh`/`max` effort에서는 64k 이상 권장 ③ `0`은 캐시 프리워밍 전용 ④ 도구 루프에서는 요청당 상한이라 턴 전체를 못 묶음 |
| `output_config.task_budget` (beta) | `output_config: {task_budget: {type:"tokens", total:N, remaining?:M}}` + 헤더 `task-budgets-2026-03-13` | **모델이 인지하는 예산.** 서버가 카운트다운 마커를 주입 → 모델이 스스로 페이스 조절, 예산 소진에 맞춰 우아하게 마무리. thinking·도구 호출·**도구 결과**까지 포함해 차감 | 예산이 과제에 비해 너무 작으면 **거절/조기 중단** 행동이 나옴 (문서 경고). p99 실측 후 잡을 것 | ① **하드캡 아님** — "soft hint". 초과 가능 ② 최소 `total` = **20,000**, 미만이면 400 ③ **응답에 잔여 예산 필드가 없다** (모델만 봄) ④ 매 턴 `remaining`을 클라이언트가 깎으면 캐시 무효화 + 과소보고 → 조기 종료 유발. 전체 히스토리 재전송 루프에서는 `remaining` 생략 ⑤ 재전송한 과거 메시지는 재차감되지 않음 |
| `stop_sequences` | 최상위 `["..."]` | 지정 문자열 생성 시 즉시 중단. `stop_reason:"stop_sequence"`, `stop_sequence`에 매치값 | 모델이 인지하지 못하는 절단이므로 `max_tokens`와 같은 성격의 손실 | 구조화 출력 강제 목적의 legacy 스캐폴드. 현재는 `output_config.format`(structured outputs)이 정식 대체재 — 축 2와 연결 |
| 모델 선택 | `model` | 단가 × 출력 길이 성향. **Opus 5는 이전 Opus보다 기본 응답이 길다**(문서 명시) → 단가비에 길이비가 곱해짐 | 티어별 능력 차 | ① Haiku 4.5는 `effort`·adaptive thinking **미지원**(400) ② 4.7 이후 모델은 **토크나이저가 달라 같은 텍스트에 약 30% 더 많은 토큰**을 낸다 — 구세대와 토큰 수를 직접 비교하면 안 됨 |

### effort 레벨별 thinking 행동 (공식 표)

| effort | thinking 행동 |
|---|---|
| `max` | 항상 생각, 깊이 제한 없음 |
| `xhigh` | 항상 깊게 생각, 확장 탐색 |
| `high` (기본) | 거의 항상 생각 |
| `medium` | 중간. 쉬운 질의는 생각을 건너뛸 수 있음 |
| `low` | 최소화. 쉬운 과제는 생각을 건너뜀 |

### `thinking:{"type":"disabled"}` — Claude Opus 5의 알려진 부작용 (핵심)

문서에 명시된 두 가지 사고이며, **effort 하향이 더 나은 레버**라는 결론의 근거다.

1. **도구 호출이 평문으로 샌다.** 구조화된 `tool_use` 블록 대신 사용자 대면 텍스트에 도구 호출을 써버린다. **턴은 정상 종료되고 호출은 실행되지 않는다** — 에러도, 경고도 없는 무성 실패. 에이전트 루프에서는 그 누출 텍스트가 히스토리에 남아 이후 턴까지 오염시킨다. 검색 등 도구 집약 워크로드에서 가장 흔함.
2. **`<thinking>` 등 내부 XML 태그가 응답에 샌다.** 시스템 프롬프트에 "생각하지 마라 / 추론하지 마라" 류 규칙이 있으면 **누출이 오히려 증가**한다 (반직관적).

공식 1차 권고: *"the primary mitigation for both is to keep thinking enabled and control token cost with lower effort levels instead of disabling thinking: for most tasks, thinking enabled at `low` effort performs better than thinking disabled at similar cost."*

끌 수밖에 없을 때의 공식 완화 문구(원문 그대로 쓸 것):
> `When you use a tool, you may say a brief sentence first. If no tool can express what the user asked for, say so instead of guessing. Do not include internal or system XML tags in your response.`

주의: 태그를 이름으로 지목("`<thinking>` 태그를 쓰지 마라")하는 것이 일반형보다 **덜 효과적**이다.

---

## 2. 모델별 지원 매트릭스

**틀린 파라미터 = 400.** 아래는 공식 표 기준 (thinking-troubleshooting §Configurations each model rejects, effort §Effort levels, task-budgets §Feature support).

### 2.1 thinking

| 모델 | 지원 타입 | `thinking` 생략 시 | 400으로 거부 |
|---|---|---|---|
| Claude Fable 5 | adaptive만 | **항상 on** | `enabled`, `disabled` |
| Claude Mythos 5 | adaptive만 | **항상 on** | `enabled`, `disabled` |
| Claude Mythos Preview | adaptive, extended | 항상 on | `disabled` |
| **Claude Opus 5** | adaptive만 | **on** | `enabled`; `disabled`는 effort `xhigh`/`max`와 조합 시 400 |
| Claude Opus 4.8 | adaptive만 | **off** | `enabled` |
| Claude Opus 4.7 | adaptive만 | **off** | `enabled` |
| **Claude Sonnet 5** | adaptive만 | **on** | `enabled` |
| Claude Opus 4.6 | adaptive, extended(deprecated) | off | 없음 |
| Claude Sonnet 4.6 | adaptive, extended(deprecated) | off | 없음 |
| Claude Opus 4.5 | extended만 | off | `adaptive` |
| **Claude Haiku 4.5** | extended만 | off | `adaptive` |
| Claude Sonnet 4.5 | extended만 | off | `adaptive` |

- `budget_tokens`(extended thinking): 4.6 세대에서 deprecated(동작함), **4.7 이후 모델은 400**. 최소 1,024, `max_tokens`보다 작아야 함(interleaved 예외).
- 대체 매핑: `budget_tokens` 제거 → `thinking:{type:"adaptive"}` + `output_config.effort`.

### 2.2 `thinking.display` 기본값

| 기본 `"omitted"` | 기본 `"summarized"` |
|---|---|
| Fable 5, Mythos 5, Mythos Preview, **Opus 5**, **Sonnet 5**, Opus 4.8, Opus 4.7 | Opus 4.6, Sonnet 4.6 및 그 이전 |

`omitted`여도 `signature` 필드는 암호화된 전체 thinking을 담고 있어 멀티턴 연속성이 유지된다. 라운드트립 시 **그대로 되돌려 보낼 것** (수정하면 400).

### 2.3 effort 레벨

| 모델 | low | medium | high | xhigh | max |
|---|---|---|---|---|---|
| Fable 5 / Mythos 5 | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Opus 5** | ✅ | ✅ | ✅(기본) | ✅ | ✅ |
| Opus 4.8 / Opus 4.7 | ✅ | ✅ | ✅(기본) | ✅ | ✅ |
| **Sonnet 5** | ✅ | ✅ | ✅(기본) | ✅ | ✅ |
| Opus 4.6 / Sonnet 4.6 | ✅ | ✅ | ✅(기본) | ❌ | ✅ |
| Opus 4.5 | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Haiku 4.5 / Sonnet 4.5** | ❌ | ❌ | ❌ | ❌ | ❌ |

### 2.4 `task_budget` (beta `task-budgets-2026-03-13`)

| 모델 | 지원 |
|---|---|
| Opus 5, Fable 5, Mythos 5, Opus 4.8, Opus 4.7 | ✅ beta |
| **Sonnet 5** | ❌ **미지원** |
| Opus 4.6, Sonnet 4.6, Haiku 4.5 | ❌ |

> ⚠️ 로컬 캐시된 요약 자료 중 "Sonnet 5도 task_budget 지원"이라고 적힌 것이 있으나, **공식 Feature support 표는 Sonnet 5를 Not supported로 명시**한다. 공식 문서를 따른다. Claude Code / Cowork 표면에서도 미지원.

### 2.5 단가 (출력 토큰 기준, 2026-08-13 확인)

| 모델 | 입력 $/MTok | 출력 $/MTok | 배치 출력 $/MTok | 최대 출력 |
|---|---|---|---|---|
| Claude Fable 5 | 10 | **50** | 25 | 128k |
| Claude Opus 5 | 5 | **25** | 12.50 | 128k |
| Claude Opus 4.8 / 4.7 | 5 | 25 | 12.50 | 128k |
| Claude Sonnet 5 | 2 | **10** | 5 | 128k |
| Claude Sonnet 4.6 | 3 | 15 | 7.50 | 128k |
| Claude Haiku 4.5 | 1 | **5** | 2.50 | 64k |

- Sonnet 5의 $2/$10은 **도입가가 아니라 확정 표준가**가 되었다 (9/1 인상 취소 공지).
- 출력 단가비 Opus 5 : Sonnet 5 : Haiku 4.5 = **5 : 2 : 1**.
- Batch API는 입·출력 **50% 할인**. 지연 허용 워크로드에서 가장 큰 단일 레버.
- Fast mode(Opus 5/4.8): $10/$50 — 출력 단가가 **2배**. 속도 대가.
- `inference_geo:"us"`는 모든 토큰에 **1.1배**.
- 배치 API에서 `output-300k-2026-03-24` 헤더로 최대 출력 300k까지 확장 가능(Opus 5, 4.8, 4.7, 4.6, Sonnet 5, 4.6).

---

## 3. 가설

각 가설은 검증 가능성 태그를 단다. 이 축은 **대부분 API 없이는 검증 불가**하다.

| # | 가설 | 태그 |
|---|---|---|
| **H3-1** | `effort`를 낮추면 `output_tokens`는 단조 감소하지만, 감소분의 대부분이 `thinking_tokens`이고 Opus 5에서 visible(응답문) 토큰은 유의하게 줄지 않는다. → effort는 **thinking 레버**이지 응답문 레버가 아니다 | **[API 필요]** |
| **H3-2** | `thinking:disabled`는 출력 토큰을 가장 크게 줄이지만 Opus 5에서 평문 도구 호출 누출·XML 태그 누출이 측정 가능한 빈도로 발생한다. `adaptive + effort:low`가 비슷한 절감을 부작용 없이 낸다 | **[API 필요]** |
| **H3-3** | `display:"omitted"`와 `"summarized"`의 `output_tokens`는 구분되지 않는다. display는 **지연 레버이지 비용 레버가 아니다**. (문서가 그렇게 말하지만 계측으로 확인 — 어긋나면 그게 더 중요한 발견) | **[API 필요]** |
| **H3-4** | `max_tokens` 하향으로 얻은 출력 토큰 감소분의 상당 비율은 `stop_reason:"max_tokens"`(잘림)에서 온다. 즉 절감 기법이 아니라 손실 기법이다 | **[API 필요]** |
| **H3-5** | 같은 예산을 `task_budget`으로 주면 누적 출력 토큰이 무제한 조건보다 감소하되 `end_turn`으로 완결한다. 동일 예산에서 **완결률이 max_tokens보다 높다** | **[API 필요]** |
| **H3-6** | 동일 과제에서 모델별 출력 길이 성향이 다르고, 그 차이는 단가 차이와 같은 방향이 아니다. 실질 비용비 = 단가비 × 길이비이므로 라우팅 손익분기는 단가비만으로 계산할 수 없다 | **[API 필요]** + 길이 성향만 **[proxy 검증 가능]** |
| **H3-7** | visible 출력 토큰을 줄이는 데는 effort 하향보다 간결성 시스템 프롬프트가 효과적이며, 두 레버는 서로 다른 토큰 풀을 건드리므로 **가산적**이다. → 축 1과 축 3은 경쟁이 아니라 곱셈 관계 | **[API 필요]** + 프롬프트 요인만 **[proxy 검증 가능]** |

**기각 조건도 미리 못박는다.** H3-1은 visible 토큰이 effort에 따라 20% 이상 단조 감소하면 기각. H3-3은 두 display 조건의 `output_tokens` 중앙값 차이가 조건 내 사분위 범위를 넘으면 기각. H3-4는 낮은 `max_tokens`에서 `stop_reason:"max_tokens"` 비율이 20% 미만이면 기각.

---

## 4. 실험 프로토콜 / 스크립트 경로

### 4.1 [API 필요] — 실행 대기 스크립트

키 확보 즉시 실행. 실행하지 않았음(키 없음). 전부 `usage.output_tokens` 기준으로 기록하고 `experiments/results/*.jsonl`에 append.

| 가설 | 스크립트 | 결과 파일 |
|---|---|---|
| 공용 유틸 | `experiments/scripts/common.py` | — |
| 고정 과제 세트 | `experiments/scripts/tasks.py` | — |
| H3-1 | `experiments/scripts/exp01_effort_sweep.py` | `exp01_effort_sweep.jsonl` |
| H3-2 | `experiments/scripts/exp02_thinking_modes.py` | `exp02_thinking_modes.jsonl` (+ `.leaks`) |
| H3-3 | `experiments/scripts/exp03_display_billing.py` | `exp03_display_billing.jsonl` (+ `.detail`) |
| H3-4, H3-5 | `experiments/scripts/exp04_max_tokens_vs_task_budget.py` | `exp04_max_tokens.jsonl`, `exp04_task_budget.jsonl` |
| H3-6 | `experiments/scripts/exp05_model_tier.py` | `exp05_model_tier.jsonl` |
| H3-7 | `experiments/scripts/exp06_conciseness_vs_effort.py` | `exp06_conciseness_vs_effort.jsonl` |

공통 실행법:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...     # 또는 `ant auth login`
python experiments/scripts/exp01_effort_sweep.py --trials 3
python experiments/scripts/exp01_effort_sweep.py --summarize-only   # 집계만
```

설계 공통 규칙 (스크립트에 반영됨):
- **과제 고정, 언어 고정(영어), 파라미터만 변경.** 난이도 3층(easy/medium/hard)으로 층화.
- 400 에러도 결과로 기록한다 — 모델별 지원 여부 검증이 이 축의 절반이다. 음성 통제를 명시적으로 넣었다(예: Opus 5 `disabled`+`xhigh`, Sonnet 5 `task_budget`, `disabled`+`display`).
- 부작용(H3-2)은 저빈도 사고다. `--trials`를 최소 5, 가능하면 10 이상. **n=3에서 "0건 관측"은 아무것도 증명하지 못한다.**
- 비용 추정치를 각 스크립트 docstring에 적어두었다. 먼저 `--trials 1`로 감을 잡을 것.

### 4.2 [proxy 검증 가능] — naive 서브에이전트 프로토콜

API 없이 대리 검증 가능한 것은 **두 가지뿐**이다. 나머지(effort, display, task_budget, max_tokens)는 파라미터 자체가 서브에이전트 프롬프트로 표현되지 않으므로 원리적으로 불가.

#### P-A. 모델 티어별 출력 길이 성향 (H3-6의 길이 성향 부분)

- **과제:** `experiments/scripts/tasks.py`의 `TASKS` 9개 중 medium 3개 + hard 3개 = 6개.
- **조건:** 서브에이전트 모델 = {Haiku, Sonnet, Opus} 3수준. (Agent 도구의 `model` 파라미터로 지정)
- **프롬프트 전문(모든 조건 동일, 한 글자도 바꾸지 않는다):**
  ```
  {TASKS의 prompt 원문을 그대로}
  ```
  → **피험 에이전트에게 실험이라는 사실을 알리지 않는다.** "간결하게" 같은 지시를 절대 넣지 않는다. 넣는 순간 성향 측정이 아니라 지시 수용도 측정이 된다.
- **n:** 조건당 과제당 5회 = 3 × 6 × 5 = 90 시행.
- **측정법:** 산출물의 **문자 수 / 단어 수 / 줄 수**. 조건 간 **상대 비율만** 보고. 절대 토큰 수로 환산 금지 — 4.7 이후 토크나이저가 같은 텍스트에 약 30% 더 많은 토큰을 내므로 모델군을 가로지르는 문자→토큰 환산은 원리적으로 깨진다.
- **품질 기준:** 판정 에이전트가 6개 과제 각각에 대해 사전 작성한 "필수 논점 체크리스트"(과제당 4–6항목)로 채점. 모델·조건은 익명화하고 제시 순서를 무작위화한다.
- **보고 형식:** `Haiku : Sonnet : Opus = 1.00 : X.XX : Y.YY (proxy, 문자 수 기준, n=30/조건)`.

#### P-B. 간결성 프롬프트의 효과 (H3-7의 프롬프트 요인)

- **과제:** 위와 동일한 6개. 조건 간 과제·모델 완전 고정(Sonnet 하나로 고정).
- **조건 A (대조군) 프롬프트 전문:**
  ```
  {TASKS의 prompt 원문}
  ```
- **조건 B (처치군) 프롬프트 전문** — 앞에 공식 문서 문구를 그대로 붙인다:
  ```
  Keep responses focused, brief, and concise. Keep disclaimers and caveats short, and spend most of the response on the main answer. When asked to explain something, give a high-level summary unless an in-depth explanation is specifically requested.

  {TASKS의 prompt 원문}
  ```
  문구를 자작으로 바꾸지 않는다. 출처 문구를 써야 API 실험(exp06)과 결과를 직접 비교할 수 있다.
- **n:** 조건당 과제당 5회 = 2 × 6 × 5 = 60 시행.
- **측정법:** 문자 수. 상대 감소율 `1 − (B/A)`로 보고, 반드시 `(proxy)` 표기.
- **품질 기준:** P-A와 동일한 체크리스트. **토큰이 줄었는데 필수 논점이 빠졌으면 절감이 아니라 품질 저하**로 분류한다. 이 판정 없이 감소율만 보고하지 않는다.
- **한계 명시:** proxy는 visible 응답문만 잰다. thinking 토큰은 서브에이전트 산출물에 나타나지 않으므로 **총 출력 토큰 절감률은 이 방법으로 측정 불가**하다. H3-7의 "직교성" 주장은 API 검증(exp06) 없이는 확정할 수 없다.

---

## 5. 한계

1. **이 축은 API 없이 사실상 검증 불가하다.** 7개 가설 중 5개는 순수 [API 필요]이고, 나머지 2개도 절반만 proxy로 닿는다. `effort`, `display`, `task_budget`, `max_tokens`는 서브에이전트 프롬프트로 표현할 수 있는 개념이 아니다.

2. **proxy는 thinking 토큰을 볼 수 없다.** 이 축의 핵심 발견(= 절감이 thinking에서 오는가 응답문에서 오는가)은 `usage.output_tokens_details.thinking_tokens` 없이는 원리적으로 관측 불가. proxy 실험 결과로 effort 관련 결론을 내리면 안 된다.

3. **문자↔토큰 환산이 모델군을 가로지르면 깨진다.** Opus 4.7 이후 모델은 새 토크나이저를 쓰고 같은 텍스트에 약 30% 더 많은 토큰을 낸다. 구세대 모델과의 토큰 수 직접 비교는 무효.

4. **절감률 수치를 이 문서에 하나도 적지 않았다.** 공식 문서는 effort 레벨별 토큰 절감 퍼센트를 **공표하지 않는다** ("Significant token savings" 같은 정성 표현뿐). 측정 전까지 전부 "측정 필요".

5. **부작용 발생률은 저빈도라 표본이 커야 한다.** Opus 5 thinking-disabled 부작용은 문서가 "occasionally"라고만 표현한다. 정량 기준선이 없으므로 우리 워크로드에서 직접 재야 하고, n이 작으면 0건이 나와도 아무 의미가 없다.

6. **effort 변경은 프롬프트 캐시를 깬다.** "요청마다 난이도에 맞춰 effort를 동적 조절"은 출력 토큰은 줄이지만 입력 토큰 비용을 올릴 수 있다. 축 3만 보고 최적화하면 전체 비용이 오를 수 있으므로, 절감 판정은 **입력+출력 합산 비용** 기준이어야 한다.

7. **모델별 지원 매트릭스는 빠르게 변한다.** 2025–2026년에 `budget_tokens` 제거, `xhigh` 추가, thinking 기본값 전환, `disabled`의 effort 게이팅 등이 연달아 일어났다. 실험 실행 시점에 §2를 재확인할 것. 실제로 이번 조사에서도 캐시된 자료와 공식 문서가 `task_budget`의 Sonnet 5 지원 여부에서 어긋났다.

8. **비용 검증 자체가 비용이다.** exp04 Part B(에이전트 루프)는 단일 실행이 수십 달러에 이를 수 있다. 예산 없이 전량 실행하면 절감 연구가 순손실이 된다. `--trials 1`부터.
