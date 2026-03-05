import os
import shutil
import time

content_dir = "content"
media_dir_name = os.path.join("assets", "media")
target_dir = os.path.join(content_dir, media_dir_name)

def master_sync():
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp3', '.mp4')
    print("--- 미디어 파일 중앙 집중화 복사 시작 (가볍고 빠른 버전) ---")
    
    count = 0
    ignore_target_path = target_dir.lower()
    
    for root, dirs, files in os.walk(content_dir):
        root_lower = root.lower()
        
        # 우리가 파일을 모아둘 목적지 폴더만 무시 (무한 복제 방지)
        if ignore_target_path in root_lower:
            continue
            
        for file in files:
            if file.lower().endswith(exts):
                source_path = os.path.join(root, file)
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