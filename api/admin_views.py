from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .permissions import IsAdminRole
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
import logging

from .models import GroupBuy, Bid, BidToken, Product, BidTokenAdjustmentLog, BidTokenPurchase
from .serializers import GroupBuySerializer
from .utils.s3_utils import upload_file_to_s3, delete_file_from_s3
from .utils.email_sender import EmailSender

User = get_user_model()
logger = logging.getLogger(__name__)

from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.middleware.csrf import get_token
import json

# 관리자 페이지용 UserSerializer 정의
class UserSerializer(serializers.ModelSerializer):
    active_tokens_count = serializers.SerializerMethodField()
    business_reg_number = serializers.CharField(read_only=True)
    business_license_image = serializers.URLField(read_only=True, allow_null=True)
    is_business_verified = serializers.BooleanField(read_only=True)
    actual_username = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'actual_username', 'nickname', 'email', 'role', 'active_tokens_count', 'date_joined', 'is_active',
                  'business_reg_number', 'business_license_image', 'is_business_verified']
        read_only_fields = ['date_joined', 'active_tokens_count']
    
    def get_active_tokens_count(self, obj):
        # 활성 상태이고 만료되지 않은 입찰권 수 계산
        return BidToken.objects.filter(
            seller=obj,
            status='active',
            expires_at__gt=timezone.now()
        ).count()
    
    def get_actual_username(self, obj):
        # 카카오 사용자의 경우 실제 username을 반환, 아니면 기존 username
        if hasattr(obj, 'sns_type') and obj.sns_type == 'kakao':
            # 카카오 사용자의 경우 kakao_ prefix가 있는 실제 ID 표시
            return obj.username if obj.username and obj.username.startswith('kakao_') else f'kakao_{obj.id}'
        return obj.username or obj.email.split('@')[0] if obj.email else '알 수 없음'

