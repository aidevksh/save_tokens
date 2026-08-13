# 축 1 — 프롬프트 지시문

대상: Claude 계열(Opus 5 / Sonnet 5 / Opus 4.8 등). 목표: **프롬프트 지시문만으로 출력 토큰을 줄이는 기법**의 근거 수집 → 가설 → 실험 설계.
실험은 아직 실행하지 않음. 설계까지만.

---

## 1. 리서치 요약

### 1.1 출력 길이는 `effort`가 아니라 프롬프트로 제어한다 (핵심)

- **Claude Opus 5의 기본 응답은 이전 Opus보다 길다.** 그리고 `effort`는 *사고(thinking) 분량*을 조절할 뿐 **가시적 응답 길이를 신뢰성 있게 줄이지 못한다.** 공식 문서 원문: "Effort controls thinking volume, not visible response length: on Claude Opus 5, changing effort does not reliably shorten responses, so prompt for length instead."
  - 출처: https://platform.claude.com/docs/en/build-with-claude/effort
  - 출처: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- 반대로 **도구 사용이 끼는 경우** `effort`는 출력 형태에 영향을 준다. 낮은 effort는 "Proceed directly to action without preamble", "Use terse confirmation messages after completion", 도구 호출 수 감소.
  - 출처: https://platform.claude.com/docs/en/build-with-claude/effort ("Effort with tool use")
- → **축 1(프롬프트)과 축 3(API 파라미터)은 서로 다른 부분을 건드린다.** 단일 턴 텍스트 응답의 길이는 축 1의 영역.

### 1.2 공식 권장 간결성 지시문 (원문 그대로)

| 용도 | 원문 스니펫 | 출처 |
|---|---|---|
| 사용자 대면 멀티턴 제품 (Opus 5) | `Keep responses focused, brief, and concise. Keep disclaimers and caveats short, and spend most of the response on the main answer. When asked to explain something, give a high-level summary unless an in-depth explanation is specifically requested.` | [prompting-claude-opus-5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) |
| 긴 system prompt의 **말미 리마인더** | `<tone_preference>\nKeep outputs reasonably concise.\n</tone_preference>` | 동상 |
| 일반 간결성 (Opus 4.8 / Sonnet 5) | `Provide concise, focused responses. Skip non-essential context, and keep examples minimal.` | [prompting-claude-opus-4-8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8), [prompting-claude-sonnet-5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5) |
| 파일로 쓰는 산출물 길이 | `Match the length of written documents to what the task needs: cover the substance, but do not pad with filler sections, redundant summaries, or boilerplate.` | prompting-claude-opus-5 |
| 에이전트 내레이션 축소 | `Before your first tool call, say in one sentence what you're about to do. While working, give a brief update only when you find something important or change direction. When you finish, lead with the outcome...` | prompting-claude-opus-5 |
| 자기수정 서술 억제 | `Only correct an earlier statement when the error would change the user's code, conclusions, or decisions. State corrections plainly and briefly, then continue the task. For slips that change nothing for the user, make the fix and move on without noting it.` | prompting-claude-opus-5 |
| 과제 범위 확장 억제 | `Deliver what was asked, at the scope intended. Make routine judgment calls yourself, and check in only when different readings of the request would lead to materially different work. ...` | prompting-claude-opus-5 |
| 서론(preamble) 제거 | `Respond directly without preamble. Do not start with phrases like 'Here is...', 'Based on...', etc.` | [claude-prompting-best-practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) (prefill 대체 방법) |

**중요:** 긴 system prompt에서는 앞의 간결성 지시를 **말미 리마인더와 짝지으라(pair)**고 명시. 즉 "위치"가 공식 권고에 포함되어 있다.

### 1.3 긍정형 vs 부정형 표현

- 출력 형식 제어 원칙: **"Tell Claude what to do instead of what not to do."** 예시로 "Do not use markdown in your response" 대신 "Your response should be composed of smoothly flowing prose paragraphs."
  - 출처: claude-prompting-best-practices ("Control the format of responses")
- 간결성에 대해서도 동일: "Positive examples showing how Claude can communicate with the appropriate level of concision tend to be more effective than negative examples or instructions that tell the model what not to do."
  - 출처: prompting-claude-opus-4-8, prompting-claude-sonnet-5
- 단, **길이 감소량에 대한 수치는 공식 문서에 없음 → 측정 필요.**

### 1.4 프롬프트 스타일이 출력 스타일에 전이된다

- "The formatting style used in your prompt may influence Claude's response style. ... removing markdown from your prompt can reduce the volume of markdown in the output."
  - 출처: claude-prompting-best-practices ("Match your prompt style to the desired output")
