# 라운드 1 실험 계획

작성일 2026-08-13. 리서치 5축(`research/01`~`05`)의 가설을 **지금 이 환경에서 실행 가능한 것 하나**로 통합한 실행 명세.

**실행 조건 (변경 불가)**
- `ANTHROPIC_API_KEY` 없음, `ant` CLI 없음 → `usage.output_tokens` / `count_tokens` 사용 불가. `[API 필요]` 가설은 전량 §7로 이월.
- 실행 수단은 Claude Code **Agent 도구 서브에이전트 1종**뿐. `claude -p --output-format stream-json` 경로(축 5 P1)는 라운드 1에서 쓰지 않는다 → 도구 호출 사이 나레이션은 원리적으로 측정 불가.
- **naive 피험 에이전트 총 24개.** 아래 배분이 상한을 정확히 채운다.
- 모든 수치는 문자 수 **(proxy)**. 절대 토큰 환산 금지, 조건 간 상대 비율로만 보고.

---

## 0. 선정 결과

### 0.1 선정한 가설 3개

| ID | 가설 (라운드 1 형태) | 통합한 원 가설 | 선정 이유 |
|---|---|---|---|
| **H1** | 동일 페이로드(12레코드 × 8필드)를 **전체 키 JSON**으로 낼 때보다 **헤더 TSV**로 낼 때 산출물 문자 수가 감소하며, 셀 정확도는 유지된다 | 축2 H1 | 조작 변수가 "직렬화 형식"이라 이 저장소 CLAUDE.md의 억제 규칙과 **직교**한다(§1). 정답 키(`02-tickets-groundtruth.tsv`)가 이미 있어 "짧아졌지만 틀림"을 96셀 단위로 기계 판정할 수 있다. 페이로드가 형식에 의해 거의 결정되므로 분산이 작아 n=4로도 결론이 선다 |
| **H2** | 30줄 파일의 6줄 수정에서 **전체 재출력** 대비 **unified diff**가 산출물 문자 수를 줄이지만, 그 이득은 **기계 적용 성공률**에 의해 상쇄될 수 있다 | 축2 H7 · 축4 H3 · 축5(diff만 출력) — **3개 축이 같은 지점을 가리킨다** | 세 축이 독립적으로 같은 기법을 지목한 유일한 항목. 축4는 `(변경비율+오버헤드비율) < 패치 성공률`이라는 부등식까지 제시했고, 라운드 1에서 좌변(문자 수)과 우변(적용 성공률)을 **동시에** 실측할 수 있다. 기대 결과 파일(`02-patch-expected.yaml`)로 부수 손상까지 줄 단위 판정 가능 |
| **H3** | 공식 억제 스니펫 묶음(S1·S3·S5·S6·S7·S9)을 주고 검증 지시를 제거하면, 코딩 과제에서 **사용자 대면 요약 길이**와 **코드/주석 분량**이 감소하며 과제 완수도(`verify_a.py`)는 유지된다 | 축5 H1·H2·H3·H4·H5(묶음) · 축1 H1·H4·H6 · 축3 P-B | 이 저장소의 헤드라인 질문("프롬프트로 출력을 줄일 수 있는가")이고 4개 축이 수렴한다. 실제 코딩 에이전트 워크로드라 외적 타당도가 가장 높다. **다만 오염이 가장 심한 가설이며, 그래서 판정 규칙을 비대칭으로 사전 등록했다(§6.4)** |

### 0.2 탈락시킨 가설과 사유

| 원 가설 | 사유 |
|---|---|
| 축1 H1(긍정형 vs 부정형), H4(서론 억제 단독), H7(프롬프트 마크다운 전이) | 예산. 요인 분해는 묶음 효과(H3)가 움직인 것을 확인한 뒤에 해야 낭비가 없다. 라운드 1b |
| 축1 H2(간결성 지시 위치) | 서브에이전트는 system/user 분리를 제어할 수 없어 "단일 프롬프트 앞/뒤"로만 대리 검증 가능 → 공식 권고(긴 system prompt 전제)에 대한 검정력이 낮다. API 확보 후가 정석 |
| 축1 H3(수치 상한 "600자 이내") | 처치가 곧 길이 지정이라 절감 방향은 자명하고, 진짜 쟁점(품질 하락)은 5점 체크리스트 n=4로 검출되지 않는다 |
| 축1 H5(예시 길이 앵커링) | 근거 없는 탐색적 가설. 재료(긴 예시 확장본) 제작 비용까지 필요 |
| 축1 H6 / 축5 H2(검증 지시 제거 **단독**) | **가장 아까운 탈락.** 공식 문서가 유일하게 "토큰 감소 + 품질 손실 없음"을 명시한 항목이다. 다만 H3의 조건 A에 검증 지시를 넣어 묶음의 일부로 포함시켰으므로 완전 배제는 아니다. 단독 효과 분해는 라운드 1b |
| 축2 H2(키 축약) | 정확도 손실 검출이 목적인데 n=4로는 저빈도 혼동을 못 잡는다 |
| 축2 H3·H5(enum 정수 코드화, positional) | **문자↔토큰 비율이 깨진다.** 영문 단어를 한 자리 숫자로 바꾸는 조작이라 문자 수 절감이 토큰 절감을 대변하지 못한다(축2 한계 §4-2 자인). proxy로 재면 안 되는 가설 → §7 |
| 축2 H6(마크다운 표 vs TSV) | 예산. 같은 과제를 공유해 추가 비용이 조건 1개(n=4)뿐이라 라운드 1b 최우선 후보 |
| 축2 H8(레코드 수 종속성) | 조건 3개 × n=3 추가가 필요. 절감 폭의 스케일링은 절감 존재 확인 이후 문제 |
| 축4 H1·H2(라우팅 손익분기) | `[계산으로 검증]`이지만 입력값 `O_h/O_o`(모델 티어별 출력 길이비)를 얻으려면 티어 3수준 × 과제 × n = 최소 9~90 시행. 라운드 1 예산으로 불가 |
| 축4 H4·H5(멀티에이전트 팬아웃) | 실험 자체가 에이전트를 배수로 소비한다(조건 B 1회 = 오케스트레이터 1 + 서브 3). 24개 예산에서 다른 가설을 전부 밀어낸다 |
| 축5 H1(도구 호출 사이 나레이션) | Agent 도구 경로에서 부모는 서브에이전트의 최종 보고만 본다. `interstitial_chars`는 stream-json 트랜스크립트가 있어야 측정 가능 → 실행 수단 제약으로 불가(축5 L4) |
| 축5 H6(서브에이전트 스폰 억제), H7(하위가산성) | H6은 소규모 과제에서 바닥 효과 + 중첩 스폰 관측 불가. H7은 요인 분해가 선행되어야 함 |
| 축3 전량, 축2 H4a·H4b, 축4 H6·H7 | `[API 필요]` → §7 |

### 0.3 예산 배분표

| 가설 | 조건 | n | 소계 |
|---|---|---|---|
| H1 직렬화 | A(전체 키 JSON) | 4 | 4 |
| H1 직렬화 | B(헤더 TSV) | 4 | 4 |
| H2 변경분 | A(전체 재출력) | 4 | 4 |
| H2 변경분 | B(unified diff) | 4 | 4 |
| H3 억제 묶음 | A(구모델 관행 잔재) | 4 | 4 |
| H3 억제 묶음 | B(억제 묶음 + 검증 지시 제거) | 4 | 4 |

**산술 확인: 3 가설 × 2 조건 × n 4 = 6 × 4 = 24 ≤ 24.** 상한을 정확히 채우며 초과하지 않는다.

