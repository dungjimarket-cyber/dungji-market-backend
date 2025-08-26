"""
이니시스 결제 관련 뷰
"""
import hashlib
import json
import logging
import time
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User, BidToken, BidTokenPurchase
from .models_payment import Payment

logger = logging.getLogger(__name__)

# 이니시스 설정
INICIS_MID = 'dungjima14'  # 상점 아이디
INICIS_KEY = 'rKnPljRn5m6J9Mzz'  # 상점 키 (해시키 생성용)
INICIS_API_KEY = 'ekek*24641'  # API 키 (API 호출용)

# 이니시스 URL
INICIS_PAY_URL = 'https://stdpay.inicis.com' if not settings.DEBUG else 'https://stgstdpay.inicis.com'
INICIS_API_URL = 'https://api.inicis.com/v1' if not settings.DEBUG else 'https://stgapi.inicis.com/v1'


def generate_signature(params):
    """이니시스 서명 생성"""
    # 이니시스 표준: key + oid + price + timestamp + signKey 형태로 해시
    sign_param = f"{INICIS_KEY}{params['oid']}{params['price']}{params['timestamp']}{INICIS_KEY}"
    # SHA256 해시 생성
    signature = hashlib.sha256(sign_param.encode('utf-8')).hexdigest()
    return signature