- 마크다운 볼륨 감소 = 헤더/불릿 마크업 문자 감소 → 출력 토큰 감소 가능성. **수치 없음 → 측정 필요.**

### 1.5 예시(few-shot)의 효과

- "Examples are one of the most reliable ways to steer Claude's output **format, tone, and structure**." 권장 개수 **3–5개**, `<example>` 태그로 감쌀 것, 다양성 확보(모델이 의도치 않은 패턴을 학습하지 않도록).
  - 출처: claude-prompting-best-practices ("Use examples effectively")
- 공식 문서는 "예시가 *길이*를 고정한다"고 직접 말하지 않는다. "format/structure를 steer한다"에서 유추한 것 → **탐색적 가설.**

### 1.6 과잉 검증(self-verification) 지시 제거

- Opus 5는 시키지 않아도 자기 검증을 한다. 프롬프트에 명시적 검증 지시("include a final verification step for any non-trivial task", "use a subagent to verify")가 있으면 **제거하라**. 원문: "removing them reduces wasted tokens **with no loss in quality**."
- 자기 재확인 지시도 동일: "Avoid instructing re-checks it already performs (`double-check your answer`, `re-verify before responding`); like verification instructions, these compound with the model's own behavior and add cost without improving results."
  - 출처: prompting-claude-opus-5 ("Task scope and over-verification", "Self-correction")
- **이 항목만은 공식 문서가 "토큰 낭비 감소 + 품질 손실 없음"을 명시적으로 주장한다.** 절감률 수치는 없음 → 측정 필요.

### 1.7 강제 진행보고 스캐폴딩 제거

- "If you've added scaffolding to force interim status messages ('After every 3 tool calls, summarize progress'), **try removing it**." — Opus 4.8 / Sonnet 5 문서 공통.
  - 에이전트 축(축 5) 소재지만, 프롬프트 지시문 제거로 출력을 줄이는 같은 계열.

### 1.8 수치 상한 지시에 대한 주의

- 번들 스킬 문서(`claude-api` 스킬, `shared/prompt-audit.md`)는 **하드 워드 캡(`at most N words`)을 "정성적 길이 지침으로 대체하라"**고 권고한다. 이유: 출력 캡이 어려운 문제에서 추론을 굶긴다(starve reasoning), 그리고 이전 모델의 장황함에 맞춰 튜닝된 값이 그대로 남는 경우가 많다.
  - 출처: Anthropic `claude-api` 스킬 번들 문서 `shared/prompt-audit.md` (공개 URL 없음, 로컬 스킬 자산)
- 즉 **수치 상한은 길이는 줄이되 품질을 깎을 위험**이 명시된 유일한 기법이다. → H3의 근거.

### 1.9 위치(position) 효과에 대한 유일한 수치

- 긴 문서(20k+ 토큰) 입력 시 **질의를 프롬프트 끝에 두면 응답 품질이 테스트에서 최대 30% 향상**. 원문: "Queries at the end can improve response quality by up to 30 percent in tests, especially with complex, multidocument inputs."
  - 출처: claude-prompting-best-practices ("Longform data / long context tips")
- **주의: 이것은 *품질* 수치이며 *길이 절감* 수치가 아니다.** 다만 "말미가 지시 준수에 유리하다"는 방향성 근거로는 쓸 수 있다.

### 1.10 워딩 민감성 / 측정 의무

- "Steering effectiveness can be sensitive to exact wording. If one phrasing doesn't produce the behavior you want, try a more direct variant."
- "Prompt-based steering changes model behavior, so treat it like any other prompt change: **measure before you ship.**" + 사고를 덜 하게 유도하면 품질이 떨어질 수 있다는 경고.
  - 출처: https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost

### 1.11 참고: 번들 마이그레이션 문서의 20% 주장

- Anthropic `claude-api` 스킬 번들 문서 `shared/model-migration.md`(Migrating to Claude Opus 5)는 "in testing, a short conciseness instruction cut user-facing response length by **~20%**"라고 기술한다.
- 그러나 **동일 내용의 공개 문서 페이지(prompting-claude-opus-5)에는 이 수치가 없다** ("A short conciseness instruction is effective"만 있음).
- 따라서 이 20%는 **단일 번들 출처의 미검증 수치**로 취급하고, 우리 실험 결과와 별도로 보고한다. 본 저장소 수치로 인용 금지.

### 1.12 절감률 수치 현황 요약

