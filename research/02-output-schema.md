# 축 2 — 출력 스키마

대상: Claude 계열 전용. 출력(completion) 토큰 절감 목적.
작성 시점: 2026-08-13. 실험 미실행 — 설계까지만.

## 1. 리서치 요약

### 1.1 출력 토큰을 사전에 셀 수단이 없다 (이 축의 최대 제약)

- `POST /v1/messages/count_tokens` 는 **입력 토큰만** 반환한다. "The response contains the total number of input tokens." — https://platform.claude.com/docs/en/build-with-claude/token-counting
- 반환값은 추정치다. "The token count is an **estimate**. In some cases, the actual number of input tokens used when creating a message might differ by a small amount." (같은 출처)
- 따라서 **출력 포맷 A와 B의 토큰 비용 차이는 실제로 생성시켜 `usage.output_tokens` 를 읽는 방법 외에는 확정할 수 없다.** 오프라인 계산 불가.
- Claude 토크나이저는 공개되지 않았다. 구조 문자(`{`, `"`, `:`, `\t`)가 몇 토큰인지 문서화된 수치 없음 → **측정 필요**.
- tiktoken 등 타 벤더 토크나이저 수치는 Claude에 적용 불가. 공식 안내는 "count tokens ... use `messages.count_tokens`, never `tiktoken`" (claude-api 스킬 번들 `shared/token-counting.md`).
- 토크나이저는 모델 세대에 따라 다르다. Claude Opus 4.7 이후 모델은 이전 세대 대비 **같은 텍스트가 약 30% 더 많은 토큰**으로 계산된다. "The same input text produces approximately 30 percent more tokens than on earlier models." — https://platform.claude.com/docs/en/build-with-claude/token-counting
  → **함의: 포맷별 절감률은 모델 세대 간 이식 불가.** 조건 비교 시 모델을 고정해야 한다.

### 1.2 출력 직렬화 형식이 출력 토큰을 바꾼다 — Claude 계열 유일한 공식 수치

- token-efficient tool use (베타, `token-efficient-tools-2025-02-19`): 도구 호출의 **직렬화 방식만** 바꾸고 의미는 유지한 기능. Anthropic 공식 블로그: "reducing output token consumption by **up to 70%**", "early users have seen a reduction of **14%**" (평균). — https://claude.com/blog/token-saving-updates
- **적용 모델: Claude 3.7 Sonnet 한정.** 위 수치는 모두 3.7 Sonnet 기준이며 다른 모델에 그대로 적용할 수 없다.
- 현재 상태: 이 베타는 Claude 4+ 모델에 **내장**되었고 헤더는 무효(no effect)다 (claude-api 스킬 번들 `shared/model-migration.md`, "Beta Headers to Remove on 4.6" 표). 전용 문서 페이지는 현재 마이그레이션 가이드로 리다이렉트된다.
  → **함의: 14%/70%는 오늘의 Claude 4/5 계열에서 "추가로 얻을 수 있는 절감"이 아니라 이미 베이스라인에 포함된 값일 가능성이 높다.** 이 수치를 근거로 "포맷을 바꾸면 14% 아낀다"고 주장하면 안 된다. 다만 **"의미 동일 + 직렬화만 변경 → 출력 토큰이 두 자릿수 % 단위로 움직인다"** 는 명제 자체는 Anthropic 1차 출처로 뒷받침된다. 이것이 이 축의 존재 근거다.

### 1.3 응답 포맷 선택은 성능에도 영향을 준다

- "even your tool response structure—for example XML, JSON, or Markdown—can have an impact on evaluation performance." 보편 정답은 없고 평가 기반 선택을 권장. — https://www.anthropic.com/engineering/writing-tools-for-agents
- 같은 글의 concise/detailed 사례: detailed 응답 206 토큰 → concise 응답 72 토큰, "we use ~⅓ of the tokens with `\"concise\"` tool responses."
  → **주의: 이 수치는 "도구가 에이전트에게 돌려주는 응답"(= 다음 턴의 입력 토큰)이고, 모델이 생성하는 출력 토큰이 아니다.** 축 2에 직접 인용 불가. 다만 "정보량이 아니라 표현 밀도를 줄여 1/3까지 줄어들 수 있다"는 크기감의 참고치.
