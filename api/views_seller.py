"""
판매자 마이페이지 API 뷰
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Bid, GroupBuy, BidToken, BidTokenPurchase
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

User = get_user_model()

class SellerProfileView(APIView):
    """
    판매자 프로필 정보 API 뷰
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        판매자 프로필 정보 조회
        """
        user = request.user
        
        # 디버깅 로그 추가
        print(f"[SellerProfileView] 인증 헤더: {request.headers.get('Authorization')}")
        print(f"[SellerProfileView] 사용자: {user.username} ({user.role}), 인증 여부: {user.is_authenticated}")
        
        # 개발 목적 임시 판매자 프로필 제공
        # 실제 환경에서는 아래 코드 주석 해제 필요
        # if not hasattr(user, 'userprofile') or user.userprofile.role != 'seller':
        #     return Response(
        #         {"detail": "판매자 권한이 없습니다."},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
        # 활성 입찰 수 계산 (입찰기록 - 모든 입찰)
        active_bids = Bid.objects.filter(seller=user).count()
        
        # 선택 대기 중인 입찰 수 계산 (최종선택 대기중 - 공구가 종료되고 선택 대기 중인 입찰)
        pending_selection = Bid.objects.filter(
            seller=user, 
            status='pending',
            groupbuy__status='ended'  # 공구가 종료된 상태
        ).count()
        
        # 판매 확정 대기 중인 건 수 계산 (판매 확정 - selected 상태의 입찰)
        pending_sales = Bid.objects.filter(
            seller=user, 
            status='selected'
        ).count()
        
        # 판매 완료 건 수 계산 (판매 완료 - confirmed 상태의 입찰)
        completed_sales = Bid.objects.filter(
            seller=user, 
            status='confirmed'
        ).count()
        
        # 판매자 평점 계산 (리뷰가 있는 경우)
        rating = 0
        if hasattr(user, 'reviews_received'):
            reviews = user.reviews_received.all()
            if reviews.exists():
                rating = sum(review.rating for review in reviews) / reviews.count()
        
        # 남은 입찰권 및 무제한 입찰권 여부 (실제 데이터)
        now = timezone.now()
        
        # 활성 상태의 입찰권 필터링
        active_tokens = BidToken.objects.filter(
            seller=user, 
            status='active',
            expires_at__gt=now
        )
        
        # 기본 입찰권 개수
        remaining_bids = active_tokens.filter(token_type='single').count()
        
        # 무제한 입찰권 보유 여부
        has_unlimited_bids = active_tokens.filter(token_type='unlimited').exists()
        
        # 응답 데이터 구성
        data = {
            "name": user.get_full_name() or user.username,
            "nickname": user.nickname if hasattr(user, 'nickname') else user.username,
            "username": user.username,
            "email": user.email,
            "phone": user.phone_number if hasattr(user, 'phone_number') else '',
            "businessNumber": user.business_reg_number if hasattr(user, 'business_reg_number') else '',
            "isRemoteSales": user.is_remote_sales_enabled if hasattr(user, 'is_remote_sales_enabled') else False,
            "address": user.address_detail if hasattr(user, 'address_detail') else '',
            "addressRegion": {
                "code": user.address_region.code,
                "name": user.address_region.name,
                "full_name": user.address_region.full_name
            } if user.address_region else None,
            "profileImage": user.profile_image if hasattr(user, 'profile_image') and user.profile_image else None,
            "isVip": hasattr(user, 'userprofile') and user.userprofile.is_vip,
            "rating": rating,
            "activeBids": active_bids,
            "pendingSelection": pending_selection,
            "pendingSales": pending_sales,
            "completedSales": completed_sales,
            "remainingBids": remaining_bids,
            "hasUnlimitedBids": has_unlimited_bids,
            "notificationEnabled": True  # 기본값
        }
        
        return Response(data)
    
    def patch(self, request):
        """
        판매자 프로필 정보 수정
        """
        user = request.user
        
        # 판매자 권한 체크
        if user.role != 'seller':
            return Response(
                {"detail": "판매자 권한이 없습니다."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 업데이트 가능한 필드들
        allowed_fields = [
            'nickname', 'description', 'phone', 'address', 
            'business_number', 'is_remote_sales', 'address_region_id',
            'profile_image'
        ]
        
        # 요청 데이터 필터링
        update_data = {}
        for field in allowed_fields:
            if field in request.data:
                # 필드명 변환 (프론트엔드 -> 백엔드)
                if field == 'phone':
                    update_data['phone_number'] = request.data[field].replace('-', '')
                elif field == 'business_number':
                    update_data['business_reg_number'] = request.data[field].replace('-', '')
                elif field == 'is_remote_sales':
                    update_data['is_remote_sales_enabled'] = request.data[field]
                elif field == 'address':
                    update_data['address_detail'] = request.data[field]
                elif field == 'address_region_id':
                    # 지역 코드로 Region 객체 찾기
                    from .models import Region
                    try:
                        region = Region.objects.get(code=request.data[field])
                        update_data['address_region'] = region
                    except Region.DoesNotExist:
                        return Response(
                            {"detail": "유효하지 않은 지역 코드입니다."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    update_data[field] = request.data[field]
        
        # 닉네임 중복 확인
        if 'nickname' in update_data:
            if User.objects.filter(nickname=update_data['nickname']).exclude(id=user.id).exists():
                return Response(
                    {"detail": "이미 사용 중인 닉네임입니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 사용자 정보 업데이트
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.save()
        
        # 업데이트된 프로필 정보 반환
        return self.get(request)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_bid_tokens(request):
    """
    입찰권 구매 API
    
    요청 데이터:
    - token_type: 입찰권 유형 ('single' - 입찰권 단품, 'unlimited' - 무제한 구독권)
    - quantity: 구매할 수량 (default: 1, unlimited은 항상 1개)
    """
    user = request.user
    
    # 판매자 권한 체크 (개발용 임시 비활성화)
    # if not hasattr(user, 'userprofile') or user.userprofile.role != 'seller':
    #     return Response({"detail": "판매자 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    
    # 요청 데이터 확인
    token_type = request.data.get('token_type', 'single')
    quantity = int(request.data.get('quantity', 1))
    
    # 입찰권 유형 검증
    if token_type not in ['single', 'unlimited']:
        return Response({"detail": "유효하지 않은 입찰권 유형입니다."}, status=status.HTTP_400_BAD_REQUEST)
    
    # 수량 검증 (무제한은 항상 1개만 구매 가능)
    if token_type == 'unlimited' and quantity > 1:
        return Response({"detail": "무제한 입찰권은 한 번에 1개만 구매 가능합니다."}, status=status.HTTP_400_BAD_REQUEST)
    
    if quantity < 1 or quantity > 100:
        return Response({"detail": "구매 수량은 1~100 사이의 값이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)
    
    # 가격 계산
    price_map = {
        'single': 1990,   # 1,990원 (입찰권 단품)
        'unlimited': 29900 # 29,900원 (무제한 구독권 30일)
    }
    unit_price = price_map.get(token_type)
    total_price = unit_price * quantity
    
    # 구매 내역 생성 및 입찰권 생성
    try:
        with transaction.atomic():
            # 구매 내역 생성
            purchase = BidTokenPurchase.objects.create(
                seller=user,
                token_type=token_type,
                quantity=quantity,
                total_price=total_price,
                payment_status='completed',  # 실제로는 결제 연동 필요
                payment_date=timezone.now()
            )
            
            # 입찰권 생성
            tokens = []
            for _ in range(quantity):
                # 만료일 계산 (토큰 유형에 따라 다름)
                if token_type == 'single':
                    # 단품 입찰권은 유효기간 없음
                    token = BidToken.objects.create(
                        seller=user,
                        token_type=token_type,
                        expires_at=None,
                        status='active'
                    )
                else:  # unlimited
                    # 무제한 구독권은 30일 유효
                    token = BidToken.objects.create(
                        seller=user,
                        token_type=token_type,
                        expires_at=timezone.now() + timezone.timedelta(days=30),
                        status='active'
                    )
                tokens.append(token)
            
            # 응답 구성
            response_data = {
                "purchase_id": purchase.id,
                "token_type": token_type,
                "quantity": quantity,
                "total_price": total_price,
                "tokens_created": len(tokens),
                "expires_at": tokens[0].expires_at if tokens else None
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response({"detail": f"구매 처리 중 오류가 발생했습니다: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bid_tokens(request):
    """
    사용자의 입찰권 목록 조회 API
    """
    user = request.user
    
    # 현재 시간
    now = timezone.now()
    
    # 활성 상태의 입찰권 필터링
    active_tokens = BidToken.objects.filter(
        seller=user, 
        status='active',
    )
    
    # 유효한 토큰만 필터링 (만료일이 없거나 현재 시간보다 미래인 경우)
    valid_tokens = active_tokens.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    
    # 입찰권 타입별 집계
    single_tokens = valid_tokens.filter(token_type='single').count()
    
    # 무제한 구독권 확인
    unlimited_subscription = False
    unlimited_expires_at = None
    
    # 가장 만료일이 늦은 무제한 구독권 찾기
    latest_unlimited = valid_tokens.filter(token_type='unlimited').order_by('-expires_at').first()
    
    if latest_unlimited:
        unlimited_subscription = True
        unlimited_expires_at = latest_unlimited.expires_at
    
    # 최근 구매 내역
    recent_purchases = BidTokenPurchase.objects.filter(
        seller=user,
        payment_status='completed'
    ).order_by('-purchase_date')[:5]
    
    # 구매 내역 데이터 준비
    purchase_data = [{
        'id': purchase.id,
        'token_type': purchase.token_type,
        'token_type_display': purchase.get_token_type_display(),
        'quantity': purchase.quantity,
        'total_price': purchase.total_price,
        'purchase_date': purchase.purchase_date
    } for purchase in recent_purchases]
    
    response_data = {
        'single_tokens': single_tokens,
        'unlimited_subscription': unlimited_subscription,
        'unlimited_expires_at': unlimited_expires_at,
        'total_tokens': single_tokens + (1 if unlimited_subscription else 0),
        'recent_purchases': purchase_data
    }
    
    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bid_summary(request):
    """
    판매자의 입찰 요약 정보 조회
    """
    user = request.user
    
    # 디버깅 로그 추가
    print(f"[get_bid_summary] 인증 헤더: {request.headers.get('Authorization')}")
    print(f"[get_bid_summary] 사용자: {user}, 인증 여부: {user.is_authenticated}")
    if hasattr(user, 'userprofile'):
        print(f"[get_bid_summary] 역할: {user.userprofile.role}")
    else:
        print("[get_bid_summary] userprofile 속성 없음")
    
    # 개발 목적을 위해 임시 주석 처리
    # if not hasattr(user, 'userprofile') or user.userprofile.role != 'seller':
    #     return Response(
    #         {"detail": "판매자 권한이 없습니다."},
    #         status=status.HTTP_403_FORBIDDEN
    #     )
    
    # 전체 입찰 수
    total_bids = Bid.objects.filter(seller=user).count()
    
    # 활성화된 입찰 수 (pending 상태)
    active_bids = Bid.objects.filter(seller=user, status='pending').count()
    
    # 완료된 입찰 수 (confirmed 또는 rejected 상태)
    completed_bids = Bid.objects.filter(
        seller=user, 
        status__in=['confirmed', 'rejected']
    ).count()
    
    # 수락된 입찰 수 (confirmed 상태)
    accepted_bids = Bid.objects.filter(seller=user, status='confirmed').count()
    
    # 거절된 입찰 수 (rejected 상태)
    rejected_bids = Bid.objects.filter(seller=user, status='rejected').count()
    
    data = {
        "totalBids": total_bids,
        "activeBids": active_bids,
        "completedBids": completed_bids,
        "acceptedBids": accepted_bids,
        "rejectedBids": rejected_bids
    }
    
    return Response(data)

class SellerSalesView(APIView):
    """
    판매자의 판매 확정 목록 API 뷰
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        판매 확정 목록 조회
        """
        user = request.user
        
        # 디버깅 로그 추가
        print(f"[SellerSalesView] 인증 헤더: {request.headers.get('Authorization')}")
        print(f"[SellerSalesView] 사용자: {user}, 인증 여부: {user.is_authenticated}")
        if hasattr(user, 'userprofile'):
            print(f"[SellerSalesView] 역할: {user.userprofile.role}")
        else:
            print("[SellerSalesView] userprofile 속성 없음")
        
        # 개발 목적을 위해 임시 주석 처리
        # if not hasattr(user, 'userprofile') or user.userprofile.role != 'seller':
        #     return Response(
        #         {"detail": "판매자 권한이 없습니다."},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
        # 쿼리 파라미터
        status_filter = request.query_params.get('status', None)
        search_query = request.query_params.get('search', None)
        
        # 기본 쿼리셋 - 판매자의 선택된 입찰
        queryset = Bid.objects.filter(
            seller=user,
            status__in=['selected', 'confirmed']
        )
        
        # 상태 필터링
        if status_filter == 'pending':
            queryset = queryset.filter(status='selected')
        elif status_filter == 'confirmed':
            queryset = queryset.filter(status='confirmed')
        
        # 검색 필터링
        if search_query:
            queryset = queryset.filter(
                groupbuy__product__name__icontains=search_query
            )
        
        # 가상 데이터로 응답 구성 (실제로는 페이지네이션 적용 필요)
        # 그룹바이와 제품 정보를 포함하는 복잡한 쿼리 필요
        results = []
        
        for bid in queryset:
            groupbuy = bid.groupbuy
            product = groupbuy.product
            
            # 판매 확정 정보 구성
            sale_data = {
                "id": bid.id,
                "productName": product.name,
                "provider": "SK텔레콤",  # 가상 데이터, 실제로는 제품 속성에서 가져와야 함
                "plan": "5만원대",  # 가상 데이터, 실제로는 제품 속성에서 가져와야 함
                "tradeNumber": f"#{groupbuy.id:06d}",
                "confirmationDate": bid.updated_at.isoformat(),
                "subsidyAmount": bid.amount,
                "status": "confirmed" if bid.status == 'confirmed' else "pending",
                "buyerInfo": [
                    # 가상 데이터, 실제로는 구매자 정보를 가져와야 함
                    {
                        "name": groupbuy.creator.get_full_name() or groupbuy.creator.username,
                        "contact": "010-1234-5678"  # 가상 데이터
                    }
                ]
            }
            
            results.append(sale_data)
        
        # 페이지네이션된 응답 구성
        data = {
            "count": len(results),
            "next": None,
            "previous": None,
            "results": results
        }
        
        return Response(data)
    
    def get_detail(self, request, bid_id):
        """
        판매 확정 상세 정보 조회
        """
        user = request.user
        
        # 디버깅 로그 추가
        print(f"[get_detail] 인증 헤더: {request.headers.get('Authorization')}")
        print(f"[get_detail] 사용자: {user}, 인증 여부: {user.is_authenticated}")
        if hasattr(user, 'userprofile'):
            print(f"[get_detail] 역할: {user.userprofile.role}")
        else:
            print("[get_detail] userprofile 속성 없음")
        
        # 개발 목적을 위해 임시 주석 처리
        # if not hasattr(user, 'userprofile') or user.userprofile.role != 'seller':
        #     return Response(
        #         {"detail": "판매자 권한이 없습니다."},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
        try:
            bid = Bid.objects.get(id=bid_id, seller=user)
        except Bid.DoesNotExist:
            return Response(
                {"detail": "해당 입찰 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 선택된 입찰이 아닌 경우
        if bid.status not in ['selected', 'confirmed']:
            return Response(
                {"detail": "판매 확정 상태가 아닙니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        groupbuy = bid.groupbuy
        product = groupbuy.product
        
        # 가상 데이터로 구매자 정보 구성
        buyer_info = [
            {
                "name": groupbuy.creator.get_full_name() or groupbuy.creator.username,
                "contact": "010-1234-5678"  # 가상 데이터
            }
        ]
        
        # 실제 참가자가 있는 경우 추가
        for participant in groupbuy.participants.all():
            buyer_info.append({
                "name": participant.user.get_full_name() or participant.user.username,
                "contact": "010-9876-5432"  # 가상 데이터
            })
        
        # 응답 데이터 구성
        data = {
            "id": bid.id,
            "productName": product.name,
            "provider": "SK텔레콤",  # 가상 데이터
            "plan": "5만원대",  # 가상 데이터
            "tradeNumber": f"#{groupbuy.id:06d}",
            "confirmationDate": bid.updated_at.isoformat(),
            "subsidyAmount": bid.amount,
            "status": "confirmed" if bid.status == 'confirmed' else "pending",
            "buyerInfo": buyer_info
        }
        
        return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_seller_sale_detail(request, bid_id):
    """
    판매 확정 상세 정보 조회 뷰
    """
    # 디버깅 로그 추가
    print(f"[get_seller_sale_detail] bid_id: {bid_id}")
    print(f"[get_seller_sale_detail] 인증 헤더: {request.headers.get('Authorization')}")
    
    view = SellerSalesView()
    return view.get_detail(request, bid_id)