| 기법 | 공개 출처 절감률 |
|---|---|
| 간결성 지시(정성) | **측정 필요** (번들 문서에 ~20% 주장 있으나 공개 문서 미확인) |
| 긍정형 vs 부정형 | **측정 필요** (방향성만 문서화) |
| 말미 리마인더 추가 | **측정 필요** (권고만 존재) |
| 수치 상한 | **측정 필요** (품질 위험만 문서화) |
| 서론/맺음말 억제 | **측정 필요** |
| 짧은 예시 앵커링 | **측정 필요** (근거 없음, 탐색적) |
| 검증 지시 제거 | **측정 필요** ("no loss in quality"는 명시, 절감률은 없음) |
| 프롬프트 마크다운 제거 | **측정 필요** |

---

## 2. 가설

전부 **동일 언어(한국어) 고정**, 동일 과제, 동일 시행 수 조건에서의 상대 비교.

> **H1** — 조건 A(간결성 지시 없음) 대비 조건 B1a(**긍정형** 간결성 지시)에서 출력 길이가 감소하며, 과제 요구사항 충족도는 유지된다. 또한 B1a는 조건 B1b(**부정형** 간결성 지시)보다 감소 폭이 크거나 같고 요구사항 충족도가 높다.
> **근거**: "Tell Claude what to do instead of what not to do" / "Positive examples ... more effective than negative examples" (claude-prompting-best-practices, prompting-claude-opus-4-8, prompting-claude-sonnet-5). 절감률 수치는 없음.

> **H2** — 긴 프롬프트에서, 간결성 지시를 **앞부분에만** 넣은 조건(B2a) 대비 **앞부분 + 말미 `<tone_preference>` 리마인더**를 넣은 조건(B2b)에서 출력 길이가 추가로 감소하며 요구사항 충족도는 유지된다.
> **근거**: prompting-claude-opus-5가 긴 system prompt에서 말미 리마인더와 "pair"하라고 명시. 말미 배치 유리성의 간접 근거로 "queries at the end ... up to 30 percent"(품질 수치이며 길이 수치 아님).

> **H3** — 정성 간결성 지시(B1a) 대비 **수치 상한 지시**(B3, "600자 이내")에서 출력 길이가 더 크게 감소하지만, **요구사항 충족도가 하락**한다(길이-품질 트레이드오프가 관측된다). 또한 길이의 분산은 B3에서 더 작다.
> **근거**: `claude-api` 스킬 `shared/prompt-audit.md` — 하드 워드 캡은 추론을 굶기므로 정성 지침으로 대체 권고. 절감률·하락폭 수치 없음.

> **H4** — 조건 A 대비 **서론·맺음말·자기평가·자기수정 서술 억제 지시**(B4)에서 출력 길이가 감소하며 요구사항 충족도는 유지된다.
> **근거**: prefill 대체 가이드의 "Respond directly without preamble..." (claude-prompting-best-practices) + Opus 5 자기수정 서술 억제 스니펫 (prompting-claude-opus-5). 절감률 수치 없음.

> **H5** — 조건 A 대비 **짧은 예시 2개**를 붙인 조건(B5s)에서 출력 길이가 감소하고, **긴 예시 2개**를 붙인 조건(B5l)에서는 감소하지 않거나 증가한다. 즉 출력 길이는 예시의 길이를 따라간다(앵커링).
> **근거 없음, 탐색적.** 공식 문서는 예시가 "format, tone, structure"를 steer한다고만 하고 길이 앵커링은 언급하지 않음.

> **H6** — **과잉 검증 유발 지시를 포함한 조건(A6, "답변 전 스스로 재검증하라")** 대비 **해당 지시를 제거한 조건(A)** 에서 출력 길이가 감소하며 요구사항 충족도는 유지된다. (역방향 비교: 제거가 처치)
> **근거**: prompting-claude-opus-5 — "removing them reduces wasted tokens with no loss in quality" / "double-check your answer ... add cost without improving results". 유일하게 품질 무손실이 명시된 항목. 절감률 수치 없음.

> **H7** — 과제 지시문을 **마크다운(헤더·불릿) 렌더링**으로 준 조건(A7) 대비 **동일 내용의 평문 산문 렌더링**으로 준 조건(B7)에서 출력의 마크업 문자 비율과 전체 길이가 감소하며 요구사항 충족도는 유지된다.
> **근거**: "removing markdown from your prompt can reduce the volume of markdown in the output" (claude-prompting-best-practices). 절감률 수치 없음.

---

## 3. 실험 프로토콜

### 3.0 환경 제약과 그에 따른 설계 결정