- 여기 세는 24개는 **naive 피험 에이전트만**이다. 산출물을 채점하는 판정 에이전트는 naive가 아니고 측정 대상도 아니므로 예산에 포함하지 않는다(1개면 충분, §5).
- **재실행 예비분은 없다.** 무효 시행(형식 위반·언어 위반·중단)이 생기면 그 조건은 유효 n이 줄어든 상태로 §6.1의 "유효 시행 3건 미만 → 판정 불가"에 걸린다. 예산을 더 받으면 무효분만 보충 실행한다.
- n=3이 아니라 n=4로 잡은 이유: 조건당 4건이면 무효 1건이 나와도 §6.1의 최소 유효 시행 3건을 지킬 수 있다. n을 더 늘리려면 가설을 2개로 줄여야 하는데, 위 3개는 각각 다른 축군을 대표하므로 하나를 빼면 라운드 1이 답할 수 있는 질문의 폭이 과도하게 좁아진다.

---

## 1. 오염 문제 처리 (이 계획서에서 가장 중요한 절)

### 1.1 사실관계

- Claude Code 서브에이전트는 **프로젝트 `CLAUDE.md`를 컨텍스트로 물고 시작한다.** 저장소 밖 디렉터리를 작업 대상으로 지정해도, 오케스트레이터가 이 저장소에서 에이전트를 띄우는 한 로드된다. **따라서 축 5가 제안한 "저장소 밖에서 실행" 만으로는 해결되지 않는다.**
- 확인한 사실(2026-08-13):
  - 사용자 스코프 `C:/Users/FORYOUCOM/.claude/CLAUDE.md` **없음**, `C:/Users/FORYOUCOM/CLAUDE.md` **없음**. → 오염원은 프로젝트 `CLAUDE.md` **하나**로 특정된다.
  - 그 파일의 SHA-256 = `cfaf94a02be69edd9b3fecddd6c110239564865ed2c375ee6e3ade61d9294165`. **라운드 1 시행 중 이 파일을 수정하지 않는다.** 수정하면 그 이후 시행은 앞선 시행과 비교 불가다. 종료 후 해시를 재확인해 기록한다.

### 1.2 오염원별 작용 분석

| CLAUDE.md 규칙 | H1(직렬화) | H2(변경분) | H3(억제 묶음) |
|---|---|---|---|
| "한국어로, 결론부터. 서론·요약 반복·자평 금지" | 영향 미미(산출물이 데이터 파일) | 영향 미미 | **직접 오염.** 조건 A의 `summary.md`가 이미 부분 억제됨 |
| "표나 목록으로 표현되면 산문 대신 그것을 쓴다" | 형식을 프롬프트가 명시 지정하므로 무력 | 무관 | 약한 오염(요약 형태) |
| "코드 수정 시 변경된 부분만 보여준다. 파일 전체 재출력 금지" | 무관 | **정면 충돌.** 조건 A가 곧 전체 재출력이다 | 무관 |
| "근거 없는 절감률 추정 금지" 등 연구 운영 규칙 | 무관 | 무관 | 무관 |

### 1.3 채택 방침 — 4단 조합

**(1) 처치가 오염 규칙과 직교하는 가설을 우선 선정한다 (선택지 c의 강화판).**
H1·H2의 조작 변수는 "출력 직렬화 형식"이고, `CLAUDE.md`는 형식을 지정하지 않는다. 오염은 조건 A/B에 **공통 상수**로 걸리므로 차분은 유효하다. 이것은 사후 변명이 아니라 **가설 선정 기준으로 먼저 썼다** — 24개 예산의 2/3를 오염 내성이 있는 가설에 배정한 이유다.

**(2) 측정 대상을 대화 응답이 아니라 지정 경로의 파일로 뺀다 (선택지 b의 변형).**
`CLAUDE.md`의 억제 규칙은 문면상 "**응답**"을 대상으로 한다("응답 규칙" 절). 산출물을 `<외부 경로>/out.json` 같은 파일로 요구하면 그 규칙의 적용 범위가 약해진다. **제거가 아니라 약화**이며, 크기는 알 수 없다. 부수 효과로 측정 대상이 명확해지고(요구사항), 피험자의 최종 보고 텍스트는 측정에서 완전히 배제된다.

**(3) 프롬프트 첫 줄에서 범위를 재지정한다 (선택지 b).**
전 조건 동일 문장: "작업 디렉터리는 `<경로>` 입니다. 이 디렉터리는 다른 팀이 관리하는 독립 프로젝트이고, 아래 지시가 이 작업의 유일한 명세입니다. 다른 위치의 파일이나 규약은 참조하지 마세요." 조건 간 글자 단위로 동일하므로 차분에 영향을 주지 않는다. **효과는 보장되지 않는다** — `CLAUDE.md`는 시스템 프롬프트가 아니라 그 뒤의 user 메시지로 전달되고 준수 자체가 확률적이므로(축5 F13), 이 문장이 그것을 이긴다는 근거는 없다. 실패해도 조건 A/B에 동일하게 실패한다는 것이 이 조치의 유일한 안전장치다.

**(4) H3는 절감률을 하한(lower bound)으로만 해석한다 (선택지 a).**
조건 A가 이미 부분 억제된 상태이므로 관측되는 감소는 무오염 환경에서의 감소보다 **작다**. 방향은 신뢰하고 크기는 하한으로만 읽는다.

**(5) H2의 정면 충돌은 하한 논증으로 덮지 않는다 — 눈에 보이는 실패로 만든다.**
조건 A(전체 재출력)는 `CLAUDE.md`와 직접 충돌한다. 완화책은 (2)의 파일 산출물 요구(규칙은 "보여준다"에 걸린다)와 형식 명시 지시다. 그럼에도 피험자가 파일을 축약하면 — 30줄 미만, 변경된 줄만 기록, "생략" 표기 등 — 그 시행은 §5.2의 **형식 준수 게이트에서 무효 처리**된다. 오염이 길이 수치를 조용히 깎는 대신 **무효 시행 수로 드러나게** 하는 설계이며, 무효가 2건 이상이면 H2는 "판정 불가"로 보고하고 길이 수치를 내지 않는다.

### 1.4 그 결과 **할 수 없게 되는 주장** (사전 명시)

1. **"간결성 지시는 출력을 N% 줄인다"는 절대 크기 주장 불가.** H3에서 얻는 것은 "이미 억제 규칙이 걸린 baseline 대비 추가 절감의 하한"뿐이다. 축1 §1.11의 번들 문서 ~20% 주장과 우리 수치를 같은 축에 올려 비교할 수 없다.
2. **일반 API 사용자 환경으로의 외삽 불가.** 우리 조건 A는 일반 사용자의 기본 상태가 아니다. techniques/ 문서에 절감률을 적을 때 "조건 A = 억제 규칙이 이미 걸린 Claude Code 세션"을 반드시 병기한다.
3. **H3의 null 결과로 기각을 주장할 수 없다.** "효과 없음"과 "이미 억제되어 바닥 효과"가 구별되지 않기 때문이다. → §6.4에 비대칭 판정 규칙으로 사전 등록한다(채택은 가능, 기각은 불가).
4. **포장지(wrapper) 문자량에 대한 주장 불가.** "서론 금지" 규칙이 이미 wrapper를 눌렀고, 우리는 산출물 파일만 재므로 전문·후문·코드펜스를 측정하지 않는다. 축2 H4a(포장지 구조적 제거)는 라운드 1 대상이 아니다.
5. **thinking 토큰에 대한 주장 불가.** 가시 산출물만 잰다. 어떤 처치가 파일은 줄이면서 사고를 늘리면 proxy는 절감을 과대평가한다. 이 축의 구조적 한계이며 API 확보 전에는 해소 불가.
6. **모델 세대 간 이식 불가.** 결과에 사용 모델 ID를 병기하고, 다른 세대와 문자 수 비율을 직접 비교하지 않는다.

