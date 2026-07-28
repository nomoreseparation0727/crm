# 자산운용사 트래커

여러 자산운용사를 시간에 따라 추적합니다: AUM 추이, 펀드 보유종목(한국 주식 비중에
특히 초점), 주요 인사, 분기별 SEC 13F 공시. 현재 추적 중인 회사는
[Burgundy Asset Management](https://www.burgundyasset.com)(캐나다 토론토),
[Kopernik Global Investors](https://www.kopernikglobal.com)(미국 플로리다),
[DRZ](https://drz-inc.com) 세 곳이며, `scraper/burgundy/companies.py`에 회사를
추가하는 것만으로 새로운 회사를 계속 추가할 수 있습니다. 모든 관측치는 덮어쓰지
않고 새로운 행으로 저장되므로 전체 이력을 쿼리할 수 있고, 변경 감지(diffing)
엔진이 연속된 스냅샷을 비교해 변경 로그("신규 보유종목", "AUM 5% 증가", "OOO 퇴사"
등)를 만들어냅니다.

## 이런 설계를 택한 이유

여기서 추적하는 회사들은 대부분 **외국(캐나다/미국) 민간 운용사**이기 때문에
한국의 규제 공시 제도(DART)가 적용되지 않습니다 — 이런 회사의 "AUM + 전체
포트폴리오 + 인사 정보"를 한 번에 제공하는 단일 API는 존재하지 않습니다. 대신
다음 두 가지 소스를 사용합니다:

1. **SEC EDGAR 13F** (`scraper/burgundy/sources/sec_edgar.py`) -- 구조화되어 있고
   무료이며, 규정에 맞는 User-Agent 헤더만 있으면 별도 인증이 필요 없습니다. 분기별로
   갱신됩니다. 각 회사가 미국 기관투자운용사로서 보고하는 미국 상장 주식과 ADR만
   다루며, 직접 보유한 한국 보통주는 **절대** 여기에 나타나지 않습니다. 2018년
   이후 공시만 수집합니다 (오래된 정기 추이 파악이 목적이 아니고, 2013년 XML
   공시 의무화 이전 공시는 형식이 달라 안정적으로 파싱되지 않습니다).
2. **각 회사의 홈페이지** (`scraper/burgundy/sources/website.py`) -- 회사 자체의
   팀 소개 페이지와 펀드 팩트시트/코멘터리 PDF로, 실제로 한국 보유종목, AUM 수치,
   인사 정보가 나오는 곳입니다.

모든 데이터는 계속 추가(append)되는 방식(SCD Type 2 스타일, `db/migrations/0001_init.sql`
참고)이라, 추이와 변경사항은 그때그때 계산하는 게 아니라 이력에 대한 단순 SQL 쿼리로
얻을 수 있습니다.

## 새 회사 추가하기

`scraper/burgundy/companies.py`의 `COMPANIES` 목록에 `CompanyConfig` 하나를
추가하면 됩니다:

```python
CompanyConfig(
    slug="acme",                          # 대시보드 URL(/acme)에 쓰이는 짧은 식별자
    name="Acme Asset Management",
    website="https://www.acme-example.com",
    team_url="https://www.acme-example.com/our-team/",   # 추측값 -- 아래 참고
    funds_url="https://www.acme-example.com/funds/",      # 추측값 -- 아래 참고
    aum_currency="USD",                    # 회사가 자체 공시하는 통화
    sec_cik=None,                           # 확인 전까지는 None, 아래 참고
)
```

이 값들은 이름/웹사이트 등 **공개된 사실**이라 환경변수가 아니라 코드로 관리합니다.
DB 스키마와 스크래퍼/대시보드 코드 전부 이미 다중 회사를 지원하도록 되어 있어서,
이 한 파일만 고치면 됩니다.

- `team_url` / `funds_url`은 실제 사이트 구조를 모른 채 채워 넣은 **추측값**입니다.
  Burgundy 때와 마찬가지로: 첫 배포 후 로그에서 404가 나면 실제 경로로 고치면 됩니다.
- `sec_cik`은 비워두면 이름으로 자동 검색을 시도하는데, 비슷한 이름의 다른 회사를
  잘못 찾을 위험이 있습니다. https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany
  에서 직접 확인해서 채워 넣는 걸 권장합니다.

## 알려진 한계: 웹사이트 스크래퍼는 실제 사이트로 검증되지 않았음

burgundyasset.com/kopernikglobal.com/drz-inc.com은 이 프로젝트를 만드는 동안
이 개발 환경에서 직접 열어볼 수 없었습니다 (개발 환경 자체의 아웃바운드 정책 때문 --
실제로 Railway에서 배포해보면 사이트 자체는 잘 열립니다). 그래서
`sources/website.py`는 실제 DOM을 확인해서 만든 고정 CSS 셀렉터 대신 **휴리스틱
패턴 매칭**(사람 이름처럼 보이는 제목, "assets"라는 단어 근처의 "billion" 앞 숫자,
퍼센트로 끝나는 표의 행 등)을 사용합니다.

모든 요청은 `raw_snapshots` 테이블에 그대로 보관되는데, 이는 나중에 파서를 튜닝할 때
사이트를 다시 긁어올 필요 없이 이미 가져온 HTML/PDF 텍스트로 재실행할 수 있도록
하기 위함입니다. 각 회사를 배포한 뒤에는:

1. `raw_snapshots`에서 실제로 무엇이 수집됐는지 확인하세요.
2. `scrape_runs`에서 에러를 확인하세요 (`SELECT * FROM scrape_runs ORDER BY id DESC`).
   `company_id`로 어느 회사의 실행인지 구분됩니다.
3. 경로가 틀렸다면 `companies.py`의 `team_url` / `funds_url`을 실제 경로로 고치세요.
4. `sources/website.py`의 파싱 휴리스틱을 실제 콘텐츠에 맞게 조정하세요.

SEC 13F 파이프라인에는 이런 문제가 없습니다 -- `data.sec.gov`의 JSON API와 13F
정보 테이블(information table) XML 스키마는 안정적이고 문서화된 포맷입니다.

## 저장소 구조

```
db/migrations/    순수 SQL 마이그레이션 (schema_migrations 테이블이 적용 여부를 추적)
db/migrate.py     멱등적인(idempotent) 마이그레이션 실행기
scraper/          Python: 데이터 수집, 스냅샷/변경사항 기록, Railway cron이 실행
  burgundy/companies.py   추적 대상 회사 목록 (여기에 회사 추가)
dashboard/        Next.js: 동일한 Postgres를 읽어 AUM/보유종목/팀 정보를 렌더링
  app/[company]/  회사별 대시보드 라우트 (/burgundy, /kopernik, /drz, ...)
```

## 로컬 환경 설정

Postgres, Python 3.12+, Node 20+가 필요합니다.

```bash
createdb burgundy
export DATABASE_URL=postgresql://localhost/burgundy
python3 db/migrate.py

cd scraper
pip install -r requirements.txt
cp ../.env.example ../.env   # 최소한 SEC_EDGAR_USER_AGENT는 채워야 함
python3 -m burgundy.jobs.run_all

cd ../dashboard
npm install
cp .env.local.example .env.local   # 동일한 DATABASE_URL
npm run dev   # http://localhost:3000 (첫 추적 회사로 자동 이동)
```

## Railway 배포

하나의 Railway 프로젝트에 세 개의 서비스를 만듭니다:

1. **Postgres** -- Railway의 관리형 Postgres 플러그인.
2. **scraper** (cron) -- 이 GitHub 저장소로부터 새 서비스 생성.
   - Root Directory: 저장소 루트 (Dockerfile이 빌드 컨텍스트로 `db/`가 필요하며,
     `scraper/railway.toml`의 `dockerfilePath`를 참고하세요).
   - `DATABASE_URL`은 Postgres 플러그인의 연결 변수로 설정 (`${{Postgres.DATABASE_URL}}`
     참조 문법 사용, 직접 값을 복사/붙여넣기하지 말 것 -- 값이 잘릴 수 있음),
     `SEC_EDGAR_USER_AGENT`는 실제 연락처 문자열로 설정하세요.
   - Cron 일정은 `scraper/railway.toml`에 설정되어 있습니다 (매일 UTC 06:00);
     대시보드의 Settings -> Cron Schedule에서 변경하거나 파일을 직접 수정하세요.
   - 실행할 때마다 먼저 대기 중인 마이그레이션을 적용하므로(`entrypoint.sh`),
     스키마 변경사항이 배포와 함께 자동으로 반영됩니다.
3. **dashboard** (web) -- 같은 저장소로부터 또 다른 서비스 생성.
   - Root Directory: `dashboard/`.
   - `DATABASE_URL`을 동일한 Postgres 변수로 설정하세요.
   - Nixpacks를 사용합니다 (Next.js에는 Dockerfile이 필요 없음); `next start`가
     Railway의 `PORT`를 자동으로 읽습니다. `package.json`의 `engines.node`가
     Nixpacks에게 적절한 Node 버전을 알려줍니다.

대시보드가 첫 예약 실행을 기다리지 않고 바로 데이터를 보여줄 수 있도록, scraper의
첫 실행은 수동으로 트리거하세요 (Railway에서는 cron 서비스를 즉시 실행할 수 있습니다).

## 데이터 모델

전체 스키마는 `db/migrations/`를 참고하세요. 요약:

| 테이블 | 저장하는 내용 |
|---|---|
| `companies` | 추적 대상 회사 (`slug`로 대시보드 라우팅) |
| `aum_snapshots` | AUM 수치 이력, 관측 1건당 1행 |
| `funds` | 각 회사가 운용하는 펀드 (웹사이트에서 발견된 것들) |
| `fund_holdings_snapshots` | 관측 시점별 펀드 상위 보유종목 (전체 포트폴리오가 아니라 공개된 만큼만) |
| `sec13f_filings` / `sec13f_holdings` | 분기별 13F 공시와 그 세부 항목 |
| `executives_snapshots` | 관측 시점별 팀/리더십 명단 |
| `change_events` | 매 스크래핑 직후 계산된 변경사항 -- 대시보드의 활동 피드는 이 테이블만 읽음 |
| `raw_snapshots` | 요청마다 보관된 원본 HTML/PDF 텍스트, 재스크래핑 없이 파서를 재튜닝하기 위함 |
| `scrape_runs` | 작업 실행 로그 (상태, 에러, 처리 건수), `company_id`로 회사별 구분 |

## 컴플라이언스 참고사항

- SEC EDGAR는 호출자를 식별할 수 있는 설명이 담긴 User-Agent를 요구합니다; 스크래퍼는
  `SEC_EDGAR_USER_AGENT`를 통해 이를 강제하며, 값이 없으면 실행을 거부합니다.
- 웹사이트 스크래퍼는 공개적으로 게시된 페이지(팀 소개, 펀드 팩트시트)만 읽습니다 --
  인증 우회나 비공개(gated) 콘텐츠 스크래핑은 하지 않습니다.
- DART 등 한국 규제 API는 사용하지 않습니다. 여기서 추적하는 회사들은 외국 민간
  운용사이며, 한국에 본사를 둔 운용사에 적용되는 방식의 DART 공시 의무가 적용되지
  않기 때문입니다.
