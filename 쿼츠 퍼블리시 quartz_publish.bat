@echo off
chcp 65001 >nul
setlocal
echo [사용 종료] 이 구형 실행기는 새 동기화 체계로 교체되었습니다.
echo.
echo 1. "%~dp0..\세계관\세계관_동기화.bat" 실행
echo 2. "%~dp0세계관_Quartz.bat" 실행
echo 두 실행기가 각각 성공한 뒤 다음 작업을 진행하세요.
echo 이 파일은 변경이나 업로드를 실행하지 않습니다.
echo 원본 보관 위치: 세계관 폴더의 99-동기화 제외 파일\sync\legacy-backup\retired-2026-09-30
if not "%~1"=="" goto finish
echo.
echo 창을 닫으려면 아무 키나 누르세요.
pause >nul
:finish
exit /b 2
