"""
인터넷/TV 상품을 위한 커스텀 필드 설정 및 데이터 파싱 명령어
"""
from django.core.management.base import BaseCommand
from api.models import Category, ProductCustomField, ProductCustomValue, Product
from api.utils.internet_parser import parse_internet_product_title


class Command(BaseCommand):
    help = '인터넷/TV 상품을 위한 커스텀 필드 설정 및 데이터 파싱'

    def handle(self, *args, **options):
        self.stdout.write('인터넷/TV 카테고리 커스텀 필드 설정 시작...')
        
        # 인터넷 및 인터넷+TV 카테고리 찾기
        internet_categories = Category.objects.filter(
            detail_type__in=['internet', 'internet_tv']
        ).distinct()
        
        if not internet_categories.exists():
            self.stdout.write(self.style.ERROR('인터넷/TV 카테고리를 찾을 수 없습니다.'))
            return
        
        # 각 카테고리에 대해 커스텀 필드 생성
        custom_fields_config = [
            {
                'field_name': 'carrier',
                'field_label': '통신사',
                'field_type': 'select',
                'is_required': True,
                'options': ['SK브로드밴드', 'KT', 'LG U+']
            },
            {
                'field_name': 'speed',
                'field_label': '인터넷 속도',
                'field_type': 'select',
                'is_required': True,
                'options': ['100M', '200M', '500M', '1G', '2.5G', '5G', '10G']
            },
            {
                'field_name': 'product_plan',
                'field_label': '상품 플랜',
                'field_type': 'text',
                'is_required': False,
                'options': []
            },
            {
                'field_name': 'has_tv',
                'field_label': 'TV 포함',
                'field_type': 'boolean',
                'is_required': True,
                'options': []
            },
            {
                'field_name': 'tv_channels',
                'field_label': 'TV 채널 정보',
                'field_type': 'text',
                'is_required': False,
                'options': []
            },
            {
                'field_name': 'subscription_type',
                'field_label': '가입 유형',
                'field_type': 'select',
                'is_required': True,
                'options': ['신규가입', '번호이동']
            },
            {
                'field_name': 'contract_period',
                'field_label': '약정 기간',
                'field_type': 'select',
                'is_required': True,
                'options': ['24개월', '36개월', '무약정']
            },
            {
                'field_name': 'monthly_fee',
                'field_label': '월 요금',
                'field_type': 'text',
                'is_required': False,
                'options': []
            },
            {
                'field_name': 'installation_fee',
                'field_label': '설치비',
                'field_type': 'text',
                'is_required': False,
                'options': []
            },
            {
                'field_name': 'gift_info',
                'field_label': '사은품 정보',
                'field_type': 'text',
                'is_required': False,
                'options': []
            },
            {
                'field_name': 'additional_benefits',
                'field_label': '추가 혜택',
                'field_type': 'text',
                'is_required': False,
                'options': []
            }
        ]
        
        # 각 카테고리에 커스텀 필드 생성
        for category in internet_categories:
            self.stdout.write(f'\n카테고리: {category.name} ({category.detail_type})')
            
            for field_config in custom_fields_config:
                field, created = ProductCustomField.objects.get_or_create(
                    category=category,
                    field_name=field_config['field_name'],
                    defaults={
                        'field_label': field_config['field_label'],
                        'field_type': field_config['field_type'],
                        'is_required': field_config['is_required'],
                        'options': field_config['options']
                    }
                )
                
                if created:
                    self.stdout.write(f'  ✓ 필드 생성: {field_config["field_label"]}')
                else:
                    # 기존 필드 업데이트
                    field.field_label = field_config['field_label']
                    field.field_type = field_config['field_type']
                    field.is_required = field_config['is_required']
                    field.options = field_config['options']
                    field.save()
                    self.stdout.write(f'  ↻ 필드 업데이트: {field_config["field_label"]}')
        
        # 이제 모든 인터넷/TV 상품의 데이터를 파싱하여 커스텀 값 저장
        self.stdout.write('\n\n상품 데이터 파싱 및 저장 시작...')
        
        products = Product.objects.filter(
            category__detail_type__in=['internet', 'internet_tv']
        )
        
        processed = 0
        for product in products:
            self.stdout.write(f'\n처리 중: {product.name}')
            
            # 상품 제목 파싱
            parsed_info = parse_internet_product_title(product.name)
            
            # 각 필드에 대해 커스텀 값 저장
            field_mappings = {
                'carrier': {
                    'type': 'text',
                    'value': self._map_carrier(parsed_info['carrier'])
                },
                'speed': {
                    'type': 'text',
                    'value': parsed_info['speed']
                },
                'product_plan': {
                    'type': 'text',
                    'value': parsed_info['product_plan']
                },
                'has_tv': {
                    'type': 'boolean',
                    'value': parsed_info['has_tv']
                },
                'tv_channels': {
                    'type': 'text',
                    'value': parsed_info['tv_channels']
                },
                'subscription_type': {
                    'type': 'text',
                    'value': '신규가입' if parsed_info['subscription_type'] == 'new' else '번호이동'
                },
                'contract_period': {
                    'type': 'text',
                    'value': '24개월'  # 기본값
                },
                'monthly_fee': {
                    'type': 'text',
                    'value': parsed_info['monthly_fee']
                },
                'installation_fee': {
                    'type': 'text',
                    'value': parsed_info.get('installation_fee', '')
                },
                'gift_info': {
                    'type': 'text',
                    'value': parsed_info['gift_info']
                },
                'additional_benefits': {
                    'type': 'text',
                    'value': parsed_info['additional_benefits']
                }
            }
            
            for field_name, field_data in field_mappings.items():
                try:
                    # 해당 필드 찾기
                    custom_field = ProductCustomField.objects.filter(
                        category=product.category,
                        field_name=field_name
                    ).first()
                    
                    if not custom_field:
                        continue
                    
                    # 커스텀 값 생성 또는 업데이트
                    custom_value, created = ProductCustomValue.objects.get_or_create(
                        product=product,
                        field=custom_field,
                        defaults={}
                    )
                    
                    # 값 타입에 따라 적절한 필드에 저장
                    if field_data['type'] == 'text':
                        custom_value.text_value = field_data['value'] or ''
                    elif field_data['type'] == 'boolean':
                        custom_value.boolean_value = field_data['value']
                    elif field_data['type'] == 'number':
                        custom_value.number_value = field_data['value']
                    
                    custom_value.save()
                    
                    if created:
                        self.stdout.write(f'    + {field_name}: {field_data["value"]}')
                    else:
                        self.stdout.write(f'    ↻ {field_name}: {field_data["value"]}')
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ! 오류 {field_name}: {str(e)}'))
            
            processed += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n\n완료! 총 {processed}개 상품 처리'))
    
    def _map_carrier(self, carrier_code):
        """통신사 코드를 한글명으로 변환"""
        mapping = {
            'SKT': 'SK브로드밴드',
            'KT': 'KT',
            'LGU': 'LG U+'
        }
        return mapping.get(carrier_code, carrier_code)