#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
법정동 코드 CSV 파일을 사용하여 Region 모델에 지역 데이터를 가져오는 스크립트
"""

import os
import sys
import csv
import django
import argparse
import glob

# Django 설정 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')

django.setup()

from api.models_region import Region

def import_regions_from_csv(csv_file_path, max_level=2):
    """
    CSV 파일에서 Region 모델로 지역 데이터를 가져옵니다.
    
    Args:
        csv_file_path: CSV 파일 경로
        max_level: 가져올 최대 레벨 (0: 시/도, 1: 시/군/구, 2: 동/읍/면)
    """
    # 지역 캐시 (code -> Region 객체)
    region_cache = {}
    
    # CSV 파일 열기
    print(f"CSV 파일 읽기: {csv_file_path}")
    with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        
        # 헤더 확인
        print(f"CSV 헤더: {reader.fieldnames}")
        
        # CSV 행 처리
        for row in reader:
            # 코드와 상위 지역 코드 가져오기
            code = row['법정동코드'].strip()
            parent_code = row['상위지역코드'].strip()
            region_name = row['법정동명'].strip()
            
            # 폐지된 지역은 건너뜀
            if row.get('폐지일') and row['폐지일'].strip():
                continue
                
            # 코드 길이로 레벨 결정
            if code.endswith('00000000'):  # 시/도 레벨
                level = 0
                full_name = region_name
            elif code.endswith('000000'):  # 시/군/구 레벨
                level = 1
                # 상위 지역이 있으면 전체 이름에 포함
                parent_region = region_cache.get(parent_code)
                if parent_region:
                    full_name = f"{parent_region.name} {region_name.split()[-1]}"
                else:
                    full_name = region_name
            else:  # 동/읍/면 레벨
                level = 2
                # 상위 지역이 있으면 전체 이름에 포함
                parent_region = region_cache.get(parent_code)
                if parent_region and parent_region.parent:
                    full_name = f"{parent_region.parent.name} {parent_region.name} {region_name.split()[-1]}"
                elif parent_region:
                    full_name = f"{parent_region.name} {region_name.split()[-1]}"
                else:
                    full_name = region_name
                
            # 최대 레벨 체크
            if level > max_level:
                continue
                
            # 이미 추가된 지역인지 확인
            if Region.objects.filter(code=code).exists():
                region = Region.objects.get(code=code)
                region_cache[code] = region
                print(f"이미 존재하는 지역: {region_name} (코드: {code}, 레벨: {level})")
                continue
                
            # 상위 지역이 있는 경우
            parent = None
            if parent_code != '0000000000' and parent_code in region_cache:
                parent = region_cache[parent_code]
            
            # 지역명에서 마지막 부분만 추출 (예: "서울특별시 강남구" -> "강남구")
            short_name = region_name.split()[-1]
            
            # Region 모델에 저장
            region = Region(
                code=code,
                name=short_name,
                full_name=full_name,
                parent=parent,
                level=level,
                is_active=True
            )
            region.save()
            region_cache[code] = region
            
            print(f"지역 추가: {region_name} (코드: {code}, 레벨: {level})")

def import_all_region_files(data_dir, max_level=1):
    """
    지정된 디렉토리에서 모든 지역 CSV 파일을 가져옵니다.
    
    Args:
        data_dir: CSV 파일이 있는 디렉토리 경로
        max_level: 가져올 최대 레벨
    """
    # 모든 CSV 파일 찾기
    csv_files = glob.glob(os.path.join(data_dir, '*_regions.csv'))
    
    if not csv_files:
        print(f"경고: {data_dir}에서 *_regions.csv 패턴의 파일을 찾을 수 없습니다.")
        # legal_codes.csv 파일이 있는지 확인
        legal_codes = os.path.join(data_dir, 'legal_codes.csv')
        if os.path.exists(legal_codes):
            csv_files = [legal_codes]
            print(f"legal_codes.csv 파일을 사용합니다: {legal_codes}")
    
    # 각 파일 처리
    for csv_file in sorted(csv_files):
        print(f"\n처리 중: {os.path.basename(csv_file)}")
        import_regions_from_csv(csv_file, max_level)
    
    print(f"\n총 {Region.objects.count()}개의 지역이 데이터베이스에 있습니다.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='법정동 코드 CSV 파일에서 Region 모델로 데이터를 가져옵니다.')
    parser.add_argument('--csv', help='단일 CSV 파일 경로')
    parser.add_argument('--data-dir', help='여러 CSV 파일이 있는 디렉토리 경로')
    parser.add_argument('--max-level', type=int, default=1, help='가져올 최대 레벨 (0: 시/도, 1: 시/군/구, 2: 동/읍/면)')
    
    args = parser.parse_args()
    
    if args.csv:
        import_regions_from_csv(args.csv, args.max_level)
    elif args.data_dir:
        import_all_region_files(args.data_dir, args.max_level)
    else:
        # 기본값으로 현재 디렉토리의 상위 data 디렉토리 사용
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        print(f"CSV 파일 경로나 데이터 디렉토리가 지정되지 않았습니다. 기본 경로 사용: {data_dir}")
        import_all_region_files(data_dir, args.max_level)
    print("완료: Region 모델에 지역 데이터가 추가되었습니다.")
    
    # Region 모델 확인
    regions_count = Region.objects.count()
    print(f"Region 모델에 총 {regions_count}개의 지역이 있습니다.")
