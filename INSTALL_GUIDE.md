udio.microsoft.com/visual-cpp-build-tools/
- 또는 미리 컴파일된 wheel 파일 사용:
  ```bash
  pip install --only-binary :all: package_name
  ```

### Discord 권한 오류
```
discord.errors.Forbidden: 403 Forbidden
```
**해결**: 봇에 충분한 권한이 없습니다
- Discord 서버 설정에서 봇 역할 확인
- 필요 권한: 메시지 보내기, 임베드 링크, 슬래시 명령어 사용

## 🎮 사용법

### 봇 초대
1. Discord Developer Portal에서 OAuth2 → URL Generator
2. Scopes: `bot`, `applications.commands` 선택
3. Bot Permissions: 
   - Send Messages
   - Embed Links
   - Use Slash Commands
   - Read Message History
4. 생성된 URL로 봇 초대

### 명령어

#### `/analyze` - 메인 분석
```
/analyze content:"마인크래프트 건축" category:게임 depth:deep
```
- **content**: 분석할 주제 (필수)
- **category**: 게임/먹방/브이로그 등 (선택)
- **keywords**: 추가 키워드, 쉼표로 구분 (선택)
- **depth**: light/medium/deep (기본: medium)

#### `/quick` - 빠른 체크
```
/quick keywords:"마크 건축, 마크 팁, 마크 서바이벌"
```
- 최대 10개 키워드 빠른 분석

#### `/cache_status` - 캐시 상태
```
/cache_status
```
- Redis 캐시 성능 확인

## 📊 분석 깊이별 차이

| 기능 | Light | Medium | Deep |
|------|-------|--------|------|
| 키워드 확장 | 90개 | 90개 | 90개 |
| 최종 선별 | 20개 | 40개 | 60개 |
| YouTube 분석 | ✅ | ✅ | ✅ |
| 경쟁자 분석 | ❌ | 5개 채널 | 10개 채널 |
| 소요 시간 | 10-15초 | 20-30초 | 30-45초 |
| 캐시 활용 | ✅ | ✅ | ✅ |

## 🚀 성능 최적화 팁

### 1. Redis 사용
- 설치 시 응답 속도 75% 향상
- 동일 키워드 재분석 시 즉시 응답

### 2. API 키 모두 설정
- Gemini API: 더 나은 제목 생성
- YouTube API: 정확한 경쟁도 분석

### 3. 적절한 분석 깊이 선택
- 일반 분석: Medium
- 빠른 확인: Light  
- 심층 전략: Deep

## 📈 v6 → v7 업그레이드 가이드

### 주요 변경사항
1. **키워드 확장**: 20개 → 90개
2. **2단계 필터링**: 더 정밀한 선별
3. **Redis 캐싱**: 선택적 성능 향상
4. **모듈화**: 깔끔한 코드 구조
5. **진행 표시**: 실시간 상태 업데이트

### 마이그레이션
1. 새 폴더에 v7 설치 (기존 v6와 별도)
2. 동일한 API 키 사용 가능
3. Discord 봇 토큰 재사용 가능
4. 명령어 이름 변경: `/qw` → `/analyze`

## 🐛 디버깅

### 로그 확인
```bash
# 상세 로그 활성화
python main.py --log-level DEBUG
```

### 일반적인 문제

1. **봇이 응답하지 않음**
   - 슬래시 명령어 동기화 대기 (최대 1시간)
   - `/help` 명령어로 테스트

2. **분석이 너무 느림**
   - Redis 설치 및 실행 확인
   - 인터넷 연결 상태 확인
   - API 할당량 확인

3. **일부 기능 작동 안 함**
   - 선택적 API 키 확인 (YouTube, Gemini)
   - 로그에서 경고 메시지 확인

## 📞 지원

### 문제 보고
- GitHub Issues: [프로젝트 저장소]
- Discord 서버: [지원 서버]

### 기능 요청
- 새로운 카테고리 추가
- 분석 메트릭 제안
- UI/UX 개선 아이디어

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🙏 크레딧

- 개발자: 먼지
- Claude API: Anthropic
- Gemini API: Google
- YouTube Data API: Google
- Redis: Redis Labs

---

**v7.0.0** | 2024년 제작 | YouTube 키워드 분석의 새로운 기준