# Generated migration for fixing tax/accounting consultation flows
# 세무사/회계사 플로우를 전문가 선택 후 분기되도록 수정
# 참고: 세무통, 찾아줘세무사, 삼일회계법인, 딜로이트 등 실제 플랫폼 분석 (2024)

from django.db import migrations


# 새로운 세무·회계 플로우 데이터 (전문가 선택 후 분기)
TAX_ACCOUNTING_FLOWS = [
    # Step 1: 전문가 유형 선택
    {
        'step_number': 1,
        'question': '어떤 전문가가 필요하세요?',
        'depends_on_step': None,
        'depends_on_options': [],
        'options': [
            {'key': 'tax_expert', 'label': '세무사', 'icon': '📊', 'description': '세금 신고, 기장대행, 절세 상담'},
            {'key': 'accountant', 'label': '회계사', 'icon': '📈', 'description': '외부감사, 재무실사, 경영컨설팅'},
        ]
    },
    # ===== 세무사 선택 시 플로우 =====
    {
        'step_number': 2,
        'question': '어떤 세무 서비스가 필요하세요?',
        'depends_on_step': 1,
        'depends_on_options': ['tax_expert'],
        'options': [
            {'key': 'tax_filing', 'label': '세금 신고 대행', 'icon': '📋', 'description': '종소세, 부가세, 법인세 등'},
            {'key': 'bookkeeping', 'label': '기장대행 (월 장부관리)', 'icon': '📝', 'description': '증빙정리, 장부작성, 신고까지'},
            {'key': 'tax_saving', 'label': '절세 상담', 'icon': '💰', 'description': '합법적 절세 전략'},
            {'key': 'property_tax', 'label': '재산세제 상담', 'icon': '🏠', 'description': '양도세, 상속세, 증여세'},
            {'key': 'business_start', 'label': '창업/사업자 관련', 'icon': '🚀', 'description': '사업자등록, 업종 선택'},
            {'key': 'tax_issue', 'label': '세무 문제 해결', 'icon': '🔍', 'description': '세무조사, 가산세, 경정청구'},
        ]
    },
    # 세금 신고 대행 상세
    {
        'step_number': 3,
        'question': '어떤 세금 신고가 필요하세요?',
        'depends_on_step': 2,
        'depends_on_options': ['tax_filing'],
        'options': [
            {'key': 'income_tax', 'label': '종합소득세', 'icon': '📊', 'description': '5월 정기신고'},
            {'key': 'vat', 'label': '부가가치세', 'icon': '📋', 'description': '1월/7월 정기신고'},
            {'key': 'corporate_tax', 'label': '법인세', 'icon': '🏢', 'description': '3월 정기신고'},
            {'key': 'withholding', 'label': '원천세', 'icon': '💳', 'description': '매월 신고'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # 기장대행 상세
    {
        'step_number': 3,
        'question': '현재 기장 상황은?',
        'depends_on_step': 2,
        'depends_on_options': ['bookkeeping'],
        'options': [
            {'key': 'new', 'label': '처음 맡기려고 함', 'icon': '✨', 'description': '신규 의뢰'},
            {'key': 'change', 'label': '기존 세무사 변경', 'icon': '🔄', 'description': '담당자 변경'},
            {'key': 'self_to_pro', 'label': '직접 하다가 맡기려고', 'icon': '📊', 'description': '셀프 → 전문가'},
            {'key': 'inquiry', 'label': '기장료 비교/문의', 'icon': '💰'},
        ]
    },
    # 재산세제 상세
    {
        'step_number': 3,
        'question': '어떤 재산세제 상담이 필요하세요?',
        'depends_on_step': 2,
        'depends_on_options': ['property_tax'],
        'options': [
            {'key': 'transfer_tax', 'label': '양도소득세', 'icon': '🏠', 'description': '부동산/주식 양도'},
            {'key': 'inheritance', 'label': '상속세', 'icon': '👨‍👩‍👧', 'description': '상속재산 신고'},
            {'key': 'gift_tax', 'label': '증여세', 'icon': '🎁', 'description': '증여재산 신고'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # 절세 상담 상세
    {
        'step_number': 3,
        'question': '어떤 절세가 궁금하세요?',
        'depends_on_step': 2,
        'depends_on_options': ['tax_saving'],
        'options': [
            {'key': 'expense', 'label': '비용처리 방법', 'icon': '🧾', 'description': '적격증빙, 경비인정'},
            {'key': 'business_type', 'label': '개인 vs 법인 전환', 'icon': '🏢', 'description': '유리한 사업자 형태'},
            {'key': 'income_deduction', 'label': '소득공제/세액공제', 'icon': '📉'},
            {'key': 'family_business', 'label': '가족 급여/지분', 'icon': '👨‍👩‍👧'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # 창업 관련 상세
    {
        'step_number': 3,
        'question': '어떤 창업 관련 상담이 필요하세요?',
        'depends_on_step': 2,
        'depends_on_options': ['business_start'],
        'options': [
            {'key': 'registration', 'label': '사업자등록 방법', 'icon': '📄'},
            {'key': 'business_type', 'label': '개인 vs 법인 선택', 'icon': '🤔'},
            {'key': 'tax_benefit', 'label': '창업 세제혜택', 'icon': '🎁', 'description': '청년창업, 중소기업 등'},
            {'key': 'initial_setup', 'label': '초기 세무 세팅', 'icon': '⚙️'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # 세무 문제 상세
    {
        'step_number': 3,
        'question': '어떤 세무 문제인가요?',
        'depends_on_step': 2,
        'depends_on_options': ['tax_issue'],
        'options': [
            {'key': 'tax_audit', 'label': '세무조사 대응', 'icon': '🔍', 'description': '조사 통보, 소명자료'},
            {'key': 'penalty', 'label': '가산세 문제', 'icon': '⚠️', 'description': '신고불성실, 납부지연'},
            {'key': 'correction', 'label': '수정신고/경정청구', 'icon': '✏️', 'description': '과다납부 환급'},
            {'key': 'dispute', 'label': '과세 불복/이의신청', 'icon': '⚖️'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # ===== 회계사 선택 시 플로우 =====
    {
        'step_number': 2,
        'question': '어떤 회계 서비스가 필요하세요?',
        'depends_on_step': 1,
        'depends_on_options': ['accountant'],
        'options': [
            {'key': 'audit', 'label': '외부감사', 'icon': '🔍', 'description': '법정감사, 재무제표 감사'},
            {'key': 'due_diligence', 'label': '재무실사 (DD)', 'icon': '📑', 'description': 'M&A, 투자 실사'},
            {'key': 'valuation', 'label': '기업가치평가', 'icon': '📈', 'description': 'DCF, 상대가치, 자산가치'},
            {'key': 'consulting', 'label': '경영컨설팅', 'icon': '💼', 'description': '내부통제, IFRS, ESG'},
            {'key': 'financial', 'label': '회계/결산 자문', 'icon': '📊', 'description': '법인결산, 연결재무제표'},
            {'key': 'other', 'label': '기타 상담', 'icon': '💬'},
        ]
    },
    # 외부감사 상세
    {
        'step_number': 3,
        'question': '어떤 감사가 필요하세요?',
        'depends_on_step': 2,
        'depends_on_options': ['audit'],
        'options': [
            {'key': 'statutory', 'label': '법정감사 (외감법)', 'icon': '📋', 'description': '자산 500억 이상 등'},
            {'key': 'voluntary', 'label': '임의감사', 'icon': '✅', 'description': '투자유치, 내부목적'},
            {'key': 'review', 'label': '검토 (Review)', 'icon': '🔎', 'description': '간이감사'},
            {'key': 'special', 'label': '특수목적감사', 'icon': '🎯', 'description': '정부보조금, 기타'},
        ]
    },
    # 재무실사 상세
    {
        'step_number': 3,
        'question': '어떤 실사가 필요하세요?',
        'depends_on_step': 2,
        'depends_on_options': ['due_diligence'],
        'options': [
            {'key': 'buy_side', 'label': '인수자 측 실사', 'icon': '🛒', 'description': '인수 전 검토'},
            {'key': 'sell_side', 'label': '매도자 측 실사', 'icon': '💰', 'description': '매각 준비'},
            {'key': 'investment', 'label': '투자 실사', 'icon': '📈', 'description': 'VC/PE 투자'},
            {'key': 'ipo', 'label': 'IPO 실사', 'icon': '🏛️', 'description': '상장 준비'},
        ]
    },
    # 기업가치평가 상세
    {
        'step_number': 3,
        'question': '가치평가 목적은?',
        'depends_on_step': 2,
        'depends_on_options': ['valuation'],
        'options': [
            {'key': 'ma', 'label': 'M&A 거래', 'icon': '🤝', 'description': '인수합병 가격산정'},
            {'key': 'investment', 'label': '투자유치', 'icon': '💵', 'description': '투자 밸류에이션'},
            {'key': 'stock_option', 'label': '스톡옵션 평가', 'icon': '📊'},
            {'key': 'tax', 'label': '세무목적', 'icon': '🧾', 'description': '상속증여, 양도'},
            {'key': 'litigation', 'label': '소송/분쟁', 'icon': '⚖️', 'description': '주주분쟁 등'},
        ]
    },
    # 경영컨설팅 상세
    {
        'step_number': 3,
        'question': '어떤 컨설팅이 필요하세요?',
        'depends_on_step': 2,
        'depends_on_options': ['consulting'],
        'options': [
            {'key': 'internal_control', 'label': '내부통제/내부회계관리', 'icon': '🔐'},
            {'key': 'ifrs', 'label': 'IFRS 도입/전환', 'icon': '🌐', 'description': '국제회계기준'},
            {'key': 'esg', 'label': 'ESG 컨설팅', 'icon': '🌱', 'description': '지속가능경영'},
            {'key': 'process', 'label': '업무프로세스 개선', 'icon': '⚙️'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # 회계/결산 자문 상세
    {
        'step_number': 3,
        'question': '어떤 회계 자문이 필요하세요?',
        'depends_on_step': 2,
        'depends_on_options': ['financial'],
        'options': [
            {'key': 'settlement', 'label': '법인결산', 'icon': '📅', 'description': '연간 결산 대행'},
            {'key': 'consolidation', 'label': '연결재무제표', 'icon': '🔗', 'description': '그룹사 연결'},
            {'key': 'accounting_policy', 'label': '회계정책 자문', 'icon': '📘'},
            {'key': 'payroll', 'label': '급여/4대보험', 'icon': '💳'},
            {'key': 'custom', 'label': '기타 (직접 입력)', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # 기타 상담 (회계사)
    {
        'step_number': 3,
        'question': '어떤 상담이 필요하신지 적어주세요',
        'depends_on_step': 2,
        'depends_on_options': ['other'],
        'options': [
            {'key': 'custom', 'label': '상담 내용 입력', 'icon': '📝', 'is_custom_input': True},
        ]
    },
    # ===== 공통 마무리 질문 =====
    {
        'step_number': 4,
        'question': '사업 형태는?',
        'depends_on_step': None,
        'depends_on_options': [],
        'options': [
            {'key': 'sole_proprietor', 'label': '개인사업자', 'icon': '👤'},
            {'key': 'freelancer', 'label': '프리랜서/3.3%', 'icon': '💼'},
            {'key': 'corporation', 'label': '법인', 'icon': '🏢'},
            {'key': 'startup', 'label': '스타트업', 'icon': '🚀', 'description': '벤처/초기기업'},
            {'key': 'prospective', 'label': '예비창업자', 'icon': '💡'},
            {'key': 'individual', 'label': '일반 개인', 'icon': '🙋'},
        ]
    },
    {
        'step_number': 5,
        'question': '얼마나 급하세요?',
        'depends_on_step': None,
        'depends_on_options': [],
        'options': [
            {'key': 'very_urgent', 'label': '매우 급함', 'icon': '🚨', 'description': '1주일 이내 처리 필요'},
            {'key': 'urgent', 'label': '빠른 처리 필요', 'icon': '⏰', 'description': '이번 달 내'},
            {'key': 'normal', 'label': '여유 있음', 'icon': '📅', 'description': '1~2개월 내'},
            {'key': 'just_inquiry', 'label': '단순 문의/비교', 'icon': '💬', 'description': '정보 수집 중'},
        ]
    },
]


def update_tax_accounting_flows(apps, schema_editor):
    """세무사/회계사 플로우를 새로운 구조로 업데이트"""
    ConsultationFlow = apps.get_model('api', 'ConsultationFlow')
    ConsultationFlowOption = apps.get_model('api', 'ConsultationFlowOption')
    LocalBusinessCategory = apps.get_model('api', 'LocalBusinessCategory')

    # 세무사, 회계사 카테고리 찾기
    target_categories = ['세무사', '회계사']

    for category_name in target_categories:
        try:
            category = LocalBusinessCategory.objects.get(name=category_name)
        except LocalBusinessCategory.DoesNotExist:
            print(f'카테고리 "{category_name}" 없음 - 건너뜀')
            continue

        # 기존 플로우 삭제
        existing_flows = ConsultationFlow.objects.filter(category=category)
        for flow in existing_flows:
            ConsultationFlowOption.objects.filter(flow=flow).delete()
        existing_flows.delete()
        print(f'카테고리 "{category_name}" 기존 플로우 삭제 완료')

        # 새 플로우 생성
        for idx, flow_data in enumerate(TAX_ACCOUNTING_FLOWS):
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

        print(f'카테고리 "{category_name}" 새 플로우 생성 완료 ({len(TAX_ACCOUNTING_FLOWS)}개 질문)')


def reverse_migration(apps, schema_editor):
    """롤백 시에는 아무것도 하지 않음 (수동 복구 필요)"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0118_expert_profile_consultation_match'),
    ]

    operations = [
        migrations.RunPython(update_tax_accounting_flows, reverse_migration),
    ]
