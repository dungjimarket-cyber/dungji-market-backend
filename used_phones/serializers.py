"""
Used Phones Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer, UsedPhoneRegion
from api.models import Region

User = get_user_model()


class UsedPhoneImageSerializer(serializers.ModelSerializer):
    """중고폰 이미지 시리얼라이저"""
    imageUrl = serializers.SerializerMethodField()
    thumbnailUrl = serializers.SerializerMethodField()
    
    class Meta:
        model = UsedPhoneImage
        fields = ['id', 'image', 'image_url', 'imageUrl', 'thumbnail', 'thumbnail_url', 'thumbnailUrl', 
                 'is_main', 'order', 'width', 'height', 'file_size']
        read_only_fields = ['id', 'image_url', 'thumbnail_url', 'width', 'height', 'file_size']
    
    def get_imageUrl(self, obj):
        """프론트엔드 호환성을 위한 imageUrl 필드"""
        if obj.image_url:
            return obj.image_url
        elif obj.image:
            return obj.image.url if hasattr(obj.image, 'url') else None
        return None
    
    def get_thumbnailUrl(self, obj):
        """프론트엔드 호환성을 위한 thumbnailUrl 필드"""
        if obj.thumbnail_url:
            return obj.thumbnail_url
        elif obj.thumbnail:
            return obj.thumbnail.url if hasattr(obj.thumbnail, 'url') else None
        # 썸네일이 없으면 원본 이미지 URL 반환
        return self.get_imageUrl(obj)


class SellerSerializer(serializers.ModelSerializer):
    """판매자 정보 시리얼라이저"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class UsedPhoneListSerializer(serializers.ModelSerializer):
    """중고폰 목록 시리얼라이저"""
    images = UsedPhoneImageSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UsedPhone
        fields = [
            'id', 'brand', 'model', 'storage', 'color', 'price', 
            'min_offer_price', 'accept_offers', 'condition_grade',
            'battery_status', 'status', 'view_count', 'favorite_count',
            'offer_count', 'region_name', 'images', 'is_favorite',
            'created_at', 'body_only'
        ]
    
    def get_region_name(self, obj):
        """지역 이름 반환 - 안전하게 처리"""
        if hasattr(obj, 'region') and obj.region:
            return obj.region.full_name
        return None
    
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False


class UsedPhoneDetailSerializer(serializers.ModelSerializer):
    """중고폰 상세 시리얼라이저"""
    seller = SellerSerializer(read_only=True)
    images = UsedPhoneImageSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    regions = serializers.SerializerMethodField()
    
    class Meta:
        model = UsedPhone
        fields = '__all__'
        read_only_fields = ['id', 'seller', 'view_count', 'favorite_count', 
                           'offer_count', 'created_at', 'updated_at']
    
    def get_region_name(self, obj):
        """지역 이름 반환 - 안전하게 처리"""
        if hasattr(obj, 'region') and obj.region:
            return obj.region.full_name
        return None
    
    def get_regions(self, obj):
        """다중 지역 정보 반환"""
        phone_regions = obj.regions.select_related('region').all()
        return [
            {
                'code': pr.region.code,
                'name': pr.region.name,
                'full_name': pr.region.full_name
            }
            for pr in phone_regions
        ]
    
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False


