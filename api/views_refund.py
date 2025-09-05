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
            
            # 이니시스 환불 처리
            refund_response = process_inicis_refund(
                payment=payment,
                refund_amount=refund_request.request_amount,
                reason=refund_request.reason
            )
            
            if refund_response['success']:
                # 환불 요청 상태 업데이트
                refund_request.status = 'approved'
                refund_request.admin_note = admin_note
                refund_request.processed_by = request.user
                refund_request.processed_at = timezone.now()
                refund_request.refund_amount = refund_request.request_amount
                refund_request.refund_method = 'inicis'
                refund_request.refund_data = refund_response.get('data', {})
                refund_request.save()
                
                # 결제 정보 업데이트
                payment.status = 'refunded'
                payment.refund_amount = refund_request.request_amount
                payment.cancelled_at = timezone.now()
                payment.cancel_reason = f"환불 승인: {refund_request.reason}"
                payment.save()
                
                logger.info(f"환불 승인 완료: user={payment.user.id}, payment_id={payment.id}, amount={refund_request.request_amount}")
                
                return Response({
                    'success': True,
                    'message': '환불이 승인되어 처리되었습니다.',
                    'refund_amount': int(refund_request.request_amount)
                })
            else:
                # 이니시스 환불 실패
                refund_request.status = 'rejected'
                refund_request.admin_note = f"이니시스 환불 실패: {refund_response.get('error', '알 수 없는 오류')}"
                if admin_note:
                    refund_request.admin_note += f" (관리자 메모: {admin_note})"
                refund_request.processed_by = request.user
                refund_request.processed_at = timezone.now()
                refund_request.save()
                
                return Response({
                    'error': f"환불 처리 실패: {refund_response.get('error', '알 수 없는 오류')}",
                    'inicis_error': refund_response.get('inicis_error')
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


def process_inicis_refund(payment, refund_amount, reason):
    """이니시스 환불 처리"""
    
    try:
        # 환불 요청 파라미터 구성
        refund_params = {
            'mid': InicisPaymentService.MID,
            'tid': payment.tid,
            'msg': reason[:100],  # 환불 사유 (최대 100자)
        }
        
        # 부분환불인지 전액환불인지 확인
        if refund_amount < payment.amount:
            # 부분환불
            refund_params['price'] = int(refund_amount)
            api_endpoint = '/v2/pg/partialRefund'
        else:
            # 전액환불
            api_endpoint = '/v2/pg/refund'
        
        # 서명 생성
        signature_data = f"{refund_params['mid']}{refund_params['tid']}"
        if 'price' in refund_params:
            signature_data += str(refund_params['price'])
        signature_data += refund_params['msg']
        
        signature = hashlib.sha512(signature_data.encode('utf-8')).hexdigest()
        refund_params['hashData'] = signature
        
        # 이니시스 API 호출
        api_url = f"{InicisPaymentService.get_api_url()}{api_endpoint}"
        headers = {
            'Content-Type': 'application/json',
        }
        
        response = requests.post(api_url, json=refund_params, headers=headers, timeout=30)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('resultCode') == '00':
            logger.info(f"이니시스 환불 성공: tid={payment.tid}, amount={refund_amount}")
            return {
                'success': True,
                'data': response_data
            }
        else:
            error_msg = response_data.get('resultMsg', '알 수 없는 오류')
            logger.error(f"이니시스 환불 실패: tid={payment.tid}, error={error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'inicis_error': response_data
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"이니시스 API 호출 오류: {str(e)}")
        return {
            'success': False,
            'error': 'PG사 통신 오류가 발생했습니다.'
        }
    except Exception as e:
        logger.error(f"이니시스 환불 처리 중 오류: {str(e)}")
        return {
            'success': False,
            'error': '환불 처리 중 오류가 발생했습니다.'
        }


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