- Claude Code는 도구 응답을 기본 25,000 토큰으로 제한한다 (같은 출처).
- 원칙: "find the *smallest possible* set of high-signal tokens that maximize the likelihood of some desired outcome." — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### 1.4 Structured Outputs (`output_config.format`)

- 메커니즘: "Structured outputs guarantee schema-compliant responses through **constrained decoding**", "Structured outputs use **constrained sampling with compiled grammar artifacts**." — https://platform.claude.com/docs/en/build-with-claude/structured-outputs
  → 스키마 밖 토큰(전문/후문/코드펜스/설명)은 문법상 생성 불가. **출력에서 "포장지"가 구조적으로 제거된다.**
- 입력 쪽 비용은 늘어난다: "When using structured outputs, Claude **automatically receives an additional system prompt** explaining the expected output format. This means: **Your input token count is slightly higher**." (같은 출처)
- 출력 토큰이 늘어나는지 줄어드는지에 대한 **공식 수치는 없다 → 측정 필요.** 특히 `required` 필드가 많은 스키마는 모델이 생략했을 필드를 강제 생성시켜 출력을 늘릴 수 있다(가설 H4b).
- 첫 호출 지연: "the first time you use a specific schema, there is **additional latency while the grammar compiles**"; "**Compiled grammars are cached for 24 hours** from last use". `name`/`description`만 바꾸면 캐시 무효화 안 됨. `output_config.format` 변경은 프롬프트 캐시를 무효화한다. (같은 출처)
- 스키마 제약 (측정 설계에 영향): 재귀 스키마 불가, 숫자 제약(`minimum`/`maximum`) 불가, 문자열 길이 제약(`minLength`/`maxLength`) **불가** → **스키마로 출력 길이를 직접 제한할 수 없다.** 배열 `minItems`는 0과 1만 지원. 모든 object에 `additionalProperties: false` 필요. (같은 출처)
- 지원 모델: Fable 5 / Mythos 5 / Opus 5 / Opus 4.8 / 4.7 / 4.6 / Sonnet 5 / Sonnet 4.6 / Sonnet 4.5 / Opus 4.5 / Haiku 4.5. (같은 출처)

### 1.5 키 이름·enum 이름 자체가 모델 동작에 실린다

- "JSON schemas define what's structurally valid, but can't express usage patterns: when to include optional parameters, which combinations make sense, or what conventions your API expects." — https://www.anthropic.com/engineering/advanced-tool-use
  → 키 이름을 `description` → `d` 로 줄이면 **구조 검증은 통과하지만 의미 단서가 사라진다.** 정확도 트레이드오프가 예상되는 이론적 근거. 크기는 **측정 필요**.
- 반대로 도구 설명 품질이 성능을 좌우한다는 관찰: "One of the most effective methods for improving tools is prompt-engineering your tool descriptions and specs." — https://www.anthropic.com/engineering/writing-tools-for-agents

### 1.6 모델 세대별 기본 장황도 차이 (교란 요인)

- Claude Opus 5는 이전 세대보다 기본 응답과 산출 문서가 더 길다: "Default visible responses and written deliverables run longer on Claude Opus 5 than on Claude Opus 4.8", 대응책은 "Prompt explicitly for conciseness or a target length". — https://platform.claude.com/docs/en/about-claude/models/migration-guide
- 같은 출처: **`effort` 를 낮춰도 사용자 대면 출력 길이가 안정적으로 줄지는 않는다.** → 축 2 실험에서 `effort` 는 길이 통제 수단이 아니며, 조건 간 고정만 하면 된다.

### 1.7 확인된 수치가 없는 항목 (모두 "측정 필요")

| 항목 | 상태 |
|---|---|
| JSON vs TSV vs 줄바꿈 구분 포맷의 출력 토큰 차이 | 측정 필요 (Claude 공식 수치 없음) |
| 키 축약(`description`→`d`)의 절감률 / 정확도 손실 | 측정 필요 |
| enum 문자열 → 정수 코드화의 절감률 | 측정 필요 |
| Structured Outputs 사용 시 출력 길이 증감 | 측정 필요 |
| 마크다운 장식(헤더/표/굵게)의 출력 토큰 비용 | 측정 필요 |
| diff/patch 반환 vs 전체 재출력의 절감률 | 측정 필요 |
| positional(값만) 반환의 절감률 / 정확도 손실 | 측정 필요 |
| 구조 문자 1개(`{`, `"`, `\t`)의 토큰 수 | 측정 필요 (토크나이저 비공개) |

