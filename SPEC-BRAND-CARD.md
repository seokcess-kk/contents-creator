# 콘텐츠 엔진 MVP Spec — 브랜드 카드 트랙 v1

> 작성일: 2026-04-16
> 단계: Phase 1 (MVP) — SEO 트랙과 병행
> 범위: 브랜드 등록 → 자산 추출 → 키워드 기반 상세페이지형 카드 기획 → 이미지 슬롯 생성 → HTML 합성 → 완화 의료법 검증 → 풀페이지 PNG 출력
> 자매 문서: `SPEC-SEO-TEXT.md` (SEO 트랙). 두 트랙의 합류 지점은 본 문서 §13 + `SPEC-SEO-TEXT.md` §14 에 정의

---

## 1. 목표 & 핵심 원칙

### 1-1. 목표

특정 브랜드(주로 병원·한의원)의 **상세페이지형 마케팅 자산**을 키워드별로 생성한다. 산출물은 네이버 블로그 본문 안에 이미지로 삽입되며, 검색 후킹 → 브랜드 인지 → 유입 동선의 시각적 구성요소가 된다.

### 1-2. 핵심 원칙

- **상세페이지 = 마케팅 풀스토리** — 단순 카드가 아니라 도입→공감→솔루션→차별화→증거→FAQ→CTA까지 풀세트 마케팅 자산
- **분석 1번, 생성 N번** — 브랜드 등록·자산 추출은 1회. 키워드별 카드 생성은 N회
- **템플릿이 슬롯을 정의, LLM 은 카피·이미지 슬롯 결정** — 디자인은 코드(템플릿)가, 메시지는 LLM이
- **동일 카피, 다른 레이아웃** — SOV 다양성. 같은 핵심 메시지를 여러 시각 표현으로
- **완화 의료법 (BRAND_LENIENT)** — 법적 risk 만 차단, 마케팅 후킹 표현은 허용
- **사용자 입력 우선, LLM 보완** — 브랜드 자산은 사용자가 1차 입력, 빈 필드만 LLM이 자동 추출
- **트랙 격리** — SEO 트랙(`domain/crawler`, `analysis`, `generation`, `composer`)과 코드 import 의존 제로. 합류는 application 레이어에서만

### 1-3. 이 Spec 에 포함되지 않는 것 (추후 단계)

- 브랜드 카드 A/B 테스트, 클릭률 트래킹
- 비주얼 분석(VLM)으로 경쟁사 카드 자동 분석
- 영상·GIF 산출물
- 카드 자동 본문 삽입 (현재는 사용자 수동 업로드)
- 다국어 카드 (한국어 only)

---

## 2. 산출물 규격

### 2-1. 캔버스

| 항목 | 값 | 비고 |
|---|---|---|
| 가로 | **1080 px 고정** | 네이버 본문 권장 폭 |
| 세로 | **가변** (블록 구성에 의해 결정) | 블록 시퀀스의 자연 높이 |
| 권장 범위 | min 2400 / target 4000~6000 / soft max 9000 / hard max 18000 px | 9000 초과 시 자동 분할 |
| 파일 단위 | **확장자는 PNG 통일, 장수는 가변** | 기본 1 카드 = 1 파일. 9000 px 초과 시 자동으로 N 장 분할 (§2-4 참조) |
| 색공간 | sRGB | |
| DPI | 72 | 웹 표준 |
| 폰트 임베딩 | 시스템 폰트 X. 프로젝트 `assets/fonts/` 의 한국어 웹폰트 사용 (Pretendard 권장) | |

### 2-2. 포맷

- **PNG only** (투명도 불필요, 24bit)
- 압축: pillow `optimize=True`
- 메타데이터: 생성 시각·브랜드 ID·키워드·템플릿 ID·variant 번호를 PNG `tEXt` 청크에 기록 (운영 추적용)

### 2-3. 파일명 규칙

```
# 분할 없음
card-{template_id}-{variant_idx:02d}.png
예) card-clinic-classic-01.png

# 자동 분할 시 (9000 px 초과)
card-{template_id}-{variant_idx:02d}{split_suffix}.png
예) card-clinic-classic-01a.png, card-clinic-classic-01b.png, card-clinic-classic-01c.png
```

- 분할된 파일은 `a` → `b` → `c` 순으로 위에서 아래. 사용자는 네이버 업로드 시 이 순서대로 첨부
- `cards-manifest.json` 에 분할 정보 명시 (§5-9)

### 2-4. 자동 분할 규칙

소프트 max(9000 px) 초과 시:
1. **분할 경계 후보** = 블록과 블록 사이의 수직 여백 중점
2. 각 분할 조각은 **가로 1080 유지**, 세로 4000~8000 사이가 되도록 경계 선택 (그리디)
3. 한 블록 내부는 절대 분할하지 않음 (블록 중간에서 잘리면 가독성 파괴)
4. 블록 하나가 단독으로 9000 px 초과하면 — 해당 카드 변형은 실패 처리 (템플릿 설계 오류 경고)
5. 최종 조각 수가 4장 초과하면 경고 로그. 사용자가 해당 키워드에서 해당 템플릿을 피하도록 유도

### 2-5. 네이버 본문 삽입 워크플로우 (수동)

1. `cards-manifest.json` 의 `recommended_position` 확인
2. 사용자가 네이버 스마트에디터에서 해당 위치에 이미지 업로드
3. 분할 카드인 경우 `a` → `b` → `c` 순서로 연속 업로드
4. 자동 삽입 미지원 — 네이버 에디터의 외부 이미지 참조는 끊기므로

---

## 3. 상세페이지 블록 카탈로그 (병원 마케팅 표준)

한국형 병원·클리닉 상세페이지 레퍼런스 기반 13개 표준 블록. 템플릿이 이 중 일부를 슬롯으로 정의하고, LLM 이 슬롯을 채운다.

### 3-1. 블록 카탈로그

| ID | 한글명 | 역할 | 필수성 | 권장 높이(px) | 이미지 슬롯 권장 |
|---|---|---|---|---|---|
| `hero` | 히어로 | 첫인상·메인 카피·시각 후킹 | 필수 | 800~1200 | 강력 권장 |
| `pain_hook` | 고민 후킹 | "이런 고민 있으신가요?" 페인 포인트 나열 | 필수 | 600~900 | 선택 |
| `empathy` | 공감 | 독자 감정 동조 | 선택 | 400~600 | 텍스트 위주 |
| `why_now` | 왜 지금 | 시급성·계절성·트렌드 근거 | 선택 | 400~600 | 통계/그래픽 권장 |
| `solution_intro` | 솔루션 소개 | 브랜드의 접근 방법 개요 | 필수 | 600~900 | 권장 |
| `differentiator` | 차별점 | 3~5개 차별 포인트 (아이콘 그리드) | 필수 | 800~1200 | 아이콘 슬롯 다수 |
| `process` | 진료 과정 | 단계별 진행 흐름 (1→2→3→...) | 선택 | 700~1000 | 단계별 일러스트 권장 |
| `doctor_team` | 의료진 | 원장·전문의 프로필 | 선택 | 600~900 | **브랜드 `media_library` 참조** (type=`doctor`) |
| `equipment` | 장비/시설 | 장비·시술실 강조 | 선택 | 500~800 | **브랜드 `media_library` 참조** (type=`equipment` 또는 `facility`) |
| `case_result` | 사례/결과 | 일반화된 결과 서술 (Before/After 직접 언급 금지 — 의료법) | 선택 | 700~1000 | 다이어그램 권장 (AI 생성 가능) |
| `review` | 후기/평판 | 환자 인용 (의료법 가이드 준수) | 선택 | 500~800 | 텍스트 위주 |
| `faq` | FAQ | 주요 질문 3~5개 | 선택 | 600~900 | 텍스트 위주 |
| `closer` | 마무리 | 브랜드 마무리 인사 + 검색 유도 텍스트(예: "네이버에서 'OO한의원' 검색") + 주소·영업시간 | 필수 | 500~800 | 로고만 (지도는 본문 네이버 지도 임베드로 분리) |

> **location_map 블록 없음**: 네이버 지도는 블로그 본문에 별도 임베드(네이버 스마트에디터 기능)로 삽입하므로 카드 내부에 렌더하지 않음. `closer` 블록의 주소·영업시간 텍스트만 카드에 포함.
>
> **CTA 버튼 UI 금지**: 네이버 블로그 본문 이미지는 클릭 시 외부 링크 이동이 불가능하다. 따라서 "상담 예약", "전화하기" 같은 버튼형 UI 요소는 시각적으로도 생성하지 않는다 (사용자 오해 방지). `closer` 블록은 오로지 텍스트 정보 전달 — 브랜드 네임, 검색 유도 문구, 주소, 영업시간, 로고 이미지만 포함한다. `BrandGuideline.cta_examples` 필드는 [B4] LLM 프롬프트의 톤 참고용으로만 사용하고, 실제 블록 렌더에는 버튼 스타일로 노출되지 않는다.
>
> **실사 사진 vs AI 이미지 분리**:
> - `doctor_team`, `equipment` 는 실제 인물·시설 사진이 필요하므로 **Nano Banana 생성 금지**. 반드시 브랜드 `media_library` 에서 참조
> - `media_library` 에 해당 type 의 자산이 없으면 그 블록은 **자동 skip** (블록 시퀀스에서 제외)
> - `hero`, `differentiator`, `case_result` 등은 AI 이미지 생성 가능 (Nano Banana)

