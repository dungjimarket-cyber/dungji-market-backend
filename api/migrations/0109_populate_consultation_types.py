# Generated manually - 상담 유형 초기 데이터

from django.db import migrations


# 업종별 상담 유형 데이터
CONSULTATION_TYPES_DATA = {
    '세무사': [
        ('종합소득세 신고', '📊', '개인사업자, 프리랜서 소득세 신고 대행'),
        ('부가세 신고', '📋', '부가가치세 신고 및 환급'),
        ('기장 대행', '📝', '월별 세무 기장 및 장부 관리'),
        ('절세 상담', '💰', '합법적 절세 방법 상담'),
        ('법인 설립', '🏢', '개인→법인 전환, 법인 설립 절차'),
    ],
    '회계사': [
        ('재무 상담', '📈', '재무제표 분석 및 경영 상담'),
        ('회계 감사', '🔍', '외부/내부 회계 감사'),
        ('결산 신고', '📅', '연간 결산 및 법인세 신고'),
        ('급여/4대보험', '💳', '급여 책정 및 4대보험 관리'),
    ],
    '변호사': [
        ('계약 검토', '📄', '각종 계약서 법적 검토'),
        ('소송 상담', '⚖️', '민사/형사 소송 상담'),
        ('노동 분쟁', '👔', '해고, 임금체불 등 노무 문제'),
        ('채권 추심', '💵', '미수금, 외상금 법적 처리'),
        ('법률 자문', '📚', '기업 및 개인 법률 자문'),
    ],
    '법무사': [
        ('부동산 등기', '🏠', '소유권, 담보권 등기'),
        ('법인 등기', '🏛️', '회사 설립, 임원 변경 등기'),
        ('인허가 서류', '📑', '사업 인허가 신청 서류'),
        ('공정증서', '✍️', '금전차용, 계약서 공정증서'),
    ],
    '공인중개사': [
        ('매매 상담', '🏘️', '주택/상가 매매 중개'),
        ('전세/월세', '🔑', '임대차 계약 상담'),
        ('권리금 상담', '💼', '점포 권리금 평가 및 계약'),
        ('투자 상담', '📊', '부동산 투자 수익성 분석'),
    ],
    '인테리어': [
        ('주거 인테리어', '🛋️', '아파트, 주택 인테리어'),
        ('상업 공간', '🏪', '카페, 음식점, 사무실'),
        ('리모델링', '🔨', '노후 건물 리모델링'),
        ('시공 견적', '📝', '공사비 견적 상담'),
    ],
    '청소 전문': [
        ('입주 청소', '🧹', '새집 입주 전 청소'),
        ('이사 청소', '📦', '이사 전후 청소'),
        ('정기 청소', '🗓️', '주간/월간 정기 청소'),
        ('특수 청소', '✨', '에어컨, 세탁기, 소독'),
    ],
    '이사 전문': [
        ('가정 이사', '🏡', '가정집 이사'),
        ('사무실 이전', '🏢', '사무실/상가 이전'),
        ('포장 이사', '📦', '전문 포장 이사'),
        ('견적 상담', '💰', '이사 비용 견적'),
    ],
    '휴대폰 대리점': [
        ('개통 상담', '📱', '신규 가입, 번호이동'),
        ('요금제 상담', '💳', '요금제 변경, 비교'),
        ('기기 상담', '📲', '최신 기기 추천'),
    ],
    '자동차 정비': [
        ('정기 점검', '🔧', '엔진오일, 타이어 등'),
        ('수리 견적', '🛠️', '고장 수리 견적'),
        ('사고 수리', '🚗', '사고 차량 수리'),
    ],
}


def populate_consultation_types(apps, schema_editor):
    """상담 유형 초기 데이터 생성"""
    LocalBusinessCategory = apps.get_model('api', 'LocalBusinessCategory')
    ConsultationType = apps.get_model('api', 'ConsultationType')

    for category_name, types in CONSULTATION_TYPES_DATA.items():
        try:
            category = LocalBusinessCategory.objects.get(name=category_name)
        except LocalBusinessCategory.DoesNotExist:
            print(f'카테고리 "{category_name}" 없음 - 건너뜀')
            continue

        for idx, (type_name, icon, description) in enumerate(types):
            ConsultationType.objects.update_or_create(
                category=category,
                name=type_name,
                defaults={
                    'icon': icon,
                    'description': description,
                    'order_index': idx,
                    'is_active': True,
                }
            )

    print('상담 유형 초기 데이터 생성 완료')


def reverse_populate(apps, schema_editor):
    """롤백 시 데이터 삭제"""
    ConsultationType = apps.get_model('api', 'ConsultationType')
    ConsultationType.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0108_consultation_models'),
    ]

    operations = [
        migrations.RunPython(populate_consultation_types, reverse_populate),
    ]