---

## 2. 가설

`H*` 는 모두 동일 입력·동일 모델·동일 언어 구성 하에서의 조건 간 비교.

- **H1 (JSON→TSV):** 조건 A(전체 키 JSON) 대비 조건 D(헤더 있는 TSV)에서 출력 길이(문자 수)가 감소하며, 셀 단위 필드 정확도는 유지된다(≥99%).
- **H2 (키 축약):** 조건 A 대비 조건 B(1글자 축약 키 JSON)에서 출력 길이가 감소하지만, 셀 정확도는 A보다 낮아진다 — 특히 `product`/`category` 처럼 의미가 가까운 필드에서 열 혼동이 발생한다.
- **H3 (enum 코드화):** 조건 A 대비 조건 C(전체 키 JSON + enum 정수 코드)에서 출력 길이가 감소하며, 정확도 손실은 H2(키 축약)보다 작다. 근거: 코드표가 프롬프트에 명시되면 필드 정체성은 키가 계속 지탱하기 때문.
- **H4a (Structured Outputs — 포장지 제거):** 산문 지시로 JSON을 요구한 조건(A)의 응답에는 데이터 블록 바깥 문자(전문·코드펜스·후문)가 존재하며, 이 "비페이로드 문자"가 전체 출력 문자의 비무시 비율을 차지한다. `output_config.format` 은 constrained decoding으로 이를 구조적으로 0으로 만든다.
- **H4b (Structured Outputs — 필수 필드 역효과):** 모든 필드가 `required` 인 스키마에서는, 모델이 자발적으로 생략했을 필드(값 불명확·해당 없음)까지 채워지므로 페이로드 문자는 오히려 증가한다. 즉 SO의 순효과 = (포장지 제거 이득) − (필수 필드 강제 비용)이며 부호는 스키마 설계에 의존한다.
- **H5 (positional):** 조건 D(헤더 TSV) 대비 조건 E(헤더 없음 + 고정 열 순서 + enum 코드)에서 출력 길이가 추가로 감소하지만, 열 정렬 오류(값 밀림)로 인해 **레코드 단위 정확도**가 가장 크게 하락한다.
- **H6 (마크다운 장식):** 조건 F(마크다운 표)는 동일 정보를 담은 조건 D(TSV)보다 출력 길이가 길다. 증가분은 구분자·정렬 공백·구분선에서 나오며 레코드 수에 비례한다.
- **H7 (변경분만 반환):** 30줄 중 6줄만 바뀌는 수정 과제에서, 전체 재출력(조건 P-A) 대비 변경분만 반환(P-B: unified diff / P-C: `줄번호: 새 내용`)이 출력 길이를 감소시키되, 적용 후 최종 파일 일치율은 P-A가 가장 높다(변경분 포맷은 줄번호 오기·컨텍스트 누락 위험이 있다).
- **H8 (레코드 수 종속성):** 포맷별 절감 폭은 레코드 수 N에 대해 대략 선형으로 커진다. 레코드당 구조 오버헤드가 거의 상수이므로, N=1에서는 조건 간 차이가 무의미하고 N이 커질수록 유의해진다. (검증: 동일 프로토콜을 N=3 서브셋과 N=12 전체로 각각 실행해 절감 폭을 비교)

---

## 3. 실험 프로토콜

### 3.0 환경 제약 및 대체 측정

- `ANTHROPIC_API_KEY` 없음, `ant` CLI 없음 → `usage.output_tokens` / `count_tokens` 사용 불가.
- 대체 측정: **naive 서브에이전트**에게 조건별 프롬프트를 주고 산출물의 문자 수 / 줄 수를 측정.
- 모든 수치에 `(proxy)` 표기. **절대 토큰 수로 보고하지 않는다. 조건 간 상대 비율로만 보고한다.**
- 피험 에이전트는 자신이 토큰 절감 실험의 대상임을 알아서는 안 된다. 프롬프트 어디에도 "토큰", "간결", "짧게", "절약" 을 넣지 않는다.