### 3-2. 블록 입력 스키마 (모든 블록 공통)

```python
class BlockId(str, Enum):
    HERO = "hero"
    PAIN_HOOK = "pain_hook"
    EMPATHY = "empathy"
    WHY_NOW = "why_now"
    SOLUTION_INTRO = "solution_intro"
    DIFFERENTIATOR = "differentiator"
    PROCESS = "process"
    DOCTOR_TEAM = "doctor_team"
    EQUIPMENT = "equipment"
    CASE_RESULT = "case_result"
    REVIEW = "review"
    FAQ = "faq"
    CLOSER = "closer"

class Block(BaseModel):
    id: BlockId                      # 자유 문자열 금지 — Enum 강제
    template_slot_idx: int           # 템플릿 내 슬롯 번호
    headline: str | None
    subheadline: str | None
    body: list[str]                  # 본문 단락 또는 불릿
    callouts: list[str] = []         # 강조 포인트 (아이콘 그리드 등)
    image_slot: ImageSlot | None     # 이미지가 필요한 블록만
    layout_variant: str              # "left_text", "centered", "two_col" 등
    background_token: str            # 디자인 토큰 키 (color/gradient)
```

```python
class ImageSourceKind(str, Enum):
    AI = "ai"                        # Nano Banana 생성
    MEDIA_LIBRARY = "media_library"  # 브랜드 실사 사진 참조

class AiImagePurpose(str, Enum):
    HERO = "hero"
    ICON = "icon"
    SECTION_BG = "section_bg"
    PROCESS_STEP = "process_step"
    DIAGRAM = "diagram"

class ImageSlot(BaseModel):
    source_kind: ImageSourceKind
    aspect_ratio: str                # "16:9", "1:1", "3:4"

    # source_kind=AI 일 때만
    ai_purpose: AiImagePurpose | None = None
    prompt_hint: str | None = None
    style_tokens: list[str] = []     # ["clean", "medical", "warm"] 브랜드 자산에서 주입

    # source_kind=MEDIA_LIBRARY 일 때만
    media_type: MediaAssetType | None = None
    selection_tags: list[str] = []   # 라이브러리 선택 힌트 (예: ["principal"])
    selected_asset_id: UUID | None = None  # [B4] 이후 [B5]/[B6] 에서 채워짐

    fallback_text: str | None = None # 이미지 없을 시 대체 텍스트

    @model_validator(mode="after")
    def check_source_kind_fields(self):
        if self.source_kind == ImageSourceKind.AI:
            if self.ai_purpose is None or self.prompt_hint is None:
                raise ValueError("AI source requires ai_purpose and prompt_hint")
            if self.media_type is not None:
                raise ValueError("AI source must not set media_type")
        else:  # MEDIA_LIBRARY
            if self.media_type is None:
                raise ValueError("media_library source requires media_type")
            if self.ai_purpose is not None or self.prompt_hint is not None:
                raise ValueError("media_library source must not set ai_* fields")
        return self
```

> `purpose` 필드가 AI용·media 용 값을 동시에 가지는 dual-truth 를 제거했다. AI 이미지 목적은 `ai_purpose`, media 타입은 `media_type` 으로 완전 분리한다. model_validator 가 런타임 불일치를 차단한다.

### 3-2-1. 블록 → media_type 매핑 (결정적)

media_library 참조 블록과 MediaAssetType 의 매핑은 코드 상수로 고정:

```python
BLOCK_MEDIA_MAPPING: dict[BlockId, MediaAssetType] = {
    BlockId.DOCTOR_TEAM: MediaAssetType.DOCTOR,
    BlockId.EQUIPMENT: MediaAssetType.EQUIPMENT,
    # facility 타입이 필요한 블록은 equipment 와 통합 운영. 필요 시 별도 BlockId 신설
}
```

이 매핑에 없는 블록은 AI 이미지 또는 텍스트 전용. 매핑은 `domain/brand_card/block_rules.py` 에 단일 출처로 관리.

### 3-3. 블록 조합 규칙

- **필수 5개**: `hero`, `pain_hook`, `solution_intro`, `differentiator`, `closer`
- **권장 시퀀스**:
  ```
  hero → pain_hook → empathy(opt) → why_now(opt) → solution_intro
       → differentiator → process(opt) → doctor_team(opt)
       → equipment(opt) → case_result(opt) → review(opt) → faq(opt) → closer
  ```
- **블록 수**: 최소 5개(필수만), 권장 8~10개, 최대 13개 전체
- 블록 순서는 권장 시퀀스를 기본으로 하되 **템플릿 정의가 우선**
- **media_library 참조 블록(BLOCK_MEDIA_MAPPING 내 블록)은 필수로 승격할 수 없다.** 필수 블록은 반드시 텍스트 또는 AI 이미지로만 구성되어야 한다. 이유: 사진 자산이 없는 브랜드도 카드 생성이 가능해야 함

### 3-4. 의료법 친화 블록 작성 규칙 (모든 블록 공통)

블록 카피 작성 시 다음을 준수. fixer 가 후처리하지만 사전 주입이 1차 방어:

- Before/After 직접 언급 금지 → "변화", "개선" 같은 일반 표현
- "100%", "완치", "최고", "유일" 등 절대 표현 금지
- 다른 의료기관과의 직접 비교 금지
- 환자 후기는 일반화 (특정 효과 보장 표현 X)
- 시술명은 표준 명칭 사용

---

## 4. 브랜드 등록 (Brand Onboarding)

### 4-1. 입력 채널

| 입력 | 형식 | 필수성 |
|---|---|---|
| 브랜드명 | 텍스트 | 필수 |
| 홈페이지 URL | URL | 필수 |
| 로고 파일 | png/svg | 권장 (없으면 홈페이지에서 추출 시도) |
| 추가 소스 (텍스트) | txt / docx / pdf 다중 업로드 | 선택 |
| **media_library (실사 사진)** | jpg/png 다중 업로드 + type 라벨 | 선택 — 있으면 `doctor_team`·`equipment` 블록 사용 가능 |
| 사용자 직접 입력 (구조화 폼) | JSON | **권장** — 빈 필드만 LLM 보완 |

### 4-1-1. brand slug 정규화 규칙

`brand_profiles.slug` 는 파일 시스템 경로·DB 인덱스 양쪽에서 사용되므로 정규화 필수.

```python
def normalize_brand_slug(name: str) -> str:
    # 1. 한글 → 로마자 (korean-romanizer 또는 unicodedata)
    # 2. 소문자화
    # 3. 공백 → "-"
    # 4. 영문/숫자/하이픈 외 제거
    # 5. 연속 하이픈 단일화
    # 6. 양 끝 하이픈 제거
    # 7. 최대 50자 트림
    # 예: "강남 OO한의원" -> "gangnam-oo-hanuiwon"
```

- slug 충돌 시 `-2`, `-3` 접미사 자동 부여
- slug 는 등록 시 1회 고정. 브랜드명 변경해도 slug 유지 (참조 안정성)

### 4-2. 자산 추출 파이프라인 [B1]~[B3]

```
[B1] 소스 수집 + 전처리
  - 홈페이지: Bright Data Web Unlocker 로 fetch (SEO 트랙과 동일 zone 재사용)
    → BeautifulSoup 으로 <script>/<style>/<nav>/<footer> 제거
    → 본문 텍스트 추출 (body 전체 .get_text(separator="\n", strip=True))
    → 길이 20000자 초과 시 머리 + 꼬리 10000자씩 slicing
  - 첨부 파일: 로컬 파일 → 텍스트 변환
    → txt: 그대로
    → docx: python-docx (paragraph 순회 + 표 셀 flatten)
    → pdf: pypdf 로 페이지별 extract_text. 파싱 실패/빈 텍스트면 pdfplumber 로 fallback
  - 로고: 사용자 업로드 우선. 없으면 홈페이지 HTML 에서 <link rel="icon">,
    og:image, header 내 img[alt*=logo], class 에 logo 포함 img 순차 폴백
  - media_library: 사용자가 업로드한 실사 사진 파일 + type 라벨
    → 메타 추출: Pillow 로 해상도·orientation 판별
    → 원본 복사: **brands/{slug}/media/{id}.{ext}** (brand 레벨, version 무관)
    → sha256 해시 계산 → 중복 체크 (unique (brand_id, file_sha256))
    → MediaAsset 레코드 생성 (LLM 호출 없음, 코드만)
  - 출력: {homepage_text, attachments[], logo_path | null, media_assets[]}
    ↓
[B2] 자산 추출 (LLM, Sonnet 4.6, tool_use)
  - 입력: [B1] 텍스트 합본 (LLM 프롬프트 총 길이 < 60k tokens 보장)
  - **user_input 의 기채움 필드는 프롬프트에 "이미 확정됨 — 생성 금지" 마커로 전달**
    → LLM 은 빈 필드만 생성. 호출당 토큰 절약 + 품질 안정
    → 모든 필드가 이미 채워져 있으면 [B2] 자체를 skip (LLM 호출 없음)
  - 사용자 직접 입력 필드는 추출 결과 *덮어쓰지 않음* (§4-5 머지 규칙)
  - 빈 필드만 LLM 결과로 채움 (hybrid)
    ↓
[B3] 자산 정규화 + 저장
  - 디자인 토큰: 컬러 hex 변환 (#RGB → #RRGGBB), 폰트명 정규화
  - Supabase brand_profiles + brand_assets 저장
  - 로컬 미러: brands/{brand_slug}/{version}/assets.json + raw_sources/
```

