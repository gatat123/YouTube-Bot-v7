# Railway 배포 가이드 - YouTube 키워드 분석 봇 v7

## 📋 준비사항

### 1. 필수 계정 및 API 키
- **Railway 계정**: [railway.app](https://railway.app) 가입
- **Discord Bot Token**: [Discord Developer Portal](https://discord.com/developers/applications)에서 생성
- **Gemini API Key**: [Google AI Studio](https://makersuite.google.com/app/apikey)에서 발급
- **YouTube Data API Key** (선택): [Google Cloud Console](https://console.cloud.google.com)에서 발급

### 2. 프로젝트 준비
```bash
# Git 저장소 초기화 (아직 안했다면)
git init
git add .
git commit -m "Initial commit - YouTube Bot v7"
```

---

## 🚀 Railway 배포 단계

### Step 1: Railway 프로젝트 생성

1. [Railway Dashboard](https://railway.app/dashboard)에 로그인
2. **"New Project"** 클릭
3. **"Deploy from GitHub repo"** 선택
4. GitHub 계정 연결 및 저장소 선택

또는 CLI 사용:
```bash
# Railway CLI 설치
npm install -g @railway/cli

# 로그인
railway login

# 프로젝트 생성
railway init
```

### Step 2: 환경 변수 설정

Railway 대시보드에서:

1. 프로젝트 선택 → **"Variables"** 탭
2. 다음 환경 변수 추가:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here  # 선택사항

# Railway가 자동으로 제공하는 변수들:
# PORT, RAILWAY_ENVIRONMENT
# PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
```

3. **"Add Variable"** 버튼으로 각각 추가

### Step 3: PostgreSQL 데이터베이스 추가 (선택사항)

캐시 백업을 위한 PostgreSQL 추가:

1. Railway 프로젝트에서 **"+ New"** → **"Database"** → **"PostgreSQL"**
2. PostgreSQL이 자동으로 프로비저닝됨
3. 환경 변수가 자동으로 설정됨 (PGHOST, PGPORT 등)

> 💡 PostgreSQL을 추가하지 않아도 봇은 메모리 캐시만으로 정상 작동합니다.

### Step 4: 배포

#### 옵션 1: 자동 배포 (권장)
GitHub에 push하면 자동으로 배포됩니다:

```bash
git add .
git commit -m "Update configuration"
git push origin main
```

#### 옵션 2: 수동 배포
Railway CLI 사용:

```bash
railway up
```

### Step 5: 배포 확인

1. Railway 대시보드에서 빌드 로그 확인
2. **"Deployments"** 탭에서 배포 상태 확인
3. 성공 시 "Active" 상태 표시

---

## 🔧 문제 해결

### 1. 봇이 시작되지 않을 때

**로그 확인:**
```bash
railway logs
```

**일반적인 문제:**
- API 키가 올바르게 설정되지 않음 → 환경 변수 재확인
- 의존성 설치 실패 → `requirements.txt` 확인
- 포트 바인딩 문제 → Railway는 자동으로 PORT 환경변수 제공

### 2. 메모리 사용량이 높을 때

Railway 무료 플랜 한계:
- RAM: 512MB
- CPU: 0.5 vCPU

해결책:
- 캐시 크기 조정 (`cache_manager.py`의 `maxsize` 값 줄이기)
- 불필요한 로깅 비활성화

### 3. PostgreSQL 연결 실패

- PostgreSQL 서비스가 활성화되어 있는지 확인
- 환경 변수가 올바르게 설정되어 있는지 확인
- 연결 실패 시 자동으로 메모리 캐시만 사용됨

### 4. Discord 슬래시 명령어가 보이지 않을 때

1. 봇을 서버에서 제거 후 다시 초대
2. 봇 권한 확인 (슬래시 명령어 사용 권한 필요)
3. 봇 재시작 후 1-2분 대기 (Discord 캐시)

---

## 📊 모니터링

### Railway 대시보드에서 확인 가능한 정보:
- **Metrics**: CPU, 메모리 사용량
- **Logs**: 실시간 로그
- **Deployments**: 배포 히스토리
- **Environment**: 환경 변수

### 유용한 명령어:
```bash
# 실시간 로그 보기
railway logs --tail

# 서비스 재시작
railway restart

# 환경 변수 확인
railway variables
```

---

## 💰 비용 관리

### Railway 무료 플랜:
- $5 크레딧/월
- 실행 시간 500시간
- 봇은 24/7 실행 시 약 720시간 필요

### 비용 절감 팁:
1. 개발/테스트는 로컬에서
2. 불필요한 로깅 최소화
3. 캐시 적극 활용
4. PostgreSQL은 필요시에만 사용

### 예상 월 비용:
- 봇만: 약 $3-4
- 봇 + PostgreSQL: 약 $5-7

---

## 🔄 업데이트 방법

### 1. 코드 업데이트
```bash
# 로컬에서 수정
git add .
git commit -m "Update: 새로운 기능 추가"
git push origin main
```

### 2. 환경 변수 업데이트
- Railway 대시보드 → Variables → 수정

### 3. 의존성 업데이트
```bash
# requirements.txt 수정 후
git add requirements.txt
git commit -m "Update dependencies"
git push
```

---

## 🛡️ 보안 권장사항

1. **API 키 관리**
   - 절대 코드에 직접 입력하지 않기
   - `.env` 파일은 `.gitignore`에 포함
   - Railway 환경 변수만 사용

2. **봇 권한**
   - 필요한 최소 권한만 부여
   - Administrator 권한 지양

3. **로그 관리**
   - 민감한 정보 로깅 금지
   - 프로덕션에서는 INFO 레벨 이상만

---

## 📝 배포 체크리스트

- [ ] 모든 API 키 준비 완료
- [ ] `.env` 파일이 `.gitignore`에 포함됨
- [ ] `requirements.txt` 모든 의존성 포함
- [ ] 로컬 테스트 완료
- [ ] Git 저장소에 커밋
- [ ] Railway 프로젝트 생성
- [ ] 환경 변수 설정
- [ ] 배포 및 로그 확인
- [ ] Discord에서 봇 작동 테스트
- [ ] 슬래시 명령어 정상 작동 확인

---

## 🆘 추가 도움말

### 공식 문서:
- [Railway 문서](https://docs.railway.app)
- [Discord.py 문서](https://discordpy.readthedocs.io)
- [Gemini API 문서](https://ai.google.dev/docs)

### 문제 발생 시:
1. Railway 대시보드의 로그 확인
2. 환경 변수 재확인
3. 로컬에서 먼저 테스트
4. Railway Discord 커뮤니티 참고

---

## 🎉 배포 완료!

봇이 성공적으로 배포되면:
1. Discord 서버에서 `/analyze` 명령어 사용
2. 분석 결과 확인
3. `/cache_stats`로 캐시 상태 모니터링

Happy YouTube Analyzing! 🚀