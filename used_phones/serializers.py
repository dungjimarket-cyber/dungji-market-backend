"""
Used Phones Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer,
    UsedPhoneRegion, UsedPhoneTransaction, UsedPhoneReview,
    UsedPhoneReport, UsedPhonePenalty
)
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
    sell_count = serializers.SerializerMethodField()
    buy_count = serializers.SerializerMethodField()
    total_trade_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'email', 'sell_count', 'buy_count', 'total_trade_count']
    
    def get_sell_count(self, obj):
        """판매 완료 횟수"""
        from .models import UsedPhone
        return UsedPhone.objects.filter(seller=obj, status='sold').count()
    
    def get_buy_count(self, obj):
        """구매 완료 횟수 (수락된 제안)"""
        from .models import UsedPhoneOffer
        # 사용자가 제안했고 수락된 건수
        return UsedPhoneOffer.objects.filter(buyer=obj, status='accepted').count()
    
    def get_total_trade_count(self, obj):
        """총 거래 횟수"""
        sell_count = self.get_sell_count(obj)
        buy_count = self.get_buy_count(obj)
        return sell_count + buy_count


class UsedPhoneListSerializer(serializers.ModelSerializer):
    """중고폰 목록 시리얼라이저"""
    images = UsedPhoneImageSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    regions = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    offer_count = serializers.SerializerMethodField()  # offer_count를 동적으로 계산
    buyer = serializers.SerializerMethodField()  # 구매자 정보 추가
    transaction_id = serializers.SerializerMethodField()  # 거래 ID 추가

    class Meta:
        model = UsedPhone
        fields = [
            'id', 'brand', 'model', 'storage', 'color', 'price', 'final_price',
            'min_offer_price', 'accept_offers', 'condition_grade',
            'condition_description', 'battery_status', 'status', 'view_count',
            'favorite_count', 'offer_count', 'region_name', 'regions', 'images',
            'is_favorite', 'created_at', 'body_only', 'has_box', 'has_charger',
            'has_earphones', 'meeting_place', 'is_modified', 'buyer', 'transaction_id'
        ]
    
    def get_region_name(self, obj):
        """지역 이름 반환 - 안전하게 처리"""
        if hasattr(obj, 'region') and obj.region:
            return obj.region.full_name
        return None
    
    def get_regions(self, obj):
        """다중 지역 정보 반환"""
        # prefetch_related를 사용하여 N+1 문제 해결
        try:
            phone_regions = obj.regions.select_related('region').all()
            return [
                {
                    'id': pr.id,
                    'name': pr.region.name if pr.region else None,
                    'full_name': pr.region.full_name if pr.region else None,
                }
                for pr in phone_regions
            ]
        except:
            return []
    
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False
    
    def get_final_price(self, obj):
        """거래완료된 경우 실제 거래 금액 반환"""
        if obj.status == 'sold':
            # 수락된 제안의 금액을 찾기
            accepted_offer = obj.offers.filter(status='accepted').first()
            if accepted_offer:
                return accepted_offer.offered_price
        return None

    def get_offer_count(self, obj):
        """실시간으로 pending 상태의 유니크한 구매자 수 계산"""
        from .models import UsedPhoneOffer
        return UsedPhoneOffer.objects.filter(
            phone=obj,
            status='pending'
        ).values('buyer').distinct().count()

    def get_buyer(self, obj):
        """거래 완료된 경우 구매자 정보 반환"""
        try:
            if obj.status != 'sold':
                return None

            # prefetch된 transactions 사용
            transactions = obj.transactions.all() if hasattr(obj, 'transactions') else []
            for transaction in transactions:
                if transaction.status == 'completed' and transaction.buyer:
                    return {
                        'id': transaction.buyer.id,
                        'nickname': getattr(transaction.buyer, 'nickname', transaction.buyer.username)
                    }

            # prefetch가 안된 경우 직접 쿼리 (fallback)
            from .models import UsedPhoneTransaction
            transaction = UsedPhoneTransaction.objects.filter(
                phone=obj,
                status='completed'
            ).select_related('buyer').first()
            if transaction and transaction.buyer:
                return {
                    'id': transaction.buyer.id,
                    'nickname': getattr(transaction.buyer, 'nickname', transaction.buyer.username)
                }
        except Exception:
            pass
        return None

    def get_transaction_id(self, obj):
        """거래 완료된 경우 거래 ID 반환"""
        try:
            if obj.status == 'sold':
                from .models import UsedPhoneTransaction
                transaction = UsedPhoneTransaction.objects.filter(
                    phone=obj,
                    status='completed'
                ).first()
                if transaction:
                    return transaction.id
        except Exception as e:
            # 오류 발생 시 None 반환
            return None
        return None


class UsedPhoneDetailSerializer(serializers.ModelSerializer):
    """중고폰 상세 시리얼라이저"""
    seller = SellerSerializer(read_only=True)
    images = UsedPhoneImageSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    regions = serializers.SerializerMethodField()
    buyer_id = serializers.SerializerMethodField()
    buyer = serializers.SerializerMethodField()
    transaction_id = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = UsedPhone
        fields = ['id', 'seller', 'brand', 'model', 'storage', 'color',
                  'condition_grade', 'condition_description', 'battery_status',
                  'price', 'min_offer_price', 'accept_offers', 'description',
                  'body_only', 'has_box', 'has_charger', 'has_earphones',
                  'meeting_place', 'status', 'view_count', 'favorite_count',
                  'offer_count', 'sold_at', 'created_at', 'updated_at',
                  'images', 'is_favorite', 'region_name', 'regions',
                  'buyer_id', 'buyer', 'transaction_id', 'final_price']
        read_only_fields = ['id', 'seller', 'view_count', 'favorite_count',
                           'offer_count', 'created_at', 'updated_at']
    
    def get_region_name(self, obj):
        """지역 이름 반환 - 안전하게 처리"""
        if hasattr(obj, 'region') and obj.region:
            return obj.region.full_name
        return None
    
    def get_regions(self, obj):
        """다중 지역 정보 반환"""
        try:
            phone_regions = obj.regions.select_related('region').all()
            return [
                {
                    'code': pr.region.code,
                    'name': pr.region.name,
                    'full_name': pr.region.full_name
                }
                for pr in phone_regions
            ]
        except Exception as e:
            logger.error(f"Error getting regions for phone {obj.id}: {e}")
            return []
    
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_buyer_id(self, obj):
        """거래중일 때 구매자 ID 반환"""
        try:
            if obj.status == 'trading':
                # 수락된 제안 찾기
                from .models import UsedPhoneOffer
                accepted_offer = UsedPhoneOffer.objects.filter(
                    phone=obj,
                    status='accepted'
                ).first()
                if accepted_offer and accepted_offer.buyer:
                    return accepted_offer.buyer.id
        except Exception:
            pass
        return None

    def get_buyer(self, obj):
        """거래중/판매완료 시 구매자 정보 반환"""
        try:
            if obj.status in ['trading', 'sold']:
                # 수락된 제안 찾기
                from .models import UsedPhoneOffer
                accepted_offer = UsedPhoneOffer.objects.filter(
                    phone=obj,
                    status='accepted'
                ).select_related('buyer').first()
                if accepted_offer and accepted_offer.buyer:
                    return {
                        'id': accepted_offer.buyer.id,
                        'username': accepted_offer.buyer.username,
                        'nickname': getattr(accepted_offer.buyer, 'nickname', None),
                        'email': accepted_offer.buyer.email,
                    }
        except Exception:
            pass
        return None

    def get_transaction_id(self, obj):
        """거래 완료된 경우 트랜잭션 ID 반환"""
        try:
            # sold, trading 상태일 때 트랜잭션 ID 반환
            if obj.status in ['sold', 'trading']:
                # 가장 최근의 트랜잭션 찾기 (취소된 것 제외)
                from .models import UsedPhoneTransaction
                transaction = UsedPhoneTransaction.objects.filter(
                    phone=obj
                ).exclude(status='cancelled').order_by('-created_at').first()
                if transaction:
                    return transaction.id
        except Exception:
            pass
        return None

    def get_final_price(self, obj):
        """거래완료된 경우 실제 거래 금액 반환"""
        if obj.status == 'sold':
            # 수락된 제안의 금액을 찾기
            from .models import UsedPhoneOffer
            accepted_offer = UsedPhoneOffer.objects.filter(
                phone=obj,
                status='accepted'
            ).first()
            if accepted_offer:
                return accepted_offer.offered_price
        return None


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
    
    def validate_price(self, value):
        """가격 유효성 검사 - 천원 단위"""
        if value % 1000 != 0:
            raise serializers.ValidationError("가격은 천원 단위로 입력해주세요.")
        if value < 1000:
            raise serializers.ValidationError("최소 가격은 1,000원입니다.")
        if value > 9900000:
            raise serializers.ValidationError("최대 가격은 990만원입니다.")
        return value

    def validate_min_offer_price(self, value):
        """최소 제안가 유효성 검사 - 천원 단위"""
        if value is not None:
            if value % 1000 != 0:
                raise serializers.ValidationError("가격은 천원 단위로 입력해주세요.")
            if value < 1000:
                raise serializers.ValidationError("최소 가격은 1,000원입니다.")
            if value > 9900000:
                raise serializers.ValidationError("최대 가격은 990만원입니다.")
        return value

    def validate_images(self, value):
        """이미지 유효성 검사"""
        if len(value) > 10:
            raise serializers.ValidationError("최대 10개의 이미지만 업로드할 수 있습니다.")

        # 이미지 크기 및 형식 검사
        for image in value:
            # 파일 크기 검사 (10MB 제한 - 이미지당)
            if image.size > 10 * 1024 * 1024:
                raise serializers.ValidationError(f"이미지 파일 크기는 10MB를 초과할 수 없습니다. ({image.name})")

            # 파일 형식 검사
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise serializers.ValidationError(f"지원하지 않는 이미지 형식입니다. JPEG, PNG, WebP만 지원됩니다. ({image.name})")

        return value

    def validate(self, data):
        """전체 유효성 검사"""
        price = data.get('price')
        min_offer_price = data.get('min_offer_price')

        if min_offer_price is not None and price and min_offer_price >= price:
            raise serializers.ValidationError({
                'min_offer_price': '최소 제안가는 즉시 판매가보다 낮아야 합니다.'
            })

        return data
    
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

    def validate_offered_price(self, value):
        # 천원 단위 검증
        if value % 1000 != 0:
            raise serializers.ValidationError("가격은 천원 단위로 입력해주세요.")

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


class UsedPhoneTransactionSerializer(serializers.ModelSerializer):
    """거래 시리얼라이저"""
    phone_model = serializers.CharField(source='phone.model', read_only=True)
    seller_username = serializers.CharField(source='seller.username', read_only=True)
    buyer_username = serializers.CharField(source='buyer.username', read_only=True)

    class Meta:
        model = UsedPhoneTransaction
        fields = [
            'id', 'phone', 'phone_model', 'offer', 'seller', 'seller_username',
            'buyer', 'buyer_username', 'status', 'seller_confirmed', 'buyer_confirmed',
            'seller_confirmed_at', 'buyer_confirmed_at', 'final_price',
            'meeting_date', 'meeting_location', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'completed_at']


class UsedPhoneReviewSerializer(serializers.ModelSerializer):
    """거래 후기 시리얼라이저"""
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True)
    reviewee_username = serializers.CharField(source='reviewee.username', read_only=True)

    class Meta:
        model = UsedPhoneReview
        fields = [
            'id', 'transaction', 'reviewer', 'reviewer_username',
            'reviewee', 'reviewee_username', 'rating', 'comment',
            'is_punctual', 'is_friendly', 'is_honest', 'is_fast_response',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reviewer', 'reviewee', 'created_at', 'updated_at']

    def validate(self, data):
        """거래 완료 후에만 리뷰 작성 가능"""
        transaction = data.get('transaction')
        if transaction and transaction.status != 'completed':
            raise serializers.ValidationError("거래가 완료된 후에만 리뷰를 작성할 수 있습니다.")

        # 리뷰어가 거래 당사자인지 확인
        request_user = self.context['request'].user
        if transaction.seller != request_user and transaction.buyer != request_user:
            raise serializers.ValidationError("해당 거래의 당사자만 리뷰를 작성할 수 있습니다.")

        return data


class UsedPhoneReportSerializer(serializers.ModelSerializer):
    """중고폰 신고 시리얼라이저"""
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    reported_user_username = serializers.CharField(source='reported_user.username', read_only=True)
    reported_phone_model = serializers.CharField(source='reported_phone.model', read_only=True)
    processed_by_username = serializers.CharField(source='processed_by.username', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = UsedPhoneReport
        fields = [
            'id', 'reported_user', 'reported_user_username',
            'reported_phone', 'reported_phone_model', 'reporter', 'reporter_username',
            'report_type', 'report_type_display', 'description', 'status', 'status_display',
            'admin_note', 'processed_by', 'processed_by_username', 'processed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reporter', 'processed_by', 'processed_at', 'created_at', 'updated_at']

    def validate(self, data):
        """신고 유효성 검증"""
        request_user = self.context['request'].user
        reported_user = data.get('reported_user')

        # 자신을 신고할 수 없음
        if reported_user == request_user:
            raise serializers.ValidationError("자신을 신고할 수 없습니다.")

        # 같은 사용자를 24시간 내에 중복 신고 방지
        from django.utils import timezone
        from datetime import timedelta

        recent_report = UsedPhoneReport.objects.filter(
            reporter=request_user,
            reported_user=reported_user,
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).exists()

        if recent_report:
            raise serializers.ValidationError("24시간 내에 같은 사용자를 중복 신고할 수 없습니다.")

        return data


class UsedPhonePenaltySerializer(serializers.ModelSerializer):
    """중고폰 패널티 시리얼라이저"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    issued_by_username = serializers.CharField(source='issued_by.username', read_only=True)
    revoked_by_username = serializers.CharField(source='revoked_by.username', read_only=True)
    penalty_type_display = serializers.CharField(source='get_penalty_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_currently_active = serializers.SerializerMethodField()
    related_reports_count = serializers.SerializerMethodField()

    class Meta:
        model = UsedPhonePenalty
        fields = [
            'id', 'user', 'user_username', 'penalty_type', 'penalty_type_display',
            'reason', 'duration_days', 'start_date', 'end_date', 'status', 'status_display',
            'issued_by', 'issued_by_username', 'revoked_by', 'revoked_by_username',
            'revoked_at', 'is_currently_active', 'related_reports_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'start_date', 'issued_by', 'revoked_by', 'revoked_at',
            'created_at', 'updated_at'
        ]

    def get_is_currently_active(self, obj):
        """현재 패널티가 활성 상태인지 반환"""
        return obj.is_active()

    def get_related_reports_count(self, obj):
        """관련 신고 수 반환"""
        return obj.related_reports.count()


class UserRatingSerializer(serializers.ModelSerializer):
    """사용자 평점 정보 시리얼라이저"""
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()
    penalty_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'nickname', 'average_rating', 'total_reviews',
            'recent_reviews', 'penalty_status'
        ]

    def get_average_rating(self, obj):
        """평균 평점 계산"""
        from django.db.models import Avg
        avg = obj.received_used_phone_reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg, 1) if avg else None

    def get_total_reviews(self, obj):
        """총 리뷰 개수"""
        return obj.received_used_phone_reviews.count()

    def get_recent_reviews(self, obj):
        """최근 리뷰 3개"""
        recent_reviews = obj.received_used_phone_reviews.select_related(
            'reviewer', 'transaction__phone'
        ).order_by('-created_at')[:3]

        return [{
            'id': review.id,
            'rating': review.rating,
            'comment': review.comment,
            'reviewer_username': review.reviewer.username,
            'phone_model': review.transaction.phone.model,
            'created_at': review.created_at,
            'is_punctual': review.is_punctual,
            'is_friendly': review.is_friendly,
            'is_honest': review.is_honest,
            'is_fast_response': review.is_fast_response,
        } for review in recent_reviews]

    def get_penalty_status(self, obj):
        """현재 패널티 상태"""
        active_penalty = obj.used_phone_penalties.filter(status='active').first()
        if active_penalty and active_penalty.is_active():
            return {
                'has_penalty': True,
                'penalty_type': active_penalty.get_penalty_type_display(),
                'end_date': active_penalty.end_date,
                'reason': active_penalty.reason
            }
        return {'has_penalty': False}
