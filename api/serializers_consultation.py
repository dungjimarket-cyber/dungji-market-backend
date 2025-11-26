"""
상담 신청 관련 시리얼라이저
"""
from rest_framework import serializers
from .models_consultation import ConsultationType, ConsultationRequest
from .models_consultation_flow import ConsultationFlow, ConsultationFlowOption
from .models_local_business import LocalBusinessCategory


class ConsultationTypeSerializer(serializers.ModelSerializer):
    """상담 유형 시리얼라이저"""
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = ConsultationType
        fields = [
            'id', 'name', 'description', 'icon',
            'category', 'category_name', 'order_index'
        ]
        read_only_fields = ['id']


class ConsultationRequestCreateSerializer(serializers.ModelSerializer):
    """상담 신청 생성용 시리얼라이저 (비회원도 사용 가능)"""
    category = serializers.CharField()  # ID 또는 이름 허용

    class Meta:
        model = ConsultationRequest
        fields = [
            'name', 'phone', 'email',
            'category', 'consultation_type', 'region',
            'content', 'ai_summary', 'ai_recommended_types'
        ]

    def validate_category(self, value):
        """카테고리 검증 - ID, 이름, 통합 카테고리 ID 지원"""
        from django.db.models import Q

        # 통합 카테고리 매핑 (프론트엔드 가상 ID → 실제 DB 카테고리명)
        MERGED_CATEGORY_MAP = {
            'tax_accounting': '세무사',
            'legal_service': '변호사',
            'cleaning_moving': '청소 전문',
            '세무·회계': '세무사',
            '법률 서비스': '변호사',
            '청소·이사': '청소 전문',
        }

        # 숫자면 ID로 검색
        if str(value).isdigit():
            try:
                return LocalBusinessCategory.objects.get(id=int(value))
            except LocalBusinessCategory.DoesNotExist:
                raise serializers.ValidationError('존재하지 않는 카테고리입니다.')

        # 통합 카테고리 매핑 확인
        if value in MERGED_CATEGORY_MAP:
            real_category_name = MERGED_CATEGORY_MAP[value]
            category = LocalBusinessCategory.objects.filter(name=real_category_name).first()
            if category:
                return category

        # 문자열이면 이름/google_place_type으로 검색
        category = LocalBusinessCategory.objects.filter(
            Q(google_place_type__iexact=value) |
            Q(name__iexact=value) |
            Q(name_en__iexact=value)
        ).first()

        if not category:
            raise serializers.ValidationError(f'카테고리를 찾을 수 없습니다: {value}')

        return category

    def validate_phone(self, value):
        """전화번호 형식 검증"""
        import re
        phone = re.sub(r'[^0-9]', '', value)
        if len(phone) < 10 or len(phone) > 11:
            raise serializers.ValidationError('올바른 전화번호를 입력해주세요.')
        return value

    def validate_content(self, value):
        """상담 내용 최소 길이 검증"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError('상담 내용을 10자 이상 입력해주세요.')
        return value

    def create(self, validated_data):
        # 로그인한 사용자가 있으면 연결
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class ConsultationRequestListSerializer(serializers.ModelSerializer):
    """상담 신청 목록용 시리얼라이저"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    consultation_type_name = serializers.CharField(
        source='consultation_type.name',
        read_only=True,
        default=None
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ConsultationRequest
        fields = [
            'id', 'name', 'phone', 'email',
            'category', 'category_name', 'category_icon',
            'consultation_type', 'consultation_type_name',
            'region', 'status', 'status_display',
            'created_at'
        ]