### 4-3. 추출 결과 스키마

```python
class BrandProfile(BaseModel):
    id: UUID
    name: str
    slug: str
    homepage_url: HttpUrl
    created_at: datetime
    asset_version: int               # 자산 갱신마다 증가
    locale: str = "ko-KR"

class BrandAssets(BaseModel):
    """버전 관리 대상 — 텍스트 기반 자산만 포함. media_library 는 제외."""
    brand_id: UUID
    version: int

    design_guide: DesignGuide
    business_context: BusinessContext
    brand_guideline: BrandGuideline

    logo_url: str | None             # Supabase Storage 또는 로컬 경로
    raw_source_paths: list[str]      # 원본 보관

# ⚠️ media_library 는 brand 레벨로 관리 (버전 무관). BrandProfile 에서 별도 조회.
# 이유: 실사 사진은 자산 갱신(색·차별점 수정)과 독립적으로 추가·교체되며,
# 버전별 복제 시 디스크·DB 낭비가 크다. asset_version 증가와 별개로 운영.

class MediaAssetType(str, Enum):
    DOCTOR = "doctor"                # 원장·전문의 프로필 사진
    FACILITY = "facility"            # 시술실·대기실·병원 외관
    EQUIPMENT = "equipment"          # 장비·기기
    CERT = "cert"                    # 인증서·자격증 (선택)
    OTHER = "other"

class MediaAsset(BaseModel):
    id: UUID
    brand_id: UUID                   # brand 레벨 소속 (버전 무관)
    type: MediaAssetType
    file_path: str                   # brands/{slug}/media/{id}.jpg
    title: str | None                # "원장 홍길동", "다이어트 시술실 1"
    description: str | None          # 블록 렌더 시 alt 텍스트로 사용
    orientation: Literal["portrait", "landscape", "square"]
    width: int
    height: int
    tags: list[str] = []             # "principal", "specialist_A" 등 선택 힌트
    created_at: datetime             # 등록 시점 추적용

class DesignGuide(BaseModel):
    primary_color: str               # hex
    secondary_color: str | None
    accent_color: str | None
    neutral_palette: list[str]       # 회색 계열 등
    font_family_heading: str         # "Pretendard", "Noto Sans KR" 등
    font_family_body: str
    border_radius: int               # 디자인 토큰 (px)
    style_tokens: list[str]          # ["clean", "warm", "trustworthy"] — 이미지 슬롯에 전달
    do_not_use_colors: list[str] = [] # 금지 컬러

class BusinessContext(BaseModel):
    industry: str                    # "한의원", "피부과", "치과" 등
    specialty: list[str]             # ["다이어트", "체형 교정"]
    target_audience: list[str]       # ["30대 직장인 여성", ...]
    location: str | None             # "서울 강남구"
    differentiators: list[str]       # 사용자가 직접 정의한 차별점 3~5개
    proof_points: list[str]          # 인증·경력·장비 등
    tone_keywords: list[str]         # ["전문적", "친근함", "신뢰"]

class BrandGuideline(BaseModel):
    voice: str                       # "전문적이지만 친근한 톤"
    must_use_phrases: list[str]      # 브랜드가 항상 쓰는 표현
    forbidden_phrases: list[str]     # 브랜드가 절대 안 쓰는 표현
    cta_examples: list[str]          # "상담 예약", "방문 안내" 등
    legal_notes: str | None          # 의료법 관련 자체 가이드라인
```

### 4-4. Supabase 테이블 (§9 참조)

- `brand_profiles` — 브랜드 메타
- `brand_assets` — JSON 자산 (version 별 row)

### 4-5. 사용자 직접 입력 우선 규칙 (Hybrid)

```python
def merge_assets(user_input: dict, llm_extracted: dict) -> BrandAssets:
    # 1. user_input 의 None/빈 문자열/빈 리스트가 아닌 필드 → 그대로 사용
    # 2. 빈 필드만 llm_extracted 로 채움
    # 3. 머지 결과를 BrandAssets 로 검증
    ...
```

빈 값 판정: `None`, `""`, `[]`, `{}` → 빈 것으로 간주.

### 4-6. `register_brand` 는 Upsert (신규 생성 + 업데이트 통합)

브랜드 정보(홈페이지·첨부 문서·사용자 입력·media 파일)는 운영 중 자주 바뀐다. 따라서 `register_brand` 는 단순 생성이 아니라 **idempotent upsert** 로 동작한다. 별도의 `update_brand_assets` use case 를 두지 않는다.

#### 동작 규칙

```python
def register_brand(
    name: str,
    homepage_url: str,
    user_input: dict | None = None,
    extra_sources: list[Path] | None = None,
    logo_file: Path | None = None,
    media_files: list[tuple[Path, MediaAssetType, ...]] | None = None,
    reporter: ProgressReporter | None = None,
) -> BrandProfile:
    """
    1. slug 정규화 (§4-1-1) → 기존 brand 조회
    2. 없으면: 신규 brand_profiles row 생성 (asset_version=1)
    3. 있으면: 기존 brand_id 재사용, 아래 로직 수행
       - 소스 재수집 ([B1]) → LLM 재추출 ([B2]) → 머지 ([B3])
       - 직전 version 과 diff 비교:
         - 변경 없음 → version 증가 안 함, 기존 레코드 유지
         - 변경 있음 → 새 brand_assets row 생성 (version += 1)
                      + brand_profiles.current_asset_version 갱신
       - media_files 인자가 있으면 brand_media_assets 에 append (기존 삭제 X)
    4. 반환: 최신 BrandProfile
    """
```

#### 매칭 키 결정

- **기본**: `slug` (이름 기반 정규화 결과)
- **충돌 케이스**: 같은 slug 가 다른 brand 를 가리키면 `homepage_url` 을 2차 키로 비교
- 두 키 모두 다른데 사용자가 같은 이름 쓰려 하면 `BrandSlugConflictError` — slug 뒤에 `-2` 붙이거나 사용자에게 네이밍 변경 요청

#### media 파일 처리

- **추가만 지원**. 기존 media 삭제는 별도 use case `remove_media_asset(brand_id, media_id)`
- 같은 파일을 중복 등록하려 하면 (sha256 해시 비교) skip
- media 는 asset_version 과 무관하게 brand 레벨 소속

#### 주의

- `diff` 비교는 design_guide/business_context/brand_guideline 3 섹션만. `raw_source_paths` 는 제외 (파일 경로만 바뀌어도 version 증가하면 부담)
- 변경 판정은 Pydantic `model_dump()` 후 dict 비교. 필드 정렬·정규화 필수
- 과거 version 은 자동 정리하지 않음. 운영자가 `cleanup_brand_versions(brand_id, keep=5)` 수동 호출

#### `update_brand_assets` 제거 사유

- 사용자 입력(이름·홈페이지) 이 있으면 이미 신규 등록과 의미가 동일
- 두 함수를 분리하면 호출자 혼란, 시그니처 중복
- upsert 단일 진입점이 Phase 2 Web UI 에서도 더 명확

---

## 5. 카드 생성 파이프라인

### 5-1. 단계 개요

```
입력: keyword + brand_id + variant_count (N)
    ↓
[B4] 카드 기획 (LLM, Opus 4.6) — **단일 호출로 N 변형 반환**
  - 입력:
    - 키워드
    - 브랜드 자산 (design_guide/business_context/brand_guideline)
    - (선택) SEO 패턴 카드 — None 이면 프롬프트 해당 섹션 생략
    - 템플릿 카탈로그 요약 (template_id + slot_sequence + tone_match)
    - **available_media**: {doctor: N, facility: N, equipment: N}
      → LLM 이 media 가 없는 블록을 처음부터 제외하도록 사전 정보 제공
  - 단일 호출 이유: 변형 간 diversity 강제 + N회 호출 대비 토큰·지연 절감
  - 출력: CardPlansResult.variants = N개
    ↓
[B4-v] validate_card_plan — 코드 검증 (LLM 불필요, 빠른 검사)
  - 필수 5개 블록(hero/pain_hook/solution_intro/differentiator/closer) 모두 포함?
  - 각 block.id 가 BlockId Enum 에 존재?
  - 각 block 이 선택된 template_id 의 slot_sequence 에 정의된 블록인가?
  - media_library 참조 블록의 media_type 자산이 실재?
  - 실패 시: [B4] 1회 재호출 (구체적 실패 원인 피드백 주입)
  - 재실패 시: 해당 variant 를 failed_variants 로 기록, 나머지 variant 는 계속
    ↓
[B5] 이미지 슬롯 생성 (Gemini Nano Banana)
  - LLM 이 image_slot 에 표시한 슬롯만 생성
  - 슬롯 단위 캐시 (동일 prompt_hint+style_tokens 재사용)
    ↓
[B6] HTML 합성 (Jinja2 템플릿)
  - 템플릿 ID 별로 다른 HTML/CSS
  - 브랜드 디자인 토큰 → CSS 변수 주입
    ↓
[B7] 컴플라이언스 검증 (BRAND_LENIENT, Sonnet 4.6)
  - 텍스트 + 이미지 메타에 적용
  - 위반 시 fixer (구절 치환 우선)
    ↓
[B8] Playwright 풀페이지 스크린샷 → PNG
  - chromium headless, viewport 1080
  - 폰트 로드 완료 대기
  - 이미지 슬롯 로드 완료 대기
    ↓
[B9] 패키지 정리 + cards-manifest.json
```

