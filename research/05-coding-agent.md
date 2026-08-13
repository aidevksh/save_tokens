# 축 5 — 코딩 에이전트

## 1. 리서치 요약 (출처 URL 필수)

결론부터: 이 축에서 **출력 토큰을 줄이는 유일하게 문서화된 레버는 프롬프트 지시문**이다. `effort`는 사고량을 줄이지만 가시 출력 길이는 신뢰성 있게 줄이지 못한다고 공식 문서가 명시한다.

| # | 발견 | 근거 | 출처 |
|---|---|---|---|
| F1 | Opus 5의 기본 사용자 대면 응답이 이전 Opus보다 길다. effort를 낮춰도 가시 응답이 짧아지지 않는다 → 길이는 프롬프트로 지시해야 한다 | "Effort controls thinking volume, not visible response length: on Claude Opus 5, changing effort does not reliably shorten responses, so prompt for length instead." | [effort.md](https://platform.claude.com/docs/en/build-with-claude/effort), [prompting-claude-opus-5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) |
| F2 | Opus 5는 **시키지 않아도 자기검증**한다. 검증 지시를 남겨두면 과잉검증이 발생하고, 제거하면 품질 손실 없이 토큰이 준다 | "removing them reduces wasted tokens with no loss in quality" | [prompting-claude-opus-5 §Task scope and over-verification](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) |
| F3 | Opus 5는 **도구 호출 사이 나레이션이 늘었다**("무엇을 할지 예고"). 억제/조정 모두 "원하는 cadence를 명시"로 가능 | "Claude Opus 5 narrates readily during agentic work… its per-message output in agentic sessions is often longer than prior models'" | [prompting-claude-opus-5 §User-facing progress updates](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) |
| F4 | **디스크에 쓰는 산출물(리포트·마크다운·요약)도 길어졌다.** 대화 verbosity와 별개의 축이며 별도 지시가 필요 | "files that Claude Opus 5 writes to disk (reports, Markdown documents, summaries) are often longer than on prior models" | 동상 §Written deliverable length |
| F5 | **작업 범위 확장(scope creep)**: 요청하지 않은 단계를 추가하거나 과제 정의를 스스로 바꾼다 | "Claude Opus 5 can also expand the scope of a task, adding steps that weren't requested" | 동상 §Task scope and over-verification |
| F6 | **서브에이전트 위임 성향이 이전 모델보다 강하다.** 작은 작업에 쓰면 비용·시간이 배가된다 → 명시적 캡 필요. (Opus 4.8은 반대로 *덜* 위임했으므로, 4.8용 "더 위임하라" 지시는 제거 대상) | "Claude Opus 5 delegates to subagents more readily than prior models… it multiplies cost and time when applied to small tasks" | 동상 §Controlling subagent spawning; [migration-guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) |
| F7 | **자기수정 서술(correction narration)이 늘었다** | "The model also narrates corrections to its earlier statements more than prior models do, which can be undesirable in user-facing products." | 동상 §Self-correction |
| F8 | effort 하향은 **도구 호출 사이 preamble·도구 호출 수·주석 분량**을 동시에 줄인다 → 나레이션/주석 밀도는 부분적으로 effort의 함수 | "Lower effort levels tend to: Combine multiple operations into fewer tool calls / Make fewer tool calls / Proceed directly to action without preamble / Use terse confirmation messages after completion". 높은 effort는 "Include more comprehensive code comments" | [effort.md §Effort with tool use](https://platform.claude.com/docs/en/build-with-claude/effort) |
| F9 | 코드 리뷰 하네스에서 "high-severity만 보고" 류 지시는 문자 그대로 지켜져 리콜을 떨어뜨린다 → **짧아진 출력이 곧 절감이 아니라 과제 미수행일 수 있다.** 완수도 판정이 필수인 이유 | "the model may follow that instruction literally and report less" | [prompting-claude-opus-5 §Capability improvements](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) |
| F10 | 서브에이전트는 자기 컨텍스트에서 수만 토큰을 쓰고 **1,000~2,000 토큰의 요약만 반환**한다 → 오케스트레이터 *입력* 컨텍스트는 아끼지만 시스템 *총 출력*은 늘린다 | "may use tens of thousands of tokens or more, but returns only a condensed, distilled summary of its work (often 1,000-2,000 tokens)" | [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) |
| F11 | Claude Code 측 레버: `CLAUDE.md`는 **200줄 이하** 권장, 길수록 준수율이 떨어진다. 구체적·간결·구조화된 지시가 가장 잘 지켜진다 | "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." / "The more specific and concise your instructions, the more consistently Claude follows them." | [code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory) |
| F12 | Claude Code에는 출력 형태에 직접 작용하는 설정이 있다: `outputStyle`(시스템 프롬프트 일부), `effortLevel`(low/medium/high/xhigh 세션 지속), `agent`(메인 스레드를 특정 서브에이전트로 실행) | 설정 문서 표 | [code.claude.com/docs/en/settings](https://code.claude.com/docs/en/settings) |
| F13 | `CLAUDE.md`는 **시스템 프롬프트가 아니라 시스템 프롬프트 뒤의 user 메시지**로 전달된다 → 준수는 확률적. 강제하려면 hook을 써야 한다 | "CLAUDE.md content is delivered as a user message after the system prompt, not as part of the system prompt itself… there's no guarantee of strict compliance" | [code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory) |
| F14 | 서브에이전트 사용 판단 기준(공식): 메인 대화를 쓰라 — "quick, targeted change", "Latency matters. Subagents start fresh and may need time to gather context" | 문서 표 | [code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents) |

**축 5 전체에 대한 함의**: F1~F7은 전부 "Opus 5가 기본값으로 더 많이 말한다 → 프롬프트로 눌러라" 형태다. 즉 이 축의 절감 기법은 **CLAUDE.md / 시스템 프롬프트에 넣는 억제 지시문 묶음**으로 구현되며, 그 효과 크기는 아직 공개 수치가 없다(공식 문서는 "reduces wasted tokens"라고만 서술). 수치는 측정 필요.

---

## 2. 공식 문서에서 확인된 실전 프롬프트 스니펫 (원문 인용 + 출처)

아래는 Anthropic이 공식적으로 제시한 억제 프롬프트 **원문**이다. 실험 조건 B는 이 문구들을 그대로 쓴다(번역·의역 금지 — 문구가 곧 처치 변수다).

### S1. 응답 verbosity 억제
출처: [prompting-claude-opus-5 §Response length and verbosity](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)
```text
Keep responses focused, brief, and concise. Keep disclaimers and caveats short, and spend most of the response on the main answer. When asked to explain something, give a high-level summary unless an in-depth explanation is specifically requested.
```

### S2. 긴 시스템 프롬프트 말미의 재확인 태그
출처: 동상
```text
<tone_preference>
Keep outputs reasonably concise.
</tone_preference>
```

### S3. 도구 호출 사이 나레이션 cadence 지정 (축 5의 핵심 스니펫)
출처: [prompting-claude-opus-5 §User-facing progress updates](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)
```text
Before your first tool call, say in one sentence what you're about to do. While working, give a brief update only when you find something important or change direction. When you finish, lead with the outcome: your first sentence should answer "what happened" or "what did you find," with supporting detail after it for readers who want it.
```
동 절의 방법론 원칙(중요): *"Positive examples of the communication style you want tend to be more effective than instructions about what not to do."* — 즉 "…하지 마라"보다 원하는 형태의 긍정 예시가 낫다. 마이그레이션 가이드도 같은 취지: *"Positive examples showing how Claude can communicate with the appropriate level of concision tend to be more effective than negative examples or instructions that tell the model what not to do."* ([migration-guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide))

### S4. 마크다운 산출물 길이 팽창 억제
출처: [prompting-claude-opus-5 §Written deliverable length](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)
```text
Match the length of written documents to what the task needs: cover the substance, but do not pad with filler sections, redundant summaries, or boilerplate.
```

### S5. 작업 범위 확장 억제
출처: 동상 §Task scope and over-verification
```text
Deliver what was asked, at the scope intended. Make routine judgment calls yourself, and check in only when different readings of the request would lead to materially different work. If the request seems mistaken or a better approach exists, say so in a sentence and continue with the task as asked rather than quietly narrowing, widening, or transforming it. Finish the whole task, and stop short of actions that are clearly beyond what was asked.
```

### S6. 서브에이전트 과다 위임 억제
출처: 동상 §Controlling subagent spawning
```text
Delegate to a subagent only for large tasks that are genuinely independent and parallelizable, such as a wide multi-file investigation. Do not delegate work you can finish yourself in a handful of tool calls, and do not use subagents to verify or double-check your own work. If one subagent can complete the task, use one rather than several, and keep spawn counts low.
```

### S7. 자기수정 서술 억제
출처: 동상 §Self-correction
```text
Only correct an earlier statement when the error would change the user's code, conclusions, or decisions. State corrections plainly and briefly, then continue the task. For slips that change nothing for the user, make the fix and move on without noting it.
```

### S8. 불필요한 자기검증 제거 — **추가가 아니라 삭제 지시**
출처: 동상 §Task scope and over-verification / §Self-correction / [migration-guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide)
> "If your prompt contains explicit verification instructions ("include a final verification step for any non-trivial task," "use a subagent to verify"), **remove them**: instructions like these cause over-verification on Claude Opus 5, and removing them reduces wasted tokens with no loss in quality. The same applies to legacy harness scaffolding that adds separate verification steps."
>
> "Avoid instructing re-checks it already performs ("double-check your answer," "re-verify before responding"); like verification instructions, these compound with the model's own behavior and add cost without improving results."
>
> (migration guide) "Remove verification and self-check instructions carried over from prompts tuned for earlier models; they cause over-verification on Claude Opus 5."

### S9. 코드 주석 밀도 + 나레이션을 함께 다루는 확장 블록 (마이그레이션 가이드 수록)
출처: [migration-guide → Migrating to Claude Opus 5 → Behavioral shifts](https://platform.claude.com/docs/en/about-claude/models/migration-guide). 마지막 두 문단이 **코드 주석 밀도**를 직접 다루는 유일한 공식 문구다.
```text
# Communicating with the user
Your text output is what the user reads between tool calls; they usually can't see your thinking or the raw tool results. Write it for a teammate who stepped away and is catching up, not for a log file: they don't know the codenames or shorthand you created along the way, and they didn't watch your process unfold. Before your first tool call, say in a sentence what you're about to do; while working, give brief updates when you find something load-bearing or change direction.

Lead with the outcome. Your first sentence after finishing should answer "what happened" or "what did you find" — the thing the user would ask for if they said "just give me the TLDR." Supporting detail and reasoning should come after, for readers who want them.

Being readable and being concise are different things, and readable matters more. If the user has to reread your summary or ask you to explain, any time saved by brevity is gone. The way to keep output short is to be selective about what you include (drop details that don't change what the reader would do next), not to compress the writing into fragments, abbreviations, arrow chains like `A → B → fails`, or jargon. What you do include, write in complete sentences with the technical terms spelled out. Don't make the reader cross-reference labels or numbering you invented earlier; say what you mean in place.

Match the response to the question: a simple question should be answered with a direct answer in prose, not headers and sections. Use tables only for short enumerable facts, with explanations in the surrounding prose rather than the cells. Calibrate to the user — a bit tighter for an expert, more explanatory for someone newer.

Write code that reads like the surrounding code: match its comment density, naming, and idiom.

Only write a code comment to state a constraint the code itself can't show — never to say where it came from, what the next line does, or why your change is correct; that's you talking to the reviewer, not the next reader, and it's noise the moment the PR merges.
```

### S10. 범용 verbosity 억제 한 줄 (모델 무관, 마이그레이션 가이드)
출처: [migration-guide → Behavior changes](https://platform.claude.com/docs/en/about-claude/models/migration-guide)
```text
Provide concise, focused responses. Skip non-essential context, and keep examples minimal.
```

> **주의(S1~S10 공통)**: 이 문구들은 Anthropic이 *권장 예시*로 제시한 것이며, 문서 어디에도 절감률 수치가 붙어 있지 않다. 효과 크기는 본 저장소에서 측정해야 한다.

---

## 3. 가설

| ID | 가설 | 처치 | 1차 종속변수 |
|---|---|---|---|
| **H1** | CLAUDE.md에 S3(나레이션 cadence) 지시가 있을 때, 없을 때 대비 에이전트의 **사용자 대면 텍스트 총량**(도구 호출 사이 텍스트 + 최종 응답)이 감소하며 과제 완수도는 유지된다 | S3 | `user_facing_chars_total` |
| **H2** | 조건 A에 "각 변경 후 검증 단계를 반드시 포함하라" 류의 **검증 지시가 있을 때** 대비, 이를 **제거**하면 도구 호출 수와 사용자 대면 텍스트가 감소하고 테스트 통과율은 동일하다 (S8 검증) | 검증 지시 삭제 | `tool_calls`, `user_facing_chars_total` |
| **H3** | S1+S3의 "마지막 요약" 규칙이 있을 때 **최종 응답 문자 수**가 감소하며, 완수도 체크리스트 점수는 유지된다 | S1+S3 | `final_response_chars` |
| **H4** | S5(범위 제한)가 있을 때 **생성·수정된 코드 줄 수**와 요청되지 않은 산출물(신규 파일·README·헬퍼 추상화) 개수가 감소하며 테스트 통과율은 유지된다 | S5 | `total_lines`, 미요청 산출물 개수 |
| **H5** | S9의 주석 규칙이 있을 때 **생성 코드의 주석 밀도**(`#`/`//` 줄 비율)가 감소하며 테스트 통과율은 유지된다 | S9 마지막 2문단 | `comment_density` |
| **H6** | S6(서브에이전트 캡)이 있을 때 소규모 코딩 과제에서 **서브에이전트 호출이 0회**로 수렴하고 총 출력이 감소하며 완수도는 유지된다 | S6 | `subagent_calls`, `user_facing_chars_total` |
| **H7** | S1·S3·S5·S6·S7·S9를 **모두 합친 묶음**의 절감 효과는 개별 처치 효과의 산술합보다 **작다**(하위가산성/포화). 즉 억제 지시를 늘릴수록 한계 효용이 체감한다 | 묶음 vs 단일 요인 | `user_facing_chars_total`의 조건별 차이 |

기각 조건(모든 가설 공통): 처치 조건에서 §4.5 완수도 체크리스트를 **하나라도 통과하지 못하면** 해당 시행은 "절감 성공"으로 집계하지 않고, 3회 중 2회 이상 미완수면 가설을 기각한다.

---

## 4. 실험 프로토콜

### 4.0 픽스처 (이미 생성됨)

| 경로 | 내용 | 기준 상태 |
|---|---|---|
| `experiments/fixtures/task-a-bugfix/stats.py` + `test_stats.py` | 버그 3개(정수 나눗셈 `mean`, 정렬·짝수 미처리 `median`, 빈 입력/동점 미처리 `mode`) | `python -m unittest test_stats` → 11개 중 **6 실패** |
| `experiments/fixtures/task-b-refactor/ingest.py` + `test_ingest.py` | 3개 로더에 파싱·검증 로직이 그대로 3중 복제 (68줄) | 테스트 **5/5 통과** (동작 보존 리팩터링 과제) |
| `experiments/fixtures/task-c-feature/todo.js` + `todo.test.js` | `complete()` / `list(status)` 미구현 (42줄) | `node --test` → 9개 중 **5 실패** |
| `experiments/fixtures/verify/verify_a.py`, `verify_b.py`, `verify_c.js` | **심사자 전용** 완수도 검증기. 제공 테스트 통과 + 테스트 파일 무수정 + **피험자가 본 적 없는 신규 입력** 검증(테스트 피팅 방지) | 기준 상태에서 각각 FAIL |
| `experiments/fixtures/code_metrics.py` | 코드 산출물 구조 지표 수집기. `code` 모드(줄 수·주석 밀도) / `transcript` 모드(stream-json 파싱, 라운드 2 전용). **길이 계측은 `tools/measure.py` 로 통일** — 이름 분리 경위는 `experiments/round1-plan.md` §4 | 동작 확인 완료 |

환경: Python 3.13, Node v22.15.0 확인됨.

### 4.1 실행 방식

**P1 (권장) — `claude -p` 서브프로세스 + stream-json 트랜스크립트.** 도구 호출 *사이* 텍스트까지 측정 가능한 유일한 방법.

```bash
# 1) 시행 디렉터리는 반드시 저장소 밖에 만든다 (아래 4.6 오염 통제 참조)
TRIAL="$SCRATCH/trial_A_a_1"
mkdir -p "$TRIAL"
cp experiments/fixtures/task-a-bugfix/* "$TRIAL/"
cp conditions/A.md "$TRIAL/CLAUDE.md"     # 조건 B면 conditions/B.md

# 2) 실행 (모델·effort는 조건 간 고정)
cd "$TRIAL" && claude -p "$(cat ../prompt_a.txt)" \
  --model claude-opus-5 \
  --output-format stream-json --verbose \
  > "$TRIAL/run.ndjson"

# 3) 측정
python experiments/fixtures/code_metrics.py transcript "$TRIAL/run.ndjson"
python experiments/fixtures/code_metrics.py code "$TRIAL" experiments/fixtures/task-a-bugfix
python experiments/fixtures/verify/verify_a.py "$TRIAL"
```

**P2 (대체) — Agent 툴 서브에이전트.** `claude -p` 실행이 막혔을 때. 조건은 CLAUDE.md 대신 **프롬프트 프리픽스**로 주입한다. 한계: 부모는 서브에이전트의 최종 보고만 보므로 `final_response_chars`·`subagent_calls`·코드 지표만 측정 가능하고 **H1의 중간 나레이션은 측정 불가**.

### 4.2 조건 프롬프트 전문 (복사해 그대로 사용)

**조건 A — `conditions/A.md`** (억제 지시 없음 + 구모델 관행 잔재. 이것이 대조군이다)

```markdown
# Project instructions

This is a small standalone code exercise. Python 3.13 and Node 22 are available.

- Respond in English.
- Run the project's test suite to check your work.
- Include a final verification step for any non-trivial task, and double-check your answer before responding.
```

**조건 B — `conditions/B.md`** (S1·S3·S5·S6·S7·S9 묶음, 검증 지시 제거)

```markdown
# Project instructions

This is a small standalone code exercise. Python 3.13 and Node 22 are available.

- Respond in English.
- Run the project's test suite to check your work.

## Communicating with the user

Before your first tool call, say in one sentence what you're about to do. While working, give a brief update only when you find something important or change direction. When you finish, lead with the outcome: your first sentence should answer "what happened" or "what did you find," with supporting detail after it for readers who want it.

Keep responses focused, brief, and concise. Keep disclaimers and caveats short, and spend most of the response on the main answer. When asked to explain something, give a high-level summary unless an in-depth explanation is specifically requested.

Only correct an earlier statement when the error would change the user's code, conclusions, or decisions. State corrections plainly and briefly, then continue the task. For slips that change nothing for the user, make the fix and move on without noting it.

## Scope

Deliver what was asked, at the scope intended. Make routine judgment calls yourself, and check in only when different readings of the request would lead to materially different work. If the request seems mistaken or a better approach exists, say so in a sentence and continue with the task as asked rather than quietly narrowing, widening, or transforming it. Finish the whole task, and stop short of actions that are clearly beyond what was asked.

## Delegation

Delegate to a subagent only for large tasks that are genuinely independent and parallelizable, such as a wide multi-file investigation. Do not delegate work you can finish yourself in a handful of tool calls, and do not use subagents to verify or double-check your own work. If one subagent can complete the task, use one rather than several, and keep spawn counts low.

## Code

Write code that reads like the surrounding code: match its comment density, naming, and idiom.

Only write a code comment to state a constraint the code itself can't show — never to say where it came from, what the next line does, or why your change is correct; that's you talking to the reviewer, not the next reader, and it's noise the moment the PR merges.

<tone_preference>
Keep outputs reasonably concise.
</tone_preference>
```

> 조건 A와 B의 공통 서두 3줄(과제 성격·언어·테스트 실행)은 **바이트 단위로 동일**해야 한다. 차이는 억제 블록의 유무와 검증 지시 유무뿐이다.

### 4.3 과제 프롬프트 전문 (조건 A/B 동일)

**`prompt_a.txt`**
```text
The tests in test_stats.py are failing. Fix the bugs in stats.py so the whole suite passes. Do not modify test_stats.py.
```

**`prompt_b.txt`**
```text
ingest.py contains three loader functions that repeat the same parse, validate, and coerce logic. Refactor ingest.py to remove that duplication. The public behaviour of load_users, load_orders, and load_products must not change, and test_ingest.py must keep passing unmodified.
```

**`prompt_c.txt`**
```text
Some tests in todo.test.js are failing because todo.js is missing the complete() function and status filtering in list(). Implement them so the whole suite passes. Do not modify todo.test.js.
```

### 4.4 설계와 시행 횟수

- **Phase 1 (묶음 효과, H1·H2·H3·H4·H5·H6 스크리닝)**: 2 조건(A/B) × 3 과제(a/b/c) × **n=3** = 18 시행.
- **Phase 2 (요인 분해, H7)**: Phase 1에서 유의미하게 움직인 지표에 대해 과제 A 하나만 골라 단일 요인 조건 B1(=S3만), B2(=검증 지시 제거만), B4(=S5만), B5(=S9만), B6(=S6만)을 각 n=3. 개별 효과의 합 vs 묶음 효과를 비교해 H7을 판정한다.
- **순서**: 시행을 A,B,A,B… 로 교대 배치하고 과제 순서는 시행마다 로테이션한다(드리프트·캐시 효과 통제).
- **고정값**: 모델 ID, effort, `max_tokens`, 도구 허용 목록, 응답 언어(English)를 조건 간 동일하게 고정하고 원시 결과에 기록한다.

### 4.5 완수도 판정 체크리스트 (짧아졌지만 덜 했으면 기각)

시행 결과를 `experiments/raw/05-<phase>-<condition>-<task>-<n>/` 에 저장하고 아래를 **전부** 통과해야 "완수"로 집계한다.

**공통 (전 과제)**
- [ ] 검증 스크립트가 exit 0 (`verify_a.py` / `verify_b.py` / `verify_c.js`)
- [ ] 제공된 테스트 파일이 바이트 단위로 무수정
- [ ] 피험자가 본 적 없는 신규 입력 검증 통과 (테스트 하드코딩·특수 케이스 처리로 통과하지 않았음)
- [ ] 과제와 무관한 파일을 생성·수정하지 않음 (요청되지 않은 README/문서/설정 파일 0개)
- [ ] 최종 응답이 "무엇을 했는지"를 명시함 (완료 여부를 사용자가 알 수 있음)

**과제 A 추가**
- [ ] `mean`·`median`·`mode` **세 함수 모두** 수정됨 (한두 개만 고치고 테스트가 우연히 통과하지 않았음)

**과제 B 추가**
- [ ] `ingest.py`에 필드 개수 검증과 빈 필드 검증이 각각 1회만 존재 (실제로 중복이 제거됨)
- [ ] 세 로더의 공개 시그니처가 그대로 유지됨
- [ ] `ingest.py` 줄 수가 기준(68줄) 이하

**과제 C 추가**
- [ ] `complete()`가 미존재 id에 `null`을 반환하고 멱등적임
- [ ] `list()`가 인자 없이 호출되면 전체를 반환하고, 잘못된 status에는 throw함
- [ ] `add`/`remove`/`render`/`get`의 기존 동작이 깨지지 않음

### 4.6 측정 지표

`measure.py transcript` 출력 (P1 전용):

| 지표 | 정의 | 대응 가설 |
|---|---|---|
| `final_response_chars` | 도구 호출을 포함하지 않는 **마지막 assistant 메시지**의 텍스트 문자 수 = 종료 요약 | H3 |
| `interstitial_chars` / `interstitial_blocks` | 그 이전 assistant 메시지들의 텍스트 문자 수 / 텍스트가 있었던 메시지 개수 = 도구 호출 사이 나레이션 | H1 |
| `user_facing_chars_total` | 위 둘의 합 | H1, H6, H7 |
| `tool_calls`, `subagent_calls` | `tool_use` 블록 수 / `Task`·`Agent` 툴 호출 수 | H2, H6 |

`measure.py code` 출력: `nonblank_code_lines`, `comment_lines`, `comment_density`, `total_lines`, `baseline_lines` → H4, H5.

**보고 규칙**: 전부 문자/줄 수의 **조건 간 상대 비율**로만 보고하고 `(proxy)` 표기. 절대 토큰 수로 환산하지 않는다. 조건 간 언어를 English로 고정했으므로 문자↔토큰 비율은 조건 간 대략 일정하다고 가정한다(§5 참조).

### 4.7 오염 통제 (필수)

1. **시행 디렉터리를 이 저장소 밖에 만든다.** 이 저장소의 `CLAUDE.md`에는 이미 "결론부터·서론 금지·표 사용·변경분만 출력" 같은 **조건 B와 동일한 성격의 억제 규칙**이 들어 있다. 저장소 안에서 실험하면 조건 A가 오염되어 효과가 0에 수렴한다. 시행 디렉터리는 스크래치패드나 `%TEMP%` 아래에 둔다.
2. 상위 디렉터리에 `CLAUDE.md`가 없는 경로를 고른다. 시행 시작 시 `/context`(또는 `InstructionsLoaded` 훅)로 **실제로 로드된 메모리 파일 목록**을 기록한다.
3. 사용자 스코프 `~/.claude/CLAUDE.md`와 auto memory는 A/B 양쪽에 동일하게 걸리므로 차이를 상쇄하지만, 존재 여부와 대략적 크기를 원시 결과에 기록한다.
4. 피험 에이전트에게 토큰 실험임을 알리지 않는다. 조건 파일명은 `A.md`/`B.md`가 아니라 무의미한 이름으로 바꿔 저장한 뒤 `CLAUDE.md`로 복사한다.

---

## 5. 한계 / 교란 요인

| # | 한계 | 영향 | 완화 |
|---|---|---|---|
| L1 | **API 호출 불가** → `usage.output_tokens` 측정 불가. 모든 수치가 문자 수 proxy | 절대 절감률 산출 불가 | 상대 비율로만 보고. API 키 확보 시 전량 재측정 |
| L2 | **thinking 토큰이 측정에서 완전히 누락된다.** Opus 5는 raw chain of thought를 반환하지 않고, `display`도 기본 `omitted`다. 억제 지시가 가시 출력을 줄이면서 사고 토큰을 늘리는 경우 proxy는 절감을 과대평가한다 | H1·H3의 효과가 과대 추정될 수 있음 | `display: "summarized"`로 요약 사고량이라도 기록하거나, 이 축의 결론에 "가시 출력 한정" 단서를 반드시 붙인다 |
| L3 | **`effort`가 강력한 교란 변수.** F8대로 effort 하향만으로 preamble·도구 호출·주석이 동시에 줄어든다. effort가 조건 간 다르면 프롬프트 효과와 구별 불가 | 전 가설 | effort를 명시적으로 고정하고 기록. Phase 3로 effort 스윕(low/medium/high)을 별도 실험으로 분리 |
| L4 | **P2(서브에이전트) 경로에서는 중간 나레이션을 볼 수 없다** — 부모는 최종 보고만 받는다. H1을 P2로는 검증할 수 없다 | H1 | P1(`claude -p --output-format stream-json`)을 우선 시도. 불가하면 H1은 "측정 필요"로 남긴다 |
| L5 | **저장소 자체 CLAUDE.md 오염** (§4.7-1). 이 실험 설계에서 가장 실수하기 쉬운 지점 | 조건 A 무력화 | 시행 디렉터리를 저장소 밖에 두고 로드된 메모리 파일 목록을 매 시행 기록 |
| L6 | **문자↔토큰 비율의 조건 간 안정성 가정.** 억제 지시가 출력의 *형태*(산문 → 불릿·약어·화살표 체인)를 바꾸면 문자당 토큰 비율이 달라진다. 공교롭게도 S9는 그런 압축을 명시적으로 금지하고 있어(`not to compress the writing into fragments, abbreviations, arrow chains`) 조건 B가 오히려 문자 대비 토큰이 비쌀 수 있다 | 전 가설 | 언어를 English로 고정. 출력 형태 변화(불릿 비율·평균 문장 길이)를 부가 지표로 함께 기록 |
| L7 | **n=3은 소표본.** 에이전트 실행은 시행 간 분산이 크다(도구 호출 수가 2배 차이나는 일이 흔함) | 통계적 결론 | 효과가 작으면(±20% 미만) "판정 보류"로 처리하고 n을 6으로 늘린다. 중앙값 위주로 보고 |
| L8 | **과제가 작다.** 3개 과제 모두 단일 파일·수십 줄 규모다. F6(서브에이전트)·F4(마크다운 산출물)의 효과는 이 규모에서 바닥 효과에 걸려 나타나지 않을 수 있다 | H4·H6 특히 | H6은 서브에이전트가 애초에 거의 안 쓰이면 "해당 없음"으로 처리. 필요하면 다중 파일 조사 과제를 4번째 과제로 추가 |
| L9 | **완수도 체크리스트는 이진 판정이라 "품질 저하"를 놓친다.** 테스트는 통과하지만 코드가 나빠지는 경우(과도한 특수 케이스, 가독성 하락)를 잡지 못한다 | 전 가설 | verify 스크립트의 신규 입력 검증으로 하드코딩은 차단됨. 나머지 품질은 심사 에이전트가 diff를 보고 3점 척도로 별도 기록 |
| L10 | **F9의 함정**: 억제 지시가 과하면 모델이 문자 그대로 지켜 *일을 덜 한다*. Anthropic이 코드 리뷰 리콜 저하 사례로 직접 경고한 실패 모드 | 전 가설 | 완수도 체크리스트가 이 실험의 핵심 방어선. 절감률만 보고 채택 판정하지 않는다 |
| L11 | **CLAUDE.md는 강제가 아니다** (F13). 준수 자체가 확률적이므로 "지시가 있었는데 무시된" 시행이 섞인다 | 효과 크기 희석 | 시행별로 지시 준수 여부(예: 나레이션 블록 수)를 별도 기록해 준수/미준수 시행을 나눠 본다 |
| L12 | 이 문서의 인용 스니펫은 Opus 5 기준이다. Sonnet 5·Haiku 4.5에서는 기본 verbosity 성향이 달라 효과 방향이 바뀔 수 있다 | 일반화 | 결론에 "Opus 5 한정" 단서 명시. 모델 확장은 별도 실험 |