def generate_mkey(mid):
    """이니시스 암호화 키 생성"""
    # MID + INICIS_KEY 해시
    mkey = hashlib.sha256(f"{mid}{INICIS_KEY}".encode('utf-8')).hexdigest()
    return mkey


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prepare_payment(request):
    """결제 준비 - 서명 생성"""
    try:
        user = request.user
        data = request.data
        
        # 필수 파라미터 검증
        required_fields = ['orderId', 'amount', 'productName', 'buyerName', 'buyerTel', 'buyerEmail']
        for field in required_fields:
            if field not in data:
                return Response(
                    {'error': f'{field}는 필수 항목입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 타임스탬프 생성
        timestamp = str(int(time.time() * 1000))
        
        # 서명 생성용 파라미터
        sign_params = {
            'oid': data['orderId'],
            'price': str(data['amount']),
            'timestamp': timestamp
        }
        
        # 서명 생성
        signature = generate_signature(sign_params)
        
        # 암호화 키 생성
        mkey = generate_mkey(INICIS_MID)
        
        # Payment 레코드 생성
        payment = Payment.objects.create(
            user=user,
            order_id=data['orderId'],
            amount=data['amount'],
            product_name=data['productName'],
            buyer_name=data['buyerName'],
            buyer_tel=data['buyerTel'],
            buyer_email=data['buyerEmail'],
            payment_method='inicis',
            status='pending'
        )
        
        return Response({
            'timestamp': timestamp,
            'signature': signature,
            'mkey': mkey,
            'paymentId': payment.id
        })
        
    except Exception as e:
        logger.error(f"Payment prepare error: {str(e)}")
        return Response(
            {'error': '결제 준비 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@require_http_methods(['POST'])
def payment_return(request):
    """결제 완료 후 리턴 URL"""
    try:
        # 이니시스로부터 받은 결과 파라미터
        result_code = request.POST.get('resultCode', '')
        result_msg = request.POST.get('resultMsg', '')
        mid = request.POST.get('mid', '')
        order_id = request.POST.get('orderid', '')
        amount = request.POST.get('amt', '')
        tid = request.POST.get('tid', '')
        
        # Payment 레코드 조회
        payment = Payment.objects.filter(order_id=order_id).first()
        
        if not payment:
            logger.error(f"Payment not found for order: {order_id}")
            return JsonResponse({'error': '결제 정보를 찾을 수 없습니다.'}, status=404)
        
        if result_code == '0000':
            # 결제 성공
            payment.status = 'completed'
            payment.tid = tid
            payment.completed_at = datetime.now()
            payment.save()
            
            # 비드 토큰 생성
            with transaction.atomic():
                user = payment.user
                # 금액에 따른 토큰 수 계산 (1만원당 1개 + 보너스)
                base_tokens = int(payment.amount / 10000)
                bonus_tokens = 0
                
                if payment.amount >= 100000:
                    bonus_tokens = int(base_tokens * 0.2)  # 20% 보너스
                elif payment.amount >= 50000:
                    bonus_tokens = int(base_tokens * 0.1)  # 10% 보너스
                
                total_tokens = base_tokens + bonus_tokens
                
                # BidToken 생성
                for _ in range(total_tokens):
                    BidToken.objects.create(
                        seller=user,
                        token_type='single',
                        status='active'
                    )
                
                # BidTokenPurchase 레코드 생성
                BidTokenPurchase.objects.create(
                    seller=user,
                    token_type='single',
                    quantity=total_tokens,
                    total_price=payment.amount,
                    payment_status='completed',
                    payment_date=datetime.now(),
                    order_id=order_id,
                    payment_key=tid
                )
            
            # 성공 페이지로 리다이렉트
            return JsonResponse({
                'success': True,
                'orderId': order_id,
                'amount': amount,
                'tokens': total_tokens
            })
            
        else:
            # 결제 실패
            payment.status = 'failed'
            payment.payment_data = {
                'error_code': result_code,
                'error_message': result_msg
            }
            payment.save()
            
            return JsonResponse({
                'success': False,
                'error': result_msg,
                'code': result_code
            })
            
    except Exception as e:
        logger.error(f"Payment return error: {str(e)}")
        return JsonResponse({
            'error': '결제 처리 중 오류가 발생했습니다.'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def payment_close(request):
    """결제창 닫기"""
    return JsonResponse({'message': '결제가 취소되었습니다.'})


@csrf_exempt
@require_http_methods(['POST'])
def payment_popup(request):
    """모바일 결제 팝업"""
    return JsonResponse({'message': '모바일 결제 진행 중'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """결제 검증"""
    try:
        data = request.data
        order_id = data.get('orderId')
        
        # Payment 레코드 조회
        payment = Payment.objects.filter(order_id=order_id).first()
        
        if not payment:
            return Response(
                {'error': '결제 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 이미 완료된 결제인지 확인
        if payment.status == 'completed':
            return Response({
                'success': True,
                'message': '이미 완료된 결제입니다.',
                'payment': {
                    'orderId': payment.order_id,
                    'amount': payment.amount,
                    'status': payment.status
                }
            })
        
        return Response({
            'success': False,
            'error': '결제가 완료되지 않았습니다.'
        })
            
    except Exception as e:
        logger.error(f"Payment verify error: {str(e)}")
        return Response(
            {'error': '결제 검증 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_payment(request):
    """결제 취소"""
    try:
        tid = request.data.get('tid')
        reason = request.data.get('reason', '구매자 요청')
        
        # Payment 레코드 조회
        payment = Payment.objects.filter(tid=tid).first()
        
        if not payment:
            return Response(
                {'error': '결제 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 권한 확인
        if payment.user != request.user:
            return Response(
                {'error': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # TODO: 실제 이니시스 API 호출하여 취소 처리
        
        # Payment 상태 업데이트
        payment.status = 'cancelled'
        payment.cancelled_at = datetime.now()
        payment.cancel_reason = reason
        payment.save()
        
        # BidTokenPurchase 업데이트
        purchase = BidTokenPurchase.objects.filter(order_id=payment.order_id).first()
        if purchase:
            purchase.payment_status = 'cancelled'
            purchase.save()
            
            # 해당 구매로 생성된 토큰 제거
            BidToken.objects.filter(
                seller=payment.user,
                created_at__date=purchase.purchase_date.date(),
                status='active'
            ).delete()
        
        return Response({
            'success': True,
            'message': '결제가 취소되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"Payment cancel error: {str(e)}")
        return Response(
            {'error': '결제 취소 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )