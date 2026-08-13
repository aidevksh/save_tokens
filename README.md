# save_tokens

Claude 모델의 **출력(completion) 토큰**을 줄이는 방법을 Claude 에이전트가 직접 리서치·가설수립·실험·판정하는 저장소.

사전등록(pre-registration) 방식으로 진행한다. 데이터를 보기 전에 판정 기준을 고정하고, 실행 후에는 임계값·지표·집계 방식을 바꾸지 않는다.

## 라운드 1 결과

| 가설 | 판정 | 실측 (proxy) |
|---|---|---|
| 표 형태 페이로드를 JSON → 헤더 TSV | **채택** | **−65.9%** (공백 제외 문자 기준 / 원시 문자 −64.5%), 셀 정확도 손실 0 |
| 파일 수정을 전체 재출력 → unified diff | **기각** | **+22.3%** — diff가 더 길었다 |
| 억제 프롬프트 묶음 (코딩 에이전트) | 판정 불가 | 하네스 차단에 의한 차등 탈락 |

**"변경분만 출력"이 항상 이득은 아니다.** 30줄 YAML의 6줄 수정에서 unified diff는 원본보다 22% 길었다. 적용 실패는 0건이었으니 품질이 아니라 오버헤드에서 졌다 — 컨텍스트 3줄 × hunk 3개가 원본 대부분을 다시 실어 나른다.

자세한 판정 근거: [experiments/round1-results.md](experiments/round1-results.md)

## 라운드 2 결과 — 손익분기는 실재한다

변경 형상을 고정(6곳 수정, 3덩어리)하고 **파일 길이만** 바꿨다. 12시행 전부 품질 게이트 통과, 무효 0건, `git apply -p1` 성공 12/12.

| 파일 길이 | 전체 재출력 | diff (컨텍스트 3줄) | diff (컨텍스트 1줄) |
|---|---|---|---|
| **30줄** | 510자 | 641자 **+25.6%** | 476자 **−6.8%** |
| **120줄** | 2,469자 | 823자 **−66.7%** | 533자 **−78.4%** |

| 가설 | 판정 |
|---|---|
| 파일 길이가 diff의 승패를 뒤집는다 | **채택** — 부호 역전 확인. 라운드 1 기각은 "diff가 나쁘다"가 아니라 "N=30에서 졌다"였다 |
| 컨텍스트 축소가 손익분기를 아래로 옮긴다 | **채택** (근거 약함) — `N*`가 38~40줄에서 26~28줄로. 단 −6.8%는 2줄 마진의 칼날 위 |
| 오버헤드를 줄이면 적용 실패가 오른다 (H/q 결합) | **판정 불가** — 사전등록 §6 P5의 채택·기각 조건이 이 데이터에서 동시에 참이었다. 기준 결함이므로 결과를 보고 읽기를 고르지 않았다 |

라운드 2가 라운드 1을 두 곳 정정했다: H/q 결합은 연속 트레이드오프가 아니라 **컨텍스트 0줄에서만 나타나는 문턱**이고, 결정성은 과제 유형이 아니라 **출력 명세가 자유도를 남겼는가**의 속성이다.

자세한 판정 근거: [experiments/round2-results.md](experiments/round2-results.md)

## 구조

| 경로 | 내용 |
|---|---|
| [research/](research/) | 축별 리서치 — 가설과 근거. 수치는 전부 출처 URL 첨부 |
| [experiments/round1-plan.md](experiments/round1-plan.md) · [round2-plan.md](experiments/round2-plan.md) | 사전등록 (판정 기준 §6) |
| [experiments/round1-results.md](experiments/round1-results.md) · [round2-results.md](experiments/round2-results.md) | 판정 보고서 |
| [experiments/prompts/](experiments/prompts/) | 피험자 프롬프트 전문. 조건 간 공통부가 바이트 동일함을 생성기가 해시로 보장 |
| [experiments/runs/](experiments/runs/) | 시행 32건의 프롬프트와 산출물. 시행별 디렉터리 + 조건 대응표 + 파일 해시 목록 |
| [experiments/raw/](experiments/raw/) | 측정값, 품질 채점, 사건 기록, 가설 인덱스 |
| [dashboard/hypotheses.html](dashboard/hypotheses.html) | **가설 지도** — 37건 전수 현황. 축별로 묶고 판정·실측치·해설 링크를 붙였다. [tools/hypomap.py](tools/hypomap.py)가 TSV 두 개에서 생성 |
| [explainers/](explainers/) | 실험마다 하나씩. 입력 프롬프트 → 실제 산출물 → 절감률을 그림으로 따라가는 해설. 명세 JSON에서 [tools/explainer.py](tools/explainer.py)가 생성하며 HTML은 손으로 고치지 않는다 |
| [techniques/](techniques/) | 채택된 기법만. 기각·판정불가는 넣지 않는다 |
| [tools/measure.py](tools/measure.py) | 길이 계측기 (조건 간 언어 구성이 어긋나면 비교를 무효 처리) |
| [CLAUDE.md](CLAUDE.md) | 에이전트 운영 규칙 + 확정된 사실 |

## 측정에 관한 경고

이 저장소의 모든 수치는 **문자 수 proxy이며 토큰이 아니다.**

실행 환경에 `ANTHROPIC_API_KEY`가 없어 `usage.output_tokens`를 쓸 수 없었다. 조건 간 상대 비율로만 해석해야 하며, 절대 토큰으로 환산하면 안 된다. 특히 TSV는 탭과 짧은 토막이 많아 문자당 토큰 비율이 JSON과 다를 수 있으므로, −65.9%를 실제 토큰 절감률로 읽으면 안 된다.

API 키가 확보되면 [experiments/scripts/](experiments/scripts/)의 실행 대기 스크립트로 전량 재측정한다.

## 방법론상 알려진 한계

- **조건 내 분산 0.** 결정적 과제라 조건별 4개 시행이 바이트 단위로 동일한 산출물을 냈다. n=4로 표기하되 통계적으로는 조건당 1건과 같다.
- **baseline 오염.** 피험 서브에이전트가 프로젝트 `CLAUDE.md`를 물고 시작하는데 거기에 이미 억제 규칙이 있다. 순수 baseline을 만들 수단이 없어, 억제 프롬프트 가설의 측정치는 절감률의 **하한**으로만 읽는다.
- **차등 탈락.** 하네스가 서브에이전트의 리포트성 `.md` 쓰기를 막았고, 그 차단이 조건 A에만 2/2로 걸려 가설 하나가 판정 불가가 됐다. 상세: [experiments/raw/r1-incidents.md](experiments/raw/r1-incidents.md)

## 공개 시 적용한 편집

공개 저장소로 올리면서 실행 환경의 로컬 사용자명이 든 절대 경로를 익명화했다. 내용상 변경은 없다.

- `experiments/raw/r1-H*.json` — 측정 대상 키를 절대 경로에서 시행 ID(`t01/out.json`)로 축약
- `experiments/round1-plan.md` — 경로의 사용자명을 `<USER>`로 치환
- `experiments/scripts/score_r1.py` — 하드코딩된 시행 경로를 환경변수 `ST_R1_ROOT`로 분리 (익명화 후 재실행해 결과가 동일함을 확인)

측정값·판정·사전등록 기준은 손대지 않았다.