class ConsultationRequestDetailSerializer(serializers.ModelSerializer):
    """상담 신청 상세용 시리얼라이저 (관리자용)"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    consultation_type_name = serializers.CharField(
        source='consultation_type.name',
        read_only=True,
        default=None
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = ConsultationRequest
        fields = [
            'id', 'name', 'phone', 'email',
            'user', 'user_username',
            'category', 'category_name', 'category_icon',
            'consultation_type', 'consultation_type_name',
            'region', 'content', 'ai_summary', 'ai_recommended_types',
            'status', 'status_display', 'admin_note',
            'created_at', 'updated_at', 'contacted_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at'
        ]


class AIAssistRequestSerializer(serializers.Serializer):
    """AI 내용 정리 요청용 시리얼라이저"""
    category = serializers.CharField()  # ID 또는 이름 허용
    content = serializers.CharField(min_length=10)

    def validate_category(self, value):
        """카테고리 검증 - ID 또는 이름/google_place_type 지원"""
        from django.db.models import Q

        # 숫자면 ID로 검색
        if str(value).isdigit():
            try:
                return LocalBusinessCategory.objects.get(id=int(value))
            except LocalBusinessCategory.DoesNotExist:
                raise serializers.ValidationError('존재하지 않는 카테고리입니다.')

        # 문자열이면 이름/google_place_type으로 검색
        category = LocalBusinessCategory.objects.filter(
            Q(google_place_type__iexact=value) |
            Q(name__iexact=value) |
            Q(name_en__iexact=value)
        ).first()

        if not category:
            raise serializers.ValidationError(f'카테고리를 찾을 수 없습니다: {value}')

        return category


class AIAssistResponseSerializer(serializers.Serializer):
    """AI 내용 정리 응답용 시리얼라이저"""
    summary = serializers.CharField()
    recommended_types = serializers.ListField(
        child=serializers.DictField()
    )


# ========== 상담 질문 플로우 시리얼라이저 ==========

class ConsultationFlowOptionSerializer(serializers.ModelSerializer):
    """상담 선택지 시리얼라이저"""

    class Meta:
        model = ConsultationFlowOption
        fields = [
            'id', 'key', 'label', 'icon', 'logo', 'description',
            'is_custom_input', 'order_index'
        ]


class ConsultationFlowSerializer(serializers.ModelSerializer):
    """상담 질문 플로우 시리얼라이저"""
    options = ConsultationFlowOptionSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = ConsultationFlow
        fields = [
            'id', 'category', 'category_name', 'step_number', 'question',
            'is_required', 'depends_on_step', 'depends_on_options',
            'options'
        ]


class ConsultationFlowListSerializer(serializers.ModelSerializer):
    """상담 질문 플로우 목록용 시리얼라이저 (옵션 포함)"""
    options = ConsultationFlowOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ConsultationFlow
        fields = [
            'id', 'step_number', 'question', 'is_required',
            'depends_on_step', 'depends_on_options', 'options'
        ]


# 통합 카테고리 매핑 (프론트엔드에서 가상으로 생성된 카테고리 → 실제 DB 카테고리)
MERGED_CATEGORY_TO_REAL = {
    'tax_accounting': '세무사',  # 세무·회계 → 세무사 (대표)
    'legal_service': '변호사',   # 법률 서비스 → 변호사 (대표)
    'cleaning_moving': '청소 전문',  # 청소·이사 → 청소 전문 (대표)
    '세무·회계': '세무사',
    '법률 서비스': '변호사',
    '청소·이사': '청소 전문',
}


class AIPolishRequestSerializer(serializers.Serializer):
    """AI 문장 다듬기 요청용 시리얼라이저"""
    category = serializers.CharField()
    selections = serializers.ListField(
        child=serializers.DictField(),
        help_text='선택된 내용 목록 [{step: 1, question: "...", answer: "..."}]'
    )
    additional_content = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='추가 입력 내용'
    )

    def validate_category(self, value):
        """카테고리 검증 - 숫자 ID, 문자열 ID, 통합 카테고리 모두 지원"""
        from django.db.models import Q

        # 숫자면 ID로 검색
        if str(value).isdigit():
            try:
                return LocalBusinessCategory.objects.get(id=int(value))
            except LocalBusinessCategory.DoesNotExist:
                raise serializers.ValidationError('존재하지 않는 카테고리입니다.')

        # 통합 카테고리 매핑 확인 (tax_accounting → 세무사 등)
        if value in MERGED_CATEGORY_TO_REAL:
            real_category_name = MERGED_CATEGORY_TO_REAL[value]
            category = LocalBusinessCategory.objects.filter(name=real_category_name).first()
            if category:
                return category

        # 문자열 ID 또는 이름으로 검색
        category = LocalBusinessCategory.objects.filter(
            Q(google_place_type__iexact=value) |
            Q(name__iexact=value) |
            Q(name_en__iexact=value)
        ).first()

        if not category:
            raise serializers.ValidationError(f'카테고리를 찾을 수 없습니다: {value}')

        return category


# ========== 관리자용 시리얼라이저 ==========

class ConsultationFlowOptionAdminSerializer(serializers.ModelSerializer):
    """상담 선택지 관리자용 시리얼라이저 (CRUD)"""

    class Meta:
        model = ConsultationFlowOption
        fields = [
            'id', 'flow', 'key', 'label', 'icon', 'logo', 'description',
            'is_custom_input', 'order_index', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConsultationFlowAdminSerializer(serializers.ModelSerializer):
    """상담 질문 플로우 관리자용 시리얼라이저 (CRUD)"""
    options = ConsultationFlowOptionAdminSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)

    class Meta:
        model = ConsultationFlow
        fields = [
            'id', 'category', 'category_name', 'category_icon',
            'step_number', 'question', 'is_required',
            'depends_on_step', 'depends_on_options',
            'order_index', 'is_active', 'options',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        """플로우 생성 시 옵션도 함께 생성"""
        options_data = self.context.get('request').data.get('options', [])
        flow = ConsultationFlow.objects.create(**validated_data)

        for idx, opt_data in enumerate(options_data):
            ConsultationFlowOption.objects.create(
                flow=flow,
                key=opt_data.get('key', f'option_{idx}'),
                label=opt_data.get('label', ''),
                icon=opt_data.get('icon', ''),
                logo=opt_data.get('logo', ''),
                description=opt_data.get('description', ''),
                is_custom_input=opt_data.get('is_custom_input', False),
                order_index=opt_data.get('order_index', idx),
                is_active=opt_data.get('is_active', True),
            )

        return flow

    def update(self, instance, validated_data):
        """플로우 수정 시 옵션도 함께 수정"""
        options_data = self.context.get('request').data.get('options')

        # 기본 필드 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 옵션 데이터가 있으면 옵션도 업데이트
        if options_data is not None:
            # 기존 옵션 삭제
            instance.options.all().delete()

            # 새 옵션 생성
            for idx, opt_data in enumerate(options_data):
                ConsultationFlowOption.objects.create(
                    flow=instance,
                    key=opt_data.get('key', f'option_{idx}'),
                    label=opt_data.get('label', ''),
                    icon=opt_data.get('icon', ''),
                    logo=opt_data.get('logo', ''),
                    description=opt_data.get('description', ''),
                    is_custom_input=opt_data.get('is_custom_input', False),
                    order_index=opt_data.get('order_index', idx),
                    is_active=opt_data.get('is_active', True),
                )

        return instance
