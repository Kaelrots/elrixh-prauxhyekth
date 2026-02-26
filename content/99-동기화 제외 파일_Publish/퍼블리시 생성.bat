@echo off
:: 한글 깨짐 방지
chcp 65001 > nul

echo ==========================================
echo 작업 환경 경로를 자동 탐색합니다...
echo ==========================================

:: 1. 노트북 경로 (C드라이브) 확인
if exist "C:\구글 드라이브\세계관" (
    set "TARGET_PATH=C:\구글 드라이브\세계관"
    echo [안내] 노트북 환경이 감지되었습니다. (C드라이브)
    goto :EXECUTE
)

:: 2. 데스크탑 경로 (E드라이브) 확인
if exist "E:\구글 드라이브\세계관" (
    set "TARGET_PATH=E:\구글 드라이브\세계관"
    echo [안내] 데스크탑 환경이 감지되었습니다. (E드라이브)
    goto :EXECUTE
)

:: 3. 둘 다 없을 경우 에러 처리
echo [오류] C드라이브와 E드라이브 모두에서 세계관 경로를 찾을 수 없습니다.
pause
exit /b

:EXECUTE
echo.
echo 발견된 경로: "%TARGET_PATH%"
echo 퍼블리시용 테이블 및 인링크 변환을 시작합니다...
echo.

node convert-tables-final-with-inlink.publish.js "%TARGET_PATH%"

echo.
pause