class AdminViewSet(viewsets.ViewSet):
    """
    관리자 전용 API를 위한 ViewSet
    
    관리자 권한이 필요한 기능들을 제공합니다.
    """
    permission_classes = [IsAdminRole]
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]
    
    def list(self, request):
        """기본 목록 엔드포인트"""
        return Response({"message": "관리자 API 엔드포인트"})
    
    def retrieve(self, request, pk=None):
        """기본 상세 엔드포인트"""
        return Response({"message": f"관리자 API 아이템 {pk}"})
    
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
    
    @action(detail=True, methods=['get'], url_path='seller-detail')
    def seller_detail(self, request, pk=None):
        """
        특정 셀러 사용자의 상세 정보를 반환하는 API
        URL: /api/admin/{pk}/seller-detail/
        """
        try:
            seller = User.objects.get(pk=pk, role='seller')
            serializer = UserSerializer(seller)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({"error": "셀러를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'], url_path='add-bid-permission')
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
                price_per_token = 59000  # 무제한 구독권 가격 (오픈기념 할인가)
            
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
                    
                    # 기존 이미지가 있는 경우 삭제
                    if product.image:
                        product.image.delete(save=False)
                    
                    # 새 이미지 파일로 업데이트
                    product.image = image_file
                    product.save()
                    product_updated = True
                    
                    # 실제 저장된 URL 가져오기
                    image_url = product.image.url if product.image else image_url
                    
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
    
    @action(detail=False, methods=['get'])
    def pending_business_verifications(self, request):
        """
        사업자 인증 대기중인 판매자 목록 조회
        """
        try:
            # 사업자 등록번호가 있지만 아직 인증되지 않은 판매자 조회
            pending_sellers = User.objects.filter(
                role='seller',
                business_reg_number__isnull=False,
                is_business_verified=False
            ).exclude(business_reg_number='').order_by('-date_joined')
            
            serializer = UserSerializer(pending_sellers, many=True)
            
            return Response({
                'count': pending_sellers.count(),
                'results': serializer.data
            })
        except Exception as e:
            logger.error(f"사업자 인증 대기 목록 조회 오류: {str(e)}")
            return Response(
                {'error': '목록 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def approve_business_verification(self, request, pk=None):
        """
        사업자 인증 승인
        """
        try:
            user = get_object_or_404(User, id=pk, role='seller')
            
            if user.is_business_verified:
                return Response(
                    {'error': '이미 인증된 사업자입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 사업자 인증 승인
            user.is_business_verified = True
            user.save()
            
            # 이메일 알림 발송
            try:
                EmailSender.send_notification_email(
                    recipient_email=user.email,
                    subject='[둥지마켓] 사업자 인증이 승인되었습니다',
                    template_name='emails/business_verification_approved.html',
                    context={
                        'user_name': user.first_name or user.username,
                    }
                )
            except Exception as e:
                logger.error(f"사업자 인증 승인 이메일 발송 실패: {str(e)}")
            
            return Response({
                'message': '사업자 인증이 승인되었습니다.',
                'user': UserSerializer(user).data
            })
            
        except Exception as e:
            logger.error(f"사업자 인증 승인 오류: {str(e)}")
            return Response(
                {'error': '승인 처리 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def reject_business_verification(self, request, pk=None):
        """
        사업자 인증 거절
        """
        try:
            user = get_object_or_404(User, id=pk, role='seller')
            
            rejection_reason = request.data.get('reason', '사업자 정보 확인 불가')
            
            # 사업자 정보 초기화
            user.business_reg_number = None
            user.business_license_image = None
            user.is_business_verified = False
            user.save()
            
            # 이메일 알림 발송
            try:
                EmailSender.send_notification_email(
                    recipient_email=user.email,
                    subject='[둥지마켓] 사업자 인증이 거절되었습니다',
                    template_name='emails/business_verification_rejected.html',
                    context={
                        'user_name': user.first_name or user.username,
                        'rejection_reason': rejection_reason
                    }
                )
            except Exception as e:
                logger.error(f"사업자 인증 거절 이메일 발송 실패: {str(e)}")
            
            return Response({
                'message': '사업자 인증이 거절되었습니다.',
                'user': UserSerializer(user).data
            })
            
        except Exception as e:
            logger.error(f"사업자 인증 거절 오류: {str(e)}")
            return Response(
                {'error': '거절 처리 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def upload_business_license(self, request, pk=None):
        """
        사업자등록증 이미지 업로드
        """
        try:
            user = get_object_or_404(User, id=pk, role='seller')
            
            # 이미지 파일 확인
            if 'business_license' not in request.FILES:
                return Response(
                    {'error': '사업자등록증 이미지 파일이 필요합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            image_file = request.FILES['business_license']
            
            # 이미지 파일 타입 검증
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return Response(
                    {'error': '지원되지 않는 이미지 형식입니다. JPEG, PNG, GIF, WEBP 형식만 허용됩니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 파일 크기 제한 (10MB)
            if image_file.size > 10 * 1024 * 1024:
                return Response(
                    {'error': '이미지 크기는 10MB를 초과할 수 없습니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 기존 이미지가 있으면 S3에서 삭제
            if user.business_license_image:
                try:
                    delete_file_from_s3(user.business_license_image)
                except Exception as e:
                    logger.warning(f"기존 사업자등록증 이미지 삭제 실패: {str(e)}")
            
            # S3에 새 이미지 업로드
            image_url = upload_file_to_s3(image_file)
            
            if not image_url:
                return Response(
                    {'error': '이미지 업로드 중 오류가 발생했습니다.'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 사용자 정보 업데이트
            user.business_license_image = image_url
            user.save()
            
            return Response({
                'message': '사업자등록증이 성공적으로 업로드되었습니다.',
                'user': UserSerializer(user).data,
                'business_license_image': image_url
            })
            
        except Exception as e:
            logger.error(f"사업자등록증 업로드 오류: {str(e)}")
            return Response(
                {'error': '업로드 처리 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        관리자 대시보드용 통계 정보
        """
        try:
            from django.db.models import Count, Sum, Avg
            
            # 사용자 통계
            total_users = User.objects.count()
            buyers = User.objects.filter(role='buyer').count()
            sellers = User.objects.filter(role='seller').count()
            verified_sellers = User.objects.filter(role='seller', is_business_verified=True).count()
            
            # 공구 통계
            total_groupbuys = GroupBuy.objects.count()
            active_groupbuys = GroupBuy.objects.filter(status__in=['recruiting', 'bidding']).count()
            completed_groupbuys = GroupBuy.objects.filter(status='completed').count()
            
            # 입찰 통계
            total_bids = Bid.objects.count()
            successful_bids = Bid.objects.filter(status='selected').count()
            
            return Response({
                'users': {
                    'total': total_users,
                    'buyers': buyers,
                    'sellers': sellers,
                    'verified_sellers': verified_sellers,
                    'pending_verifications': User.objects.filter(
                        role='seller',
                        business_reg_number__isnull=False,
                        is_business_verified=False
                    ).exclude(business_reg_number='').count()
                },
                'groupbuys': {
                    'total': total_groupbuys,
                    'active': active_groupbuys,
                    'completed': completed_groupbuys
                },
                'bids': {
                    'total': total_bids,
                    'successful': successful_bids,
                    'success_rate': round((successful_bids / total_bids * 100) if total_bids > 0 else 0, 2)
                }
            })
            
        except Exception as e:
            logger.error(f"관리자 통계 조회 오류: {str(e)}")
            return Response(
                {'error': '통계 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def sellers_with_details(self, request):
        """
        판매회원 목록 조회 (입찰권, 구독권 상태 포함)
        """
        try:
            from django.db.models import Count, Q, F
            from datetime import datetime
            
            sellers = User.objects.filter(role='seller').annotate(
                total_bid_tokens=Count('bid_tokens', filter=Q(bid_tokens__status='active')),
                single_tokens=Count('bid_tokens', filter=Q(bid_tokens__status='active', bid_tokens__token_type='single')),
                has_subscription=Count('bid_tokens', filter=Q(
                    bid_tokens__status='active',
                    bid_tokens__token_type='unlimited',
                    bid_tokens__expires_at__gt=timezone.now()
                ))
            ).order_by('-date_joined')
            
            sellers_data = []
            for seller in sellers:
                # 구독권 상태 확인
                active_subscription = BidToken.objects.filter(
                    seller=seller,
                    token_type='unlimited',
                    status='active',
                    expires_at__gt=timezone.now()
                ).first()
                
                # 실제 사용자 이름 결정 (카카오 사용자 처리)
                actual_username = seller.username
                if hasattr(seller, 'sns_type') and seller.sns_type == 'kakao':
                    actual_username = seller.username if seller.username and seller.username.startswith('kakao_') else f'kakao_{seller.id}'
                elif not seller.username:
                    actual_username = seller.email.split('@')[0] if seller.email else '알 수 없음'
                
                sellers_data.append({
                    'id': seller.id,
                    'username': seller.username,
                    'actual_username': actual_username,
                    'nickname': seller.nickname,
                    'email': seller.email,
                    'bid_tokens_count': seller.single_tokens,
                    'has_subscription': bool(active_subscription),
                    'subscription_expires_at': active_subscription.expires_at if active_subscription else None,
                    'is_business_verified': seller.is_business_verified,
                    'date_joined': seller.date_joined
                })
            
            return Response(sellers_data)
            
        except Exception as e:
            logger.error(f"판매회원 목록 조회 오류: {str(e)}")
            return Response(
                {'error': '판매회원 목록 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def seller_detail(self, request, pk=None):
        """
        특정 판매회원 상세 정보 조회
        """
        try:
            seller = get_object_or_404(User, id=pk, role='seller')
            
            # 입찰권 정보
            active_tokens = BidToken.objects.filter(
                seller=seller,
                status='active'
            )
            single_tokens_count = active_tokens.filter(token_type='single').count()
            
            # 구독권 정보
            active_subscription = active_tokens.filter(
                token_type='unlimited',
                expires_at__gt=timezone.now()
            ).first()
            
            # 입찰권 사용 이력
            used_tokens = BidToken.objects.filter(
                seller=seller,
                status='used'
            ).order_by('-updated_at')[:20]  # 최근 20개
            
            # 구매 내역
            purchases = BidTokenPurchase.objects.filter(
                seller=seller,
                payment_status='completed'
            ).order_by('-payment_date')[:20]  # 최근 20개
            
            # 조정 이력
            adjustment_logs = BidTokenAdjustmentLog.objects.filter(
                seller=seller
            ).order_by('-created_at')[:20]  # 최근 20개
            
            return Response({
                'seller': {
                    'id': seller.id,
                    'username': seller.username,
                    'nickname': seller.nickname,
                    'email': seller.email,
                    'phone_number': seller.phone_number,
                    'is_business_verified': seller.is_business_verified,
                    'business_reg_number': seller.business_reg_number,
                    'date_joined': seller.date_joined
                },
                'tokens': {
                    'single_tokens_count': single_tokens_count,
                    'has_subscription': bool(active_subscription),
                    'subscription_expires_at': active_subscription.expires_at if active_subscription else None
                },
                'usage_history': [
                    {
                        'id': token.id,
                        'used_at': token.updated_at,
                        'bid_id': token.bid.id if hasattr(token, 'bid') else None
                    } for token in used_tokens
                ],
                'purchase_history': [
                    {
                        'id': purchase.id,
                        'token_type': purchase.token_type,
                        'quantity': purchase.quantity,
                        'total_price': purchase.total_price,
                        'payment_date': purchase.payment_date
                    } for purchase in purchases
                ],
                'adjustment_logs': [
                    {
                        'id': log.id,
                        'adjustment_type': log.adjustment_type,
                        'quantity': log.quantity,
                        'reason': log.reason,
                        'admin_username': log.admin.username if log.admin else 'System',
                        'created_at': log.created_at
                    } for log in adjustment_logs
                ]
            })
            
        except Exception as e:
            logger.error(f"판매회원 상세 조회 오류: {str(e)}")
            return Response(
                {'error': '판매회원 정보 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def adjust_bid_tokens(self, request, pk=None):
        """
        판매회원 입찰권 추가/차감
        """
        try:
            seller = get_object_or_404(User, id=pk, role='seller')
            
            adjustment_type = request.data.get('adjustment_type')  # 'add' or 'subtract'
            quantity = request.data.get('quantity', 0)
            reason = request.data.get('reason', '')
            
            # 유효성 검증
            if adjustment_type not in ['add', 'subtract']:
                return Response(
                    {'error': '유효하지 않은 조정 유형입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not isinstance(quantity, int) or quantity <= 0:
                return Response(
                    {'error': '유효한 수량을 입력해주세요.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not reason:
                return Response(
                    {'error': '조정 사유를 입력해주세요.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 차감 시 보유 수량 확인
            if adjustment_type == 'subtract':
                active_tokens_count = BidToken.objects.filter(
                    seller=seller,
                    status='active',
                    token_type='single'
                ).count()
                
                if active_tokens_count < quantity:
                    return Response(
                        {'error': f'보유 입찰권이 부족합니다. (보유: {active_tokens_count}개)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # 입찰권 차감
                tokens_to_deactivate = BidToken.objects.filter(
                    seller=seller,
                    status='active',
                    token_type='single'
                )[:quantity]
                
                for token in tokens_to_deactivate:
                    token.status = 'expired'
                    token.save()
            else:
                # 입찰권 추가
                for _ in range(quantity):
                    BidToken.objects.create(
                        seller=seller,
                        token_type='single',
                        status='active'
                    )
            
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type=adjustment_type,
                quantity=quantity,
                reason=reason
            )
            
            # 현재 활성 입찰권 수 계산
            active_tokens_count = BidToken.objects.filter(
                seller=seller,
                status='active',
                token_type='single'
            ).count()
            
            return Response({
                'message': f'입찰권이 성공적으로 {"추가" if adjustment_type == "add" else "차감"}되었습니다.',
                'seller_id': seller.id,
                'adjustment_type': adjustment_type,
                'quantity': quantity,
                'current_tokens_count': active_tokens_count
            })
            
        except Exception as e:
            logger.error(f"입찰권 조정 오류: {str(e)}")
            return Response(
                {'error': '입찰권 조정 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def grant_subscription(self, request, pk=None):
        """
        판매회원에게 구독권 부여
        """
        try:
            from datetime import timedelta
            
            seller = get_object_or_404(User, id=pk, role='seller')
            
            duration_days = request.data.get('duration_days', 30)
            reason = request.data.get('reason', '')
            
            if not isinstance(duration_days, int) or duration_days <= 0:
                return Response(
                    {'error': '유효한 기간을 입력해주세요.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not reason:
                return Response(
                    {'error': '부여 사유를 입력해주세요.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 기존 구독권 만료 처리
            BidToken.objects.filter(
                seller=seller,
                token_type='unlimited',
                status='active'
            ).update(status='expired')
            
            # 새 구독권 생성
            expires_at = timezone.now() + timedelta(days=duration_days)
            subscription = BidToken.objects.create(
                seller=seller,
                token_type='unlimited',
                status='active',
                expires_at=expires_at
            )
            
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='grant_subscription',
                quantity=duration_days,
                reason=reason
            )
            
            return Response({
                'message': f'{duration_days}일 구독권이 성공적으로 부여되었습니다.',
                'seller_id': seller.id,
                'subscription_id': subscription.id,
                'expires_at': expires_at
            })
            
        except Exception as e:
            logger.error(f"구독권 부여 오류: {str(e)}")
            return Response(
                {'error': '구독권 부여 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@csrf_exempt
@require_http_methods(["POST"])
def adjust_user_bid_tokens(request, user_id):
    """개별 사용자의 견적 티켓 조정 API (Django Admin 페이지용)"""
    
    logger.info(f"견적 티켓 조정 요청 - User ID: {user_id}, Request User: {request.user}")
    
    # 수동으로 인증 체크 (302 리다이렉트 방지)
    if not request.user.is_authenticated:
        return JsonResponse(
            {'success': False, 'error': '로그인이 필요합니다.'}, 
            status=401,
            json_dumps_params={'ensure_ascii': False}
        )
    
    if not request.user.is_staff:
        return JsonResponse(
            {'success': False, 'error': '관리자 권한이 필요합니다.'}, 
            status=403,
            json_dumps_params={'ensure_ascii': False}
        )
    
    try:
        # 사용자 확인
        try:
            user = User.objects.get(id=user_id, role='seller')
        except User.DoesNotExist:
            logger.warning(f"판매자를 찾을 수 없음: ID {user_id}")
            response = JsonResponse(
                {'success': False, 'error': f'ID {user_id}의 판매자를 찾을 수 없습니다.'}, 
                json_dumps_params={'ensure_ascii': False}
            )
            response['Content-Type'] = 'application/json; charset=utf-8'
            return response
        
        # 요청 데이터 파싱
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'success': False, 'error': '잘못된 JSON 형식입니다.'}, 
                status=400,
                json_dumps_params={'ensure_ascii': False}
            )
        
        adjustment_type = data.get('adjustment_type')  # 'add', 'subtract', 'set'
        quantity = int(data.get('quantity', 0))
        reason = data.get('reason', '관리자 수동 조정')
        
        if not all([adjustment_type, quantity >= 0]):
            return JsonResponse(
                {'success': False, 'error': '필수 정보가 누락되었습니다.'}, 
                json_dumps_params={'ensure_ascii': False}
            )
        
        if adjustment_type not in ['add', 'subtract', 'set']:
            return JsonResponse(
                {'success': False, 'error': '잘못된 조정 유형입니다.'}, 
                json_dumps_params={'ensure_ascii': False}
            )
        
        # 현재 활성 토큰 수 확인
        current_tokens = BidToken.objects.filter(
            seller=user,
            status='active',
            token_type='single'
        ).count()
        
        if adjustment_type == 'add':
            # 티켓 추가
            for _ in range(quantity):
                BidToken.objects.create(
                    seller=user,
                    token_type='single',
                    status='active'
                )
            message = f'{quantity}개의 견적 티켓이 추가되었습니다.'
            
        elif adjustment_type == 'subtract':
            # 티켓 차감
            if quantity > current_tokens:
                return JsonResponse({
                    'success': False, 
                    'error': f'활성 토큰이 {current_tokens}개만 있습니다. {quantity}개를 차감할 수 없습니다.'
                }, json_dumps_params={'ensure_ascii': False})
            
            tokens_to_remove = BidToken.objects.filter(
                seller=user,
                status='active',
                token_type='single'
            ).order_by('created_at')[:quantity]
            
            for token in tokens_to_remove:
                token.status = 'expired'
                token.expires_at = timezone.now()
                token.save()
            
            message = f'{quantity}개의 견적 티켓이 차감되었습니다.'
            
        elif adjustment_type == 'set':
            # 티켓 개수 설정
            if quantity > current_tokens:
                # 부족한 만큼 추가
                for _ in range(quantity - current_tokens):
                    BidToken.objects.create(
                        seller=user,
                        token_type='single',
                        status='active'
                    )
            elif quantity < current_tokens:
                # 초과한 만큼 제거
                tokens_to_remove = BidToken.objects.filter(
                    seller=user,
                    status='active',
                    token_type='single'
                ).order_by('created_at')[:current_tokens - quantity]
                
                for token in tokens_to_remove:
                    token.status = 'expired'
                    token.expires_at = timezone.now()
                    token.save()
            
            message = f'견적 티켓이 {quantity}개로 설정되었습니다.'
        
        # 조정 이력 기록
        BidTokenAdjustmentLog.objects.create(
            seller=user,
            admin=request.user,
            adjustment_type=adjustment_type,
            quantity=quantity,
            reason=reason
        )
        
        # 현재 토큰 상태 조회
        updated_tokens = BidToken.objects.filter(
            seller=user,
            status='active',
            token_type='single'
        ).count()
        
        response = JsonResponse({
            'success': True,
            'message': message,
            'current_tokens': updated_tokens,
            'previous_tokens': current_tokens
        }, json_dumps_params={'ensure_ascii': False})
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response
        
    except User.DoesNotExist:
        response = JsonResponse({'success': False, 'error': '사용자를 찾을 수 없습니다.'}, json_dumps_params={'ensure_ascii': False})
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response
    except Exception as e:
        logger.error(f"견적 티켓 조정 오류: {str(e)}")
        response = JsonResponse({'success': False, 'error': f'처리 중 오류가 발생했습니다: {str(e)}'}, json_dumps_params={'ensure_ascii': False})
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response


# 프론트엔드에서 기대하는 개별 API 엔드포인트들
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminRole])
def get_seller_detail(request, seller_id):
    """
    특정 셀러 상세 정보 조회 API
    URL: /api/admin/sellers/{seller_id}/
    """
    try:
        seller = User.objects.get(pk=seller_id, role='seller')
        serializer = UserSerializer(seller)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({"error": "셀러를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"셀러 상세 조회 오류: {str(e)}")
        return Response({"error": "서버 오류가 발생했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminRole])
def add_bid_permission_endpoint(request, user_id):
    """
    특정 사용자에게 입찰권 추가 API
    URL: /api/admin/add_bid_permission/{user_id}/
    """
    try:
        from datetime import timedelta
        from django.utils import timezone
        from api.models import BidToken, BidTokenPurchase
        
        user = User.objects.get(pk=user_id)
        
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
        
        # 입찰권 생성
        created_tokens = []
        for _ in range(bid_count):
            token = BidToken.objects.create(
                seller=user,
                token_type=token_type,
                status='active',
                expires_at=timezone.now() + timedelta(days=365 if token_type == 'unlimited' else 30)
            )
            created_tokens.append(token)
        
        logger.info(f"관리자 {request.user.username}가 사용자 {user.username}에게 {token_type} 입찰권 {bid_count}개 부여")
        
        return Response({
            "message": f"{user.nickname or user.username}에게 {token_type} 입찰권 {bid_count}개를 성공적으로 부여했습니다.",
            "created_tokens": len(created_tokens)
        }, status=status.HTTP_201_CREATED)
        
    except User.DoesNotExist:
        return Response({"error": "사용자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"입찰권 부여 오류: {str(e)}")
        return Response({"error": "서버 오류가 발생했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminRole])
def get_seller_detail_with_full_info(request, seller_id):
    """
    판매자 상세 정보를 토큰, 이력 정보와 함께 조회
    URL: /api/admin/sellers/{seller_id}/
    """
    try:
        from api.models import BidToken, BidTokenPurchase, BidTokenUsage, BidTokenAdjustmentLog
        
        seller = User.objects.get(pk=seller_id, role='seller')
        
        # 기본 정보
        data = {
            'id': seller.id,
            'username': seller.username,
            'actual_username': seller.username,
            'nickname': seller.nickname or seller.username,
            'email': seller.email,
            'phone_number': seller.phone_number,
            'seller_category': getattr(seller, 'seller_category', None),
            'is_business_verified': seller.is_business_verified,
            'business_reg_number': seller.business_reg_number or '--',
            'business_license_image': seller.business_license_image.url if seller.business_license_image else None,
            'date_joined': seller.date_joined.isoformat(),
            'role': seller.role,
            'is_active': seller.is_active,
            'active_tokens_count': BidToken.objects.filter(seller=seller, status='active', token_type='single').count(),
        }
        
        # 토큰 정보
        active_subscription = BidToken.objects.filter(
            seller=seller,
            status='active',
            token_type='unlimited'
        ).order_by('-expires_at').first()
        
        data['tokens'] = {
            'single_tokens_count': BidToken.objects.filter(seller=seller, status='active', token_type='single').count(),
            'has_subscription': bool(active_subscription),
            'subscription_expires_at': active_subscription.expires_at.isoformat() if active_subscription else None
        }
        
        # 사용 이력 (최근 20건)
        usage_history = BidTokenUsage.objects.filter(
            token__seller=seller
        ).select_related('bid').order_by('-used_at')[:20]
        
        data['usage_history'] = [
            {
                'id': usage.id,
                'used_at': usage.used_at.isoformat(),
                'bid_id': usage.bid.id if usage.bid else None
            }
            for usage in usage_history
        ]
        
        # 구매 내역 (최근 20건)
        purchase_history = BidTokenPurchase.objects.filter(
            seller=seller
        ).order_by('-payment_date')[:20]
        
        data['purchase_history'] = [
            {
                'id': purchase.id,
                'token_type': purchase.token_type,
                'quantity': purchase.quantity,
                'total_price': float(purchase.total_price),
                'payment_date': purchase.payment_date.isoformat()
            }
            for purchase in purchase_history
        ]
        
        # 조정 이력 (최근 20건)
        adjustment_logs = BidTokenAdjustmentLog.objects.filter(
            seller=seller
        ).select_related('admin').order_by('-created_at')[:20]
        
        data['adjustment_logs'] = [
            {
                'id': log.id,
                'adjustment_type': log.adjustment_type,
                'quantity': log.quantity,
                'reason': log.reason,
                'admin_username': log.admin.username if log.admin else 'System',
                'created_at': log.created_at.isoformat()
            }
            for log in adjustment_logs
        ]
        
        return Response(data)
        
    except User.DoesNotExist:
        return Response({"error": "판매자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"판매자 상세 조회 오류: {str(e)}")
        return Response({"error": "서버 오류가 발생했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminRole])
def adjust_bid_tokens(request):
    """
    견적티켓 조정 API
    URL: /api/admin/bid-tokens/adjust/
    """
    try:
        from api.models import BidToken, BidTokenAdjustmentLog
        
        seller_id = request.data.get('seller_id')
        action = request.data.get('action')  # 'add' or 'subtract'
        amount = request.data.get('amount')
        reason = request.data.get('reason')
        
        if not all([seller_id, action, amount, reason]):
            return Response({'error': '필수 정보가 누락되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        seller = User.objects.get(pk=seller_id, role='seller')
        
        if action == 'add':
            # 토큰 추가
            for _ in range(amount):
                BidToken.objects.create(
                    seller=seller,
                    token_type='single',
                    status='active'
                )
            adjustment_type = 'add'
            message = f'견적티켓 {amount}개가 추가되었습니다.'
            
        elif action == 'subtract':
            # 토큰 차감
            active_tokens = BidToken.objects.filter(
                seller=seller,
                status='active',
                token_type='single'
            ).order_by('created_at')[:amount]
            
            if active_tokens.count() < amount:
                return Response({'error': '차감할 견적티켓이 부족합니다.'}, status=status.HTTP_400_BAD_REQUEST)
            
            for token in active_tokens:
                token.status = 'expired'
                token.save()
            
            adjustment_type = 'subtract'
            message = f'견적티켓 {amount}개가 차감되었습니다.'
        else:
            return Response({'error': '유효하지 않은 작업입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 조정 이력 기록
        BidTokenAdjustmentLog.objects.create(
            seller=seller,
            admin=request.user,
            adjustment_type=adjustment_type,
            quantity=amount,
            reason=reason
        )
        
        return Response({'message': message})
        
    except User.DoesNotExist:
        return Response({'error': '판매자를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"견적티켓 조정 오류: {str(e)}")
        return Response({'error': '서버 오류가 발생했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminRole])
def search_users(request):
    """
    사용자 검색 API (관리자용)
    URL: /api/admin/users/search/
    """
    try:
        from django.db.models import Q
        
        search_term = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 20)), 100)  # 최대 100개
        
        if not search_term:
            return Response({
                'results': [],
                'count': 0,
                'message': '검색어를 입력해주세요.'
            })
        
        # 기본 검색 조건
        search_q = Q()
        
        # 이름/닉네임 검색
        search_q |= Q(username__icontains=search_term)
        search_q |= Q(nickname__icontains=search_term)
        search_q |= Q(first_name__icontains=search_term)
        search_q |= Q(last_name__icontains=search_term)
        search_q |= Q(representative_name__icontains=search_term)
        
        # 이메일 검색
        search_q |= Q(email__icontains=search_term)
        
        # 전화번호 검색 (하이픈 제거)
        clean_phone = search_term.replace('-', '').replace(' ', '')
        if clean_phone.isdigit():
            search_q |= Q(phone_number__icontains=clean_phone)
        
        # 사업자번호 검색 (하이픈 제거)
        clean_business = search_term.replace('-', '').replace(' ', '')
        if clean_business.isdigit() and len(clean_business) >= 10:
            search_q |= Q(business_number__icontains=clean_business)
        
        # ID로 직접 검색
        if search_term.isdigit():
            search_q |= Q(id=int(search_term))
        
        # SNS 사용자 검색
        if 'kakao' in search_term.lower() or 'google' in search_term.lower():
            search_q |= Q(sns_type__icontains=search_term)
        
        # 검색 실행
        users = User.objects.filter(search_q).distinct().order_by('-date_joined')[:limit]
        
        # 결과 준비
        results = []
        for user in users:
            # 사용자 대시 이름 결정
            display_name = user.nickname or user.get_full_name() or user.username
            if user.sns_type:
                display_name += f" ({user.sns_type})"
            
            # 사업자 정보 추가
            business_info = ''
            if user.role == 'seller':
                if user.business_number:
                    business_info += f" | 사업자: {user.business_number}"
                if user.is_business_verified:
                    business_info += " ✓"
            
            results.append({
                'id': user.id,
                'text': f"{display_name} ({user.email}){business_info}",
                'username': user.username,
                'email': user.email,
                'nickname': user.nickname,
                'role': user.role,
                'is_business_verified': user.is_business_verified if user.role == 'seller' else None,
                'phone_number': user.phone_number,
                'date_joined': user.date_joined.strftime('%Y-%m-%d')
            })
        
        return Response({
            'results': results,
            'count': len(results),
            'total_count': User.objects.filter(search_q).count() if len(results) == limit else len(results),
            'has_more': len(results) == limit
        })
        
    except Exception as e:
        logger.error(f"사용자 검색 오류: {str(e)}")
        return Response(
            {'error': '검색 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminRole])
def grant_subscription(request):
    """
    구독권 부여 API
    URL: /api/admin/bid-tokens/grant-subscription/
    """
    try:
        from datetime import timedelta
        from django.utils import timezone
        from api.models import BidToken, BidTokenAdjustmentLog
        
        seller_id = request.data.get('seller_id')
        days = request.data.get('days')
        reason = request.data.get('reason')
        
        if not all([seller_id, days, reason]):
            return Response({'error': '필수 정보가 누락되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        seller = User.objects.get(pk=seller_id, role='seller')
        
        # 기존 활성 구독권 비활성화
        BidToken.objects.filter(
            seller=seller,
            token_type='unlimited',
            status='active'
        ).update(status='expired')
        
        # 새 구독권 생성
        expires_at = timezone.now() + timedelta(days=days)
        BidToken.objects.create(
            seller=seller,
            token_type='unlimited',
            status='active',
            expires_at=expires_at
        )
        
        # 조정 이력 기록
        BidTokenAdjustmentLog.objects.create(
            seller=seller,
            admin=request.user,
            adjustment_type='grant_subscription',
            quantity=days,
            reason=reason
        )
        
        return Response({
            'message': f'{days}일 구독권이 부여되었습니다.',
            'expires_at': expires_at.isoformat()
        })
        
    except User.DoesNotExist:
        return Response({'error': '판매자를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"구독권 부여 오류: {str(e)}")
        return Response({'error': '서버 오류가 발생했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
