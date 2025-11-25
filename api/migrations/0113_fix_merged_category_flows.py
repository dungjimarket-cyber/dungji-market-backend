# Generated manually - 통합 카테고리 플로우 수정 (1단계 세부업종 선택)

from django.db import migrations


# 통합 카테고리용 질문 플로우 데이터
# 1단계에서 세부 업종 선택 후, 조건부로 다른 질문 표시
CONSULTATION_FLOWS_DATA = {
    '세무·회계': [
        {
            'step_number': 1,
            'question': '어떤 전문가가 필요하세요?',
            'options': [
                {'key': 'tax', 'label': '세무사', 'icon': '📊', 'description': '세금 신고, 절세, 기장대행 등'},
                {'key': 'accounting', 'label': '회계사', 'icon': '📈', 'description': '재무제표, 회계감사, 경영컨설팅 등'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 세무사 선택 시 질문들
        {
            'step_number': 2,
            'question': '어떤 세무 업무가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['tax'],
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
        # 회계사 선택 시 질문들
        {
            'step_number': 2,
            'question': '어떤 회계 업무가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['accounting'],
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
            'step_number': 3,
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
            'step_number': 4,
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
            'step_number': 5,
            'question': '현재 상황은?',
            'options': [
                {'key': 'new_request', 'label': '신규 의뢰', 'icon': '✨'},
                {'key': 'change_expert', 'label': '기존 담당자 변경', 'icon': '🔄'},
                {'key': 'simple_inquiry', 'label': '단순 문의', 'icon': '❓'},
                {'key': 'urgent', 'label': '급한 처리 필요', 'icon': '🚨'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '법률 서비스': [
        {
            'step_number': 1,
            'question': '어떤 전문가가 필요하세요?',
            'options': [
                {'key': 'lawyer', 'label': '변호사', 'icon': '⚖️', 'description': '소송, 법률자문, 형사사건 등'},
                {'key': 'judicial_scrivener', 'label': '법무사', 'icon': '📋', 'description': '등기, 법인설립, 내용증명 등'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 변호사 선택 시 질문들
        {
            'step_number': 2,
            'question': '어떤 법률 분야인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['lawyer'],
            'options': [
                {'key': 'contract', 'label': '계약/채권', 'icon': '📄'},
                {'key': 'damage', 'label': '손해배상', 'icon': '💔'},
                {'key': 'real_estate', 'label': '부동산', 'icon': '🏠'},
                {'key': 'family', 'label': '가사/이혼', 'icon': '👨‍👩‍👧'},
                {'key': 'labor', 'label': '노동', 'icon': '👷'},
                {'key': 'criminal', 'label': '형사', 'icon': '🚔'},
                {'key': 'corporate', 'label': '기업법무', 'icon': '🏢'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 법무사 선택 시 질문들
        {
            'step_number': 2,
            'question': '어떤 법무 업무가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['judicial_scrivener'],
            'options': [
                {'key': 'real_estate_reg', 'label': '부동산 등기', 'icon': '🏠'},
                {'key': 'corporate_reg', 'label': '법인등기', 'icon': '🏢'},
                {'key': 'incorporation', 'label': '법인설립', 'icon': '✨'},
                {'key': 'certified_doc', 'label': '내용증명', 'icon': '📄'},
                {'key': 'small_claims', 'label': '민사서류 작성', 'icon': '📝'},
                {'key': 'divorce_doc', 'label': '이혼서류', 'icon': '👨‍👩‍👧'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 변호사: 본인 입장
        {
            'step_number': 3,
            'question': '본인의 입장은?',
            'depends_on_step': 1,
            'depends_on_options': ['lawyer'],
            'options': [
                {'key': 'plaintiff', 'label': '청구/소제기 측', 'icon': '⚔️'},
                {'key': 'defendant', 'label': '피소/대응 측', 'icon': '🛡️'},
                {'key': 'consultation', 'label': '상담만 필요', 'icon': '💬'},
                {'key': 'document', 'label': '서류 검토만', 'icon': '📝'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 법무사: 상황
        {
            'step_number': 3,
            'question': '현재 상황은?',
            'depends_on_step': 1,
            'depends_on_options': ['judicial_scrivener'],
            'options': [
                {'key': 'buying', 'label': '부동산 매수 예정', 'icon': '🏠'},
                {'key': 'selling', 'label': '부동산 매도 예정', 'icon': '💰'},
                {'key': 'starting_business', 'label': '사업 시작 예정', 'icon': '🚀'},
                {'key': 'document_needed', 'label': '서류 작성 필요', 'icon': '📄'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 4,
            'question': '분쟁 금액/규모는?',
            'depends_on_step': 1,
            'depends_on_options': ['lawyer'],
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
            'question': '예상 비용은?',
            'depends_on_step': 1,
            'depends_on_options': ['judicial_scrivener'],
            'options': [
                {'key': 'under_500k', 'label': '50만원 미만', 'icon': '💵'},
                {'key': '500k_to_1m', 'label': '50~100만원', 'icon': '💰'},
                {'key': '1m_to_3m', 'label': '100~300만원', 'icon': '💎'},
                {'key': 'over_3m', 'label': '300만원 이상', 'icon': '🏆'},
                {'key': 'unknown', 'label': '모름/상담 후 결정', 'icon': '🤔'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 5,
            'question': '시급성은?',
            'options': [
                {'key': 'urgent', 'label': '급함 (기한 임박)', 'icon': '🚨'},
                {'key': 'within_month', 'label': '한 달 이내', 'icon': '📅'},
                {'key': 'flexible', 'label': '여유 있음', 'icon': '🕐'},
                {'key': 'prevention', 'label': '예방/준비 차원', 'icon': '🛡️'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],
    '청소·이사': [
        {
            'step_number': 1,
            'question': '어떤 서비스가 필요하세요?',
            'options': [
                {'key': 'moving', 'label': '이사 서비스', 'icon': '🚚', 'description': '가정/사무실 이사, 포장이사 등'},
                {'key': 'cleaning', 'label': '청소 서비스', 'icon': '🧹', 'description': '입주청소, 정기청소, 특수청소 등'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 이사 선택 시 질문들
        {
            'step_number': 2,
            'question': '어떤 이사인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['moving'],
            'options': [
                {'key': 'home_move', 'label': '가정 이사', 'icon': '🏠'},
                {'key': 'office_move', 'label': '사무실 이사', 'icon': '🏢'},
                {'key': 'small_move', 'label': '원룸/소형 이사', 'icon': '📦'},
                {'key': 'long_distance', 'label': '장거리 이사', 'icon': '🚛'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 청소 선택 시 질문들
        {
            'step_number': 2,
            'question': '어떤 청소가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['cleaning'],
            'options': [
                {'key': 'move_in', 'label': '입주 청소', 'icon': '🏠'},
                {'key': 'move_out', 'label': '이사 청소', 'icon': '📦'},
                {'key': 'regular', 'label': '정기 청소', 'icon': '✨'},
                {'key': 'special', 'label': '특수 청소', 'icon': '🧽', 'description': '에어컨, 새집증후군 등'},
                {'key': 'office', 'label': '사무실/상가 청소', 'icon': '🏢'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
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
            'step_number': 4,
            'question': '희망 날짜는?',
            'options': [
                {'key': 'this_week', 'label': '이번 주', 'icon': '📅'},
                {'key': 'next_week', 'label': '다음 주', 'icon': '🗓️'},
                {'key': 'within_month', 'label': '한 달 이내', 'icon': '📆'},
                {'key': 'specific_date', 'label': '특정 날짜 지정', 'icon': '✅'},
                {'key': 'flexible', 'label': '협의 가능', 'icon': '🤝'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 이사: 추가 서비스
        {
            'step_number': 5,
            'question': '추가 서비스가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['moving'],
            'options': [
                {'key': 'packing', 'label': '포장 서비스', 'icon': '📦'},
                {'key': 'storage', 'label': '보관 서비스', 'icon': '🏪'},
                {'key': 'disposal', 'label': '폐기물 처리', 'icon': '🗑️'},
                {'key': 'cleaning_too', 'label': '청소도 함께', 'icon': '🧹'},
                {'key': 'none', 'label': '없음', 'icon': '✅'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 청소: 추가 요청
        {
            'step_number': 5,
            'question': '추가 요청사항은?',
            'depends_on_step': 1,
            'depends_on_options': ['cleaning'],
            'options': [
                {'key': 'window', 'label': '외부 창문 청소', 'icon': '🪟'},
                {'key': 'balcony', 'label': '베란다/발코니', 'icon': '🌿'},
                {'key': 'aircon', 'label': '에어컨 청소', 'icon': '❄️'},
                {'key': 'kitchen_deep', 'label': '주방 집중 청소', 'icon': '🍳'},
                {'key': 'none', 'label': '없음', 'icon': '✅'},
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
    """상담 질문 플로우 데이터 생성 (통합 카테고리 지원)"""
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

        # step_number + depends_on 조합으로 고유 식별
        # 같은 step_number라도 depends_on이 다르면 다른 flow로 생성
        for idx, flow_data in enumerate(flows):
            # 플로우 생성
            flow = ConsultationFlow.objects.create(
                category=category,
                step_number=flow_data['step_number'],
                question=flow_data['question'],
                is_required=flow_data.get('is_required', True),
                depends_on_step=flow_data.get('depends_on_step'),
                depends_on_options=flow_data.get('depends_on_options', []),
                order_index=idx,  # 순서 보장용
                is_active=True,
            )

            # 옵션 생성
            for opt_idx, option_data in enumerate(flow_data.get('options', [])):
                ConsultationFlowOption.objects.create(
                    flow=flow,
                    key=option_data['key'],
                    label=option_data['label'],
                    icon=option_data.get('icon', ''),
                    description=option_data.get('description', ''),
                    is_custom_input=option_data.get('is_custom_input', False),
                    order_index=opt_idx,
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
        ('api', '0112_fix_consultation_flows'),
    ]

    operations = [
        # 먼저 unique_together 제약 제거 (같은 step_number에 조건부 질문 여러 개 허용)
        migrations.AlterUniqueTogether(
            name='consultationflow',
            unique_together=set(),
        ),
        # 그 다음 데이터 생성
        migrations.RunPython(populate_consultation_flows, reverse_populate),
    ]
