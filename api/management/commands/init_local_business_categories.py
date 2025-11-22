"""
지역 업체 카테고리 초기 데이터 생성
"""
from django.core.management.base import BaseCommand
from api.models import LocalBusinessCategory


class Command(BaseCommand):
    help = '지역 업체 카테고리 초기 데이터 생성'

    def handle(self, *args, **options):
        """초기 카테고리 데이터 생성"""
        self.stdout.write(self.style.SUCCESS('=== 업종 카테고리 초기화 시작 ===\n'))

        categories = [
            {
                'name': '회계사',
                'name_en': 'accountant',
                'icon': '💼',
                'google_place_type': 'accounting',
                'description': '회계 감사, 재무 상담, 회계 처리 등 회계 전문 서비스',
                'order_index': 1
            },
            {
                'name': '세무사',
                'name_en': 'tax accountant office',
                'icon': '💼',
                'google_place_type': 'accounting',
                'description': '세무 신고, 세무 상담, 세무 조정 등 세무 관련 전문 서비스',
                'order_index': 2
            },
            {
                'name': '법무사',
                'name_en': 'judicial scrivener office',
                'icon': '📋',
                'google_place_type': 'legal',
                'description': '등기, 인허가, 법률 문서 작성 등 법무 전문 서비스',
                'order_index': 3
            },
            {
                'name': '변호사',
                'name_en': 'law firm',
                'icon': '⚖️',
                'google_place_type': 'lawyer',
                'description': '법률 상담, 소송 대리, 계약서 작성 등 법률 전문 서비스',
                'order_index': 4
            },
            {
                'name': '공인중개사',
                'name_en': 'real estate agency',
                'icon': '🏠',
                'google_place_type': 'real_estate_agency',
                'description': '부동산 매매, 임대차, 중개 등 부동산 거래 전문 서비스',
                'order_index': 5
            },
            {
                'name': '인테리어',
                'name_en': 'interior design',
                'icon': '🛠️',
                'google_place_type': 'interior_designer',
                'description': '주거 및 상업 공간 인테리어 설계 및 시공',
                'order_index': 6
            },
            {
                'name': '휴대폰 대리점',
                'name_en': 'mobile phone store',
                'icon': '📱',
                'google_place_type': 'cell_phone_store',
                'description': '휴대폰 개통, 요금제 상담, 단말기 판매',
                'order_index': 7
            },
            {
                'name': '정비소',
                'name_en': 'auto repair shop',
                'icon': '🔧',
                'google_place_type': 'car_repair',
                'description': '자동차 정비, 수리, 점검 등 차량 관리 서비스',
                'order_index': 8
            },
        ]

        created_count = 0
        updated_count = 0

        for cat_data in categories:
            category, created = LocalBusinessCategory.objects.update_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ 생성: {category}"))
            else:
                updated_count += 1
                self.stdout.write(f"  ↻ 업데이트: {category}")

        self.stdout.write(self.style.SUCCESS(
            f"\n=== 완료: 생성 {created_count}개, 업데이트 {updated_count}개 ==="
        ))
