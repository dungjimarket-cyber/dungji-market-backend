"""
전문가 프로필 및 상담 매칭 시리얼라이저
"""
from rest_framework import serializers
from django.utils import timezone

from .models_expert import ExpertProfile, ConsultationMatch
from .models_local_business import LocalBusinessCategory
from .models_region import Region
from .models_consultation import ConsultationRequest


class LocalBusinessCategorySimpleSerializer(serializers.ModelSerializer):
    """업종 카테고리 간단 시리얼라이저"""
    class Meta:
        model = LocalBusinessCategory
        fields = ['id', 'name', 'icon']


class RegionSimpleSerializer(serializers.ModelSerializer):
    """지역 간단 시리얼라이저"""
    class Meta:
        model = Region
        fields = ['code', 'name', 'full_name']


class ExpertProfileSerializer(serializers.ModelSerializer):
    """전문가 프로필 시리얼라이저"""
    category = LocalBusinessCategorySimpleSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=LocalBusinessCategory.objects.all(),
        source='category',
        write_only=True
    )
    regions = RegionSimpleSerializer(many=True, read_only=True)
    region_codes = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False  # 수정 시에는 필수 아님
    )
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)

    class Meta:
        model = ExpertProfile
        fields = [
            'id', 'user', 'user_nickname',
            'category', 'category_id',
            'representative_name',
            'is_business', 'business_name', 'business_number', 'business_license_image',
            'license_number', 'license_image',
            'regions', 'region_codes',
            'contact_phone', 'contact_email',
            'profile_image', 'tagline', 'introduction',
            'status', 'is_receiving_requests',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        region_codes = validated_data.pop('region_codes', [])
        profile = ExpertProfile.objects.create(**validated_data)

        # 지역 연결
        regions = Region.objects.filter(code__in=region_codes)
        profile.regions.set(regions)

        return profile

    def update(self, instance, validated_data):
        region_codes = validated_data.pop('region_codes', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 지역 업데이트
        if region_codes is not None:
            regions = Region.objects.filter(code__in=region_codes)
            instance.regions.set(regions)

        return instance


class ExpertProfilePublicSerializer(serializers.ModelSerializer):
    """
    전문가 프로필 공개용 시리얼라이저
    - 답변한 전문가 정보를 고객에게 보여줄 때 사용
    - 연락처는 연결 후에만 공개
    """
    category = LocalBusinessCategorySimpleSerializer(read_only=True)
    regions = RegionSimpleSerializer(many=True, read_only=True)
    user_profile_image = serializers.CharField(source='user.profile_image', read_only=True)

    class Meta:
        model = ExpertProfile
        fields = [
            'id',
            'representative_name',
            'is_business', 'business_name',
            'category',
            'regions',
            'profile_image', 'user_profile_image',
            'tagline', 'introduction',
        ]


class ExpertProfileWithContactSerializer(ExpertProfilePublicSerializer):
    """
    전문가 프로필 + 연락처 시리얼라이저
    - 연결된 후 연락처 공개
    - contact_phone이 없으면 user.phone_number 사용
    """
    contact_phone = serializers.SerializerMethodField()

    class Meta(ExpertProfilePublicSerializer.Meta):
        fields = ExpertProfilePublicSerializer.Meta.fields + [
            'contact_phone', 'contact_email'
        ]

    def get_contact_phone(self, obj):
        # contact_phone이 있으면 사용, 없으면 user.phone_number fallback
        return obj.contact_phone or (obj.user.phone_number if obj.user else None)


class ConsultationMatchSerializer(serializers.ModelSerializer):
    """상담 매칭 시리얼라이저"""
    expert = ExpertProfilePublicSerializer(read_only=True)
    consultation_id = serializers.PrimaryKeyRelatedField(
        queryset=ConsultationRequest.objects.all(),
        source='consultation',
        write_only=True
    )

    class Meta:
        model = ConsultationMatch
        fields = [
            'id', 'consultation', 'consultation_id', 'expert',
            'status',
            'expert_message', 'available_time',
            'created_at', 'replied_at', 'connected_at', 'completed_at'
        ]
        read_only_fields = ['id', 'consultation', 'expert', 'created_at', 'replied_at', 'connected_at', 'completed_at']


class ConsultationMatchDetailSerializer(ConsultationMatchSerializer):
    """
    상담 매칭 상세 시리얼라이저
    - 연결된 경우 연락처 포함
    """
    expert = serializers.SerializerMethodField()

    def get_expert(self, obj):
        if obj.status in ['connected', 'completed']:
            return ExpertProfileWithContactSerializer(obj.expert).data
        return ExpertProfilePublicSerializer(obj.expert).data


class ExpertReplySerializer(serializers.Serializer):
    """전문가 답변 시리얼라이저"""
    expert_message = serializers.CharField(required=False, allow_blank=True)
    available_time = serializers.CharField(required=False, allow_blank=True, max_length=200)


# 전문가용 상담 요청 시리얼라이저
class ConsultationRequestForExpertSerializer(serializers.ModelSerializer):
    """전문가에게 보여줄 상담 요청 시리얼라이저"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    match_status = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    expert_message = serializers.SerializerMethodField()
    available_time = serializers.SerializerMethodField()

    class Meta:
        model = ConsultationRequest
        fields = [
            'id', 'category_name',
            'region', 'answers',
            'customer_name', 'customer_phone',
            'match_status', 'expert_message', 'available_time',
            'created_at'
        ]

    def get_match_status(self, obj):
        """현재 전문가의 매칭 상태"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'expert_profile'):
            match = obj.matches.filter(expert=request.user.expert_profile).first()
            if match:
                return match.status
        return None

    def get_customer_name(self, obj):
        """고객 이름 (연결 후에만 공개)"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'expert_profile'):
            match = obj.matches.filter(
                expert=request.user.expert_profile,
                status__in=['connected', 'completed']
            ).first()
            if match:
                return obj.name
        return None

    def get_customer_phone(self, obj):
        """고객 연락처 (연결 후에만 공개)"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'expert_profile'):
            match = obj.matches.filter(
                expert=request.user.expert_profile,
                status__in=['connected', 'completed']
            ).first()
            if match:
                return obj.phone
        return None

    def get_expert_message(self, obj):
        """현재 전문가가 남긴 답변 내용"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'expert_profile'):
            match = obj.matches.filter(expert=request.user.expert_profile).first()
            if match:
                return match.expert_message
        return ''

    def get_available_time(self, obj):
        """현재 전문가가 남긴 상담 가능 일자"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'expert_profile'):
            match = obj.matches.filter(expert=request.user.expert_profile).first()
            if match:
                return match.available_time
        return ''

    def get_answers(self, obj):
        answers = {}
        if obj.content:
            answers['상담 내용'] = obj.content
        if obj.consultation_type_text:
            answers['상담 유형'] = obj.consultation_type_text
        return answers


# 고객용 상담 내역 시리얼라이저
class ConsultationRequestForCustomerSerializer(serializers.ModelSerializer):
    """고객에게 보여줄 상담 요청 시리얼라이저"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    replied_experts_count = serializers.SerializerMethodField()
    connected_expert = serializers.SerializerMethodField()
    matches = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()

    class Meta:
        model = ConsultationRequest
        fields = [
            'id', 'category_name',
            'region', 'answers',
            'name', 'phone',
            'replied_experts_count', 'connected_expert',
            'matches',
            'created_at'
        ]

    def get_answers(self, obj):
        """상담 내용을 answers 형식으로 변환"""
        # content 필드를 질문-답변 형식으로 변환
        answers = {}
        if obj.content:
            answers['상담 내용'] = obj.content
        if obj.consultation_type_text:
            answers['상담 유형'] = obj.consultation_type_text
        return answers

    def get_replied_experts_count(self, obj):
        """답변한 전문가 수"""
        return obj.matches.filter(status='replied').count()

    def get_connected_expert(self, obj):
        """연결된 전문가 정보"""
        connected_match = obj.matches.filter(status__in=['connected', 'completed']).first()
        if connected_match:
            return ExpertProfileWithContactSerializer(connected_match.expert).data
        return None

    def get_matches(self, obj):
        """답변한 전문가 목록"""
        matches = obj.matches.filter(status__in=['replied', 'connected', 'completed'])
        return ConsultationMatchDetailSerializer(matches, many=True).data
