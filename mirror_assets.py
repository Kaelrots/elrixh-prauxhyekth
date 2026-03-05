import os
import shutil
import time

# 경로 설정
content_dir = "content"
# 복사될 목적지 폴더 (여기만 피하면 됨)
media_dir_name = os.path.join("assets", "media")
target_dir = os.path.join(content_dir, media_dir_name)

def master_sync():
    # 목적지 폴더가 없으면 생성
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp3', '.mp4')
    print("--- [수정됨] 미디어 파일 중앙 집중화 (원본 Assets 폴더 인식 가능) ---")
    
    count = 0
    # 무시해야 할 '결과물 폴더'의 절대 경로
    abs_target_dir = os.path.abspath(target_dir).lower()
    
    for root, dirs, files in os.walk(content_dir):
        # 현재 탐색 중인 폴더의 절대 경로
        abs_root = os.path.abspath(root).lower()
        
        # 🚨 핵심 수정: 이름에 'assets'가 있다고 무조건 거르는 게 아니라,
        # '복사 목적지 폴더' 그 자체일 때만 건너뜁니다.
        # 이제 원본 'Assets' 폴더는 무시되지 않고 정상적으로 복사됩니다.
        if abs_root == abs_target_dir:
            continue
            
        # public 폴더는 건너뜀 (이미 생성된 웹사이트 파일이므로)
        if "public" in os.path.relpath(root, content_dir).lower().split(os.sep):
            continue
            
        for file in files:
            if file.lower().endswith(exts):
                source_path = os.path.join(root, file)
                # 파일명에 공백이 있으면 하이픈으로 변경
                safe_name = file.replace(" ", "-")
                dest_path = os.path.join(target_dir, safe_name)
                
                try:
                    shutil.copy(source_path, dest_path)
                    count += 1
                except shutil.SameFileError:
                    pass
                except PermissionError:
                    time.sleep(0.3)
                    try:
                        shutil.copy(source_path, dest_path)
                        count += 1
                    except:
                        pass
                        
    print(f"--- 총 {count}개의 미디어 파일이 성공적으로 중앙 폴더에 모였습니다! ---")

if __name__ == "__main__":
    master_sync()