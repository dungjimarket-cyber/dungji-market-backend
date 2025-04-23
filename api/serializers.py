from rest_framework import serializers
from .models import Product, Category, GroupBuy, Participation, TelecomProductDetail, ElectronicsProductDetail, RentalProductDetail, SubscriptionProductDetail, StandardProductDetail, ProductCustomValue
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
        fields = ['carrier', 'registration_type', 'plan_info', 'contract_info', 'total_support_amount']

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
    product_detail = ProductSerializer(source='product', read_only=True)
    creator = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    
    class Meta:
        model = GroupBuy
        fields = ['id', 'title', 'description', 'product', 'product_name', 'product_detail', 'creator', 'creator_name',
                'status', 'min_participants', 'max_participants',
                'start_time', 'end_time', 'current_participants', 'region_type', 'product_details']
        extra_kwargs = {
            'product': {'required': True, 'write_only': False},  # 쓰기 가능하게 유지
            'creator': {'required': True},  # creator 필드를 필수로 지정
            'min_participants': {'required': True, 'min_value': 1},
            'max_participants': {'required': True, 'min_value': 1, 'max_value': 100},
            'end_time': {'required': True},
            'region_type': {'required': False},
            'product_details': {'required': False}
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