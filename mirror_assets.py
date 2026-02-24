import os
import shutil
import re
import urllib.parse

# 경로 설정
content_dir = "content"
public_dir = "public"
media_dir_name = "assets/media"
target_media_dir = os.path.join(public_dir, media_dir_name)

def master_sync():
    # ==========================================
    # 1단계: 미디어 파일 수집 (기존과 동일)
    # ==========================================
    if not os.path.exists(target_media_dir):
        os.makedirs(target_media_dir, exist_ok=True)

    exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp3', '.mp4')
    print("--- 1. 미디어 파일 단일 폴더로 수집 중 ---")
    
    count = 0
    for root, dirs, files in os.walk(content_dir):
        for file in files:
            if file.lower().endswith(exts):
                source_path = os.path.join(root, file)
                safe_name = file.replace(" ", "-") # 공백 -> 하이픈
                dest_path = os.path.join(target_media_dir, safe_name)
                shutil.copy2(source_path, dest_path)
                count += 1
    print(f"--- 총 {count}개의 미디어 파일 수집 완료 ---")

    # ==========================================
    # 2단계 & 3단계: HTML 링크 교정 및 표 이미지 복구
    # ==========================================
    print("--- 2. 웹사이트(HTML) 링크 교정 및 표 이미지 복구 중 ---")
    html_count = 0
    
    for root, dirs, files in os.walk(public_dir):
        for file in files:
            if file.endswith(".html"):
                html_path = os.path.join(root, file)
                
                # 상대 경로 계산
                rel_dir = os.path.relpath(root, public_dir)
                depth = 0 if rel_dir == "." else len(rel_dir.split(os.sep))
                prefix = f"./{media_dir_name}/" if depth == 0 else "../" * depth + f"{media_dir_name}/"

                with open(html_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # [함수 1] 깨진 경로(href, src)를 올바른 media 폴더로 연결
                def fix_path(match):
                    attr = match.group(1)   # src=" or href="
                    url = match.group(2)    # url
                    quote = match.group(3)  # "
                    
                    if url.startswith("http") or "static/" in url or "Assets/" in url:
                        return match.group(0)

                    if any(ext in url.lower() for ext in exts):
                        # 경로 세탁 (공백, +, %20 제거 및 하이픈화)
                        filename = url.rstrip('/').split('/')[-1]
                        filename = urllib.parse.unquote(filename).replace('+', ' ')
                        filename = re.sub(r'\s+', '-', filename.strip())
                        
                        # 파라미터 제거
                        if '#' in filename: filename = filename.split('#')[0]
                        if '?' in filename: filename = filename.split('?')[0]

                        return f"{attr}{prefix}{filename}{quote}"
                    return match.group(0)

                # 1차 수정: 경로 고치기
                content = re.sub(r'(src="|href=")(.*?)(")', fix_path, content)

                # [함수 2] 표 안에서 !<a>...</a> 로 찢어진 태그를 <img>로 변환
                # 패턴: ! (공백가능) <a href="이미지경로">텍스트(사이즈)</a>
                def restore_table_image(match):
                    img_url = match.group(1) # 이미지 주소
                    inner_text = match.group(2) # 1200 또는 설명 텍스트
                    
                    # 텍스트가 숫자라면 width로 간주 (Obsidian 문법 |1200)
                    if inner_text.isdigit():
                        return f'<img src="{img_url}" width="{inner_text}" alt="{inner_text}" />'
                    else:
                        return f'<img src="{img_url}" alt="{inner_text}" />'

                # 2차 수정: !<a href="...">text</a> 패턴 찾기 (이미지 확장자 포함된 링크만)
                # 주의: 1차 수정에서 href가 이미 고쳐졌으므로 그 경로를 그대로 씁니다.
                pattern = r'!\s*<a\s+[^>]*?href="([^"]*?(?:png|jpg|jpeg|gif|webp))"[^>]*?>\s*(.*?)\s*</a>'
                content = re.sub(pattern, restore_table_image, content, flags=re.IGNORECASE)

                # 변경 저장
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    html_count += 1

    print(f"--- 총 {html_count}개의 HTML 파일 처리 완료! (표 이미지 복구 포함) ---")

if __name__ == "__main__":
    master_sync()