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
    print("--- 1. 미디어 파일 양방향 수집 ---")
    
    count = 0
    ignore_content_media = os.path.join(content_dir, media_dir_name).lower()
    
    for root, dirs, files in os.walk(content_dir):
        root_lower = root.lower()
        if root_lower == ignore_content_media or "public" in root_lower:
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
                        pass
                    except PermissionError:
                        time.sleep(0.3)
                        try:
                            shutil.copy(source_path, dest_path)
                        except:
                            pass
                count += 1
    print(f"--- 총 {count}개의 미디어 파일 소스 처리 완료 ---")

    # 2단계: HTML 링크 교정 (절대 경로 강제 적용)
    print("--- 2. 웹사이트(HTML) 미디어 절대 경로(/) 꽂아넣기 시작 ---")
    html_count = 0
    for root, dirs, files in os.walk(public_dir):
        for file in files:
            if file.endswith(".html"):
                html_path = os.path.join(root, file)
                
                with open(html_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                def fix_path(match):
                    attr, url, quote = match.group(1), match.group(2), match.group(3)
                    
                    # 외부 링크나 이미 /assets/media/ 가 박힌 건 패스
                    if url.startswith("http") or "static/" in url or "Assets/" in url or url.startswith("/assets/media/"):
                        return match.group(0)
                        
                    if any(ext in url.lower() for ext in exts):
                        # 기존 경로에 붙어있는 지저분한 ../ 다 떼어내고 순수 파일명만 추출
                        filename = url.rstrip('/').split('/')[-1]
                        filename = urllib.parse.unquote(filename).replace('+', ' ')
                        filename = re.sub(r'\s+', '-', filename.strip())
                        
                        # 🚨 [핵심] 복잡한 계산 집어치우고 무조건 사이트 최상위(/)부터 찾아가도록 박아줌!
                        return f'{attr}/assets/media/{filename}{quote}'
                        
                    return match.group(0)

                # src="...", href="..." 찾아내기
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