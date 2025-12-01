# Generated migration for fixing realtor consultation flows
# 공인중개사 플로우를 거래유형+매물유형 구조로 개선
# 참고: 직방, 다방, 네이버부동산 등 실제 플랫폼 분석 (2024)

from django.db import migrations


# 새로운 공인중개사 플로우 데이터
REALTOR_FLOWS = [
    # Step 1: 목적 + 거래유형 통합
    {
        'step_number': 1,
        'question': '어떤 도움이 필요하세요?',
        'depends_on_step': None,
        'depends_on_options': [],
        'options': [
            {'key': 'buy', 'label': '집 사기 (매매)', 'icon': '🏠', 'description': '내 집 마련'},
            {'key': 'jeonse', 'label': '전세 구하기', 'icon': '📋', 'description': '전세로 들어갈 집'},
            {'key': 'monthly', 'label': '월세 구하기', 'icon': '💵', 'description': '월세로 들어갈 집'},
            {'key': 'sell', 'label': '집 팔기 (매매)', 'icon': '💰', 'description': '소유한 집 매도'},
            {'key': 'lease_out', 'label': '세입자 구하기', 'icon': '🔑', 'description': '전세/월세 세입자 모집'},
            {'key': 'commercial_find', 'label': '상가/사무실 구하기', 'icon': '🏢', 'description': '임대 또는 매매'},
            {'key': 'commercial_list', 'label': '상가/사무실 내놓기', 'icon': '🏪', 'description': '임대 또는 매매'},
            {'key': 'consulting', 'label': '부동산 상담만', 'icon': '💬', 'description': '시세, 투자, 세금 등'},
        ]
    },
    # Step 2: 매물 유형 - 주거용 구하기 (buy, jeonse, monthly)
    {
        'step_number': 2,
        'question': '어떤 매물을 찾으세요?',
        'depends_on_step': 1,
        'depends_on_options': ['buy', 'jeonse', 'monthly'],
        'options': [
            {'key': 'apt', 'label': '아파트', 'icon': '🏢'},
            {'key': 'officetel', 'label': '오피스텔', 'icon': '🏙️'},
            {'key': 'villa', 'label': '빌라/연립/다세대', 'icon': '🏠'},
            {'key': 'house', 'label': '단독/다가구/전원주택', 'icon': '🏡'},
            {'key': 'room', 'label': '원룸/투룸', 'icon': '🛏️'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # Step 2: 매물 유형 - 주거용 내놓기 (sell, lease_out)
    {
        'step_number': 2,
        'question': '어떤 매물을 내놓으세요?',
        'depends_on_step': 1,
        'depends_on_options': ['sell', 'lease_out'],
        'options': [
            {'key': 'apt', 'label': '아파트', 'icon': '🏢'},
            {'key': 'officetel', 'label': '오피스텔', 'icon': '🏙️'},
            {'key': 'villa', 'label': '빌라/연립/다세대', 'icon': '🏠'},
            {'key': 'house', 'label': '단독/다가구/전원주택', 'icon': '🏡'},
            {'key': 'room', 'label': '원룸/투룸', 'icon': '🛏️'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # Step 2: 상업용 - 구하기 (commercial_find)
    {
        'step_number': 2,
        'question': '어떤 매물을 찾으세요?',
        'depends_on_step': 1,
        'depends_on_options': ['commercial_find'],
        'options': [
            {'key': 'store', 'label': '상가/점포', 'icon': '🏪'},
            {'key': 'office', 'label': '사무실', 'icon': '💼'},
            {'key': 'building', 'label': '건물 전체', 'icon': '🏢'},
            {'key': 'factory', 'label': '공장/창고', 'icon': '🏭'},
            {'key': 'land', 'label': '토지', 'icon': '🌳'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # Step 2: 상업용 - 내놓기 (commercial_list)
    {
        'step_number': 2,
        'question': '어떤 매물을 내놓으세요?',
        'depends_on_step': 1,
        'depends_on_options': ['commercial_list'],
        'options': [
            {'key': 'store', 'label': '상가/점포', 'icon': '🏪'},
            {'key': 'office', 'label': '사무실', 'icon': '💼'},
            {'key': 'building', 'label': '건물 전체', 'icon': '🏢'},
            {'key': 'factory', 'label': '공장/창고', 'icon': '🏭'},
            {'key': 'land', 'label': '토지', 'icon': '🌳'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # Step 2: 상담 유형 (consulting)
    {
        'step_number': 2,
        'question': '어떤 상담이 필요하세요?',
        'depends_on_step': 1,
        'depends_on_options': ['consulting'],
        'options': [
            {'key': 'price', 'label': '시세/가격 문의', 'icon': '💰', 'description': '우리 집 얼마?'},
            {'key': 'investment', 'label': '투자 상담', 'icon': '📈', 'description': '수익형/갭투자 등'},
            {'key': 'tax', 'label': '세금 관련', 'icon': '🧾', 'description': '양도세, 취득세 등'},
            {'key': 'legal', 'label': '계약/법률 관련', 'icon': '📋', 'description': '계약서, 등기 등'},
            {'key': 'loan', 'label': '대출 상담', 'icon': '🏦', 'description': '주담대, 전세대출 등'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # Step 3: 예산 - 매매 구매 (buy)
    {
        'step_number': 3,
        'question': '구매 예산은?',
        'depends_on_step': 1,
        'depends_on_options': ['buy'],
        'options': [
            {'key': 'under_1', 'label': '1억 미만', 'icon': '💵'},
            {'key': '1_3', 'label': '1억~3억', 'icon': '💰'},
            {'key': '3_5', 'label': '3억~5억', 'icon': '💰'},
            {'key': '5_10', 'label': '5억~10억', 'icon': '💎'},
            {'key': 'over_10', 'label': '10억 이상', 'icon': '🏆'},
            {'key': 'undecided', 'label': '미정/상담 후 결정', 'icon': '🤔'},
        ]
    },
    # Step 3: 예산 - 매매 판매 (sell)
    {
        'step_number': 3,
        'question': '희망 매매가는?',
        'depends_on_step': 1,
        'depends_on_options': ['sell'],
        'options': [
            {'key': 'under_1', 'label': '1억 미만', 'icon': '💵'},
            {'key': '1_3', 'label': '1억~3억', 'icon': '💰'},
            {'key': '3_5', 'label': '3억~5억', 'icon': '💰'},
            {'key': '5_10', 'label': '5억~10억', 'icon': '💎'},
            {'key': 'over_10', 'label': '10억 이상', 'icon': '🏆'},
            {'key': 'undecided', 'label': '미정/상담 후 결정', 'icon': '🤔'},
        ]
    },
    # Step 3: 예산 - 전세 구하기 (jeonse)
    {
        'step_number': 3,
        'question': '전세금 예산은?',
        'depends_on_step': 1,
        'depends_on_options': ['jeonse'],
        'options': [
            {'key': 'under_1', 'label': '1억 미만', 'icon': '💵'},
            {'key': '1_2', 'label': '1억~2억', 'icon': '💰'},
            {'key': '2_3', 'label': '2억~3억', 'icon': '💰'},
            {'key': '3_5', 'label': '3억~5억', 'icon': '💎'},
            {'key': 'over_5', 'label': '5억 이상', 'icon': '🏆'},
            {'key': 'undecided', 'label': '미정/상담 후 결정', 'icon': '🤔'},
        ]
    },
    # Step 3: 예산 - 세입자 구하기 (lease_out)
    {
        'step_number': 3,
        'question': '희망 전세/보증금은?',
        'depends_on_step': 1,
        'depends_on_options': ['lease_out'],
        'options': [
            {'key': 'under_1', 'label': '1억 미만', 'icon': '💵'},
            {'key': '1_2', 'label': '1억~2억', 'icon': '💰'},
            {'key': '2_3', 'label': '2억~3억', 'icon': '💰'},
            {'key': '3_5', 'label': '3억~5억', 'icon': '💎'},
            {'key': 'over_5', 'label': '5억 이상', 'icon': '🏆'},
            {'key': 'undecided', 'label': '미정/상담 후 결정', 'icon': '🤔'},
        ]
    },
    # Step 3: 예산 - 월세 구하기 (monthly)
    {
        'step_number': 3,
        'question': '월세 예산은? (보증금 별도)',
        'depends_on_step': 1,
        'depends_on_options': ['monthly'],
        'options': [
            {'key': 'under_50', 'label': '50만원 미만', 'icon': '💵'},
            {'key': '50_70', 'label': '50~70만원', 'icon': '💰'},
            {'key': '70_100', 'label': '70~100만원', 'icon': '💰'},
            {'key': '100_150', 'label': '100~150만원', 'icon': '💎'},
            {'key': 'over_150', 'label': '150만원 이상', 'icon': '🏆'},
            {'key': 'undecided', 'label': '미정/상담 후 결정', 'icon': '🤔'},
        ]
    },
    # Step 3: 예산 - 상가/사무실 구하기 (commercial_find)
    {
        'step_number': 3,
        'question': '예산은?',
        'depends_on_step': 1,
        'depends_on_options': ['commercial_find'],
        'options': [
            {'key': 'under_1', 'label': '1억 미만', 'icon': '💵'},
            {'key': '1_3', 'label': '1억~3억', 'icon': '💰'},
            {'key': '3_5', 'label': '3억~5억', 'icon': '💰'},
            {'key': '5_10', 'label': '5억~10억', 'icon': '💎'},
            {'key': 'over_10', 'label': '10억 이상', 'icon': '🏆'},
            {'key': 'undecided', 'label': '미정/상담 후 결정', 'icon': '🤔'},
        ]
    },
    # Step 3: 예산 - 상가/사무실 내놓기 (commercial_list)
    {
        'step_number': 3,
        'question': '희망 금액은?',
        'depends_on_step': 1,
        'depends_on_options': ['commercial_list'],
        'options': [
            {'key': 'under_1', 'label': '1억 미만', 'icon': '💵'},
            {'key': '1_3', 'label': '1억~3억', 'icon': '💰'},
            {'key': '3_5', 'label': '3억~5억', 'icon': '💰'},
            {'key': '5_10', 'label': '5억~10억', 'icon': '💎'},
            {'key': 'over_10', 'label': '10억 이상', 'icon': '🏆'},
            {'key': 'undecided', 'label': '미정/상담 후 결정', 'icon': '🤔'},
        ]
    },
    # Step 4: 희망 시기 (consulting 제외 전체)
    {
        'step_number': 4,
        'question': '희망 시기는?',
        'depends_on_step': 1,
        'depends_on_options': ['buy', 'jeonse', 'monthly', 'sell', 'lease_out', 'commercial_find', 'commercial_list'],
        'options': [
            {'key': 'asap', 'label': '급함 (2주 내)', 'icon': '🚨'},
            {'key': '1month', 'label': '1개월 내', 'icon': '📅'},
            {'key': '3month', 'label': '3개월 내', 'icon': '🗓️'},
            {'key': '6month', 'label': '6개월 내', 'icon': '📆'},
            {'key': 'browsing', 'label': '천천히 알아보는 중', 'icon': '👀'},
        ]
    },
]


def update_realtor_flows(apps, schema_editor):
    """공인중개사 플로우를 새로운 구조로 업데이트"""
    ConsultationFlow = apps.get_model('api', 'ConsultationFlow')
    ConsultationFlowOption = apps.get_model('api', 'ConsultationFlowOption')
    LocalBusinessCategory = apps.get_model('api', 'LocalBusinessCategory')

    category_name = '공인중개사'

    try:
        category = LocalBusinessCategory.objects.get(name=category_name)
    except LocalBusinessCategory.DoesNotExist:
        print(f'카테고리 "{category_name}" 없음 - 건너뜀')
        return

    # 기존 플로우 삭제
    existing_flows = ConsultationFlow.objects.filter(category=category)
    for flow in existing_flows:
        ConsultationFlowOption.objects.filter(flow=flow).delete()
    existing_flows.delete()
    print(f'카테고리 "{category_name}" 기존 플로우 삭제 완료')

    # 새 플로우 생성
    for idx, flow_data in enumerate(REALTOR_FLOWS):
        flow = ConsultationFlow.objects.create(
            category=category,
            step_number=flow_data['step_number'],
            question=flow_data['question'],
            is_required=True,
            depends_on_step=flow_data.get('depends_on_step'),
            depends_on_options=flow_data.get('depends_on_options', []),
            order_index=idx,
            is_active=True,
        )

        # 옵션 생성
        for opt_idx, option_data in enumerate(flow_data.get('options', [])):
            ConsultationFlowOption.objects.create(
                flow=flow,
                key=option_data['key'],
                label=option_data['label'],
                icon=option_data.get('icon', ''),
                logo=option_data.get('logo', ''),
                description=option_data.get('description', ''),
                is_custom_input=option_data.get('is_custom_input', False),
                order_index=opt_idx,
                is_active=True,
            )

    print(f'카테고리 "{category_name}" 새 플로우 생성 완료 ({len(REALTOR_FLOWS)}개 질문)')


def reverse_migration(apps, schema_editor):
    """롤백 시에는 아무것도 하지 않음 (수동 복구 필요)"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0119_fix_tax_accounting_flows'),
    ]

    operations = [
        migrations.RunPython(update_realtor_flows, reverse_migration),
    ]