- `ANTHROPIC_API_KEY` / `ant` CLI 없음 → `usage.output_tokens`, `count_tokens` 사용 불가.
- 유일한 실행 수단: **naive 서브에이전트에게 조건별 프롬프트로 동일 과제를 주고 산출물의 문자/어절/줄 수를 측정.**
- 피험 에이전트는 **자신이 토큰 실험 대상임을 몰라야 한다.** 프롬프트에 "토큰", "실험", "측정", "조건 A/B", "짧게 써서 비용을 아껴라" 등의 메타 단어 금지. (단, 처치 자체인 길이 지시문은 허용 — 그것이 처치다.)
- 서브에이전트는 system prompt를 직접 제어할 수 없다 → **H2의 "system 앞/뒤"는 "단일 프롬프트 내 앞부분/말미"로 치환**하여 검증한다. 진짜 system/user 분리 검증은 API 확보 후로 미룬다(§4 참조).
- **언어 고정: 모든 조건에서 한국어.** 모든 프롬프트 말미(또는 지시 블록)에 동일한 한국어 지정 문구를 넣어 조건 간 차이가 생기지 않게 한다.

### 3.1 과제 3종 (지시문 전문)

아래 `{과제}` 자리에 그대로 삽입한다. 세 과제 모두 외부 파일/도구 접근 불필요(자기완결형).

---

#### T1 — 코드 설명

```
아래 Python 클래스가 무엇을 하는지 설명해 주세요.

```python
import time
from collections import OrderedDict

class TTLCache:
    def __init__(self, capacity=128, ttl=60.0):
        self.capacity = capacity
        self.ttl = ttl
        self._store = OrderedDict()

    def get(self, key):
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key, value):
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, time.monotonic() + self.ttl)
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)
```
```

**T1 요구사항 체크리스트 (각 1점, 총 5점)**
1. LRU 축출 정책(가장 오래 사용되지 않은 항목 제거)을 언급한다.
2. TTL 만료가 `get` 시점에 지연 확인·삭제된다(lazy expiration)는 점을 언급한다.
3. `move_to_end`가 최근 사용 순서를 갱신하는 역할임을 설명한다.
4. `capacity` 초과 시 `popitem(last=False)`로 가장 오래된 항목을 제거함을 설명한다.
5. 만료 판정이 절대시각(`time.monotonic() + ttl`) 저장 방식으로 이뤄짐을 언급한다.

---

#### T2 — 기술 문서 요약

```
다음 문서를 요약해 주세요.

<document>
PostgreSQL은 MVCC(다중 버전 동시성 제어)를 사용한다. 행을 UPDATE하거나 DELETE해도 기존 행 버전은 즉시 사라지지 않고 '죽은 튜플(dead tuple)'로 테이블에 남는다. 어떤 트랜잭션도 더 이상 그 버전을 볼 수 없게 된 뒤에야 회수 대상이 된다.

VACUUM은 이 죽은 튜플이 차지한 공간을 회수해 같은 테이블의 새 행이 재사용할 수 있도록 표시한다. 다만 일반 VACUUM은 파일 크기를 운영체제에 반환하지 않는다. 파일을 실제로 줄이려면 VACUUM FULL이 필요한데, VACUUM FULL은 테이블을 통째로 다시 쓰면서 ACCESS EXCLUSIVE 잠금을 잡기 때문에 그동안 해당 테이블에 대한 읽기와 쓰기가 모두 차단된다.

autovacuum 데몬은 테이블별 변경 행 수가 임계치를 넘으면 VACUUM을 자동으로 실행한다. 임계치는 autovacuum_vacuum_threshold와 autovacuum_vacuum_scale_factor로 결정되며 기본값은 각각 50행과 테이블 행 수의 20%다. 대형 테이블에서는 scale_factor 20%가 너무 커서 vacuum이 드물게 실행되므로, 테이블 단위로 scale_factor를 낮추는 것이 일반적인 튜닝이다.

VACUUM은 또한 트랜잭션 ID 순환(wraparound)을 막기 위해 오래된 행을 동결(freeze)하는 역할도 한다.
</document>
```

**T2 요구사항 체크리스트 (각 1점, 총 5점)**
1. MVCC로 인해 죽은 튜플이 남는다는 배경을 언급한다.
2. 일반 VACUUM은 재사용 표시만 하고 OS에 파일 공간을 반환하지 않는다는 점을 언급한다.
3. VACUUM FULL이 ACCESS EXCLUSIVE 잠금으로 읽기·쓰기를 차단한다는 점을 언급한다.
4. autovacuum 임계치가 threshold + scale_factor로 결정되며 기본값이 50행 / 20%임을 언급한다.
5. wraparound 방지를 위한 freeze 역할을 언급한다.

---

#### T3 — 자유 서술형

```
새 내부 서비스의 API를 REST로 할지 GraphQL로 할지 결정해야 합니다. 어떤 기준으로 판단해야 하는지 설명해 주세요.
```

