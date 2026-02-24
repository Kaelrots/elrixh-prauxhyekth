import os
import re

# 1. 경로 설정 (카엘님의 실제 경로)
vault_path = r"C:\구글 드라이브\세계관_Publish"

def master_link_fixer():
    # 처리할 미디어 확장자
    exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp3', '.mp4')
    
    print("--- [최종] HTML 표 및 모든 링크 하이픈(-) 대통합 시작 ---")
    
    for root, dirs, files in os.walk(vault_path):
        for name in files:
            if name.endswith(".md"):
                file_path = os.path.join(root, name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                def clean_url(match):
                    prefix = match.group(1) # ![[ , [[ , href=" , src="
                    url_part = match.group(2) # 실제 파일 경로/이름
                    suffix = match.group(3) # ]] , "
                    
                    # 확장자가 포함된 경우에만 변환 수행
                    if any(ext in url_part.lower() for ext in exts):
                        # 1. 경로 끝의 '/' 제거 (가장 중요: 4fda7d 에러 해결)
                        new_url = url_part.rstrip('/')
                        # 2. '+' 기호를 공백으로 변경 후, 모든 공백을 하이픈(-)으로 통합
                        new_url = new_url.replace('+', ' ')
                        new_url = re.sub(r'\s+', '-', new_url.strip())
                        
                        return f"{prefix}{new_url}{suffix}"
                    return match.group(0)

                # 규칙 1: Obsidian 문법 [[ ]] 또는 ![[ ]]
                content = re.sub(r'(!?\[\[)(.*?)(\]\])', clean_url, content)
                
                # 규칙 2: HTML 문법 href="..." 또는 src="..." (표 내부 해결)
                content = re.sub(r'(href="|src=")(.*?)(")', clean_url, content)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

    print("--- 모든 문서의 링크가 하이픈(-) 체계로 완벽히 수정되었습니다! ---")

if __name__ == "__main__":
    master_link_fixer()