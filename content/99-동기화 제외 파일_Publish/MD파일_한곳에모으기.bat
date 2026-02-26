@echo off
chcp 65001 > nul
setlocal

:: ---------------------------------------------------------
:: 1. 경로 자동 감지 로직
:: ---------------------------------------------------------
set "PATH_LAPTOP=D:\세계관"
set "PATH_DESKTOP=C:\Users\user\Desktop\세계관"
set "SOURCE_PATH="

:: 노트북 경로 확인
if exist "%PATH_LAPTOP%\" (
    set "SOURCE_PATH=%PATH_LAPTOP%"
    echo [환경 감지] 노트북 환경입니다. (%PATH_LAPTOP%)
) else (
    :: 데스크탑 경로 확인
    if exist "%PATH_DESKTOP%\" (
        set "SOURCE_PATH=%PATH_DESKTOP%"
        echo [환경 감지] 데스크탑 환경입니다. (%PATH_DESKTOP%)
    )
)

:: ---------------------------------------------------------
:: 2. 유효성 검사 및 타겟 설정
:: ---------------------------------------------------------
if not defined SOURCE_PATH (
    echo.
    echo [오류] '세계관' 폴더를 찾을 수 없습니다.
    echo 확인된 경로 1: %PATH_LAPTOP%
    echo 확인된 경로 2: %PATH_DESKTOP%
    echo.
    pause
    exit /b
)

:: JS 파일 존재 확인
if not exist "flatten_md.js" (
    echo.
    echo [오류] 같은 폴더에 'flatten_md.js' 파일이 없습니다.
    echo.
    pause
    exit /b
)

:: 타겟 폴더 설정 (원본경로_All_In_One)
set "TARGET_PATH=%SOURCE_PATH%_All_In_One"

:: ---------------------------------------------------------
:: 3. 실행
:: ---------------------------------------------------------
echo.
echo [목표] 모든 .md 파일을 하나의 폴더로 모읍니다. (폴더 구조 제거)
echo [대상] %TARGET_PATH%
echo [주의] 파일명이 겹치면 자동으로 번호(_1)가 붙습니다.
echo.
echo 실행하려면 아무 키나 누르세요...
pause > nul

node flatten_md.js "%SOURCE_PATH%" "%TARGET_PATH%"

echo.
pause