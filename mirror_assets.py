import os
import shutil
import re
import urllib.parse
import time

# 경로 설정
content_dir = "content"
public_dir = "public"
media_dir_name = os.path.join("assets", "media")

target_dirs = [
    os.path.join(content_dir, media_dir_name),
    os.path.join(public_dir, media_dir_name)
]

def master_sync():
    for t_dir in target_dirs:
        if not os.path.exists(t_dir):
            os.makedirs(t_dir, exist_ok=True)

    exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp3', '.mp4')
    print("--- 1. 미디어 파일 양방향 수집 시작 (자기복제 방지 완벽판) ---")
    
    count = 0
    for root, dirs, files in os.walk(content_dir):
        # 🚨 핵심 수정: 대문자 Assets, 소문자 assets 모두 정확히 필터링 (root.lower() 사용)
        root_lower = root.lower()
        if "assets" in root_lower or "public" in root_lower:
            continue
            
        for file in files:
            if file.lower().endswith(exts):
                source_path = os.path.join(root, file)
                safe_name = file.replace(" ", "-")
                
                for t_dir in target_dirs:
                    dest_path = os.path.join(t_dir, safe_name)
                    
                    try:
                        shutil.copy(source_path, dest_path)
                    except shutil.SameFileError:
                        # 💡 원본과 대상이 완전히 같은 파일(대소문자만 다른 경우 등)이면 그냥 넘어감
                        pass
                    except PermissionError:
                        time.sleep(0.3)
                        try:
                            shutil.copy(source_path, dest_path)
                        except:
                            print(f"⚠️ 건너뜀 (사용 중인 파일): {safe_name}")
                            
                count += 1
    print(f"--- 총 {count}개의 미디어 파일 소스 처리 완료 ---")

    # 2단계: HTML 링크 교정 및 표 이미지 복구
    print("--- 2. 웹사이트(HTML) 링크 교정 및 표 이미지 복구 중 ---")
    html_count = 0
    for root, dirs, files in os.walk(public_dir):
        for file in files:
            if file.endswith(".html"):
                html_path = os.path.join(root, file)
                rel_dir = os.path.relpath(root, public_dir)
                depth = 0 if rel_dir == "." else len(rel_dir.split(os.sep))
                # HTML 내 미디어 경로 구분자는 항상 '/'여야 함
                prefix_media = media_dir_name.replace(os.sep, '/')
                prefix = f"./{prefix_media}/" if depth == 0 else "../" * depth + f"{prefix_media}/"

                with open(html_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                def fix_path(match):
                    attr, url, quote = match.group(1), match.group(2), match.group(3)
                    if url.startswith("http") or "static/" in url or "Assets/" in url:
                        return match.group(0)
                    if any(ext in url.lower() for ext in exts):
                        filename = url.rstrip('/').split('/')[-1]
                        filename = urllib.parse.unquote(filename).replace('+', ' ')
                        filename = re.sub(r'\s+', '-', filename.strip())
                        return f"{attr}{prefix}{filename}{quote}"
                    return match.group(0)

                content = re.sub(r'(src="|href=")(.*?)(")', fix_path, content)

                def restore_table_image(match):
                    img_url, inner_text = match.group(1), match.group(2)
                    size = f' width="{inner_text}"' if inner_text.isdigit() else ""
                    return f'<img src="{img_url}"{size} alt="{inner_text}" />'

                pattern = r'!\s*<a\s+[^>]*?href="([^"]*?(?:png|jpg|jpeg|gif|webp))"[^>]*?>\s*(.*?)\s*</a>'
                content = re.sub(pattern, restore_table_image, content, flags=re.IGNORECASE)

                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    html_count += 1
    print(f"--- 총 {html_count}개의 HTML 파일 처리 완료! ---")

if __name__ == "__main__":
    master_sync()