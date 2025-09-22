"""
전자제품/가전 Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    UsedElectronics, ElectronicsRegion, ElectronicsImage,
    ElectronicsOffer, ElectronicsFavorite, ElectronicsTransaction
)
from api.models import Region
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class ElectronicsImageSerializer(serializers.ModelSerializer):
    """전자제품 이미지 시리얼라이저"""
    imageUrl = serializers.SerializerMethodField()

    class Meta:
        model = ElectronicsImage
        fields = ['id', 'image', 'imageUrl', 'is_primary', 'order']
        read_only_fields = ['id']

    def get_imageUrl(self, obj):
        """이미지 URL 반환"""
        if obj.image:
            request = self.context.get('request')
            if request and hasattr(obj.image, 'url'):
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url if hasattr(obj.image, 'url') else None
        return None


class SellerSerializer(serializers.ModelSerializer):
    """판매자 정보 시리얼라이저"""
    sell_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'sell_count']
        read_only_fields = ['id', 'username', 'nickname']

    def get_sell_count(self, obj):
        """판매 완료 수"""
        return obj.used_electronics.filter(status='sold').count()


class RegionSerializer(serializers.ModelSerializer):
    """지역 정보 시리얼라이저"""
    class Meta:
        model = Region
        fields = ['id', 'sido', 'sigungu', 'dong', 'name']


class ElectronicsListSerializer(serializers.ModelSerializer):
    """전자제품 목록 시리얼라이저"""
    images = ElectronicsImageSerializer(many=True, read_only=True)
    seller = SellerSerializer(read_only=True)
    regions = serializers.SerializerMethodField()
    subcategory_display = serializers.CharField(source='get_subcategory_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_grade_display', read_only=True)
    purchase_period_display = serializers.CharField(source='get_purchase_period_display', read_only=True)
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = UsedElectronics
        fields = [
            'id', 'subcategory', 'subcategory_display', 'brand', 'model_name',
            'price', 'accept_offers', 'condition_grade', 'condition_display',
            'purchase_period', 'purchase_period_display', 'status',
            'images', 'seller', 'regions', 'view_count', 'offer_count',
            'favorite_count', 'is_favorited', 'created_at'
        ]

    def get_regions(self, obj):
        """거래 지역 목록"""
        regions = []
        for er in obj.regions.all():
            regions.append({
                'id': er.region.id,
                'name': str(er.region)
            })
        return regions

    def get_is_favorited(self, obj):
        """현재 사용자의 찜 여부"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from api.models_unified_simple import UnifiedFavorite
                return UnifiedFavorite.objects.filter(
                    user=request.user,
                    item_type='electronics',
                    item_id=obj.id
                ).exists()
            except:
                # 통합 모델 실패시 기존 방식으로 폴백
                return obj.favorites.filter(user=request.user).exists()
        return False