### 5-2. [B4] 카드 기획 프롬프트 구조

```
[시스템]
너는 병원 마케팅 상세페이지 기획자다.
브랜드 자산과 키워드를 받아, N개의 카드 변형을 기획한다.
각 변형은 동일한 브랜드 메시지를 다른 후킹 앵글 또는 다른 레이아웃으로 표현한다.
의료법 위반 표현은 사용하지 않는다 (BRAND_LENIENT 카테고리 주입).

[브랜드 자산]
{brand_assets.business_context}
{brand_assets.brand_guideline}
디자인 토큰은 카피에 영향을 주지 않으나, 톤 키워드 {tone_keywords} 를 반영하라.

[키워드]
{keyword}

[(선택) SEO 패턴 카드 참조]
※ pattern_card == None 이면 이 섹션 자체를 프롬프트에서 완전 생략 (prompt_builder 가 조건부 삽입).
타겟 독자 고민: {pattern_card.target_reader.concerns}
공통 소구 포인트: {pattern_card.aggregated_appeal_points.common}
※ 이 정보는 참고만. 브랜드 자산이 우선.

[사용 가능한 media 자산]
※ 실사 사진이 있는 타입만 카드에 포함하라. 없는 타입의 블록은 시퀀스에서 제외.
- doctor: {available_media.doctor} 장
- facility: {available_media.facility} 장
- equipment: {available_media.equipment} 장
예: doctor=0 이면 doctor_team 블록을 선택하지 말 것.

[변형 N개 기획 지시]
- 변형마다 다른 후킹 앵글 (예: 페인 중심 / 솔루션 중심 / 사회적 증거 중심)
- 각 변형의 블록 시퀀스 (필수 5개 + 선택 0~8개)
- 각 블록의 카피 (헤드라인, 본문, 콜아웃)
- 각 블록에서 이미지 슬롯이 필요한지 판단 (텍스트로 충분하면 image_slot=null)
- 이미지 슬롯이 필요하면 prompt_hint 와 aspect_ratio 결정

[BRAND_LENIENT 의료법 카테고리]
{compliance_rules.brand_lenient.pre_generation_injection}

[출력 — tool_use]
record_card_plans 로 N개 변형 기록
```

### 5-3. 구조화 출력 (tool_use)

```python
class CardPlan(BaseModel):
    variant_idx: int
    template_id: str                 # LLM 이 템플릿 풀에서 선택
    angle: str                       # "페인 중심" / "솔루션 중심" 등
    blocks: list[Block]
    estimated_height_px: int         # 휴리스틱 계산 (블록 권장 높이 합)
    recommended_position: Literal["intro", "mid", "ending"]

class CardPlansResult(BaseModel):
    keyword: str
    brand_id: UUID
    variants: list[CardPlan]
```

LLM 이 템플릿을 선택하는 방식: `[B4]` 입력에 사용 가능한 템플릿 카탈로그(ID + 슬롯 정의 요약)를 함께 전달. LLM 은 ID만 반환.

### 5-4. [B5] 이미지 슬롯 생성

- **트리거**: `block.image_slot is not None` AND `image_slot.source_kind == "ai"` 인 슬롯만
- **두 가지 source_kind**:
  - `ai`: Nano Banana 호출 (hero, differentiator 아이콘, case_result 다이어그램 등 일러스트성)
  - `media_library`: 브랜드 자산에서 참조. 해당 type 의 MediaAsset 을 선택 (doctor_team, equipment, facility). **API 호출 없음**
- **media_library 참조 규칙**:
  - [B4] 카드 기획이 해당 블록을 선택할 때, 브랜드 media_library 에 필요 type 자산이 존재하는지 먼저 확인
  - 없으면 해당 블록 자체를 시퀀스에서 제외 (skip)
  - 복수 후보 있을 시 LLM 이 `tags` 힌트로 선택 (예: `["principal"]` → 원장 우선)
- **모델**: Gemini Nano Banana (gemini-2.5-flash-image) — `source_kind=ai` 일 때만
- **프롬프트 조립**: `prompt_hint + style_tokens(브랜드) + 의료 안전 가이드`
- **캐시 2계층**:
  - **글로벌 캐시**: `brands/{brand_slug}/cache/img-{cache_key}.png` — 동일 브랜드에서 키워드 바뀌어도 재사용 (style_tokens, prompt_hint 동일 시)
  - **작업 산출물 복사본**: `output/{slug}/{ts}/cards/assets/img-{cache_key[:12]}.png` — 패키지 재현성·감사용
  - 우선순위: 작업 시작 시 글로벌 캐시 조회 → 없으면 API 호출 → 글로벌 캐시에 저장 → 작업 디렉토리에 복사
- **캐시 키**: `sha256(prompt_hint + sorted(style_tokens) + aspect_ratio + brand_id + gemini_model_version)` — 모델 버전 bump 시 자동 무효화
- **실패 대응**: `image_slot.fallback_text` 가 있으면 텍스트 블록으로 자동 대체. 없으면 해당 슬롯만 비움 (블록 자체는 유지)

### 5-5. [B6] HTML 합성

- **사전 검증 (render 전)**: `template.validates(card_plan)` 호출
  - 모든 `block.id` 가 템플릿의 `slot_sequence` 에 존재하는지
  - 블록 순서가 `slot_sequence` 순서와 호환되는지 (부분집합 OK, 순서 뒤섞기 X)
  - 템플릿이 요구하는 필수 슬롯(`meta.json.required_slots`)이 모두 채워졌는지
  - 실패 시: 누락·불일치 블록이 필수가 아니면 graceful skip + 경고 로그 기록. 필수 블록 불일치면 variant 실패 분류
- **템플릿 엔진**: Jinja2
- **템플릿 위치**: `domain/brand_card/templates/{template_id}/`
  - `card.html.j2` — 카드 전체 골격
  - `blocks/{block_id}.html.j2` — 블록 단위 부분 템플릿
  - `style.css` — 템플릿 전용 스타일
  - `meta.json` — 슬롯 정의 (어느 블록을 어느 순서로 받는지)
- **CSS 변수 주입**:
  ```css
  :root {
    --primary: {{ brand.design_guide.primary_color }};
    --secondary: {{ brand.design_guide.secondary_color }};
    --font-heading: {{ brand.design_guide.font_family_heading }};
    --font-body: {{ brand.design_guide.font_family_body }};
    --radius: {{ brand.design_guide.border_radius }}px;
  }
  ```
- **폰트 로드**: HTML 헤더에 `@font-face` 로 `assets/fonts/Pretendard.woff2` 등 임베딩

### 5-6. [B7] 컴플라이언스 검증 (BRAND_LENIENT)

§7 참조. 본문은 §7 만, 여기서는 호출 위치만 언급:
- HTML 합성 직후, PNG 렌더링 전
- 위반 시 fixer 가 블록 카피만 교체 → HTML 재합성 → 재검증
- 최대 2회 재시도. 초과 시 해당 변형은 실패 처리(다른 변형은 진행)

### 5-7. [B8] Playwright 렌더링

- **드라이버**: `playwright` Python 패키지 (Chromium headless)
- **뷰포트**: 1080 width × 100 height (스크린샷은 full_page=True 이므로 height 무관)
- **렌더 절차**:
  ```python
  page.set_viewport_size({"width": 1080, "height": 100})
  page.goto(f"file://{html_path}")
  page.wait_for_load_state("networkidle")
  # 폰트 로드 보장
  page.evaluate("document.fonts.ready")
  page.screenshot(path=png_path, full_page=True, omit_background=False)
  ```
- **PNG 후처리**:
  - 9000 px 초과 시 §2-5 자동 분할 알고리즘 실행:
    1. HTML DOM 에서 블록 경계 y좌표 목록 조회 (`page.evaluate`)
    2. 블록 사이 여백 중점을 후보로, 4000~8000 범위 조각 되도록 그리디 선택
    3. Pillow 로 크롭하여 `-01a`, `-01b`, ... 저장
    4. 원본 풀 PNG 는 폐기 (또는 디버그 모드에서만 보존)
  - PNG `tEXt` 메타 삽입 (Pillow): 브랜드 ID, 키워드, 템플릿 ID, variant 번호, 생성 시각
  - hard max 18000 px 초과 시 — 변형 실패로 분류하고 cards-manifest 의 failed_variants 에 기록

