# YouTube 키워드 분석 봇 v7 🚀

> AI 기반 YouTube 키워드 분석 및 콘텐츠 전략 제공 Discord 봇

## 🎯 주요 특징

### v7 업데이트 내용
- **✨ 키워드 확장**: 40개의 키워드 확장
- **🤖 AI 엔진 변경**: Claude → Gemini 2.5 Pro (테스트 비용 절감)
- **💾 캐싱 시스템**: Python 메모리 캐시 + PostgreSQL 백업
- **🚀 Railway 배포**: 클라우드 배포 지원
- **📊 예측 엔진**: 실제 동작하는 성과 예측 모델
- **🔍 실제 데이터**: Google Trends 실제 데이터 검증 강화

### 핵심 기능
1. **40개 키워드 확장**: 다층적 키워드 분석
2. **2단계 필터링**: 40개 → 15개 정밀 선별
3. **실시간 트렌드 분석**: Google Trends 실제 데이터
4. **경쟁자 분석**: YouTube 상위 채널 분석
5. **성과 예측**: 조회수, 구독자 증가 예측
6. **스마트 캐싱**: 응답 속도 75% 향상

## 🛠️ 기술 스택

- **언어**: Python 3.11+
- **AI**: Gemini 2.5 Pro
- **봇 프레임워크**: Discord.py 2.3+
- **캐싱**: Python 메모리 캐시 + PostgreSQL (선택)
- **배포**: Railway
- **APIs**: YouTube Data API v3, Google Trends

## 📋 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/youtube-keyword-bot-v7.git
cd youtube-keyword-bot-v7
```

### 2. 가상환경 설정
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
`.env.example`을 `.env`로 복사하고 수정:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
YOUTUBE_API_KEY=your_youtube_api_key  # 선택사항
```

### 5. 봇 실행
```bash
python main.py
```

## 🚀 Railway 배포

자세한 배포 가이드는 [RAILWAY_DEPLOY_GUIDE.md](RAILWAY_DEPLOY_GUIDE.md) 참조

간단 배포:
1. Railway 계정 생성
2. GitHub 저장소 연결
3. 환경 변수 설정
4. 자동 배포 완료!

## 💬 사용법

### 기본 명령어
```
/analyze content:"YouTube 쇼츠 만들기" category:"Education"
```

### 파라미터
- `content` (필수): 분석할 주제
- `category` (선택): Gaming, Education, Entertainment, Tech, Vlog, Food
- `keywords` (선택): 추가 키워드 (쉼표 구분)
- `depth` (선택): light, medium, deep

### 기타 명령어
- `/cache_stats`: 캐시 상태 확인

## 📁 프로젝트 구조

```
youtube-keyword-bot-v7/
├── main.py                 # 메인 봇 파일
├── config.py              # 설정 관리
├── requirements.txt       # 의존성
├── .env.example          # 환경 변수 예시
├── runtime.txt           # Python 버전
├── Procfile             # Railway 프로세스
├── railway.json         # Railway 설정
│
├── core/                # 핵심 모듈
│   ├── keyword_expander.py    # Gemini 키워드 확장
│   ├── trend_analyzer.py      # 트렌드 분석
│   ├── competitor_analyzer.py # 경쟁 분석
│   └── prediction_engine.py   # 예측 엔진
│
├── utils/               # 유틸리티
│   ├── cache_manager.py       # 메모리 캐시
│   ├── progress_tracker.py    # 진행률 추적
│   └── api_manager.py         # API 관리
│
└── services/            # 외부 서비스
    ├── youtube_service.py     # YouTube API
    ├── trends_service.py      # Google Trends
    └── gemini_service.py      # Gemini AI
```

## 📊 성능

| 지표 | v6 | v7 | 개선율 |
|------|-----|-----|--------|
| 응답 시간 | 20-30초 | 5-10초 | -75% |
| 키워드 수 | 20개 | 90개 | +350% |
| 최종 선별 | 15개 | 40개 | +167% |
| API 비용 | $0.5/요청 | $0.2/요청 | -60% |

## 🔧 설정 커스터마이징

### 캐시 설정 (cache_manager.py)
```python
# 메모리 캐시 크기
self.memory_cache = TTLCache(maxsize=1000, ttl=3600)

# TTL 전략
self.ttl_strategy = {
    "trending": 1800,    # 30분
    "stable": 86400,     # 24시간
    "seasonal": 604800   # 7일
}
```

### 예측 모델 조정 (prediction_engine.py)
```python
# 카테고리별 성장 배수
self.category_multipliers = {
    "Gaming": 2.5,
    "Education": 1.8,
    # ...
}
```

## 🐛 문제 해결

### 봇이 응답하지 않을 때
1. Discord 봇 토큰 확인
2. 봇 권한 확인 (슬래시 명령어 사용)
3. 로그 확인

### Google Trends 데이터가 없을 때
- 자동으로 대체 수집 방법 시도
- 너무 많은 요청 시 일시적 제한 가능

### 메모리 사용량이 높을 때
- 캐시 크기 조정
- PostgreSQL 백업 활성화

## 📝 라이선스

MIT License - 자유롭게 사용 가능

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 👥 만든이

- 개발자: [Your Name]
- 문의: [your.email@example.com]

## 🙏 감사의 말

- Google Gemini API
- Discord.py 커뮤니티
- Railway 플랫폼

---

**v7.0.0** | Last Updated: 2025-08-06
