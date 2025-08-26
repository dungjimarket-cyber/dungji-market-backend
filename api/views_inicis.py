"""
이니시스 결제 관련 API 뷰
KG이니시스 표준결제 연동
"""

import hashlib
import json
import logging
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import User, BidToken
from api.models_payment import Payment

logger = logging.getLogger(__name__)


class InicisPaymentService:
    """이니시스 결제 서비스"""
    
    # 상점 정보 (테스트 환경)
    MID = 'INIpayTest'  # 테스트 상점 아이디
    SIGNKEY = 'SU5JTElURV9UUklQTEVERVNfS0VZU1RS'  # 테스트 서명키 (공식 샘플과 동일)
    
    # API URLs
    PROD_URL = 'https://iniapi.inicis.com/api/v1'
    TEST_URL = 'https://stginiapi.inicis.com/api/v1'
    
    @classmethod
    def get_api_url(cls):
        """환경에 따른 API URL 반환"""
        # 아직 계약 전이므로 항상 테스트 환경 사용
        return cls.TEST_URL
    
    @classmethod
    def generate_signature(cls, params):
        """
        이니시스 서명 생성
        SHA-256 해시 사용
        표준결제창 연동 규격에 따른 서명 생성
        """
        # 공식 샘플 기준 서명 생성
        oid = params.get('oid', '')
        price = params.get('price', '')
        timestamp = params.get('timestamp', '')
        
        # SHA-256 해시 데이터 - signature
        # signature = SHA256("oid=xxx&price=xxx&timestamp=xxx")
        signature_data = f"oid={oid}&price={price}&timestamp={timestamp}"
        signature = hashlib.sha256(signature_data.encode('utf-8')).hexdigest()
        
        return signature
    
    @classmethod
    def generate_mkey(cls, params):
        """
        이니시스 mkey 생성
        SHA-256 해시 사용
        """
        # mkey = SHA256(signKey)
        mkey = hashlib.sha256(cls.SIGNKEY.encode('utf-8')).hexdigest()
        return mkey
    
    @classmethod
    def generate_verification(cls, params):
        """
        이니시스 verification 생성
        SHA-256 해시 사용
        """
        # verification = SHA256("oid=xxx&price=xxx&signKey=xxx&timestamp=xxx")
        oid = params.get('oid', '')
        price = params.get('price', '')
        timestamp = params.get('timestamp', '')
        
        verification_data = f"oid={oid}&price={price}&signKey={cls.SIGNKEY}&timestamp={timestamp}"
        verification = hashlib.sha256(verification_data.encode('utf-8')).hexdigest()
        
        return verification


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prepare_inicis_payment(request):
    """
    이니시스 결제 준비
    결제창 호출에 필요한 서명과 파라미터 생성
    """
    try:
        user = request.user
        
        # 판매자만 입찰권 구매 가능
        if user.role != 'seller':
            return Response(
                {'error': '판매자만 입찰권을 구매할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 요청 데이터
        data = request.data
        order_id = data.get('orderId')
        amount = int(data.get('amount', 0))
        product_name = data.get('productName', '입찰권')
        buyer_name = data.get('buyerName', user.get_full_name() or user.username)
        buyer_tel = data.get('buyerTel', user.phone_number or '')
        buyer_email = data.get('buyerEmail', user.email)
        
        if amount <= 0:
            return Response(
                {'error': '결제 금액이 유효하지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 타임스탬프 생성
        timestamp = str(int(datetime.now().timestamp() * 1000))
        
        # 서명 생성을 위한 파라미터
        sign_params = {
            'mid': InicisPaymentService.MID,
            'oid': order_id,
            'price': str(amount),
            'timestamp': timestamp
        }
        
        # 서명 생성
        signature = InicisPaymentService.generate_signature(sign_params)
        mkey = InicisPaymentService.generate_mkey(sign_params)
        verification = InicisPaymentService.generate_verification(sign_params)
        
        # Payment 레코드 생성 (대기 상태)
        payment = Payment.objects.create(
            user=user,
            order_id=order_id,
            payment_method='inicis',
            amount=Decimal(str(amount)),
            status='pending',
            product_name=product_name,
            buyer_name=buyer_name,
            buyer_tel=buyer_tel,
            buyer_email=buyer_email,
            payment_data={
                'mid': InicisPaymentService.MID,
                'timestamp': timestamp,
                'signature': signature
            }
        )
        
        logger.info(f"이니시스 결제 준비 완료: user={user.id}, order_id={order_id}, amount={amount}")
        
        return Response({
            'success': True,
            'orderId': order_id,
            'timestamp': timestamp,
            'signature': signature,
            'mkey': mkey,
            'verification': verification,
            'payment_id': payment.id
        })
        
    except Exception as e:
        logger.error(f"이니시스 결제 준비 중 오류: {str(e)}")
        return Response(
            {'error': '결제 준비 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_inicis_payment(request):
    """
    이니시스 결제 검증
    결제 완료 후 결과 검증 및 처리
    """
    try:
        user = request.user
        data = request.data
        
        # 결제 결과 파라미터
        order_id = data.get('orderId')
        auth_result_code = data.get('authResultCode')
        auth_token = data.get('authToken')
        tid = data.get('tid')
        
        # Payment 레코드 조회
        try:
            payment = Payment.objects.get(order_id=order_id, user=user)
        except Payment.DoesNotExist:
            logger.error(f"결제 정보를 찾을 수 없음: order_id={order_id}, user={user.id}")
            return Response(
                {'error': '결제 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 이미 처리된 결제인지 확인
        if payment.status == 'completed':
            return Response({
                'success': True,
                'message': '이미 처리된 결제입니다.'
            })
        
        # 결제 성공 여부 확인
        if auth_result_code == '0000':
            # 결제 성공 처리
            with transaction.atomic():
                # Payment 업데이트
                payment.status = 'completed'
                # authToken이 너무 길므로 order_id를 tid로 사용
                payment.tid = order_id[:200]  # 200자 제한
                payment.completed_at = datetime.now()
                payment.payment_data.update({
                    'authToken': auth_token,  # 긴 토큰은 JSON 필드에 저장
                    'authResultCode': auth_result_code,
                    'originalTid': tid,
                    'authUrl': data.get('authUrl'),
                    'netCancelUrl': data.get('netCancelUrl'),
                    'idc_name': data.get('idc_name'),
                })
                payment.save()
                
                # 입찰권 지급 (10,000원당 1개)
                token_count = payment.amount // 10000
                if token_count > 0:
                    for _ in range(int(token_count)):
                        BidToken.objects.create(
                            user=user,
                            token_type='paid',
                            payment=payment,
                            description=f'이니시스 결제 ({order_id})'
                        )
                    
                    # 사용자 입찰권 개수 업데이트
                    user.bid_tokens += int(token_count)
                    user.save()
                
                logger.info(f"이니시스 결제 성공: user={user.id}, order_id={order_id}, amount={payment.amount}, tokens={token_count}")
            
            return Response({
                'success': True,
                'message': '결제가 완료되었습니다.',
                'token_count': int(token_count),
                'total_tokens': user.bid_tokens
            })
        else:
            # 결제 실패 처리
            payment.status = 'failed'
            payment.payment_data.update({
                'authResultCode': auth_result_code,
                'authToken': auth_token,  # 실패해도 토큰은 저장
                'failReason': data.get('authResultMsg', '결제 실패'),
                'authUrl': data.get('authUrl'),
                'netCancelUrl': data.get('netCancelUrl'),
                'idc_name': data.get('idc_name'),
            })
            payment.save()
            
            logger.warning(f"이니시스 결제 실패: user={user.id}, order_id={order_id}, code={auth_result_code}")
            
            return Response(
                {'error': '결제가 실패했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"이니시스 결제 검증 중 오류: {str(e)}")
        return Response(
            {'error': '결제 검증 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_inicis_payment(request):
    """
    이니시스 결제 취소
    """
    try:
        user = request.user
        data = request.data
        
        tid = data.get('tid')
        reason = data.get('reason', '구매자 요청')
        
        # Payment 레코드 조회
        try:
            payment = Payment.objects.get(tid=tid, user=user)
        except Payment.DoesNotExist:
            return Response(
                {'error': '결제 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 이미 취소된 결제인지 확인
        if payment.status == 'cancelled':
            return Response({
                'success': True,
                'message': '이미 취소된 결제입니다.'
            })
        
        # 결제 취소 처리
        with transaction.atomic():
            # 사용된 입찰권이 있는지 확인
            used_tokens = BidToken.objects.filter(
                payment=payment,
                is_used=True
            ).exists()
            
            if used_tokens:
                return Response(
                    {'error': '이미 사용된 입찰권이 있어 취소할 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 입찰권 제거
            token_count = BidToken.objects.filter(payment=payment).count()
            BidToken.objects.filter(payment=payment).delete()
            
            # 사용자 입찰권 개수 감소
            user.bid_tokens = max(0, user.bid_tokens - token_count)
            user.save()
            
            # Payment 상태 업데이트
            payment.status = 'cancelled'
            payment.cancelled_at = datetime.now()
            payment.cancel_reason = reason
            payment.save()
            
            logger.info(f"이니시스 결제 취소: user={user.id}, tid={tid}, tokens_removed={token_count}")
        
        return Response({
            'success': True,
            'message': '결제가 취소되었습니다.',
            'refunded_amount': int(payment.amount)
        })
        
    except Exception as e:
        logger.error(f"이니시스 결제 취소 중 오류: {str(e)}")
        return Response(
            {'error': '결제 취소 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
def inicis_webhook(request):
    """
    이니시스 웹훅 처리
    가상계좌 입금 등 비동기 이벤트 처리
    """
    try:
        data = request.data
        
        # 웹훅 타입 확인
        noti_type = data.get('type')
        
        if noti_type == 'vbank':
            # 가상계좌 입금 처리
            order_id = data.get('oid')
            tid = data.get('tid')
            
            try:
                payment = Payment.objects.get(order_id=order_id)
                
                if payment.status != 'completed':
                    with transaction.atomic():
                        # Payment 상태 업데이트
                        payment.status = 'completed'
                        payment.tid = tid
                        payment.completed_at = datetime.now()
                        payment.save()
                        
                        # 입찰권 지급
                        user = payment.user
                        token_count = payment.amount // 10000
                        
                        if token_count > 0:
                            for _ in range(int(token_count)):
                                BidToken.objects.create(
                                    user=user,
                                    token_type='paid',
                                    payment=payment,
                                    description=f'가상계좌 입금 ({order_id})'
                                )
                            
                            user.bid_tokens += int(token_count)
                            user.save()
                        
                        logger.info(f"가상계좌 입금 완료: order_id={order_id}, amount={payment.amount}")
                
            except Payment.DoesNotExist:
                logger.error(f"결제 정보를 찾을 수 없음: order_id={order_id}")
        
        return Response({'success': True})
        
    except Exception as e:
        logger.error(f"이니시스 웹훅 처리 중 오류: {str(e)}")
        return Response(
            {'error': '웹훅 처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
def inicis_return(request):
    """
    이니시스 결제 완료 후 리턴 URL
    """
    try:
        # GET/POST 파라미터 통합 처리
        params = request.GET.dict() if request.method == 'GET' else request.data
        
        # 결제 결과 파라미터
        result_code = params.get('resultCode')
        result_msg = params.get('resultMsg')
        order_id = params.get('merchantData', params.get('oid'))
        
        # 프론트엔드 리다이렉트 URL 생성
        frontend_url = settings.FRONTEND_URL or 'http://localhost:3000'
        
        if result_code == '00':
            # 성공
            redirect_url = f"{frontend_url}/mypage/seller/bid-tokens?payment=success&orderId={order_id}"
        else:
            # 실패
            redirect_url = f"{frontend_url}/mypage/seller/bid-tokens?payment=failed&msg={result_msg}"
        
        # HTML 응답으로 리다이렉트
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>결제 처리 중...</title>
        </head>
        <body>
            <script>
                window.location.href = '{redirect_url}';
            </script>
        </body>
        </html>
        """
        
        from django.http import HttpResponse
        return HttpResponse(html_response, content_type='text/html')
        
    except Exception as e:
        logger.error(f"이니시스 리턴 처리 중 오류: {str(e)}")
        return Response(
            {'error': '결제 처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
def inicis_close(request):
    """
    이니시스 결제창 닫기 처리
    """
    # 프론트엔드로 리다이렉트
    frontend_url = settings.FRONTEND_URL or 'http://localhost:3000'
    redirect_url = f"{frontend_url}/mypage/seller/bid-tokens?payment=cancelled"
    
    html_response = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>결제 취소</title>
    </head>
    <body>
        <script>
            window.location.href = '{redirect_url}';
        </script>
    </body>
    </html>
    """
    
    from django.http import HttpResponse
    return HttpResponse(html_response, content_type='text/html')