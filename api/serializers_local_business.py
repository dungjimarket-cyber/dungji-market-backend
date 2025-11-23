"""
지역 업체 정보 Serializer
"""
from rest_framework import serializers
from api.models_local_business import (
    LocalBusinessCategory,
    LocalBusiness,
    LocalBusinessLink
)


class LocalBusinessCategorySerializer(serializers.ModelSerializer):
    """업종 카테고리 Serializer"""

    class Meta:
        model = LocalBusinessCategory
        fields = [
            'id', 'name', 'name_en', 'icon',
            'google_place_type', 'description',
            'order_index', 'is_active'
        ]


class LocalBusinessLinkSerializer(serializers.ModelSerializer):
    """업체 외부 링크 Serializer"""

    class Meta:
        model = LocalBusinessLink
        fields = [
            'id', 'link_type', 'title', 'url',
            'source', 'published_at', 'created_at'
        ]


class LocalBusinessListSerializer(serializers.ModelSerializer):
    """업체 목록 Serializer (간단한 정보만)"""

    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    # region_name은 이제 모델 필드이므로 자동 포함
    rating = serializers.FloatField(read_only=True)
    # photo_url은 프록시 API 사용을 위해 boolean만 반환
    has_photo = serializers.SerializerMethodField()
    custom_photo_url = serializers.SerializerMethodField()
    editorial_summary = serializers.CharField(read_only=True)

    class Meta:
        model = LocalBusiness
        fields = [
            'id', 'name', 'address', 'phone_number',
            'category_name', 'category_icon',
            'region_name',
            'rating', 'review_count',
            'popularity_score', 'rank_in_region',
            'is_verified', 'is_new',
            'has_photo', 'photo_url', 'custom_photo_url',
            'editorial_summary',
            'website_url',
            'view_count',
            'created_at'
        ]

    def get_has_photo(self, obj):
        """사진 존재 여부만 반환 (URL은 노출 안 함)"""
        return bool(obj.custom_photo or obj.photo_url)

    def get_custom_photo_url(self, obj):
        """커스텀 이미지 URL (우선순위: custom_photo > photo_url)"""
        if obj.custom_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.custom_photo.url)
            return obj.custom_photo.url
        return None


class LocalBusinessDetailSerializer(serializers.ModelSerializer):
    """업체 상세 Serializer"""

    category = LocalBusinessCategorySerializer(read_only=True)
    # region_name은 이제 모델 필드이므로 자동 포함
    links = LocalBusinessLinkSerializer(many=True, read_only=True)
    rating = serializers.FloatField(read_only=True)
    custom_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = LocalBusiness
        fields = [
            'id', 'name', 'address', 'phone_number',
            'category', 'region_name',
            'google_place_id', 'latitude', 'longitude',
            'rating', 'review_count',
            'google_maps_url', 'photo_url', 'custom_photo_url',
            'editorial_summary',
            'popularity_score', 'rank_in_region',
            'is_verified', 'is_new',
            'view_count', 'last_synced_at',
            'links',
            'created_at', 'updated_at'
        ]

    def get_custom_photo_url(self, obj):
        """커스텀 이미지 URL (우선순위: custom_photo > photo_url)"""
        if obj.custom_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.custom_photo.url)
            return obj.custom_photo.url
        return None