---

## 2. 시행 명세

### 2.0 공통 실행 규칙

| 항목 | 값 |
|---|---|
| 서브에이전트 유형 | `general-purpose` (전 24시행 동일) |
| 모델 | `opus` 로 **명시 고정** (가설 근거가 Opus 5 문서). 예산 사정으로 바꾸려면 24개 전부 같은 값으로 바꾸고 결과에 기록 |
| `run_in_background` | 자유. 단 **라운드(6개) 단위로만 병렬화**한다 — 라운드 내 6개는 서로 다른 조건이므로 시간 드리프트가 조건에 균등하게 걸린다 |
| 후속 메시지 | 금지. 각 피험자는 **1회 프롬프트로 끝낸다**(SendMessage 사용 금지). 추가 지시는 처치 오염이다 |
| 피험자의 최종 보고 텍스트 | **측정 대상 아님.** 측정은 지정 경로의 파일만 |
| 시행 루트 | `C:/Users/FORYOUCOM/AppData/Local/Temp/st-r1/` (저장소 밖. 상위에 `CLAUDE.md` 없음을 확인함) |
| 디렉터리명 | `t01`~`t24`. **조건을 유추할 수 없는 이름**을 쓴다(축5 §4.7-4) |

시행 순서는 6조건 라운드로빈이며, 라운드 2·4에서는 조건 순서를 뒤집어 A가 항상 먼저 오지 않게 한다.

### 2.1 시행표

| 시행ID | 가설 | 조건 | 과제 | 산출물 저장 경로 |
|---|---|---|---|---|
| H1-A-1 | H1 | A 전체 키 JSON | 티켓 12건 추출 | `…/st-r1/t01/out.json` |
| H1-B-1 | H1 | B 헤더 TSV | 티켓 12건 추출 | `…/st-r1/t02/out.tsv` |
| H2-A-1 | H2 | A 전체 재출력 | deploy.yaml 6곳 수정 | `…/st-r1/t03/out.yaml` |
| H2-B-1 | H2 | B unified diff | deploy.yaml 6곳 수정 | `…/st-r1/t04/out.diff` |
| H3-A-1 | H3 | A 구모델 관행 | stats.py 버그 수정 | `…/st-r1/t05/` (수정된 `stats.py` + `summary.md`) |
| H3-B-1 | H3 | B 억제 묶음 | stats.py 버그 수정 | `…/st-r1/t06/` (수정된 `stats.py` + `summary.md`) |
| H1-B-2 | H1 | B | 동일 | `…/st-r1/t07/out.tsv` |
| H1-A-2 | H1 | A | 동일 | `…/st-r1/t08/out.json` |
| H2-B-2 | H2 | B | 동일 | `…/st-r1/t09/out.diff` |
| H2-A-2 | H2 | A | 동일 | `…/st-r1/t10/out.yaml` |
| H3-B-2 | H3 | B | 동일 | `…/st-r1/t11/` |
| H3-A-2 | H3 | A | 동일 | `…/st-r1/t12/` |
| H1-A-3 | H1 | A | 동일 | `…/st-r1/t13/out.json` |
| H1-B-3 | H1 | B | 동일 | `…/st-r1/t14/out.tsv` |
| H2-A-3 | H2 | A | 동일 | `…/st-r1/t15/out.yaml` |
| H2-B-3 | H2 | B | 동일 | `…/st-r1/t16/out.diff` |
| H3-A-3 | H3 | A | 동일 | `…/st-r1/t17/` |
| H3-B-3 | H3 | B | 동일 | `…/st-r1/t18/` |
| H1-B-4 | H1 | B | 동일 | `…/st-r1/t19/out.tsv` |
| H1-A-4 | H1 | A | 동일 | `…/st-r1/t20/out.json` |
| H2-B-4 | H2 | B | 동일 | `…/st-r1/t21/out.diff` |
| H2-A-4 | H2 | A | 동일 | `…/st-r1/t22/out.yaml` |
| H3-B-4 | H3 | B | 동일 | `…/st-r1/t23/` |
| H3-A-4 | H3 | A | 동일 | `…/st-r1/t24/` |

조건별 시행 디렉터리 묶음:

```
H1-A : t01 t08 t13 t20      H1-B : t02 t07 t14 t19
H2-A : t03 t10 t15 t22      H2-B : t04 t09 t16 t21
H3-A : t05 t12 t17 t24      H3-B : t06 t11 t18 t23
```

### 2.2 시행 전 준비 (오케스트레이터가 수행, 피험자 관여 없음)

```bash
R=/c/Users/FORYOUCOM/AppData/Local/Temp/st-r1
mkdir -p $R
for i in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24; do mkdir -p $R/t$i; done

# H3 시행 디렉터리에만 픽스처를 복사한다. verify 스크립트는 절대 복사하지 않는다.
cd /c/Users/FORYOUCOM/Desktop/save_tokens
for i in 05 06 11 12 17 18 23 24; do cp experiments/fixtures/task-a-bugfix/stats.py experiments/fixtures/task-a-bugfix/test_stats.py $R/t$i/; done

# H1/H2 시행 디렉터리는 비워 둔다. 입력은 전부 프롬프트 인라인이다.
ls $R/t01 $R/t05
```

---

## 3. 피험 에이전트 프롬프트 (verbatim)

**사용법:** 조건별 프롬프트 전문은 아래 3쌍 6개다. 치환하는 것은 **`<<DIR>>` 한 곳뿐**이며, 값은 §2.1의 저장 경로 디렉터리다(예: H1-A-1 → `C:/Users/FORYOUCOM/AppData/Local/Temp/st-r1/t01`). 그 외에는 한 글자도 바꾸지 않는다.

**검증 의무:** 실행 전, 각 쌍의 조건 A/B 프롬프트에서 조작 변수 블록을 제거한 나머지가 **글자 단위로 동일**한지 diff로 확인한다(§4.0).

---

### 3.1 H1 조건 A — 전체 키 JSON

