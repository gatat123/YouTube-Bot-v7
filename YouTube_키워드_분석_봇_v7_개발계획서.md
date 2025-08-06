# YouTube 키워드 분석 봇 v7 개발 계획서

**수정사항**
# 캐싱 시스템 변경 ✓

Redis → Python 메모리 캐시로 변경
PostgreSQL 백업 기능 추가 (선택적)
cache_manager.py 완전히 재작성

# 불필요한 서비스 제거 ✓

TikTok/Twitter 서비스 파일 제거
관련 의존성 제거

# Google Trends 실제 데이터 ✓

trends_service.py 개선
실제 데이터 검증 로직 강화
대체 수집 방법 구현

# 예측 엔진 구현 ✓

prediction_engine.py 실제 동작하는 규칙 기반 모델 구현
조회수, 구독자 증가, 성공률 예측 기능

# AI 모델 변경 ✓

Claude API → Gemini 2.5 Pro로 변경
keyword_expander.py 수정 완료
비용 절감 효과 (약 60%)


## 📋 원본 프로젝트 개요

### 목표
기존 YouTube 키워드 분석 봇(v6)을 대폭 개선하여 더 정확하고 실용적인 키워드 분석 및 콘텐츠 전략을 제공하는 봇 개발

### 핵심 개선사항
- **키워드 확장**: 20개 → 90개로 대폭 확대
- **필터링 강화**: 2단계 필터링으로 40개 정밀 선별
- **성능 최적화**: Redis 캐싱으로 응답속도 75% 단축
- **실시간 분석**: TikTok, Twitter 트렌드 통합 -> TikTok/Twitter 서비스 파일 제거
- **예측 기능**: AI 기반 조회수/성과 예측 -> prediction_engine.py 실제 동작하는 규칙 기반 모델 구현

---

## 🏗️ 시스템 아키텍처

```
사용자 입력
    │
    ▼
┌──────────────┐
│ API Gateway  │ ←─── Redis Cache (L1: 메모리, L2: 디스크)
└──────────────┘
    │
    ▼
┌──────────────────┐     ┌─────────────┐
│ Claude AI        │────▶│ 90개 키워드  │
│ (강화된 프롬프트) │     │    추출     │
└──────────────────┘     └─────────────┘
           │
           ▼
    ┌──────────────────────────────────┐
    │        병렬 API 호출 (90개)       │
    │  • Google Trends (배치 5개씩)     │
    │  • YouTube 자동완성*              │
    └──────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │ 1차 필터링    │ (상위 60개 선별 - 실제 데이터 기반)
    └──────────────┘
           │
    ┌──────┴───────┬────────┬────────┐
    ▼              ▼        ▼        ▼
Google Trends  YouTube API  TikTok  Twitter
(상세 분석)    (메트릭 수집)
    │              │        │        │
    └──────┬───────┴────────┴────────┘
           ▼
    ┌──────────────┐
    │ 2차 필터링    │ (35-40개 정밀 선별)
    └──────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
Title Gen    Prediction
(Gemini)      Engine
    │             │
    └──────┬──────┘
           ▼
    ┌──────────────┐
    │ 최종 리포트  │
    └──────────────┘
```

**YouTube 자동완성*: Google의 자동완성 API (http://suggestqueries.google.com)를 사용하여 YouTube 검색창에서 제안되는 연관 키워드를 수집합니다. YouTube API와는 별개의 무료 서비스입니다.

---

## 🚀 개발 로드맵

### Phase 1: 핵심 기능 강화 (1-2주)

#### 1. Claude AI 키워드 확장 개선
```python
# 기존: 20개 단순 추출
# 개선: 90개 다층 확장

keyword_structure = {
    "핵심 키워드": 30개,     # 직접 동의어, 축약어, 별칭
    "검색 의도별": 20개,     # 정보성, 학습형, 비교형, 문제해결
    "타겟 대상별": 15개,     # 초보자, 중급자, 전문가
    "시간/상황별": 10개,     # 시즌, 트렌드, 최신
    "롱테일 조합": 15개      # 3-5단어 자연스러운 조합
}
```

**구현 내용:**
- `ClaudeAnalyzer` 클래스의 `extract_smart_keywords()` 메서드 재작성
- 프롬프트 엔지니어링으로 다층적 키워드 추출
- 카테고리별 특화 키워드 전략 적용

#### 2. Redis 캐싱 시스템
```python
class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=False
        )
    
    # 동적 TTL 관리
    ttl_strategy = {
        "급상승": 3600,      # 1시간
        "안정적": 86400,     # 24시간  
        "계절성": 604800     # 7일
    }
```

**구현 내용:**
- Redis 설치 및 연동
- 캐시 키 생성 로직 (해시 기반)
- TTL 자동 조정 알고리즘
- 유사 검색어 그룹핑

#### 3. 실시간 진행 상황 업데이트
```python
class ProgressTracker:
    stages = [
        ("🔍", "카테고리 분석", 2),
        ("🤖", "AI 키워드 확장", 5),
        ("📊", "Google Trends 분석", 8),
        ("📺", "YouTube 데이터 수집", 6),
        ("🏆", "경쟁자 분석", 4),
        ("💡", "제목 생성", 3)
    ]
```

**구현 내용:**
- Discord 임베드 실시간 업데이트
- 진행률 바 시각화
- 예상 완료 시간 표시

---

### Phase 2: 분석 고도화 (3-4주)

#### 4. 경쟁 채널 딥 다이브
```python
class CompetitorAnalyzer:
    async def analyze_top_competitors(self, keyword: str):
        # 상위 10개 영상의 채널 분석
        # 구독자 규모, 업로드 패턴, 태그 분석
        # 콘텐츠 공백 매트릭스 생성
        # 콜라보 기회 점수 계산
```

**구현 내용:**
- YouTube API로 경쟁 채널 데이터 수집
- 성장 궤적 분석 알고리즘
- 콘텐츠 갭 분석
- 시너지 점수 계산

#### 5. 실시간 트렌드 레이더
```python
class TrendRadar:
    sources = {
        "tiktok": TikTokMonitor(),
        "twitter": TwitterMonitor(),
        "reddit": RedditMonitor()
    }
    
    async def detect_viral_potential(self, keyword):
        # 바이럴 예측 스코어 계산
        # 24시간 내 대응 전략 생성
```

**구현 내용:**
- TikTok 해시태그 모니터링 API
- Twitter 실시간 트렌드 추적
- 바이럴 예측 알고리즘
- 즉시 대응 콘텐츠 템플릿

---

### Phase 3: 지능형 예측 (5-6주)

#### 6. 예측 분석 엔진
```python
class PredictionEngine:
    def predict_views(self, keyword_data):
        # 머신러닝 모델 기반 조회수 예측
        # 최적 업로드 타이밍 계산
        # 구독자 증가율 시뮬레이션
```

**구현 내용:**
- 과거 데이터 수집 및 학습
- 예측 모델 구축 (RandomForest/XGBoost)
- 신뢰 구간 계산
- 시각화 대시보드

#### 7. 인터랙티브 분석 리포트
```python
class InteractiveReport:
    components = {
        "trend_chart": "Chart.js 실시간 그래프",
        "keyword_map": "D3.js 관계도",
        "heatmap": "Plotly 경쟁도 맵",
        "action_plan": "다운로드 가능 PDF"
    }
```

**구현 내용:**
- 웹 기반 대시보드 개발
- 인터랙티브 차트 구현
- PDF 리포트 생성
- 공유 기능

---

## 📊 키워드 필터링 상세 프로세스

### 1차 필터링 (90개 → 50개)
```python
def first_filter(keywords):
    # 빠른 기회 점수 계산
    for keyword in keywords:
        score = calculate_quick_opportunity_score(keyword)
    return top_50_keywords
```

### 2차 필터링 (60개 → 40개)
```python
def second_filter(keywords_with_metrics):
    # 종합 점수 기반 정밀 선별
    final_keywords = {
        "핵심 추천": 20개,
        "블루오션": 15개,
        "급상승": 15개,
        "롱테일": 5개,
        "실험용": 5개
    }
    return final_keywords
```

---

## 🛠️ 기술 스택

### Backend
- **언어**: Python 3.10+
- **프레임워크**: Discord.py 2.0
- **캐싱**: Redis
- **데이터베이스**: SQLite (이력 저장)

### APIs
- **Claude API**: 키워드 확장
- **Gemini API**: 제목 생성
- **YouTube Data API v3**: 메트릭 수집
- **Google Trends API**: 트렌드 분석
- **TikTok API**: 실시간 트렌드
- **Twitter API v2**: 버즈 모니터링

### 시각화
- **Chart.js**: 트렌드 차트
- **D3.js**: 키워드 네트워크
- **Plotly**: 히트맵

---

## 📁 파일 구조

```
youtube-keyword-bot-v7/
│
├── main.py                 # 메인 봇 파일
├── config.py              # 설정 관리
├── requirements.txt       # 의존성
│
├── core/
│   ├── __init__.py
│   ├── keyword_expander.py    # Claude AI 키워드 확장
│   ├── trend_analyzer.py      # 트렌드 분석
│   ├── competitor_analyzer.py # 경쟁 분석
│   └── prediction_engine.py   # 예측 엔진
│
├── utils/
│   ├── cache_manager.py       # Redis 캐싱
│   ├── progress_tracker.py    # 진행 상황
│   └── api_manager.py         # API 통합 관리
│
├── services/
│   ├── youtube_service.py     # YouTube API
│   ├── trends_service.py      # Google Trends
│   ├── tiktok_service.py      # TikTok 모니터링
│   └── twitter_service.py     # Twitter 모니터링
│
└── tests/
    ├── test_keyword_expander.py
    └── test_prediction.py
```

---

## 🔧 환경 설정

### 필수 환경 변수 (.env)
```bash
# Discord
DISCORD_BOT_TOKEN=your_token

# APIs
ANTHROPIC_API_KEY=your_claude_key
GEMINI_API_KEY=your_gemini_key
YOUTUBE_API_KEY=your_youtube_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional
TIKTOK_API_KEY=your_tiktok_key
TWITTER_BEARER_TOKEN=your_twitter_token
```

### 설치 명령어
```bash
# Redis 설치
sudo apt-get install redis-server

# Python 패키지
pip install -r requirements.txt

# 봇 실행
python main.py
```

---

## 📈 예상 성과

| 지표 | 현재 (v6) | 목표 (v7) | 개선율 |
|------|-----------|-----------|--------|
| 응답 시간 | 20-30초 | 5-10초 | -75% |
| 키워드 정확도 | 70% | 90% | +28% |
| API 비용 | $0.5/요청 | $0.2/요청 | -60% |
| 키워드 추출 수 | 20개 | 90개 | +350% |
| 최종 선별 키워드 | 15개 | 40개 | +167% |

---

## ✅ 체크리스트

### Phase 1 시작 전
- [ ] Redis 서버 설치 및 설정
- [ ] API 키 확보 (Claude, Gemini, YouTube)
- [ ] 개발 환경 세팅
- [ ] 테스트 Discord 서버 준비

### 코드 작업
- [ ] main_v6_improved.py 백업
- [ ] 새 프로젝트 구조 생성
- [ ] 기존 코드 모듈화
- [ ] 단위 테스트 작성

### 구현 순서
1. **Week 1**: Claude AI 프롬프트 개선
2. **Week 2**: Redis 캐싱 구현
3. **Week 3**: 경쟁 채널 분석
4. **Week 4**: 트렌드 레이더
5. **Week 5-6**: 예측 엔진 및 대시보드

---

## 💡 추가 아이디어

### 향후 확장 가능성
- YouTube Shorts 특화 분석
- 대본 작성 도우미
- 수익화 전략 분석

### 프리미엄 기능
- 개인 브랜드 키워드 추적
- 맞춤형 주간 리포트
- API 우선 순위 큐
- 전용 캐시 서버

---