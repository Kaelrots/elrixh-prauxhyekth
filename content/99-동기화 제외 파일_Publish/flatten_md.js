const fs = require('fs');
const path = require('path');

// 명령줄 인자 받기
const srcRoot = process.argv[2]; // 원본 경로
const destRoot = process.argv[3]; // 대상 경로

if (!srcRoot || !destRoot) {
    console.error("❌ 사용법: node flatten_md.js <원본경로> <대상경로>");
    process.exit(1);
}

// 🚫 제외할 폴더 목록
const EXCLUDE_DIRS = [
    '.git', 
    '.obsidian', 
    '.trash',
    '99-동기화 제외 파일', 
    '99-이미지 파일 모음',
    'node_modules'
];

let fileCount = 0;
let duplicateCount = 0;

// 대상 폴더 생성
if (!fs.existsSync(destRoot)) {
    fs.mkdirSync(destRoot, { recursive: true });
}

function flattenCopy(currentSrc) {
    const entries = fs.readdirSync(currentSrc, { withFileTypes: true });

    for (const entry of entries) {
        const srcPath = path.join(currentSrc, entry.name);

        // 1. 폴더인 경우 (재귀 진입)
        if (entry.isDirectory()) {
            if (EXCLUDE_DIRS.includes(entry.name)) continue;
            flattenCopy(srcPath); // 대상 경로는 전달하지 않음 (항상 destRoot로 모음)
        } 
        // 2. 파일인 경우 (.md 확인)
        else if (entry.isFile()) {
            if (entry.name.toLowerCase().endsWith('.md')) {
                let targetName = entry.name;
                let targetPath = path.join(destRoot, targetName);

                // ⚠️ 중복 파일명 처리 로직
                let counter = 1;
                while (fs.existsSync(targetPath)) {
                    const namePart = path.parse(entry.name).name;
                    const extPart = path.parse(entry.name).ext;
                    targetName = `${namePart}_${counter}${extPart}`;
                    targetPath = path.join(destRoot, targetName);
                    counter++;
                }

                if (counter > 1) duplicateCount++;

                fs.copyFileSync(srcPath, targetPath);
                fileCount++;
            }
        }
    }
}

console.log(`\n🚀 파일 모으기 시작 (폴더 구조 제거)`);
console.log(`📂 원본: ${srcRoot}`);
console.log(`📂 대상: ${destRoot}`);
console.log(`----------------------------------------`);

const startTime = Date.now();
try {
    flattenCopy(srcRoot);
} catch (err) {
    console.error(`\n❌ 오류 발생: ${err.message}`);
}

const duration = ((Date.now() - startTime) / 1000).toFixed(2);
console.log(`----------------------------------------`);
console.log(`✅ 작업 완료!`);
console.log(`📄 총 복사된 파일: ${fileCount}개`);
console.log(`🔄 이름 중복으로 변경된 파일: ${duplicateCount}개`);
console.log(`⏱️ 소요 시간: ${duration}초`);