from rest_framework import serializers
from api.models import *

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

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    active_groupbuy = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'category', 'category_name',
                'product_type', 'base_price', 'image_url', 'is_available', 'active_groupbuy',
                'carrier', 'registration_type', 'plan_info', 'contract_info', 
                'total_support_amount', 'release_date']

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
    
    class Meta:
        model = GroupBuy
        fields = ['id', 'title', 'description', 'product', 'product_name', 'product_detail', 'creator', 'creator_name',
                'status', 'min_participants', 'max_participants',
                'start_time', 'end_time', 'current_participants']
        extra_kwargs = {
            'product': {'required': True, 'write_only': False},  # 쓰기 가능하게 유지
            'min_participants': {'required': True, 'min_value': 2},
            'max_participants': {'required': True, 'min_value': 2, 'max_value': 5},
            'end_time': {'required': True}
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
            
            if end_time - now < timedelta(hours=24):
                raise serializers.ValidationError({
                    'end_time': '공구 기간은 최소 24시간 이상이어야 합니다.'
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