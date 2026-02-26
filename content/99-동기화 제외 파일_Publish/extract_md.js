const fs = require('fs');
const path = require('path');

// 명령줄 인자 받기
const srcRoot = process.argv[2]; // 원본 경로
const destRoot = process.argv[3]; // 대상 경로

if (!srcRoot || !destRoot) {
    console.error("❌ 사용법: node extract_md.js <원본경로> <대상경로>");
    process.exit(1);
}

// 🚫 제외할 폴더 목록 (필요에 따라 추가/삭제)
const EXCLUDE_DIRS = [
    '.git', 
    '.obsidian', 
    '.trash',
    '99-동기화 제외 파일', 
    '99-이미지 파일 모음', // 이미지는 제외하고 텍스트만 가져오려면 포함
    'node_modules'
];

let fileCount = 0;

function copyMdFilesRecursive(currentSrc, currentDest) {
    // 대상 폴더가 없으면 생성
    if (!fs.existsSync(currentDest)) {
        fs.mkdirSync(currentDest, { recursive: true });
    }

    const entries = fs.readdirSync(currentSrc, { withFileTypes: true });

    for (const entry of entries) {
        const srcPath = path.join(currentSrc, entry.name);
        const destPath = path.join(currentDest, entry.name);

        // 1. 폴더인 경우 (재귀 처리)
        if (entry.isDirectory()) {
            if (EXCLUDE_DIRS.includes(entry.name)) {
                // 제외 폴더는 스킵
                continue;
            }
            copyMdFilesRecursive(srcPath, destPath);
        } 
        // 2. 파일인 경우 (.md 확인)
        else if (entry.isFile()) {
            if (entry.name.toLowerCase().endsWith('.md')) {
                fs.copyFileSync(srcPath, destPath);
                fileCount++;
                // 진행 상황 로그 (너무 많으면 주석 처리)
                // console.log(`[복사] ${entry.name}`);
            }
        }
    }
    
    // 빈 폴더가 생겼다면 삭제 (선택 사항 - 원치 않으면 이 부분 삭제)
    try {
        if (fs.readdirSync(currentDest).length === 0) {
            fs.rmdirSync(currentDest);
        }
    } catch (e) {}
}

console.log(`\n🚀 작업 시작`);
console.log(`📂 원본: ${srcRoot}`);
console.log(`📂 대상: ${destRoot}`);
console.log(`----------------------------------------`);

const startTime = Date.now();
try {
    copyMdFilesRecursive(srcRoot, destRoot);
} catch (err) {
    console.error(`\n❌ 오류 발생: ${err.message}`);
}

const duration = ((Date.now() - startTime) / 1000).toFixed(2);
console.log(`----------------------------------------`);
console.log(`✅ 작업 완료!`);
console.log(`📄 총 복사된 파일: ${fileCount}개`);
console.log(`⏱️ 소요 시간: ${duration}초`);