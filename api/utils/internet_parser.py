"""
인터넷/TV 상품 제목 파싱 유틸리티
"""
import re
from typing import Dict, Any


def parse_internet_product_title(title: str) -> Dict[str, Any]:
    """
    인터넷/TV 상품 제목을 파싱하여 구조화된 정보를 추출
    
    Args:
        title: 상품 제목 (예: "SK브로드밴드 기가(1G)+TV 신규가입")
    
    Returns:
        파싱된 정보를 담은 딕셔너리
    """
    result = {
        'carrier': '',
        'speed': '',
        'product_plan': '',
        'has_tv': False,
        'subscription_type': 'new',  # 기본값은 신규가입
        'tv_channels': '',
        'monthly_fee': '',
        'gift_info': '',
        'additional_benefits': '',
        'raw_product_title': title
    }
    
    title_upper = title.upper()
    
    # 통신사 추출
    if 'SK브로드밴드' in title or 'SKB' in title or 'SK인터넷' in title:
        result['carrier'] = 'SKT'
    elif 'KT인터넷' in title or 'KT ' in title or title.startswith('KT'):
        result['carrier'] = 'KT'
    elif 'LG U+' in title or 'LGU+' in title or 'U+인터넷' in title or 'LG유플러스' in title:
        result['carrier'] = 'LGU'
    
    # 속도 추출 (괄호 안의 속도 우선, 없으면 텍스트에서 찾기)
    speed_match = re.search(r'\(([0-9]+(?:\.[0-9]+)?[MG])\)', title_upper)
    if speed_match:
        speed_raw = speed_match.group(1)
        # 속도 정규화
        if '10G' in speed_raw:
            result['speed'] = '10G'
        elif '5G' in speed_raw:
            result['speed'] = '5G'
        elif '2.5G' in speed_raw:
            result['speed'] = '2.5G'
        elif '1G' in speed_raw or speed_raw == 'G':
            result['speed'] = '1G'
        elif '500M' in speed_raw:
            result['speed'] = '500M'
        elif '200M' in speed_raw:
            result['speed'] = '200M'
        elif '100M' in speed_raw:
            result['speed'] = '100M'
    else:
        # 괄호가 없는 경우 텍스트에서 속도 찾기
        if '10기가' in title or '10G' in title_upper:
            result['speed'] = '10G'
        elif '5기가' in title or '5G' in title_upper:
            result['speed'] = '5G'
        elif '2.5기가' in title or '2.5G' in title_upper:
            result['speed'] = '2.5G'
        elif '기가' in title or '1G' in title_upper:
            result['speed'] = '1G'
        elif '500메가' in title or '500M' in title_upper:
            result['speed'] = '500M'
        elif '200메가' in title or '200M' in title_upper:
            result['speed'] = '200M'
        elif '100메가' in title or '100M' in title_upper:
            result['speed'] = '100M'
    
    # 상품 플랜명 추출
    plan_keywords = {
        '기가프리미엄': '기가프리미엄',
        '기가라이트': '기가라이트',
        '기가': '기가',
        '광랜': '광랜',
        '슬림플러스': '슬림플러스',
        '슬림': '슬림',
        '베이직': '베이직',
        '에센스': '에센스',
        '스탠다드': '스탠다드',
        '프리미엄': '프리미엄'
    }
    
    for keyword, plan_name in plan_keywords.items():
        if keyword in title:
            result['product_plan'] = plan_name
            break
    
    # TV 포함 여부
    if '+TV' in title_upper or '+ TV' in title_upper or 'TV' in title_upper:
        result['has_tv'] = True
        
        # TV 채널 정보 추출 (있는 경우)
        if '프리미엄' in title and 'TV' in title_upper:
            result['tv_channels'] = '프리미엄'
        elif '기본형' in title:
            result['tv_channels'] = '기본형'
        elif re.search(r'(\d+)채널', title):
            channel_match = re.search(r'(\d+)채널', title)
            result['tv_channels'] = f'{channel_match.group(1)}채널'
    
    # 가입유형 추출
    if '신규' in title:
        result['subscription_type'] = 'new'
    elif '번호이동' in title or '통신사이동' in title or '이동' in title:
        result['subscription_type'] = 'transfer'
    
    # 월 요금 추출 (패턴: X만원, X원, X,XXX원 등)
    fee_match = re.search(r'(\d+(?:,\d{3})?)\s*원|(\d+)\s*만\s*원', title)
    if fee_match:
        if fee_match.group(1):
            result['monthly_fee'] = f'{fee_match.group(1)}원'
        elif fee_match.group(2):
            result['monthly_fee'] = f'{fee_match.group(2)}만원'
    
    # 사은품 정보 추출
    gift_keywords = ['상품권', '캐시백', '현금', '사은품', '경품']
    for keyword in gift_keywords:
        if keyword in title:
            # 사은품 관련 텍스트를 추출 (간단한 휴리스틱)
            gift_match = re.search(rf'([^,]*{keyword}[^,]*)', title)
            if gift_match:
                result['gift_info'] = gift_match.group(1).strip()
                break
    
    # 추가 혜택 추출
    benefit_keywords = ['넷플릭스', '유튜브', '와이파이', '공유기', '무료', '할인']
    benefits = []
    for keyword in benefit_keywords:
        if keyword in title:
            benefits.append(keyword)
    if benefits:
        result['additional_benefits'] = ', '.join(benefits)
    
    return result


def update_internet_detail_from_title(internet_detail, product_title: str):
    """
    GroupBuyInternetDetail 인스턴스를 상품 제목에서 파싱한 정보로 업데이트
    
    Args:
        internet_detail: GroupBuyInternetDetail 인스턴스
        product_title: 상품 제목
    """
    parsed_info = parse_internet_product_title(product_title)
    
    # 파싱된 정보로 필드 업데이트 (빈 값이 아닌 경우만)
    if parsed_info['carrier']:
        internet_detail.carrier = parsed_info['carrier']
    if parsed_info['speed']:
        internet_detail.speed = parsed_info['speed']
    if parsed_info['product_plan']:
        internet_detail.product_plan = parsed_info['product_plan']
    
    internet_detail.has_tv = parsed_info['has_tv']
    internet_detail.subscription_type = parsed_info['subscription_type']
    
    if parsed_info['tv_channels']:
        internet_detail.tv_channels = parsed_info['tv_channels']
    if parsed_info['monthly_fee']:
        internet_detail.monthly_fee = parsed_info['monthly_fee']
    if parsed_info['gift_info']:
        internet_detail.gift_info = parsed_info['gift_info']
    if parsed_info['additional_benefits']:
        internet_detail.additional_benefits = parsed_info['additional_benefits']
    
    internet_detail.raw_product_title = product_title
    
    return internet_detail