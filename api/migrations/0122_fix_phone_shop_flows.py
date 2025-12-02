# Generated migration for fixing phone shop consultation flows
# 휴대폰 대리점 플로우를 4가지 상품 + 지원금 문의 구조로 개선

from django.db import migrations


# 새로운 휴대폰 대리점 플로우 데이터
PHONE_SHOP_FLOWS = [
    # Step 1: 메인 상품 선택
    {
        'step_number': 1,
        'question': '어떤 상품이 필요하세요?',
        'depends_on_step': None,
        'depends_on_options': [],
        'options': [
            {'key': 'internet', 'label': '인터넷', 'icon': '🌐', 'description': '인터넷만 가입/변경'},
            {'key': 'internet_tv', 'label': '인터넷 + TV', 'icon': '📺', 'description': '인터넷, TV 결합'},
            {'key': 'triple', 'label': '휴대폰 + 인터넷 + TV', 'icon': '🏠', 'description': '트리플 결합 할인'},
            {'key': 'phone', 'label': '휴대폰', 'icon': '📱', 'description': '휴대폰만 개통/변경'},
        ]
    },
    # ===== 인터넷 선택 시 =====
    {
        'step_number': 2,
        'question': '어떤 인터넷 상담인가요?',
        'depends_on_step': 1,
        'depends_on_options': ['internet'],
        'options': [
            {'key': 'new_install', 'label': '신규 가입', 'icon': '✨', 'description': '새로 설치'},
            {'key': 'change', 'label': '타사 변경', 'icon': '🔄', 'description': 'SKT↔KT↔LGU+'},
            {'key': 'move', 'label': '이전 설치', 'icon': '🏠', 'description': '이사할 때'},
            {'key': 'speed_up', 'label': '속도 변경/업그레이드', 'icon': '⚡'},
        ]
    },
    # ===== 인터넷+TV 선택 시 =====
    {
        'step_number': 2,
        'question': '현재 상황은?',
        'depends_on_step': 1,
        'depends_on_options': ['internet_tv'],
        'options': [
            {'key': 'both_new', 'label': '둘 다 신규 가입', 'icon': '✨'},
            {'key': 'add_tv', 'label': '인터넷 있고 TV 추가', 'icon': '📺'},
            {'key': 'add_internet', 'label': 'TV 있고 인터넷 추가', 'icon': '🌐'},
            {'key': 'change_both', 'label': '타사에서 변경', 'icon': '🔄'},
        ]
    },
    # ===== 트리플 결합 선택 시 =====
    {
        'step_number': 2,
        'question': '현재 상황은?',
        'depends_on_step': 1,
        'depends_on_options': ['triple'],
        'options': [
            {'key': 'all_new', 'label': '전부 신규 가입', 'icon': '✨'},
            {'key': 'add_phone', 'label': '인터넷/TV 있고 휴대폰 추가', 'icon': '📱'},
            {'key': 'add_home', 'label': '휴대폰 있고 인터넷/TV 추가', 'icon': '🏠'},
            {'key': 'change_all', 'label': '타사에서 전체 변경', 'icon': '🔄'},
        ]
    },
    # ===== 휴대폰 선택 시 =====
    {
        'step_number': 2,
        'question': '어떤 휴대폰 상담인가요?',
        'depends_on_step': 1,
        'depends_on_options': ['phone'],
        'options': [
            {'key': 'new', 'label': '신규 가입', 'icon': '✨', 'description': '새 번호 개통'},
            {'key': 'mnp', 'label': '번호이동', 'icon': '🔄', 'description': '타사→이동 (번호 유지)'},
            {'key': 'upgrade', 'label': '기기변경', 'icon': '📱', 'description': '같은 통신사, 새 폰'},
            {'key': 'plan_only', 'label': '요금제만 변경', 'icon': '💳'},
        ]
    },
    # ===== 휴대폰 - 기기 선택 (신규/번호이동/기기변경) =====
    {
        'step_number': 3,
        'question': '관심 있는 기기는?',
        'depends_on_step': 2,
        'depends_on_options': ['new', 'mnp', 'upgrade'],
        'options': [
            {'key': 'iphone', 'label': '아이폰', 'icon': '🍎'},
            {'key': 'galaxy_s', 'label': '갤럭시 S시리즈', 'icon': '📱'},
            {'key': 'galaxy_fold', 'label': '폴드/플립', 'icon': '📲'},
            {'key': 'budget', 'label': '가성비폰', 'icon': '💵'},
            {'key': 'recommend', 'label': '추천 원해요', 'icon': '🤔'},
        ]
    },
    # ===== Step 3: 지원금/혜택 문의 (인터넷/TV 관련) =====
    {
        'step_number': 3,
        'question': '지원금/혜택 관련 궁금한 점이 있으세요?',
        'depends_on_step': 1,
        'depends_on_options': ['internet', 'internet_tv', 'triple'],
        'options': [
            {'key': 'cashback', 'label': '현금 사은품 궁금해요', 'icon': '💵', 'description': '가입 시 현금 지원'},
            {'key': 'bundle_discount', 'label': '결합할인 궁금해요', 'icon': '👨‍👩‍👧', 'description': '가족/유무선 결합'},
            {'key': 'promotion', 'label': '프로모션/이벤트', 'icon': '🎁', 'description': '진행 중인 혜택'},
            {'key': 'recommend', 'label': '잘 모르겠어요', 'icon': '🤔', 'description': '전문가 추천'},
        ]
    },
    # ===== Step 4: 지원금/혜택 문의 (휴대폰) =====
    {
        'step_number': 4,
        'question': '지원금/혜택 관련 궁금한 점이 있으세요?',
        'depends_on_step': 2,
        'depends_on_options': ['new', 'mnp', 'upgrade'],
        'options': [
            {'key': 'subsidy', 'label': '공시지원금 궁금해요', 'icon': '💰', 'description': '단말기 가격 할인'},
            {'key': 'plan_discount', 'label': '요금할인(선택약정)', 'icon': '💳', 'description': '25% 요금 할인'},
            {'key': 'bundle_discount', 'label': '결합할인 궁금해요', 'icon': '👨‍👩‍👧', 'description': '가족/유무선 결합'},
            {'key': 'transfer_subsidy', 'label': '전환지원금 궁금해요', 'icon': '🔄', 'description': '번호이동 추가 지원'},
            {'key': 'recommend', 'label': '잘 모르겠어요', 'icon': '🤔', 'description': '전문가 추천'},
        ]
    },
    # ===== Step 4: 통신사 선택 (인터넷/TV 관련) =====
    {
        'step_number': 4,
        'question': '선호하는 통신사가 있나요?',
        'depends_on_step': 1,
        'depends_on_options': ['internet', 'internet_tv', 'triple'],
        'options': [
            {'key': 'skt', 'label': 'SK브로드밴드', 'icon': '🔴'},
            {'key': 'kt', 'label': 'KT', 'icon': '⚪'},
            {'key': 'lgu', 'label': 'LG U+', 'icon': '🟣'},
            {'key': 'compare', 'label': '비교 후 결정', 'icon': '⚖️'},
        ]
    },
    # ===== Step 5: 통신사 선택 (휴대폰) =====
    {
        'step_number': 5,
        'question': '원하는 통신사는?',
        'depends_on_step': 2,
        'depends_on_options': ['new', 'mnp', 'upgrade', 'plan_only'],
        'options': [
            {'key': 'skt', 'label': 'SKT', 'icon': '🔴'},
            {'key': 'kt', 'label': 'KT', 'icon': '⚪'},
            {'key': 'lgu', 'label': 'LG U+', 'icon': '🟣'},
            {'key': 'compare', 'label': '비교 후 결정', 'icon': '⚖️'},
        ]
    },
]


def update_phone_shop_flows(apps, schema_editor):
    """휴대폰 대리점 플로우를 새로운 구조로 업데이트"""
    ConsultationFlow = apps.get_model('api', 'ConsultationFlow')
    ConsultationFlowOption = apps.get_model('api', 'ConsultationFlowOption')
    LocalBusinessCategory = apps.get_model('api', 'LocalBusinessCategory')

    category_name = '휴대폰 대리점'

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
    for idx, flow_data in enumerate(PHONE_SHOP_FLOWS):
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

    print(f'카테고리 "{category_name}" 새 플로우 생성 완료 ({len(PHONE_SHOP_FLOWS)}개 질문)')


def reverse_migration(apps, schema_editor):
    """롤백 시에는 아무것도 하지 않음 (수동 복구 필요)"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0121_add_region_last_changed_at'),
    ]

    operations = [
        migrations.RunPython(update_phone_shop_flows, reverse_migration),
    ]
