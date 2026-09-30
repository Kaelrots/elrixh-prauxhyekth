@echo off
chcp 65001 >nul
setlocal
if "%~1"=="" (
  echo [Quartz 웹 빌드 및 게시] 실제 작업을 시작합니다.
  node "%~dp0..\세계관\99-동기화 제외 파일\sync\quartz-main.cjs" --publish
) else (
  node "%~dp0..\세계관\99-동기화 제외 파일\sync\quartz-main.cjs" %*
)
set "WORLD_SYNC_EXIT=%ERRORLEVEL%"
if not "%~1"=="" goto finish
echo.
if "%WORLD_SYNC_EXIT%"=="0" (
  echo [완료] 웹 빌드와 GitHub 업로드를 완료했습니다.
  echo 실제 사이트 반영은 GitHub 배포 완료 후 확인하세요.
) else (
  echo [실패] 위 오류 내용을 확인해 주세요. 종료 코드: %WORLD_SYNC_EXIT%
  echo 실패한 상태에서는 다음 작업으로 넘어가지 마세요.
)
echo.
echo 창을 닫으려면 아무 키나 누르세요.
pause >nul
:finish
exit /b %WORLD_SYNC_EXIT%
