"""
이니시스 결제 관련 API 뷰
KG이니시스 표준결제 연동
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import User, BidToken, BidTokenPurchase
from api.models_payment import Payment

logger = logging.getLogger(__name__)


class InicisPaymentService:
    """이니시스 결제 서비스"""
    
    # 상점 정보 (운영 환경)
    MID = 'dungjima14'  # 실제 상점 아이디
    SIGNKEY = 'MzVBZ0hzWU5kOXpnQUczclRIR2dMdz09'  # 웹결제 사인키
    API_KEY = 'yT5fxdUqycph7JBJ'  # INIAPI key
    API_IV = 'KvDu7eNXGotbaV=='  # INIAPI iv
    MOBILE_HASHKEY = 'D1EEF4CE7B4D9B1795BBFD255D35FE24'  # 모바일 hashkey
    
    # API URLs
    PROD_URL = 'https://iniapi.inicis.com/api/v1'
    TEST_URL = 'https://stginiapi.inicis.com/api/v1'
    
    @classmethod
    def get_api_url(cls):
        """환경에 따른 API URL 반환"""
        # 실제 운영 환경 사용
        return cls.PROD_URL
    
    @classmethod
    def mobile_payment_approval(cls, auth_url, auth_token):
        """
        이니시스 모바일 결제 승인 요청
        인증 후 실제 결제 승인 처리
        """
        try:
            import requests
            import urllib.parse
            from datetime import datetime
            
            logger.info(f"이니시스 모바일 승인 요청 시작")
            
            # authToken 정리 (줄바꿈 제거 및 hAsH 부분 처리)
            clean_auth_token = auth_token
            if 'hAsH:' in auth_token:
                # hAsH: 부분 제거 (이니시스 내부 해시값으로 추정)
                clean_auth_token = auth_token.split('hAsH:')[0]
                logger.info(f"authToken에서 hAsH 부분 제거: 원래 길이 {len(auth_token)} -> 정리 후 {len(clean_auth_token)}")
            
            # 줄바꿈 문자 제거
            clean_auth_token = clean_auth_token.replace('\r\n', '').replace('\r', '').replace('\n', '')
            
            logger.info(f"정리된 authToken 길이: {len(clean_auth_token)}")
            logger.info(f"정리된 authToken 앞부분: {clean_auth_token[:50]}...")
            
            # 승인 요청 데이터 (이니시스 API 스펙에 맞춤)
            # 표준 승인 API에 필요한 최소 파라미터만 사용
            approval_data = {
                'mid': cls.MID,
                'authToken': clean_auth_token
            }
            
            # URL 인코딩
            encoded_data = urllib.parse.urlencode(approval_data)
            
            logger.info(f"승인 요청 URL: {auth_url}")
            logger.info(f"승인 요청 데이터: {approval_data}")
            logger.info(f"URL 인코딩된 데이터: {encoded_data}")
            
            # 승인 API 호출
            response = requests.post(
                auth_url,
                data=encoded_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'charset': 'UTF-8'
                },
                timeout=30
            )
            
            logger.info(f"승인 응답 상태: {response.status_code}")
            logger.info(f"승인 응답 전체: {response.text}")
            
            if response.status_code == 200:
                # 응답 파싱
                result_params = {}
                
                # XML 응답인 경우 먼저 확인 (이니시스는 주로 XML 응답)
                if response.text.strip().startswith('<?xml'):
                    try:
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(response.text)
                        
                        # XML에서 필드 추출
                        for elem in root:
                            result_params[elem.tag] = elem.text
                        
                        logger.info(f"승인 결과 (XML): {result_params}")
                    except Exception as xml_error:
                        logger.error(f"XML 파싱 오류: {xml_error}")
                        logger.error(f"XML 응답 내용: {response.text}")
                        return None
                else:
                    # JSON 응답인 경우
                    try:
                        import json
                        result_params = json.loads(response.text)
                        logger.info(f"승인 결과 (JSON): {result_params}")
                    except json.JSONDecodeError:
                        # URL 인코딩된 응답인 경우
                        for pair in response.text.split('&'):
                            if '=' in pair:
                                key, value = pair.split('=', 1)
                                result_params[key] = urllib.parse.unquote(value)
                        logger.info(f"승인 결과 (URL-encoded): {result_params}")
                
                return result_params
            else:
                logger.error(f"승인 API 오류: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"이니시스 모바일 승인 요청 실패: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
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
        logger.info(f"=== 이니시스 결제 준비 시작 ===")
        logger.info(f"요청 사용자: ID={user.id}, 역할={user.role}")
        
        # 판매자만 입찰권 구매 가능
        if user.role != 'seller':
            logger.error(f"권한 오류: 사용자 역할 {user.role}은 판매자가 아님")
            return Response(
                {'error': '판매자만 입찰권을 구매할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 요청 데이터
        data = request.data
        logger.info(f"요청 데이터: {data}")
        
        order_id = data.get('orderId')
        amount = int(data.get('amount', 0))
        product_name = data.get('productName', '입찰권')
        buyer_name = data.get('buyerName', user.get_full_name() or user.username)
        buyer_tel = data.get('buyerTel', user.phone_number or '')
        buyer_email = data.get('buyerEmail', user.email)
        
        logger.info(f"파싱된 파라미터: order_id={order_id}, amount={amount}, product={product_name}")
        
        if amount <= 0:
            logger.error(f"결제 금액 오류: {amount}")
            return Response(
                {'error': '결제 금액이 유효하지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 타임스탬프 생성
        timestamp = str(int(datetime.now().timestamp() * 1000))
        logger.info(f"타임스탬프 생성: {timestamp}")
        
        # 서명 생성을 위한 파라미터
        sign_params = {
            'mid': InicisPaymentService.MID,
            'oid': order_id,
            'price': str(amount),
            'timestamp': timestamp
        }
        
        logger.info(f"서명 파라미터: {sign_params}")
        
        # 서명 생성
        signature = InicisPaymentService.generate_signature(sign_params)
        mkey = InicisPaymentService.generate_mkey(sign_params)
        verification = InicisPaymentService.generate_verification(sign_params)
        
        logger.info(f"생성된 서명: signature={signature[:20]}..., mkey={mkey[:20]}..., verification={verification[:20]}...")
        
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
        
        logger.info(f"Payment 레코드 생성 완료: ID={payment.id}")
        
        response_data = {
            'success': True,
            'orderId': order_id,
            'timestamp': timestamp,
            'signature': signature,
            'mkey': mkey,
            'verification': verification,
            'payment_id': payment.id
        }
        
        logger.info(f"응답 데이터 준비 완료: {response_data}")
        logger.info(f"=== 이니시스 결제 준비 완료 ===")
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"이니시스 결제 준비 중 오류: {str(e)}")
        import traceback
        logger.error(f"스택 트레이스: {traceback.format_exc()}")
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
        
        logger.info(f"=== 이니시스 결제 검증 시작 v2.3 ===")
        logger.info(f"요청 사용자: ID={user.id}, 역할={user.role}")
        logger.info(f"요청 데이터: {data}")
        logger.info(f"최소 파라미터만 사용하는 승인 요청으로 수정...")
        
        # 결제 결과 파라미터
        order_id = data.get('orderId')
        auth_result_code = data.get('authResultCode')
        auth_token = data.get('authToken')
        tid = data.get('tid')
        
        # 필수 파라미터 검증
        if not order_id:
            logger.error("필수 파라미터 누락: orderId")
            return Response(
                {'success': False, 'error': '주문번호가 누락되었습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not auth_result_code:
            logger.error("필수 파라미터 누락: authResultCode")
            return Response(
                {'success': False, 'error': '인증 결과 코드가 누락되었습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"파싱된 파라미터: order_id={order_id}, auth_result_code={auth_result_code}, auth_token={'있음' if auth_token else '없음'}")
        
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
            # 이미 처리된 결제의 토큰 정보 가져오기
            is_subscription = '구독' in payment.product_name or 'unlimited' in payment.product_name.lower() or '무제한' in payment.product_name
            if is_subscription:
                token_count = 1 if payment.amount >= 29900 else 0
            else:
                token_count = int(payment.amount // 1990)
            
            # 단품 및 구독권 개수 계산
            single_tokens = BidToken.objects.filter(
                seller=user,
                token_type='single',
                status='active'
            ).count()
            
            subscription_count = BidToken.objects.filter(
                seller=user,
                token_type='unlimited',
                status='active',
                expires_at__gt=datetime.now()
            ).count()
            
            return Response({
                'success': True,
                'message': '이미 처리된 결제입니다.',
                'token_count': token_count,
                'total_tokens': single_tokens,
                'subscription_count': subscription_count,
                'is_subscription': is_subscription
            })
        
        # 결제 성공 여부 확인 (authResultCode가 '00' 또는 '0000'일 수 있음)  
        if auth_result_code in ['00', '0000']:
            pay_method = data.get('payMethod', '')
            
            logger.info(f"결제 방법 확인: {pay_method}")
            logger.info(f"결제 성공 처리 시작: order_id={order_id}")
            
            # payMethod가 없는 경우 기본값으로 Card 설정 (모바일에서는 payMethod가 없을 수 있음)
            if not pay_method:
                pay_method = 'Card'  # 기본값
                logger.info(f"payMethod가 없어서 기본값 설정: {pay_method}")
            
            # 가상계좌(무통장입금)인 경우 별도 처리 (승인 불필요)
            if pay_method in ['VBank', 'VBANK', 'vbank']:
                # 무통장입금은 입금대기 상태로 설정
                with transaction.atomic():
                    payment.status = 'waiting_deposit'
                    payment.tid = order_id[:200]
                    payment.vbank_name = data.get('vactBankName', '')
                    payment.vbank_num = data.get('VACT_Num', '')
                    payment.vbank_date = data.get('VACT_Date', '')
                    payment.vbank_holder = data.get('VACT_Name', '')
                    payment.payment_data.update({
                        'authToken': auth_token,
                        'authResultCode': auth_result_code,
                        'originalTid': tid,
                        'payMethod': pay_method,
                        'vactBankCode': data.get('vactBankCode'),
                    })
                    payment.save()
                    
                    logger.info(f"무통장입금 대기: order_id={order_id}, bank={payment.vbank_name}, account={payment.vbank_num}")
                    
                    # 무통장입금 안내 응답
                    return Response({
                        'success': True,
                        'message': f'무통장입금 계좌가 발급되었습니다. {payment.vbank_name} {payment.vbank_num}로 {payment.vbank_date}까지 입금해주세요.',
                        'is_vbank': True,
                        'vbank_name': payment.vbank_name,
                        'vbank_num': payment.vbank_num,
                        'vbank_date': payment.vbank_date,
                        'vbank_holder': payment.vbank_holder,
                        'amount': payment.amount
                    })
            
            # 실시간 결제(카드, 계좌이체, 휴대폰) 처리 - 승인 필요
            # DirectBank = 계좌이체, Card = 카드, HPP = 휴대폰
            else:
                # 모바일 결제 승인 요청
                auth_url = data.get('authUrl')
                auth_token = data.get('authToken')
                
                logger.info(f"이니시스 모바일 결제 승인 시작: order_id={order_id}, authResultCode={auth_result_code}")
                logger.info(f"결제 방법: {pay_method}")
                logger.info(f"authUrl: {auth_url}")
                logger.info(f"authToken 길이: {len(auth_token) if auth_token else 0}")
                
                # 승인 요청 필요
                if auth_url and auth_token:
                    approval_result = InicisPaymentService.mobile_payment_approval(
                        auth_url, auth_token
                    )
                    
                    if not approval_result:
                        logger.error(f"이니시스 승인 요청 실패: 응답 없음")
                        return Response({
                            'success': False,
                            'error': '결제 승인 요청에 실패했습니다.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # 결과 코드 확인 (다양한 필드명 처리)
                    result_code = approval_result.get('resultCode') or approval_result.get('ResultCode') or approval_result.get('result_code')
                    result_msg = approval_result.get('resultMsg') or approval_result.get('ResultMsg') or approval_result.get('result_msg')
                    
                    if result_code not in ['00', '0000', '00000']:
                        error_code = approval_result.get('errorCode') or approval_result.get('ErrorCode') or result_code
                        logger.error(f"이니시스 승인 실패: code={error_code}, msg={result_msg}")
                        logger.error(f"승인 실패 전체 응답: {approval_result}")
                        
                        # 계좌이체 특별 오류 처리
                        if pay_method in ['DirectBank', 'DIRECTBANK']:
                            error_msg = f'계좌이체 승인 실패: {result_msg} (code: {error_code})'
                        else:
                            error_msg = f'{result_msg} (code: {error_code})'
                        
                        return Response({
                            'success': False,
                            'error': error_msg,
                            'error_code': error_code
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    logger.info(f"이니시스 승인 성공: {approval_result}")
                
                # 실시간 결제 처리
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
                        'authUrl': data.get('authUrl'),  # 참고용 저장
                        'netCancelUrl': data.get('netCancelUrl'),  # 취소 시 사용
                        'idc_name': data.get('idc_name'),
                        'payMethod': pay_method,
                    })
                    payment.save()
                    
                    # 입찰권 지급 - 상품 유형에 따라 처리
                    # productName에서 구독권 여부 확인
                    is_subscription = '구독' in payment.product_name or 'unlimited' in payment.product_name.lower() or '무제한' in payment.product_name
                    
                    logger.info(f"상품명: {payment.product_name}, 구독권 여부: {is_subscription}, 금액: {payment.amount}")
                    
                    subscription_expires_at = None  # 초기화
                    
                    if is_subscription:
                        # 무제한 구독권 (29,900원)
                        if payment.amount >= 29900:
                            # 기존 활성 구독권 확인
                            existing_subscription = BidToken.objects.filter(
                                seller=user,
                                token_type='unlimited',
                                status='active',
                                expires_at__gt=datetime.now()  # 아직 만료되지 않은 구독권
                            ).order_by('-expires_at').first()
                            
                            if existing_subscription:
                                # 기존 구독권이 있으면 그 만료일 이후부터 시작
                                start_date = existing_subscription.expires_at
                                expires_at = start_date + timedelta(days=30)
                                logger.info(f"구독권 추가: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {expires_at.strftime('%Y-%m-%d %H:%M')} (기존 구독 이후)")
                            else:
                                # 기존 구독권이 없으면 현재부터 30일
                                expires_at = datetime.now() + timedelta(days=30)
                                logger.info(f"구독권 신규 구매: {datetime.now().strftime('%Y-%m-%d %H:%M')} ~ {expires_at.strftime('%Y-%m-%d %H:%M')}")
                            
                            new_subscription = BidToken.objects.create(
                                seller=user,
                                token_type='unlimited',
                                expires_at=expires_at
                            )
                            token_count = 1
                            # 응답에 포함할 구독권 정보 저장
                            subscription_expires_at = expires_at
                        else:
                            token_count = 0
                            logger.warning(f"구독권 결제 금액 부족: {payment.amount}원 < 29,900원")
                    else:
                        # 단품 입찰권 (1,990원당 1개)
                        token_count = int(payment.amount // 1990)
                        if token_count > 0:
                            # 단품 이용권은 생성일로부터 90일 후 만료
                            expires_at = datetime.now() + timedelta(days=90)
                            for _ in range(token_count):
                                BidToken.objects.create(
                                    seller=user,
                                    token_type='single',
                                    expires_at=expires_at  # 90일 만료
                                )
                            logger.info(f"견적이용권 {token_count}개 생성: 만료일 {expires_at.strftime('%Y-%m-%d')}")
                    
                    # BidTokenPurchase 레코드 생성 (구매 내역용)
                    BidTokenPurchase.objects.create(
                        seller=user,
                        token_type='unlimited' if is_subscription else 'single',
                        quantity=1 if is_subscription else token_count,
                        total_price=payment.amount,
                        payment_status='completed',
                        payment_date=datetime.now(),
                        order_id=order_id,
                        payment_key=auth_token[:200] if auth_token else None
                    )
                    
                    logger.info(f"이니시스 결제 성공: user={user.id}, order_id={order_id}, amount={payment.amount}, tokens={token_count}")
                
                # 사용자의 현재 총 입찰권 개수 계산
                # 단품 입찰권 개수
                single_tokens = BidToken.objects.filter(
                    seller=user, 
                    token_type='single',
                    status='active'
                ).count()
                
                # 구독권 개수 (만료되지 않은 것만)
                subscription_count = BidToken.objects.filter(
                    seller=user,
                    token_type='unlimited',
                    status='active',
                    expires_at__gt=datetime.now()
                ).count()
                
                current_tokens = single_tokens  # 단품 개수를 기본으로 표시
                
                # 구매 완료 메시지 설정
                response_data = {
                    'success': True,
                    'token_count': token_count,
                    'total_tokens': current_tokens,
                    'subscription_count': subscription_count,
                    'is_subscription': is_subscription
                }
                
                if is_subscription:
                    if subscription_count > 1:
                        message = f'구독권이 추가되었습니다. (현재 {subscription_count}개 보유)'
                    else:
                        message = '구독권이 구매 완료되었습니다.'
                    
                    # 구독권 만료일 정보 추가
                    if subscription_expires_at:
                        response_data['subscription_expires_at'] = subscription_expires_at.isoformat()
                        response_data['subscription_period'] = f"{(subscription_expires_at - timedelta(days=30)).strftime('%Y-%m-%d')} ~ {subscription_expires_at.strftime('%Y-%m-%d')}"
                else:
                    message = f'견적이용권 {token_count}개가 구매 완료되었습니다.'
                
                response_data['message'] = message
                
                return Response(response_data)
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
        logger.error(f"오류 타입: {type(e)}")
        logger.error(f"요청 데이터: {request.data}")
        import traceback
        logger.error(f"스택 트레이스: {traceback.format_exc()}")
        
        # 구체적인 오류 메시지 생성
        error_message = str(e) if str(e) and str(e) != 'None' else '결제 검증 중 오류가 발생했습니다.'
        
        return Response(
            {
                'success': False,
                'error': error_message,
                'error_code': getattr(e, 'code', None)
            },
            status=status.HTTP_400_BAD_REQUEST
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
            # 사용된 입찰권이 있는지 확인 (결제 시점 기준으로 생성된 토큰 중에서)
            # payment와 연결된 필드가 없으므로 시간 기준으로 확인
            payment_time = payment.created_at if hasattr(payment, 'created_at') else payment.completed_at
            used_tokens = BidToken.objects.filter(
                seller=user,
                status='used',
                created_at__gte=payment_time - timedelta(minutes=5),  # 결제 시점 전후 5분 내 생성된 토큰
                created_at__lte=payment_time + timedelta(minutes=5)
            ).exists()
            
            if used_tokens:
                return Response(
                    {'error': '이미 사용된 입찰권이 있어 취소할 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 입찰권 제거 (상품 유형에 따라 처리)
            is_subscription = '구독' in payment.product_name or 'unlimited' in payment.product_name.lower() or '무제한' in payment.product_name
            
            if is_subscription:
                # 구독권 취소 - 가장 마지막에 구매한 구독권 삭제 (만료일이 가장 늦은 것)
                latest_subscription = BidToken.objects.filter(
                    seller=user,
                    token_type='unlimited',
                    status='active'
                ).order_by('-expires_at').first()
                
                if latest_subscription:
                    latest_subscription.delete()
                    logger.info(f"구독권 취소: 만료일 {latest_subscription.expires_at}")
                
                token_count = 1
            else:
                # 단품 취소 - 결제 금액 기준으로 계산
                token_count = int(payment.amount // 1990)
                # 가장 최근에 생성된 single 타입 활성 토큰부터 삭제
                tokens_to_delete = BidToken.objects.filter(
                    seller=user,
                    token_type='single',
                    status='active'
                ).order_by('-created_at')[:token_count]
                
                for token in tokens_to_delete:
                    token.delete()
            
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
                
                # waiting_deposit 상태의 결제만 처리
                if payment.status == 'waiting_deposit':
                    with transaction.atomic():
                        # Payment 상태 업데이트
                        payment.status = 'completed'
                        payment.tid = tid if tid else payment.tid
                        payment.completed_at = datetime.now()
                        payment.payment_data['deposit_confirmed'] = True
                        payment.payment_data['deposit_confirmed_at'] = datetime.now().isoformat()
                        payment.save()
                        
                        # 입찰권 지급
                        user = payment.user
                        is_subscription = '구독' in payment.product_name or 'unlimited' in payment.product_name.lower() or '무제한' in payment.product_name
                        
                        if is_subscription:
                            # 무제한 구독권 (29,900원)
                            if payment.amount >= 29900:
                                # 기존 활성 구독권 확인
                                existing_subscription = BidToken.objects.filter(
                                    seller=user,
                                    token_type='unlimited',
                                    status='active',
                                    expires_at__gt=datetime.now()
                                ).order_by('-expires_at').first()
                                
                                if existing_subscription:
                                    # 기존 구독권이 있으면 그 만료일 이후부터 시작
                                    expires_at = existing_subscription.expires_at + timedelta(days=30)
                                else:
                                    # 기존 구독권이 없으면 현재부터 30일
                                    expires_at = datetime.now() + timedelta(days=30)
                                
                                BidToken.objects.create(
                                    seller=user,
                                    token_type='unlimited',
                                    expires_at=expires_at
                                )
                                token_count = 1
                            else:
                                token_count = 0
                        else:
                            # 단품 입찰권 (1,990원당 1개)
                            token_count = payment.amount // 1990
                            if token_count > 0:
                                expires_at = datetime.now() + timedelta(days=90)
                                for _ in range(int(token_count)):
                                    BidToken.objects.create(
                                        seller=user,
                                        token_type='single',
                                        expires_at=expires_at  # 90일 만료
                                    )
                        
                        # BidTokenPurchase 레코드 생성 (구매 내역용)
                        BidTokenPurchase.objects.create(
                            seller=user,
                            token_type='unlimited' if is_subscription else 'single',
                            quantity=1 if is_subscription else int(token_count),
                            total_price=payment.amount,
                            payment_status='completed',
                            payment_date=datetime.now(),
                            order_id=order_id,
                            payment_key=payment.tid
                        )
                        
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


@csrf_exempt
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_mobile_hash(request):
    """
    모바일 결제용 해시키 생성
    """
    try:
        data = request.data
        order_id = data.get('orderId')
        amount = data.get('amount')
        
        # 모바일 해시 생성 (간단한 예시)
        # 실제로는 이니시스 모바일 해시키 규격에 맞춰 생성
        import hashlib
        hash_data = f"{InicisPaymentService.MID}_{order_id}_{amount}_{InicisPaymentService.MOBILE_HASHKEY}"
        mobile_hash = hashlib.md5(hash_data.encode('utf-8')).hexdigest()
        
        return Response({
            'success': True,
            'hash': mobile_hash
        })
        
    except Exception as e:
        logger.error(f"모바일 해시키 생성 중 오류: {str(e)}")
        return Response(
            {'error': '해시키 생성에 실패했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_payments(request):
    """
    사용자의 입금 대기 중인 결제 내역 조회
    """
    try:
        user = request.user
        
        # 입금 대기 상태인 결제 내역 조회
        pending_payments = Payment.objects.filter(
            user=user,
            status='waiting_deposit'
        ).order_by('-created_at')
        
        payment_list = []
        for payment in pending_payments:
            payment_data = {
                'id': payment.id,
                'order_id': payment.order_id,
                'amount': int(payment.amount),
                'product_name': payment.product_name,
                'vbank_name': payment.vbank_name,
                'vbank_num': payment.vbank_num,
                'vbank_holder': payment.vbank_holder,
                'vbank_date': payment.vbank_date,
                'created_at': payment.created_at.isoformat(),
                'payment_method': payment.payment_method
            }
            payment_list.append(payment_data)
        
        return Response({
            'success': True,
            'pending_payments': payment_list,
            'count': len(payment_list)
        })
        
    except Exception as e:
        logger.error(f"입금 대기 결제 조회 중 오류: {str(e)}")
        return Response(
            {'error': '결제 내역 조회 중 오류가 발생했습니다.'},
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