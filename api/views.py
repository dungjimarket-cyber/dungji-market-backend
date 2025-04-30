from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import authentication_classes, permission_classes, api_view, action
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authtoken.models import Token
from .models import Category, Product, GroupBuy, Participation, Wishlist, Review
from .serializers import CategorySerializer, ProductSerializer, GroupBuySerializer, ParticipationSerializer, WishlistSerializer, ReviewSerializer
from .utils import update_groupbuy_status, update_groupbuys_status
import json
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    try:
        data = request.data
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', '')

        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
            sns_type='email'
        )

        return Response(
            {'message': 'User registered successfully'},
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        logger.error(f'Error registering user: {str(e)}')
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def create_sns_user(request):
    try:
        data = request.data
        sns_id = data.get('sns_id')
        sns_type = data.get('sns_type')
        email = data.get('email')
        name = data.get('name', '')
        profile_image = data.get('profile_image', '')
        
        # 디버깅 로그 추가
        logger.info(f"SNS 로그인 요청: sns_id={sns_id}, sns_type={sns_type}, email={email}, name={name}")
        logger.info(f"프로필 이미지 URL: {profile_image}")

        if not sns_id or not sns_type or not email:
            return Response(
                {'error': 'SNS ID, type, and email are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user exists by sns_id
        user = User.objects.filter(sns_id=sns_id).first()
        if user:
            # 기존 사용자 정보 업데이트
            user.last_login = timezone.now()
            # 프로필 이미지 매번 업데이트 (변경사항이 있을 수 있으므로)
            if profile_image:
                logger.info(f"기존 사용자({user.id})의 프로필 이미지 업데이트: {profile_image}")
                user.profile_image = profile_image
            user.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'jwt': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
                'user_id': user.id,
                'username': user.get_full_name() or user.username,
                'phone_number': user.phone_number,
                'profile_image': user.profile_image,
                'sns_type': user.sns_type,
                'sns_id': user.sns_id,
                'email': user.email,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            })

        # Check if user exists by email
        user = User.objects.filter(email=email).first()
        if user:
            if user.sns_type != 'email':
                return Response(
                    {'error': 'Email already registered with different SNS provider'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Update existing email user with SNS info
            user.sns_id = sns_id
            user.sns_type = sns_type
            if profile_image:
                user.profile_image = profile_image
            user.save()
        else:
            # Create new user
            logger.info(f"새 사용자 생성: email={email}, sns_type={sns_type}, sns_id={sns_id}")
            logger.info(f"새 사용자 프로필 이미지: {profile_image}")
            
            # 사용자 생성
            user = User.objects.create_user(
                username=email,
                email=email,
                password=None,  # SNS users don't need password
                first_name=name,
                sns_type=sns_type,
                sns_id=sns_id
            )
            
            # 프로필 이미지 별도 설정
            if profile_image:
                user.profile_image = profile_image
                user.save()
                logger.info(f"사용자 프로필 이미지 저장 완료: {user.id}")

        # JWT 토큰 발급
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        # 로깅 추가
        logger.info(f"반환할 사용자 정보: id={user.id}, first_name={user.first_name}, username={user.username}, full_name={user.get_full_name()}")
        
        return Response({
            'jwt': {
                'access': access_token,
                'refresh': refresh_token,
            },
            'user_id': user.id,
            'username': user.first_name or user.get_full_name() or user.username,  # 닉네임 우선 사용
            'phone_number': user.phone_number,
            'profile_image': user.profile_image,
            'sns_type': user.sns_type,
            'sns_id': user.sns_id,
            'email': user.email,
            'access': access_token,
            'refresh': refresh_token,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f'Error creating SNS user: {str(e)}')
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = Category.objects.all()
        parent_id = self.request.query_params.get('parent', None)
        if parent_id is not None:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset

    def retrieve(self, request, *args, **kwargs):
        # Get category by slug
        category = self.get_object()
        serializer = self.get_serializer(category)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        category = self.get_object()
        products = Product.objects.filter(category=category)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Product.objects.all()
        category = self.request.query_params.get('category', None)
        category_type = self.request.query_params.get('category_type', None)
        product_type = self.request.query_params.get('product_type', None)
        
        if category:
            queryset = queryset.filter(category__slug=category)
        if category_type:
            queryset = queryset.filter(category__detail_type=category_type)
        if product_type:
            queryset = queryset.filter(product_type=product_type)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        # 메인 상품 데이터 추출
        product_data = request.data.copy()
        
        # 카테고리별 상세 정보 추출
        detail_data = {}
        for detail_type in [
            'telecom_detail', 'electronics_detail', 'rental_detail', 
            'subscription_detail', 'standard_detail'
        ]:
            if detail_type in request.data:
                detail_data[detail_type] = request.data.pop(detail_type)
        
        # 커스텀 필드 데이터 추출
        custom_fields = {}
        if 'custom_fields' in request.data:
            custom_fields = request.data.pop('custom_fields')
        
        # 트랜잭션으로 모든 작업 처리
        with transaction.atomic():
            # 상품 생성
            serializer = self.get_serializer(data=product_data)
            serializer.is_valid(raise_exception=True)
            product = serializer.save()
            
            # 카테고리 상세 정보 저장
            if product.category:
                category_detail_type = product.category.detail_type
                if category_detail_type == 'telecom' and 'telecom_detail' in detail_data:
                    telecom_data = detail_data['telecom_detail']
                    telecom_serializer = TelecomProductDetailSerializer(data=telecom_data)
                    if telecom_serializer.is_valid():
                        telecom_serializer.save(product=product)
                elif category_detail_type == 'electronics' and 'electronics_detail' in detail_data:
                    electronics_data = detail_data['electronics_detail']
                    electronics_serializer = ElectronicsProductDetailSerializer(data=electronics_data)
                    if electronics_serializer.is_valid():
                        electronics_serializer.save(product=product)
                elif category_detail_type == 'rental' and 'rental_detail' in detail_data:
                    rental_data = detail_data['rental_detail']
                    rental_serializer = RentalProductDetailSerializer(data=rental_data)
                    if rental_serializer.is_valid():
                        rental_serializer.save(product=product)
                elif category_detail_type == 'subscription' and 'subscription_detail' in detail_data:
                    subscription_data = detail_data['subscription_detail']
                    subscription_serializer = SubscriptionProductDetailSerializer(data=subscription_data)
                    if subscription_serializer.is_valid():
                        subscription_serializer.save(product=product)
                else:
                    standard_data = detail_data.get('standard_detail', {})
                    standard_serializer = StandardProductDetailSerializer(data=standard_data)
                    if standard_serializer.is_valid():
                        standard_serializer.save(product=product)
            
            # 커스텀 필드 값 저장
            for field_name, value in custom_fields.items():
                try:
                    field = ProductCustomField.objects.get(
                        category=product.category, 
                        field_name=field_name
                    )
                    
                    field_type = field.field_type
                    field_value = ProductCustomValue(product=product, field=field)
                    
                    if field_type == 'text':
                        field_value.text_value = value
                    elif field_type == 'number':
                        field_value.number_value = value
                    elif field_type == 'boolean':
                        field_value.boolean_value = value
                    elif field_type == 'date':
                        field_value.date_value = value
                    
                    field_value.save()
                except ProductCustomField.DoesNotExist:
                    pass
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        # update 메서드도 create와 유사하게 구현
        instance = self.get_object()
        
        # 메인 상품 데이터 추출
        product_data = request.data.copy()
        
        # 카테고리별 상세 정보 추출
        detail_data = {}
        for detail_type in [
            'telecom_detail', 'electronics_detail', 'rental_detail', 
            'subscription_detail', 'standard_detail'
        ]:
            if detail_type in request.data:
                detail_data[detail_type] = request.data.pop(detail_type)
        
        # 커스텀 필드 데이터 추출
        custom_fields = {}
        if 'custom_fields' in request.data:
            custom_fields = request.data.pop('custom_fields')
        
        # 트랜잭션으로 모든 작업 처리
        with transaction.atomic():
            # 상품 업데이트
            serializer = self.get_serializer(instance, data=product_data, partial=True)
            serializer.is_valid(raise_exception=True)
            product = serializer.save()
            
            # 카테고리 상세 정보 업데이트
            if product.category:
                category_detail_type = product.category.detail_type
                
                if category_detail_type == 'telecom':
                    telecom_data = detail_data.get('telecom_detail', {})
                    telecom_instance = getattr(product, 'telecom_detail', None)
                    if telecom_instance:
                        telecom_serializer = TelecomProductDetailSerializer(telecom_instance, data=telecom_data, partial=True)
                    else:
                        telecom_serializer = TelecomProductDetailSerializer(data=telecom_data)
                    
                    if telecom_serializer.is_valid():
                        telecom_serializer.save(product=product)
                        
                # 다른 카테고리 타입에 대해서도 유사하게 처리...
            
            # 커스텀 필드 값 업데이트
            for field_name, value in custom_fields.items():
                try:
                    field = ProductCustomField.objects.get(
                        category=product.category, 
                        field_name=field_name
                    )
                    
                    try:
                        field_value = ProductCustomValue.objects.get(product=product, field=field)
                    except ProductCustomValue.DoesNotExist:
                        field_value = ProductCustomValue(product=product, field=field)
                    
                    field_type = field.field_type
                    if field_type == 'text':
                        field_value.text_value = value
                    elif field_type == 'number':
                        field_value.number_value = value
                    elif field_type == 'boolean':
                        field_value.boolean_value = value
                    elif field_type == 'date':
                        field_value.date_value = value
                    
                    field_value.save()
                except ProductCustomField.DoesNotExist:
                    pass
            
            return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category_type(self, request):
        category_type = request.query_params.get('type', None)
        if not category_type:
            return Response({'error': '카테고리 타입을 지정해주세요.'}, status=status.HTTP_400_BAD_REQUEST)
            
        products = Product.objects.filter(category__detail_type=category_type)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

@api_view(['GET'])
def get_category_fields(request, category_id):
    """카테고리별 필수 필드 및 커스텀 필드 정보 반환"""
    try:
        category = Category.objects.get(id=category_id)
        
        # 카테고리 기본 정보
        data = {
            'id': category.id,
            'name': category.name,
            'detail_type': category.detail_type,
            'required_fields': category.required_fields,
        }
        
        # 카테고리별 필수 필드 정보
        detail_fields = []
        if category.detail_type == 'telecom':
            detail_fields = [
                {'name': 'carrier', 'type': 'select', 'required': True, 
                 'options': [{'value': k, 'label': v} for k, v in Product.CARRIER_CHOICES]},
                {'name': 'registration_type', 'type': 'select', 'required': True,
                 'options': [{'value': k, 'label': v} for k, v in Product.REGISTRATION_TYPE_CHOICES]},
                {'name': 'plan_info', 'type': 'text', 'required': True},
                {'name': 'contract_info', 'type': 'text', 'required': True},
                {'name': 'total_support_amount', 'type': 'number', 'required': True},
            ]
        elif category.detail_type == 'electronics':
            detail_fields = [
                {'name': 'manufacturer', 'type': 'text', 'required': True},
                {'name': 'warranty_period', 'type': 'number', 'required': True},
                {'name': 'power_consumption', 'type': 'text', 'required': False},
                {'name': 'dimensions', 'type': 'text', 'required': False},
            ]
        elif category.detail_type == 'rental':
            detail_fields = [
                {'name': 'rental_period_options', 'type': 'json', 'required': True},
                {'name': 'maintenance_info', 'type': 'text', 'required': False},
                {'name': 'deposit_amount', 'type': 'number', 'required': True},
                {'name': 'monthly_fee', 'type': 'number', 'required': True},
            ]
        elif category.detail_type == 'subscription':
            detail_fields = [
                {'name': 'billing_cycle', 'type': 'select', 'required': True,
                 'options': [{'value': k, 'label': v} for k, v in SubscriptionProductDetail.BILLING_CYCLE_CHOICES]},
                {'name': 'auto_renewal', 'type': 'boolean', 'required': True},
                {'name': 'free_trial_days', 'type': 'number', 'required': False},
            ]
        elif category.detail_type == 'none':
            detail_fields = [
                {'name': 'brand', 'type': 'text', 'required': False},
                {'name': 'origin', 'type': 'text', 'required': False},
                {'name': 'shipping_fee', 'type': 'number', 'required': True},
                {'name': 'shipping_info', 'type': 'text', 'required': False},
            ]
            
        data['detail_fields'] = detail_fields
        
        # 커스텀 필드 정보
        custom_fields = []
        for field in category.custom_fields.all():
            custom_fields.append({
                'name': field.field_name,
                'label': field.field_label,
                'type': field.field_type,
                'required': field.is_required,
                'options': field.options if field.field_type == 'select' else [],
            })
        
        data['custom_fields'] = custom_fields
        
        return Response(data)
    except Category.DoesNotExist:
        return Response({'error': '카테고리를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

# views.py
from django.db.models import Count
from django.utils import timezone

class GroupBuyViewSet(ModelViewSet):
    serializer_class = GroupBuySerializer
    queryset = GroupBuy.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = GroupBuy.objects.select_related('product', 'product__category').all()
        status_param = self.request.query_params.get('status', None)
        category_id = self.request.query_params.get('category', None)

        # status 필터 처리
        if status_param == 'active':
            queryset = queryset.filter(end_time__gt=timezone.now())
        elif status_param == 'completed':
            queryset = queryset.filter(end_time__lte=timezone.now())

        # category 필터 처리
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
            
        # 공구 상태 자동 업데이트 (최대 100개까지만 처리)
        update_groupbuys_status(queryset[:100])

        return queryset

    @action(detail=False)
    def popular(self, request):
        popular_groupbuys = GroupBuy.objects.annotate(
            curent_participants=Count('participation')
        ).filter(
            end_time__gt=timezone.now()
        ).order_by('-curent_participants')[:3]
        
        # 공구 상태 자동 업데이트
        update_groupbuys_status(popular_groupbuys)
        
        serializer = self.get_serializer(popular_groupbuys, many=True)
        data = serializer.data
        
        now = timezone.now()
        
        # 계산된 상태 및 남은 시간 추가
        for item, instance in zip(data, popular_groupbuys):
            end_time = instance.end_time
            item['calculated_status'] = instance.status
            
            # 남은 시간 계산 (초 단위)
            if now < end_time:
                remaining_seconds = int((end_time - now).total_seconds())
                item['remaining_seconds'] = remaining_seconds
            else:
                item['remaining_seconds'] = 0
                
        return Response(data)

    @action(detail=False)
    def recent(self, request):
        recent_groupbuys = GroupBuy.objects.filter(
            end_time__gt=timezone.now()
        ).order_by('-start_time')[:3]
        
        # 공구 상태 자동 업데이트
        update_groupbuys_status(recent_groupbuys)
        
        serializer = self.get_serializer(recent_groupbuys, many=True)
        data = serializer.data
        
        now = timezone.now()
        
        # 계산된 상태 및 남은 시간 추가
        for item, instance in zip(data, recent_groupbuys):
            end_time = instance.end_time
            item['calculated_status'] = instance.status
            
            # 남은 시간 계산 (초 단위)
            if now < end_time:
                remaining_seconds = int((end_time - now).total_seconds())
                item['remaining_seconds'] = remaining_seconds
            else:
                item['remaining_seconds'] = 0
                
        return Response(data)  # Require authentication for creating group buys

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'popular', 'recent']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        now = timezone.now()
        for item, instance in zip(data, queryset):
            # 계산된 상태 추가
            end_time = instance.end_time
            if instance.status == 'recruiting' and now > end_time:
                if instance.current_participants >= instance.min_participants:
                    item['calculated_status'] = 'completed'
                else:
                    item['calculated_status'] = 'cancelled'
            else:
                item['calculated_status'] = instance.status
            # 남은 시간 계산 (초 단위)
            if now < end_time:
                remaining_seconds = int((end_time - now).total_seconds())
                item['remaining_seconds'] = remaining_seconds
            else:
                item['remaining_seconds'] = 0
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        update_groupbuy_status(instance)
        serializer = self.get_serializer(instance)
        data = serializer.data
        now = timezone.now()
        end_time = instance.end_time
        if instance.status == 'recruiting' and now > end_time:
            if instance.current_participants >= instance.min_participants:
                data['calculated_status'] = 'completed'
            else:
                data['calculated_status'] = 'cancelled'
        else:
            data['calculated_status'] = instance.status
        if now < end_time:
            remaining_seconds = int((end_time - now).total_seconds())
            data['remaining_seconds'] = remaining_seconds
        else:
            data['remaining_seconds'] = 0
        return Response(data)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @action(detail=False, methods=['get'])
    def my_groupbuys(self, request):
        user_groupbuys = self.get_queryset().filter(creator=request.user)
        serializer = self.get_serializer(user_groupbuys, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def joined_groupbuys(self, request):
        joined = self.get_queryset().filter(participants=request.user)
        serializer = self.get_serializer(joined, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """사용자가 공구에 참여하는 API"""
        groupbuy = self.get_object()
        user = request.user
        
        # 이미 참여 중인지 확인
        if Participation.objects.filter(user=user, groupbuy=groupbuy).exists():
            return Response(
                {'error': '이미 참여 중인 공구입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 공구 상태 확인
        now = timezone.now()
        if groupbuy.status != 'recruiting' or now > groupbuy.end_time:
            return Response(
                {'error': '참여할 수 없는 공구입니다. 모집이 종료되었거나 마감되었습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최대 참여자 수 확인
        if groupbuy.current_participants >= groupbuy.max_participants:
            return Response(
                {'error': '최대 참여자 수에 도달했습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 참여 생성
        participation = Participation.objects.create(
            user=user,
            groupbuy=groupbuy,
            is_leader=False  # 일반 참여자
        )
        
        # 현재 참여자 수 증가
        groupbuy.current_participants += 1
        groupbuy.save(update_fields=['current_participants'])
        
        return Response({
            'id': participation.id,
            'user_id': user.id,
            'groupbuy_id': groupbuy.id,
            'joined_at': participation.joined_at,
            'message': '공구 참여가 완료되었습니다.'
        }, status=status.HTTP_201_CREATED)

class ParticipationViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Participation.objects.all()
    serializer_class = ParticipationSerializer

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'email': user.email,
            'username': user.get_full_name() or user.username,
            'profile_image': user.profile_image,
            'sns_type': user.sns_type,
        })

    def patch(self, request):
        user = request.user
        email = request.data.get('email')
        
        if email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({'error': '이미 사용 중인 이메일입니다.'}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email
            user.save()

        return Response({
            'id': user.id,
            'email': user.email,
            'username': user.get_full_name() or user.username,
            'profile_image': user.profile_image,
            'sns_type': user.sns_type,
        })

class WishlistViewSet(ModelViewSet):
    """찜하기 기능을 위한 ViewSet"""
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # 사용자가 찜하기를 생성할 때 현재 사용자를 자동으로 설정
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def check_wished(self, request):
        """특정 공구에 대한 찜하기 여부 확인"""
        groupbuy_id = request.query_params.get('groupbuy_id')
        if not groupbuy_id:
            return Response({"error": "공구 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        is_wished = Wishlist.objects.filter(
            user=request.user,
            groupbuy_id=groupbuy_id
        ).exists()
        
        return Response({"is_wished": is_wished})
    
    @action(detail=False, methods=['post'])
    def toggle_wish(self, request):
        """찜하기 토글 (생성/삭제)"""
        groupbuy_id = request.data.get('groupbuy_id')
        if not groupbuy_id:
            return Response({"error": "공구 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            groupbuy = GroupBuy.objects.get(id=groupbuy_id)
            wish_exists = Wishlist.objects.filter(user=request.user, groupbuy=groupbuy).exists()
            
            # 이미 찜한 경우 삭제, 아닌 경우 추가
            if wish_exists:
                Wishlist.objects.filter(user=request.user, groupbuy=groupbuy).delete()
                return Response({"status": "unwished", "message": "찜하기가 취소되었습니다."}, status=status.HTTP_200_OK)
            else:
                wishlist = Wishlist.objects.create(user=request.user, groupbuy=groupbuy)
                serializer = self.get_serializer(wishlist)
                return Response({"status": "wished", "message": "찜하기가 추가되었습니다.", "data": serializer.data}, status=status.HTTP_201_CREATED)
        except GroupBuy.DoesNotExist:
            return Response({"error": "존재하지 않는 공구입니다."}, status=status.HTTP_404_NOT_FOUND)


class ReviewViewSet(ModelViewSet):
    """리뷰 및 별점 기능을 위한 ViewSet"""
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # 사용자 자신의 리뷰만 조회하거나 파라미터로 특정 공구 리뷰 조회
        groupbuy_id = self.request.query_params.get('groupbuy_id')
        if groupbuy_id:
            return Review.objects.filter(groupbuy_id=groupbuy_id)
        return Review.objects.filter(user=self.request.user)
    
    def get_permissions(self):
        """리뷰 조회는 로그인 없이 가능, 나머지 동작은 로그인 필요"""
        if self.action in ['list', 'retrieve', 'groupbuy_reviews']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """리뷰 작성 시 현재 사용자 정보 자동 설정 및 자신의 공구에는 리뷰 작성 불가"""
        groupbuy = serializer.validated_data.get('groupbuy')
        
        # 자신이 만든 공구에는 리뷰를 작성할 수 없음
        if groupbuy.creator == self.request.user:
            raise serializers.ValidationError({
                'non_field_errors': ['자신이 만든 공구에는 리뷰를 작성할 수 없습니다.']
            })
            
        # 리뷰 저장
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def groupbuy_reviews(self, request):
        """특정 공구의 리뷰 목록 조회"""
        groupbuy_id = request.query_params.get('groupbuy_id')
        if not groupbuy_id:
            return Response({"error": "공구 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        reviews = Review.objects.filter(groupbuy_id=groupbuy_id).order_by('-created_at')
        serializer = self.get_serializer(reviews, many=True)
        
        # 평점 평균 계산
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        
        return Response({
            "reviews": serializer.data,
            "count": reviews.count(),
            "avg_rating": round(avg_rating, 1)
        })
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """내가 쓰기 리뷰 목록"""
        reviews = Review.objects.filter(user=request.user).order_by('-created_at')
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """리뷰 신고"""
        review = self.get_object()
        reason = request.data.get('reason', '')
        
        # 신고 로직 구현 (예: 관리자에게 알림 발송 등)
        # 실제 구현은 생략하고 신고 처리를 표시만 함
        
        return Response({
            "status": "success",
            "message": "리뷰 신고가 접수되었습니다."
        }, status=status.HTTP_200_OK)