**T3 요구사항 체크리스트 (각 1점, 총 5점)**
1. 클라이언트 다양성 / over-fetching·under-fetching 문제를 판단 기준으로 든다.
2. 캐싱(HTTP 계층 캐시 활용도, GraphQL의 캐싱 난이도)을 다룬다.
3. 팀 역량·도구 생태계·운영 비용(스키마 관리, N+1 등)을 다룬다.
4. 스키마 진화 / 버저닝 전략을 다룬다.
5. 마지막에 결정 기준을 정리하거나 명확한 권고를 제시한다.

---

### 3.2 조건 프롬프트 전문

모든 조건은 아래 **공통 래퍼**를 사용한다. `{과제}`에 T1/T2/T3 지시문 전문을 그대로 삽입한다.

#### 조건 A — baseline (공통, 전 과제)

```
다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

{과제}
```

#### 조건 B1a — 긍정형 간결성 지시 (H1)

```
답변은 초점을 좁혀 간결하게 작성하세요. 면책·주의 문구는 짧게 유지하고, 답변의 대부분을 핵심 내용에 씁니다. 설명을 요청받은 경우, 심화 설명을 별도로 요구받지 않았다면 개괄 수준으로 답합니다.

다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

{과제}
```

*(공식 스니펫 "Keep responses focused, brief, and concise. Keep disclaimers and caveats short, and spend most of the response on the main answer. When asked to explain something, give a high-level summary unless an in-depth explanation is specifically requested."의 한국어 렌더링. 언어 고정을 위해 번역했으며 이 번역 자체가 교란 요인일 수 있다 — §4 참조.)*

#### 조건 B1b — 부정형 간결성 지시 (H1 대조군)

```
장황하게 쓰지 마세요. 불필요한 배경 설명을 늘어놓지 말고, 같은 내용을 반복하지 마세요. 지나치게 자세히 설명하지 마세요.

다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

{과제}
```

#### 조건 B3 — 수치 상한 지시 (H3)

```
답변은 공백 포함 600자 이내로 작성하세요.

다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

{과제}
```

#### 조건 B4 — 서론·맺음말·자평·자기수정 서술 억제 (H4)

```
서론 없이 곧바로 본론으로 답하세요. "다음은 ~입니다", "~에 대해 설명드리겠습니다" 같은 도입 문구를 쓰지 않습니다. 답변을 끝맺는 요약 문단, 자기 평가(예: "도움이 되었기를 바랍니다"), 앞서 쓴 자기 서술을 정정하는 문장도 넣지 않습니다.

다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

{과제}
```

#### 조건 A6 — 과잉 검증 유발 지시 포함 (H6의 baseline; 처치는 "제거"이므로 방향이 반대)

```
답변하기 전에 스스로 한 번 더 검증하고, 빠뜨린 부분이 없는지 재확인한 뒤 답하세요. 사소하지 않은 과제라면 마지막에 검증 단계를 포함하세요.

다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

{과제}
```

> H6 비교: **A6(검증 지시 포함) → A(제거)**. A는 이미 위에 정의되어 있으므로 추가 실행 불필요.

---

### 3.3 T1 전용 조건 (H2 / H5 / H7)

H2·H5·H7은 과제별 전용 재료가 필요하므로 **T1(코드 설명)에서만** 실행한다. 재료 부담과 총 시행 수를 통제하기 위한 결정이며, 유의미한 효과가 관측되면 T2/T3으로 확장한다.

#### 공통 긴 컨텍스트 블록 `{CTX}` (H2 전용)

```
당신은 사내 백엔드 플랫폼 팀을 지원하는 기술 어시스턴트입니다. 이 팀은 결제 정산, 사용자 세션, 내부 검색 세 도메인을 담당하며 Python과 Go를 함께 사용합니다. 팀에는 주니어 3명, 시니어 2명이 있고 코드 리뷰는 최소 1인 승인제로 운영됩니다. 배포는 하루 2회 정기 배포와 긴급 핫픽스 절차가 따로 있으며, 스테이징 환경은 프로덕션과 데이터 스키마만 동일하고 트래픽 규모는 1/50 수준입니다. 관측 스택은 Prometheus와 Grafana를 쓰고, 로그는 구조화 JSON으로 수집합니다. 팀 규약상 새 외부 의존성 추가는 별도 승인을 받아야 하며, 표준 라이브러리로 해결 가능한 경우 표준 라이브러리를 우선합니다. 캐시 계층은 현재 Redis를 쓰지만 프로세스 로컬 캐시를 앞단에 두는 패턴도 일부 서비스에서 쓰입니다. 답변 대상은 이 팀의 구성원이며, 기본 개념보다는 이 코드베이스에서의 실제 함의를 알고 싶어 합니다.
```

**A2 (H2 baseline — 간결성 지시 없음)**
```
{CTX}

다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

{T1}
```