class UsedPhoneCreateSerializer(serializers.ModelSerializer):
    """중고폰 등록 시리얼라이저"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=5,  # 최대 5개 이미지
        help_text="최대 5개의 이미지를 업로드할 수 있습니다."
    )
    regions = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        max_length=3,  # 최대 3개 지역
        help_text="최대 3개의 지역을 선택할 수 있습니다."
    )
    
    class Meta:
        model = UsedPhone
        exclude = ['seller', 'view_count', 'favorite_count', 'offer_count', 
                  'status', 'sold_at']
    
    def validate_images(self, value):
        """이미지 유효성 검사"""
        if len(value) > 5:
            raise serializers.ValidationError("최대 5개의 이미지만 업로드할 수 있습니다.")
        
        # 이미지 크기 및 형식 검사
        for image in value:
            # 파일 크기 검사 (3MB 제한)
            if image.size > 3 * 1024 * 1024:
                raise serializers.ValidationError(f"이미지 파일 크기는 3MB를 초과할 수 없습니다. ({image.name})")
            
            # 파일 형식 검사
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise serializers.ValidationError(f"지원하지 않는 이미지 형식입니다. JPEG, PNG, WebP만 지원됩니다. ({image.name})")
        
        return value
    
    def create(self, validated_data):
        """중고폰 생성 및 이미지 처리"""
        import logging
        from api.models import Region
        logger = logging.getLogger(__name__)
        
        logger.info("===== UsedPhone Create Start =====")
        logger.info(f"Received data keys: {validated_data.keys()}")
        
        images_data = validated_data.pop('images', [])
        # regions 데이터는 save 메서드에서 전달받은 것을 사용
        regions_data = validated_data.pop('regions', [])
        
        logger.info(f"Images count: {len(images_data)}")
        logger.info(f"Regions count: {len(regions_data)}")
        
        # region 필드 처리
        region_code = validated_data.get('region')
        if region_code:
            try:
                # 지역 코드로 Region 객체 찾기
                region_obj = Region.objects.get(code=region_code)
                validated_data['region'] = region_obj
                logger.info(f"Region found: {region_obj.full_name} (code: {region_code})")
            except Region.DoesNotExist:
                logger.warning(f"Region not found with code: {region_code}, using default")
                # 기본 지역 설정
                default_region = Region.objects.filter(level=0).first()
                if default_region:
                    validated_data['region'] = default_region
                    logger.info(f"Default region set to: {default_region}")
                else:
                    validated_data.pop('region', None)
            except Exception as e:
                logger.error(f"Failed to process region: {e}")
                validated_data.pop('region', None)
        else:
            # region이 없는 경우 기본값 설정
            try:
                default_region = Region.objects.filter(level=0).first()
                if default_region:
                    validated_data['region'] = default_region
                    logger.info(f"No region provided, default set to: {default_region}")
                else:
                    validated_data.pop('region', None)
            except Exception as e:
                logger.error(f"Failed to set default region: {e}")
                validated_data.pop('region', None)
        
        # body_only 기본값 설정
        if 'body_only' not in validated_data:
            validated_data['body_only'] = False
        
        # 필수 필드가 없는 경우 기본값 설정
        if 'battery_status' not in validated_data:
            validated_data['battery_status'] = 'unknown'
            
        logger.info(f"Creating UsedPhone with data: {validated_data}")
        
        try:
            phone = UsedPhone.objects.create(**validated_data)
            logger.info(f"UsedPhone created successfully with ID: {phone.id}")
        except Exception as e:
            logger.error(f"Failed to create UsedPhone: {e}")
            raise
        
        # 이미지 처리
        for index, image in enumerate(images_data):
            try:
                phone_image = UsedPhoneImage.objects.create(
                    phone=phone,
                    image=image,
                    is_main=(index == 0),  # 첫 번째 이미지를 대표 이미지로 설정
                    order=index
                )
                
                # 로깅
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"이미지 업로드 완료: {phone_image.id}, 순서: {index}")
                
            except Exception as e:
                # 이미지 업로드 실패 시 로그 기록하지만 전체 생성은 계속
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"이미지 업로드 실패: {e}")
        
        # 지역 처리는 views.py의 perform_create에서 처리함
        logger.info("Regions will be processed in perform_create")
        
        return phone


class UsedPhoneOfferSerializer(serializers.ModelSerializer):
    """가격 제안 시리얼라이저"""
    buyer = SellerSerializer(read_only=True)
    phone_model = serializers.CharField(source='phone.model', read_only=True)
    
    class Meta:
        model = UsedPhoneOffer
        fields = '__all__'
        read_only_fields = ['id', 'buyer', 'status', 'seller_message', 
                           'created_at', 'updated_at']
    
    def validate_amount(self, value):
        phone = self.context.get('phone')
        if phone and phone.min_offer_price and value < phone.min_offer_price:
            raise serializers.ValidationError(
                f"제안 금액은 최소 {phone.min_offer_price:,}원 이상이어야 합니다."
            )
        return value


class UsedPhoneFavoriteSerializer(serializers.ModelSerializer):
    """찜 시리얼라이저"""
    phone = UsedPhoneListSerializer(read_only=True)
    
    class Meta:
        model = UsedPhoneFavorite
        fields = ['id', 'phone', 'created_at']
        read_only_fields = ['id', 'created_at']
