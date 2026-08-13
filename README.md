# save_tokens

Claude 모델의 **출력(completion) 토큰**을 줄이는 방법을 Claude 에이전트가 직접 리서치·가설수립·실험·판정하는 저장소.

사전등록(pre-registration) 방식으로 진행한다. 데이터를 보기 전에 판정 기준을 고정하고, 실행 후에는 임계값·지표·집계 방식을 바꾸지 않는다.

## 라운드 1 결과

| 가설 | 판정 | 실측 (proxy) |
|---|---|---|
| 표 형태 페이로드를 JSON → 헤더 TSV | **채택** | 산출물 문자 수 **−65.9%**, 셀 정확도 손실 0 |
| 파일 수정을 전체 재출력 → unified diff | **기각** | **+22.3%** — diff가 더 길었다 |
| 억제 프롬프트 묶음 (코딩 에이전트) | 판정 불가 | 하네스 차단에 의한 차등 탈락 |

**"변경분만 출력"이 항상 이득은 아니다.** 30줄 YAML의 6줄 수정에서 unified diff는 원본보다 22% 길었다. 적용 실패는 0건이었으니 품질이 아니라 오버헤드에서 졌다 — 컨텍스트 3줄 × hunk 3개가 원본 대부분을 다시 실어 나른다. 컨텍스트 3줄 기준 손익분기는 약 40줄이다.

자세한 판정 근거: [experiments/round1-results.md](experiments/round1-results.md)

## 구조

| 경로 | 내용 |
|---|---|
| [research/](research/) | 축별 리서치 — 가설과 근거. 수치는 전부 출처 URL 첨부 |
| [experiments/round1-plan.md](experiments/round1-plan.md) | 라운드 1 사전등록 (판정 기준 §6) |
| [experiments/round1-results.md](experiments/round1-results.md) | 판정 보고서 |
| [experiments/raw/](experiments/raw/) | 시행 20건 원시 산출물, 측정값, 품질 채점, 사건 기록 |
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
