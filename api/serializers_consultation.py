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
            'id', 'key', 'label', 'icon', 'description',
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
        """카테고리 검증"""
        from django.db.models import Q

        if str(value).isdigit():
            try:
                return LocalBusinessCategory.objects.get(id=int(value))
            except LocalBusinessCategory.DoesNotExist:
                raise serializers.ValidationError('존재하지 않는 카테고리입니다.')

        category = LocalBusinessCategory.objects.filter(
            Q(google_place_type__iexact=value) |
            Q(name__iexact=value) |
            Q(name_en__iexact=value)
        ).first()

        if not category:
            raise serializers.ValidationError(f'카테고리를 찾을 수 없습니다: {value}')

        return category