### 3.1 실험 1 — 추출 과제 × 출력 포맷 6조건

#### 3.1.1 입력 데이터

`experiments/data/02-tickets-input.md` (고객지원 티켓 12건, 한국어 산문).
레코드 12건 × 필드 8개 = **셀 96개**.
정답 키: `experiments/data/02-tickets-groundtruth.tsv` (판정자 전용 — 피험 에이전트에게 절대 노출 금지).

> ⚠️ 입력은 **프롬프트에 본문을 붙여넣어** 제공한다. 파일 경로를 주면 피험 에이전트가 저장소를 탐색해 정답 키·프로토콜을 읽고 naive 조건이 깨진다.

#### 3.1.2 조건 목록

| 조건 | 출력 포맷 | 키 | enum 값 |
|---|---|---|---|
| A (기준선) | JSON 배열 of 객체 | 전체 이름 | 영문 문자열 |
| B | JSON 배열 of 객체 | 1글자 축약 | 영문 문자열 |
| C | JSON 배열 of 객체 | 전체 이름 | 정수 코드 |
| D | TSV (헤더 1행 + 12행) | 헤더에 전체 이름 | 영문 문자열 |
| E | TSV (헤더 없음, 고정 열 순서) | 없음(positional) | 정수 코드 |
| F | 마크다운 표 | 헤더에 전체 이름 | 영문 문자열 |

조건 A↔B: 키 축약만 다름 (H2).
조건 A↔C: enum 코드화만 다름 (H3).
조건 A↔D: 직렬화 형식만 다름 (H1).
조건 D↔E: 헤더 제거 + enum 코드화 (H5).
조건 D↔F: 장식만 다름 (H6).

#### 3.1.3 시행 횟수

조건당 **n = 3**. 총 18회. 매 시행은 **새 서브에이전트 1개**(대화 이월 없음). 실행 순서는 조건이 섞이도록 무작위화한다(A,D,F,B,E,C,… 식으로 라운드 로빈).

#### 3.1.4 과제 지시문 전문

아래 `<<공통부>>` 는 모든 조건에서 **문자 단위로 동일**하게 유지한다. 조건별로 `<<출력 형식>>` 블록만 교체한다.

---

**<<공통부>> (모든 조건 공통, 그대로 복사)**

```
아래는 고객지원 티켓 기록 12건입니다. 각 티켓에서 다음 8개 항목을 추출하세요.

항목:
1. ticket_id — 티켓 번호 (예: TK-1001)
2. date — 접수일 (YYYY-MM-DD)
3. tier — 고객 플랜
4. product — 제품 영역
5. category — 분류
6. priority — 등급
7. resolved — 해결 여부
8. response_hours — 첫 응대까지 걸린 시간(시간 단위 숫자)

값 대응표:
- tier: 무료=free, 프로=pro, 엔터프라이즈=enterprise
- product: 결제=billing, 모바일 앱=mobile_app, 웹 콘솔=web_console, API=api
- category: 버그=bug, 장애=outage, 문의=question, 기능요청=feature_request, 환불=refund
- priority: 낮음=low, 보통=medium, 높음=high, 긴급=urgent
- resolved: 해결 완료=true, 미해결=false

[여기에 experiments/data/02-tickets-input.md 의 "티켓 기록" 절 본문 12건을 그대로 붙여넣는다]

<<출력 형식>>
```

---

**조건 A — `<<출력 형식>>` 블록**

```
출력 형식: 결과를 JSON 배열로 출력하세요. 배열의 각 원소는 다음 8개 키를 가진 객체입니다.
ticket_id, date, tier, product, category, priority, resolved, response_hours
tier / product / category / priority 는 위 대응표의 영문 값을, resolved 는 true 또는 false 를, response_hours 는 숫자를 사용합니다.
```

**조건 B — `<<출력 형식>>` 블록**

