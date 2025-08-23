"""
인터넷/TV 상품의 속도 정보만 관리하는 간소화된 커스텀 필드 설정
"""
from django.core.management.base import BaseCommand
from api.models import Category, ProductCustomField, ProductCustomValue, Product
from api.utils.internet_speed_parser import extract_speed_from_title, has_tv_in_title


class Command(BaseCommand):
    help = '인터넷/TV 상품의 속도 정보 커스텀 필드 설정'

    def handle(self, *args, **options):
        self.stdout.write('인터넷/TV 속도 커스텀 필드 설정 시작...')
        
        # 인터넷 및 인터넷+TV 카테고리 찾기
        internet_categories = Category.objects.filter(
            detail_type__in=['internet', 'internet_tv']
        ).distinct()
        
        if not internet_categories.exists():
            self.stdout.write(self.style.ERROR('인터넷/TV 카테고리를 찾을 수 없습니다.'))
            return
        
        # 기존 불필요한 커스텀 필드 삭제
        self.stdout.write('\n기존 불필요한 커스텀 필드 정리...')
        unnecessary_fields = [
            'carrier',  # 통신사는 공구 등록 시 선택
            'subscription_type',  # 가입유형은 공구 등록 시 선택
            'product_plan',  # 상품 플랜명 불필요
            'tv_channels',  # TV 채널 정보 불필요
            'contract_period',  # 약정기간 불필요
            'monthly_fee',  # 월 요금 불필요
            'installation_fee',  # 설치비 불필요
            'gift_info',  # 사은품 정보 불필요
            'additional_benefits',  # 추가 혜택 불필요
        ]
        
        for category in internet_categories:
            deleted_count = ProductCustomField.objects.filter(
                category=category,
                field_name__in=unnecessary_fields
            ).delete()[0]
            
            if deleted_count > 0:
                self.stdout.write(f'  - {category.name}: {deleted_count}개 필드 삭제')
        
        # 속도와 TV 포함 여부 필드만 생성/업데이트
        self.stdout.write('\n필수 커스텀 필드 설정...')
        
        for category in internet_categories:
            self.stdout.write(f'\n카테고리: {category.name} ({category.detail_type})')
            
            # 속도 필드
            speed_field, created = ProductCustomField.objects.get_or_create(
                category=category,
                field_name='speed',
                defaults={
                    'field_label': '인터넷 속도',
                    'field_type': 'select',
                    'is_required': True,
                    'options': ['100M', '200M', '500M', '1G', '2.5G', '5G', '10G']
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ 필드 생성: 인터넷 속도')
            else:
                self.stdout.write(f'  ↻ 필드 유지: 인터넷 속도')
            
            # TV 포함 여부 필드
            tv_field, created = ProductCustomField.objects.get_or_create(
                category=category,
                field_name='has_tv',
                defaults={
                    'field_label': 'TV 포함',
                    'field_type': 'boolean',
                    'is_required': True,
                    'options': []
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ 필드 생성: TV 포함')
            else:
                self.stdout.write(f'  ↻ 필드 유지: TV 포함')
        
        # 모든 인터넷/TV 상품의 속도 정보 추출 및 저장
        self.stdout.write('\n\n상품 속도 정보 추출 및 저장...')
        
        products = Product.objects.filter(
            category__detail_type__in=['internet', 'internet_tv']
        )
        
        processed = 0
        for product in products:
            # 속도 추출
            speed = extract_speed_from_title(product.name)
            has_tv = has_tv_in_title(product.name)
            
            self.stdout.write(f'\n{product.name}')
            self.stdout.write(f'  → 속도: {speed if speed else "없음"}')
            self.stdout.write(f'  → TV: {"포함" if has_tv else "미포함"}')
            
            # 속도 필드 값 저장
            if speed:
                speed_field = ProductCustomField.objects.filter(
                    category=product.category,
                    field_name='speed'
                ).first()
                
                if speed_field:
                    custom_value, created = ProductCustomValue.objects.get_or_create(
                        product=product,
                        field=speed_field,
                        defaults={'text_value': speed}
                    )
                    
                    if not created:
                        custom_value.text_value = speed
                        custom_value.save()
            
            # TV 포함 여부 저장
            tv_field = ProductCustomField.objects.filter(
                category=product.category,
                field_name='has_tv'
            ).first()
            
            if tv_field:
                custom_value, created = ProductCustomValue.objects.get_or_create(
                    product=product,
                    field=tv_field,
                    defaults={'boolean_value': has_tv}
                )
                
                if not created:
                    custom_value.boolean_value = has_tv
                    custom_value.save()
            
            processed += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n\n완료! 총 {processed}개 상품 처리'))
        self.stdout.write('\n정리 결과:')
        self.stdout.write('  - 상품별 저장 데이터: 속도(괄호 안 값), TV 포함 여부')
        self.stdout.write('  - 공구 등록 시 선택: 통신사, 가입유형')
        self.stdout.write('  - GroupBuyInternetDetail: 통신사, 가입유형 저장')
        self.stdout.write('  - ProductCustomValue: 속도만 저장')