### 5-9. [B9] cards-manifest.json

```json
{
  "keyword": "강남 다이어트 한의원",
  "brand_id": "...",
  "generated_at": "2026-04-16T...",
  "variants": [
    {
      "file": "card-clinic-classic-01.png",
      "template_id": "clinic-classic",
      "angle": "페인 중심",
      "height_px": 4820,
      "block_count": 9,
      "recommended_position": "intro",
      "compliance_passed": true,
      "compliance_iterations": 1
    }
  ],
  "failed_variants": []
}
```

저장: `output/{slug}/{ts}/cards/cards-manifest.json`

### 5-10. 에러 핸들링 정책 통합표

단계별 실패 조건과 대응을 한곳에서 정의한다. 코드 구현 시 이 표가 contract.

| 단계 | 실패 조건 | 재시도 | 실패 시 처리 | 전파 |
|---|---|---|---|---|
| [B1] 소스 수집 | 홈페이지 fetch 실패 | 2회 (BrightData 기본) | `homepage_text=""` 로 진행, LLM 이 첨부 문서만으로 자산 추출 시도 | 없음 |
| [B1] 소스 수집 | 첨부 파싱 실패 (docx/pdf) | 없음 | 해당 파일 skip + 경고 | 없음 |
| [B1] media 수집 | 개별 파일 읽기 실패 | 없음 | 해당 파일 skip + 경고 | 없음 |
| [B2] 자산 추출 | LLM tool_use 응답 실패 | 1회 재호출 | 필수 필드가 없으면 `register_brand` 실패 전파. 비필수 필드면 빈 값 허용 | register_brand 전체 실패 가능 |
| [B3] 저장 | Supabase INSERT 실패 | 1회 재시도 (tenacity) | 재실패 시 예외 raise → `register_brand` 실패 | 전파 |
| [B4] 카드 기획 | tool_use 응답 실패 | 1회 재호출 | 전체 variant 실패 → `BrandCardResult.status = "failed"` | partial 가능 |
| [B4-v] 검증 | 필수 블록 누락 등 | [B4] 1회 재호출 | 해당 variant 만 failed_variants | variant 단위 |
| [B5] 이미지 생성 | Gemini API 에러 | 1회 재호출 | `image_slot.fallback_text` 사용. 없으면 슬롯 비움 (블록 유지) | 슬롯 단위 |
| [B5] 이미지 생성 | safety filter 차단 | 재시도 안 함 | fallback_text 사용. 없으면 블록 자체 실패 처리 | 블록 단위 |
| [B6] HTML 검증 | `template.validates` 실패 (필수 블록 불일치) | 없음 | 해당 variant 만 실패 | variant 단위 |
| [B6] HTML 합성 | Jinja2 렌더 에러 | 없음 | 해당 variant 만 실패 + 스택 트레이스 로그 | variant 단위 |
| [B7] 컴플라이언스 | 위반 발견 | fixer 최대 2회 | 3회째도 위반이면 해당 variant 실패 | variant 단위 |
| [B8] Playwright | 브라우저 기동 실패 | 1회 재시도 | 전체 카드 생성 실패 (런타임 문제) | 전체 실패 |
| [B8] 렌더 | hard max 18000px 초과 | 없음 | 해당 variant 실패 (템플릿 설계 문제 경고) | variant 단위 |
| [B8] 분할 | 블록 하나가 9000px 초과 | 없음 | 해당 variant 실패 | variant 단위 |
| [B9] manifest | 파일 쓰기 실패 | 1회 재시도 | 재실패 시 예외 raise | 전체 실패 |

**공통 원칙**:
- "전체 실패" = `BrandCardResult.status = "failed"`, `variants = []`
- "variant 단위" = 나머지 variant 는 계속 진행, `failed_variants[]` 에 이유 기록
- "슬롯 단위" = variant 는 살아남음, 해당 image_slot 만 비움

**재시도 시 LLM 호출 피드백**:
재호출 시 프롬프트에 `previous_error` 섹션을 추가해 LLM 이 왜 실패했는지 알 수 있게 한다. 맹목 재시도 금지.

---

## 6. 템플릿 시스템

### 6-1. 템플릿 정의

템플릿 = (HTML 골격 + CSS + 슬롯 메타). 디자인 다양성을 코드로 관리한다.

```
domain/brand_card/templates/
├─ clinic-classic/      # 정통 의료, 차분한 컬러, 좌우 정렬
├─ clinic-bold/         # 강렬한 색, 큰 헤드라인, 비대칭
├─ clinic-minimal/      # 여백 위주, 흑백·단일 액센트
├─ clinic-warm/         # 따뜻한 색, 부드러운 라운드, 가족 친화
├─ clinic-editorial/    # 매거진 스타일, 텍스트 위주, 대형 사진
└─ ...
```

각 폴더의 `meta.json`:

```json
{
  "id": "clinic-classic",
  "name": "Clinic Classic",
  "description": "정통 의료, 신뢰감, 좌우 정렬 위주",
  "slot_sequence": [
    {"block_id": "hero", "layout_variants": ["centered", "left_text"]},
    {"block_id": "pain_hook", "layout_variants": ["bullet_list", "card_grid"]},
    {"block_id": "solution_intro", "layout_variants": ["left_text"]},
    {"block_id": "differentiator", "layout_variants": ["icon_grid_3", "icon_grid_4"]},
    {"block_id": "process", "layout_variants": ["horizontal_steps", "vertical_steps"]},
    {"block_id": "closer", "layout_variants": ["centered_with_logo", "text_only"]}
  ],
  "min_blocks": 5,
  "max_blocks": 10,
  "tone_match": ["전문적", "신뢰", "차분"]
}
```

### 6-2. SOV 다양성 — 동일 카피, 다른 레이아웃

핵심 메커니즘:
1. LLM 이 블록 카피를 결정 (`Block.headline`, `Block.body` 등)
2. LLM 이 템플릿 ID를 변형마다 다르게 선택 (또는 동일 템플릿의 다른 `layout_variant` 선택)
3. 같은 카피라도 `clinic-classic` 의 `centered` vs `clinic-bold` 의 `left_text` 는 시각적으로 완전 다름
4. 결과: 한 키워드 N장의 카드는 메시지 일관성 + 시각 다양성 모두 확보

### 6-3. MVP 템플릿 갯수

- 초기 5종: `clinic-classic`, `clinic-bold`, `clinic-minimal`, `clinic-warm`, `clinic-editorial`
- 각 템플릿은 블록당 평균 2개 layout_variant → 실효 다양성 약 5×2^N
- 추가 템플릿은 별도 PR 로 폴더만 추가하면 자동 등록 (`templates/` 글로빙)

### 6-4. 템플릿 등록 자동화

`domain/brand_card/template_registry.py` 가 런타임에 `templates/` 폴더를 글로빙해 모든 `meta.json` 로드. 등록 코드 별도 작성 불필요.

---

## 7. 컴플라이언스 — BRAND_LENIENT 프로필

### 7-1. 단일 출처 원칙

`domain/compliance/rules.py` 에 두 프로필을 모두 정의. SEO 트랙은 `SEO_STRICT`, 브랜드 카드는 `BRAND_LENIENT` 사용.

```python
class CompliancePolicy(str, Enum):
    SEO_STRICT = "seo_strict"
    BRAND_LENIENT = "brand_lenient"

# rules.py
RULES: dict[CompliancePolicy, list[Rule]] = {
    CompliancePolicy.SEO_STRICT: [...8개 카테고리 전부...],
    CompliancePolicy.BRAND_LENIENT: [...법적 risk only...],
}
```

### 7-2. BRAND_LENIENT 차단 카테고리 초안 (의료광고법 기반)

법적 risk가 명확히 큰 케이스만. 마케팅 후킹용 일반 표현(`효과적`, `차별화된`, `프리미엄`, `전문적`)은 허용.

| 카테고리 | 차단 사유 | 예시 차단 표현 | 대체 방향 |
|---|---|---|---|
| `absolute_guarantee` | 의료법 시행령 §23 — 효능·효과 보장 금지 | `100% 완치`, `반드시 좋아집니다`, `보장합니다`, `절대적인` | "개선이 기대됩니다", "도움이 될 수 있습니다" |
| `unique_superlative` | 의료법 §56 — 비교·우위 표현 금지 | `최고`, `유일`, `1등`, `최상`, `대한민국 최초` (입증 불가) | "차별화된", "전문적인" |
| `direct_comparison` | §56 — 타 의료기관 직접 비교 금지 | `OO병원보다`, `타 병원과 달리`, `다른 곳은 못 하는` | 비교 없이 자신의 강점만 |
| `before_after_explicit` | §56 — Before/After 직접 비교 사진·표현 제한 | `시술 전후 사진`, `Before/After`, `완전히 달라진` | "변화", "개선", "관리 후 모습" |
| `cure_treatment_promise` | §56 — 치료 효과 확정 표현 금지 | `완치`, `재발 없음 보장`, `평생 효과` | "장기적 관리", "지속적 효과 기대" |
| `patient_testimonial_specific` | §56 — 특정 효과 보장형 후기 인용 제한 | `"3kg 빠졌어요" - 환자 후기` 같은 수치+효과 직접 인용 | 일반화된 만족 표현 |
| `unverified_award` | §56 — 검증 안 된 상·인증 표시 금지 | `세계 1위`, `Best Doctor 선정` (출처 불명) | 검증 가능한 자격만 |

