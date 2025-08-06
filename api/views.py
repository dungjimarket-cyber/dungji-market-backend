from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import Q, Count, F, Sum, Avg, Case, When, Value, IntegerField
from rest_framework.decorators import action
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status, generics, filters
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authtoken.models import Token
from .models import Category, Product, GroupBuy, Participation, Wishlist, Review, Bid
from .models_region import Region
from .serializers import CategorySerializer, ProductSerializer, GroupBuySerializer, ParticipationSerializer, WishlistSerializer, ReviewSerializer, BidSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from .utils import update_groupbuy_status
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
        role = data.get('role', 'buyer')  # 기본값은 구매자
        
        # 로깅 추가
        logger.info(f"회원가입 요청: email={email}, name={name}, role={role}")

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

        # role 값이 유효한지 확인 (seller 또는 buyer만 허용)
        if role not in ['seller', 'buyer']:
            return Response(
                {'error': 'Invalid role. Must be either "seller" or "buyer".'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
            sns_type='email',
            role=role  # 사용자가 선택한 역할로 설정
        )
        
        logger.info(f"사용자 생성 완료: {email}, 역할: {role}")

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
        
        # 이메일이 없거나 빈 값인 경우 기본 이메일 생성
        if not email or email == '':
            email = f'{sns_id}@{sns_type}.user'
            logger.info(f"이메일 정보 없음, 기본 이메일 생성: {email}")
        
        # 디버깅 로그 추가
        logger.info(f"SNS 로그인 요청: sns_id={sns_id}, sns_type={sns_type}, email={email}, name={name}")
        logger.info(f"프로필 이미지 URL: {profile_image}")

        if not sns_id or not sns_type or not email:
            return Response(
                {'error': 'SNS ID, type, and email are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1차: SNS ID로 사용자 확인 (가장 중요한 체크)
        # 카카오 계정의 고유 ID로 사용자를 찾아서 PC/모바일 중복 가입 방지
        user = User.objects.filter(sns_id=sns_id, sns_type=sns_type).first()
        is_new_user = False  # 신규 사용자 여부 플래그
        
        if user:
            logger.info(f"SNS ID로 기존 사용자 찾음: user_id={user.id}, sns_id={sns_id}, sns_type={sns_type}")
            # 기존 사용자 정보 업데이트
            user.last_login = timezone.now()
            
            # 이메일이 변경되었거나 비어있었던 경우 업데이트
            # (카카오는 PC/모바일에서 다른 이메일을 제공할 수 있음)
            if email and email != user.email:
                logger.info(f"사용자({user.id})의 이메일 업데이트: {user.email} -> {email}")
                user.email = email
            
            # 프로필 이미지 매번 업데이트 (변경사항이 있을 수 있으므로)
            if profile_image:
                logger.info(f"사용자({user.id})의 프로필 이미지 업데이트")
                user.profile_image = profile_image
                
            user.save()
            # JWT 토큰 발급 - CustomTokenObtainPairSerializer 사용
            from api.serializers_jwt import CustomTokenObtainPairSerializer
            refresh = CustomTokenObtainPairSerializer.get_token(user)
            access_token = refresh.access_token
            
            return Response({
                'jwt': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                },
                'user_id': user.id,
                'username': user.get_full_name() or user.username,
                'phone_number': user.phone_number,
                'profile_image': user.profile_image,
                'sns_type': user.sns_type,
                'sns_id': user.sns_id,
                'email': user.email,
                'access': str(access_token),
                'refresh': str(refresh),
                'is_new_user': is_new_user  # 신규 사용자 여부 추가
            })

        # 2차: 이메일로 사용자 확인 (SNS ID로 찾지 못한 경우만)
        if email and email != f'{sns_id}@{sns_type}.user':  # 자동 생성 이메일이 아닌 경우만
            user = User.objects.filter(email=email).first()
            if user:
                # 같은 이메일을 가진 다른 SNS 타입의 계정이 있는 경우
                if user.sns_type and user.sns_type != 'email' and user.sns_type != sns_type:
                    logger.warning(f"이메일 중복: 기존 sns_type={user.sns_type}, 새로운 sns_type={sns_type}")
                    return Response(
                        {'error': f'이 이메일은 이미 {user.sns_type} 계정으로 가입되어 있습니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # 이메일로만 가입된 사용자인 경우 SNS 정보 업데이트
                elif user.sns_type == 'email' or not user.sns_type:
                    logger.info(f"이메일 사용자를 SNS 계정으로 연결: user_id={user.id}")
                    user.sns_id = sns_id
                    user.sns_type = sns_type
                    if profile_image:
                        user.profile_image = profile_image
                    user.save()
                    
                    # JWT 토큰 발급 - CustomTokenObtainPairSerializer 사용
                    from api.serializers_jwt import CustomTokenObtainPairSerializer
                    refresh = CustomTokenObtainPairSerializer.get_token(user)
                    access_token = refresh.access_token
                    
                    return Response({
                        'jwt': {
                            'access': str(access_token),
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
                        'refresh': str(refresh),
                        'is_new_user': is_new_user  # 신규 사용자 여부 추가
                    })
        
        # 3차: 새 사용자 생성 (SNS ID로도, 이메일로도 찾지 못한 경우)
        logger.info(f"새 사용자 생성: email={email}, sns_type={sns_type}, sns_id={sns_id}")
        logger.info(f"새 사용자 프로필 이미지: {profile_image}")
        
        # 카카오 간편가입 시 자동 닉네임 생성
        if sns_type == 'kakao' and (not name or name == ''):
            # role이 전달되지 않은 경우 기본적으로 buyer로 설정 
            role = data.get('role', 'buyer')
            
            # 역할에 따른 닉네임 프리픽스 설정
            if role == 'seller':
                nickname_prefix = '어미새'
            else:
                nickname_prefix = '참새'
            
            # 순차적인 번호 생성을 위해 현재 해당 프리픽스를 가진 사용자들의 번호 확인
            from django.db.models import Q
            import re
            
            # 참새로 시작하는 닉네임들 찾기 (nickname 필드 사용)
            existing_nicknames = User.objects.filter(
                Q(nickname__startswith=nickname_prefix)
            ).values_list('nickname', flat=True)
            
            # 사용된 번호들 추출
            used_numbers = []
            pattern = re.compile(rf'^{nickname_prefix}(\d+)$')
            
            for nickname in existing_nicknames:
                if nickname:  # nickname이 None이 아닌 경우만 처리
                    match = pattern.match(nickname)
                    if match:
                        used_numbers.append(int(match.group(1)))
            
            # 가장 작은 사용 가능한 번호 찾기
            if not used_numbers:
                next_number = 1
            else:
                # 1부터 시작해서 빈 번호 찾기
                used_numbers.sort()
                next_number = 1
                for num in used_numbers:
                    if num == next_number:
                        next_number += 1
                    else:
                        break
            
            generated_nickname = f"{nickname_prefix}{next_number}"
            name = generated_nickname
            
            logger.info(f"카카오 간편가입 자동 닉네임 생성: {name}, role: {role}")
        
        # 사용자 생성
        user = User.objects.create_user(
            username=email,
            email=email,
            password=None,  # SNS users don't need password
            first_name=name,
            nickname=name,  # nickname 필드에도 동일하게 설정
            sns_type=sns_type,
            sns_id=sns_id,
            role=role if 'role' in locals() and role else 'buyer'  # role 설정
        )
        is_new_user = True  # 신규 사용자로 플래그 설정
        
        # 프로필 이미지 별도 설정
        if profile_image:
            user.profile_image = profile_image
            user.save()
            logger.info(f"사용자 프로필 이미지 저장 완료: {user.id}")

        # JWT 토큰 발급 - CustomTokenObtainPairSerializer 사용
        from api.serializers_jwt import CustomTokenObtainPairSerializer
        refresh = CustomTokenObtainPairSerializer.get_token(user)
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
            'is_new_user': is_new_user  # 신규 사용자 여부 추가
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
        
        # 부모 카테고리 필터링
        parent_id = self.request.query_params.get('parent', None)
        if parent_id is not None:
            queryset = queryset.filter(parent_id=parent_id)
        
        # 서비스 카테고리 필터링 (show_services 파라미터가 없으면 기본적으로 서비스가 아닌 카테고리만 표시)
        show_services = self.request.query_params.get('show_services', 'false').lower() == 'true'
        if not show_services:
            queryset = queryset.filter(is_service=True)  # 수정: is_service=True인 항목만 표시 (휴대폰만 표시)
        
        # 모든 카테고리 표시 옵션 (관리자용)
        show_all = self.request.query_params.get('show_all', 'false').lower() == 'true'
        if show_all:
            queryset = Category.objects.all()
            
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
                {'name': 'plan_info', 'type': 'select', 'required': True,
                 'options': [
                     {'value': '5G 라이트', 'label': '5G 라이트 (월 55,000원)'},
                     {'value': '5G 스탠다드', 'label': '5G 스탠다드 (월 75,000원)'},
                     {'value': '5G 프리미엄', 'label': '5G 프리미엄 (월 95,000원)'},
                     {'value': '5G 시그니처', 'label': '5G 시그니처 (월 130,000원)'},
                     {'value': '5G 플래티넘', 'label': '5G 플래티넘 (월 150,000원)'},
                 ]},
                {'name': 'contract_info', 'type': 'select', 'required': True,
                 'options': [
                     {'value': '24개월', 'label': '24개월 약정'},
                     {'value': '36개월', 'label': '36개월 약정'},
                     {'value': '무약정', 'label': '무약정'},
                 ]},
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
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers  # serializers 모듈 import 추가

class GroupBuyViewSet(ModelViewSet):
    serializer_class = GroupBuySerializer
    queryset = GroupBuy.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = GroupBuy.objects.select_related('product', 'product__category').all()
        status_param = self.request.query_params.get('status', None)
        category_id = self.request.query_params.get('category', None)
        sort_param = self.request.query_params.get('sort', None)
        ordering_param = self.request.query_params.get('ordering', None)
        
        # 통신사 관련 필터
        telecom_carrier = self.request.query_params.get('telecom_carrier', None)
        subscription_type = self.request.query_params.get('subscription_type', None)
        plan_info = self.request.query_params.get('plan_info', None)
        
        # 제조사 필터
        manufacturer = self.request.query_params.get('manufacturer', None)
        
        # 지역 검색 필터
        region_search = self.request.query_params.get('region_search', None)
        
        # 현재 시간 가져오기
        now = timezone.now()

        # status 필터 처리
        if status_param:
            # 쉼표로 구분된 상태값 처리
            if ',' in status_param:
                status_list = [s.strip() for s in status_param.split(',')]
                queryset = queryset.filter(status__in=status_list)
            else:
                # 기존 단일 값 처리
                if status_param == 'active':
                    # 진행중: 마감시간이 지나지 않고 recruiting 또는 bidding 상태인 공구
                    queryset = queryset.filter(
                        end_time__gt=now,
                        status__in=['recruiting', 'bidding']
                    )
                elif status_param == 'ended':
                    # 종료: 마감시간이 지났거나 final_selection/seller_confirmation/completed/cancelled 상태인 공구
                    queryset = queryset.filter(
                        Q(end_time__lte=now) | 
                        Q(status__in=['final_selection', 'seller_confirmation', 'completed', 'cancelled'])
                    )
                elif status_param == 'completed':
                    # 완료: completed 상태이거나 마감시간이 지난 공구
                    queryset = queryset.filter(
                        Q(status='completed') | Q(end_time__lte=now)
                    )
                elif status_param == 'in_progress':
                    # 최종선택 이전 상태(recruiting, bidding)만 필터링
                    queryset = queryset.filter(status__in=['recruiting', 'bidding'])

        # category 필터 처리
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
            
        # 통신사 필터 처리
        if telecom_carrier:
            # GroupBuyTelecomDetail과 조인하여 통신사로 필터링
            queryset = queryset.filter(telecom_detail__telecom_carrier=telecom_carrier)
            
        # 가입유형 필터 처리
        if subscription_type:
            # GroupBuyTelecomDetail과 조인하여 가입유형으로 필터링
            queryset = queryset.filter(telecom_detail__subscription_type=subscription_type)
            
        # 요금제 필터 처리
        if plan_info:
            # GroupBuyTelecomDetail과 조인하여 요금제로 필터링
            queryset = queryset.filter(telecom_detail__plan_info=plan_info)
            
        # 제조사 필터 처리
        if manufacturer:
            # 제조사 이름으로 상품명 필터링
            # 제조사명이 포함된 상품을 찾기
            manufacturer_keywords = {
                '삼성': ['Samsung', 'Galaxy', '갤럭시', '삼성'],
                '애플': ['Apple', 'iPhone', 'iPad', '아이폰', '아이패드', '애플'],
                'LG': ['LG'],
                '샤오미': ['Xiaomi', 'Mi', '샤오미'],
                '구글': ['Google', 'Pixel', '구글', '픽셀'],
                '모토로라': ['Motorola', 'Moto', '모토로라'],
                '원플러스': ['OnePlus', '원플러스']
            }
            
            # 제조사에 해당하는 키워드들로 OR 조건 생성
            if manufacturer in manufacturer_keywords:
                keywords = manufacturer_keywords[manufacturer]
                q_objects = Q()
                for keyword in keywords:
                    q_objects |= Q(product__name__icontains=keyword)
                queryset = queryset.filter(q_objects)
            else:
                # 직접 제조사명으로 검색
                queryset = queryset.filter(product__name__icontains=manufacturer)
        
        # 지역 검색 처리
        if region_search:
            # 지역명으로 검색 (시/도 또는 시/군/구 이름 포함)
            # 1. 전국 비대면 공구는 제외
            # 2. 지역 이름에 검색어가 포함된 공구 필터링
            queryset = queryset.filter(
                Q(regions__region__name__icontains=region_search) |  # GroupBuyRegion을 통해 Region의 name 검색
                Q(region__name__icontains=region_search) |  # 직접 연결된 region의 name 검색
                Q(region_name__icontains=region_search)  # 구 region_name 필드 (호환성)
            ).exclude(region_type='nationwide').distinct()  # 전국 비대면 제외 및 중복 제거
            
        # 정렬 처리 - ordering 파라미터 우선 사용
        if ordering_param:
            # ordering 파라미터가 있으면 그대로 사용
            # 쉼표로 구분된 여러 필드 지원
            ordering_fields = [field.strip() for field in ordering_param.split(',')]
            queryset = queryset.order_by(*ordering_fields)
        elif sort_param == 'popular':
            # 인기순: 참여자 많은 순으로 정렬
            queryset = queryset.order_by('-current_participants', '-start_time')
        else:
            # 최신순 (기본 정렬)
            queryset = queryset.order_by('-start_time')
        
        # 공구 상태 자동 업데이트 (최대 100개까지만 처리)
        for groupbuy in queryset[:100]:
            update_groupbuy_status(groupbuy)

        return queryset
        
    def create(self, request, *args, **kwargs):
        """공구 생성 API"""
        # 디버깅을 위해 요청 데이터 로깅
        print("\n[GroupBuy 생성 요청 데이터]")
        for key, value in request.data.items():
            print(f"{key}: {value}")
        
        # 현재 사용자를 공구 생성자로 자동 지정
        data = request.data.copy()
        data['creator'] = request.user.id
        
        # 현재 시간을 시작 시간으로 자동 설정
        if 'start_time' not in data:
            data['start_time'] = timezone.now().isoformat()
        
        # 초기 상태 설정
        if 'status' not in data:
            data['status'] = 'recruiting'
        
        # 초기 참여자 수 설정
        if 'current_participants' not in data:
            data['current_participants'] = 1  # 생성자가 처음 참여자
        
        # 통신사, 가입유형, 요금제 정보를 product_details에서 추출
        telecom_info = {}
        has_telecom_info = False
        if 'product_details' in data and isinstance(data['product_details'], dict):
            product_details = data['product_details']
            print("\n[GroupBuy 상품 세부 정보]")
            print(product_details)
            
            # 통신사 정보 추출
            if 'telecom_carrier' in product_details and product_details['telecom_carrier']:
                telecom_info['telecom_carrier'] = product_details['telecom_carrier']
                has_telecom_info = True
                print(f"telecom_carrier: {telecom_info['telecom_carrier']}")
            
            # 가입유형 정보 추출
            if 'subscription_type' in product_details and product_details['subscription_type']:
                telecom_info['subscription_type'] = product_details['subscription_type']
                has_telecom_info = True
                print(f"subscription_type: {telecom_info['subscription_type']}")
            
            # 요금제 정보 추출
            if 'telecom_plan' in product_details and product_details['telecom_plan']:
                telecom_info['plan_info'] = product_details['telecom_plan']
                has_telecom_info = True
                print(f"plan_info: {telecom_info['plan_info']}")
                
            # 통신 관련 정보를 product_details에서 제거 (중복 방지)
            clean_product_details = {}
            for key, value in product_details.items():
                if key not in ['telecom_carrier', 'telecom_plan', 'subscription_type'] and value:
                    clean_product_details[key] = value
            
            # 기타 세부 정보만 product_details에 유지
            if clean_product_details:
                data['product_details'] = clean_product_details
            else:
                # 통신 관련 정보만 있었다면 product_details는 비운 상태로 유지
                data['product_details'] = None
                
        # 디버깅 정보 출력
        print(f"\n[통신 정보 확인] has_telecom_info: {has_telecom_info}")
        if telecom_info:
            for key, value in telecom_info.items():
                print(f"{key}: {value}")
            
        # 통신 정보는 GroupBuyTelecomDetail 모델에 저장하기 위해 임시 저장
        
        
        # 중복 공구 확인 - 통신사/가입유형/요금제 정보가 있는 경우 중복 허용
        product_id = data.get('product')
        creator_id = data.get('creator')
        
        # 동일한 상품으로 이미 생성된 공구가 있는지 확인 (같은 생성자가 만든 경우만)
        existing_groupbuy = GroupBuy.objects.filter(
            product_id=product_id,
            creator_id=creator_id,
            status__in=['recruiting', 'bidding', 'seller_confirmation'] # 진행 중인 공구만 체크
        ).first()
        
        # 통신 제품인 경우 통신사/가입유형/요금제 정보가 다르면 중복 허용
        if existing_groupbuy:
            if not has_telecom_info:
                # 통신 정보가 없는 경우 중복 공구 생성 불가
                error_msg = {
                    'product': [
                        '이미 해당 상품으로 진행 중인 공동구매가 있습니다. 기존 공구가 완료된 후 새로운 공구를 생성해주세요.'
                    ]
                }
                return Response(error_msg, status=status.HTTP_400_BAD_REQUEST)
            else:
                # 통신 정보가 있는 경우, 기존 공구의 통신 정보와 비교
                from .models import GroupBuyTelecomDetail
                existing_telecom_detail = GroupBuyTelecomDetail.objects.filter(groupbuy=existing_groupbuy).first()
                
                # 기존 공구에 통신 정보가 없거나, 통신 정보가 같은 경우 중복 생성 불가
                if not existing_telecom_detail:
                    # 기존 공구에 통신 정보가 없는 경우
                    pass  # 통신 정보가 다르므로 생성 허용
                elif (existing_telecom_detail.telecom_carrier == telecom_info.get('telecom_carrier', '') and
                      existing_telecom_detail.subscription_type == telecom_info.get('subscription_type', '') and
                      existing_telecom_detail.plan_info == telecom_info.get('plan_info', '')):
                    # 통신 정보가 같은 경우 중복 생성 불가
                    error_msg = {
                        'product': [
                            '이미 해당 상품으로 진행 중인 공동구매가 있습니다. 기존 공구가 완료된 후 새로운 공구를 생성해주세요.'
                        ]
                    }
                    return Response(error_msg, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=data)
        
        try:
            serializer.is_valid(raise_exception=True)
            groupbuy = serializer.save()
            
            # 통신 정보가 있는 경우 GroupBuyTelecomDetail 모델 생성
            if has_telecom_info and telecom_info:
                from .models import GroupBuyTelecomDetail
                
                # 필수 필드 확인 및 기본값 설정
                if 'telecom_carrier' not in telecom_info:
                    telecom_info['telecom_carrier'] = 'SKT'  # 기본값
                
                if 'subscription_type' not in telecom_info:
                    telecom_info['subscription_type'] = 'new'  # 기본값
                
                if 'plan_info' not in telecom_info:
                    telecom_info['plan_info'] = '5만원대'  # 기본값
                
                # 요금제 정보 변환 (5G_premium -> 7만원대)
                if 'plan_info' in telecom_info:
                    plan_info = telecom_info['plan_info']
                    if plan_info == '5G_basic' or plan_info == '3만원대':
                        telecom_info['plan_info'] = '3만원대'
                    elif plan_info == '5G_standard' or plan_info == '5만원대':
                        telecom_info['plan_info'] = '5만원대'
                    elif plan_info == '5G_premium' or plan_info == '7만원대':
                        telecom_info['plan_info'] = '7만원대'
                    elif plan_info == '5G_special' or plan_info == '9만원대':
                        telecom_info['plan_info'] = '9만원대'
                    elif plan_info == '5G_platinum' or plan_info == '10만원대':
                        telecom_info['plan_info'] = '10만원대'
                
                # 약정기간은 항상 24개월로 고정
                contract_period = '24개월'
                
                # GroupBuyTelecomDetail 모델 생성
                GroupBuyTelecomDetail.objects.create(
                    groupbuy=groupbuy,
                    telecom_carrier=telecom_info['telecom_carrier'],
                    subscription_type=telecom_info['subscription_type'],
                    plan_info=telecom_info['plan_info'],
                    contract_period=contract_period
                )
                
                print(f"\n[GroupBuyTelecomDetail 생성 완료] groupbuy_id: {groupbuy.id}")
            
            # 다중 지역 처리 - regions 필드가 있는 경우 GroupBuyRegion 모델에 저장
            if 'regions' in request.data and isinstance(request.data['regions'], list) and request.data['regions']:
                from .models import GroupBuyRegion, Region
                
                print(f"\n[다중 지역 처리 시작] regions 데이터: {request.data['regions']}")
                
                # 최대 3개 지역으로 제한
                regions_data = request.data['regions'][:3]
                
                for idx, region_data in enumerate(regions_data):
                    print(f"\n[지역 {idx+1}] 처리 중: {region_data}")
                    
                    # 지역 코드로 Region 객체 찾기
                    region_code = region_data.get('code')
                    region_name = region_data.get('name')
                    region = None
                    
                    if region_code:
                        # 1. 먼저 정확한 코드로 검색
                        region = Region.objects.filter(code=region_code).first()
                        if region:
                            print(f"[지역 검색 성공 - 코드 매칭] {region.name} (코드: {region.code})")
                        else:
                            # 2. 코드가 시도_시군구 형식인 경우 처리
                            if '_' in region_code:
                                parts = region_code.split('_', 1)
                                if len(parts) == 2:
                                    sido = parts[0]
                                    sigungu = parts[1]
                                    # 시도명과 시군구명으로 지역 검색
                                    # 먼저 정확한 이름으로 검색
                                    region = Region.objects.filter(
                                        name=sigungu,
                                        full_name__contains=sido,
                                        level__in=[1, 2]  # 시군구 레벨 (1 또는 2)
                                    ).first()
                                    
                                    # 못 찾으면 부분 매칭으로 재시도
                                    if not region:
                                        region = Region.objects.filter(
                                            Q(full_name__contains=sido) & Q(full_name__contains=sigungu),
                                            level__in=[1, 2]  # 시군구 레벨 (1 또는 2)
                                        ).first()
                                    if region:
                                        print(f"[지역 검색 성공 - 이름 매칭] 시도: {sido}, 시군구: {sigungu} -> {region.name}")
                                    else:
                                        print(f"[지역 검색 실패] 시도: {sido}, 시군구: {sigungu}")
                                        # 디버깅을 위해 해당 지역명이 DB에 있는지 확인
                                        similar_regions = Region.objects.filter(
                                            Q(name__icontains=sigungu) | Q(full_name__icontains=sigungu),
                                            level__in=[1, 2]
                                        )[:5]
                                        if similar_regions:
                                            print(f"  유사한 지역 목록:")
                                            for r in similar_regions:
                                                print(f"    - {r.name} (full: {r.full_name}, code: {r.code})")
                            else:
                                print(f"[지역 검색 실패] 코드 {region_code}에 해당하는 지역을 찾을 수 없습니다.")
                    
                    # 3. 이름으로 검색 시도 (코드로 찾지 못한 경우)
                    if not region and region_name:
                        # 시군구 레벨에서 이름으로 검색
                        region = Region.objects.filter(name=region_name, level__in=[1, 2]).first()
                        if region:
                            print(f"[지역 검색 성공 - 이름으로 검색] {region.name} (코드: {region.code})")
                        else:
                            print(f"[지역 검색 실패] 이름 {region_name}에 해당하는 지역을 찾을 수 없습니다.")
                    
                    if region:
                        # GroupBuyRegion 생성
                        GroupBuyRegion.objects.create(
                            groupbuy=groupbuy,
                            region=region
                        )
                        print(f"[지역 추가 완료] {region.name} (코드: {region.code})")
                    else:
                        print(f"[지역 추가 실패] region_data: {region_data}")
                
                # 첫 번째 지역을 기존 region 필드에 저장 (하위 호환성)
                if regions_data and len(regions_data) > 0:
                    first_region_code = regions_data[0].get('code')
                    if first_region_code:
                        first_region = Region.objects.filter(code=first_region_code).first()
                        if first_region:
                            groupbuy.region = first_region
                            groupbuy.region_name = first_region.name
                            groupbuy.save()
                            print(f"[기본 지역 설정] {first_region.name}")
                
                print(f"\n[다중 지역 처리 완료] 총 {GroupBuyRegion.objects.filter(groupbuy=groupbuy).count()}개 지역 저장됨")
            
            # 생성자를 참여자로 자동 추가 (리더로 설정)
            Participation.objects.create(
                user=request.user,
                groupbuy=groupbuy,
                is_leader=True
            )
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except serializers.ValidationError as e:
            print("\n[GroupBuy 생성 유효성 검사 오류]")
            print(e.detail)
            
            # 중복 공구 제약 오류인 경우 더 상세한 오류 메시지 제공
            if 'non_field_errors' in e.detail and any('unique' in str(err).lower() for err in e.detail['non_field_errors']):
                error_msg = {
                    'non_field_errors': [
                        '이미 동일한 상품으로 생성한 공구가 있습니다. '
                        '통신사, 가입유형, 요금제 정보를 입력하여 다른 공구로 등록해주세요.'
                    ]
                }
                return Response(error_msg, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False)
    def popular(self, request):
        # 최종선택 이전 상태(recruiting, bidding)인 공구만 필터링
        popular_groupbuys = GroupBuy.objects.annotate(
            curent_participants=Count('participation')
        ).filter(
            end_time__gt=timezone.now(),
            status__in=['recruiting', 'bidding']  # 최종선택 이전 상태만
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

    def update(self, request, *args, **kwargs):
        """공구 정보 업데이트 메서드 - 다중 지역 처리 포함"""
        print(f"\n[GroupBuy Update] Received data: {request.data}")
        print(f"[GroupBuy Update] Request user: {request.user}")
        
        instance = self.get_object()
        print(f"[GroupBuy Update] Instance: {instance.id}, Creator: {instance.creator}")
        
        # Check if user is the creator
        if instance.creator != request.user:
            return Response(
                {'error': '본인이 작성한 공구만 수정할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Remove creator field from update data if present
        data = request.data.copy()
        if 'creator' in data:
            data.pop('creator')
        
        serializer = self.get_serializer(instance, data=data, partial=True)
        
        if not serializer.is_valid():
            print(f"[GroupBuy Update] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.is_valid(raise_exception=True)
        groupbuy = serializer.save()
        
        # 통신 정보가 있는 경우 GroupBuyTelecomDetail 모델 업데이트
        if 'product_details' in request.data and isinstance(request.data['product_details'], dict):
            telecom_info = request.data['product_details']
            has_telecom_info = any(key in telecom_info for key in ['telecom_carrier', 'subscription_type', 'plan_info', 'telecom_plan'])
            
            if has_telecom_info:
                from .models import GroupBuyTelecomDetail
                
                # 기존 통신 정보 가져오기
                telecom_detail = GroupBuyTelecomDetail.objects.filter(groupbuy=groupbuy).first()
                
                # 필수 필드 확인 및 기본값 설정
                if 'telecom_carrier' not in telecom_info:
                    telecom_info['telecom_carrier'] = 'SKT'  # 기본값
                
                if 'subscription_type' not in telecom_info:
                    telecom_info['subscription_type'] = 'new'  # 기본값
                
                # plan_info 또는 telecom_plan 중 하나를 사용
                plan_info = telecom_info.get('plan_info') or telecom_info.get('telecom_plan', '5만원대')
                
                # 요금제 정보 변환 (5G_premium -> 7만원대)
                if plan_info == '5G_basic' or plan_info == '3만원대':
                    plan_info = '3만원대'
                elif plan_info == '5G_standard' or plan_info == '5만원대':
                    plan_info = '5만원대'
                elif plan_info == '5G_premium' or plan_info == '7만원대':
                    plan_info = '7만원대'
                elif plan_info == '5G_special' or plan_info == '9만원대':
                    plan_info = '9만원대'
                elif plan_info == '5G_platinum' or plan_info == '10만원대':
                    plan_info = '10만원대'
                
                # 약정기간은 항상 24개월로 고정
                contract_period = '24개월'
                
                if telecom_detail:
                    # 기존 정보 업데이트
                    telecom_detail.telecom_carrier = telecom_info['telecom_carrier']
                    telecom_detail.subscription_type = telecom_info['subscription_type']
                    telecom_detail.plan_info = plan_info
                    telecom_detail.contract_period = contract_period
                    telecom_detail.save()
                    print(f"[GroupBuyTelecomDetail 업데이트 완료] groupbuy_id: {groupbuy.id}")
                else:
                    # 새로 생성
                    GroupBuyTelecomDetail.objects.create(
                        groupbuy=groupbuy,
                        telecom_carrier=telecom_info['telecom_carrier'],
                        subscription_type=telecom_info['subscription_type'],
                        plan_info=plan_info,
                        contract_period=contract_period
                    )
                    print(f"[GroupBuyTelecomDetail 생성 완료] groupbuy_id: {groupbuy.id}")
        
        # 다중 지역 처리 - regions 필드가 있는 경우 GroupBuyRegion 모델에 저장
        if 'regions' in request.data and isinstance(request.data['regions'], list) and request.data['regions']:
            from .models import GroupBuyRegion, Region
            
            print(f"\n[업데이트 - 다중 지역 처리 시작] regions 데이터: {request.data['regions']}")
            
            # 기존 지역 정보 삭제
            deleted_count = GroupBuyRegion.objects.filter(groupbuy=groupbuy).delete()[0]
            print(f"[기존 지역 삭제] {deleted_count}개 지역 삭제됨")
            
            # 최대 3개 지역으로 제한
            regions_data = request.data['regions'][:3]
            
            for idx, region_data in enumerate(regions_data):
                print(f"\n[지역 {idx+1}] 처리 중: {region_data}")
                
                # 지역 코드로 Region 객체 찾기
                region_code = region_data.get('code')
                region_name = region_data.get('name')
                region = None
                
                if region_code:
                    # 1. 먼저 정확한 코드로 검색
                    region = Region.objects.filter(code=region_code).first()
                    if region:
                        print(f"[지역 검색 성공 - 코드 매칭] {region.name} (코드: {region.code})")
                    else:
                        # 2. 코드가 시도_시군구 형식인 경우 처리
                        if '_' in region_code:
                            parts = region_code.split('_', 1)
                            if len(parts) == 2:
                                sido = parts[0]
                                sigungu = parts[1]
                                # 시도명과 시군구명으로 지역 검색
                                region = Region.objects.filter(
                                    Q(full_name__contains=sido) & Q(full_name__contains=sigungu),
                                    level__in=[1, 2]  # 시군구 레벨 (1 또는 2)
                                ).first()
                                if region:
                                    print(f"[지역 검색 성공 - 이름 매칭] 시도: {sido}, 시군구: {sigungu} -> {region.name}")
                                else:
                                    print(f"[지역 검색 실패] 시도: {sido}, 시군구: {sigungu}")
                        else:
                            print(f"[지역 검색 실패] 코드 {region_code}에 해당하는 지역을 찾을 수 없습니다.")
                
                # 3. 이름으로 검색 시도 (코드로 찾지 못한 경우)
                if not region and region_name:
                    # 시군구 레벨에서 이름으로 검색
                    region = Region.objects.filter(name=region_name, level__in=[1, 2]).first()
                    if region:
                        print(f"[지역 검색 성공 - 이름으로 검색] {region.name} (코드: {region.code})")
                    else:
                        print(f"[지역 검색 실패] 이름 {region_name}에 해당하는 지역을 찾을 수 없습니다.")
                
                if region:
                    # GroupBuyRegion 생성
                    GroupBuyRegion.objects.create(
                        groupbuy=groupbuy,
                        region=region
                    )
                    print(f"[지역 추가 완료] {region.name} (코드: {region.code})")
                else:
                    print(f"[지역 추가 실패] region_data: {region_data}")
            
            # 첫 번째 지역을 기존 region 필드에 저장 (하위 호환성)
            if regions_data and len(regions_data) > 0:
                first_region_code = regions_data[0].get('code')
                if first_region_code:
                    first_region = Region.objects.filter(code=first_region_code).first()
                    if first_region:
                        groupbuy.region = first_region
                        groupbuy.region_name = first_region.name
                        groupbuy.save()
                        print(f"[기본 지역 설정] {first_region.name}")
            
            print(f"\n[업데이트 - 다중 지역 처리 완료] 총 {GroupBuyRegion.objects.filter(groupbuy=groupbuy).count()}개 지역 저장됨")
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'popular', 'recent', 'bids', 'winning_bid']:
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
        
        # 입찰 정보 추가 (최종선택중인 경우)
        if instance.status in ['final_selection', 'seller_confirmation', 'completed']:
            from api.models import Bid
            # 낙찰된 입찰 정보
            winning_bid = instance.bid_set.filter(is_selected=True).first()
            if winning_bid:
                # 사용자가 참여자이거나 낙찰된 판매자인 경우에만 실제 금액 표시
                user = request.user
                is_participant = False
                is_winning_seller = False
                
                # 인증된 사용자인 경우에만 참여자/판매자 확인
                if user.is_authenticated:
                    is_participant = instance.participation_set.filter(user=user).exists()
                    is_winning_seller = winning_bid.seller == user
                
                if is_participant or is_winning_seller:
                    data['winning_bid_amount'] = winning_bid.amount
                else:
                    # 미참여자는 마스킹 처리
                    amount_str = str(winning_bid.amount)
                    if len(amount_str) > 3:
                        masked_amount = amount_str[0] + '*' * (len(amount_str) - 3) + '원'
                    else:
                        masked_amount = '***원'
                    data['winning_bid_amount_masked'] = masked_amount
                    data['winning_bid_amount'] = None
                
                # 전체 입찰 수
                total_bids = instance.bid_set.count()
                data['total_bids_count'] = total_bids
                
                # 입찰 내역 (상위 10개)
                top_bids = instance.bid_set.order_by('-amount')[:10]
                bid_list = []
                for idx, bid in enumerate(top_bids, 1):
                    if is_participant or is_winning_seller:
                        bid_list.append({
                            'rank': idx,
                            'amount': bid.amount,
                            'is_winner': bid.status == 'selected'
                        })
                    else:
                        # 미참여자는 1위만 마스킹된 금액 표시
                        if idx == 1:
                            amount_str = str(bid.amount)
                            if len(amount_str) > 3:
                                masked_amount = amount_str[0] + '*' * (len(amount_str) - 3)
                            else:
                                masked_amount = '***'
                            bid_list.append({
                                'rank': idx,
                                'amount_masked': masked_amount + '원',
                                'is_winner': bid.status == 'selected'
                            })
                data['bid_ranking'] = bid_list
        
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
        """참여중인 공구 목록 조회
        
        구매자: recruiting, bidding 상태의 참여 공구 (final_selection, completed, cancelled 제외)
        판매자: 사용하지 않음
        """
        user = request.user
        
        if user.role == 'buyer':
            # 참여중인 공구: recruiting, bidding 상태만 
            # final_selection, seller_confirmation, completed, cancelled 제외
            joined = self.get_queryset().filter(
                participants=user,
                status__in=['recruiting', 'bidding']
            ).distinct()
        else:
            joined = self.get_queryset().none()
            
        serializer = self.get_serializer(joined, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def pending_selection(self, request):
        """최종 선택 대기중인 공구 목록 조회
        
        구매자: 참여한 공구 중 final_selection_buyers 상태인 공구 (선택 여부 무관)
        판매자: 낙찰된 공구 중 final_selection_seller 상태이면서 최종선택하지 않은 공구
        """
        user = request.user
        
        if user.role == 'buyer':
            # 구매자가 참여한 공구 중 final_selection_buyers 상태인 모든 공구
            # 선택 여부와 관계없이 12시간 동안 이 카테고리에 유지
            pending = self.get_queryset().filter(
                participants=user,
                status='final_selection_buyers'
            ).distinct()
        elif user.role == 'seller':
            # 판매자가 낙찰된 공구 중 final_selection_seller 상태인 공구
            pending = self.get_queryset().filter(
                bid__seller=user,
                bid__status='selected',  # is_selected 대신 status='selected' 사용
                bid__final_decision='pending',
                status='final_selection_seller'
            ).distinct()
        else:
            pending = self.get_queryset().none()
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def purchase_confirmed(self, request):
        """거래중인 공구 목록 조회
        
        구매자가 구매확정하고 판매자도 판매확정한 공구 (거래중 상태)
        """
        user = request.user
        
        if user.role == 'buyer':
            # 구매자가 구매확정한 공구 중 completed 상태이면서 
            # 낙찰된 판매자가 판매확정한 공구
            from .models import Bid
            confirmed = self.get_queryset().filter(
                participants=user,
                participation__user=user,
                participation__final_decision='confirmed',
                status='completed',
                bid__status='accepted',
                bid__seller_final_decision='confirmed'
            ).distinct()
        else:
            confirmed = self.get_queryset().none()
        
        serializer = self.get_serializer(confirmed, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def waiting_seller_decision(self, request):
        """판매자 최종선택 대기중인 공구 목록 조회
        
        구매자가 구매확정한 공구 중 판매자가 아직 결정하지 않은 공구
        """
        user = request.user
        
        if user.role == 'buyer':
            # 구매자가 구매확정한 공구 중 final_selection_seller 상태인 공구
            waiting = self.get_queryset().filter(
                participants=user,
                participation__user=user,
                participation__final_decision='confirmed',
                status='final_selection_seller'
            ).distinct()
        else:
            waiting = self.get_queryset().none()
        
        serializer = self.get_serializer(waiting, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def purchase_completed(self, request):
        """구매 완료된 공구 목록 조회
        
        사용자가 참여한 공구 중 completed 상태인 공구 목록 반환
        """
        user = request.user
        
        if user.role == 'buyer':
            completed = self.get_queryset().filter(
                participants=user,
                status='completed'
            ).distinct()
        else:
            completed = self.get_queryset().none()
        
        serializer = self.get_serializer(completed, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def cancelled_groupbuys(self, request):
        """취소된 공구 목록 조회
        
        구매자: 참여했던 공구 중 취소된 공구
        판매자: 입찰했던 공구 중 취소된 공구
        """
        user = request.user
        
        if user.role == 'buyer':
            # 구매자가 참여했던 공구 중 취소된 공구 (삭제 처리된 것 제외)
            # 1. 최종선택에서 포기를 선택한 경우
            cancelled_by_choice = self.get_queryset().filter(
                participation__user=user,
                participation__final_decision='cancelled',
                participation__is_deleted_by_user=False,  # 삭제된 것 제외
                status__in=['cancelled', 'final_selection']
            )
            
            # 2. 최종선택 기간 만료로 취소된 경우
            from django.db.models import Q
            from django.utils import timezone
            now = timezone.now()
            expired_final_selection = self.get_queryset().filter(
                participation__user=user,
                participation__final_decision='pending',
                participation__is_deleted_by_user=False,  # 삭제된 것 제외
                status='cancelled',
                final_selection_end__lt=now
            )
            
            # 3. 전반적으로 취소된 공구
            general_cancelled = self.get_queryset().filter(
                participation__user=user,
                participation__is_deleted_by_user=False,  # 삭제된 것 제외
                status='cancelled'
            )
            
            # 합치고 중복 제거
            cancelled = (cancelled_by_choice | expired_final_selection | general_cancelled).distinct()
            
            # 취소 사유 추가
            result = []
            for gb in cancelled:
                data = self.get_serializer(gb).data
                participation = gb.participation_set.filter(user=user).first()
                
                if participation and participation.final_decision == 'cancelled':
                    data['cancel_reason'] = '구매 포기'
                elif gb.status == 'cancelled' and gb.final_selection_end and gb.final_selection_end < now:
                    data['cancel_reason'] = '최종선택 기간 만료'
                elif gb.status == 'cancelled':
                    # 낙찰자 포기 여부 확인
                    selected_bid = gb.bid_set.filter(status='selected', final_decision='cancelled').first()
                    if selected_bid:
                        data['cancel_reason'] = '낙찰자의 판매포기로 인한 공구 진행 취소'
                    else:
                        data['cancel_reason'] = '공구 취소'
                        
                result.append(data)
                
        elif user.role == 'seller':
            # 판매자가 입찰했던 공구 중 취소된 공구 (삭제 처리된 것 제외)
            from .models import Bid
            from django.utils import timezone
            now = timezone.now()
            
            # 1. 판매 포기한 경우
            cancelled_by_choice = self.get_queryset().filter(
                bid__seller=user,
                bid__final_decision='cancelled',
                bid__is_deleted_by_user=False,  # 삭제된 것 제외
                status__in=['cancelled', 'final_selection']
            )
            
            # 2. 최종선택 기간 만료로 취소된 경우
            expired_final_selection = self.get_queryset().filter(
                bid__seller=user,
                bid__is_selected=True,
                bid__final_decision='pending',
                bid__is_deleted_by_user=False,  # 삭제된 것 제외
                status='cancelled',
                final_selection_end__lt=now
            )
            
            # 3. 전반적으로 취소된 공구
            general_cancelled = self.get_queryset().filter(
                bid__seller=user,
                bid__is_deleted_by_user=False,  # 삭제된 것 제외
                status='cancelled'
            )
            
            # 합치고 중복 제거
            cancelled = (cancelled_by_choice | expired_final_selection | general_cancelled).distinct()
            
            # 취소 사유 추가
            result = []
            for gb in cancelled:
                data = self.get_serializer(gb).data
                bid = gb.bid_set.filter(seller=user).first()
                
                if bid and bid.final_decision == 'cancelled':
                    data['cancel_reason'] = '판매 포기'
                elif gb.status == 'cancelled' and gb.final_selection_end and gb.final_selection_end < now:
                    data['cancel_reason'] = '최종선택 기간 만료'
                elif gb.status == 'cancelled':
                    # 구매자 전원 포기 여부 확인
                    total_participants = gb.participation_set.count()
                    cancelled_participants = gb.participation_set.filter(final_decision='cancelled').count()
                    if total_participants > 0 and total_participants == cancelled_participants:
                        data['cancel_reason'] = '구매자 전원 구매포기로 인한 공구 진행 취소'
                    else:
                        data['cancel_reason'] = '공구 취소'
                        
                result.append(data)
        else:
            result = []
        
        return Response(result)
    
    @action(detail=True, methods=['delete'])
    def delete_cancelled(self, request, pk=None):
        """취소된 공구 삭제 (사용자의 리스트에서만 제거)"""
        groupbuy = self.get_object()
        user = request.user
        
        # 공구가 취소 상태인지 확인
        if groupbuy.status != 'cancelled':
            return Response(
                {'error': '취소된 공구만 삭제할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 구매자인 경우: 참여 기록에서 is_deleted 플래그 설정
        if user.role == 'buyer':
            participation = Participation.objects.filter(
                user=user,
                groupbuy=groupbuy
            ).first()
            
            if participation:
                # 실제 삭제가 아닌 플래그 설정 (나중에 기록 추적 가능)
                participation.is_deleted_by_user = True
                participation.save()
                return Response({'message': '취소된 공구가 목록에서 제거되었습니다.'})
            else:
                return Response(
                    {'error': '해당 공구에 참여한 기록이 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # 판매자인 경우: 입찰 기록에서 is_deleted 플래그 설정
        elif user.role == 'seller':
            bid = Bid.objects.filter(
                seller=user,
                groupbuy=groupbuy
            ).first()
            
            if bid:
                # 실제 삭제가 아닌 플래그 설정
                bid.is_deleted_by_user = True
                bid.save()
                return Response({'message': '취소된 공구가 목록에서 제거되었습니다.'})
            else:
                return Response(
                    {'error': '해당 공구에 입찰한 기록이 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(
            {'error': '권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
        
    # 판매자용 API 엔드포인트들
    @action(detail=False, methods=['get'])
    def seller_bids(self, request):
        """판매자의 입찰 내역 조회"""
        if request.user.role != 'seller':
            return Response({'error': '판매자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        # 판매자가 입찰한 모든 공구 조회 (취소된 공구 제외)
        from .models import Bid
        bids = Bid.objects.filter(
            seller=request.user,
            is_deleted_by_user=False
        ).select_related('groupbuy')
        
        groupbuy_data = []
        for bid in bids:
            gb_data = self.get_serializer(bid.groupbuy).data
            gb_data['my_bid_amount'] = bid.amount
            gb_data['bid_status'] = bid.status
            gb_data['is_selected'] = bid.is_selected
            groupbuy_data.append(gb_data)
        
        return Response(groupbuy_data)
    
    @action(detail=False, methods=['get'])
    def seller_waiting_buyer(self, request):
        """판매자의 구매자 최종선택 대기중인 공구 조회"""
        if request.user.role != 'seller':
            return Response({'error': '판매자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        # 낙찰되었지만 구매자들이 아직 선택중인 공구
        waiting = self.get_queryset().filter(
            bid__seller=request.user,
            bid__is_selected=True,
            status='final_selection_buyers'
        ).distinct()
        
        data = []
        for gb in waiting:
            gb_data = self.get_serializer(gb).data
            # 구매자 선택 마감 시간 추가
            if gb.final_selection_end:
                gb_data['buyer_selection_end_time'] = gb.final_selection_end
            data.append(gb_data)
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def seller_pending_decision(self, request):
        """판매자의 판매확정/포기 선택 대기중인 공구 조회"""
        if request.user.role != 'seller':
            return Response({'error': '판매자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        # 구매자 선택이 끝나고 판매자가 결정해야 하는 공구
        from .models import Bid, Participation
        pending = self.get_queryset().filter(
            bid__seller=request.user,
            bid__is_selected=True,
            bid__seller_final_decision='pending',
            status='final_selection_seller'
        ).distinct()
        
        data = []
        for gb in pending:
            gb_data = self.get_serializer(gb).data
            # 구매확정 인원 수 계산
            confirmed_count = Participation.objects.filter(
                groupbuy=gb,
                final_decision='confirmed'
            ).count()
            gb_data['confirmed_buyers'] = confirmed_count
            # 판매자 선택 마감 시간 추가
            if gb.seller_selection_end:
                gb_data['seller_selection_end_time'] = gb.seller_selection_end
            data.append(gb_data)
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def seller_trading(self, request):
        """판매자의 거래중인 공구 조회"""
        if request.user.role != 'seller':
            return Response({'error': '판매자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        # 구매확정 + 판매확정 완료되어 거래중인 공구
        from .models import Participation
        trading = self.get_queryset().filter(
            bid__seller=request.user,
            bid__is_selected=True,
            bid__seller_final_decision='confirmed',
            status='completed'
        ).distinct()
        
        data = []
        for gb in trading:
            gb_data = self.get_serializer(gb).data
            # 구매확정 인원 수
            confirmed_count = Participation.objects.filter(
                groupbuy=gb,
                final_decision='confirmed'
            ).count()
            gb_data['confirmed_buyers'] = confirmed_count
            data.append(gb_data)
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def seller_completed(self, request):
        """판매자의 판매완료된 공구 조회"""
        if request.user.role != 'seller':
            return Response({'error': '판매자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        # 판매완료 처리된 공구
        from .models import Bid, Participation
        completed = self.get_queryset().filter(
            bid__seller=request.user,
            bid__is_selected=True,
            bid__is_sale_completed=True,
            status='completed'
        ).distinct()
        
        data = []
        for gb in completed:
            gb_data = self.get_serializer(gb).data
            # 구매확정 인원 수
            confirmed_count = Participation.objects.filter(
                groupbuy=gb,
                final_decision='confirmed'
            ).count()
            gb_data['confirmed_buyers'] = confirmed_count
            # 판매완료 시간
            bid = Bid.objects.filter(
                groupbuy=gb,
                seller=request.user,
                is_selected=True
            ).first()
            if bid and bid.sale_completed_at:
                gb_data['completed_at'] = bid.sale_completed_at
            data.append(gb_data)
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def seller_cancelled(self, request):
        """판매자의 취소된 공구 조회"""
        if request.user.role != 'seller':
            return Response({'error': '판매자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        # 취소된 공구 (삭제 처리된 것 제외)
        from .models import Bid
        cancelled_bids = Bid.objects.filter(
            seller=request.user,
            is_deleted_by_user=False,
            groupbuy__status='cancelled'
        ).select_related('groupbuy')
        
        data = []
        for bid in cancelled_bids:
            gb_data = self.get_serializer(bid.groupbuy).data
            gb_data['my_bid_amount'] = bid.amount
            
            # 취소 사유 추가
            if bid.seller_final_decision == 'cancelled':
                gb_data['cancel_reason'] = '판매 포기'
            elif bid.is_selected and bid.seller_final_decision == 'pending':
                gb_data['cancel_reason'] = '최종선택 기간 만료'
            else:
                gb_data['cancel_reason'] = '공구 취소'
            
            data.append(gb_data)
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def seller_final_selection(self, request):
        """판매자의 최종선택 대기중인 공구 조회"""
        if request.user.role != 'seller':
            return Response({'error': '판매자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        # 판매자가 낙찰된 공구 중 final_selection 상태이면서 최종선택하지 않은 공구
        pending = self.get_queryset().filter(
            bid__seller=request.user,
            bid__is_selected=True,
            bid__final_decision='pending',
            status='final_selection'
        ).distinct()
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def seller_confirmed(self, request):
        """판매자가 판매확정한 공구 조회"""
        if request.user.role != 'seller':
            return Response({'error': '판매자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        # 판매자가 판매확정한 공구
        confirmed = self.get_queryset().filter(
            bid__seller=request.user,
            bid__status='selected',  # is_selected 대신 status='selected' 사용
            bid__final_decision='confirmed',
            status__in=['final_selection_seller', 'completed']  # 새로운 상태에 맞게 수정
        ).distinct()
        
        serializer = self.get_serializer(confirmed, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def seller_completed(self, request):
        """판매자의 판매완료된 공구 조회"""
        if request.user.role != 'seller':
            return Response({'error': '판매자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        # 판매자가 참여한 completed 상태의 공구
        completed = self.get_queryset().filter(
            bid__seller=request.user,
            bid__is_selected=True,
            status='completed'
        ).distinct()
        
        serializer = self.get_serializer(completed, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """사용자가 공구에 참여하는 API"""
        from django.db import transaction, IntegrityError
        from django.core.exceptions import ValidationError
        
        groupbuy = self.get_object()
        user = request.user
        
        # 닉네임 정보 확인 및 업데이트
        username = request.data.get('username')
        if username and username.strip():
            # 닉네임이 제공되었으면 사용자 정보 업데이트
            user.username = username
            user.save(update_fields=['username'])
            logger.info(f"사용자({user.id}) 닉네임이 '{username}'으로 업데이트되었습니다.")
        
        # 이미 참여 중인지 확인
        if Participation.objects.filter(user=user, groupbuy=groupbuy).exists():
            return Response(
                {'error': '이미 참여 중인 공구입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 동일 상품의 다른 공구에 참여 중인지 확인
        if Participation.objects.filter(
            user=user,
            groupbuy__product=groupbuy.product,
            groupbuy__status__in=['recruiting', 'bidding']
        ).exists():
            return Response(
                {'error': '이미 동일한 상품의 다른 공구에 참여중입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 공구 상태 확인 - recruiting 또는 bidding 상태에서만 참여 가능
        now = timezone.now()
        if groupbuy.status not in ['recruiting', 'bidding'] or now > groupbuy.end_time:
            return Response(
                {'error': '참여할 수 없는 공구입니다. 모집이 종료되었거나 마감되었습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최대 참여자 수 확인 (최신 데이터로 다시 확인)
        groupbuy.refresh_from_db()
        if groupbuy.current_participants >= groupbuy.max_participants:
            return Response(
                {'error': '최대 참여자 수에 도달했습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 트랜잭션으로 참여 생성 및 참여자 수 업데이트를 원자적으로 처리
            with transaction.atomic():
                # 참여 생성
                participation = Participation.objects.create(
                    user=user,
                    groupbuy=groupbuy,
                    is_leader=False  # 일반 참여자
                )
                
                # 현재 참여자 수 증가 (F 표현식 사용하여 race condition 방지)
                GroupBuy.objects.filter(pk=groupbuy.id).update(
                    current_participants=F('current_participants') + 1
                )
                
                # 최신 데이터로 갱신
                groupbuy.refresh_from_db()
                
            return Response({
                'id': participation.id,
                'user_id': user.id,
                'groupbuy_id': groupbuy.id,
                'joined_at': participation.joined_at,
                'current_participants': groupbuy.current_participants,
                'message': '공구 참여가 완료되었습니다.'
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            return Response(
                {'error': '참여 처리 중 오류가 발생했습니다. 이미 참여 중일 수 있습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"공구 참여 중 오류 발생: {str(e)}")
            return Response(
                {'error': '참여 처리 중 오류가 발생했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    # vote 메서드는 voting 상태를 제거하면서 삭제됨
    # 최종선택은 final_selection 상태에서 처리됨
    
    @action(detail=True, methods=['get'])
    def contact_info(self, request, pk=None):
        """구매/판매 확정 후 상대방 연락처 정보 조회"""
        groupbuy = self.get_object()
        user = request.user
        
        # 공구 상태 확인
        if groupbuy.status not in ['final_selection', 'completed']:
            return Response(
                {'error': '연락처 정보는 최종선택 또는 완료 상태에서만 조회 가능합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 구매자인 경우 - 구매 확정했는지 확인
        participation = groupbuy.participation_set.filter(user=user).first()
        if participation and participation.final_decision == 'confirmed':
            # 낙찰된 판매자 정보 제공
            winning_bid = groupbuy.bid_set.filter(status='selected').first()
            if winning_bid and winning_bid.final_decision == 'confirmed':
                seller = winning_bid.seller
                return Response({
                    'role': 'buyer',
                    'contact_info': {
                        'name': seller.username,
                        'business_name': getattr(seller, 'business_name', ''),
                        'phone': seller.phone_number if seller.phone_number else '미등록',
                        'email': seller.email,
                        'profile_image': seller.profile_image
                    }
                })
            else:
                return Response(
                    {'error': '판매자가 아직 판매를 확정하지 않았습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 판매자인 경우 - 판매 확정했는지 확인
        winning_bid = groupbuy.bid_set.filter(seller=user, status='selected').first()
        if winning_bid and winning_bid.final_decision == 'confirmed':
            # 구매 확정한 참여자들 정보 제공
            confirmed_participations = groupbuy.participation_set.filter(final_decision='confirmed')
            participants_info = []
            for p in confirmed_participations:
                participants_info.append({
                    'name': p.user.username,
                    'phone': p.user.phone_number if p.user.phone_number else '미등록',
                    'email': p.user.email,
                    'joined_at': p.joined_at
                })
            
            return Response({
                'role': 'seller',
                'contact_info': participants_info
            })
        
        return Response(
            {'error': '연락처 정보를 조회할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # my_vote 메서드는 voting 상태를 제거하면서 삭제됨
    
    @action(detail=True, methods=['get'])
    def bids(self, request, pk=None):
        """공구의 입찰 목록 조회"""
        groupbuy = self.get_object()
        bids = Bid.objects.filter(groupbuy=groupbuy).select_related('seller').order_by('-amount')
        
        # 입찰 데이터 직렬화
        bid_data = []
        for bid in bids:
            bid_data.append({
                'id': bid.id,
                'seller': {
                    'id': bid.seller.id,
                    'username': bid.seller.username,
                    'business_name': getattr(bid.seller, 'business_name', ''),
                    'profile_image': getattr(bid.seller, 'profile_image', ''),
                    'rating': getattr(bid.seller, 'rating', None)
                },
                'bid_type': bid.bid_type,
                'amount': bid.amount,
                'message': bid.message or '',
                'created_at': bid.created_at,
                'is_selected': bid.is_selected
            })
        
        return Response(bid_data)
    
    @action(detail=True, methods=['get'])
    def winning_bid(self, request, pk=None):
        """낙찰된 입찰 정보 조회"""
        groupbuy = self.get_object()
        
        # 낙찰된 입찰 찾기
        winning_bid = Bid.objects.filter(groupbuy=groupbuy, is_selected=True).first()
        
        if not winning_bid:
            return Response(
                {'message': '아직 낙찰된 입찰이 없습니다.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            'bid': {
                'id': winning_bid.id,
                'seller': {
                    'id': winning_bid.seller.id,
                    'username': winning_bid.seller.username,
                    'business_name': getattr(winning_bid.seller, 'business_name', ''),
                    'profile_image': getattr(winning_bid.seller, 'profile_image', '')
                },
                'bid_type': winning_bid.bid_type,
                'amount': winning_bid.amount,
                'message': winning_bid.message or '',
                'created_at': winning_bid.created_at
            },
            'total_participants': groupbuy.current_participants
        })
    
    # voting_results 메서드는 voting 상태를 제거하면서 삭제됨
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """사용자가 공구에서 나가기 API"""
        from django.db import transaction
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Leave API called for groupbuy_id: {pk}, user_id: {request.user.id}")
        
        try:
            groupbuy = self.get_object()
            logger.debug(f"GroupBuy found: {groupbuy.id}, creator_id: {groupbuy.creator.id if groupbuy.creator else 'None'}")
            
            user = request.user
            logger.debug(f"User: {user.id}, is_creator: {user.id == groupbuy.creator.id if groupbuy.creator else False}")
            
            # 참여 여부 확인
            try:
                participation = Participation.objects.get(user=user, groupbuy=groupbuy)
                logger.debug(f"Participation found: {participation.id}")
            except Participation.DoesNotExist:
                logger.warning(f"Error: User is not participating in this group buy")
                return Response(
                    {'error': '참여하지 않은 공구입니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 입찰 진행 여부 확인
            has_bids = Bid.objects.filter(groupbuy=groupbuy).exists()
            logger.debug(f"Has bids: {has_bids}")
            
            if has_bids:
                logger.warning(f"Error: Cannot leave group buy with active bids")
                return Response(
                    {'error': '입찰이 진행 중인 공구에서는 나가기가 불가합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Unexpected error in leave API: {str(e)}")
            error_message = f'공구 나가기 중 오류가 발생했습니다: {str(e)}'
            return Response(
                {
                    'error': error_message,
                    'error_detail': str(e),
                    'status': 'error'
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 공구 생성자 처리
        logger.debug(f"Checking if user is creator: {user.id == groupbuy.creator.id if groupbuy.creator else False}")
        if groupbuy.creator == user:
            logger.info(f"User is the creator of this group buy")
            
            # 공구에 다른 참여자가 있는지 확인 (자기 자신은 제외)
            other_participants_exist = Participation.objects.filter(groupbuy=groupbuy).exclude(user=user).exists()
            logger.debug(f"Other participants exist: {other_participants_exist}")
            
            # 입찰자가 없고 다른 참여자도 없는 경우
            if not has_bids and not other_participants_exist:
                logger.info(f"No bids and no other participants, allowing creator to leave and cancelling group buy")
                try:
                    with transaction.atomic():
                        # 공구 상태를 취소로 변경
                        groupbuy.status = 'cancelled'
                        groupbuy.save(update_fields=['status'])
                        logger.info(f"Group buy status changed to cancelled")
                        
                        # 참여 삭제
                        participation.delete()
                        logger.info(f"Participation deleted")
                    
                    return Response({
                        'message': '공구가 취소되었습니다. 동일한 상품으로 새로운 공구를 만들 수 있습니다.'
                    }, status=status.HTTP_200_OK)
                except Exception as e:
                    logger.error(f"Error while cancelling group buy: {str(e)}")
                    error_message = f'공구 취소 중 오류가 발생했습니다: {str(e)}'
                    return Response(
                        {
                            'error': error_message,
                            'error_detail': str(e),
                            'status': 'error'
                        }, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                logger.warning(f"Creator cannot leave: has_bids={has_bids}, other_participants_exist={other_participants_exist}")
                # 입찰자가 있거나 다른 참여자가 있으면 탈퇴 불가
                return Response(
                    {'error': '입찰자가 있거나 다른 참여자가 있는 공구의 생성자는 나가기가 불가합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 생성자가 아닌 경우
        logger.info(f"User is not the creator, proceeding with normal leave")
        
        try:
            with transaction.atomic():
                # 참여 삭제
                participation.delete()
                logger.info(f"Participation deleted for non-creator")
                
                # 현재 참여자 수 감소 (F 표현식 사용하여 race condition 방지)
                GroupBuy.objects.filter(pk=groupbuy.id).update(
                    current_participants=F('current_participants') - 1
                )
                
                # 최신 데이터로 갱신
                groupbuy.refresh_from_db()
                logger.info(f"Current participants decreased to {groupbuy.current_participants}")
            
            return Response({
                'message': '공구 나가기가 완료되었습니다.',
                'current_participants': groupbuy.current_participants
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during non-creator leave: {str(e)}")
            error_message = f'공구 나가기 중 오류가 발생했습니다: {str(e)}'
            return Response(
                {
                    'error': error_message,
                    'error_detail': str(e),
                    'status': 'error'
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
    @action(detail=True, methods=['get'])
    def check_participation(self, request, pk=None):
        """사용자의 공구 참여 여부와 입찰 진행 상태를 확인하는 API"""
        groupbuy = self.get_object()
        user = request.user
        
        # 로그인하지 않은 경우
        if user.is_anonymous:
            return Response({
                'is_participating': False,
                'has_bids': False,
                'can_leave': False
            })
        
        # 참여 여부 확인
        is_participating = Participation.objects.filter(user=user, groupbuy=groupbuy).exists()
        
        # 입찰 진행 여부 확인
        has_bids = Bid.objects.filter(groupbuy=groupbuy).exists()
        
        # 탈퇴 가능 여부 확인
        can_leave = is_participating and not has_bids and groupbuy.creator != user
        
        return Response({
            'is_participating': is_participating,
            'has_bids': has_bids,
            'can_leave': can_leave
        })
    
    @action(detail=True, methods=['get'])
    def participants_detail(self, request, pk=None):
        """공구 참여자 상세 정보를 반환하는 API
        
        공구 생성자 또는 관리자만 접근 가능하며,
        참여자의 상세 정보와 동의 상태를 반환합니다.
        """
        groupbuy = self.get_object()
        user = request.user
        
        # 권한 확인: 공구 생성자이거나 관리자인 경우만 접근 가능
        if not (groupbuy.creator == user or user.is_staff or user.is_superuser):
            return Response(
                {'error': '공구 생성자 또는 관리자만 참여자 정보를 조회할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 활성 참여자 조회 (삭제되지 않은 참여자)
        participations = Participation.objects.filter(
            groupbuy=groupbuy
        ).select_related('user').prefetch_related('consent')
        
        # 참여자 정보 구성
        participants_data = []
        for participation in participations:
            participant_info = {
                'id': participation.id,
                'user': {
                    'id': participation.user.id,
                    'username': participation.user.username,
                    'email': participation.user.email,
                },
                'joined_at': participation.joined_at,
                'is_leader': participation.is_leader,
            }
            
            # 동의 상태 정보 추가 (존재하는 경우)
            try:
                if hasattr(participation, 'consent'):
                    consent = participation.consent
                    participant_info['consent_status'] = {
                        'status': consent.status,
                        'agreed_at': consent.agreed_at,
                        'disagreed_at': consent.disagreed_at,
                        'consent_deadline': consent.consent_deadline,
                    }
                else:
                    participant_info['consent_status'] = None
            except:
                participant_info['consent_status'] = None
                
            participants_data.append(participant_info)
        
        # 응답 데이터 구성
        response_data = {
            'total_count': len(participants_data),
            'participants': participants_data,
            'groupbuy': {
                'id': groupbuy.id,
                'title': groupbuy.title,
                'status': groupbuy.status,
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

class ParticipationViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Participation.objects.all()
    serializer_class = ParticipationSerializer
    
    def get_queryset(self):
        # 현재 로그인한 사용자의 참여 정보만 반환
        return Participation.objects.filter(user=self.request.user)
        
    @action(detail=False, methods=['get'])
    def me(self, request):
        """현재 로그인한 사용자의 참여 공구 목록 반환"""
        participations = Participation.objects.filter(user=request.user)
        serializer = self.get_serializer(participations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='(?P<groupbuy_id>[^/.]+)/final-decision')
    def final_decision(self, request, groupbuy_id=None):
        """참여자의 최종 구매 결정 (구매확정/구매포기)"""
        try:
            # 참여 정보 확인
            participation = Participation.objects.get(
                user=request.user,
                groupbuy_id=groupbuy_id
            )
            
            # 공구 상태 확인
            if participation.groupbuy.status != 'final_selection':
                return Response(
                    {'error': '최종선택 기간이 아닙니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 이미 결정한 경우
            if participation.final_decision != 'pending':
                return Response(
                    {'error': '이미 최종선택을 완료했습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 결정 유형 검증
            decision = request.data.get('decision')
            if decision not in ['confirmed', 'cancelled']:
                return Response(
                    {'error': '올바르지 않은 선택입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 최종 결정 업데이트
            participation.final_decision = decision
            participation.save()
            
            # 알림 생성
            from .models import Notification
            if decision == 'confirmed':
                Notification.objects.create(
                    user=participation.user,
                    groupbuy=participation.groupbuy,
                    notification_type='purchase_confirmed',
                    message=f"{participation.groupbuy.title} 공구의 구매를 확정했습니다. 판매자 정보를 확인하세요."
                )
            else:
                Notification.objects.create(
                    user=participation.user,
                    groupbuy=participation.groupbuy,
                    notification_type='purchase_cancelled',
                    message=f"{participation.groupbuy.title} 공구의 구매를 포기했습니다."
                )
            
            # 모든 참여자와 판매자가 결정을 완료했는지 확인
            self._check_all_decisions_complete(participation.groupbuy)
            
            return Response({
                'message': '최종선택이 완료되었습니다.',
                'decision': decision
            })
            
        except Participation.DoesNotExist:
            return Response(
                {'error': '참여 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _check_all_decisions_complete(self, groupbuy):
        """모든 참여자와 판매자의 결정이 완료되었는지 확인"""
        from .models import Bid
        
        # 참여자들의 결정 확인
        pending_participants = groupbuy.participation_set.filter(final_decision='pending').exists()
        
        # 낙찰된 판매자의 결정 확인
        winning_bid = groupbuy.bid_set.filter(status='selected').first()
        seller_pending = winning_bid and winning_bid.final_decision == 'pending'
        
        # 모두 결정을 완료한 경우
        if not pending_participants and not seller_pending:
            # 구매 확정한 참여자가 있고 판매자도 확정한 경우
            confirmed_participants = groupbuy.participation_set.filter(final_decision='confirmed').exists()
            seller_confirmed = winning_bid and winning_bid.final_decision == 'confirmed'
            
            if confirmed_participants and seller_confirmed:
                groupbuy.status = 'completed'
            else:
                groupbuy.status = 'cancelled'
            
            groupbuy.save()

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        response_data = {
            'id': user.id,
            'email': user.email,
            'username': user.username,  # 닉네임 수정을 위해 get_full_name() 사용하지 않고 username만 반환
            'profile_image': user.profile_image,
            'sns_type': user.sns_type,
            'phone_number': user.phone_number,
            'address_detail': user.address_detail,
            'role': user.role,
            'is_business_verified': user.is_business_verified,
        }
        
        # 주소 지역 정보 추가
        if user.address_region:
            response_data['address_region'] = {
                'id': user.address_region.code,  # code is the primary key
                'code': user.address_region.code,
                'name': user.address_region.name,
                'full_name': user.address_region.full_name,
            }
        else:
            response_data['address_region'] = None
            
        return Response(response_data)

    def patch(self, request):
        user = request.user
        email = request.data.get('email')
        username = request.data.get('username')
        phone_number = request.data.get('phone_number')
        address_region_id = request.data.get('address_region_id')
        address_detail = request.data.get('address_detail')
        
        changed = False
        
        # 이메일 업데이트 처리
        if email is not None:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({'error': '이미 사용 중인 이메일입니다.'}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email
            changed = True
        
        # 닉네임(사용자명) 업데이트 처리
        if username is not None:
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                return Response({'error': '이미 사용 중인 닉네임입니다.'}, status=status.HTTP_400_BAD_REQUEST)
            user.username = username
            changed = True
        
        # 휴대폰 번호 업데이트 처리
        if phone_number is not None:
            if phone_number and User.objects.filter(phone_number=phone_number).exclude(id=user.id).exists():
                return Response({'error': '이미 사용 중인 휴대폰 번호입니다.'}, status=status.HTTP_400_BAD_REQUEST)
            user.phone_number = phone_number
            changed = True
        
        # 주소 지역 업데이트 처리
        if address_region_id is not None:
            if address_region_id:
                try:
                    region = Region.objects.get(code=address_region_id)
                    user.address_region = region
                    changed = True
                except Region.DoesNotExist:
                    return Response({'error': '유효하지 않은 지역입니다.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                user.address_region = None
                changed = True
        
        # 상세 주소 업데이트 처리
        if address_detail is not None:
            user.address_detail = address_detail
            changed = True
            
        # 변경사항이 있으면 저장
        if changed:
            user.save()
        
        # 응답 데이터 구성
        response_data = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'profile_image': user.profile_image,
            'sns_type': user.sns_type,
            'phone_number': user.phone_number,
            'address_detail': user.address_detail,
            'role': user.role,
            'is_business_verified': user.is_business_verified,
        }
        
        # 주소 지역 정보 추가
        if user.address_region:
            response_data['address_region'] = {
                'id': user.address_region.code,  # code is the primary key
                'code': user.address_region.code,
                'name': user.address_region.name,
                'full_name': user.address_region.full_name,
            }
        else:
            response_data['address_region'] = None
            
        return Response(response_data)

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


class SellerViewSet(ViewSet):
    """판매자 관련 API를 위한 뷰셋
    
    판매자 활동에 필요한 API 엔드포인트를 제공합니다.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    @action(detail=False, methods=['GET'])
    def bids(self, request):
        """판매자의 입찰 목록을 반환하는 API
        
        로그인한 판매자가 입찰한 목록을 반환합니다.
        """
        user = request.user
        
        # 판매자 역할 확인
        if user.role != 'seller':
            return Response(
                {'error': '판매자 권한이 필요합니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 판매자가 입찰한 목록 가져오기
        bids = Bid.objects.filter(seller=user)
        serializer = BidSerializer(bids, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['GET'])
    def settlements(self, request):
        """판매자의 정산 내역을 반환하는 API
        
        로그인한 판매자의 정산 내역을 반환합니다.
        """
        user = request.user
        
        # 판매자 역할 확인
        if user.role != 'seller':
            return Response(
                {'error': '판매자 권한이 필요합니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # 정산 대기 중(선택된 입찰) 내역 가져오기
        selected_bids = Bid.objects.filter(
            seller=user, 
            is_selected=True, 
            status='selected'
        )
        serializer = BidSerializer(selected_bids, many=True)
        return Response(serializer.data)


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
    
    def create(self, request, *args, **kwargs):
        """리뷰 생성 API with detailed error logging"""
        logger.info(f"리뷰 생성 요청 - 사용자: {request.user.username}")
        logger.info(f"요청 데이터: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except serializers.ValidationError as e:
            logger.error(f"리뷰 생성 검증 오류: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"리뷰 생성 중 예상치 못한 오류: {str(e)}")
            raise
    
    def perform_create(self, serializer):
        """리뷰 작성 시 현재 사용자 정보 자동 설정 및 자신의 공구에는 리뷰 작성 불가"""
        groupbuy = serializer.validated_data.get('groupbuy')
        
        # 자신이 만든 공구에는 리뷰를 작성할 수 없음
        if groupbuy.creator == self.request.user:
            raise serializers.ValidationError({
                'non_field_errors': ['자신이 만든 공구에는 리뷰를 작성할 수 없습니다.']
            })
            
        # 리뷰 저장 - 현재 사용자를 작성자로 설정
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
