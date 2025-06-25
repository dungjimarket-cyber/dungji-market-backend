from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, Permission
from django.db.models import Q, Count, F, Sum, Avg, Case, When, Value, IntegerField
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
from .serializers import CategorySerializer, ProductSerializer, GroupBuySerializer, ParticipationSerializer, WishlistSerializer, ReviewSerializer, BidSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
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
        role = data.get('role', 'user')  # 기본값은 일반 사용자
        
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

        # role 값이 유효한지 확인 (seller 또는 user만 허용)
        if role not in ['seller', 'user']:
            return Response(
                {'error': 'Invalid role. Must be either "seller" or "user".'},
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

        # Check if user exists by sns_id
        user = User.objects.filter(sns_id=sns_id).first()
        if user:
            # 기존 사용자 정보 업데이트
            user.last_login = timezone.now()
            
            # 이메일이 비어있고 새로운 이메일이 있는 경우 업데이트
            if (not user.email or user.email == '') and email:
                logger.info(f"기존 사용자({user.id})의 이메일 업데이트: {email}")
                user.email = email
            
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
from django.db.models import Count
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

        # status 필터 처리
        if status_param == 'active':
            queryset = queryset.filter(end_time__gt=timezone.now())
        elif status_param == 'completed':
            queryset = queryset.filter(end_time__lte=timezone.now())

        # category 필터 처리
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
            
        # 정렬 처리
        if sort_param:
            # 한글 정렬 옵션 처리
            if sort_param == '최신순' or sort_param == 'newest':
                queryset = queryset.order_by('-start_time')  # 최신 공구가 먼저 표시
            elif sort_param == '인기순(참여자많은순)' or sort_param == 'popular':
                queryset = queryset.order_by('-current_participants')  # 참여자 많은 순으로 정렬
            else:
                # 기본 정렬은 최신순
                queryset = queryset.order_by('-start_time')
        else:
            # 기본 정렬은 최신순
            queryset = queryset.order_by('-start_time')
            
        # 공구 상태 자동 업데이트 (최대 100개까지만 처리)
        update_groupbuys_status(queryset[:100])

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
        
        # 동일한 상품으로 이미 생성된 공구가 있는지 확인 (모든 사용자 대상)
        existing_groupbuy = GroupBuy.objects.filter(
            product_id=product_id,
            status__in=['recruiting', 'in_progress'] # 진행 중인 공구만 체크
        ).first()
        
        # 통신 제품인 경우 통신사/가입유형/요금제 정보가 다르면 중복 허용
        if existing_groupbuy:
            if not has_telecom_info:
                # 통신 정보가 없는 경우 중복 공구 생성 불가
                error_msg = {
                    'non_field_errors': [
                        f'이미 동일한 제품({existing_groupbuy.product_name})으로 진행 중인 공구가 있습니다. '
                        f'다른 제품을 선택하거나, 통신 제품의 경우 통신사/가입유형/요금제 정보를 다르게 입력하여 등록해주세요.'
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
                        'non_field_errors': [
                            f'이미 동일한 제품과 동일한 통신 정보로 진행 중인 공구가 있습니다. '
                            f'다른 제품을 선택하거나, 통신사/가입유형/요금제 정보를 다르게 입력하여 등록해주세요.'
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
                
                # GroupBuyTelecomDetail 모델 생성
                GroupBuyTelecomDetail.objects.create(
                    groupbuy=groupbuy,
                    telecom_carrier=telecom_info['telecom_carrier'],
                    subscription_type=telecom_info['subscription_type'],
                    plan_info=telecom_info['plan_info'],
                    contract_period=telecom_info.get('contract_period')
                )
                
                print(f"\n[GroupBuyTelecomDetail 생성 완료] groupbuy_id: {groupbuy.id}")
            
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
        
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """사용자가 공구에서 탈퇴하는 API"""
        groupbuy = self.get_object()
        user = request.user
        
        # 참여 여부 확인
        try:
            participation = Participation.objects.get(user=user, groupbuy=groupbuy)
        except Participation.DoesNotExist:
            return Response(
                {'error': '참여하지 않은 공구입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 입찰 진행 여부 확인
        has_bids = Bid.objects.filter(groupbuy=groupbuy).exists()
        if has_bids:
            return Response(
                {'error': '입찰이 진행 중인 공구에서는 탈퇴할 수 없습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 공구 생성자는 탈퇴 불가
        if groupbuy.creator == user:
            return Response(
                {'error': '공구 생성자는 탈퇴할 수 없습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 참여 삭제
        participation.delete()
        
        # 현재 참여자 수 감소
        groupbuy.current_participants -= 1
        groupbuy.save(update_fields=['current_participants'])
        
        return Response({
            'message': '공구 탈퇴가 완료되었습니다.'
        }, status=status.HTTP_200_OK)
        
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
            'username': user.username,  # 닉네임 수정을 위해 get_full_name() 사용하지 않고 username만 반환
            'profile_image': user.profile_image,
            'sns_type': user.sns_type,
        })

    def patch(self, request):
        user = request.user
        email = request.data.get('email')
        username = request.data.get('username')
        
        changed = False
        
        # 이메일 업데이트 처리
        if email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({'error': '이미 사용 중인 이메일입니다.'}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email
            changed = True
        
        # 닉네임(사용자명) 업데이트 처리
        if username:
            user.username = username
            changed = True
            
        # 변경사항이 있으면 저장
        if changed:
            user.save()

        return Response({
            'id': user.id,
            'email': user.email,
            'username': user.username,  # 닉네임 수정을 위해 get_full_name() 사용하지 않고 username만 반환
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