**B2a (앞부분에만 간결성 지시)**
```
답변은 초점을 좁혀 간결하게 작성하세요. 면책·주의 문구는 짧게 유지하고, 답변의 대부분을 핵심 내용에 씁니다.

{CTX}

다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

{T1}
```

**B2b (앞부분 + 말미 리마인더)**
```
답변은 초점을 좁혀 간결하게 작성하세요. 면책·주의 문구는 짧게 유지하고, 답변의 대부분을 핵심 내용에 씁니다.

{CTX}

다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

{T1}

<tone_preference>
출력 분량을 적당히 간결하게 유지하세요.
</tone_preference>
```

#### B5s — 짧은 예시 2개 (H5)

```
다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다. 아래 예시와 같은 방식으로 답합니다.

<examples>
<example>
질문: 아래 함수가 무엇을 하는지 설명해 주세요.

def dedupe(items):
    seen = set()
    out = []
    for i in items:
        if i not in out and i not in seen:
            seen.add(i)
            out.append(i)
    return out

답변: 리스트에서 중복을 제거하되 처음 등장한 순서를 보존합니다. `seen` 집합으로 이미 본 값을 O(1)에 판별합니다. 다만 `i not in out` 검사가 중복이라 리스트 선형 탐색이 매번 일어나며, 이 조건은 제거해도 동작이 같고 O(n)으로 빨라집니다. 값이 해시 가능해야 동작합니다.
</example>

<example>
질문: 아래 함수가 무엇을 하는지 설명해 주세요.

def retry(fn, times=3, delay=0.5):
    for n in range(times):
        try:
            return fn()
        except Exception:
            if n == times - 1:
                raise
            time.sleep(delay * (2 ** n))

답변: `fn`을 최대 `times`회 호출하고, 실패하면 지연을 2배씩 늘려(0.5s, 1s, 2s) 재시도합니다. 마지막 시도에서 실패하면 예외를 그대로 올립니다. 지터가 없어 동시 재시도가 몰릴 수 있고, `Exception`을 통째로 잡아 재시도해도 소용없는 오류까지 반복합니다.
</example>
</examples>

{T1}
```

#### B5l — 긴 예시 2개 (H5 대조군)

> 위 B5s와 **동일한 구조·동일한 예시 질문**을 쓰되, 각 예시의 `답변:` 부분을 아래 규칙으로 확장한다. 확장된 답변 본문은 실행 전에 작성해 파일로 고정하고, 3회 시행 내내 동일한 문자열을 사용한다.
> - 각 예시 답변을 **도입 한 문장 + 소제목 3개(동작 개요 / 단계별 흐름 / 주의점) + 마무리 요약 문단** 구조로 확장한다.
> - 각 예시 답변의 공백 제외 문자 수가 **B5s 대응 답변의 4~6배**가 되도록 한다(실측해서 맞춘다).
> - 담긴 **사실 내용은 B5s와 동일**해야 한다. 새 사실을 추가하면 길이 외 변수가 섞인다.

#### A7 / B7 — 프롬프트 스타일 매칭 (H7)

**A7 (마크다운 렌더링 지시문)**
```
다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

## 과제
아래 Python 클래스가 무엇을 하는지 설명합니다.

### 다뤄야 할 것
- 자료구조 선택
- 만료 처리
- 축출 정책

### 코드
```python
(T1의 코드 블록 그대로)
```
```

**B7 (평문 산문 렌더링 지시문 — 내용 동일, 마크업 없음)**
```
다음 과제를 수행해 주세요. 답변은 한국어로 작성합니다.

아래 Python 클래스가 무엇을 하는지 설명해 주세요. 자료구조 선택, 만료 처리, 축출 정책을 다뤄 주세요. 코드는 다음과 같습니다.

import time
from collections import OrderedDict

class TTLCache:
    def __init__(self, capacity=128, ttl=60.0):
        self.capacity = capacity
        self.ttl = ttl
        self._store = OrderedDict()

    def get(self, key):
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key, value):
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, time.monotonic() + self.ttl)
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)
```

---

### 3.4 시행 계획

| 그룹 | 조건 | 과제 | n | 실행 수 |
|---|---|---|---|---|
| 공통 | A, B1a, B1b, B3, B4, A6 (6개) | T1, T2, T3 | 3 | 54 |
| T1 전용 | A2, B2a, B2b, B5s, B5l, A7, B7 (7개) | T1 | 3 | 21 |
| **합계** | | | | **75** |

