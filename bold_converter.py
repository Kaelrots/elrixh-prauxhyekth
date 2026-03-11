import os
import re

# 1. 쿼츠의 content 폴더 경로를 지정해 주세요. (예: './content')
directory = './content'

# 2. 정규표현식
# 굵은 글씨를 찾는 정규표현식 (**텍스트**)
bold_pattern = re.compile(r'\*\*(.*?)\*\*')
# 헤더 라인을 찾는 정규표현식 (공백 무시하고 #으로 시작하며 뒤에 띄어쓰기가 있는 줄)
header_pattern = re.compile(r'^\s*#+\s')

# 3. 폴더 내의 모든 .md 파일을 순회하며 변환합니다.
for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith('.md'):
            filepath = os.path.join(root, file)
            
            # 파일 읽기 (줄 단위로 읽어옵니다)
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            is_changed = False
            
            for line in lines:
                # 현재 줄이 헤더인지 확인
                if header_pattern.match(line):
                    # 헤더인 경우: **텍스트** 를 텍스트 로 변경 (** 만 삭제)
                    new_line = bold_pattern.sub(r'\1', line)
                else:
                    # 헤더가 아닌 일반 줄인 경우: <font> 태그로 변경
                    new_line = bold_pattern.sub(r'<font style="font-weight:bold">\1</font>', line)
                
                new_lines.append(new_line)
                
                # 원본 줄과 내용이 달라졌다면 변경이 일어난 것으로 체크
                if new_line != line:
                    is_changed = True
            
            # 파일 내용에 변화가 있었을 경우에만 덮어쓰기
            if is_changed:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                print(f"변환 완료: {file}")

print("모든 파일의 굵은 글씨 변환이 완료되었습니다!")