총 **7개 카테고리**. (`SEO_STRICT` 는 8개로 시술명 표시 규정까지 포함하지만 BRAND_LENIENT 는 7개로 축소)

> ⚠️ 위 목록은 **초안**이다. 사용자 제공 SEO_STRICT 8개 카테고리가 확정된 후 `rules.py` 작성 시 함께 검토·확정한다.

### 7-3. 검증 흐름

```
HTML 합성 결과의 모든 텍스트 추출 (headline, body, callouts, alt 텍스트)
    ↓
[7-1] 규칙 기반 1차 (정규식, RULES[BRAND_LENIENT])
    ↓
[7-2] LLM 검증 (Sonnet, tool_use) — 정규식이 못 잡는 암시적 표현
    ↓
위반 → fixer (구절 치환 우선) → 해당 블록 카피 교체 → HTML 재합성 → 재검증
    ↓
2회 후 실패 → 해당 변형 실패. 다른 변형은 계속
```

### 7-4. fixer 차이점 (SEO 트랙과 비교)

- 도입부 톤 락(M2) 개념 없음 — 카드는 hero 블록도 재생성 가능
- 블록 단위 재생성 가능 (LLM 호출)
- **블록 재생성 시 `image_slot` 은 재사용**. 카피만 교체하여 이미지 생성 비용·시간을 절약. image_slot 자체를 교체해야 할 경우(예: 이미지 alt 텍스트가 위반) 에만 Nano Banana 재호출
- 이미지 슬롯의 텍스트 알트는 검증 대상이지만 이미지 자체는 미검증 (추후 단계 OCR)

---

## 8. 도메인 구조

### 8-1. 새 도메인 폴더

```
domain/brand_card/
├── CLAUDE.md                  ← 도메인 규칙
├── model.py                   ← BrandProfile, BrandAssets, Block, CardPlan, CardResult, ImageSlot
├── source_loader.py           ← [B1] HTML/txt/docx/pdf 파싱
├── asset_extractor.py         ← [B2] LLM 자산 추출 (Sonnet)
├── asset_merger.py            ← user_input + llm_extracted 머지
├── card_planner.py            ← [B4] LLM 카드 기획 (Opus)
├── prompt_builder.py          ← 모든 LLM 프롬프트 빌드 단일 진입점
├── image_generator.py         ← [B5] Nano Banana 호출 + 캐시
├── template_registry.py       ← templates/ 글로빙 + meta 로드
├── html_renderer.py           ← [B6] Jinja2 합성
├── playwright_renderer.py     ← [B8] PNG 렌더
├── repository.py              ← Supabase brand_profiles / brand_assets / brand_cards
└── templates/
    ├── clinic-classic/
    │   ├── meta.json
    │   ├── card.html.j2
    │   ├── style.css
    │   └── blocks/{block_id}.html.j2
    ├── clinic-bold/
    └── ...
```

### 8-2. application/ 추가 use case

```python
# application/orchestrator.py 에 추가
def register_brand(
    name: str,
    homepage_url: str,
    user_input: dict | None = None,
    extra_sources: list[Path] | None = None,
    logo_file: Path | None = None,
    media_files: list[tuple[Path, MediaAssetType, dict]] | None = None,
    reporter: ProgressReporter | None = None,
) -> BrandProfile:
    """
    Idempotent upsert. 신규 생성 + 기존 업데이트 겸용.
    상세: §4-6.
    """

# media 단건 관리 (부가 use case)
def remove_media_asset(brand_id: UUID, media_id: UUID) -> None: ...

def run_brand_card_only(
    keyword: str,
    brand_id: UUID,
    variant_count: int = 3,
    reporter: ProgressReporter | None = None,
) -> BrandCardResult: ...

def run_full_package(
    keyword: str,
    brand_id: UUID,
    card_variant_count: int = 3,
    reporter: ProgressReporter | None = None,
) -> PackageResult: ...
```

- `update_brand_assets` 는 **제거**. `register_brand` 가 upsert 이므로 중복.
- `run_full_package` 는 SEO 트랙(기존 `run_pipeline`)과 브랜드 카드 트랙을 병렬 실행 후 합류한다. §13 참조.

### 8-3. application/stage_runner.py 확장

```python
def run_stage_brand_source_loading(brand_input) -> RawSources: ...
def run_stage_brand_asset_extraction(raw_sources, user_input) -> BrandAssets: ...
def run_stage_card_planning(keyword, brand_assets, pattern_card?) -> list[CardPlan]: ...
def run_stage_image_slot_generation(card_plans) -> list[CardPlan]: ...  # image_slot 채움
def run_stage_card_html_render(card_plans, brand_assets) -> list[Path]: ...
def run_stage_card_compliance(html_paths, blocks) -> list[ComplianceResult]: ...
def run_stage_card_screenshot(html_paths) -> list[Path]: ...
```

### 8-4. 레이어 import 규칙 (기존과 동일)

- `application/` → `domain/brand_card/` ✅
- `domain/brand_card/` → `application/` ❌
- `domain/brand_card/` → `domain/crawler/` 등 다른 도메인 ❌ (격리)
- `domain/brand_card/` 는 `domain/compliance/rules.py` 만 예외적으로 import 허용 (단일 출처 원칙)

### 8-5. 가디언 에이전트 (선택)

- `.claude/agents/brand-card-guardian.md` (선택, 추후 작성) — `domain/brand_card/` 변경 시 템플릿 무결성·BRAND_LENIENT 사용 검사

---

## 9. Supabase 스키마

기존 `pattern_cards`, `generated_contents` 와 격리. 외래키 관계 없음.

```sql
-- 브랜드 프로필
create table brand_profiles (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  homepage_url text not null,
  locale text default 'ko-KR',
  current_asset_version int default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index idx_brand_profiles_slug on brand_profiles (slug);

-- 브랜드 자산 (버전별)
create table brand_assets (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brand_profiles(id) on delete cascade,
  version int not null,
  design_guide jsonb not null,
  business_context jsonb not null,
  brand_guideline jsonb not null,
  logo_url text,
  raw_source_paths jsonb,            -- 로컬 파일 경로 리스트
  created_at timestamptz default now(),
  unique (brand_id, version)
);

-- 브랜드 미디어 라이브러리 (실사 사진) — brand 레벨, asset_version 무관
create table brand_media_assets (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brand_profiles(id) on delete cascade,
  type text not null,                -- doctor | facility | equipment | cert | other
  file_path text not null,
  file_sha256 text not null,         -- 중복 업로드 검출용
  title text,
  description text,
  orientation text,                  -- portrait | landscape | square
  width int,
  height int,
  tags jsonb default '[]'::jsonb,
  created_at timestamptz default now(),
  unique (brand_id, file_sha256)     -- 같은 브랜드에 동일 파일 중복 방지
);
create index idx_brand_media_assets_brand on brand_media_assets (brand_id, type);

-- 생성된 브랜드 카드
create table brand_cards (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brand_profiles(id) on delete cascade,
  brand_asset_version int not null,
  keyword text not null,
  variant_idx int not null,
  template_id text not null,
  angle text,
  height_px int,
  block_count int,
  png_path text not null,             -- 로컬 파일 경로
  png_meta jsonb,                     -- 텍스트 본문, 블록 시퀀스 등
  compliance_passed boolean,
  compliance_iterations int,
  recommended_position text,
  created_at timestamptz default now()
);
create index idx_brand_cards_brand on brand_cards (brand_id, created_at desc);
create index idx_brand_cards_keyword on brand_cards (keyword, created_at desc);
```

---

## 10. 디렉토리 구조

### 10-1. 전체 (브랜드 관련 추가)

```
contents-creator/
├── SPEC.md                    ← SEO 트랙 (기존)
├── SPEC-BRAND-CARD.md         ← 본 문서
├── domain/
│   ├── crawler/               ← (기존)
│   ├── analysis/              ← (기존)
│   ├── generation/            ← (기존)
│   ├── compliance/            ← (기존, BRAND_LENIENT 추가)
│   ├── composer/              ← (기존)
│   └── brand_card/            ← (신규)
├── application/
│   ├── orchestrator.py        ← register_brand, run_brand_card_only, run_full_package 추가
│   └── stage_runner.py        ← 브랜드 카드 단계 헬퍼 추가
├── brands/                    ← 브랜드 자산 로컬 미러
│   └── {brand_slug}/
│       ├── cache/             ← 글로벌 이미지 캐시 (§5-4)
│       │   └── img-{cache_key}.png
│       ├── media/             ← 실사 사진 라이브러리 (brand 레벨, version 무관)
│       │   ├── doctor-{uuid}.jpg
│       │   ├── facility-{uuid}.jpg
│       │   └── equipment-{uuid}.jpg
│       └── versions/
│           └── {version}/     ← 텍스트 자산만 버전 관리
│               ├── assets.json
│               ├── logo.png   ← 버전별 로고 교체 가능
│               └── raw_sources/
│                   ├── homepage.html
│                   ├── doc1.docx
│                   └── brochure.pdf
├── output/
│   └── {slug}/{ts}/
│       ├── analysis/          ← SEO 트랙 (기존)
│       ├── content/           ← SEO 트랙 (기존)
│       └── cards/             ← 브랜드 카드 트랙 (신규)
│           ├── plans.json     ← [B4] 결과
│           ├── html/          ← [B6] 합성 HTML
│           │   ├── card-clinic-classic-01.html
│           │   └── ...
│           ├── assets/        ← [B5] 이미지 슬롯 캐시
│           │   └── img-{cache_key}.png
│           ├── card-clinic-classic-01.png
│           ├── card-clinic-bold-02.png
│           └── cards-manifest.json
└── assets/
    └── fonts/
        ├── Pretendard.woff2
        └── ...
```

