from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .permissions import IsAdminRole
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import GroupBuy, Bid, BidToken, Product
from .serializers import GroupBuySerializer
from .utils.s3_utils import upload_file_to_s3, delete_file_from_s3

User = get_user_model()

# 관리자 페이지용 UserSerializer 정의
class UserSerializer(serializers.ModelSerializer):
    active_tokens_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'active_tokens_count', 'date_joined', 'is_active']
        read_only_fields = ['date_joined', 'active_tokens_count']
    
    def get_active_tokens_count(self, obj):
        # 활성 상태이고 만료되지 않은 입찰권 수 계산
        return BidToken.objects.filter(
            seller=obj,
            status='active',
            expires_at__gt=timezone.now()
        ).count()

class AdminViewSet(viewsets.ViewSet):
    """
    관리자 전용 API를 위한 ViewSet
    
    관리자 권한이 필요한 기능들을 제공합니다.
    """
    permission_classes = [IsAdminRole]
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=True, methods=['post'], url_path='update_product_image')
    def update_product_image(self, request, pk=None):
        """
        상품 이미지를 업데이트하는 API
        
        프론트엔드 어드민에서 이미지 업로드 시 사용됩니다.
        """
        try:
            product = Product.objects.get(pk=pk)
            
            # 이미지 파일이 요청에 포함되어 있는지 확인
            if 'image' not in request.FILES:
                return Response({'error': '이미지 파일이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
            
            image_file = request.FILES['image']
            
            # 기존 이미지가 있으면 S3에서 삭제
            if product.image:
                try:
                    delete_file_from_s3(product.image.name)
                except Exception as e:
                    # 기존 파일 삭제 실패해도 계속 진행
                    pass
            
            # S3에 새 이미지 업로드
            uploaded_url = upload_file_to_s3(image_file)
            
            # 제품 모델 업데이트
            product.image = image_file
            product.image_url = uploaded_url  # image_url 필드도 함께 업데이트
            product.save()
            
            return Response({
                'success': True,
                'image_url': uploaded_url
            }, status=status.HTTP_200_OK)
            
        except Product.DoesNotExist:
            return Response({'error': '상품을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def group_purchases(self, request):
        """
        모든 공동구매 목록을 반환하는 API
        """
        groupbuys = GroupBuy.objects.all().order_by('-start_time')
        serializer = GroupBuySerializer(groupbuys, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def delete_group_purchase(self, request, pk=None):
        """
        특정 공동구매를 삭제하는 API
        """
        try:
            groupbuy = GroupBuy.objects.get(pk=pk)
            groupbuy.delete()
            return Response({"message": "공동구매가 성공적으로 삭제되었습니다."}, status=status.HTTP_200_OK)
        except GroupBuy.DoesNotExist:
            return Response({"error": "해당 공동구매를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"공동구매 삭제 중 오류가 발생했습니다: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def sellers(self, request):
        """
        모든 셀러 사용자 목록을 반환하는 API
        """
        sellers = User.objects.filter(role='seller')
        serializer = UserSerializer(sellers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_bid_permission(self, request, pk=None):
        """
        특정 셀러에게 입찰권을 부여하는 API
        
        request.data에 필요한 필드:
        - bid_count: 부여할 입찰권 수 (정수)
        - token_type: 입찰권 유형 ('single' - 입찰권 단품, 'unlimited' - 무제한 구독권 중 하나)
        """
        try:
            from datetime import timedelta
            from django.utils import timezone
            from api.models import BidToken, BidTokenPurchase
            
            user = User.objects.get(pk=pk)
            
            # 셀러 권한 확인
            if user.role != 'seller':
                return Response({"error": "셀러 사용자에게만 입찰권을 부여할 수 있습니다."}, status=status.HTTP_400_BAD_REQUEST)
            
            # 입찰권 수 확인
            bid_count = request.data.get('bid_count')
            if not bid_count or not isinstance(bid_count, int) or bid_count <= 0:
                return Response({"error": "유효한 입찰권 수를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
            
            # 입찰권 유형 확인
            token_type = request.data.get('token_type', 'single')
            if token_type not in [choice[0] for choice in BidToken.TOKEN_TYPE_CHOICES]:
                return Response({"error": "유효한 입찰권 유형을 선택해주세요."}, status=status.HTTP_400_BAD_REQUEST)
            
            # 입찰권 만료일 설정 (유형에 따라 다르게 설정)
            if token_type == 'single':
                expires_at = None  # 입찰권 단품: 유효기간 없음
                price_per_token = 1990  # 입찰권 단품 가격
            else:  # unlimited
                expires_at = timezone.now() + timedelta(days=30)  # 무제한 구독권: 30일
                price_per_token = 29900  # 무제한 구독권 가격
            
            # 입찰권 구매 내역 생성 (관리자가 부여하는 경우 무료로 처리)
            purchase = BidTokenPurchase.objects.create(
                seller=user,
                token_type=token_type,
                quantity=bid_count,
                total_price=0,  # 관리자 부여는 무료
                payment_status='completed',  # 관리자 부여는 자동 결제 완료로 처리
                payment_date=timezone.now()
            )
            
            # 입찰권 생성
            created_tokens = []
            for _ in range(bid_count):
                token = BidToken.objects.create(
                    seller=user,
                    token_type=token_type,
                    expires_at=expires_at,
                    status='active'
                )
                created_tokens.append(token)
            
            # 사용자의 현재 활성 입찰권 수 계산
            active_tokens_count = BidToken.objects.filter(
                seller=user, 
                status='active',
                expires_at__gt=timezone.now()
            ).count()
            
            return Response({
                "message": f"{user.username} 사용자에게 {bid_count}개의 {dict(BidToken.TOKEN_TYPE_CHOICES).get(token_type)}이(가) 부여되었습니다.",
                "user_id": user.id,
                "username": user.username,
                "active_tokens_count": active_tokens_count,
                "token_type": token_type
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({"error": "해당 사용자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"입찰권 부여 중 오류가 발생했습니다: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def upload_product_image(self, request):
        """
        상품 이미지를 S3에 업로드하는 API
        
        request.data에 필요한 필드:
        - image: 업로드할 이미지 파일
        - product_id: 이미지를 연결할 상품 ID (선택적)
        """
        try:
            # 이미지 파일 확인
            if 'image' not in request.FILES:
                return Response({"error": "이미지 파일이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
            
            image_file = request.FILES['image']
            
            # 이미지 파일 타입 검증
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return Response(
                    {"error": "지원되지 않는 이미지 형식입니다. JPEG, PNG, GIF, WEBP 형식만 허용됩니다."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 파일 크기 제한 (10MB)
            if image_file.size > 10 * 1024 * 1024:
                return Response(
                    {"error": "이미지 크기는 10MB를 초과할 수 없습니다."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # S3에 이미지 업로드
            image_url = upload_file_to_s3(image_file)
            
            if not image_url:
                return Response(
                    {"error": "이미지 업로드 중 오류가 발생했습니다."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 상품 ID가 제공된 경우 해당 상품의 이미지 URL 업데이트
            product_id = request.data.get('product_id')
            product_updated = False
            
            if product_id:
                try:
                    product = Product.objects.get(pk=product_id)
                    
                    # 기존 이미지가 있는 경우 S3에서 삭제
                    if product.image_url:
                        delete_file_from_s3(product.image_url)
                    
                    # 새 이미지 URL로 업데이트
                    product.image_url = image_url
                    product.save()
                    product_updated = True
                    
                except Product.DoesNotExist:
                    pass  # 상품이 없는 경우 이미지 URL만 반환
            
            return Response({
                "message": "이미지가 성공적으로 업로드되었습니다.",
                "image_url": image_url,
                "product_updated": product_updated,
                "product_id": product_id if product_updated else None
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"이미지 업로드 중 오류가 발생했습니다: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def update_product_image(self, request, pk=None):
        """
        특정 상품의 이미지를 업데이트하는 API
        
        request.data에 필요한 필드:
        - image: 업로드할 이미지 파일
        """
        try:
            # 상품 존재 여부 확인
            try:
                product = Product.objects.get(pk=pk)
            except Product.DoesNotExist:
                return Response({"error": "해당 상품을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
            
            # 이미지 파일 확인
            if 'image' not in request.FILES:
                return Response({"error": "이미지 파일이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
            
            image_file = request.FILES['image']
            
            # 이미지 파일 타입 검증
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return Response(
                    {"error": "지원되지 않는 이미지 형식입니다. JPEG, PNG, GIF, WEBP 형식만 허용됩니다."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 파일 크기 제한 (10MB)
            if image_file.size > 10 * 1024 * 1024:
                return Response(
                    {"error": "이미지 크기는 10MB를 초과할 수 없습니다."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 기존 이미지가 있는 경우 S3에서 삭제
            if product.image_url:
                delete_file_from_s3(product.image_url)
            
            # S3에 새 이미지 업로드
            image_url = upload_file_to_s3(image_file)
            
            if not image_url:
                return Response(
                    {"error": "이미지 업로드 중 오류가 발생했습니다."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 상품 이미지 URL 업데이트
            product.image_url = image_url
            product.save()
            
            return Response({
                "message": f"{product.name} 상품의 이미지가 성공적으로 업데이트되었습니다.",
                "product_id": product.id,
                "product_name": product.name,
                "image_url": image_url
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"이미지 업데이트 중 오류가 발생했습니다: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
