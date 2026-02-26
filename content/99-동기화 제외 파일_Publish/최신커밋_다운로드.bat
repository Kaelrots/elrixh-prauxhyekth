@echo off
chcp 65001 > nul
cd /d "%~dp0.."

REM 변경사항 있으면 stash
git status --porcelain > temp_git_status.txt
findstr /r /c:"^." temp_git_status.txt > nul
if %errorlevel%==0 (
  echo [변경사항 발견! stash 처리]
  git stash
)

REM 최신 커밋만 pull
git pull origin main

REM 필요시 stash pop
if %errorlevel%==0 (
  findstr /r /c:"^." temp_git_status.txt > nul
  if %errorlevel%==0 (
    git stash pop
  )
)
del temp_git_status.txt

echo [Done. 최신 상태로 동기화됨.]
pause
