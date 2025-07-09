from rest_framework import serializers
from .models import Product, Category, GroupBuy, Participation, TelecomProductDetail, ElectronicsProductDetail, RentalProductDetail, SubscriptionProductDetail, StandardProductDetail, ProductCustomValue, Wishlist, Review, GroupBuyTelecomDetail, Bid
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.crypto import get_random_string

User = get_user_model()

class FindUsernameSerializer(serializers.Serializer):
  email = serializers.EmailField(required=True)

  def validate_email(self, value):
    if not User.objects.filter(email=value).exists():
      raise serializers.ValidationError('해당 이메일로 가입된 계정이 없습니다.')
    return value

  def get_username(self):
    email = self.validated_data['email']
    user = User.objects.get(email=email)
    return user.username

class ResetPasswordSerializer(serializers.Serializer):
  email = serializers.EmailField(required=True)
  username = serializers.CharField(required=True)

  def validate(self, data):
    email = data.get('email')
    username = data.get('username')
    if not User.objects.filter(email=email, username=username).exists():
      raise serializers.ValidationError('입력하신 정보와 일치하는 계정이 없습니다.')
    return data

  def save(self):
    email = self.validated_data['email']
    username = self.validated_data['username']
    user = User.objects.get(email=email, username=username)
    temp_password = get_random_string(length=10)
    user.set_password(temp_password)
    user.save()
    send_mail(
      '[둥지마켓] 임시 비밀번호 안내',
      f'임시 비밀번호: {temp_password}\n로그인 후 반드시 비밀번호를 변경해 주세요.',
      'noreply@dungji-market.com',
      [email],
      fail_silently=False,
    )
    return temp_password

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

class GroupBuyTelecomDetailSerializer(serializers.ModelSerializer):
    subscription_type_korean = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupBuyTelecomDetail
        fields = ['telecom_carrier', 'subscription_type', 'subscription_type_korean', 'plan_info', 'contract_period']
    
    def get_subscription_type_korean(self, obj):
        """가입유형을 한글로 변환하여 반환"""
        subscription_type_map = {
            'new': '신규가입',
            'transfer': '번호이동',
            'change': '기기변경',
        }
        return subscription_type_map.get(obj.subscription_type, obj.subscription_type)

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
    # creator_name 필드를 모델의 creator_nickname 필드를 사용하도록 변경
    # 계획적 호환성을 위해 필드 이름은 creator_name으로 유지
    creator_name = serializers.CharField(source='creator_nickname', read_only=True)
    # 방장(creator) 사용자 이름을 명확하게 노출
    host_username = serializers.CharField(source='creator.username', read_only=True)
    # product_details는 GroupBuy 모델의 product_details 필드와 product의 정보를 병합하여 제공
    product_details = serializers.SerializerMethodField()
    creator = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    
    telecom_detail = GroupBuyTelecomDetailSerializer(read_only=True)
    
    class Meta:
        model = GroupBuy
        fields = ['id', 'title', 'description', 'product', 'product_name', 'creator', 'creator_name',
                'host_username', 'status', 'min_participants', 'max_participants', 'start_time', 'end_time', 
                'current_participants', 'region_type', 'telecom_detail', 'product_details']
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

    def get_product_details(self, obj):
        """product_details 필드를 가져오는 메서드
        
        1. GroupBuyTelecomDetail 모델에 저장된 통신 정보를 우선 사용
        2. 없는 필드는 상품의 원래 정보로 보완
        """
        # 기본 상품 정보 가져오기
        product_info = ProductSerializer(obj.product).data
        
        # 통신 상품인 경우 telecom_detail 정보 확인
        if 'telecom_detail' in product_info:
            telecom_detail = product_info.get('telecom_detail', {})
            
            # GroupBuyTelecomDetail 모델에서 통신 정보 가져오기
            try:
                gb_telecom = obj.telecom_detail
                if gb_telecom:
                    # 통신사 정보 업데이트
                    telecom_detail['carrier'] = gb_telecom.telecom_carrier
                    
                    # 가입유형 정보 업데이트
                    telecom_detail['registration_type'] = gb_telecom.subscription_type
                    
                    # 가입유형 한글명 추가
                    subscription_type_map = {
                        'new': '신규가입',
                        'transfer': '번호이동',
                        'change': '기기변경',
                    }
                    telecom_detail['registration_type_korean'] = subscription_type_map.get(gb_telecom.subscription_type, gb_telecom.subscription_type)
                    
                    # 요금제 정보 업데이트
                    telecom_detail['plan_info'] = gb_telecom.plan_info
                    
                    # 약정기간 정보 업데이트 (있는 경우)
                    if gb_telecom.contract_period:
                        telecom_detail['contract_info'] = gb_telecom.contract_period
            except GroupBuyTelecomDetail.DoesNotExist:
                # GroupBuyTelecomDetail이 없는 경우 기존 product_details에서 가져오기
                custom_details = obj.product_details or {}
                
                # 사용자가 입력한 통신사, 유형, 요금제 정보가 있으면 사용
                if custom_details:
                    # 사용자가 입력한 통신사 정보가 있으면 업데이트
                    if 'telecom_carrier' in custom_details:
                        telecom_detail['carrier'] = custom_details.get('telecom_carrier')
                        
                    # 사용자가 입력한 유형 정보가 있으면 업데이트
                    if 'subscription_type' in custom_details:
                        telecom_detail['registration_type'] = custom_details.get('subscription_type')
                        
                    # 사용자가 입력한 요금제 정보가 있으면 업데이트
                    if 'telecom_plan' in custom_details:
                        telecom_detail['plan_info'] = custom_details.get('telecom_plan')
            
            # 업데이트된 telecom_detail 정보를 product_info에 반영
            product_info['telecom_detail'] = telecom_detail
        
        # 최종 product_details 반환
        return product_info
        
    def validate(self, data):
        if data.get('min_participants', 0) > data.get('max_participants', 0):
            raise serializers.ValidationError({
                'min_participants': '최소 참여자 수는 최대 참여자 수보다 클 수 없습니다.'
            })
        
        # 활성 상태의 공구에 대해서만 중복 체크
        if data.get('product') and data.get('creator'):
            active_statuses = ['recruiting', 'bidding', 'voting', 'seller_confirmation']
            existing_groupbuy = GroupBuy.objects.filter(
                product=data['product'],
                creator=data['creator'],
                status__in=active_statuses
            ).first()
            
            if existing_groupbuy:
                raise serializers.ValidationError({
                    'product': '이미 해당 상품으로 진행 중인 공동구매가 있습니다. 기존 공구가 완료된 후 새로운 공구를 생성해주세요.'
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


class BidSerializer(serializers.ModelSerializer):
    """입찰 데이터를 위한 시리얼라이저
    
    판매자가 입찰한 내역 및 상태를 관리합니다.
    """
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    groupbuy_title = serializers.CharField(source='groupbuy.title', read_only=True)
    product_name = serializers.CharField(source='groupbuy.product.name', read_only=True)
    current_participants = serializers.IntegerField(source='groupbuy.current_participants', read_only=True)
    max_participants = serializers.IntegerField(source='groupbuy.max_participants', read_only=True)
    
    class Meta:
        model = Bid
        fields = ['id', 'groupbuy', 'groupbuy_title', 'product_name', 'seller', 'seller_name',
                 'bid_type', 'amount', 'message', 'contract_period', 'created_at', 'updated_at',
                 'is_selected', 'status', 'current_participants', 'max_participants']
        extra_kwargs = {
            'seller': {'required': True, 'write_only': True},
            'groupbuy': {'required': True},
            'amount': {'required': True, 'min_value': 0},
        }