```text
작업 디렉터리는 <<DIR>> 입니다. 이 디렉터리는 다른 팀이 관리하는 독립 프로젝트이고, 아래 지시가 이 작업의 유일한 명세입니다. 다른 위치의 파일이나 규약은 참조하지 마세요.

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

티켓 기록:

**TK-1001** / 2026-07-02 접수. 엔터프라이즈 계약 고객사에서 API 게이트웨이 전체가 응답하지 않는다는 신고. 장애로 분류, 긴급 등급. 접수 후 30분 만에 원인 파악 및 복구되어 해결 완료.

**TK-1002** / 2026-07-02 접수. 무료 플랜 사용자가 모바일 앱에서 프로필 사진 업로드 시 앱이 종료된다고 제보. 버그로 분류, 낮음 등급. 26시간 후 첫 답변이 나갔고 현재 미해결 상태.

**TK-1003** / 2026-07-03 접수. 프로 플랜 사용자가 결제 화면에서 이중 청구가 발생했다며 환불을 요청. 환불로 분류, 높음 등급. 3.5시간 만에 응대하여 해결 완료.

**TK-1004** / 2026-07-04 접수. 프로 플랜 사용자가 웹 콘솔의 팀원 초대 절차를 몰라 방법을 물어봄. 문의로 분류, 낮음 등급. 12시간 후 답변했고 해결 완료.

**TK-1005** / 2026-07-05 접수. 엔터프라이즈 고객사가 웹 콘솔 대시보드의 사용량 그래프가 실제 값과 다르게 표시된다고 신고. 버그로 분류, 높음 등급. 1.5시간 만에 첫 응대했으나 아직 미해결.

**TK-1006** / 2026-07-06 접수. 무료 플랜 사용자가 API 요청 한도가 어떻게 계산되는지 물어봄. 문의로 분류, 보통 등급. 48시간 후 답변했고 해결 완료.

**TK-1007** / 2026-07-07 접수. 엔터프라이즈 고객사에서 결제 인보이스에 세금 항목이 누락되어 발행됨. 버그로 분류, 긴급 등급. 0.25시간 만에 응대하여 해결 완료.

**TK-1008** / 2026-07-08 접수. 프로 플랜 사용자가 모바일 앱에 다크 모드를 추가해 달라고 요청. 기능요청으로 분류, 낮음 등급. 30시간 후 회신했으나 미해결로 남아 있음.

**TK-1009** / 2026-07-09 접수. 무료 플랜 사용자가 결제 취소 후 금액이 돌아오지 않았다며 환불을 요구. 환불로 분류, 보통 등급. 20시간 후 응대했고 미해결.

**TK-1010** / 2026-07-10 접수. 엔터프라이즈 고객사에서 모바일 앱 로그인이 전 지역에서 실패하는 광범위한 장애 발생. 장애로 분류, 긴급 등급. 0.75시간 만에 복구되어 해결 완료.

**TK-1011** / 2026-07-11 접수. 프로 플랜 사용자가 API 응답의 페이지네이션 커서가 중복 레코드를 반환한다고 제보. 버그로 분류, 보통 등급. 6시간 만에 응대하여 해결 완료.

**TK-1012** / 2026-07-12 접수. 무료 플랜 사용자가 웹 콘솔에서 결제 내역을 내려받는 위치를 물어봄. 문의로 분류, 낮음 등급. 15시간 후 답변했고 해결 완료.

출력 형식: 결과를 JSON 배열로 <<DIR>>/out.json 에 저장하세요. 배열의 각 원소는 다음 8개 키를 가진 객체입니다.
ticket_id, date, tier, product, category, priority, resolved, response_hours
tier / product / category / priority 는 위 대응표의 영문 값을, resolved 는 true 또는 false 를, response_hours 는 숫자를 사용합니다.

파일에는 결과 데이터만 넣고 설명이나 주석은 넣지 않습니다. 이 대화에서 설명이 필요하면 한국어로 씁니다.
```

### 3.2 H1 조건 B — 헤더 TSV

> 조건 A와 다른 곳은 `출력 형식:` 문단 하나뿐이다. 그 위(범위 재지정 문장 ~ TK-1012)와 아래(마지막 문단)는 조건 A와 글자 단위로 동일하다.

```text
작업 디렉터리는 <<DIR>> 입니다. 이 디렉터리는 다른 팀이 관리하는 독립 프로젝트이고, 아래 지시가 이 작업의 유일한 명세입니다. 다른 위치의 파일이나 규약은 참조하지 마세요.

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

티켓 기록:

**TK-1001** / 2026-07-02 접수. 엔터프라이즈 계약 고객사에서 API 게이트웨이 전체가 응답하지 않는다는 신고. 장애로 분류, 긴급 등급. 접수 후 30분 만에 원인 파악 및 복구되어 해결 완료.

**TK-1002** / 2026-07-02 접수. 무료 플랜 사용자가 모바일 앱에서 프로필 사진 업로드 시 앱이 종료된다고 제보. 버그로 분류, 낮음 등급. 26시간 후 첫 답변이 나갔고 현재 미해결 상태.

**TK-1003** / 2026-07-03 접수. 프로 플랜 사용자가 결제 화면에서 이중 청구가 발생했다며 환불을 요청. 환불로 분류, 높음 등급. 3.5시간 만에 응대하여 해결 완료.

**TK-1004** / 2026-07-04 접수. 프로 플랜 사용자가 웹 콘솔의 팀원 초대 절차를 몰라 방법을 물어봄. 문의로 분류, 낮음 등급. 12시간 후 답변했고 해결 완료.

**TK-1005** / 2026-07-05 접수. 엔터프라이즈 고객사가 웹 콘솔 대시보드의 사용량 그래프가 실제 값과 다르게 표시된다고 신고. 버그로 분류, 높음 등급. 1.5시간 만에 첫 응대했으나 아직 미해결.

**TK-1006** / 2026-07-06 접수. 무료 플랜 사용자가 API 요청 한도가 어떻게 계산되는지 물어봄. 문의로 분류, 보통 등급. 48시간 후 답변했고 해결 완료.

**TK-1007** / 2026-07-07 접수. 엔터프라이즈 고객사에서 결제 인보이스에 세금 항목이 누락되어 발행됨. 버그로 분류, 긴급 등급. 0.25시간 만에 응대하여 해결 완료.

**TK-1008** / 2026-07-08 접수. 프로 플랜 사용자가 모바일 앱에 다크 모드를 추가해 달라고 요청. 기능요청으로 분류, 낮음 등급. 30시간 후 회신했으나 미해결로 남아 있음.

**TK-1009** / 2026-07-09 접수. 무료 플랜 사용자가 결제 취소 후 금액이 돌아오지 않았다며 환불을 요구. 환불로 분류, 보통 등급. 20시간 후 응대했고 미해결.

**TK-1010** / 2026-07-10 접수. 엔터프라이즈 고객사에서 모바일 앱 로그인이 전 지역에서 실패하는 광범위한 장애 발생. 장애로 분류, 긴급 등급. 0.75시간 만에 복구되어 해결 완료.

**TK-1011** / 2026-07-11 접수. 프로 플랜 사용자가 API 응답의 페이지네이션 커서가 중복 레코드를 반환한다고 제보. 버그로 분류, 보통 등급. 6시간 만에 응대하여 해결 완료.

**TK-1012** / 2026-07-12 접수. 무료 플랜 사용자가 웹 콘솔에서 결제 내역을 내려받는 위치를 물어봄. 문의로 분류, 낮음 등급. 15시간 후 답변했고 해결 완료.

출력 형식: 결과를 TSV로 <<DIR>>/out.tsv 에 저장하세요. 첫 줄은 헤더이고, 그 아래 티켓 1건당 1줄씩 총 12줄입니다. 헤더와 데이터 행 모두 열 구분자는 탭 문자 1개이며 열 순서는 다음과 같습니다.
ticket_id, date, tier, product, category, priority, resolved, response_hours
tier / product / category / priority 는 위 대응표의 영문 값을, resolved 는 true 또는 false 를, response_hours 는 숫자를 사용합니다.

파일에는 결과 데이터만 넣고 설명이나 주석은 넣지 않습니다. 이 대화에서 설명이 필요하면 한국어로 씁니다.
```

---

### 3.3 H2 조건 A — 전체 재출력

