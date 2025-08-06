# YouTube Bot v7 파일 무결성 검사기 - PowerShell 버전
# PowerShell 5.0+ 호환

# UTF-8 인코딩 설정
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  YouTube Bot v7 파일 무결성 검사기" -ForegroundColor White
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Python 설치 확인 함수
function Test-PythonInstalled {
    try {
        $pythonVersion = python --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Python 발견: $pythonVersion" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "❌ Python이 설치되어 있지 않습니다." -ForegroundColor Red
        Write-Host "   Python 3.7 이상을 설치해주세요." -ForegroundColor Yellow
        return $false
    }
    return $false
}

# 파일 존재 확인 함수
function Test-IntegrityCheckerFile {
    $checkerFile = Join-Path $PSScriptRoot "file_integrity_checker.py"
    if (Test-Path $checkerFile) {
        Write-Host "✅ 검사기 파일 발견: file_integrity_checker.py" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ 검사기 파일을 찾을 수 없습니다: file_integrity_checker.py" -ForegroundColor Red
        return $false
    }
}

# 메인 실행 로직
try {
    # 필수 조건 확인
    if (-not (Test-PythonInstalled)) {
        Write-Host ""
        Write-Host "계속하려면 아무 키나 누르세요..." -ForegroundColor Yellow
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 1
    }

    if (-not (Test-IntegrityCheckerFile)) {
        Write-Host ""
        Write-Host "계속하려면 아무 키나 누르세요..." -ForegroundColor Yellow
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 1
    }

    # 작업 디렉토리 설정
    Set-Location $PSScriptRoot
    
    Write-Host ""
    Write-Host "🔍 파일 무결성 검사를 시작합니다..." -ForegroundColor Yellow
    Write-Host ""

    # Python 스크립트 실행
    $process = Start-Process -FilePath "python" -ArgumentList "file_integrity_checker.py" -NoNewWindow -Wait -PassThru

    # 실행 결과 확인
    if ($process.ExitCode -eq 0) {
        Write-Host ""
        Write-Host "✅ 파일 무결성 검사가 완료되었습니다." -ForegroundColor Green
        
        $reportFile = Join-Path $PSScriptRoot "file_integrity_report.json"
        if (Test-Path $reportFile) {
            Write-Host "📋 상세 보고서: file_integrity_report.json" -ForegroundColor Cyan
            
            # 보고서 크기 표시
            $fileSize = (Get-Item $reportFile).Length
            Write-Host "   보고서 크기: $([math]::Round($fileSize/1KB, 2)) KB" -ForegroundColor Gray
        }
    } else {
        Write-Host ""
        Write-Host "❌ 파일 무결성 검사 중 오류가 발생했습니다." -ForegroundColor Red
        Write-Host "   오류 코드: $($process.ExitCode)" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "아무 키나 눌러서 종료하세요..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

} catch {
    Write-Host ""
    Write-Host "❌ 예상치 못한 오류가 발생했습니다:" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "아무 키나 눌러서 종료하세요..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}