- **n = 3** (조건×과제당). 각 시행은 **독립된 새 서브에이전트 인스턴스**여야 하며, 이전 시행의 컨텍스트를 공유하지 않는다.
- 실행 순서는 조건별로 몰아서 돌리지 말고 **과제 단위로 라운드로빈**(T1의 A → T1의 B1a → … → T1의 A6 → 다시 2회차)한다. 세션 드리프트가 특정 조건에 몰리는 것을 막는다.
- 단계적 실행 권장: **Phase 1 = H1/H4/H6(공통 그룹 중 A, B1a, B1b, B4, A6)** → 효과 확인 후 Phase 2 = H3 + T1 전용 그룹.
- 서브에이전트는 파일 쓰기 없이 **최종 응답 텍스트로만** 답하게 한다. 응답 전문을 `experiments/raw/{과제}_{조건}_{회차}.md`에 그대로 저장한다(측정 담당이 저장; 피험 에이전트에게 저장 지시를 주면 메타 인지가 생긴다).

### 3.5 측정 방법

측정 대상은 **피험 에이전트의 최종 응답 텍스트 1건**. 도구 호출 로그·중간 산출물은 제외한다.

| 지표 | 정의 |
|---|---|
| `chars_prose` (**주 지표**) | 펜스 코드 블록(```` ``` ```` … ```` ``` ````)을 **제거한 뒤** 모든 공백·개행을 제거한 문자 수 |
| `chars_code` | 펜스 코드 블록 내부의 공백 제외 문자 수 (별도 기록, 주 지표에 미포함) |
| `chars_total` | 코드 포함, 공백 제외 전체 문자 수 |
| `words` | 공백 기준 어절 수 (코드 블록 제외) |
| `lines` | 비어 있지 않은 줄 수 (코드 블록 제외) |
| `markup_ratio` | `#`, `*`, `-`(줄머리), `|` 등 마크다운 마크업 문자 수 ÷ `chars_total` (H7 전용) |

**코드 블록을 주 지표에서 제외하는 이유**: T1/T3에서 조건에 따라 코드 인용 여부가 갈리면 산문 길이 비교가 오염된다. 다만 "코드를 길게 인용해서 산문이 짧아진 것"을 놓치지 않기 위해 `chars_code`를 함께 기록하고, 판정 시 `chars_total`도 확인한다.

**보고 규칙**
- 조건별로 n=3의 **중앙값**을 대표값으로, 최소·최대를 함께 기록한다(n=3에서 평균은 이상치에 약하다).
- 결과는 **조건 간 상대비(A 대비 %)** 로만 보고한다. 절대 토큰 수로 환산하지 않는다. 모든 수치에 `(proxy)` 표기.
- 한국어는 문자↔토큰 비율이 영어와 다르므로 **다른 축의 영어 실험 결과와 직접 비교하지 않는다.**

**계수 스크립트 (그대로 사용)**

```python
# scripts/count.py  —  usage: python count.py experiments/raw/*.md
import re, sys, glob, json

FENCE = re.compile(r"```.*?```", re.S)

def measure(text: str) -> dict:
    code = "".join(FENCE.findall(text))
    prose = FENCE.sub("", text)
    nows = lambda s: len(re.sub(r"\s", "", s))
    markup = len(re.findall(r"[#*|`]|^\s*[-+]\s", text, re.M))
    return {
        "chars_prose": nows(prose),
        "chars_code": nows(code),
        "chars_total": nows(text),
        "words": len(prose.split()),
        "lines": len([l for l in prose.splitlines() if l.strip()]),
        "markup_ratio": round(markup / max(nows(text), 1), 4),
    }

for path in sorted(p for a in sys.argv[1:] for p in glob.glob(a)):
    with open(path, encoding="utf-8") as f:
        print(path, json.dumps(measure(f.read()), ensure_ascii=False))
