import os
import re

# 1. 경로 설정 (content 폴더)
vault_path = r"./content"

def master_link_fixer():
    print("--- [업데이트] 모든 링크(미디어+문서) 공백을 하이픈(-)으로 변환 시작 ---")
    
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
                    
                    # 1. 외부 링크(웹사이트 주소)는 변환하지 않고 그대로 패스
                    if url_part.lower().startswith('http://') or url_part.lower().startswith('https://'):
                        return match.group(0)

                    # 2. 옵시디언 파이프(|) 별칭 분리 (별칭 부분은 하이픈 변환에서 제외)
                    parts = url_part.split('|')
                    path_and_anchor = parts[0]
                    alias = f"|{parts[1]}" if len(parts) > 1 else ""

                    # 3. 해시(#) 앵커 분리 (문단 이동 링크 보호)
                    pa_parts = path_and_anchor.split('#')
                    target_path = pa_parts[0]
                    anchor = f"#{pa_parts[1]}" if len(pa_parts) > 1 else ""

                    # 4. 파일/문서 경로 부분만 공백을 하이픈(-)으로 변환
                    new_path = target_path.rstrip('/')
                    new_path = new_path.replace('+', ' ')
                    new_path = re.sub(r'\s+', '-', new_path.strip())
                    
                    # 다시 조립
                    new_url_part = f"{new_path}{anchor}{alias}"
                    return f"{prefix}{new_url_part}{suffix}"

                # 규칙 1: Obsidian 문법 [[ ]] 또는 ![[ ]]
                content = re.sub(r'(!?\[\[)(.*?)(\]\])', clean_url, content)
                
                # 규칙 2: HTML 문법 href="..." 또는 src="..."
                content = re.sub(r'(href="|src=")(.*?)(")', clean_url, content)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

    print("--- 일반 문서 인링크 및 a href를 포함한 모든 링크 변환 완료! ---")

if __name__ == "__main__":
    master_link_fixer()