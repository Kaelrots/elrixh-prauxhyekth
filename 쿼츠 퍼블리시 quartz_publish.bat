@echo off
:: 한글 깨짐 방지를 위해 인코딩을 UTF-8로 설정합니다.
chcp 65001 > nul

echo ==========================================
echo [엘리스 프라우셰크트] 퍼블리시 자동화 시작!
echo ==========================================

echo.
echo [1/4] 마크다운 문서 내 이미지 절대경로 주입 및 링크 교정 중...
python fix_links.py

echo.
echo [2/4] 마크다운 굵은 글씨를 HTML font 태그로 변환 중...
python bold_converter.py

echo.
echo [3/4] 미디어 파일 중앙 집중화 복사 중...
python mirror_assets.py

echo.
echo [4/4] Github으로 동기화(Push) 중...
:: 🔥 [핵심 해결책] gitignore 규칙을 무시하고 미디어 폴더의 파일들을 강제로 깃허브에 올립니다!
git add -f content/assets/media/
git add .
git commit -m "오늘의 세계관 업데이트 - %date% %time%"
git push origin main

echo.
echo ==========================================
echo 모든 작업이 완료되었습니다! 퍼블리시 성공!
echo ==========================================
pause