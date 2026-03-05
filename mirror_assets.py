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
    print("--- 1. 미디어 파일 양방향 수집 시작 (원본 폴더 보호 패치) ---")
    
    count = 0
    # 무시할 정확한 '목적지' 폴더 경로 생성 (content/assets/media)
    ignore_target_path = os.path.join(content_dir, media_dir_name).lower()
    
    for root, dirs, files in os.walk(content_dir):
        root_lower = root.lower()
        
        # 🚨 [핵심 수정] 이름에 'assets'가 있다고 무조건 거르는 게 아니라,
        # 우리가 파일을 복사해 넣을 '목적지 폴더(content/assets/media)'만 정확히 건너뜁니다.
        # 이렇게 해야 원본 'content/Assets' 폴더의 이미지가 정상적으로 복사됩니다.
        if ignore_target_path in root_lower:
            continue
            
        # public 폴더는 건너뜀
        if "public" in root_lower:
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

    # 2단계: HTML 링크 교정 (스마트 경로 훔치기 전략 유지)
    print("--- 2. 웹사이트(HTML) 스마트 상대경로 교정 시작 ---")
    html_count = 0
    for root, dirs, files in os.walk(public_dir):
        for file in files:
            if file.endswith(".html"):
                html_path = os.path.join(root, file)
                
                with open(html_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Quartz가 생성한 index.css의 경로를 훔쳐서 이미지 경로에 적용
                root_prefix = "./"
                css_match = re.search(r'href="([^"]*?)index\.css"', content)
                if css_match:
                    root_prefix = css_match.group(1)

                prefix = f"{root_prefix}assets/media/"

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
    print(f"--- 총 {html_count}개의 HTML 파일 스마트 경로 보정 완료! ---")

if __name__ == "__main__":
    master_sync()