---

## 11. 기술 스택 (브랜드 카드 트랙 추가분)

| 영역 | 기술 | 비고 |
|---|---|---|
| HTML 렌더링 | Playwright (Python) + Chromium headless | 한국어 폰트·풀페이지 스크린샷 |
| HTML 템플릿 | Jinja2 | |
| docx 파싱 | python-docx | |
| pdf 파싱 | pypdf (단순 텍스트) → 한계 시 pdfplumber 검토 | |
| 이미지 생성 | Google Generative AI (Gemini Nano Banana, `gemini-2.5-flash-image`) | Gemini API 키 사용 |
| LLM 호출 | Anthropic Claude (Opus 4.6 / Sonnet 4.6) | tool_use 강제 |
| 이미지 후처리 | Pillow | PNG 메타·크기 검증 |

### 11-1. LLM 모델 역할 매핑

| 단계 | 모델 | 역할 |
|---|---|---|
| [B2] 자산 추출 | Sonnet 4.6 | 브랜드 메시지·차별점 분류·구조화 |
| [B4] 카드 기획 | Opus 4.6 | 블록 시퀀스·카피·이미지 슬롯 결정 |
| [B5] 이미지 생성 | Gemini Nano Banana | 이미지 슬롯 |
| [B7] 컴플라이언스 | Sonnet 4.6 | 검증 + 수정 제안 |

### 11-2. 새 환경 변수

`config/.env` 추가:
```
GEMINI_API_KEY=...                  # 이미지 생성
PLAYWRIGHT_BROWSERS_PATH=.playwright # 브라우저 설치 위치 (선택)
```

### 11-3. 렌더링 방법 권장 — Playwright 채택 사유

| 후보 | 한국어 폰트 | 풀페이지 PNG | CSS 신규 기능 | 의존성 무게 | 결정 |
|---|---|---|---|---|---|
| Playwright (Chromium) | ✅ | ✅ `full_page=True` | ✅ 최신 | 무거움 (~300MB) | **채택** |
| WeasyPrint | ⚠️ 폰트 임베딩 까다로움 | ❌ PDF 경유 필요 | ⚠️ flexbox 일부 | 가벼움 | 탈락 |
| imgkit / wkhtmltoimage | ⚠️ 한글 폰트 추가 작업 | ✅ | ❌ 구식 CSS | 보통 | 탈락 |
| Headless Chrome 직접 호출 | ✅ | ✅ | ✅ | 무거움 | Playwright 가 추상화 우수 |

**결정**: Playwright. 의존성 무게는 도커라이즈·Phase 2 백엔드에서 흡수 가능.

---

## 12. 검증 기준

| 항목 | 기준 |
|---|---|
| 브랜드 등록 | 사용자 입력 우선 + LLM 보완 머지가 정확히 작동 (수동 검증 3건) |
| 자산 추출 | 디자인 가이드, 비즈니스 컨텍스트, 브랜드 가이드라인 3섹션 모두 채워짐 |
| 카드 기획 | 변형별 다른 후킹 앵글 또는 다른 템플릿. 동일 변형 X |
| 이미지 슬롯 | LLM 이 image_slot 필요성을 합리적으로 판단 (불필요한 슬롯에 이미지 생성 X) |
| HTML 합성 | 모든 디자인 토큰이 CSS 변수로 주입됨 |
| 컴플라이언스 | BRAND_LENIENT 7개 카테고리 감지 + 자동 수정 후 재검증 통과 |
| Playwright 렌더 | 한글 깨짐 0건. PNG 가로 정확히 1080. 세로 권장 범위 내 |
| cards-manifest.json | 모든 변형 메타 정상 기록 + 실패 변형 목록 분리 |
| 트랙 격리 | `domain/brand_card/` 의 import 가 다른 도메인을 참조하지 않음 (compliance/rules.py 제외) |

---

## 13. 트랙 합류 (Joint Section)

### 13-1. 합류 정의

SEO 트랙(`SPEC-SEO-TEXT.md` §2)과 브랜드 카드 트랙(본 문서 §5)은 입력만 공유한다(키워드, brand_id). 코드 경로는 끝까지 분리되며, 최종 파일 시스템 디렉토리에서만 합류한다.

### 13-2. run_full_package 시그니처

```python
def run_full_package(
    keyword: str,
    brand_id: UUID,
    card_variant_count: int = 3,
    reporter: ProgressReporter | None = None,
) -> PackageResult:
    """
    SEO 트랙과 브랜드 카드 트랙을 병렬 실행하여 한 패키지로 묶어 반환.
    """
```

### 13-3. 병렬 실행 모델

```
키워드 K, brand_id B
    ↓
SEO 트랙 [1]→[5] 패턴 카드 생성  ─────┐
                                      │
              ┌───────────────────────┤
              ↓                       ↓
   SEO [6]→[7]→[8]→[9]      Brand Card [B4] (패턴 카드 참조 가능)
              ↓                       ↓
         seo-content.md       [B5]→[B6]→[B7]→[B8]→[B9]
              ↓                       ↓
              └───────── 합류 ────────┘
                         ↓
                  PackageResult
```

- [1]~[5] 는 SEO 트랙 단독 실행 (분석은 한 번만)
- [5] 패턴 카드 완료 시점에 브랜드 카드 트랙이 [B4] 시작 (패턴 카드 참조)
- [6]~[9] 와 [B4]~[B9] 는 **병렬**
- **동시성 모델**: `concurrent.futures.ThreadPoolExecutor(max_workers=2)` 채택
  - Playwright Python sync API 와 Anthropic SDK sync API 조합이 단순
  - asyncio 로 전환 시 LLM SDK 를 async 로 바꿔야 하는데 Phase 1 에선 불필요한 비용
  - 두 트랙은 독립 파일 시스템 경로를 쓰므로 GIL 도 병목 안 됨 (대부분 I/O 대기)
- SEO 트랙 [5] 실패 시 → 브랜드 카드 트랙은 `pattern_card=None` 으로 [B4] 진입 (§13-5 참조)
- SEO 트랙 [1]~[4] 실패 시 → 브랜드 카드 트랙만 단독 실행 (패턴 카드 없이)
- 한쪽 실패가 다른쪽을 종료시키지 않음. PackageResult 에 양쪽 상태 모두 기록

### 13-4. PackageResult 모델

```python
class PackageResult(BaseModel):
    keyword: str
    brand_id: UUID
    output_path: Path                 # output/{slug}/{ts}/
    seo_result: PipelineResult        # 기존 모델
    card_result: BrandCardResult      # 신규 모델
    overall_status: Literal["success", "partial", "failed"]
    # success: 양쪽 다 성공
    # partial: 한쪽만 성공
    # failed:  양쪽 다 실패
```

### 13-5. SEO 트랙이 브랜드 카드 입력으로 제공하는 것

| 항목 | 사용처 |
|---|---|
| `pattern_card.target_reader.concerns` | 카드 [B4] 페인 후킹 카피 톤 참고 |
| `pattern_card.aggregated_appeal_points.common` | 카드 [B4] 솔루션 카피 참고 (브랜드 자산이 우선) |
| `pattern_card.related_keywords` | 카드 [B4] 키워드 변주 |

⚠️ **참조만**. 브랜드 카드는 패턴 카드 없이도 (`run_brand_card_only`) 단독 실행 가능.

### 13-6. 출력 디렉토리 통합

```
output/{slug}/{YYYYMMDD-HHmm}/
├── analysis/                  # SEO
├── content/                   # SEO
├── cards/                     # 브랜드 카드
└── package-manifest.json      # 합류 메타 (양쪽 결과 요약)
```

`package-manifest.json`:
```json
{
  "keyword": "...",
  "brand_id": "...",
  "generated_at": "...",
  "seo": {
    "status": "success",
    "outline_path": "content/outline.json",
    "content_html": "content/seo-content.html",
    "compliance_passed": true
  },
  "cards": {
    "status": "success",
    "manifest_path": "cards/cards-manifest.json",
    "variant_count": 3,
    "successful": 3,
    "failed": 0
  },
  "overall_status": "success"
}
```

---

## 14. CLI 진입점 (브랜드 카드 트랙 추가)

