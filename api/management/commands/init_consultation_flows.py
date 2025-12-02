"""
상담 질문 플로우 초기화 명령어
python manage.py init_consultation_flows

목적 중심 플로우 설계:
1. 상담 목적 (무엇이 궁금한지/무엇을 원하는지)
2. 구체적 상황 (목적에 따른 세부 질문)
3. 긴급도/시기
4. 기본 정보 (환경적 정보)

참고: 세무통, 찾아줘세무사, 로톡, 짐싸, 집닥 등 실제 플랫폼 분석
"""
from django.core.management.base import BaseCommand
from api.models_local_business import LocalBusinessCategory
from api.models_consultation_flow import ConsultationFlow, ConsultationFlowOption


# 목적 중심 질문 플로우 데이터
CONSULTATION_FLOWS_DATA = {
    # ===== 세무·회계 =====
    '세무·회계': [
        {
            'step_number': 1,
            'question': '어떤 도움이 필요하세요?',
            'options': [
                {'key': 'tax_filing', 'label': '세금 신고 대행', 'icon': '📋', 'description': '종소세, 부가세, 법인세 등'},
                {'key': 'tax_saving', 'label': '절세 방법 상담', 'icon': '💰', 'description': '합법적 절세 전략'},
                {'key': 'bookkeeping', 'label': '기장/장부 관리', 'icon': '📝', 'description': '월별 세무 기장 대행'},
                {'key': 'business_start', 'label': '창업/사업자 관련', 'icon': '🚀', 'description': '사업자등록, 업종 선택 등'},
                {'key': 'tax_issue', 'label': '세무 문제 해결', 'icon': '🔍', 'description': '세무조사, 가산세 등'},
                {'key': 'other', 'label': '기타 상담', 'icon': '💬'},
            ]
        },
        # 세금 신고 대행 선택 시
        {
            'step_number': 2,
            'question': '어떤 세금 신고가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['tax_filing'],
            'options': [
                {'key': 'income_tax', 'label': '종합소득세', 'icon': '📊', 'description': '5월 신고'},
                {'key': 'vat', 'label': '부가가치세', 'icon': '📋', 'description': '1월/7월 신고'},
                {'key': 'corporate_tax', 'label': '법인세', 'icon': '🏢', 'description': '3월 신고'},
                {'key': 'withholding', 'label': '원천세', 'icon': '💳', 'description': '매월 신고'},
                {'key': 'transfer_tax', 'label': '양도소득세', 'icon': '🏠', 'description': '부동산/주식 양도'},
                {'key': 'inheritance', 'label': '상속/증여세', 'icon': '👨‍👩‍👧'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 절세 상담 선택 시
        {
            'step_number': 2,
            'question': '어떤 부분의 절세가 궁금하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['tax_saving'],
            'options': [
                {'key': 'income_deduction', 'label': '소득공제/세액공제', 'icon': '📉'},
                {'key': 'expense', 'label': '비용처리 방법', 'icon': '🧾'},
                {'key': 'business_type', 'label': '사업자 유형 선택', 'icon': '🏢', 'description': '개인 vs 법인'},
                {'key': 'family_business', 'label': '가족 급여/지분', 'icon': '👨‍👩‍👧'},
                {'key': 'retirement', 'label': '퇴직/연금 절세', 'icon': '🏖️'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 창업 관련 선택 시
        {
            'step_number': 2,
            'question': '어떤 창업 관련 상담이 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['business_start'],
            'options': [
                {'key': 'registration', 'label': '사업자등록 방법', 'icon': '📄'},
                {'key': 'business_type', 'label': '개인 vs 법인 선택', 'icon': '🤔'},
                {'key': 'tax_benefit', 'label': '창업 세제혜택', 'icon': '🎁'},
                {'key': 'initial_setup', 'label': '초기 세무 세팅', 'icon': '⚙️'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 세무 문제 선택 시
        {
            'step_number': 2,
            'question': '어떤 세무 문제인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['tax_issue'],
            'options': [
                {'key': 'tax_audit', 'label': '세무조사 대응', 'icon': '🔍'},
                {'key': 'penalty', 'label': '가산세 문제', 'icon': '⚠️'},
                {'key': 'correction', 'label': '수정신고/경정청구', 'icon': '✏️'},
                {'key': 'dispute', 'label': '과세 불복/이의신청', 'icon': '⚖️'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 기장 선택 시
        {
            'step_number': 2,
            'question': '현재 기장 상황은?',
            'depends_on_step': 1,
            'depends_on_options': ['bookkeeping'],
            'options': [
                {'key': 'new', 'label': '처음 맡기려고 함', 'icon': '✨'},
                {'key': 'change', 'label': '기존 세무사 변경', 'icon': '🔄'},
                {'key': 'self_to_pro', 'label': '직접 하다가 맡기려고', 'icon': '📊'},
                {'key': 'inquiry', 'label': '비용/서비스 문의', 'icon': '💰'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 기타 선택 시 - 자유 입력 유도
        {
            'step_number': 2,
            'question': '어떤 상담이 필요하신지 간단히 적어주세요',
            'depends_on_step': 1,
            'depends_on_options': ['other'],
            'options': [
                {'key': 'custom', 'label': '상담 내용 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '얼마나 급하세요?',
            'options': [
                {'key': 'very_urgent', 'label': '매우 급함', 'icon': '🚨', 'description': '신고기한 1주일 이내'},
                {'key': 'urgent', 'label': '빠른 처리 필요', 'icon': '⏰', 'description': '이번 달 내'},
                {'key': 'normal', 'label': '여유 있음', 'icon': '📅', 'description': '상담 후 결정'},
                {'key': 'just_inquiry', 'label': '단순 문의/비교', 'icon': '💬'},
            ]
        },
        {
            'step_number': 4,
            'question': '사업 형태는?',
            'options': [
                {'key': 'sole_proprietor', 'label': '개인사업자', 'icon': '👤'},
                {'key': 'freelancer', 'label': '프리랜서/3.3%', 'icon': '💼'},
                {'key': 'corporation', 'label': '법인사업자', 'icon': '🏢'},
                {'key': 'prospective', 'label': '예비창업자', 'icon': '🚀'},
                {'key': 'individual', 'label': '일반 개인', 'icon': '🙋'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],

    # ===== 법률 서비스 =====
    '법률 서비스': [
        {
            'step_number': 1,
            'question': '어떤 법률 문제인가요?',
            'options': [
                {'key': 'civil', 'label': '민사 (계약/손해배상)', 'icon': '📄', 'description': '금전, 계약, 손해배상 등'},
                {'key': 'family', 'label': '가사 (이혼/상속)', 'icon': '👨‍👩‍👧', 'description': '이혼, 양육권, 상속 등'},
                {'key': 'criminal', 'label': '형사 사건', 'icon': '🚔', 'description': '고소, 피의자, 피해자'},
                {'key': 'real_estate', 'label': '부동산 문제', 'icon': '🏠', 'description': '매매, 임대차, 등기'},
                {'key': 'labor', 'label': '노동/근로 문제', 'icon': '👷', 'description': '해고, 임금, 산재'},
                {'key': 'corporate', 'label': '기업/사업 관련', 'icon': '🏢', 'description': '법인설립, 계약검토'},
                {'key': 'other', 'label': '기타 법률 상담', 'icon': '⚖️'},
            ]
        },
        # 민사 선택 시
        {
            'step_number': 2,
            'question': '어떤 민사 문제인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['civil'],
            'options': [
                {'key': 'money', 'label': '돈 못 받음 (채권추심)', 'icon': '💸'},
                {'key': 'contract', 'label': '계약 분쟁', 'icon': '📋'},
                {'key': 'damage', 'label': '손해배상 청구', 'icon': '💔'},
                {'key': 'guarantee', 'label': '보증/담보 문제', 'icon': '🤝'},
                {'key': 'injunction', 'label': '가압류/가처분', 'icon': '🔒'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 가사 선택 시
        {
            'step_number': 2,
            'question': '어떤 가사 문제인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['family'],
            'options': [
                {'key': 'divorce', 'label': '이혼 상담', 'icon': '💔'},
                {'key': 'alimony', 'label': '위자료/재산분할', 'icon': '💰'},
                {'key': 'custody', 'label': '양육권/면접교섭', 'icon': '👶'},
                {'key': 'inheritance', 'label': '상속/유언', 'icon': '📜'},
                {'key': 'adoption', 'label': '입양/친자관계', 'icon': '👨‍👩‍👧'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 형사 선택 시
        {
            'step_number': 2,
            'question': '어떤 상황인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['criminal'],
            'options': [
                {'key': 'accused', 'label': '피의자/피고인 (고소당함)', 'icon': '😰'},
                {'key': 'victim', 'label': '피해자 (고소하려고)', 'icon': '😢'},
                {'key': 'investigation', 'label': '경찰/검찰 조사 예정', 'icon': '🔍'},
                {'key': 'defense', 'label': '재판 변호 필요', 'icon': '⚖️'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 부동산 선택 시
        {
            'step_number': 2,
            'question': '어떤 부동산 문제인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['real_estate'],
            'options': [
                {'key': 'contract', 'label': '매매 계약 분쟁', 'icon': '📋'},
                {'key': 'lease', 'label': '임대차 분쟁', 'icon': '🏠'},
                {'key': 'deposit', 'label': '보증금 반환', 'icon': '💰'},
                {'key': 'registration', 'label': '등기 문제', 'icon': '📄'},
                {'key': 'defect', 'label': '하자/누수 문제', 'icon': '💧'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 노동 선택 시
        {
            'step_number': 2,
            'question': '어떤 노동 문제인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['labor'],
            'options': [
                {'key': 'dismissal', 'label': '해고/권고사직', 'icon': '🚪'},
                {'key': 'wage', 'label': '임금 체불', 'icon': '💸'},
                {'key': 'severance', 'label': '퇴직금 문제', 'icon': '💰'},
                {'key': 'harassment', 'label': '직장 내 괴롭힘', 'icon': '😢'},
                {'key': 'accident', 'label': '산업재해', 'icon': '🏥'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 기업 선택 시
        {
            'step_number': 2,
            'question': '어떤 기업 법률 서비스가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['corporate'],
            'options': [
                {'key': 'incorporation', 'label': '법인 설립', 'icon': '🏢'},
                {'key': 'contract_review', 'label': '계약서 검토/작성', 'icon': '📋'},
                {'key': 'dispute', 'label': '사업상 분쟁', 'icon': '⚔️'},
                {'key': 'compliance', 'label': '법률 자문', 'icon': '📚'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 기타 선택 시
        {
            'step_number': 2,
            'question': '어떤 법률 상담이 필요하신지 적어주세요',
            'depends_on_step': 1,
            'depends_on_options': ['other'],
            'options': [
                {'key': 'custom', 'label': '상담 내용 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '현재 상황은?',
            'options': [
                {'key': 'urgent', 'label': '급함 (소송/고소 진행 중)', 'icon': '🚨'},
                {'key': 'preparing', 'label': '소송/고소 준비 중', 'icon': '📋'},
                {'key': 'consulting', 'label': '상담만 먼저', 'icon': '💬'},
                {'key': 'document', 'label': '서류 검토/작성만', 'icon': '📄'},
                {'key': 'prevention', 'label': '예방/사전 대비', 'icon': '🛡️'},
            ]
        },
        {
            'step_number': 4,
            'question': '예상 분쟁 금액은?',
            'is_required': False,
            'options': [
                {'key': 'under_10m', 'label': '1천만원 미만', 'icon': '💵'},
                {'key': '10m_to_50m', 'label': '1천~5천만원', 'icon': '💰'},
                {'key': '50m_to_100m', 'label': '5천만~1억', 'icon': '💎'},
                {'key': 'over_100m', 'label': '1억 이상', 'icon': '🏆'},
                {'key': 'non_monetary', 'label': '금전 문제 아님', 'icon': '📋'},
                {'key': 'unknown', 'label': '잘 모르겠음', 'icon': '🤔'},
            ]
        },
    ],

    # ===== 청소·이사 =====
    '청소·이사': [
        {
            'step_number': 1,
            'question': '어떤 서비스가 필요하세요?',
            'options': [
                {'key': 'moving', 'label': '이사', 'icon': '🚚', 'description': '포장이사, 반포장이사 등'},
                {'key': 'cleaning', 'label': '청소', 'icon': '🧹', 'description': '입주청소, 이사청소 등'},
                {'key': 'both', 'label': '이사 + 청소 함께', 'icon': '✨'},
            ]
        },
        # 이사 선택 시
        {
            'step_number': 2,
            'question': '어떤 이사 서비스가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['moving', 'both'],
            'options': [
                {'key': 'full_packing', 'label': '포장이사', 'icon': '📦', 'description': '전문 포장 + 운반'},
                {'key': 'semi_packing', 'label': '반포장이사', 'icon': '📋', 'description': '일부 포장 + 운반'},
                {'key': 'basic', 'label': '일반이사', 'icon': '🚚', 'description': '운반만'},
                {'key': 'small', 'label': '소형이사/원룸', 'icon': '🏠'},
                {'key': 'office', 'label': '사무실 이사', 'icon': '🏢'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 청소 선택 시
        {
            'step_number': 2,
            'question': '어떤 청소 서비스가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['cleaning'],
            'options': [
                {'key': 'move_in', 'label': '입주 청소', 'icon': '🏠', 'description': '새 집 입주 전'},
                {'key': 'move_out', 'label': '이사 청소', 'icon': '📦', 'description': '이사 후 원상복구'},
                {'key': 'regular', 'label': '정기 청소', 'icon': '🗓️'},
                {'key': 'deep', 'label': '대청소', 'icon': '✨'},
                {'key': 'special', 'label': '특수 청소', 'icon': '🧽', 'description': '에어컨, 새집증후군 등'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '공간 크기는?',
            'options': [
                {'key': 'studio', 'label': '원룸/오피스텔', 'icon': '🛏️'},
                {'key': 'small', 'label': '투룸/20평 미만', 'icon': '🏠'},
                {'key': 'medium', 'label': '20~30평', 'icon': '🏡'},
                {'key': 'large', 'label': '30~40평', 'icon': '🏘️'},
                {'key': 'xlarge', 'label': '40평 이상', 'icon': '🏰'},
                {'key': 'office', 'label': '사무실/상가', 'icon': '🏢'},
            ]
        },
        {
            'step_number': 4,
            'question': '희망 날짜는?',
            'options': [
                {'key': 'asap', 'label': '최대한 빨리', 'icon': '🚨'},
                {'key': 'this_week', 'label': '이번 주', 'icon': '📅'},
                {'key': 'next_week', 'label': '다음 주', 'icon': '🗓️'},
                {'key': 'this_month', 'label': '이번 달 내', 'icon': '📆'},
                {'key': 'specific', 'label': '날짜 정해짐', 'icon': '✅'},
                {'key': 'flexible', 'label': '협의 가능', 'icon': '🤝'},
            ]
        },
        {
            'step_number': 5,
            'question': '특별히 요청하실 사항이 있나요?',
            'is_required': False,
            'depends_on_step': 1,
            'depends_on_options': ['moving', 'both'],
            'options': [
                {'key': 'piano', 'label': '피아노/대형가전', 'icon': '🎹'},
                {'key': 'storage', 'label': '짐 보관 필요', 'icon': '📦'},
                {'key': 'disposal', 'label': '폐기물 처리', 'icon': '🗑️'},
                {'key': 'long_distance', 'label': '장거리 이사', 'icon': '🛣️'},
                {'key': 'none', 'label': '특별 요청 없음', 'icon': '✅'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
    ],

    # ===== 공인중개사 =====
    '공인중개사': [
        # Step 1: 목적 + 거래유형 통합
        {
            'step_number': 1,
            'question': '어떤 도움이 필요하세요?',
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
    ],


    # ===== 인테리어 =====
    '인테리어': [
        {
            'step_number': 1,
            'question': '어떤 인테리어가 필요하세요?',
            'options': [
                {'key': 'full', 'label': '전체 리모델링', 'icon': '🏗️', 'description': '올수리, 전체 공사'},
                {'key': 'partial', 'label': '부분 공사', 'icon': '🔨', 'description': '특정 공간만'},
                {'key': 'move_in', 'label': '입주 전 수리', 'icon': '🏠', 'description': '도배, 장판 등'},
                {'key': 'store', 'label': '상가 인테리어', 'icon': '🏪'},
                {'key': 'consulting', 'label': '견적/상담만', 'icon': '💬'},
            ]
        },
        # 부분 공사 선택 시
        {
            'step_number': 2,
            'question': '어떤 공사가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['partial', 'move_in'],
            'options': [
                {'key': 'wallpaper', 'label': '도배', 'icon': '🎨'},
                {'key': 'floor', 'label': '바닥 (장판/마루)', 'icon': '🪵'},
                {'key': 'kitchen', 'label': '주방', 'icon': '🍳'},
                {'key': 'bathroom', 'label': '욕실', 'icon': '🚿'},
                {'key': 'veranda', 'label': '베란다 확장', 'icon': '🌿'},
                {'key': 'multiple', 'label': '복합 (여러 가지)', 'icon': '📋'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 전체 리모델링 선택 시
        {
            'step_number': 2,
            'question': '현재 집 상태는?',
            'depends_on_step': 1,
            'depends_on_options': ['full'],
            'options': [
                {'key': 'old', 'label': '오래된 집 (20년+)', 'icon': '🏚️'},
                {'key': 'medium', 'label': '10~20년 된 집', 'icon': '🏠'},
                {'key': 'recent', 'label': '10년 미만', 'icon': '🏡'},
                {'key': 'new', 'label': '신축/입주 전', 'icon': '✨'},
            ]
        },
        # 상가 선택 시
        {
            'step_number': 2,
            'question': '어떤 업종인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['store'],
            'options': [
                {'key': 'restaurant', 'label': '음식점/카페', 'icon': '☕'},
                {'key': 'retail', 'label': '판매/소매점', 'icon': '🛍️'},
                {'key': 'office', 'label': '사무실', 'icon': '💼'},
                {'key': 'beauty', 'label': '미용/뷰티', 'icon': '💅'},
                {'key': 'clinic', 'label': '병원/의원', 'icon': '🏥'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 상담만 선택 시
        {
            'step_number': 2,
            'question': '어떤 상담이 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['consulting'],
            'options': [
                {'key': 'estimate', 'label': '견적 비교', 'icon': '💰'},
                {'key': 'design', 'label': '디자인 상담', 'icon': '🎨'},
                {'key': 'material', 'label': '자재 추천', 'icon': '🧱'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '공간 크기는?',
            'options': [
                {'key': 'small', 'label': '20평 미만', 'icon': '📐'},
                {'key': 'medium', 'label': '20~30평', 'icon': '📏'},
                {'key': 'large', 'label': '30~40평', 'icon': '🏠'},
                {'key': 'xlarge', 'label': '40평 이상', 'icon': '🏡'},
            ]
        },
        {
            'step_number': 4,
            'question': '예산은?',
            'options': [
                {'key': 'under_5m', 'label': '500만원 미만', 'icon': '💵'},
                {'key': '5m_10m', 'label': '500~1000만원', 'icon': '💰'},
                {'key': '10m_30m', 'label': '1000~3000만원', 'icon': '💎'},
                {'key': '30m_50m', 'label': '3000~5000만원', 'icon': '🏆'},
                {'key': 'over_50m', 'label': '5000만원 이상', 'icon': '👑'},
                {'key': 'undecided', 'label': '상담 후 결정', 'icon': '🤔'},
            ]
        },
        {
            'step_number': 5,
            'question': '공사 희망 시기는?',
            'options': [
                {'key': 'asap', 'label': '최대한 빨리', 'icon': '🚨'},
                {'key': 'month', 'label': '1개월 내', 'icon': '📅'},
                {'key': '3months', 'label': '3개월 내', 'icon': '🗓️'},
                {'key': 'flexible', 'label': '여유 있음', 'icon': '🤝'},
            ]
        },
    ],

    # ===== 휴대폰 대리점 =====
    # 4가지 주요 상품 + 지원금 문의 플로우
    '휴대폰 대리점': [
        # Step 1: 메인 상품 선택
        {
            'step_number': 1,
            'question': '어떤 상품이 필요하세요?',
            'options': [
                {'key': 'phone', 'label': '휴대폰', 'icon': '📱', 'description': '휴대폰만 개통/변경'},
                {'key': 'internet', 'label': '인터넷', 'icon': '🌐', 'description': '인터넷만 가입/변경'},
                {'key': 'internet_tv', 'label': '인터넷 + TV', 'icon': '📺', 'description': '인터넷, TV 결합'},
                {'key': 'triple', 'label': '휴대폰 + 인터넷 + TV', 'icon': '🏠', 'description': '트리플 결합 할인'},
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
        # ===== Step 3: 지원금/혜택 문의 (공통) =====
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
                {'key': 'skt', 'label': 'SK브로드밴드', 'logo': '/logos/skt.png'},
                {'key': 'kt', 'label': 'KT', 'logo': '/logos/kt.png'},
                {'key': 'lgu', 'label': 'LG U+', 'logo': '/logos/lgu.png'},
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
                {'key': 'skt', 'label': 'SKT', 'logo': '/logos/skt.png'},
                {'key': 'kt', 'label': 'KT', 'logo': '/logos/kt.png'},
                {'key': 'lgu', 'label': 'LG U+', 'logo': '/logos/lgu.png'},
                {'key': 'compare', 'label': '비교 후 결정', 'icon': '⚖️'},
            ]
        },
    ],

    # ===== 정비소 =====
    '정비소': [
        {
            'step_number': 1,
            'question': '어떤 서비스가 필요하세요?',
            'options': [
                {'key': 'repair', 'label': '고장/수리', 'icon': '🔧', 'description': '문제가 생겼어요'},
                {'key': 'maintenance', 'label': '정기 점검/소모품', 'icon': '🛠️', 'description': '엔진오일, 타이어 등'},
                {'key': 'accident', 'label': '사고 수리', 'icon': '🚗'},
                {'key': 'inspection', 'label': '자동차 검사', 'icon': '📋'},
                {'key': 'other', 'label': '기타 문의', 'icon': '💬'},
            ]
        },
        # 고장 선택 시
        {
            'step_number': 2,
            'question': '어떤 증상인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['repair'],
            'options': [
                {'key': 'engine', 'label': '시동/엔진 문제', 'icon': '🔑'},
                {'key': 'noise', 'label': '이상 소음', 'icon': '🔊'},
                {'key': 'warning', 'label': '경고등 켜짐', 'icon': '⚠️'},
                {'key': 'brake', 'label': '브레이크 문제', 'icon': '🛑'},
                {'key': 'ac', 'label': '에어컨/히터', 'icon': '❄️'},
                {'key': 'electric', 'label': '전기/배터리', 'icon': '🔋'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 정비 선택 시
        {
            'step_number': 2,
            'question': '어떤 정비가 필요하세요?',
            'depends_on_step': 1,
            'depends_on_options': ['maintenance'],
            'options': [
                {'key': 'oil', 'label': '엔진오일 교체', 'icon': '🛢️'},
                {'key': 'tire', 'label': '타이어 교체/정비', 'icon': '⚙️'},
                {'key': 'brake_pad', 'label': '브레이크 패드', 'icon': '🛑'},
                {'key': 'filter', 'label': '각종 필터 교체', 'icon': '🔄'},
                {'key': 'full_checkup', 'label': '종합 점검', 'icon': '📋'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        # 사고 선택 시
        {
            'step_number': 2,
            'question': '어떤 사고 수리인가요?',
            'depends_on_step': 1,
            'depends_on_options': ['accident'],
            'options': [
                {'key': 'minor', 'label': '경미한 접촉사고', 'icon': '🚗'},
                {'key': 'dent', 'label': '찌그러짐/덴트', 'icon': '🔨'},
                {'key': 'paint', 'label': '도색/스크래치', 'icon': '🎨'},
                {'key': 'major', 'label': '큰 사고 수리', 'icon': '🚧'},
                {'key': 'custom', 'label': '직접 입력', 'icon': '📝', 'is_custom_input': True},
            ]
        },
        {
            'step_number': 3,
            'question': '차량 종류는?',
            'options': [
                {'key': 'domestic_small', 'label': '국산 소형', 'icon': '🚗'},
                {'key': 'domestic_mid', 'label': '국산 중형/대형', 'icon': '🚙'},
                {'key': 'domestic_suv', 'label': '국산 SUV', 'icon': '🚐'},
                {'key': 'imported', 'label': '수입차', 'icon': '🏎️'},
                {'key': 'ev', 'label': '전기차/하이브리드', 'icon': '⚡'},
            ]
        },
        {
            'step_number': 4,
            'question': '얼마나 급하세요?',
            'options': [
                {'key': 'urgent', 'label': '지금 당장 (운행 불가)', 'icon': '🚨'},
                {'key': 'soon', 'label': '이번 주 내', 'icon': '📅'},
                {'key': 'normal', 'label': '시간 여유 있음', 'icon': '🕐'},
                {'key': 'estimate', 'label': '견적만 먼저', 'icon': '💰'},
            ]
        },
    ],
}


# 통합 카테고리 → 실제 DB 카테고리 매핑
CATEGORY_MAPPING = {
    '세무·회계': ['세무사', '회계사'],
    '법률 서비스': ['변호사', '법무사'],
    '청소·이사': ['청소업체', '이사업체'],
}


class Command(BaseCommand):
    help = '상담 질문 플로우 데이터 초기화 (목적 중심 설계)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='기존 데이터 삭제 후 새로 생성',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('기존 상담 플로우 데이터 삭제 중...')
            ConsultationFlow.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('기존 데이터 삭제 완료'))

        created_count = 0
        skipped_count = 0

        for category_name, flows in CONSULTATION_FLOWS_DATA.items():
            # 통합 카테고리인 경우 실제 DB 카테고리들에 각각 생성
            actual_categories = CATEGORY_MAPPING.get(category_name, [category_name])

            for actual_category_name in actual_categories:
                try:
                    category = LocalBusinessCategory.objects.get(name=actual_category_name)
                except LocalBusinessCategory.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'카테고리 "{actual_category_name}" 없음 - 건너뜀')
                    )
                    skipped_count += 1
                    continue

                # 해당 카테고리의 기존 플로우 확인
                existing_count = ConsultationFlow.objects.filter(category=category).count()
                if existing_count > 0 and not options['clear']:
                    self.stdout.write(
                        f'카테고리 "{actual_category_name}"에 이미 {existing_count}개 플로우 있음 - 건너뜀'
                    )
                    continue

                # 기존 데이터 삭제 (clear 옵션 없어도 해당 카테고리는 삭제)
                ConsultationFlow.objects.filter(category=category).delete()

                # 플로우 생성
                for idx, flow_data in enumerate(flows):
                    flow = ConsultationFlow.objects.create(
                        category=category,
                        step_number=flow_data['step_number'],
                        question=flow_data['question'],
                        is_required=flow_data.get('is_required', True),
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

                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'카테고리 "{actual_category_name}" 플로우 생성 완료 ({len(flows)}개 질문)')
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'완료: {created_count}개 카테고리 생성, {skipped_count}개 건너뜀'))
