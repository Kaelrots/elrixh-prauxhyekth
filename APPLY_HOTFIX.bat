@echo off
chcp 65001 >nul
setlocal EnableExtensions

set "SOURCE=%~dp0quartz-prepare.cjs"
if not exist "%SOURCE%" goto source_missing

set "TARGET=%~dp0..\세계관\99-동기화 제외 파일\sync\quartz-prepare.cjs"
if exist "%TARGET%" goto target_ok
set "TARGET=E:\구글 드라이브\세계관\99-동기화 제외 파일\sync\quartz-prepare.cjs"
if exist "%TARGET%" goto target_ok
set "TARGET=C:\구글 드라이브\세계관\99-동기화 제외 파일\sync\quartz-prepare.cjs"
if exist "%TARGET%" goto target_ok
goto target_missing

:target_ok
set "BACKUP=%TARGET%.before-link-hotfix.bak"
copy /y "%TARGET%" "%BACKUP%" >nul
if errorlevel 1 goto backup_failed

copy /y "%SOURCE%" "%TARGET%" >nul
if errorlevel 1 goto copy_failed

set "EXPECTED=509c4bfa9972c34b6efe6444b27aef70a3ade65fb8c6528ae06eff9cb0ae53fd"
for /f "usebackq delims=" %%H in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-FileHash -LiteralPath $env:TARGET -Algorithm SHA256).Hash.ToLower()"`) do set "ACTUAL=%%H"
if /I not "%ACTUAL%"=="%EXPECTED%" goto hash_failed

echo.
echo [OK] Quartz link resolver hotfix applied.
echo TARGET: %TARGET%
echo BACKUP: %BACKUP%
echo SHA256: %ACTUAL%
echo.
echo Run the Quartz publish BAT again.
pause
exit /b 0

:source_missing
echo [ERROR] quartz-prepare.cjs is missing next to this BAT.
pause
exit /b 3

:target_missing
echo [ERROR] Could not find the target quartz-prepare.cjs.
echo Checked the extracted-folder sibling path, E: drive, and C: drive.
pause
exit /b 2

:backup_failed
echo [ERROR] Backup failed: %BACKUP%
pause
exit /b 4

:copy_failed
echo [ERROR] Patch copy failed.
pause
exit /b 5

:hash_failed
echo [ERROR] SHA256 verification failed.
echo ACTUAL: %ACTUAL%
echo EXPECTED: %EXPECTED%
echo BACKUP: %BACKUP%
pause
exit /b 6