> 프롬프트 안에 코드펜스(```)가 들어 있으므로 이 블록의 바깥 울타리는 백틱 5개다. **바깥 울타리 안쪽 전체**가 프롬프트 전문이다.

`````text
작업 디렉터리는 <<DIR>> 입니다. 이 디렉터리는 다른 팀이 관리하는 독립 프로젝트이고, 아래 지시가 이 작업의 유일한 명세입니다. 다른 위치의 파일이나 규약은 참조하지 마세요.

아래는 배포 설정 파일 deploy.yaml 의 현재 내용과 변경 요청입니다. 요청대로 수정하세요.

현재 deploy.yaml (30줄):

```
service: payments-api
replicas: 3
image: registry.example.com/payments-api:1.4.2
port: 8080
env: staging
resources:
  cpu: 500m
  memory: 512Mi
  gpu: 0
healthcheck:
  path: /healthz
  interval_seconds: 10
  timeout_seconds: 2
  failure_threshold: 3
logging:
  level: debug
  format: text
  retention_days: 7
autoscale:
  enabled: false
  min_replicas: 1
  max_replicas: 5
  target_cpu_percent: 80
database:
  host: db-staging.internal
  port: 5432
  pool_size: 10
  ssl: false
timeouts:
  request_seconds: 30
```

변경 요청 6곳:
1. replicas 를 3에서 6으로 변경
2. env 를 staging 에서 production 으로 변경
3. logging.level 을 debug 에서 info 로 변경
4. logging.format 을 text 에서 json 으로 변경
5. autoscale.enabled 를 false 에서 true 로 변경
6. database.ssl 을 false 에서 true 로 변경

나머지 24줄은 변경하지 않습니다.

출력 형식: 수정이 반영된 deploy.yaml 파일 전체를 <<DIR>>/out.yaml 에 저장하세요. 줄 번호는 붙이지 않습니다.

파일에는 위 형식의 내용만 넣고 설명이나 주석은 넣지 않습니다. 이 대화에서 설명이 필요하면 한국어로 씁니다.
`````

### 3.4 H2 조건 B — unified diff

> 조건 A와 다른 곳은 `출력 형식:` 문단 하나뿐이다. 바깥 울타리는 백틱 5개.

`````text
작업 디렉터리는 <<DIR>> 입니다. 이 디렉터리는 다른 팀이 관리하는 독립 프로젝트이고, 아래 지시가 이 작업의 유일한 명세입니다. 다른 위치의 파일이나 규약은 참조하지 마세요.

아래는 배포 설정 파일 deploy.yaml 의 현재 내용과 변경 요청입니다. 요청대로 수정하세요.

현재 deploy.yaml (30줄):

```
service: payments-api
replicas: 3
image: registry.example.com/payments-api:1.4.2
port: 8080
env: staging
resources:
  cpu: 500m
  memory: 512Mi
  gpu: 0
healthcheck:
  path: /healthz
  interval_seconds: 10
  timeout_seconds: 2
  failure_threshold: 3
logging:
  level: debug
  format: text
  retention_days: 7
autoscale:
  enabled: false
  min_replicas: 1
  max_replicas: 5
  target_cpu_percent: 80
database:
  host: db-staging.internal
  port: 5432
  pool_size: 10
  ssl: false
timeouts:
  request_seconds: 30
```

변경 요청 6곳:
1. replicas 를 3에서 6으로 변경
2. env 를 staging 에서 production 으로 변경
3. logging.level 을 debug 에서 info 로 변경
4. logging.format 을 text 에서 json 으로 변경
5. autoscale.enabled 를 false 에서 true 로 변경
6. database.ssl 을 false 에서 true 로 변경

나머지 24줄은 변경하지 않습니다.

출력 형식: 원본 대비 변경분만 unified diff 형식으로 <<DIR>>/out.diff 에 저장하세요. 파일 헤더는 --- a/deploy.yaml 과 +++ b/deploy.yaml 로 쓰고, 각 hunk 는 @@ 로 시작하며 컨텍스트 3줄 규칙을 따릅니다.

파일에는 위 형식의 내용만 넣고 설명이나 주석은 넣지 않습니다. 이 대화에서 설명이 필요하면 한국어로 씁니다.
`````

---

### 3.5 H3 조건 A — 구모델 관행 잔재 (baseline)

> H3만 영어로 고정한다. 조작 변수인 억제 스니펫이 Anthropic 공식 영어 원문이고, 번역하면 워딩 민감성 때문에 처치 자체가 달라진다(축1 한계 §4-6). **조건 A/B 모두 영어**이므로 언어 고정 요건은 충족된다.

```text
The working directory is <<DIR>>. It is a standalone code exercise owned by another team; the instructions below are the only spec for this task, and conventions from other locations do not apply.

# Project instructions

Python 3.13 and Node 22 are available.

- Respond in English.
- Run the project's test suite to check your work.
- Include a final verification step for any non-trivial task, and double-check your answer before responding.

# Task

The tests in test_stats.py are failing. Fix the bugs in stats.py so the whole suite passes. Do not modify test_stats.py.

When you are done, write a handover note at <<DIR>>/summary.md for the teammate who picks this work up next.
```

### 3.6 H3 조건 B — 억제 묶음 + 검증 지시 제거 (처치)

> 조건 A와 다른 곳은 두 군데다. (1) `- Include a final verification step…` 줄이 **삭제**되었다. (2) `# Project instructions` 목록 뒤에 억제 블록이 **추가**되었다. `# Task` 절 이하는 조건 A와 글자 단위로 동일하다. 억제 블록의 문장은 `research/05-coding-agent.md` §2 의 S1·S3·S5·S6·S7·S9 원문 그대로이며 한 글자도 고치지 않았다.

```text
The working directory is <<DIR>>. It is a standalone code exercise owned by another team; the instructions below are the only spec for this task, and conventions from other locations do not apply.

# Project instructions

Python 3.13 and Node 22 are available.

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

# Task

The tests in test_stats.py are failing. Fix the bugs in stats.py so the whole suite passes. Do not modify test_stats.py.

When you are done, write a handover note at <<DIR>>/summary.md for the teammate who picks this work up next.
```

### 3.7 프롬프트 설계 근거 (검토용)

- **실험임을 암시하는 표현 없음.** "토큰", "간결하게 써라"(H1/H2), "측정", "조건", "실험" 어휘를 넣지 않았다. H3 조건 B의 간결성 문구는 **처치 그 자체**이므로 허용된다.
- **"파일에는 결과 데이터만 넣는다"(H1/H2)는 조건 A/B에 동일하게 들어간다.** 측정 대상을 페이로드로 한정해 형식 효과를 분리하기 위한 상수이며, 조작 변수가 아니다. 부작용으로 축2 H4a(포장지)는 이 설계로 측정되지 않는다(§1.4-4).
- **H3의 "handover note"에 길이 형용사를 넣지 않았다.** "short/brief"를 넣으면 두 조건 모두 바닥 효과에 걸려 처치 효과가 사라진다.
- **H3에서 "다른 파일을 만들지 마라"를 넣지 않았다.** 미요청 산출물 개수는 축5 H4의 **종속변수**이므로 금지하면 측정할 것이 사라진다.
- **입력은 전량 프롬프트 인라인.** 저장소 경로를 주면 피험자가 정답 키·계획서를 읽어 naive 조건이 깨진다(축2 §4-12).

---

## 4. 측정 절차

### 4.0 실행 전 — 프롬프트 동일성 검증

조건 A/B 프롬프트를 파일로 저장한 뒤, 조작 변수 블록을 뺀 나머지가 동일한지 확인한다. 다르면 실험을 시작하지 않는다.

```bash
cd /c/Users/FORYOUCOM/Desktop/save_tokens
P=/c/Users/FORYOUCOM/AppData/Local/Temp/st-r1/prompts   # §3 본문을 그대로 저장
mkdir -p $P
# H1/H2: '출력 형식:' 줄 앞까지(공통 도입부)가 동일해야 한다 -> 출력 없음이 정상
for h in h1 h2; do
  echo "== $h 도입부"
  diff <(sed -n '1,/^출력 형식:/p' $P/$h-a.txt | head -n -1) \
       <(sed -n '1,/^출력 형식:/p' $P/$h-b.txt | head -n -1)
  echo "== $h 말미"   # 마지막 문단(언어 고정 문장)도 동일해야 한다
  diff <(tail -n 2 $P/$h-a.txt) <(tail -n 2 $P/$h-b.txt)
done
# H3: '# Task' 이후 전문이 동일해야 한다
diff <(sed -n '/^# Task/,$p' $P/h3-a.txt) <(sed -n '/^# Task/,$p' $P/h3-b.txt)
```

### 4.1 길이 측정 — `tools/measure.py` 단독

**길이는 `tools/measure.py` 로만 잰다.** 손으로 세지 않고, 다른 스크립트로 재지 않는다.

```bash
cd /c/Users/FORYOUCOM/Desktop/save_tokens
R=/c/Users/FORYOUCOM/AppData/Local/Temp/st-r1
mkdir -p experiments/raw

# 조건별 4건 일괄 측정 (JSON)
python tools/measure.py --json $R/t01/out.json $R/t08/out.json $R/t13/out.json $R/t20/out.json > experiments/raw/r1-H1-A.json
python tools/measure.py --json $R/t02/out.tsv  $R/t07/out.tsv  $R/t14/out.tsv  $R/t19/out.tsv  > experiments/raw/r1-H1-B.json
python tools/measure.py --json $R/t03/out.yaml $R/t10/out.yaml $R/t15/out.yaml $R/t22/out.yaml > experiments/raw/r1-H2-A.json
python tools/measure.py --json $R/t04/out.diff $R/t09/out.diff $R/t16/out.diff $R/t21/out.diff > experiments/raw/r1-H2-B.json
python tools/measure.py --json $R/t05/summary.md $R/t12/summary.md $R/t17/summary.md $R/t24/summary.md > experiments/raw/r1-H3-A.json
python tools/measure.py --json $R/t06/summary.md $R/t11/summary.md $R/t18/summary.md $R/t23/summary.md > experiments/raw/r1-H3-B.json

# 쌍별 A/B 비교 + 언어 구성 점검. exit code 2 (언어 구성 불일치) 가 뜨면 그 쌍은 무효.
python tools/measure.py --ab $R/t01/out.json $R/t02/out.tsv;  echo "exit=$?"
python tools/measure.py --ab $R/t08/out.json $R/t07/out.tsv;  echo "exit=$?"
python tools/measure.py --ab $R/t13/out.json $R/t14/out.tsv;  echo "exit=$?"
python tools/measure.py --ab $R/t20/out.json $R/t19/out.tsv;  echo "exit=$?"
python tools/measure.py --ab $R/t03/out.yaml $R/t04/out.diff; echo "exit=$?"
python tools/measure.py --ab $R/t10/out.yaml $R/t09/out.diff; echo "exit=$?"
python tools/measure.py --ab $R/t15/out.yaml $R/t16/out.diff; echo "exit=$?"
python tools/measure.py --ab $R/t22/out.yaml $R/t21/out.diff; echo "exit=$?"
python tools/measure.py --ab $R/t05/summary.md $R/t06/summary.md; echo "exit=$?"
python tools/measure.py --ab $R/t12/summary.md $R/t11/summary.md; echo "exit=$?"
python tools/measure.py --ab $R/t17/summary.md $R/t18/summary.md; echo "exit=$?"
python tools/measure.py --ab $R/t24/summary.md $R/t23/summary.md; echo "exit=$?"
```

조건별 중앙값 집계(§4.1의 JSON을 읽어 집계만 한다 — 계측은 이미 `measure.py` 가 했다):

```bash
for f in experiments/raw/r1-H*.json; do
  python -c "import json,statistics,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(sys.argv[1], {k:statistics.median([v[k] for v in d.values()]) for k in ('chars','chars_nows','words','lines')})" "$f"
done
```

### 4.2 H3 전용 — 코드 산출물 구조 지표

```bash
for i in 05 12 17 24 06 11 18 23; do
  echo "== t$i"
  python experiments/fixtures/code_metrics.py code $R/t$i experiments/fixtures/task-a-bugfix
  ls -1 $R/t$i | grep -v -E '^(stats\.py|test_stats\.py|summary\.md|__pycache__)$' | wc -l   # 미요청 산출물 개수
done
```

### 4.3 계측기 역할 정리 (요구사항 4의 결정)

| 스크립트 | 역할 | 라운드 1 사용 |
|---|---|---|
| `tools/measure.py` | **산출물 길이 계측 전담.** 문자/공백제외문자/어절/줄/코드·산문 분리/한글 비율, `--ab` 상대 비교와 언어 구성 경고(exit 2) | 전 가설의 주 지표 |
| `experiments/fixtures/code_metrics.py` | **코드 산출물 구조 지표 전담.** 줄 수·주석 밀도 | H3의 보조 지표 (`code` 모드만) |

- 축 5가 만든 `experiments/fixtures/measure.py` 는 파일명이 `tools/measure.py` 와 겹쳐 "어느 것으로 길이를 재는가"가 모호했다. **`experiments/fixtures/code_metrics.py` 로 이름을 갈랐다.** 두 스크립트를 합치지 않은 이유: 길이 계측(텍스트 1건 입력)과 코드 구조 지표(디렉터리 2개 비교)는 입력 단위가 달라 한 CLI에 넣으면 오히려 오용을 부른다.
- `code_metrics.py` 의 `transcript` 모드는 `claude -p --output-format stream-json` 트랜스크립트가 있어야 동작한다. 라운드 1의 실행 수단에는 그런 트랜스크립트가 없으므로 **라운드 2 전용**으로 표시했다. 이 모드가 세는 문자 수를 라운드 1 길이 수치로 쓰지 않는다.
- `research/05-coding-agent.md` 의 경로 참조도 새 이름으로 갱신했다.

### 4.4 원시 결과 보존

측정이 끝나면 시행 산출물을 저장소로 복사해 남긴다(CLAUDE.md: 대화에만 남기지 않는다).

```bash
for i in $(seq -w 1 24); do mkdir -p experiments/raw/r1-t$i && cp -r $R/t$i/. experiments/raw/r1-t$i/ 2>/dev/null; done
rm -rf experiments/raw/r1-t*/__pycache__
```

기록할 메타데이터: 사용 모델 ID, 서브에이전트 유형, 실행 일시, `CLAUDE.md` SHA-256(시행 전/후), 로드된 메모리 파일 목록.

---

## 5. 품질 판정 루브릭

판정 에이전트 1개가 수행한다(naive 아님, 예산 외). **파일명을 난수 ID로 바꿔 조건 라벨을 가린 상태에서 채점**하되, 형식이 조건을 드러내는 H1/H2는 블라인드가 불가능하므로 **기계 판정만** 사용한다(주관 채점 없음). H3의 `summary.md` 서술 항목만 사람/에이전트 판단이 들어가며, 이 항목은 블라인드로 채점한다.

### 5.1 H1 — 추출 과제 (정답키 대조)

정답키: `experiments/data/02-tickets-groundtruth.tsv` (피험자에게 노출 금지).

| # | 체크 | 방법 | 실패 시 |
|---|---|---|---|
| Q1 | 파일이 존재하고 비어 있지 않다 | `test -s` | 무효 시행 |
| Q2 | 파싱 성공 (A: `json.loads` 로 배열, B: 모든 줄이 탭 8열) | 스크립트 | 정확도 0, 무효 시행 |
| Q3 | 레코드 12건 (B는 헤더 제외 12줄) | 스크립트 | 게이트 실패 |
| Q4 | 8개 필드 전부 존재 (A: 8키, B: 헤더 8열이 지정 순서) | 스크립트 | 게이트 실패 |
| Q5 | **셀 정확도** = 일치 셀 / 96 ≥ 0.99 | 정규화 후 비교: 앞뒤 공백 제거, `resolved` 는 true/false, `response_hours` 는 수치 비교(`0.5 == .5 == 0.50`), 나머지는 대소문자 무시 완전 일치 | 게이트 실패 |
| Q6 | **레코드 정확도** = 8필드 전부 맞은 레코드 / 12. 조건 A 중앙값 대비 2건 이상 낮지 않다 | 스크립트 | 게이트 실패 |
| Q7 | 파일에 데이터 외 텍스트(설명·코드펜스)가 없다 | 스크립트 | **게이트 실패 아님. 지시 위반으로 별도 기록**하고 길이는 파일 전체로 측정 |

**품질 게이트 통과 = Q1~Q6 전부 통과.** "짧아졌지만 요구사항이 빠짐"은 Q3(레코드 누락)·Q5(셀 오류)·Q6(레코드 붕괴)가 잡는다.

### 5.2 H2 — 패치 과제 (기대 결과 대조)

원본: `experiments/data/02-deploy-original.yaml`, 기대: `experiments/data/02-patch-expected.yaml`.

```bash
J=/c/Users/FORYOUCOM/AppData/Local/Temp/st-r1/judge
mkdir -p $J/tNN && cp experiments/data/02-deploy-original.yaml $J/tNN/deploy.yaml
# 조건 B: 적용 시도 순서 (하나라도 성공하면 적용 성공)
cd $J/tNN && git init -q && git add -A && git -c user.email=j@x -c user.name=j commit -qm base
git apply -p1 $R/tNN/out.diff || git apply -p0 $R/tNN/out.diff || git apply --recount -p1 $R/tNN/out.diff
# 조건 A: out.yaml 자체가 최종 파일
diff -u $J/tNN/deploy.yaml /c/Users/FORYOUCOM/Desktop/save_tokens/experiments/data/02-patch-expected.yaml
```

| # | 체크 | 실패 시 |
|---|---|---|
| Q1 | 파일 존재, 비어 있지 않음 | 무효 시행 |
| Q2 | **형식 준수.** 조건 A: 30줄 전체가 있고 "…(생략)" 류 축약이 없다 / 조건 B: `---`,`+++`,`@@` 헤더를 갖춘 unified diff 다 | **무효 시행**(§1.3-5의 오염 검출 지점). 사유를 "형식 위반(조건 A 축약)"으로 명기 |
| Q3 | **기계 적용 성공** (조건 B). 위 3가지 명령 중 하나로 적용됨 | 게이트 실패 + `q`(적용 실패율) 집계에 반영 |
| Q4 | 최종 파일이 `02-patch-expected.yaml` 과 **30줄 완전 일치** | 게이트 실패 |
| Q5 | **요청 반영률 6/6** (2,5,16,17,20,28행) | 게이트 실패 |
| Q6 | **부수 손상 0** — 나머지 24줄 중 달라진 줄 0개 | 게이트 실패 |

**품질 게이트 통과 = Q1~Q6 전부 통과.** 조건 B가 짧아도 Q3/Q6에서 떨어지면 절감으로 집계하지 않는다 — 이것이 축4 H3의 핵심(`H`와 `q`가 함께 움직인다) 검정 지점이다.

### 5.3 H3 — 코딩 과제 (검증기 사용)

```bash
python experiments/fixtures/verify/verify_a.py $R/tNN     # exit 0 이어야 함
```

| # | 체크 | 방법 | 실패 시 |
|---|---|---|---|
| Q1 | `verify_a.py` exit 0 (제공 테스트 전량 통과) | 검증기 | 게이트 실패 |
| Q2 | `test_stats.py` 무수정 | 검증기 내장 | 게이트 실패 |
| Q3 | **피험자가 본 적 없는 신규 입력 통과** (테스트 피팅 차단) | 검증기 내장 | 게이트 실패 |
| Q4 | `mean`·`median`·`mode` **세 함수 모두** 수정됨 | `diff stats.py experiments/fixtures/task-a-bugfix/stats.py` | 게이트 실패 |
| Q5 | `summary.md` 가 존재하고, **무엇을 고쳤는지**를 읽는 사람이 알 수 있게 적혀 있다(어떤 함수를 왜 고쳤는지 식별 가능) | 블라인드 채점(2점 척도: 충족/미충족) | 게이트 실패 |
| Q6 | 미요청 산출물 개수(신규 파일·문서·헬퍼 모듈) | `ls` 집계 | **게이트 아님. 종속변수로 기록** |
| Q7 | 주석 밀도, 총 줄 수 | `code_metrics.py code` | **게이트 아님. 종속변수로 기록** |

**품질 게이트 통과 = Q1~Q5 전부 통과.** Q5가 "요약이 짧아졌지만 무슨 일이 있었는지 알 수 없음"을 잡는 방어선이다. Q3가 "테스트만 맞추고 실제로는 안 고침"을 잡는다(축5 F9/L10의 실패 모드).

### 5.4 전 가설 공통 무효 처리

- 산출물 파일 미생성, 실행 중단, 지정 경로가 아닌 곳에 저장 → **무효 시행**(길이 집계에서 제외, 사유 기록).
- 지정 언어 위반(H1/H2 한국어 설명 요구·H3 영어) 또는 `measure.py --ab` exit 2 → **그 비교 쌍 무효**.
- 무효 시행은 "실패"가 아니라 **결과의 일부**다. 조건별 무효 건수를 반드시 보고한다.

---

## 6. 판정 기준 (실험 전 고정 — 사후 변경 금지)

> 이 절은 데이터를 보기 **전에** 확정한 것이다. 실행 후 임계값·지표·집계 방식을 바꾸지 않는다. 바꿔야 할 이유가 생기면 그것은 라운드 2의 사전 등록으로 넘기고, 라운드 1은 원래 기준으로 보고한다.

### 6.1 공통 규칙

1. **주 지표는 `chars_nows`**(공백 제외 문자 수). 공백 정책이 형식마다 다르므로 `chars` 보다 안정적이다. 보조로 `chars`, `lines` 를 함께 보고한다.
2. **집계 대상은 §5의 품질 게이트를 통과한 유효 시행뿐이다.** 게이트 실패 시행의 길이는 어떤 통계에도 넣지 않는다.
3. **조건별 유효 시행이 3건 미만이면 그 가설은 "판정 불가"** 로 보고하고 길이 수치를 내지 않는다. 대신 게이트 실패 사유를 결과로 보고한다.
4. 대표값은 **중앙값**. 최소·최대를 함께 기록한다(n=4에서 평균은 이상치에 약하다).
5. 보고는 **조건 A 대비 상대비**로만. 전 수치에 `(proxy)` 표기. 절대 토큰 환산 금지.
6. **방향 일관성**: 유효 시행 중 3/4 이상이 같은 방향이어야 한다. 미달이면 "불안정 — n 증가 필요".

### 6.2 H1 (직렬화) 판정

| 판정 | 조건 |
|---|---|
| **채택** | B의 `chars_nows` 중앙값이 A 대비 **10% 이상 감소** AND B의 셀 정확도 중앙값 ≥ 0.99 AND B의 레코드 정확도 중앙값이 A 대비 2건 이상 낮지 않음 AND 방향 일관성 충족 |
| **조건부 (트레이드오프 있음)** | 길이 10% 이상 감소했으나 셀 정확도 중앙값이 0.95~0.99 |
| **기각** | 길이 감소 10% 미만, 또는 셀 정확도 중앙값 < 0.95, 또는 유효 시행 중 파싱 실패 1건 이상 |

임계 10%의 근거: 페이로드가 형식에 의해 거의 결정되어 조건 내 분산이 작은 과제다. 큰 임계는 불필요하게 보수적이다.

### 6.3 H2 (변경분) 판정

| 판정 | 조건 |
|---|---|
| **채택** | B의 `chars_nows` 중앙값이 A 대비 **10% 이상 감소** AND B의 **적용 실패 0건** AND B의 유효 시행 전부 30줄 완전 일치 + 부수 손상 0 |
| **조건부 ("짧지만 신뢰 불가")** | 길이는 감소했으나 적용 실패 또는 부수 손상이 1건 이상 |
| **기각** | 길이 감소 10% 미만, 또는 적용 실패 2건 이상 |

- 축4 H3의 부등식 `(변경비율 + 오버헤드비율) < 1 − q` 좌변은 `chars_nows(B)/chars_nows(A)` 중앙값으로, 우변은 `1 − (적용 실패 건수 / 유효 시행 수)` 로 산출해 **부등식 성립 여부를 그대로 보고**한다. n=4이므로 `q` 는 0, 0.25, 0.5, … 의 거친 해상도만 나온다. **`q` 를 정밀 추정했다고 주장하지 않는다.**
- 조건 A의 무효 시행이 2건 이상이면 §1.3-5에 따라 H2 전체를 "판정 불가(오염으로 baseline 붕괴)"로 보고한다.

### 6.4 H3 (억제 묶음) 판정 — **비대칭 규칙**

| 판정 | 조건 |
|---|---|
| **채택** | B의 `summary.md` `chars_nows` 중앙값이 A 대비 **15% 이상 감소** AND B의 품질 게이트 통과율이 A 이상 AND 방향 일관성 충족. **단 "하한"으로만 보고한다**(§1.3-4) |
| **판정 불가** | 감소 15% 미만인 모든 경우 |
| **기각** | **없음.** 어떤 결과로도 H3를 기각하지 않는다 |

- 기각 판정을 없앤 이유: 조건 A가 이미 저장소 `CLAUDE.md` 의 억제 규칙에 노출되어 있어, "효과 없음"과 "이미 억제되어 바닥 효과"를 구별할 수 없다(§1.4-3). 이 상태에서 기각을 선언하면 **오염을 근거로 공식 권고 기법을 부당하게 부정**하게 된다.
- 임계를 15%로 올린 이유: 에이전트 실행은 시행 간 분산이 크다(도구 호출 수가 2배 차이나는 일이 흔하다, 축5 L7). H1/H2의 결정적 페이로드와 같은 임계를 쓰면 노이즈를 효과로 오독한다.
- **보조 판정 (채택 여부와 별개로 기록)**: `comment_density`, `total_lines`, 미요청 산출물 개수의 조건별 중앙값. 이들이 감소하면 축5 H4·H5를 지지하는 **예비 신호**로만 기록하고 채택 판정을 내리지 않는다(요인 분해 없이 묶음 처치에서 개별 스니펫에 귀인할 수 없다).
- **귀인 한계 사전 명시**: 조건 B는 6개 스니펫 추가 + 검증 지시 제거의 **묶음**이다. 어떤 스니펫이 효과를 냈는지 라운드 1은 답하지 못한다.

### 6.5 전 가설 공통 — 보고 시 반드시 병기할 것

- 사용 모델 ID, n(유효/전체), 조건별 무효 건수와 사유
- `(proxy)` 표기, 절대 토큰 미환산
- **처치 프롬프트가 늘린 입력 문자 수** (H3 조건 B는 약 1,800자의 지시가 추가된다). 출력 절감이 입력 증가를 넘는지는 라운드 1 지표로 판정할 수 없으므로 "입력 증가분 병기"까지만 한다
- 오염 단서: 조건 A가 이미 억제 규칙 아래 있었다는 사실

---

## 7. 라운드 2 이월 (API 필요)

키(`ANTHROPIC_API_KEY`) 확보 즉시 착수. 전량 `usage.output_tokens` / `usage.output_tokens_details.thinking_tokens` 기준으로 재측정한다.

| 이월 항목 | 원 가설 | 왜 API가 필요한가 |
|---|---|---|
| `effort` 스윕과 응답문/thinking 분해 | 축3 H3-1 | `output_config.effort` 는 서브에이전트 프롬프트로 표현되지 않는다. thinking 토큰 분해는 `output_tokens_details` 없이 원리적으로 불가 |
| `thinking: disabled` 부작용(평문 도구 호출 누출, XML 태그 누출) 빈도 | 축3 H3-2 | 파라미터 조작 + 저빈도 사고 관측(n≥10) |
| `display: omitted` vs `summarized` 의 과금 동일성 | 축3 H3-3 | 응답 body 길이와 과금이 어긋나는지는 `usage` 로만 확인 가능 |
| `max_tokens` 하향이 절감인가 절단인가 | 축3 H3-4 | `stop_reason` 관측 필요 |
| `task_budget` vs `max_tokens` 완결률 | 축3 H3-5 | beta 헤더 + 파라미터 |
| 간결성 프롬프트와 effort의 직교성/가산성 | 축3 H3-7 | 두 레버의 합산 효과는 thinking 분해 없이 판정 불가 |
| Structured Outputs 포장지 제거 / 필수 필드 역효과 | 축2 H4a·H4b | `output_config.format` 은 API 파라미터 |
| enum 정수 코드화 · positional 반환 | 축2 H3·H5 | **문자↔토큰 비율이 깨져 proxy 측정이 무효**. 토큰 계측이 있어야만 의미 있는 가설 |
| PTC의 출력 토큰 기여분 분해 | 축4 H6 | code execution 도구 + 턴별 `usage` 누적 |
| 구조화 출력의 절단(`P_truncate`) 반전 조건 | 축4 H7 | `stop_reason == "max_tokens"` 비율 |
| 모델 티어별 출력 길이 성향 `O_h/O_o` → 라우팅 손익분기 | 축4 H1·H2, 축3 H3-6 | proxy로도 일부 가능하나 라운드 1 예산 밖. 토크나이저 세대 차(약 30%) 때문에 모델군 교차 문자→토큰 환산은 원리적으로 깨진다 |
| 간결성 지시의 **무오염 baseline** 절감률 | 축1 H1·H4, 축5 H3 | system prompt를 완전히 통제할 수 있어야 `CLAUDE.md` 오염 없는 조건 A를 만들 수 있다. §1.4-1·2의 "할 수 없는 주장"을 해소하는 유일한 경로 |
| 간결성 지시 위치(system 앞/뒤) | 축1 H2 | 서브에이전트는 system/user 분리를 제어하지 못한다 |
| 도구 호출 사이 나레이션 | 축5 H1 | `claude -p --output-format stream-json` 트랜스크립트 필요(API 키가 아니라 **실행 수단** 제약). 확보 시 `code_metrics.py transcript` 모드가 그대로 쓰인다 |

**라운드 1b (API 불필요, 예산만 확보되면 즉시 실행 가능):** 축2 H6(마크다운 표 vs TSV — H1 과제를 공유하므로 조건 1개 n=4면 충분, 최우선), 축1 H6/축5 H2(검증 지시 제거 단독), 축1 H1(긍정형 vs 부정형), 축1 H4(서론·맺음말 억제 단독), 축1 H7(프롬프트 마크다운 전이), 축2 H8(레코드 수 종속성), 축5 H7(묶음의 하위가산성), 축4 E1(멀티에이전트 팬아웃 — 에이전트 소비량이 커서 별도 예산 필요).