```
출력 형식: 결과를 JSON 배열로 출력하세요. 배열의 각 원소는 다음 8개 키를 가진 객체입니다.
i, d, t, p, c, r, v, h
키 대응: i=ticket_id, d=date, t=tier, p=product, c=category, r=priority, v=resolved, h=response_hours
t / p / c / r 은 위 대응표의 영문 값을, v 는 true 또는 false 를, h 는 숫자를 사용합니다.
```

**조건 C — `<<출력 형식>>` 블록**

```
출력 형식: 결과를 JSON 배열로 출력하세요. 배열의 각 원소는 다음 8개 키를 가진 객체입니다.
ticket_id, date, tier, product, category, priority, resolved, response_hours
tier / product / category / priority / resolved 는 아래 코드표의 정수를 사용합니다. response_hours 는 숫자입니다.
코드표:
- tier: free=0, pro=1, enterprise=2
- product: billing=0, mobile_app=1, web_console=2, api=3
- category: bug=0, outage=1, question=2, feature_request=3, refund=4
- priority: low=0, medium=1, high=2, urgent=3
- resolved: false=0, true=1
```

**조건 D — `<<출력 형식>>` 블록**

```
출력 형식: 결과를 TSV(탭 구분)로 출력하세요. 첫 줄은 헤더입니다.
헤더: ticket_id	date	tier	product	category	priority	resolved	response_hours
그 아래 티켓 1건당 1줄, 총 12줄을 같은 열 순서로 출력합니다.
tier / product / category / priority 는 위 대응표의 영문 값을, resolved 는 true 또는 false 를, response_hours 는 숫자를 사용합니다.
```

**조건 E — `<<출력 형식>>` 블록**

```
출력 형식: 결과를 탭 구분 텍스트로 출력하세요. 헤더 줄은 넣지 않습니다.
티켓 1건당 1줄, 총 12줄. 각 줄은 다음 8개 값을 이 순서대로 탭으로 구분해 나열합니다.
ticket_id, date, tier, product, category, priority, resolved, response_hours
tier / product / category / priority / resolved 는 아래 코드표의 정수를 사용합니다. response_hours 는 숫자입니다.
코드표:
- tier: free=0, pro=1, enterprise=2
- product: billing=0, mobile_app=1, web_console=2, api=3
- category: bug=0, outage=1, question=2, feature_request=3, refund=4
- priority: low=0, medium=1, high=2, urgent=3
- resolved: false=0, true=1
```

**조건 F — `<<출력 형식>>` 블록**

```
출력 형식: 결과를 마크다운 표로 출력하세요.
열: ticket_id | date | tier | product | category | priority | resolved | response_hours
티켓 1건당 1행, 총 12행입니다.
tier / product / category / priority 는 위 대응표의 영문 값을, resolved 는 true 또는 false 를, response_hours 는 숫자를 사용합니다.
```

#### 3.1.5 측정 방법

산출물 = 서브에이전트 최종 응답 텍스트 전체(도구 호출 로그 제외). 원문 그대로 `experiments/raw/02-e1-<조건>-<시행번호>.txt` 에 저장한 뒤 측정한다.

측정 항목 4개:

| 지표 | 정의 |
|---|---|
| `total_chars` | 응답 전체 문자 수 (앞뒤 공백 trim 후). **주 지표.** 실제 과금되는 출력에 가장 가까움 |
| `payload_chars` | 데이터 블록만의 문자 수. 코드펜스(```)와 그 바깥 텍스트 제외 |
| `wrapper_chars` | `total_chars - payload_chars`. 전문·코드펜스·후문 = "포장지" (H4a 검증용) |
| `lines` | 데이터 블록의 줄 수 (기대값: A/B/C 는 자유, D=13, E=12, F=14) |

측정 스크립트 (PowerShell, 저장소 루트에서 실행):

```powershell
Get-ChildItem experiments/raw/02-e1-*.txt | ForEach-Object {
  $t = (Get-Content $_.FullName -Raw -Encoding utf8).Trim()
  [pscustomobject]@{
    file        = $_.Name
    total_chars = $t.Length
    lines       = ($t -split "`n").Count
  }
} | Export-Csv experiments/raw/02-e1-metrics.csv -NoTypeInformation -Encoding utf8
```

`payload_chars` 는 데이터 블록 경계를 사람이 표시한 뒤 동일 방식으로 센다.

보고 형식: 조건별 n=3의 **중앙값**과 최소–최대. 기준선 A 대비 비율로만 보고 (`D = A의 0.7배 (proxy, n=3)` 형식). 절대 토큰 환산 금지.

#### 3.1.6 정확도 판정 기준

정답 키: `experiments/data/02-tickets-groundtruth.tsv`.

판정 절차:
1. 산출물을 파싱해 12×8 표로 정규화한다. 파싱 자체가 실패하면(JSON 문법 오류, 열 수 불일치) 그 시행은 **파싱 실패**로 기록하고 정확도 0으로 처리한다.
2. 조건 C/E 는 정수 코드를 코드표 역방향으로 문자열 값으로 복원한 뒤 비교한다. 조건 B 는 축약 키를 원래 키로 복원한 뒤 비교한다.
3. 정규화: 앞뒤 공백 제거. `resolved` 는 `true/false` 로 통일. `response_hours` 는 수치 비교(`0.5 == .5 == 0.50`). 나머지는 대소문자 구분 없이 정확 일치.
4. 지표 3개:
   - **셀 정확도** = 일치 셀 수 / 96
   - **레코드 정확도** = 8개 필드가 모두 맞은 레코드 수 / 12
   - **누락/추가** = 출력된 레코드 수가 12가 아니면 그 자체로 결함으로 별도 기록

판정 규칙 (**길이 절감만으로 채택하지 않는다**):

| 조건별 셀 정확도 중앙값 | 판정 |
|---|---|
| = 100% | 길이 비교 대상. 절감 시 가설 지지 |
| 99% 이상 ~ 100% 미만 (오류 1셀) | 길이 비교 대상. 단 "오류 1건 발생" 을 반드시 병기 |
| 95% 이상 ~ 99% 미만 | **조건부 기각.** 길이가 줄어도 채택하지 않고 "정확도 저하 확인" 으로 보고 |
| 95% 미만 또는 3회 중 1회 이상 파싱 실패 | **기각.** 길이 수치를 보고하지 않는다 |

추가 규칙: 어느 조건이든 **레코드 정확도가 기준선 A보다 2건 이상 낮으면** 길이 절감 여부와 무관하게 기각한다.

#### 3.1.7 H8 (레코드 수 종속성) 확인

동일 프로토콜을 TK-1001~TK-1003 만 사용한 N=3 버전으로 조건 A/D/E 에 대해 n=3씩 추가 실행한다(9회). 비교 지표는 `A 대비 절감 비율(N=3)` vs `A 대비 절감 비율(N=12)`.

### 3.2 실험 2 — 변경분 반환 vs 전체 재출력 (H7)

#### 3.2.1 입력 데이터

`experiments/data/02-patch-input.md` (30줄 설정 파일 + 6곳 변경 요청).
기대 결과: `experiments/data/02-patch-expected.yaml` (판정자 전용).
입력은 역시 **프롬프트에 붙여넣어** 제공한다.

#### 3.2.2 조건

| 조건 | 출력 형식 |
|---|---|
| P-A (기준선) | 수정된 파일 전체(30줄) 재출력 |
| P-B | unified diff 형식으로 변경분만 |
| P-C | `줄번호: 새 내용` 형식으로 변경된 줄만 |

#### 3.2.3 과제 지시문 전문

**<<공통부>>**

```
아래는 배포 설정 파일 deploy.yaml 과 변경 요청입니다. 요청대로 수정하세요.

[여기에 experiments/data/02-patch-input.md 의 "원본 파일" 코드블록과 "변경 요청" 절을 그대로 붙여넣는다]

<<출력 형식>>
```

**P-A**
```
출력 형식: 수정이 반영된 deploy.yaml 파일 전체를 출력하세요. 줄 번호는 붙이지 않습니다.
```

**P-B**
```
출력 형식: 원본 대비 변경분을 unified diff 형식(--- / +++ / @@ / - / +)으로만 출력하세요. 변경되지 않은 부분은 컨텍스트 3줄 규칙을 따릅니다.
```

**P-C**
```
출력 형식: 변경된 줄만 출력하세요. 각 줄은 `줄번호: 새 내용` 형식이며, 줄번호는 원본 파일의 번호입니다. 변경되지 않은 줄은 출력하지 않습니다.
```

#### 3.2.4 시행 횟수 / 측정

조건당 n=3, 총 9회. 각각 새 서브에이전트.
측정: 실험 1과 동일한 `total_chars` / `payload_chars` / `wrapper_chars` / `lines`.

#### 3.2.5 정확도 판정 기준

1. 산출물을 원본 `deploy.yaml` 에 적용해 최종 파일을 재구성한다.
   - P-A: 출력 자체가 최종 파일
   - P-B: `git apply` 로 적용. 적용 실패 시 그 시행은 **적용 실패**
   - P-C: 지정 줄번호를 새 내용으로 치환
2. 재구성 결과를 `02-patch-expected.yaml` 과 비교.
   - **줄 단위 완전 일치율** = 일치 줄 수 / 30
   - **요청 반영률** = 6개 변경 요청 중 정확히 반영된 수 / 6
   - **부수 손상** = 변경 요청 대상이 아닌 24줄 중 달라진 줄 수 (0이어야 함)
3. 판정 규칙: 줄 단위 완전 일치율 100% 이고 부수 손상 0 인 시행만 길이 비교에 포함. 3회 중 1회 이상 적용 실패 또는 부수 손상이 있으면 그 조건은 **기각**하고 "짧지만 신뢰 불가" 로 기록한다.

### 3.3 언어 고정 규칙 (전 조건 공통)

- 지시문 언어: **한국어 고정**.
- 입력 데이터 언어: **한국어 고정**.
- 출력 필드명·enum 값 어휘: **영문 소문자 snake_case 고정**(조건 C/E 의 정수 코드화는 예외이며, 이것이 의도된 조작 변수).
- 조건 간 다른 것은 오직 `<<출력 형식>>` 블록 하나뿐. 공통부는 문자 단위로 동일해야 한다 — 실행 전 diff 로 검증한다.
- 어느 조건에도 "간결하게", "짧게", "불필요한 설명 없이" 를 넣지 않는다(축 1 변수와의 교락 방지).

### 3.4 실행 시 고정할 것

| 항목 | 값 |
|---|---|
| 모델 | 전 시행 동일 모델 1종 (사용 모델명을 원시 결과에 기록) |
| `effort` / thinking 설정 | 서브에이전트 기본값 유지, 조건 간 동일 |
| 서브에이전트 유형 | 전 시행 동일 유형 |
| 도구 접근 | 파일 읽기 불필요(프롬프트 인라인) — 저장소 탐색 금지 |
| 실행 시점 | 가능하면 같은 세션 내 연속 실행 |

---

## 4. 한계 / 교란 요인

1. **문자 수는 토큰의 대리 지표일 뿐이다.** Claude 토크나이저가 비공개이므로 `{`, `"`, `\t`, 숫자, 한글, 영문 단어의 토큰 비용비를 알 수 없다. 문자 수가 30% 줄었다고 토큰이 30% 줄었다는 보장이 없다. API 키 확보 시 `usage.output_tokens` 로 전량 재측정해야 한다.

2. **enum 코드화 조건은 언어 구성이 매칭되지 않는다(최대 약점).** 조건 C/E 는 영문 단어(`enterprise`, `feature_request`)를 ASCII 숫자로 대체한다. 이는 문자 수뿐 아니라 **문자↔토큰 비율 자체를 바꾼다.** 영문 단어는 1~3토큰인 반면 한 자리 숫자도 1토큰일 수 있어, 문자 수 기준 절감이 토큰 기준으로는 크게 축소되거나 사라질 수 있다. → **H3의 문자 수 결과는 토큰 재측정 전까지 "상한선"으로만 해석한다.**

3. **구조 문자의 토큰 효율 미상.** JSON의 `", "`, `": "` 같은 반복 시퀀스는 BPE에서 단일 토큰으로 병합될 가능성이 있다. 그렇다면 JSON의 문자 수 페널티는 토큰 페널티보다 과대평가된다. 반대로 TSV의 탭 문자가 비효율적으로 토큰화될 수도 있다. 모두 미확인.

4. **`wrapper_chars`(포장지)가 주 효과를 삼킬 수 있다.** 코드펜스·전문·후문은 조건과 무관한 모델 습관이며 시행 간 분산이 크다. 이 때문에 `total_chars` 만 보면 포맷 효과가 노이즈에 묻힐 수 있다. 그래서 `payload_chars` 를 병기하도록 설계했다. 반대로 `payload_chars` 만 보면 실제 과금 현실을 놓친다 — 두 지표를 항상 함께 보고한다.

5. **n=3은 통계적으로 약하다.** 생성은 비결정적이며 3회 중앙값으로는 신뢰구간을 말할 수 없다. 조건 간 차이가 15% 미만이면 "차이 확인 안 됨" 으로 처리하고, 유망한 조건만 n을 늘려 재실행한다.

6. **서브에이전트 하네스는 raw API 호출이 아니다.** 피험 에이전트에는 자체 시스템 프롬프트와 도구 목록이 실려 있고, 이것이 출력 스타일(마크다운 선호, 요약 문단 추가 등)에 영향을 준다. 여기서 얻은 비율이 애플리케이션의 raw `messages.create` 호출에 그대로 이식된다는 보장이 없다.

7. **Structured Outputs(H4a/H4b)는 이 환경에서 직접 검증 불가.** `output_config.format` 은 API 파라미터이므로 서브에이전트로는 재현할 수 없다. 실험 1의 조건 A는 "산문으로 JSON을 요구한 경우"의 대리 조건일 뿐이며, constrained decoding의 실제 효과(포장지 구조적 제거)는 API 키 확보 후 별도 측정해야 한다. 그때 비교해야 할 3조건: (i) 산문 JSON 지시, (ii) SO + 최소 필수 필드 스키마, (iii) SO + 전 필드 required 스키마.

8. **과제 일반화 한계.** 이 프로토콜은 폐쇄형 값(ID·날짜·enum·숫자)만 추출하는 과제다. 자유 텍스트 필드(요약문, 설명)가 있는 과제에서는 포맷 효과가 값 자체의 길이에 희석되어 훨씬 작아질 것으로 예상된다. 즉 여기서 얻는 절감률은 **낙관적 상한**이다.

9. **키 축약(H2)의 정확도 손실은 필드 수·의미 근접성에 의존한다.** 필드 8개 중 의미가 가까운 쌍(`product`/`category`, `tier`/`priority`)이 있어 혼동 가능성이 설계상 존재한다. 필드가 3개뿐이거나 서로 완전히 이질적인 스키마에서는 손실이 나타나지 않을 수 있다. 결과를 "키 축약은 위험하다" 로 일반화하지 말 것.

10. **모델 세대 이식 불가.** Claude Opus 4.7 이후 토크나이저가 바뀌어 같은 텍스트가 약 30% 더 많은 토큰이 된다(출처: token-counting 문서). 포맷별 절감 **비율**도 세대 간 달라질 수 있으므로, 결과에는 반드시 사용 모델명을 병기한다.

11. **`effort` 는 길이 통제 수단이 아니다.** 마이그레이션 가이드에 따르면 `effort` 를 낮춰도 사용자 대면 출력 길이가 안정적으로 줄지 않는다. 조건 간 고정만 하고, 길이 차이를 `effort` 로 설명하지 않는다.

12. **판정자 오염 위험.** 정답 키와 프로토콜이 저장소에 있으므로, 피험 에이전트에 파일 읽기 권한이 있고 경로를 알면 naive 조건이 깨진다. 반드시 프롬프트 인라인 방식으로만 입력을 제공한다.

---

## 출처 목록

- Structured outputs — https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Token counting — https://platform.claude.com/docs/en/build-with-claude/token-counting
- Model migration guide — https://platform.claude.com/docs/en/about-claude/models/migration-guide
- Token-saving updates (Anthropic 블로그) — https://claude.com/blog/token-saving-updates
- Writing effective tools for AI agents — https://www.anthropic.com/engineering/writing-tools-for-agents
- Effective context engineering for AI agents — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Introducing advanced tool use — https://www.anthropic.com/engineering/advanced-tool-use
- claude-api 스킬 번들 (`shared/token-counting.md`, `shared/model-migration.md`) — 로컬, URL 없음