```

### 3.6 품질 판정 기준

"짧아졌지만 답이 빠졌다"를 걸러내는 것이 목적. **길이만 보고 채택하지 않는다.**

1. **체크리스트 채점.** 각 응답을 §3.1의 과제별 5개 항목으로 채점(항목당 0 또는 1, 총 0~5점). 채점자는 **조건 라벨을 모르는 상태**에서 채점한다(파일명을 난수 ID로 바꿔 블라인드 채점).
2. **형식 위반 감점(별도 기록, 총점에 미포함).**
   - 요청한 언어가 아님(한국어 아님) → 해당 시행 **무효 처리 후 재실행**.
   - 응답이 잘림/미완결 → 무효 처리 후 재실행.
3. **채택 판정 규칙**
   - **채택**: 조건 B의 `chars_prose` 중앙값이 A 대비 **10% 이상 감소**하고, 체크리스트 중앙값이 A 대비 **감소하지 않음**(동점 이상).
   - **조건부**: 길이 10% 이상 감소했으나 체크리스트 중앙값이 **1점 감소** → "길이-품질 트레이드오프 있음"으로 기록. 축 종합 판정 에이전트에게 트레이드오프와 함께 넘긴다.
   - **기각**: 체크리스트 중앙값이 2점 이상 감소, 또는 길이 감소가 10% 미만.
   - 3회 시행 중 **2회 이상이 같은 방향**이 아니면 "불안정 — 시행 수 증가 필요"로 기록하고 채택/기각하지 않는다.
4. **H3 전용 추가 판정**: 수치 상한 조건은 체크리스트 점수 하락 여부가 곧 가설의 핵심이므로, 하락이 관측되면 그것이 **가설 지지**다(다른 가설과 판정 방향이 반대임에 주의).
5. **H5 전용 추가 판정**: B5s와 B5l의 `chars_prose` 중앙값이 예시 답변 길이의 순서(짧음 < 김)를 따르는지 확인. 순서가 뒤집히면 앵커링 가설 기각.
6. **H7 전용 추가 판정**: `chars_prose`와 함께 `markup_ratio`도 감소해야 지지. 길이만 줄고 마크업 비율이 그대로면 스타일 전이가 아닌 다른 원인이다.

---

## 4. 한계 / 교란 요인

1. **문자 수는 토큰의 대리 지표(proxy)일 뿐이다.** 한국어는 영어보다 문자당 토큰 수가 많고, 어절·조사 구조 때문에 문자↔토큰 비율이 문장마다 흔들린다. API 키 확보 시 `usage.output_tokens` 기준으로 전량 재측정해야 한다.
2. **사고(thinking) 토큰이 측정에서 완전히 빠진다.** 청구되는 출력 토큰에는 thinking이 포함되지만(공식 문서: 사고 토큰은 output 토큰으로 과금), 우리는 최종 텍스트만 잰다. 어떤 지시문이 가시 응답은 줄이면서 사고를 늘린다면 **실제 절감이 아닌데 절감으로 보일 수 있다.** 이 실험의 가장 큰 구조적 한계.
3. **`effort` / thinking 설정을 통제할 수 없다.** 서브에이전트 실행 시 어떤 effort로 도는지 우리가 지정하지 못한다. 조건 간 동일하다고 가정하지만 검증 불가.
4. **모델 버전을 고정할 수 없다.** 서브에이전트가 어떤 Claude 모델로 도는지 세션에 따라 달라질 수 있다. 최소한 라운드로빈 실행으로 조건별 편향은 줄이지만 제거하지는 못한다.
5. **system/user 위치를 진짜로 분리하지 못한다.** H2는 "단일 프롬프트의 앞/뒤"만 검증한다. 공식 권고는 *긴 system prompt*를 전제하므로, 우리 결과가 그대로 일반화되지 않는다.
6. **공식 스니펫을 한국어로 번역해 사용했다.** 문서는 "steering effectiveness can be sensitive to exact wording"이라고 경고한다. 번역 자체가 효과 크기를 바꿀 수 있고, 원문 영어 지시 + 한국어 출력 조합과도 다를 수 있다. 여력이 되면 B1a의 영어 원문 버전을 추가 arm으로 두는 것이 좋다.
7. **n=3은 작다.** 자유 서술형(T3)은 조건 내 분산이 클 것으로 예상되며, 10% 미만의 효과는 이 시행 수로 검출되지 않는다. 유망한 가설은 n을 5~10으로 올려 재실행해야 한다.
8. **처치 프롬프트 자체가 입력 토큰을 늘린다.** 간결성 지시 40자를 넣어 출력 100자를 줄였다면 순이득이지만, 프롬프트 캐시가 없는 단발 호출에서는 이득이 상쇄될 수 있다. 축 종합 판정 시 입력 증가분을 함께 보고해야 한다.
9. **체크리스트가 길이에 유리하게 편향될 수 있다.** 5개 항목을 모두 언급하려면 최소 길이가 필요하므로, 극단적 압축 조건(B3 600자)은 구조적으로 불리하다. 이것은 의도된 설계(트레이드오프 검출)지만, "간결성 = 나쁨"으로 오독하지 않도록 판정 시 명시한다.
10. **naive 유지의 취약성.** 처치 프롬프트가 "간결하게 쓰라"고 말하는 순간 피험 에이전트는 길이가 관심사임을 안다. 이것은 처치의 본질이라 제거 불가능하지만, "이 저장소는 토큰 절감 연구를 한다"는 맥락이 새어나가면 baseline까지 오염된다. **피험 에이전트에게 저장소 경로·CLAUDE.md·연구 목적을 절대 노출하지 않는다.**
11. **번들 스킬 문서 출처의 한계.** §1.8·§1.11의 근거는 로컬 `claude-api` 스킬 번들 문서이며 공개 URL이 없다. 공개 문서와 충돌하는 부분(20% 수치)은 우리 수치로 인용하지 않는다.
