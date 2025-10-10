"""
전자제품/가전 Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import models
from .models import (
    UsedElectronics, ElectronicsRegion, ElectronicsImage,
    ElectronicsOffer, ElectronicsTransaction
)
from api.models import Region
from api.models_unified_simple import UnifiedFavorite
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
        fields = ['code', 'name', 'full_name', 'level']


class ElectronicsListSerializer(serializers.ModelSerializer):
    """전자제품 목록 시리얼라이저"""
    images = ElectronicsImageSerializer(many=True, read_only=True)
    seller = SellerSerializer(read_only=True)
    regions = serializers.SerializerMethodField()
    subcategory_display = serializers.CharField(source='get_subcategory_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_grade_display', read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    has_my_offer = serializers.SerializerMethodField()
    buyer = serializers.SerializerMethodField()
    buyer_id = serializers.SerializerMethodField()
    transaction_id = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()  # 최종 거래 금액
    has_review = serializers.SerializerMethodField()  # 후기 작성 여부

    class Meta:
        model = UsedElectronics
        fields = [
            'id', 'subcategory', 'subcategory_display', 'brand', 'model_name',
            'price', 'accept_offers', 'min_offer_price', 'condition_grade', 'condition_display',
            'purchase_period', 'status',
            'images', 'seller', 'regions', 'view_count', 'offer_count',
            'favorite_count', 'is_favorited', 'is_mine', 'has_my_offer',
            'buyer', 'buyer_id', 'transaction_id', 'final_price', 'has_review',
            'created_at', 'last_bumped_at', 'bump_count'
        ]

    def get_regions(self, obj):
        """거래 지역 목록"""
        regions = []
        for er in obj.regions.all():
            regions.append({
                'code': er.region.code,
                'name': er.region.name,
                'full_name': er.region.full_name
            })
        return regions

    def get_is_favorited(self, obj):
        """현재 사용자의 찜 여부"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # 통합 찜 모델 사용
            return UnifiedFavorite.objects.filter(
                user=request.user,
                item_type='electronics',
                item_id=obj.id
            ).exists()
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
            return obj.offers.filter(buyer=request.user, status='pending').exists()
        return False

    def get_buyer(self, obj):
        """구매자 정보"""
        if obj.status in ['trading', 'sold']:
            # 거래 테이블에서 구매자 정보 조회
            from used_electronics.models import ElectronicsTransaction
            transaction = ElectronicsTransaction.objects.filter(
                electronics=obj,
                status__in=['in_progress', 'completed']
            ).first()
            if transaction and transaction.buyer:
                return SellerSerializer(transaction.buyer).data
        return None

    def get_buyer_id(self, obj):
        """구매자 ID"""
        buyer = self.get_buyer(obj)
        return buyer['id'] if buyer else None

    def get_transaction_id(self, obj):
        """거래 ID"""
        if obj.status in ['trading', 'sold']:
            from used_electronics.models import ElectronicsTransaction
            transaction = ElectronicsTransaction.objects.filter(
                electronics=obj,
                status__in=['in_progress', 'completed']
            ).first()
            return transaction.id if transaction else None
        return None

    def get_final_price(self, obj):
        """거래중 또는 거래완료된 경우 실제 거래 금액 반환"""
        if obj.status in ['trading', 'sold']:
            # 거래 중인 경우 transaction에서 final_price 가져오기
            from .models import ElectronicsTransaction
            transaction = ElectronicsTransaction.objects.filter(electronics=obj).first()
            if transaction:
                return transaction.final_price
            # transaction이 없으면 수락된 제안의 금액을 찾기
            accepted_offer = obj.offers.filter(status='accepted').first()
            if accepted_offer:
                return accepted_offer.offer_price
        return None

    def get_has_review(self, obj):
        """현재 사용자가 후기를 작성했는지 여부"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        if obj.status == 'sold':
            from .models import ElectronicsTransaction
            from api.models_unified_simple import UnifiedReview

            transaction = ElectronicsTransaction.objects.filter(
                electronics=obj,
                status='completed'
            ).first()

            if transaction:
                # 현재 사용자가 후기를 작성했는지 확인
                return UnifiedReview.objects.filter(
                    item_type='electronics',
                    transaction_id=transaction.id,
                    reviewer=request.user
                ).exists()
        return False


class ElectronicsDetailSerializer(serializers.ModelSerializer):
    """전자제품 상세 시리얼라이저"""
    images = ElectronicsImageSerializer(many=True, read_only=True)
    seller = SellerSerializer(read_only=True)
    regions = serializers.SerializerMethodField()
    subcategory_display = serializers.CharField(source='get_subcategory_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_grade_display', read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    has_my_offer = serializers.SerializerMethodField()
    buyer = serializers.SerializerMethodField()
    buyer_id = serializers.SerializerMethodField()
    transaction_id = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()  # 최종 거래 금액
    has_review = serializers.SerializerMethodField()  # 후기 작성 여부

    class Meta:
        model = UsedElectronics
        fields = [
            'id', 'subcategory', 'subcategory_display', 'brand', 'model_name',
            'purchase_period', 'usage_period', 'is_unused', 'condition_grade', 'condition_display',
            'has_box', 'has_charger', 'has_manual', 'other_accessories',
            'price', 'min_offer_price', 'accept_offers',
            'description', 'region_type', 'region', 'region_name', 'meeting_place',
            'has_warranty_card', 'serial_number', 'warranty_end_date', 'purchase_date',
            'extra_specs', 'status', 'view_count', 'offer_count', 'favorite_count',
            'created_at', 'updated_at',
            'seller', 'images', 'regions',
            'is_favorited', 'is_mine', 'has_my_offer',
            'buyer', 'buyer_id', 'transaction_id', 'final_price', 'has_review',
            'last_bumped_at', 'bump_count'
        ]
        read_only_fields = ['seller', 'view_count', 'offer_count', 'favorite_count']

    def get_regions(self, obj):
        """거래 지역 목록"""
        regions = []
        for er in obj.regions.all():
            regions.append({
                'code': er.region.code,
                'name': er.region.name,
                'full_name': er.region.full_name,
                'level': er.region.level
            })
        return regions

    def get_is_favorited(self, obj):
        """현재 사용자의 찜 여부"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # 통합 찜 모델 사용
            return UnifiedFavorite.objects.filter(
                user=request.user,
                item_type='electronics',
                item_id=obj.id
            ).exists()
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

    def get_buyer(self, obj):
        """구매자 정보"""
        if obj.status in ['trading', 'sold']:
            from used_electronics.models import ElectronicsTransaction
            transaction = ElectronicsTransaction.objects.filter(
                electronics=obj,
                status__in=['in_progress', 'completed']
            ).first()
            if transaction and transaction.buyer:
                return SellerSerializer(transaction.buyer).data
        return None

    def get_buyer_id(self, obj):
        """구매자 ID"""
        buyer = self.get_buyer(obj)
        return buyer['id'] if buyer else None

    def get_transaction_id(self, obj):
        """거래 ID"""
        if obj.status in ['trading', 'sold']:
            from used_electronics.models import ElectronicsTransaction
            transaction = ElectronicsTransaction.objects.filter(
                electronics=obj,
                status__in=['in_progress', 'completed']
            ).first()
            return transaction.id if transaction else None
        return None

    def get_final_price(self, obj):
        """거래중 또는 거래완료된 경우 실제 거래 금액 반환"""
        if obj.status in ['trading', 'sold']:
            # 거래 중인 경우 transaction에서 final_price 가져오기
            from .models import ElectronicsTransaction
            transaction = ElectronicsTransaction.objects.filter(electronics=obj).first()
            if transaction:
                return transaction.final_price
            # transaction이 없으면 수락된 제안의 금액을 찾기
            accepted_offer = obj.offers.filter(status='accepted').first()
            if accepted_offer:
                return accepted_offer.offer_price
        return None

    def get_has_review(self, obj):
        """현재 사용자가 후기를 작성했는지 여부"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        if obj.status == 'sold':
            from .models import ElectronicsTransaction
            from api.models_unified_simple import UnifiedReview

            transaction = ElectronicsTransaction.objects.filter(
                electronics=obj,
                status='completed'
            ).first()

            if transaction:
                # 현재 사용자가 후기를 작성했는지 확인
                return UnifiedReview.objects.filter(
                    item_type='electronics',
                    transaction_id=transaction.id,
                    reviewer=request.user
                ).exists()
        return False


class ElectronicsCreateUpdateSerializer(serializers.ModelSerializer):
    """전자제품 등록/수정 시리얼라이저"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=10
    )
    new_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=10
    )
    existing_image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    regions = serializers.ListField(
        child=serializers.CharField(),
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
                # regions_data에는 지역 코드가 들어옴 (프론트엔드에서 code를 전달)
                main_region = Region.objects.get(code=regions_data[0])
                validated_data['region'] = main_region
            except Region.DoesNotExist:
                pass

        # 전자제품 생성
        electronics = UsedElectronics.objects.create(**validated_data)

        # 지역 연결
        for region_code in regions_data:
            try:
                region = Region.objects.get(code=region_code)
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
                if field not in allowed_fields and field not in ['existing_image_ids', 'new_images', 'images', 'regions']:
                    validated_data.pop(field)

        # 이미지 관련 데이터 추출
        images_data = validated_data.pop('images', None)  # 기존 방식 호환
        new_images_data = validated_data.pop('new_images', None)
        existing_image_ids = validated_data.pop('existing_image_ids', None)
        regions_data = validated_data.pop('regions', None)

        # 지역 업데이트
        if regions_data is not None:
            # 기존 지역 삭제
            instance.regions.all().delete()

            # 새 지역 추가
            for idx, region_code in enumerate(regions_data):
                try:
                    region = Region.objects.get(code=region_code)
                    ElectronicsRegion.objects.create(electronics=instance, region=region)
                    if idx == 0:
                        instance.region = region
                except Region.DoesNotExist:
                    continue

        # 이미지 업데이트 - 휴대폰과 동일한 방식
        if new_images_data is not None or existing_image_ids is not None:
            # 유지할 이미지와 삭제할 이미지 구분
            if existing_image_ids:
                # 기존 이미지 중 existing_image_ids에 없는 것만 삭제
                instance.images.exclude(id__in=existing_image_ids).delete()

                # 유지된 이미지들의 순서 재정렬 (휴대폰과 동일)
                for idx, img_id in enumerate(existing_image_ids):
                    ElectronicsImage.objects.filter(id=img_id).update(
                        order=idx,
                        is_primary=(idx == 0)
                    )
            else:
                # existing_image_ids가 없으면 모든 기존 이미지 삭제
                instance.images.all().delete()

            # 새 이미지 추가
            if new_images_data:
                # 기존 이미지의 최대 order 값 찾기
                max_order = instance.images.aggregate(max_order=models.Max('order'))['max_order'] or -1

                for idx, image in enumerate(new_images_data):
                    ElectronicsImage.objects.create(
                        electronics=instance,
                        image=image,
                        is_primary=(max_order == -1 and idx == 0),  # 기존 이미지가 없으면 첫 번째를 primary로
                        order=max_order + idx + 1
                    )
        elif images_data is not None:
            # 기존 방식 호환 (images 필드로 온 경우)
            instance.images.all().delete()
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


