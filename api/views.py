from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import authentication_classes, permission_classes, api_view, action
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Category, Product, GroupBuy, Participation
from .serializers import CategorySerializer, ProductSerializer, GroupBuySerializer, ParticipationSerializer
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

        if not sns_id or not sns_type or not email:
            return Response(
                {'error': 'SNS ID, type, and email are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user exists by sns_id
        user = User.objects.filter(sns_id=sns_id).first()
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'jwt': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
                'user_id': user.id,
                'username': user.get_full_name() or user.username,
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
            user = User.objects.create_user(
                username=email,
                email=email,
                password=None,  # SNS users don't need password
                first_name=name,
                sns_type=sns_type,
                sns_id=sns_id,
                profile_image=profile_image
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'jwt': {
                'access': token.key,
                'refresh': token.key,  # For compatibility with frontend, using same token
            },
            'user_id': user.id,
            'username': user.get_full_name() or user.username,
            'email': user.email,
            'access': token.key,
            'refresh': token.key,  # For compatibility with frontend
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
        category_slug = self.request.query_params.get('category', None)
        if category_slug is not None:
            # Get the category and all its subcategories
            category = Category.objects.filter(slug=category_slug).first()
            if category:
                # Get all subcategory IDs
                subcategory_ids = list(Category.objects.filter(parent=category).values_list('id', flat=True))
                # Include the main category ID
                category_ids = [category.id] + subcategory_ids
                queryset = queryset.filter(category_id__in=category_ids)
        return queryset

# views.py
from django.db.models import Count
from django.utils import timezone

class GroupBuyViewSet(ModelViewSet):
    serializer_class = GroupBuySerializer
    queryset = GroupBuy.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = GroupBuy.objects.all()
        status = self.request.query_params.get('status', None)
        
        if status == 'active':
            queryset = queryset.filter(end_time__gt=timezone.now())
        elif status == 'completed':
            queryset = queryset.filter(end_time__lte=timezone.now())
            
        return queryset

    @action(detail=False)
    def popular(self, request):
        popular_groupbuys = GroupBuy.objects.annotate(
            participant_count=Count('participation')
        ).filter(
            end_time__gt=timezone.now()
        ).order_by('-participant_count')[:3]
        
        serializer = self.get_serializer(popular_groupbuys, many=True)
        return Response(serializer.data)

    @action(detail=False)
    def recent(self, request):
        recent_groupbuys = GroupBuy.objects.filter(
            end_time__gt=timezone.now()
        ).order_by('-start_time')[:3]
        
        serializer = self.get_serializer(recent_groupbuys, many=True)
        return Response(serializer.data)  # Require authentication for creating group buys

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'popular', 'recent']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return GroupBuy.objects.select_related('product', 'product__category').all()

    def _add_product_details(self, data, product):
        data['product'] = {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'base_price': product.base_price,
            'image_url': product.image_url,
            'category_name': product.category.name if product.category else None
        }
        return data

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # Add product details to each group buy
        for item, instance in zip(data, queryset):
            self._add_product_details(item, instance.product)

        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        # Add product details
        self._add_product_details(data, instance.product)
        
        return Response(data)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status', None)
        category_id = self.request.query_params.get('category', None)

        if status_param:
            queryset = queryset.filter(status=status_param)
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)

        return queryset

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