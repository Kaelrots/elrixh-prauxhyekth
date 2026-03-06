import os
import re
import urllib.parse

# 1. 경로 설정
vault_path = r"./content"

def master_link_fixer():
    exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp3', '.mp4')
    print("--- [궁극의 해결책] 마크다운 이미지 절대경로 주입 및 표 링크 보정 시작 ---")
    
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
                    
                    # 1. 외부 링크 무시
                    if url_part.lower().startswith("http"):
                        return match.group(0)

                    # 2. 미디어(이미지) 파일인 경우
                    if any(ext in url_part.lower() for ext in exts):
                        
                        # 🔥 수정된 핵심 포인트: 파이프(|)로 크기 조절 옵션 분리
                        img_size = ""
                        if '|' in url_part:
                            base_url, img_size = url_part.split('|', 1)
                        else:
                            base_url = url_part

                        # 앞에 무슨 경로가 붙어있든 싹둑 자르고 순수 파일명만 추출
                        filename = base_url.split('/')[-1]
                        filename = urllib.parse.unquote(filename).replace('+', ' ')
                        filename = re.sub(r'\s+', '-', filename.strip())
                        
                        # HTML 태그인 경우 깃허브가 무조건 찾을 수 있게 절대경로 주입
                        if prefix in ('src="', 'href="'):
                            return f'{prefix}/assets/media/{filename}{suffix}'
                            
                        # 🔥 옵시디언 고유 문법(![[ ]])인 경우 HTML <img> 태그로 완전 변환! (표 깨짐 원천 차단)
                        elif prefix == '![[':
                            if img_size:
                                return f'<img src="/assets/media/{filename}" width="{img_size}">'
                            else:
                                return f'<img src="/assets/media/{filename}">'
                                
                        # 일반 링크([[ ]])인 경우
                        else:
                            return f'{prefix}{filename}{suffix}'

                    # 3. 미디어가 아닌 경우 (표 안의 문서 링크 등)
                    if prefix == 'href="':
                        new_url = url_part
                        # kael/ 잉여 경로가 있으면 제거
                        if new_url.startswith('/kael/'): new_url = new_url[6:]
                        elif new_url.startswith('kael/'): new_url = new_url[5:]
                        
                        # 최상위 경로(/) 강제 부여하여 404 방지
                        if not new_url.startswith('/') and not new_url.startswith('#'):
                            new_url = '/' + new_url
                        
                        new_url = new_url.replace('+', ' ')
                        new_url = re.sub(r'\s+', '-', new_url.strip())
                        return f'{prefix}{new_url}{suffix}'
                        
                    return match.group(0)

                # 규칙 1: Obsidian 문법 [[ ]] 또는 ![[ ]]
                content = re.sub(r'(!?\[\[)(.*?)(\]\])', clean_url, content)
                
                # 규칙 2: HTML 문법 href="..." 또는 src="..."
                content = re.sub(r'(href="|src=")(.*?)(")', clean_url, content)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

    print("--- 마크다운 내 이미지 및 링크 경로 완벽 수정 완료! ---")

if __name__ == "__main__":
    master_link_fixer()