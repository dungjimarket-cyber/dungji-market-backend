# Generated manually - 상담 질문 플로우 데이터 수정 (카테고리명 일치)

from django.db import migrations


# 업종별 질문 플로우 데이터 (실제 카테고리명에 맞춤)
CONSULTATION_FLOWS_DATA = {
    '세무·회계': [
        {
            'step_number': 1,
            'question': '어떤 도움이 필요하세요?',
            'options': [
                {'key': 'income_tax', 'label': '종합소득세', 'icon': '📊'},
                {'key': 'vat', 'label': '부가세', 'icon': '📋'},
                {'key': 'bookkeeping', 'label': '기장대행', 'icon': '📝'},
                {'key': 'tax_saving', 'label': '절세상담', 'icon': '💰'},
                {'key': 'corporate_tax', 'label': '법인세', 'icon': '🏢'},
                {'key': 'transfer_tax', 'label': '양도세', 'icon': '🏠'},
                {'key': 'inheritance_tax', 'label': '상속/증여세', 'icon': '👨‍👩‍👧'},
                {'key': 'tax_audit', 'label': '세무조사 대응', 'icon': '🔍'},
                {'key': 'financial_statement', 'label': '재무제표 작성', 'icon': '📈'},
                {'key': 'audit', 'label': '회계감사', 'icon': '✅'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '사업 형태는?',
            'options': [
                {'key': 'sole_proprietor', 'label': '개인사업자', 'icon': '👤'},
                {'key': 'freelancer', 'label': '프리랜서', 'icon': '💼'},
                {'key': 'corporation', 'label': '법인', 'icon': '🏢'},
                {'key': 'startup', 'label': '예비창업자', 'icon': '🚀'},
                {'key': 'employee_side', 'label': '직장인(부업)', 'icon': '👔'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '연 매출 규모는?',
            'options': [
                {'key': 'none', 'label': '없음/신규', 'icon': '🆕'},
                {'key': 'under_30m', 'label': '3천만원 미만', 'icon': '💵'},
                {'key': '30m_to_100m', 'label': '3천~1억', 'icon': '💰'},
                {'key': '100m_to_500m', 'label': '1억~5억', 'icon': '💎'},
                {'key': 'over_500m', 'label': '5억 이상', 'icon': '🏆'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '현재 상황은?',
            'options': [
                {'key': 'new_request', 'label': '신규 의뢰', 'icon': '✨'},
                {'key': 'change_accountant', 'label': '기존 세무사 변경', 'icon': '🔄'},
                {'key': 'simple_inquiry', 'label': '단순 문의', 'icon': '❓'},
                {'key': 'urgent', 'label': '급한 처리 필요', 'icon': '🚨'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '법률 서비스': [
        {
            'step_number': 1,
            'question': '어떤 법률 분야인가요?',
            'options': [
                {'key': 'contract', 'label': '계약/채권', 'icon': '📄'},
                {'key': 'damage', 'label': '손해배상', 'icon': '💔'},
                {'key': 'real_estate', 'label': '부동산', 'icon': '🏠'},
                {'key': 'family', 'label': '가사/이혼', 'icon': '👨‍👩‍👧'},
                {'key': 'labor', 'label': '노동', 'icon': '👷'},
                {'key': 'criminal', 'label': '형사', 'icon': '⚖️'},
                {'key': 'corporate', 'label': '기업법무', 'icon': '🏢'},
                {'key': 'registration', 'label': '등기', 'icon': '📋'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '본인의 입장은?',
            'options': [
                {'key': 'plaintiff', 'label': '청구/소제기 측', 'icon': '⚔️'},
                {'key': 'defendant', 'label': '피소/대응 측', 'icon': '🛡️'},
                {'key': 'consultation', 'label': '상담만 필요', 'icon': '💬'},
                {'key': 'document', 'label': '서류 작성만', 'icon': '📝'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '분쟁 금액/규모는?',
            'options': [
                {'key': 'under_10m', 'label': '1천만원 미만', 'icon': '💵'},
                {'key': '10m_to_50m', 'label': '1천~5천만원', 'icon': '💰'},
                {'key': '50m_to_100m', 'label': '5천~1억', 'icon': '💎'},
                {'key': 'over_100m', 'label': '1억 이상', 'icon': '🏆'},
                {'key': 'non_monetary', 'label': '금전 아님', 'icon': '📋'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '시급성은?',
            'options': [
                {'key': 'urgent', 'label': '급함 (소송기한 등)', 'icon': '🚨'},
                {'key': 'within_month', 'label': '한 달 이내', 'icon': '📅'},
                {'key': 'flexible', 'label': '여유 있음', 'icon': '🕐'},
                {'key': 'prevention', 'label': '예방 차원', 'icon': '🛡️'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '공인중개사': [
        {
            'step_number': 1,
            'question': '어떤 부동산 거래인가요?',
            'options': [
                {'key': 'buy', 'label': '매매 (구매)', 'icon': '🏠'},
                {'key': 'sell', 'label': '매매 (판매)', 'icon': '💰'},
                {'key': 'jeonse', 'label': '전세', 'icon': '📋'},
                {'key': 'monthly_rent', 'label': '월세', 'icon': '💵'},
                {'key': 'commercial', 'label': '상가/사무실', 'icon': '🏢'},
                {'key': 'land', 'label': '토지', 'icon': '🌳'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '부동산 종류는?',
            'options': [
                {'key': 'apartment', 'label': '아파트', 'icon': '🏢'},
                {'key': 'villa', 'label': '빌라/다세대', 'icon': '🏠'},
                {'key': 'officetel', 'label': '오피스텔', 'icon': '🏙️'},
                {'key': 'single_house', 'label': '단독/다가구', 'icon': '🏡'},
                {'key': 'commercial_building', 'label': '상가건물', 'icon': '🏬'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '예산/가격대는?',
            'options': [
                {'key': 'under_200m', 'label': '2억 미만', 'icon': '💵'},
                {'key': '200m_to_500m', 'label': '2억~5억', 'icon': '💰'},
                {'key': '500m_to_1b', 'label': '5억~10억', 'icon': '💎'},
                {'key': 'over_1b', 'label': '10억 이상', 'icon': '🏆'},
                {'key': 'undecided', 'label': '미정', 'icon': '🤔'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '거래 시기는?',
            'options': [
                {'key': 'immediate', 'label': '즉시', 'icon': '🚨'},
                {'key': 'within_month', 'label': '1개월 이내', 'icon': '📅'},
                {'key': 'within_3months', 'label': '3개월 이내', 'icon': '🗓️'},
                {'key': 'after_3months', 'label': '3개월 이후', 'icon': '🕐'},
                {'key': 'just_looking', 'label': '둘러보는 중', 'icon': '👀'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '인테리어': [
        {
            'step_number': 1,
            'question': '어떤 공간인가요?',
            'options': [
                {'key': 'apartment', 'label': '아파트', 'icon': '🏢'},
                {'key': 'villa', 'label': '빌라/주택', 'icon': '🏠'},
                {'key': 'officetel', 'label': '오피스텔/원룸', 'icon': '🏙️'},
                {'key': 'office', 'label': '사무실', 'icon': '💼'},
                {'key': 'store', 'label': '상가/매장', 'icon': '🏬'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '시공 범위는?',
            'options': [
                {'key': 'full', 'label': '전체 리모델링', 'icon': '🏗️'},
                {'key': 'partial', 'label': '부분 시공', 'icon': '🔨'},
                {'key': 'kitchen', 'label': '주방', 'icon': '🍳'},
                {'key': 'bathroom', 'label': '욕실', 'icon': '🚿'},
                {'key': 'floor_wall', 'label': '바닥/벽지', 'icon': '🎨'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '면적은?',
            'options': [
                {'key': 'under_20', 'label': '20평 미만', 'icon': '📐'},
                {'key': '20_to_30', 'label': '20~30평', 'icon': '📏'},
                {'key': '30_to_40', 'label': '30~40평', 'icon': '📐'},
                {'key': 'over_40', 'label': '40평 이상', 'icon': '🏠'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '예산 범위는?',
            'options': [
                {'key': 'under_10m', 'label': '1천만원 미만', 'icon': '💵'},
                {'key': '10m_to_30m', 'label': '1천~3천만원', 'icon': '💰'},
                {'key': '30m_to_50m', 'label': '3천~5천만원', 'icon': '💎'},
                {'key': 'over_50m', 'label': '5천만원 이상', 'icon': '🏆'},
                {'key': 'undecided', 'label': '미정/상담 후 결정', 'icon': '🤔'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '청소·이사': [
        {
            'step_number': 1,
            'question': '어떤 서비스가 필요하세요?',
            'options': [
                {'key': 'move_house', 'label': '가정 이사', 'icon': '🏠'},
                {'key': 'move_office', 'label': '사무실 이사', 'icon': '🏢'},
                {'key': 'home_cleaning', 'label': '입주/이사 청소', 'icon': '🧹'},
                {'key': 'regular_cleaning', 'label': '정기 청소', 'icon': '✨'},
                {'key': 'special_cleaning', 'label': '특수 청소', 'icon': '🧽'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '공간 크기는?',
            'options': [
                {'key': 'studio', 'label': '원룸/투룸', 'icon': '🛏️'},
                {'key': 'under_20', 'label': '20평 미만', 'icon': '📐'},
                {'key': '20_to_30', 'label': '20~30평', 'icon': '📏'},
                {'key': '30_to_40', 'label': '30~40평', 'icon': '🏠'},
                {'key': 'over_40', 'label': '40평 이상', 'icon': '🏡'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '희망 날짜는?',
            'options': [
                {'key': 'this_week', 'label': '이번 주', 'icon': '📅'},
                {'key': 'next_week', 'label': '다음 주', 'icon': '🗓️'},
                {'key': 'within_month', 'label': '한 달 이내', 'icon': '📆'},
                {'key': 'specific_date', 'label': '특정 날짜', 'icon': '✅'},
                {'key': 'flexible', 'label': '협의 가능', 'icon': '🤝'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '추가 요청사항은?',
            'options': [
                {'key': 'packing', 'label': '포장 서비스', 'icon': '📦'},
                {'key': 'storage', 'label': '보관 서비스', 'icon': '🏪'},
                {'key': 'disposal', 'label': '폐기물 처리', 'icon': '🗑️'},
                {'key': 'none', 'label': '없음', 'icon': '✅'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '휴대폰 대리점': [
        {
            'step_number': 1,
            'question': '어떤 상담인가요?',
            'options': [
                {'key': 'new_signup', 'label': '신규 가입', 'icon': '✨'},
                {'key': 'number_port', 'label': '번호이동', 'icon': '🔄'},
                {'key': 'device_change', 'label': '기기변경', 'icon': '📱'},
                {'key': 'plan_change', 'label': '요금제 변경', 'icon': '💳'},
                {'key': 'add_service', 'label': '부가서비스', 'icon': '➕'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '통신사는?',
            'options': [
                {'key': 'skt', 'label': 'SKT', 'icon': '🔴'},
                {'key': 'kt', 'label': 'KT', 'icon': '🟠'},
                {'key': 'lgu', 'label': 'LG U+', 'icon': '🟣'},
                {'key': 'mvno', 'label': '알뜰폰', 'icon': '💰'},
                {'key': 'undecided', 'label': '미정/비교 원함', 'icon': '🤔'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '관심 기기는?',
            'options': [
                {'key': 'iphone', 'label': '아이폰', 'icon': '🍎'},
                {'key': 'galaxy_s', 'label': '갤럭시 S', 'icon': '📱'},
                {'key': 'galaxy_fold', 'label': '갤럭시 폴드/플립', 'icon': '📲'},
                {'key': 'budget', 'label': '보급형 폰', 'icon': '💵'},
                {'key': 'recommend', 'label': '기타/추천 원함', 'icon': '🤔'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '중요하게 생각하는 것은?',
            'options': [
                {'key': 'lowest_price', 'label': '최저 요금', 'icon': '💰'},
                {'key': 'more_data', 'label': '데이터 많이', 'icon': '📶'},
                {'key': 'subsidy', 'label': '공시지원금', 'icon': '💵'},
                {'key': 'latest_device', 'label': '기기 최신', 'icon': '✨'},
                {'key': 'family_plan', 'label': '가족결합', 'icon': '👨‍👩‍👧'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '정비소': [
        {
            'step_number': 1,
            'question': '정비 목적은?',
            'options': [
                {'key': 'regular_check', 'label': '정기 점검', 'icon': '🔧'},
                {'key': 'repair', 'label': '고장 수리', 'icon': '🛠️'},
                {'key': 'accident_repair', 'label': '사고 수리', 'icon': '🚗'},
                {'key': 'consumables', 'label': '타이어/소모품', 'icon': '⚙️'},
                {'key': 'tuning', 'label': '튜닝/악세사리', 'icon': '🎨'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '차량 종류는?',
            'options': [
                {'key': 'domestic_small', 'label': '국산 소형', 'icon': '🚗'},
                {'key': 'domestic_mid_large', 'label': '국산 중형/대형', 'icon': '🚙'},
                {'key': 'domestic_suv', 'label': '국산 SUV', 'icon': '🚐'},
                {'key': 'imported', 'label': '수입차', 'icon': '🏎️'},
                {'key': 'ev_hybrid', 'label': '전기차/하이브리드', 'icon': '⚡'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '증상/상황은?',
            'depends_on_step': 1,
            'depends_on_options': ['repair'],
            'options': [
                {'key': 'engine', 'label': '시동 문제', 'icon': '🔑'},
                {'key': 'noise', 'label': '이상 소음', 'icon': '🔊'},
                {'key': 'warning_light', 'label': '경고등', 'icon': '⚠️'},
                {'key': 'ac_heater', 'label': '에어컨/히터', 'icon': '❄️'},
                {'key': 'other', 'label': '기타', 'icon': '❓'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '희망 시기는?',
            'options': [
                {'key': 'urgent', 'label': '당장 급함', 'icon': '🚨'},
                {'key': 'this_week', 'label': '이번 주', 'icon': '📅'},
                {'key': 'flexible', 'label': '시간 여유 있음', 'icon': '🕐'},
                {'key': 'estimate_only', 'label': '견적만', 'icon': '💰'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
}


def populate_consultation_flows(apps, schema_editor):
    """상담 질문 플로우 초기 데이터 생성"""
    LocalBusinessCategory = apps.get_model('api', 'LocalBusinessCategory')
    ConsultationFlow = apps.get_model('api', 'ConsultationFlow')
    ConsultationFlowOption = apps.get_model('api', 'ConsultationFlowOption')

    # 기존 데이터 전체 삭제
    ConsultationFlow.objects.all().delete()

    for category_name, flows in CONSULTATION_FLOWS_DATA.items():
        try:
            category = LocalBusinessCategory.objects.get(name=category_name)
        except LocalBusinessCategory.DoesNotExist:
            print(f'카테고리 "{category_name}" 없음 - 건너뜀')
            continue

        for flow_data in flows:
            # 플로우 생성
            flow = ConsultationFlow.objects.create(
                category=category,
                step_number=flow_data['step_number'],
                question=flow_data['question'],
                is_required=flow_data.get('is_required', True),
                depends_on_step=flow_data.get('depends_on_step'),
                depends_on_options=flow_data.get('depends_on_options', []),
                is_active=True,
            )

            # 옵션 생성
            for idx, option_data in enumerate(flow_data.get('options', [])):
                ConsultationFlowOption.objects.create(
                    flow=flow,
                    key=option_data['key'],
                    label=option_data['label'],
                    icon=option_data.get('icon', ''),
                    description=option_data.get('description', ''),
                    is_custom_input=option_data.get('is_custom_input', False),
                    order_index=idx,
                    is_active=True,
                )

        print(f'카테고리 "{category_name}" 플로우 생성 완료')

    print('상담 질문 플로우 데이터 생성 완료')


def reverse_populate(apps, schema_editor):
    """롤백 시 데이터 삭제"""
    ConsultationFlow = apps.get_model('api', 'ConsultationFlow')
    ConsultationFlow.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0111_populate_consultation_flows'),
    ]

    operations = [
        migrations.RunPython(populate_consultation_flows, reverse_populate),
    ]
