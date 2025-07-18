#!/usr/bin/env python3

"""
파일 변경 감지 및 자동 재시작 스크립트
watchdog을 사용하여 코드 변경시 자동으로 Docker 컨테이너를 재시작합니다.
"""

import os
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self, compose_file="docker-compose.prod.yml"):
        self.compose_file = compose_file
        self.last_restart = 0
        self.restart_delay = 3  # 3초 디바운싱
        
    def should_ignore(self, path):
        """무시할 파일/디렉토리 판단"""
        ignore_patterns = [
            '__pycache__',
            '.pyc',
            '.git',
            '.env',
            'mediafiles',
            'staticfiles',
            'logs',
            '.DS_Store',
            '.idea',
            '.vscode'
        ]
        return any(pattern in path for pattern in ignore_patterns)
    
    def on_modified(self, event):
        if event.is_directory:
            return
            
        if self.should_ignore(event.src_path):
            return
            
        # Python 파일이나 템플릿 파일이 변경된 경우
        if event.src_path.endswith(('.py', '.html', '.css', '.js')):
            current_time = time.time()
            
            # 디바운싱: 마지막 재시작으로부터 일정 시간이 지난 경우에만 재시작
            if current_time - self.last_restart > self.restart_delay:
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] File changed: {event.src_path}")
                print("Restarting Django application...")
                
                try:
                    # Docker 컨테이너 재시작
                    subprocess.run([
                        "docker-compose", "-f", self.compose_file, 
                        "restart", "web"
                    ], check=True)
                    
                    print("Django application restarted successfully!")
                    self.last_restart = current_time
                    
                except subprocess.CalledProcessError as e:
                    print(f"Error restarting container: {e}")

def main():
    # 스크립트 인자 처리
    compose_file = sys.argv[1] if len(sys.argv) > 1 else "docker-compose.prod.yml"
    
    # 현재 디렉토리 확인
    if not os.path.exists(compose_file):
        print(f"Error: {compose_file} not found!")
        sys.exit(1)
    
    print(f"Starting file watcher for auto-reload...")
    print(f"Using Docker Compose file: {compose_file}")
    print(f"Watching directory: {os.getcwd()}")
    print("Press Ctrl+C to stop")
    
    # 이벤트 핸들러 생성
    event_handler = CodeChangeHandler(compose_file)
    observer = Observer()
    
    # 현재 디렉토리와 하위 디렉토리 감시
    observer.schedule(event_handler, path='.', recursive=True)
    
    # 감시 시작
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping file watcher...")
    
    observer.join()

if __name__ == "__main__":
    main()