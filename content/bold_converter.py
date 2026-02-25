import os
import re

# 1. 쿼츠의 content 폴더 경로를 지정해 주세요. (예: './content')
directory = './content'

# 2. 정규표현식: **텍스트** 를 찾아서 <font style="font-weight:bold">텍스트</font> 로 변경합니다.
pattern = re.compile(r'\*\*(.*?)\*\*')

# 3. 폴더 내의 모든 .md 파일을 순회하며 변환합니다.
for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith('.md'):
            filepath = os.path.join(root, file)
            
            # 파일 읽기
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 정규표현식을 이용한 치환
            new_content = pattern.sub(r'<font style="font-weight:bold">\1</font>', content)
            
            # 기존 내용과 다를 경우에만 덮어쓰기
            if content != new_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"변환 완료: {file}")

print("모든 파일의 굵은 글씨 변환이 완료되었습니다!")