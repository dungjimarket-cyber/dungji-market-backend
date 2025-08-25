import json
import uuid
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import requests
from .models import BidTokenPurchase, BidToken, User

# 토스페이먼츠 설정
TOSS_CLIENT_KEY = settings.TOSS_CLIENT_KEY if hasattr(settings, 'TOSS_CLIENT_KEY') else 'test_ck_demo'
TOSS_SECRET_KEY = settings.TOSS_SECRET_KEY if hasattr(settings, 'TOSS_SECRET_KEY') else 'test_sk_demo'
TOSS_API_URL = 'https://api.tosspayments.com/v1/payments'

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_request(request):
    """
    결제 요청 생성 API
    토스페이먼츠 결제를 위한 주문 정보를 생성합니다.
    """
    user = request.user
    
    # 요청 데이터 확인
    token_type = request.data.get('token_type', 'single')
    quantity = int(request.data.get('quantity', 1))
    
    # 입찰권 유형 검증
    if token_type not in ['single', 'unlimited']:
        return Response({"error": "유효하지 않은 입찰권 유형입니다."}, status=status.HTTP_400_BAD_REQUEST)
    
    # 수량 검증
    if token_type == 'unlimited' and quantity > 1:
        return Response({"error": "무제한 입찰권은 한 번에 1개만 구매 가능합니다."}, status=status.HTTP_400_BAD_REQUEST)
    
    if quantity < 1 or quantity > 100:
        return Response({"error": "구매 수량은 1~100 사이의 값이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)
    
    # 가격 계산
    price_map = {
        'single': 1990,   # 1,990원 (입찰권 단품)
        'unlimited': 29900 # 29,900원 (무제한 구독권 30일)
    }
    unit_price = price_map.get(token_type)
    total_amount = unit_price * quantity
    
    # 주문 ID 생성 (UUID 사용)
    order_id = f"bid_{user.id}_{uuid.uuid4().hex[:12]}"
    
    # 상품명 생성
    if token_type == 'single':
        order_name = f"견적 이용권 {quantity}개"
    else:
        order_name = "무제한 구독권 (30일)"
    
    # 구매 내역 생성 (pending 상태로)
    try:
        purchase = BidTokenPurchase.objects.create(
            seller=user,
            token_type=token_type,
            quantity=quantity,
            total_price=total_amount,
            payment_status='pending',
            order_id=order_id  # order_id 필드 추가 필요
        )
        
        # 응답 데이터
        response_data = {
            "success": True,
            "orderId": order_id,
            "orderName": order_name,
            "amount": total_amount,
            "customerName": user.username,
            "customerEmail": user.email,
            "successUrl": f"{settings.FRONTEND_URL}/payment/success",
            "failUrl": f"{settings.FRONTEND_URL}/payment/fail",
            "purchaseId": purchase.id
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"주문 생성 중 오류가 발생했습니다: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_payment(request):
    """
    결제 승인 API
    토스페이먼츠로부터 결제 승인 요청을 받아 처리합니다.
    """
    payment_key = request.data.get('paymentKey')
    order_id = request.data.get('orderId')
    amount = request.data.get('amount')
    
    if not all([payment_key, order_id, amount]):
        return Response(
            {"error": "필수 파라미터가 누락되었습니다."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 구매 내역 조회
    try:
        purchase = BidTokenPurchase.objects.get(order_id=order_id)
    except BidTokenPurchase.DoesNotExist:
        return Response(
            {"error": "주문을 찾을 수 없습니다."}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # 금액 검증
    if purchase.total_price != amount:
        return Response(
            {"error": "결제 금액이 일치하지 않습니다."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 토스페이먼츠 결제 승인 API 호출
    headers = {
        'Authorization': f'Basic {TOSS_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    
    data = {
        'paymentKey': payment_key,
        'orderId': order_id,
        'amount': amount,
    }
    
    try:
        response = requests.post(
            f'{TOSS_API_URL}/confirm',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            # 결제 성공
            payment_data = response.json()
            
            with transaction.atomic():
                # 구매 내역 업데이트
                purchase.payment_status = 'completed'
                purchase.payment_date = timezone.now()
                purchase.payment_key = payment_key
                purchase.save()
                
                # 입찰권 생성
                tokens = []
                for _ in range(purchase.quantity):
                    if purchase.token_type == 'single':
                        # 단품 입찰권은 유효기간 없음
                        token = BidToken.objects.create(
                            seller=purchase.seller,
                            token_type=purchase.token_type,
                            expires_at=None,
                            status='active'
                        )
                    else:  # unlimited
                        # 무제한 구독권은 30일 유효
                        token = BidToken.objects.create(
                            seller=purchase.seller,
                            token_type=purchase.token_type,
                            expires_at=timezone.now() + timezone.timedelta(days=30),
                            status='active'
                        )
                    tokens.append(token)
            
            return Response({
                "success": True,
                "message": "결제가 성공적으로 완료되었습니다.",
                "purchaseId": purchase.id,
                "tokens": len(tokens)
            }, status=status.HTTP_200_OK)
            
        else:
            # 결제 실패
            error_data = response.json()
            purchase.payment_status = 'failed'
            purchase.save()
            
            return Response({
                "success": False,
                "error": error_data.get('message', '결제 승인에 실패했습니다.')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except requests.exceptions.RequestException as e:
        return Response({
            "success": False,
            "error": f"결제 처리 중 오류가 발생했습니다: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_payment(request):
    """
    결제 취소 API
    """
    order_id = request.data.get('orderId')
    
    try:
        purchase = BidTokenPurchase.objects.get(order_id=order_id)
        
        if purchase.payment_status == 'pending':
            purchase.payment_status = 'cancelled'
            purchase.save()
            
            return Response({
                "success": True,
                "message": "결제가 취소되었습니다."
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "error": "취소할 수 없는 상태입니다."
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except BidTokenPurchase.DoesNotExist:
        return Response(
            {"error": "주문을 찾을 수 없습니다."}, 
            status=status.HTTP_404_NOT_FOUND
        )