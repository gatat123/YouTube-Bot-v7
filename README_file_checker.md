# 📋 YouTube Bot v7 파일 무결성 검사기 사용법

## 🎯 개요
모든 Python 파일을 검사하여 손상된 부분을 찾아내는 검사기입니다. 
구문 오류, 구조적 문제, 누락된 import 등을 자동으로 탐지합니다.

## 🚀 실행 방법

### 방법 1: 배치 파일 사용 (권장)
```cmd
run_file_checker.bat
```
- Windows 명령 프롬프트와 PowerShell 모두에서 작동
- 가장 안정적인 실행 방법

### 방법 2: PowerShell 스크립트 사용
```powershell
# PowerShell에서 실행
.\run_file_checker.ps1

# 또는 직접 호출
PowerShell -ExecutionPolicy Bypass -File run_file_checker.ps1
```
- PowerShell 전용 기능 활용
- 더 상세한 오류 정보 제공

### 방법 3: Python 직접 실행
```cmd
python file_integrity_checker.py
```
- 개발자용 직접 실행
- 스크립트 디버깅에 유용

## 📊 검사 항목

### 1. 구문 검사 (Syntax Check)
- Python AST 파싱을 통한 구문 오류 탐지
- 심각도: **CRITICAL**

### 2. 구조 검사 (Structure Check)
- 파일이 중간부터 시작하는지 확인
- 클래스/함수 정의 완결성 검사
- 들여쓰기 블록 완성도 확인
- 심각도: **HIGH** ~ **CRITICAL**

### 3. Import 검사 (Import Check)
- `__init__.py` 파일의 예상 import 확인
- 모듈별 필수 import 누락 탐지
- 심각도: **MEDIUM**

### 4. 특정 패턴 검사 (Pattern Check)
- 파일 비정상 종료 탐지
- 모듈별 필수 메서드 존재 확인
- 심각도: **MEDIUM** ~ **HIGH**

## 📄 출력 파일

### file_integrity_report.json
검사 완료 후 생성되는 상세 보고서:

```json
{
  "scan_date": "2025-01-31T...",
  "project_root": "C:\\Users\\...\\youtube-keyword-bot-v7",
  "summary": {
    "total_files_scanned": 25,
    "files_with_issues": 3,
    "healthy_files": 22,
    "health_percentage": 88.0
  },
  "severity_breakdown": {
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 5,
    "LOW": 0
  },
  "issue_types": {
    "SYNTAX_ERROR": 1,
    "TRUNCATED_START": 1,
    "MISSING_METHOD": 3
  },
  "detailed_issues": [...]
}
```

## 🔧 문제 해결

### PowerShell 실행 정책 오류
```powershell
# 현재 세션에서만 허용
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 또는 배치 파일 사용
run_file_checker.bat
```

### Python 경로 문제
```cmd
# Python 설치 확인
python --version

# 경로 추가가 필요한 경우
set PATH=%PATH%;C:\Python39;C:\Python39\Scripts
```

### 한글 깨짐 문제
```cmd
# 코드페이지 UTF-8로 설정
chcp 65001
```

## 📋 심각도 분류

| 심각도 | 설명 | 예시 |
|--------|------|------|
| **CRITICAL** | 즉시 수정 필요 | 구문 오류, 파일 읽기 실패 |
| **HIGH** | 빠른 수정 권장 | 파일 구조 손상, 불완전한 블록 |
| **MEDIUM** | 검토 후 수정 | 누락된 import, 비정상 종료 |
| **LOW** | 선택적 수정 | 스타일 가이드 위반 |

## 💡 사용 팁

1. **정기 검사**: 개발 중 주기적으로 실행하여 문제 조기 발견
2. **배포 전 검사**: 릴리즈 전 전체 파일 무결성 확인
3. **문제 파일 우선**: CRITICAL, HIGH 심각도 파일부터 수정
4. **백업 후 수정**: 중요한 파일은 백업 후 수정 작업 진행

## 🚨 주의사항

- 검사 중 파일을 수정하지 마세요
- 대용량 프로젝트는 검사 시간이 오래 걸릴 수 있습니다
- 네트워크 드라이브의 파일은 검사 속도가 느릴 수 있습니다

---

**Made for YouTube Bot v7 Project** 🤖