```bash
# 브랜드 등록 또는 업데이트 (upsert)
python scripts/register_brand.py \
  --name "강남 OO한의원" \
  --homepage https://example.com \
  --user-input brands/input.json \
  --logo brands/logo.png \
  --extra brands/brochure.pdf brands/about.docx \
  --media brands/doctor1.jpg:doctor brands/room1.jpg:facility

# 같은 이름으로 다시 호출하면 기존 brand 업데이트. asset_version 자동 증가.
# media 파일은 누적 (기존 삭제 안 됨). 삭제는 scripts/remove_media.py --brand-id --media-id

# 브랜드 카드만 생성
python scripts/generate_cards.py \
  --keyword "강남 다이어트 한의원" \
  --brand-id <uuid> \
  --variants 3

# SEO + 카드 통합 패키지
python scripts/run_full_package.py \
  --keyword "강남 다이어트 한의원" \
  --brand-id <uuid> \
  --card-variants 3
```

모든 스크립트는 `application/orchestrator.*` 의 얇은 래퍼.

---

## 15. 보류 사항 / 후속 결정 필요

| 항목 | 상태 | 처리 시점 | 담당 |
|---|---|---|---|
| SEO_STRICT 8개 카테고리 확정 | 사용자 제공 예정 | `rules.py` 작성 직전 | 사용자 |
| Playwright 의존성 추가 | ✅ 승인 | Phase B0 에서 `pyproject.toml` 반영 | Claude |
| Gemini API 키 등록 | ✅ 등록 예정 | Phase B0 에서 `.env` 확인 | 사용자 |
| MVP 템플릿 5종 | 1차 Claude prototyping → 사용자 검토 | Phase B5 초입 | Claude(1차), 사용자(검토·교체) |
| 로고 자동 추출 폴백 셀렉터 | Phase B0 실측 필요 | Phase B0 에서 10개 샘플 홈페이지 대상 실측 후 셀렉터 세트 확정 | Claude |
| PDF 파싱 한계 케이스 | Phase B0 실측 필요 | pypdf → pdfplumber fallback 전략, 한글 PDF 3종(스캔·텍스트·혼합) 테스트 | Claude |
| 이미지 슬롯 캐시 보존 정책 | MVP 영구 | 운영 시 크기 모니터링 후 TTL 검토 | — |
| Phase 2 Web UI | 별도 문서 | Phase 2 진입 시 | — |

### 15-1. 디자인 시안 주체 (템플릿 5종)

**1차**: Claude 가 `frontend-design` 스킬을 활용하여 5종 HTML/CSS prototyping.
- 각 템플릿은 독립 폴더(`templates/{id}/`)라서 후속 교체 비용 낮음
- 초안 기준: 병원 마케팅 상세페이지 한국 레퍼런스 (브랜딩 전문 클리닉, 피부과·성형외과·한의원 상세페이지) + 브랜드 디자인 토큰을 CSS 변수로 받는 골격

**2차**: 사용자 검토 → 수정 피드백 → Claude 수정

**3차 (선택)**: 사용자가 Figma 또는 이미지 시안 직접 제공 → Claude 가 HTML/CSS 로 이식. 특정 템플릿에 강한 브랜드 의도가 있을 때만 필요.

### 15-2. Phase B0 실측 체크리스트 (Phase B0 에 일괄 수행)

- [ ] Playwright 설치 → Chromium 다운로드 → 샘플 HTML 1개 full_page 스크린샷
- [ ] 한국어 웹폰트 임베딩 (Pretendard.woff2) + 렌더 시 폰트 깨짐 없음 확인
- [ ] 로고 자동 추출 — 임의 한의원 10곳 홈페이지 대상, 폴백 셀렉터 세트 확정
- [ ] PDF 파싱 — 한글 PDF 3종(스캔 이미지·텍스트·혼합) → pypdf·pdfplumber 비교
- [ ] docx 파싱 — 표 포함 docx 1개, 텍스트 flatten 정확성 확인
- [ ] Nano Banana 1회 호출 → 응답 시간·이미지 품질·한국어 텍스트 렌더 여부 실측 (렌더 실패 시 §11-3 결정 재검토)
- [ ] Gemini 응답 저장·캐시 키 sha256 일관성 확인

---

## 16. SEO 트랙과의 영향

본 트랙 도입으로 인해 SEO 트랙(`SPEC-SEO-TEXT.md`)에 가해지는 변경:

1. **`SPEC-SEO-TEXT.md` 헤더에 트랙 분리 안내 한 줄 추가** (별도 task)
2. **`domain/compliance/rules.py` 에 `CompliancePolicy` enum 도입** — SEO_STRICT 와 BRAND_LENIENT 두 프로필 동시 지원. 기존 SEO 코드는 명시적으로 `policy=SEO_STRICT` 호출하도록 마이그레이션 필요
3. **`config/schema.sql` 에 3개 테이블 추가** (`brand_profiles`, `brand_assets`, `brand_cards`) — 기존 테이블 무영향
4. **`config/.env` 키 추가** — `GEMINI_API_KEY`
5. **`pyproject.toml` 의존성 추가** — `playwright`, `jinja2`, `python-docx`, `pypdf`, `google-generativeai`, `pillow`(이미 있을 가능성)
6. **루트 `CLAUDE.md` 에 브랜드 카드 도메인 한 줄 추가**

---

## 변경 이력

- `2026-04-16`: v1 초판. SEO 트랙과 분리한 브랜드 카드 전용 SPEC. 상세페이지형 long-form PNG, 13개 표준 블록, 템플릿 시스템, BRAND_LENIENT 7개 카테고리 초안, Playwright 렌더링, run_full_package 합류 모델
- `2026-04-16`: 1차 재검토 반영. (1) "PNG 확장자 단일, 장수 가변" 명확화 + 9000 px 자동 분할 규칙(§2-5). (2) 파일명 분할 suffix 규칙. (3) brand slug 정규화(§4-1-1). (4) [B1] HTML 전처리 명시. (5) [B4] 단일 호출 N 변형 반환. (6) [B5] 이미지 캐시 2계층(글로벌+작업). (7) [B7] fixer 블록 재생성 시 image_slot 재사용. (8) [B8] 자동 분할 알고리즘. (9) §13 ThreadPoolExecutor 동시성 + SEO 실패 시 failover. (10) §15 디자인 시안 주체·Phase B0 실측 체크리스트
- `2026-04-16`: 2차 재검토 반영. (1) location_map 블록 제거, closer 블록에서 지도 분리 (네이버 지도 본문 임베드로 대체). (2) 실사 사진 = 브랜드 `media_library` 자산으로 분리. (3) `ImageSlot.source_kind = "ai" | "media_library"` 도입. (4) `doctor_team`·`equipment` 블록은 media_library 참조 전용, 자산 없으면 블록 자체 skip. (5) `brand_media_assets` 테이블 추가. (6) brands/{slug}/{version}/media/ 디렉토리 추가
- `2026-04-16`: 3차 재검토 반영. (1) B안 확정 — `run_full_package` 유지, 두 트랙 병렬·독립 실행, 한쪽 실패 partial 허용. (2) `closer_cta` → `closer` 로 이름 변경. (3) CTA 버튼 UI 요소 생성 금지 — 네이버 블로그 본문 이미지는 외부 링크 이동 불가이므로 버튼형 시각 요소는 사용자 오해 유발. closer 블록은 브랜드 네임·검색 유도 텍스트·주소·영업시간·로고만 포함
- `2026-04-16`: 4차 재검토 — 전체 비평 26개 중 즉시 수정 10개 반영 + 주요 결정 2건. (1) §2-4/§2-5 섹션 번호 재정렬. (2) `BlockId` / `ImageSourceKind` / `AiImagePurpose` Enum 도입 + `ImageSlot.model_validator` 로 dual-truth 차단. (3) `BLOCK_MEDIA_MAPPING` 단일 출처 매핑 (§3-2-1). (4) media_library 참조 블록의 필수 승격 금지 규칙. (5) [B2] 가 user_input 기채움 필드는 "확정 — 생성 금지" 마커로 skip. (6) **media_library 는 brand 레벨 공유** (#10 A안). BrandAssets 에서 분리, brand_media_assets 테이블에서 asset_version 컬럼 제거, 디렉토리 `brands/{slug}/media/` 로 이동. (7) **`register_brand` upsert 통합** (#11). `update_brand_assets` 제거. 같은 slug 재호출 시 diff 기반 asset_version 자동 증가. media 파일은 sha256 중복 방지. (8) [B4] 프롬프트에 `available_media` 가용성 전달. `pattern_card=None` 이면 해당 섹션 완전 생략. (9) [B4-v] `validate_card_plan` 스테이지 신설 — 필수 블록·Enum·템플릿 슬롯·media 실재성 검증 후 실패 시 [B4] 1회 재호출. (10) [B6] 에 `template.validates(card_plan)` 사전 검증 추가. (11) §5-10 에러 핸들링 정책 통합표 신설 — 단계별 재시도·실패·전파 범위 단일 contract. (12) SPEC.md 참조를 모두 `SPEC-SEO-TEXT.md` 로 업데이트
