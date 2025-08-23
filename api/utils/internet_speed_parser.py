"""
인터넷/TV 상품 속도 추출 유틸리티
"""
import re


def extract_speed_from_title(title: str) -> str:
    """
    상품 제목의 괄호 안에서 속도 정보만 추출
    괄호가 없는 경우 텍스트에서 속도 패턴 찾기
    
    Args:
        title: 상품 제목 (예: "KT인터넷 기가(1G)" 또는 "SK브로드밴드 500M 신규")
    
    Returns:
        속도 값 (예: "1G") 또는 빈 문자열
    """
    title_upper = title.upper()
    
    # 1. 먼저 괄호 안의 속도 정보 추출 (예: (100M), (1G), (2.5G))
    match = re.search(r'\(([0-9]+(?:\.[0-9]+)?[MG])\)', title_upper)
    
    if match:
        speed = match.group(1)
    else:
        # 2. 괄호가 없는 경우 공백으로 구분된 속도 패턴 찾기
        match = re.search(r'\b([0-9]+(?:\.[0-9]+)?[MG])\b', title_upper)
        if match:
            speed = match.group(1)
        else:
            return ''
    
    # 속도 값 정규화 (순서 중요: 더 구체적인 값부터 체크)
    if '10G' in speed:
        return '10G'
    elif '2.5G' in speed:
        return '2.5G'
    elif '5G' in speed:
        return '5G'
    elif '1G' in speed:
        return '1G'
    elif '500M' in speed:
        return '500M'
    elif '200M' in speed:
        return '200M'
    elif '100M' in speed:
        return '100M'
    else:
        return speed


def has_tv_in_title(title: str) -> bool:
    """
    상품 제목에 TV가 포함되어 있는지 확인
    
    Args:
        title: 상품 제목
    
    Returns:
        TV 포함 여부
    """
    return '+TV' in title.upper() or '+ TV' in title.upper()