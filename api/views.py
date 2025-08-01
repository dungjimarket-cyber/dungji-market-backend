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
                    # 종료: 마감시간이 지났거나 voting/final_selection/seller_confirmation/completed/cancelled 상태인 공구
                    queryset = queryset.filter(
                        Q(end_time__lte=now) | 
                        Q(status__in=['voting', 'final_selection', 'seller_confirmation', 'completed', 'cancelled'])
                    )
                elif status_param == 'completed':
                    # 완료: completed 상태이거나 마감시간이 지난 공구
                    queryset = queryset.filter(
                        Q(status='completed') | Q(end_time__lte=now)
                    )
                elif status_param == 'in_progress':
                    # 최종선택 이전 상태(recruiting, bidding, voting)만 필터링
                    queryset = queryset.filter(status__in=['recruiting', 'bidding', 'voting'])

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
            status__in=['recruiting', 'bidding', 'voting', 'seller_confirmation'] # 진행 중인 공구만 체크
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
        # 최종선택 이전 상태(recruiting, bidding, voting)인 공구만 필터링
        popular_groupbuys = GroupBuy.objects.annotate(
            curent_participants=Count('participation')
        ).filter(
            end_time__gt=timezone.now(),
            status__in=['recruiting', 'bidding', 'voting']  # 최종선택 이전 상태만
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
        if self.action in ['list', 'retrieve', 'popular', 'recent', 'bids', 'winning_bid', 'voting_results']:
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
        
    @action(detail=False, methods=['get'])
    def pending_selection(self, request):
        """최종 선택 대기중인 공구 목록 조회
        
        사용자가 참여한 공구 중 확정된(confirmed) 상태이거나 
        모집이 완료되었지만 아직 최종 선택을 하지 않은 공구 목록 반환
        """
        # 사용자가 참여한 공구 중 'confirmed' 상태인 공구 또는
        # 'recruiting' 상태지만 모집 완료된(current_participants == max_participants) 공구
        pending = self.get_queryset().filter(
            participants=request.user
        ).filter(
            Q(status='confirmed') | 
            Q(status='recruiting', current_participants__gte=F('max_participants'))
        )
        
        serializer = self.get_serializer(pending, many=True)
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
        
        # 공구 상태 확인
        now = timezone.now()
        if groupbuy.status != 'recruiting' or now > groupbuy.end_time:
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
        
    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        """공구 참여자가 원하는 판매자의 입찰에 투표"""
        from .models_voting import BidVote
        from django.db import transaction
        
        groupbuy = self.get_object()
        user = request.user
        bid_id = request.data.get('bid_id')
        
        if not bid_id:
            return Response(
                {'error': '입찰을 선택해주세요.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 공구 참여자인지 확인
        if not groupbuy.participants.filter(id=user.id).exists():
            return Response(
                {'error': '공구 참여자만 투표할 수 있습니다.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # 공구 상태가 voting인지 확인
        if groupbuy.status != 'voting':
            return Response(
                {'error': '현재 투표 기간이 아닙니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 투표 마감 시간 확인
        if groupbuy.voting_end and timezone.now() > groupbuy.voting_end:
            return Response(
                {'error': '투표 시간이 종료되었습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 입찰 확인
            bid = Bid.objects.get(id=bid_id, groupbuy=groupbuy)
            
            with transaction.atomic():
                # 기존 투표가 있으면 업데이트, 없으면 생성
                vote, created = BidVote.objects.update_or_create(
                    participant=user,
                    groupbuy=groupbuy,
                    defaults={'bid': bid}
                )
                
            return Response({
                'message': '투표가 완료되었습니다.',
                'bid_id': bid.id,
                'seller': bid.seller.username
            }, status=status.HTTP_200_OK)
            
        except Bid.DoesNotExist:
            return Response(
                {'error': '유효하지 않은 입찰입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"투표 중 오류 발생: {str(e)}")
            return Response(
                {'error': '투표 처리 중 오류가 발생했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def my_vote(self, request, pk=None):
        """현재 사용자의 투표 상태 조회"""
        from .models_voting import BidVote
        
        groupbuy = self.get_object()
        user = request.user
        
        try:
            vote = BidVote.objects.get(participant=user, groupbuy=groupbuy)
            return Response({
                'bid_id': vote.bid.id,
                'seller': vote.bid.seller.username,
                'voted_at': vote.created_at
            })
        except BidVote.DoesNotExist:
            return Response(
                {'message': '아직 투표하지 않았습니다.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
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
        from .models_voting import BidVote
        from django.db.models import Count
        
        groupbuy = self.get_object()
        
        # 낙찰된 입찰 찾기
        winning_bid = Bid.objects.filter(groupbuy=groupbuy, is_selected=True).first()
        
        if not winning_bid:
            return Response(
                {'message': '아직 낙찰된 입찰이 없습니다.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 투표 수 계산
        vote_count = BidVote.objects.filter(groupbuy=groupbuy, bid=winning_bid).count()
        total_votes = BidVote.objects.filter(groupbuy=groupbuy).count()
        
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
                'created_at': winning_bid.created_at,
                'vote_count': vote_count
            },
            'total_votes': total_votes,
            'total_participants': groupbuy.current_participants
        })
    
    @action(detail=True, methods=['get'])
    def voting_results(self, request, pk=None):
        """투표 결과 조회"""
        from .models_voting import BidVote
        from django.db.models import Count
        
        groupbuy = self.get_object()
        
        # 투표 집계
        results = BidVote.objects.filter(groupbuy=groupbuy).values(
            'bid__id', 'bid__seller__username', 'bid__amount'
        ).annotate(
            vote_count=Count('id')
        ).order_by('-vote_count')
        
        # 전체 참여자 수
        total_participants = groupbuy.current_participants
        
        # 투표한 사람 수
        total_votes = BidVote.objects.filter(groupbuy=groupbuy).count()
        
        return Response({
            'total_participants': total_participants,
            'total_votes': total_votes,
            'abstention_count': total_participants - total_votes,
            'results': list(results),
            'voting_end': groupbuy.voting_end
        })
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """사용자가 공구에서 탈퇴하는 API"""
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
                    {'error': '입찰이 진행 중인 공구에서는 탈퇴할 수 없습니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Unexpected error in leave API: {str(e)}")
            error_message = f'공구 탈퇴 중 오류가 발생했습니다: {str(e)}'
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
                    {'error': '입찰자가 있거나 다른 참여자가 있는 공구의 생성자는 탈퇴할 수 없습니다.'}, 
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
                'message': '공구 탈퇴가 완료되었습니다.',
                'current_participants': groupbuy.current_participants
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during non-creator leave: {str(e)}")
            error_message = f'공구 탈퇴 중 오류가 발생했습니다: {str(e)}'
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
