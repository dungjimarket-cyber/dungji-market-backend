from rest_framework import serializers
from .models import Product, Category, GroupBuy, Participation, TelecomProductDetail, ElectronicsProductDetail, RentalProductDetail, SubscriptionProductDetail, StandardProductDetail, ProductCustomValue, Wishlist, Review
from django.contrib.auth import get_user_model

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'parent_name', 'is_service', 'subcategories', 'product_count']

    def get_subcategories(self, obj):
        subcategories = Category.objects.filter(parent=obj)
        return CategorySerializer(subcategories, many=True).data

    def get_product_count(self, obj):
        return Product.objects.filter(category=obj).count()

class TelecomProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelecomProductDetail
        fields = ['carrier', 'registration_type', 'plan_info', 'contract_info']

class ElectronicsProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectronicsProductDetail
        fields = ['manufacturer', 'warranty_period', 'power_consumption', 'dimensions']

class RentalProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalProductDetail
        fields = ['rental_period_options', 'maintenance_info', 'deposit_amount', 'monthly_fee']

class SubscriptionProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionProductDetail
        fields = ['billing_cycle', 'auto_renewal', 'free_trial_days']

class StandardProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandardProductDetail
        fields = ['brand', 'origin', 'shipping_fee', 'shipping_info']

class ProductCustomValueSerializer(serializers.ModelSerializer):
    field_name = serializers.CharField(source='field.field_name', read_only=True)
    field_type = serializers.CharField(source='field.field_type', read_only=True)
    field_label = serializers.CharField(source='field.field_label', read_only=True)
    
    class Meta:
        model = ProductCustomValue
        fields = ['field_name', 'field_label', 'field_type', 'text_value', 'number_value', 'boolean_value', 'date_value']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_detail_type = serializers.CharField(source='category.detail_type', read_only=True)
    active_groupbuy = serializers.SerializerMethodField()
    telecom_detail = TelecomProductDetailSerializer(read_only=True)
    electronics_detail = ElectronicsProductDetailSerializer(read_only=True)
    rental_detail = RentalProductDetailSerializer(read_only=True)
    subscription_detail = SubscriptionProductDetailSerializer(read_only=True)
    standard_detail = StandardProductDetailSerializer(read_only=True)
    custom_values = ProductCustomValueSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'category', 'category_name',
                'category_detail_type', 'product_type', 'base_price', 'image_url', 
                'is_available', 'active_groupbuy', 'release_date', 'attributes',
                'telecom_detail', 'electronics_detail', 'rental_detail', 
                'subscription_detail', 'standard_detail', 'custom_values']

    def get_active_groupbuy(self, obj):
        active = GroupBuy.objects.filter(
            product=obj,
            status__in=['recruiting', 'bidding', 'voting']
        ).first()
        if active:
            return {
                'id': active.id,
                'status': active.status,
                'current_participants': active.current_participants,
                'max_participants': active.max_participants
            }
        return None

class GroupBuySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    creator_name = serializers.CharField(source='creator.first_name', read_only=True)
    # product_detail 필드는 제거 (중복 및 오류 방지)
    product_details = ProductSerializer(source='product', read_only=True)
    creator = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    
    class Meta:
        model = GroupBuy
        fields = ['id', 'title', 'description', 'product', 'product_name', 'creator', 'creator_name',
                'status', 'min_participants', 'max_participants',
                'start_time', 'end_time', 'current_participants', 'region_type', 'product_details']
        extra_kwargs = {
            'product': {'required': True, 'write_only': False},  # 쓰기 가능하게 유지
            'creator': {'required': True},  # creator 필드를 필수로 지정
            'min_participants': {'required': True, 'min_value': 1},
            'max_participants': {'required': True, 'min_value': 1, 'max_value': 100},
            'end_time': {'required': True},
            'region_type': {'required': False},
            # product_details는 read_only=True로 serializer에서 처리
            'product_details': {'read_only': True}
        }

    def validate(self, data):
        if data.get('min_participants', 0) > data.get('max_participants', 0):
            raise serializers.ValidationError({
                'min_participants': '최소 참여자 수는 최대 참여자 수보다 클 수 없습니다.'
            })
        
        if data.get('end_time'):
            from django.utils import timezone
            from datetime import timedelta
            now = timezone.now()
            end_time = data['end_time']
            
            if end_time - now < timedelta(hours=6):
                raise serializers.ValidationError({
                    'end_time': '공구 기간은 최소 6시간 이상이어야 합니다.'
                })
            if end_time - now > timedelta(hours=48):
                raise serializers.ValidationError({
                    'end_time': '공구 기간은 최대 48시간까지 설정 가능합니다.'
                })
        
        return data

class ParticipationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.first_name', read_only=True)
    groupbuy_status = serializers.CharField(source='groupbuy.status', read_only=True)

    class Meta:
        model = Participation
        fields = ['id', 'user', 'user_name', 'groupbuy', 'groupbuy_status',
                'joined_at', 'is_leader', 'is_locked']


class WishlistSerializer(serializers.ModelSerializer):
    """찜하기 기능을 위한 시리얼라이저"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    groupbuy_title = serializers.CharField(source='groupbuy.title', read_only=True)
    groupbuy_status = serializers.CharField(source='groupbuy.status', read_only=True)
    product_name = serializers.CharField(source='groupbuy.product.name', read_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'user_name', 'groupbuy', 'groupbuy_title', 'groupbuy_status', 
                'product_name', 'created_at']
        extra_kwargs = {
            'user': {'required': True},
            'groupbuy': {'required': True}
        }


class ReviewSerializer(serializers.ModelSerializer):
    """리뷰 및 별점 기능을 위한 시리얼라이저"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_profile_image = serializers.URLField(source='user.profile_image', read_only=True)
    groupbuy_title = serializers.CharField(source='groupbuy.title', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'user', 'user_name', 'user_profile_image', 'groupbuy', 'groupbuy_title',
                'rating', 'content', 'created_at', 'updated_at', 'is_purchased']
        extra_kwargs = {
            'user': {'required': True, 'write_only': True},
            'groupbuy': {'required': True},
            'rating': {'required': True, 'min_value': 1, 'max_value': 5},
            'content': {'required': True},
            'is_purchased': {'read_only': True}
        }
    
    def validate(self, data):
        """
        사용자가 해당 공구에 참여했는지 확인하여 is_purchased 필드 자동 업데이트
        """
        user = self.context['request'].user
        groupbuy = data.get('groupbuy')
        
        # 참여 여부 확인
        participation = Participation.objects.filter(user=user, groupbuy=groupbuy).exists()
        # 중복 리뷰 확인 (수정이 아닌 경우)
        if not self.instance and Review.objects.filter(user=user, groupbuy=groupbuy).exists():
            raise serializers.ValidationError({
                "error": "이미 리뷰를 작성하셨습니다."
            })
            
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        groupbuy = validated_data.get('groupbuy')
        
        # 참여 여부 확인
        is_purchased = Participation.objects.filter(user=user, groupbuy=groupbuy).exists()
        
        review = Review.objects.create(
            **validated_data,
            user=user,
            is_purchased=is_purchased
        )
        return review