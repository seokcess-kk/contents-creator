# Render 배포 + Cold Start 대응 가이드

백엔드 (`contents-creator-api`, FastAPI + uvicorn) 의 Render 호스팅 설정과
cold start 대응 옵션을 정리한다. 프론트엔드는 별도 (Vercel/Render Static).

상태 (2026-05-07 기준):

- 배포 정의: `render.yaml` + `Dockerfile`
- 현재 plan: **Starter** (`render.yaml:7`)
- Health endpoint: `GET /health` (`web/api/main.py:129`) — 인증 무관 200 OK
- APScheduler 인-프로세스 cron (순위 측정·재발행) → `web` service 가 항상 살아있어야 한다

---

## 1. Render 의 sleep 정책

| Plan | 월 가격 (USD) | RAM | Always-on | 비고 |
|---|---|---|---|---|
| Free | $0 | 0.5 GB | ❌ (15분 idle 후 sleep) | cron · WebSocket 끊김. 운영 부적합 |
| Starter | $7 | 0.5 GB | ✅ | 현재 plan. APScheduler/WS 유지 |
| Standard | $25 | 2 GB | ✅ | Playwright (브랜드 카드 PNG) 메모리 여유 |
| Pro | $85 | 4 GB | ✅ | 동시 작업 다수일 때 |

**오해 정정**: Render Starter 이상은 idle sleep 이 **없다**. cold start 가
체감되는 경우는 다음 중 하나다.

1. **배포 직후의 첫 요청** — 컨테이너 부팅 + uvicorn 워밍업 (10~30초)
2. **Free plan 사용 중** — 15분 무요청 후 sleep. 다음 요청에서 부팅 (30~60초)
3. **OOM kill 후 재시작** — Playwright + 동시 LLM 호출이 0.5 GB 를 넘으면 발생
4. **Render 의 자동 health-restart** — health check 실패 누적 시 컨테이너 재기동

운영 관점에서 1·3·4 가 진짜 cold start. 2 는 plan 업그레이드로 해소된다.

---

## 2. 권장 설정 — `render.yaml` 보강

현재 정의에서 빠진 항목 (운영 체감을 개선):

```yaml
services:
  - type: web
    name: contents-creator-api
    runtime: docker
    plan: starter
    dockerfilePath: ./Dockerfile

    # 추가 권장 ──────────────────────────────
    region: singapore             # 한국 사용자 latency. default oregon 은 200ms+ 추가
    healthCheckPath: /health      # Render 가 부팅 완료 인식 → 트래픽 라우팅 시점 단축
    autoDeploy: true              # main push 시 자동 빌드 (또는 false 로 수동 통제)
    # ────────────────────────────────────────

    envVars:
      ...
```

`healthCheckPath` 설정 시 효과:

- Render 가 신규 컨테이너의 `/health` 200 응답을 확인한 뒤에야 트래픽을 보낸다
- 부팅 중 사용자가 만나는 502/503 시간이 사실상 0
- 10초 간격으로 health 미응답 누적 시 자동 재기동 (자가 치유)

`region: singapore` 는 한국 사용자 RTT 를 약 30ms 로 단축 (oregon 200ms 대비).
변경은 새 region 으로 redeploy 가 일어나므로 한 번만 수동 실행.

---

## 3. Cold start 체감 완화 옵션

### A. 외부 keep-alive ping (권장 — 비용 0)

5분마다 `/health` 를 호출해 컨테이너를 항상 핫 상태로 유지. Starter plan 은
이미 always-on 이지만, 이 ping 은 **OOM 재시작 직후 첫 요청을 keep-alive 가
대신 받는** 효과가 있다.

무료 옵션:

- [UptimeRobot](https://uptimerobot.com) — 5분 간격, 50개 모니터까지 무료
- [cron-job.org](https://cron-job.org) — 1분 간격까지 무료
- [BetterStack Heartbeat](https://betterstack.com/uptime) — 알림과 통합

설정값:

```
URL:    https://<your-backend-domain>/health
Method: GET
Interval: 5 minutes
Expected status: 200
Alert if: response time > 5s OR status != 200
```

### B. 프론트엔드의 graceful 대응 (이미 적용됨)

- `/insights` RSC 가 `serverFetch` 실패 시 `null` 반환 → 클라이언트 SWR 가 자동 재시도
  (`web/frontend/src/app/insights/page.tsx:loadInitialSummary`)
- SWR 의 `errorRetryCount: 2` + `revalidateOnFocus: true` (`web/frontend/src/components/SwrProvider.tsx`)
- loading.tsx 9개로 첫 라우트 전환 시 빈 화면 대신 skeleton

추가로 검토 가능:

- 운영 홈 (`/`) 의 첫 진입 시 `serverFetch` 적용 (현재 client-only) — 부팅 직후 SWR
  재시도가 끝나기 전 사용자가 빈 카드를 보지 않도록
- 백엔드 readiness 가 아직 의심스러운 첫 5초 동안 frontend 가 명시적으로
  "백엔드 깨우는 중..." 토스트 표시

### C. Plan 업그레이드 (메모리 여유 → OOM 재시작 감소)

Playwright 사용 시점 (브랜드 카드 PNG 렌더) 이 동시 LLM 호출과 겹치면 0.5GB 가
빠듯하다. OOM 재시작이 주 1회 이상 관측되면 Standard 로 올린다 ($7 → $25/월,
+$18). 메모리 사용량은 Render 대시보드 Metrics 탭에서 확인.

판단 기준:

- 일평균 P95 메모리 > 400 MB → Standard 검토
- OOM kill (Render 로그에 `Killed`) 주 1회 이상 → 즉시 Standard

### D. Render Pro 의 "Zero-downtime deploys"

Pro plan 부터 새 컨테이너가 health check 통과한 뒤에야 구 컨테이너를 종료한다.
Starter 는 짧은 다운타임 (~5초) 이 있다. 운영 SLA 가 더 엄격해지면 Pro 검토.

---

## 4. 환경변수 운영 절차

`render.yaml:11-39` 의 `sync: false` 변수는 Render 대시보드에서 수동 입력한다.
키 회전 시:

1. Render 대시보드 → Service → Environment → 값 수정 → Save
2. 자동 재배포가 트리거됨 (배포 중 약 30초 다운타임 또는 Pro 면 zero-downtime)
3. 프론트엔드도 키를 쓰는 경우 (`API_KEY`, `ADMIN_API_KEY`) 함께 갱신

`.env.example` (`config/.env.example`) 과 `web/frontend/.env.local.example` 이
필요한 키 목록의 단일 출처. 새 키 추가 시:

1. `config/settings.py` 에 로딩 코드 추가
2. `config/.env.example` 갱신 (커밋)
3. `render.yaml` 의 `envVars` 에 항목 추가 (커밋)
4. Render 대시보드에서 실제 값 입력

---

## 5. 모니터링 체크리스트

매주 1회 다음을 점검:

- [ ] Render Metrics — CPU/메모리 P95, 재시작 횟수
- [ ] UptimeRobot — `/health` 가용성 99.9% 이상
- [ ] APScheduler 동작 — Supabase `ranking_snapshots` 의 매일 새 row 생성 여부
- [ ] 로그 grep — `ERROR`, `OOM`, `Killed`, `task was destroyed`
- [ ] 배치 야간 dispatch — `BATCH_OVERNIGHT_HOUR_KST` 시간대 후 신규 jobs 생성 여부

이상 신호 발견 시 `tasks/lessons.md` 에 기록.

---

## 6. 자주 묻는 항목

### Q. WebSocket 이 5분 후 끊어진다

Render Starter+ 는 WS 자체는 무제한 유지하지만, idle 60초 후 keepalive ping 이
없으면 proxy 가 끊는다. 클라이언트는 `lib/api.ts` 의 `mintJobWsToken` 로 재인증 후
재연결하면 된다. 서버 측 ping 주기를 조정하려면 `web/api/routers/jobs.py` 의 WS
endpoint 를 본다.

### Q. 배포 후 첫 요청만 느리다

`healthCheckPath: /health` 를 `render.yaml` 에 추가하면 해소된다 (§2 참조).
이미 추가했다면 부팅 시 import 가 무거운 모듈 (Playwright 등) 이 lazy-loaded
인지 확인.

### Q. Free plan 으로 내릴 수 있나

**불가**. APScheduler in-process cron 이 sleep 중에는 동작하지 않아 순위 측정·
재발행 라이프사이클이 끊긴다. WebSocket 도 sleep 시 끊긴다. 운영 환경은 Starter
이상 필수.

### Q. 비용 더 줄이려면

cron 분리: APScheduler 를 별도 worker service (Background Worker plan, $7) 로
빼면 web 만 Free 로 내릴 수 있지만, 코드 복잡도 + 배포 단위 2개로 늘어 ROI 가
낮다. Starter 단일 service 가 사실상 최저 비용 균형점.

---

## 7. 변경 이력

- `2026-05-07`: 신규 작성. 현재 Starter 운영 기준의 cold start 대응 옵션 정리
