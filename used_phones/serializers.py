"""
Used Phones Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer

User = get_user_model()


class UsedPhoneImageSerializer(serializers.ModelSerializer):
    """중고폰 이미지 시리얼라이저"""
    
    class Meta:
        model = UsedPhoneImage
        fields = ['id', 'image', 'thumbnail', 'is_main', 'order']
        read_only_fields = ['id']


class SellerSerializer(serializers.ModelSerializer):
    """판매자 정보 시리얼라이저"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class UsedPhoneListSerializer(serializers.ModelSerializer):
    """중고폰 목록 시리얼라이저"""
    images = UsedPhoneImageSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()
    region_name = serializers.CharField(source='region.full_address', read_only=True)
    
    class Meta:
        model = UsedPhone
        fields = [
            'id', 'brand', 'model', 'storage', 'color', 'price', 
            'min_offer_price', 'accept_offers', 'condition_grade',
            'battery_status', 'status', 'view_count', 'favorite_count',
            'offer_count', 'region_name', 'images', 'is_favorite',
            'created_at'
        ]
    
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
    region_name = serializers.CharField(source='region.full_address', read_only=True)
    
    class Meta:
        model = UsedPhone
        fields = '__all__'
        read_only_fields = ['id', 'seller', 'view_count', 'favorite_count', 
                           'offer_count', 'created_at', 'updated_at']
    
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
        required=False
    )
    
    class Meta:
        model = UsedPhone
        exclude = ['seller', 'view_count', 'favorite_count', 'offer_count', 
                  'status', 'sold_at']
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        phone = UsedPhone.objects.create(**validated_data)
        
        # 이미지 처리
        for index, image in enumerate(images_data):
            UsedPhoneImage.objects.create(
                phone=phone,
                image=image,
                is_main=(index == 0),
                order=index
            )
        
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
