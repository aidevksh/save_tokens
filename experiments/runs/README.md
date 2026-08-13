# 시행 기록

라운드별 시행 하나당 디렉터리 하나. **피험 에이전트에게 준 프롬프트와 그가 낸 산출물이 짝으로 들어 있다.**

```
experiments/runs/
  r1/
    conditions.tsv     시행 -> 조건 대응표
    manifest.tsv       파일 목록 + 바이트 + 해시
    t01/ … t22/        시행별 산출물
  r2/
    conditions.tsv
    manifest.tsv
    t01/ … t12/        prompt.txt + 산출물
```

## 왜 시행을 저장소 안에서 돌리지 않는가

시행 **작업** 디렉터리는 저장소 **밖** 임시 경로에 만든다. 저장소 안에서 돌리면 피험 에이전트가 정답 키(`experiments/data/*-groundtruth.*`), 기대 결과 파일, 사전등록 문서를 읽을 수 있다. 그러면 naive 조건이 깨지고 측정이 무의미해진다.

실행이 끝난 뒤 여기로 복사한다:

```
python tools/preserve.py --import <작업루트> --round r3
```

복사할 때 실행 환경의 절대 경로를 `<RUNDIR>` 로 치환하고, 남은 경로 노출이 있으면 exit code 2로 막는다. 저장소가 공개라 로컬 사용자명이 올라가면 안 된다.

## 프롬프트 위치

| 라운드 | 프롬프트 | 비고 |
|---|---|---|
| r1 | `experiments/prompts/r1-H*-*.txt` | 조건당 1개. 사전등록 §3 원문을 추출한 것 |
| r2 | `experiments/runs/r2/t*/prompt.txt` | 시행마다 실제로 준 전문 |

라운드 1은 시행별 프롬프트 파일을 남기지 않았다(조건이 같으면 프롬프트가 같아서 조건당 1개로 충분하다). 라운드 2부터는 시행 디렉터리에 그대로 들어 있다.

## 경로 이력

라운드 1·2의 산출물은 원래 `experiments/raw/r1-t*/`, `experiments/raw/r2-t*/` 에 있었고 여기로 옮겼다. 라운드 1 사전등록(`round1-plan.md`) 부록의 보존 경로가 옛 위치를 가리키는데, **사전등록 문서는 사후에 고치지 않는다**는 규칙에 따라 그대로 뒀다. 현재 위치는 이 문서가 기준이다.

`experiments/raw/` 에는 측정·채점 결과(`*-scores.json`, `*-quality.json`, `*-H*.json`)와 사건 기록(`r1-incidents.md`)만 남아 있다.
