"""
환불 관리 관련 API 뷰
"""

import hashlib
import json
import logging
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import generics

from .models_payment import Payment, RefundRequest
from .serializers_payment import (
    RefundRequestSerializer, 
    RefundRequestCreateSerializer, 
    RefundRequestAdminSerializer
)
from .views_inicis import InicisPaymentService

logger = logging.getLogger(__name__)


class RefundRequestListView(generics.ListCreateAPIView):
    """사용자 환불 요청 목록 및 생성"""
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RefundRequestCreateSerializer
        return RefundRequestSerializer
    
    def get_queryset(self):
        return RefundRequest.objects.filter(user=self.request.user)


class RefundRequestDetailView(generics.RetrieveAPIView):
    """환불 요청 상세 조회"""
    
    serializer_class = RefundRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RefundRequest.objects.filter(user=self.request.user)


class AdminRefundRequestListView(generics.ListAPIView):
    """관리자용 환불 요청 목록"""
    
    serializer_class = RefundRequestAdminSerializer
    permission_classes = [IsAdminUser]
    queryset = RefundRequest.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset.order_by('-created_at')


class AdminRefundRequestDetailView(generics.RetrieveUpdateAPIView):
    """관리자용 환불 요청 상세 및 처리"""
    
    serializer_class = RefundRequestAdminSerializer
    permission_classes = [IsAdminUser]
    queryset = RefundRequest.objects.all()


