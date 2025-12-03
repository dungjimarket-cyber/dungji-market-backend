"""
exe 빌드 스크립트
실행: python build_exe.py
"""

import subprocess
import sys
import os

def install_requirements():
    """필요한 패키지 설치"""
    packages = [
        'selenium',
        'webdriver-manager',
        'pandas',
        'openpyxl',
        'pyinstaller'
    ]

    for pkg in packages:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])

def build_exe():
    """exe 빌드"""
    print("\n=== Building EXE ===\n")

    # PyInstaller 명령
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=둥지마켓_크롤러',
        '--onefile',           # 단일 exe 파일
        '--windowed',          # 콘솔 창 숨김 (GUI 앱)
        '--noconfirm',         # 기존 빌드 덮어쓰기
        '--clean',             # 빌드 전 정리
        'crawler_gui.py'
    ]

    subprocess.check_call(cmd)

    print("\n=== Build Complete ===")
    print("exe 파일 위치: dist/둥지마켓_크롤러.exe")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("1. 패키지 설치 중...")
    install_requirements()

    print("\n2. exe 빌드 중...")
    build_exe()
