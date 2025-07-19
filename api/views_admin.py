from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import User
from .serializers import UserSerializer
from .utils.email_sender import send_email
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def pending_business_verifications(request):
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

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def approve_business_verification(request, user_id):
    """
    사업자 인증 승인
    """
    try:
        user = get_object_or_404(User, id=user_id, role='seller')
        
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
            send_email(
                to_email=user.email,
                subject='[둥지마켓] 사업자 인증이 승인되었습니다',
                template_name='business_verification_approved.html',
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

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def reject_business_verification(request, user_id):
    """
    사업자 인증 거절
    """
    try:
        user = get_object_or_404(User, id=user_id, role='seller')
        
        rejection_reason = request.data.get('reason', '사업자 정보 확인 불가')
        
        # 사업자 정보 초기화
        user.business_reg_number = None
        user.business_license_image = None
        user.is_business_verified = False
        user.save()
        
        # 이메일 알림 발송
        try:
            send_email(
                to_email=user.email,
                subject='[둥지마켓] 사업자 인증이 거절되었습니다',
                template_name='business_verification_rejected.html',
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

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_statistics(request):
    """
    관리자 대시보드용 통계 정보
    """
    try:
        from .models import GroupBuy, Bid, Product
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