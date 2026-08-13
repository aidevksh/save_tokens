# 실험 입력 데이터 — 설정 파일 수정 과제 (축 2, 실험 2 / 변경분 vs 전체 재출력)

> 피험 에이전트에게는 **프롬프트에 붙여넣어** 제공한다. 파일 경로를 주지 않는다.
> 기대 결과 파일은 `02-patch-expected.yaml` (판정자 전용).

---

## 원본 파일 `deploy.yaml` (30줄)

```
 1  service: payments-api
 2  replicas: 3
 3  image: registry.example.com/payments-api:1.4.2
 4  port: 8080
 5  env: staging
 6  resources:
 7    cpu: 500m
 8    memory: 512Mi
 9    gpu: 0
10  healthcheck:
11    path: /healthz
12    interval_seconds: 10
13    timeout_seconds: 2
14    failure_threshold: 3
15  logging:
16    level: debug
17    format: text
18    retention_days: 7
19  autoscale:
20    enabled: false
21    min_replicas: 1
22    max_replicas: 5
23    target_cpu_percent: 80
24  database:
25    host: db-staging.internal
26    port: 5432
27    pool_size: 10
28    ssl: false
29  timeouts:
30    request_seconds: 30
```

## 변경 요청 (6곳)

1. `replicas` 를 3에서 6으로 변경
2. `env` 를 `staging` 에서 `production` 으로 변경
3. `logging.level` 을 `debug` 에서 `info` 로 변경
4. `logging.format` 을 `text` 에서 `json` 으로 변경
5. `autoscale.enabled` 를 `false` 에서 `true` 로 변경
6. `database.ssl` 을 `false` 에서 `true` 로 변경

나머지 24줄은 변경하지 않는다.