@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_refund_request(request, refund_id):
    """환불 요청 승인 및 이니시스 환불 처리"""
    
    try:
        with transaction.atomic():
            # 환불 요청 조회
            try:
                refund_request = RefundRequest.objects.select_for_update().get(id=refund_id)
            except RefundRequest.DoesNotExist:
                return Response(
                    {'error': '환불 요청을 찾을 수 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 이미 처리된 요청인지 확인
            if refund_request.status != 'pending':
                return Response(
                    {'error': '이미 처리된 환불 요청입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 환불 가능 여부 재확인
            can_refund, reason = refund_request.can_refund
            if not can_refund:
                return Response(
                    {'error': f'환불 불가: {reason}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            payment = refund_request.payment
            admin_note = request.data.get('admin_note', '')
            
            logger.info(f"=== 환불 승인 처리 시작 ===")
            logger.info(f"관리자: {request.user.username}, 환불 요청 ID: {refund_id}")
            logger.info(f"결제 정보: order_id={payment.order_id}, tid={payment.tid}, amount={payment.amount}")
            
            # 내부 시스템 환불 처리 (입찰권 사용 처리 및 상태 업데이트)
            try:
                # 해당 결제로 생성된 입찰권들을 찾아서 사용 처리
                from .models import BidToken
                
                # payment_order_id 필드가 없으므로 다른 방법으로 해당 결제의 입찰권을 찾아야 함
                # BidTokenPurchase를 통해서 찾거나, 결제 시점과 사용자를 기준으로 찾기
                bid_tokens = BidToken.objects.filter(
                    seller=payment.user,
                    status='active',
                    created_at__gte=payment.created_at - timezone.timedelta(minutes=5),
                    created_at__lte=payment.created_at + timezone.timedelta(minutes=5)
                ).order_by('-created_at')
                
                logger.info(f"환불 대상 입찰권 조회: 총 {bid_tokens.count()}개 발견")
                
                # 입찰권들을 만료 처리 (환불)
                tokens_processed = 0
                for token in bid_tokens:
                    if token.status == 'active' and not token.used_for:  # 아직 사용되지 않은 토큰만 처리
                        token.status = 'expired'  # 환불로 인한 만료 처리
                        token.used_at = timezone.now()
                        # 환불 사유를 기록하기 위해 used_for를 특별한 값으로 설정하지 않고 메모를 남김
                        token.save()
                        tokens_processed += 1
                        logger.info(f"입찰권 만료 처리 (환불): ID={token.id}, 만료일={token.expires_at}")
                
                # 만약 해당 결제에 대한 입찰권을 찾지 못했다면, 구매 내역을 통해 찾기
                if tokens_processed == 0:
                    from .models import BidTokenPurchase
                    
                    # 주문 ID로 구매 내역 찾기
                    try:
                        purchase = BidTokenPurchase.objects.get(order_id=payment.order_id)
                        # 해당 구매 시점 전후의 입찰권들을 찾아서 처리
                        bid_tokens_by_purchase = BidToken.objects.filter(
                            seller=payment.user,
                            status='active',
                            created_at__gte=purchase.purchase_date - timezone.timedelta(minutes=10),
                            created_at__lte=purchase.purchase_date + timezone.timedelta(minutes=10)
                        ).order_by('-created_at')[:purchase.quantity]
                        
                        for token in bid_tokens_by_purchase:
                            if token.status == 'active' and not token.used_for:
                                token.status = 'expired'
                                token.used_at = timezone.now()
                                token.save()
                                tokens_processed += 1
                                logger.info(f"구매 내역 기반 입찰권 만료 처리: ID={token.id}")
                                
                    except BidTokenPurchase.DoesNotExist:
                        logger.warning(f"주문 ID {payment.order_id}에 대한 구매 내역을 찾을 수 없음")
                
                # 환불 요청 상태 업데이트
                refund_request.status = 'approved'
                refund_request.admin_note = admin_note if admin_note else '관리자 승인'
                refund_request.processed_by = request.user
                refund_request.processed_at = timezone.now()
                refund_request.refund_amount = refund_request.request_amount
                refund_request.refund_method = 'internal'  # 내부 처리
                refund_request.refund_data = {
                    'tokens_processed': tokens_processed,
                    'processed_at': timezone.now().isoformat(),
                    'processed_by': request.user.username,
                    'payment_order_id': payment.order_id
                }
                refund_request.save()
                
                # 결제 정보 업데이트
                payment.status = 'refunded'
                payment.refund_amount = refund_request.request_amount
                payment.cancelled_at = timezone.now()
                payment.cancel_reason = f"환불 승인: {refund_request.reason}"
                payment.save()
                
                logger.info(f"환불 승인 완료: user={payment.user.id}, payment_id={payment.id}, amount={refund_request.request_amount}, tokens_processed={tokens_processed}")
                
                return Response({
                    'success': True,
                    'message': f'환불이 승인되어 처리되었습니다. (처리된 입찰권: {tokens_processed}개)',
                    'refund_amount': int(refund_request.request_amount),
                    'tokens_processed': tokens_processed
                })
                
            except Exception as internal_error:
                logger.error(f"내부 환불 처리 중 오류: {str(internal_error)}")
                
                # 내부 처리 실패 시 환불 요청을 거부 상태로 변경
                refund_request.status = 'rejected'
                refund_request.admin_note = f"내부 처리 오류: {str(internal_error)}"
                if admin_note:
                    refund_request.admin_note += f" (관리자 메모: {admin_note})"
                refund_request.processed_by = request.user
                refund_request.processed_at = timezone.now()
                refund_request.save()
                
                return Response({
                    'error': f"환불 처리 실패: {str(internal_error)}",
                    'message': '시스템 오류로 인해 환불 처리에 실패했습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
    except Exception as e:
        logger.error(f"환불 승인 처리 중 오류: {str(e)}")
        return Response(
            {'error': '환불 처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_refund_request(request, refund_id):
    """환불 요청 거부"""
    
    try:
        # 환불 요청 조회
        try:
            refund_request = RefundRequest.objects.get(id=refund_id)
        except RefundRequest.DoesNotExist:
            return Response(
                {'error': '환불 요청을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 이미 처리된 요청인지 확인
        if refund_request.status != 'pending':
            return Response(
                {'error': '이미 처리된 환불 요청입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        admin_note = request.data.get('admin_note', '')
        rejection_reason = request.data.get('reason', '관리자 판단')
        
        # 환불 요청 상태 업데이트
        refund_request.status = 'rejected'
        refund_request.admin_note = f"거부 사유: {rejection_reason}"
        if admin_note:
            refund_request.admin_note += f" (상세: {admin_note})"
        refund_request.processed_by = request.user
        refund_request.processed_at = timezone.now()
        refund_request.save()
        
        logger.info(f"환불 요청 거부: user={refund_request.user.id}, refund_id={refund_id}, reason={rejection_reason}")
        
        return Response({
            'success': True,
            'message': '환불 요청이 거부되었습니다.',
            'reason': rejection_reason
        })
        
    except Exception as e:
        logger.error(f"환불 요청 거부 처리 중 오류: {str(e)}")
        return Response(
            {'error': '환불 요청 처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# 이니시스 환불 함수들 제거 - 내부 시스템 처리로 변경됨


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_payments(request):
    """사용자 결제 내역 조회 (환불 가능한 결제 포함)"""
    
    try:
        user = request.user
        payments = Payment.objects.filter(user=user, status='completed').order_by('-created_at')
        
        payment_data = []
        for payment in payments:
            # 환불 요청이 이미 있는지 확인
            has_refund_request = RefundRequest.objects.filter(payment=payment).exists()
            
            # 환불 가능 여부 확인 (임시 RefundRequest 객체 생성해서 확인)
            temp_refund_request = RefundRequest(
                user=user,
                payment=payment,
                request_amount=payment.amount,
                reason="temp"
            )
            can_refund, reason = temp_refund_request.can_refund
            
            payment_data.append({
                'id': payment.id,
                'order_id': payment.order_id,
                'amount': payment.amount,
                'product_name': payment.product_name,
                'pay_method': payment.payment_method,
                'created_at': payment.created_at.isoformat() if payment.created_at else None,
                'can_refund': can_refund and not has_refund_request,
                'refund_deadline': (payment.completed_at + timedelta(days=7)).isoformat() if payment.completed_at else None,
                'has_refund_request': has_refund_request
            })
        
        return Response({
            'success': True,
            'payments': payment_data
        })
        
    except Exception as e:
        logger.error(f"사용자 결제 내역 조회 중 오류: {str(e)}")
        return Response(
            {'error': '결제 내역 조회 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )