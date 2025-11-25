# Generated manually - 상담 질문 플로우 초기 데이터

from django.db import migrations


# 업종별 질문 플로우 데이터
# 구조: { 업종명: [ {step_number, question, options: [{key, label, icon?, is_custom_input?}] } ] }
CONSULTATION_FLOWS_DATA = {
    '세무사': [
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
    '회계사': [
        {
            'step_number': 1,
            'question': '어떤 도움이 필요하세요?',
            'options': [
                {'key': 'financial_statement', 'label': '재무제표 작성', 'icon': '📊'},
                {'key': 'audit', 'label': '회계감사', 'icon': '🔍'},
                {'key': 'consulting', 'label': '경영컨설팅', 'icon': '💼'},
                {'key': 'settlement', 'label': '법인결산', 'icon': '📅'},
                {'key': 'payroll', 'label': '급여/4대보험', 'icon': '💳'},
                {'key': 'funding', 'label': '자금조달', 'icon': '💰'},
                {'key': 'valuation', 'label': '기업가치평가', 'icon': '📈'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '기업 형태는?',
            'options': [
                {'key': 'sole_proprietor', 'label': '개인사업자', 'icon': '👤'},
                {'key': 'sme', 'label': '중소기업', 'icon': '🏢'},
                {'key': 'startup', 'label': '스타트업', 'icon': '🚀'},
                {'key': 'nonprofit', 'label': '비영리법인', 'icon': '🤝'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '기업 규모는? (직원 수)',
            'options': [
                {'key': '1_to_5', 'label': '1~5명', 'icon': '👤'},
                {'key': '6_to_20', 'label': '6~20명', 'icon': '👥'},
                {'key': '21_to_50', 'label': '21~50명', 'icon': '👨‍👩‍👧‍👦'},
                {'key': 'over_50', 'label': '50명 이상', 'icon': '🏢'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '요청 시점은?',
            'options': [
                {'key': 'periodic', 'label': '정기(월/분기/연)', 'icon': '📅'},
                {'key': 'one_time', 'label': '일회성', 'icon': '1️⃣'},
                {'key': 'urgent', 'label': '긴급', 'icon': '🚨'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '변호사': [
        {
            'step_number': 1,
            'question': '어떤 분야 상담인가요?',
            'options': [
                {'key': 'civil', 'label': '민사(계약/손해배상)', 'icon': '📄'},
                {'key': 'criminal', 'label': '형사', 'icon': '⚖️'},
                {'key': 'family', 'label': '가사(이혼/상속)', 'icon': '👨‍👩‍👧'},
                {'key': 'real_estate', 'label': '부동산', 'icon': '🏠'},
                {'key': 'labor', 'label': '노동/근로', 'icon': '👔'},
                {'key': 'debt', 'label': '채권추심', 'icon': '💵'},
                {'key': 'corporate', 'label': '기업법무', 'icon': '🏢'},
                {'key': 'administrative', 'label': '행정/인허가', 'icon': '📋'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '현재 상황은?',
            'options': [
                {'key': 'early_stage', 'label': '분쟁 초기', 'icon': '🔔'},
                {'key': 'considering', 'label': '소송 검토 중', 'icon': '🤔'},
                {'key': 'ongoing', 'label': '소송 진행 중', 'icon': '⚖️'},
                {'key': 'post_verdict', 'label': '판결 후 대응', 'icon': '📜'},
                {'key': 'simple_inquiry', 'label': '단순 법률 상담', 'icon': '❓'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '상대방은?',
            'options': [
                {'key': 'individual', 'label': '개인', 'icon': '👤'},
                {'key': 'company', 'label': '기업', 'icon': '🏢'},
                {'key': 'organization', 'label': '기관/단체', 'icon': '🏛️'},
                {'key': 'undecided', 'label': '미정', 'icon': '❓'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '긴급도는?',
            'options': [
                {'key': 'consultation', 'label': '단순 상담', 'icon': '💬'},
                {'key': 'document_review', 'label': '서류 검토 필요', 'icon': '📄'},
                {'key': 'urgent', 'label': '빠른 조치 필요', 'icon': '🚨'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '법무사': [
        {
            'step_number': 1,
            'question': '어떤 도움이 필요하세요?',
            'options': [
                {'key': 'real_estate_reg', 'label': '부동산 등기', 'icon': '🏠'},
                {'key': 'corporate_reg', 'label': '법인 등기', 'icon': '🏢'},
                {'key': 'litigation_doc', 'label': '소송서류 작성', 'icon': '📄'},
                {'key': 'notarization', 'label': '공정증서', 'icon': '✍️'},
                {'key': 'permit', 'label': '인허가/신고', 'icon': '📋'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '세부 내용은?',
            'depends_on_step': 1,
            'depends_on_options': ['real_estate_reg'],
            'options': [
                {'key': 'ownership_sale', 'label': '소유권 이전(매매)', 'icon': '🔑'},
                {'key': 'ownership_inherit', 'label': '소유권 이전(상속/증여)', 'icon': '👨‍👩‍👧'},
                {'key': 'mortgage', 'label': '근저당 설정/말소', 'icon': '🏦'},
                {'key': 'lease_right', 'label': '전세권 설정', 'icon': '📝'},
                {'key': 'auction', 'label': '경매 관련', 'icon': '🔨'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '진행 상황은?',
            'options': [
                {'key': 'gathering_info', 'label': '정보 수집 중', 'icon': '🔍'},
                {'key': 'contract_planned', 'label': '계약 예정', 'icon': '📅'},
                {'key': 'docs_ready', 'label': '계약 완료/서류 준비됨', 'icon': '✅'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '희망 처리 시기는?',
            'options': [
                {'key': 'within_week', 'label': '1주 내', 'icon': '🚀'},
                {'key': 'within_month', 'label': '1개월 내', 'icon': '📅'},
                {'key': 'flexible', 'label': '여유 있음', 'icon': '🕐'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '공인중개사': [
        {
            'step_number': 1,
            'question': '어떤 거래인가요?',
            'options': [
                {'key': 'sale', 'label': '매매', 'icon': '🏠'},
                {'key': 'jeonse', 'label': '전세', 'icon': '🔑'},
                {'key': 'monthly_rent', 'label': '월세', 'icon': '💵'},
                {'key': 'premium', 'label': '권리금/상가', 'icon': '🏪'},
                {'key': 'investment', 'label': '투자 상담', 'icon': '📊'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '부동산 종류는?',
            'options': [
                {'key': 'apartment', 'label': '아파트', 'icon': '🏢'},
                {'key': 'villa', 'label': '빌라/다세대', 'icon': '🏘️'},
                {'key': 'officetel', 'label': '오피스텔', 'icon': '🏨'},
                {'key': 'house', 'label': '단독/다가구', 'icon': '🏡'},
                {'key': 'commercial', 'label': '상가/사무실', 'icon': '🏪'},
                {'key': 'land', 'label': '토지', 'icon': '🌳'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '본인 입장은?',
            'options': [
                {'key': 'owner_sell', 'label': '집주인(매도/임대)', 'icon': '🏠'},
                {'key': 'tenant_buy', 'label': '세입자(매수/임차)', 'icon': '🔑'},
                {'key': 'investor', 'label': '투자 검토', 'icon': '📈'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '진행 상황은?',
            'options': [
                {'key': 'searching', 'label': '매물 탐색 중', 'icon': '🔍'},
                {'key': 'interested', 'label': '관심 매물 있음', 'icon': '❤️'},
                {'key': 'reviewing', 'label': '계약 검토 중', 'icon': '📋'},
                {'key': 'contract_stage', 'label': '계약서 작성 단계', 'icon': '✍️'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '인테리어': [
        {
            'step_number': 1,
            'question': '공간 유형은?',
            'options': [
                {'key': 'apartment', 'label': '아파트', 'icon': '🏢'},
                {'key': 'villa_house', 'label': '빌라/주택', 'icon': '🏡'},
                {'key': 'officetel', 'label': '오피스텔', 'icon': '🏨'},
                {'key': 'commercial', 'label': '상가/매장', 'icon': '🏪'},
                {'key': 'office', 'label': '사무실', 'icon': '💼'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '공사 범위는?',
            'options': [
                {'key': 'full_remodel', 'label': '전체 리모델링', 'icon': '🔨'},
                {'key': 'partial', 'label': '부분 공사', 'icon': '🛠️'},
                {'key': 'wallpaper_floor', 'label': '도배/장판만', 'icon': '🎨'},
                {'key': 'kitchen_bath', 'label': '주방/욕실', 'icon': '🚿'},
                {'key': 'extension', 'label': '확장/구조변경', 'icon': '📐'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '평수는?',
            'options': [
                {'key': 'under_10', 'label': '10평 미만', 'icon': '📏'},
                {'key': '10_to_20', 'label': '10~20평', 'icon': '📐'},
                {'key': '20_to_30', 'label': '20~30평', 'icon': '🏠'},
                {'key': '30_to_40', 'label': '30~40평', 'icon': '🏡'},
                {'key': 'over_40', 'label': '40평 이상', 'icon': '🏢'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '희망 시기는?',
            'options': [
                {'key': 'within_month', 'label': '1개월 내', 'icon': '🚀'},
                {'key': '1_to_3_months', 'label': '1~3개월', 'icon': '📅'},
                {'key': 'after_3_months', 'label': '3개월 이후', 'icon': '🕐'},
                {'key': 'estimate_only', 'label': '미정(견적만)', 'icon': '💰'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '청소 전문': [
        {
            'step_number': 1,
            'question': '청소 유형은?',
            'options': [
                {'key': 'move_in', 'label': '입주 청소', 'icon': '🏠'},
                {'key': 'move_out', 'label': '이사 청소', 'icon': '📦'},
                {'key': 'regular', 'label': '정기 청소', 'icon': '📅'},
                {'key': 'office', 'label': '사무실 청소', 'icon': '💼'},
                {'key': 'special', 'label': '특수 청소', 'icon': '✨', 'description': '에어컨, 세탁기 등'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '공간 유형은?',
            'options': [
                {'key': 'apartment', 'label': '아파트', 'icon': '🏢'},
                {'key': 'villa_house', 'label': '빌라/주택', 'icon': '🏡'},
                {'key': 'officetel', 'label': '오피스텔', 'icon': '🏨'},
                {'key': 'office_commercial', 'label': '사무실/상가', 'icon': '🏪'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '평수는?',
            'options': [
                {'key': 'under_10', 'label': '10평 미만', 'icon': '📏'},
                {'key': '10_to_20', 'label': '10~20평', 'icon': '📐'},
                {'key': '20_to_30', 'label': '20~30평', 'icon': '🏠'},
                {'key': '30_to_40', 'label': '30~40평', 'icon': '🏡'},
                {'key': 'over_40', 'label': '40평 이상', 'icon': '🏢'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '희망 일정은?',
            'options': [
                {'key': 'this_week', 'label': '이번 주', 'icon': '🚀'},
                {'key': 'next_week', 'label': '다음 주', 'icon': '📅'},
                {'key': 'after_2_weeks', 'label': '2주 이후', 'icon': '🕐'},
                {'key': 'estimate_only', 'label': '미정(견적만)', 'icon': '💰'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '이사 전문': [
        {
            'step_number': 1,
            'question': '이사 유형은?',
            'options': [
                {'key': 'home', 'label': '가정 이사', 'icon': '🏡'},
                {'key': 'office', 'label': '사무실 이전', 'icon': '🏢'},
                {'key': 'small', 'label': '원룸/소형 이사', 'icon': '📦'},
                {'key': 'long_distance', 'label': '장거리 이사', 'icon': '🚛'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 2,
            'question': '이사 방식은?',
            'options': [
                {'key': 'regular', 'label': '일반 이사', 'icon': '🚚'},
                {'key': 'packing', 'label': '포장 이사', 'icon': '📦'},
                {'key': 'storage', 'label': '보관 이사', 'icon': '🏭'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '현재 집 평수는?',
            'options': [
                {'key': 'studio', 'label': '원룸', 'icon': '🛏️'},
                {'key': '10_to_20', 'label': '10~20평', 'icon': '📐'},
                {'key': '20_to_30', 'label': '20~30평', 'icon': '🏠'},
                {'key': '30_to_40', 'label': '30~40평', 'icon': '🏡'},
                {'key': 'over_40', 'label': '40평 이상', 'icon': '🏢'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '이사 예정일은?',
            'options': [
                {'key': 'within_week', 'label': '1주 내', 'icon': '🚀'},
                {'key': '2_weeks_to_month', 'label': '2주~1개월', 'icon': '📅'},
                {'key': 'after_month', 'label': '1개월 이후', 'icon': '🕐'},
                {'key': 'estimate_only', 'label': '미정(견적만)', 'icon': '💰'},
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
    '자동차 정비': [
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

    for category_name, flows in CONSULTATION_FLOWS_DATA.items():
        try:
            category = LocalBusinessCategory.objects.get(name=category_name)
        except LocalBusinessCategory.DoesNotExist:
            print(f'카테고리 "{category_name}" 없음 - 건너뜀')
            continue

        for flow_data in flows:
            # 플로우 생성
            flow, created = ConsultationFlow.objects.update_or_create(
                category=category,
                step_number=flow_data['step_number'],
                defaults={
                    'question': flow_data['question'],
                    'is_required': flow_data.get('is_required', True),
                    'depends_on_step': flow_data.get('depends_on_step'),
                    'depends_on_options': flow_data.get('depends_on_options', []),
                    'is_active': True,
                }
            )

            # 기존 옵션 삭제 후 재생성
            ConsultationFlowOption.objects.filter(flow=flow).delete()

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

    print('상담 질문 플로우 초기 데이터 생성 완료')


def reverse_populate(apps, schema_editor):
    """롤백 시 데이터 삭제"""
    ConsultationFlow = apps.get_model('api', 'ConsultationFlow')
    ConsultationFlow.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0110_consultation_flow_models'),
    ]

    operations = [
        migrations.RunPython(populate_consultation_flows, reverse_populate),
    ]
