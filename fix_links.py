import os
import re

# 1. 경로 설정 (퍼블리시용 복사본 content 폴더)
vault_path = r"./content"

def master_link_fixer():
    print("--- [업데이트] 표 내부 HTML 링크 절대경로(/) 강제 보정 시작 ---")
    
    link_fix_count = 0
    for root, dirs, files in os.walk(vault_path):
        for name in files:
            if name.endswith(".md"):
                file_path = os.path.join(root, name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                def clean_url(match):
                    prefix = match.group(1) # ![[ , [[ , href=" , src="
                    url_part = match.group(2) # 실제 파일 경로/이름
                    suffix = match.group(3) # ]] , "
                    
                    # 1. 외부 인터넷 링크는 무시
                    if url_part.lower().startswith('http://') or url_part.lower().startswith('https://'):
                        return match.group(0)

                    # 2. 앵커 링크(#문단) 단독 사용 시 무시
                    if url_part.startswith('#'):
                        return match.group(0)

                    # 🚨 [핵심] 표 내부의 HTML href 링크만 타겟팅하여 절대경로로 멱살 잡기
                    if prefix == 'href="':
                        # 미디어 파일(.png 등)은 mirror_assets.py가 처리하므로 건드리지 않음
                        exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp3', '.mp4')
                        if not any(ext in url_part.lower() for ext in exts):
                            # 혹시라도 kael/ 이 이미 적혀있다면 싹둑 자름
                            if url_part.startswith('/kael/'):
                                url_part = url_part[6:]
                            elif url_part.startswith('kael/'):
                                url_part = url_part[5:]
                            
                            # 브라우저가 현재 폴더(/kael/)를 덧붙이지 못하도록 최상위 경로(/) 강제 주입
                            if not url_part.startswith('/'):
                                url_part = '/' + url_part

                    # 3. 옵시디언 별칭(|) 분리 보호
                    parts = url_part.split('|', 1)
                    path_and_anchor = parts[0]
                    alias = f"|{parts[1]}" if len(parts) > 1 else ""

                    # 4. 해시(#) 앵커 분리 보호
                    pa_parts = path_and_anchor.split('#', 1)
                    target_path = pa_parts[0]
                    anchor = f"#{pa_parts[1]}" if len(pa_parts) > 1 else ""

                    # 5. 경로 부분의 공백만 쿼츠 규칙에 맞게 하이픈(-)으로 변환
                    if target_path:
                        new_path = target_path.rstrip('/')
                        new_path = new_path.replace('+', ' ')
                        new_path = re.sub(r'\s+', '-', new_path.strip())
                    else:
                        new_path = ""
                    
                    new_url_part = f"{new_path}{anchor}{alias}"
                    return f"{prefix}{new_url_part}{suffix}"

                # 규칙 1: Obsidian 문법 [[ ]] 또는 ![[ ]]
                content = re.sub(r'(!?\[\[)(.*?)(\]\])', clean_url, content)
                
                # 규칙 2: HTML 문법 href="..." 또는 src="..."
                content = re.sub(r'(href="|src=")(.*?)(")', clean_url, content)

                # 파일 내용이 변경되었을 때만 덮어쓰기
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    link_fix_count += 1

    print(f"--- 완료: 총 {link_fix_count}개 문서의 표/HTML 링크 경로 보정 성공! ---")

if __name__ == "__main__":
    master_link_fixer()