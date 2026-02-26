@echo off
chcp 65001 > nul
cd /d "%~dp0..\99-동기화 제외 파일"

REM 1. Obsidian 종료 후 이 배치파일 실행!
REM 2. 변경/통계/최신커밋만 남기기 실행
echo [Vault statistics, commit, clean history...]
node sync_commit_stats.js

REM 3. 최신커밋 강제 push (에러 방지, 필요시만)
git push origin main --force

echo [All done. 최신 커밋만 남음.]
pause
