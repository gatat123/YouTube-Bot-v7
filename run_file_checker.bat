@echo off
chcp 65001 > nul
echo =====================================
echo   YouTube Bot v7 파일 무결성 검사기
echo =====================================
echo.

REM Python이 설치되어 있는지 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo    Python 3.7 이상을 설치해주세요.
    echo.
    pause
    exit /b 1
)

REM 현재 디렉토리로 이동
cd /d "%~dp0"

REM 파일 무결성 검사 실행
echo 🔍 파일 무결성 검사를 시작합니다...
echo.

python file_integrity_checker.py

REM 실행 결과 확인
if %errorlevel% equ 0 (
    echo.
    echo ✅ 파일 무결성 검사가 완료되었습니다.
    echo 📋 상세 보고서: file_integrity_report.json
) else (
    echo.
    echo ❌ 파일 무결성 검사 중 오류가 발생했습니다.
    echo    오류 코드: %errorlevel%
)

echo.
echo 아무 키나 눌러서 종료하세요...
pause >nul