class ElectronicsDetailSerializer(serializers.ModelSerializer):
    """전자제품 상세 시리얼라이저"""
    images = ElectronicsImageSerializer(many=True, read_only=True)
    seller = SellerSerializer(read_only=True)
    regions = serializers.SerializerMethodField()
    subcategory_display = serializers.CharField(source='get_subcategory_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_grade_display', read_only=True)
    purchase_period_display = serializers.CharField(source='get_purchase_period_display', read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    has_my_offer = serializers.SerializerMethodField()

    class Meta:
        model = UsedElectronics
        fields = '__all__'
        read_only_fields = ['seller', 'view_count', 'offer_count', 'favorite_count']

    def get_regions(self, obj):
        """거래 지역 목록"""
        regions = []
        for er in obj.regions.all():
            regions.append({
                'id': er.region.id,
                'sido': er.region.sido,
                'sigungu': er.region.sigungu,
                'dong': er.region.dong,
                'name': str(er.region)
            })
        return regions

    def get_is_favorited(self, obj):
        """현재 사용자의 찜 여부"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from api.models_unified_simple import UnifiedFavorite
                return UnifiedFavorite.objects.filter(
                    user=request.user,
                    item_type='electronics',
                    item_id=obj.id
                ).exists()
            except:
                # 통합 모델 실패시 기존 방식으로 폴백
                return obj.favorites.filter(user=request.user).exists()
        return False

    def get_is_mine(self, obj):
        """내 상품 여부"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.seller == request.user
        return False

    def get_has_my_offer(self, obj):
        """내 제안 존재 여부"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.offers.filter(buyer=request.user).exists()
        return False


class ElectronicsCreateUpdateSerializer(serializers.ModelSerializer):
    """전자제품 등록/수정 시리얼라이저"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=10
    )
    regions = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        max_length=3
    )

    class Meta:
        model = UsedElectronics
        exclude = ['seller', 'view_count', 'offer_count', 'favorite_count', 'region', 'region_name']

    def validate_images(self, value):
        """이미지 검증"""
        if len(value) < 1:
            raise serializers.ValidationError("최소 1장의 이미지가 필요합니다.")
        if len(value) > 10:
            raise serializers.ValidationError("이미지는 최대 10장까지 업로드 가능합니다.")

        for image in value:
            if image.size > 10 * 1024 * 1024:  # 10MB
                raise serializers.ValidationError(f"{image.name}은(는) 10MB를 초과합니다.")

        return value

    def validate_regions(self, value):
        """지역 검증"""
        if len(value) < 1:
            raise serializers.ValidationError("최소 1개의 거래 지역을 선택해주세요.")
        if len(value) > 3:
            raise serializers.ValidationError("거래 지역은 최대 3개까지 선택 가능합니다.")
        return value

    def validate_description(self, value):
        """상품 설명 검증"""
        if len(value) < 10:
            raise serializers.ValidationError("상품 설명은 10자 이상 입력해주세요.")
        if len(value) > 2000:
            raise serializers.ValidationError("상품 설명은 2000자 이내로 입력해주세요.")
        return value

    def validate_meeting_place(self, value):
        """거래 요청사항 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("거래시 요청사항을 입력해주세요.")
        if len(value) > 200:
            raise serializers.ValidationError("거래 요청사항은 200자 이내로 입력해주세요.")
        return value

    def create(self, validated_data):
        """전자제품 생성"""
        images_data = validated_data.pop('images', [])
        regions_data = validated_data.pop('regions', [])

        # 판매자 설정
        request = self.context.get('request')
        validated_data['seller'] = request.user

        # 첫 번째 지역을 메인 지역으로 설정
        if regions_data:
            try:
                main_region = Region.objects.get(id=regions_data[0])
                validated_data['region'] = main_region
            except Region.DoesNotExist:
                pass

        # 전자제품 생성
        electronics = UsedElectronics.objects.create(**validated_data)

        # 지역 연결
        for region_id in regions_data:
            try:
                region = Region.objects.get(id=region_id)
                ElectronicsRegion.objects.create(electronics=electronics, region=region)
            except Region.DoesNotExist:
                continue

        # 이미지 저장
        for idx, image in enumerate(images_data):
            ElectronicsImage.objects.create(
                electronics=electronics,
                image=image,
                is_primary=(idx == 0),
                order=idx
            )

        return electronics

    def update(self, instance, validated_data):
        """전자제품 수정"""
        # 가격제안이 있으면 일부 필드만 수정 가능
        if instance.offer_count > 0:
            allowed_fields = ['price', 'min_offer_price', 'accept_offers', 'meeting_place', 'description']
            for field in list(validated_data.keys()):
                if field not in allowed_fields:
                    validated_data.pop(field)

        images_data = validated_data.pop('images', None)
        regions_data = validated_data.pop('regions', None)

        # 지역 업데이트
        if regions_data is not None:
            # 기존 지역 삭제
            instance.regions.all().delete()

            # 새 지역 추가
            for idx, region_id in enumerate(regions_data):
                try:
                    region = Region.objects.get(id=region_id)
                    ElectronicsRegion.objects.create(electronics=instance, region=region)
                    if idx == 0:
                        instance.region = region
                except Region.DoesNotExist:
                    continue

        # 이미지 업데이트
        if images_data is not None:
            # 기존 이미지 삭제
            instance.images.all().delete()

            # 새 이미지 추가
            for idx, image in enumerate(images_data):
                ElectronicsImage.objects.create(
                    electronics=instance,
                    image=image,
                    is_primary=(idx == 0),
                    order=idx
                )

        # 나머지 필드 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class ElectronicsOfferSerializer(serializers.ModelSerializer):
    """전자제품 가격제안 시리얼라이저"""
    buyer = SellerSerializer(read_only=True)
    electronics_info = serializers.SerializerMethodField()

    class Meta:
        model = ElectronicsOffer
        fields = '__all__'
        read_only_fields = ['buyer', 'electronics', 'status']

    def get_electronics_info(self, obj):
        """전자제품 기본 정보"""
        return {
            'id': obj.electronics.id,
            'brand': obj.electronics.brand,
            'model_name': obj.electronics.model_name,
            'price': obj.electronics.price,
            'status': obj.electronics.status
        }

    def validate_offer_price(self, value):
        """제안 가격 검증"""
        if value < 1000:
            raise serializers.ValidationError("제안 가격은 1,000원 이상이어야 합니다.")
        return value

    def create(self, validated_data):
        """가격 제안 생성"""
        request = self.context.get('request')
        validated_data['buyer'] = request.user

        # 중복 제안 방지는 모델의 unique_together로 처리
        offer = ElectronicsOffer.objects.create(**validated_data)

        # 제안 수 증가
        offer.electronics.offer_count += 1
        offer.electronics.save(update_fields=['offer_count'])

        return offer


class ElectronicsFavoriteSerializer(serializers.ModelSerializer):
    """전자제품 찜 시리얼라이저"""
    electronics = ElectronicsListSerializer(read_only=True)

    class Meta:
        model = ElectronicsFavorite
        fields = '__all__'
        read_only_fields = ['user', 'electronics']