"""
판매자 마이페이지 API 뷰
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Bid, GroupBuy
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
        print(f"[SellerProfileView] 사용자: {user}, 인증 여부: {user.is_authenticated}")
        if hasattr(user, 'userprofile'):
            print(f"[SellerProfileView] 역할: {user.userprofile.role}")
        else:
            print("[SellerProfileView] userprofile 속성 없음")
        
        # 개발 목적 임시 판매자 프로필 제공
        # 실제 환경에서는 아래 코드 주석 해제 필요
        # if not hasattr(user, 'userprofile') or user.userprofile.role != 'seller':
        #     return Response(
        #         {"detail": "판매자 권한이 없습니다."},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
        # 활성 입찰 수 계산
        active_bids = Bid.objects.filter(seller=user, status='pending').count()
        
        # 선택 대기 중인 입찰 수 계산
        pending_selection = Bid.objects.filter(
            seller=user, 
            groupbuy__status='bidding'
        ).count()
        
        # 판매 확정 대기 중인 건 수 계산
        pending_sales = Bid.objects.filter(
            seller=user, 
            status='selected',
            groupbuy__status='completed'
        ).count()
        
        # 판매 완료 건 수 계산
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
        
        # 남은 입찰권 및 무제한 입찰권 여부 (가상 데이터)
        # 실제로는 입찰권 모델이 필요함
        remaining_bids = 10
        has_unlimited_bids = False
        
        # 응답 데이터 구성
        data = {
            "name": user.get_full_name() or user.username,
            "profileImage": request.build_absolute_uri(user.userprofile.profile_image.url) if hasattr(user, 'userprofile') and user.userprofile.profile_image else None,
            "isVip": hasattr(user, 'userprofile') and user.userprofile.is_vip,
            "rating": rating,
            "activeBids": active_bids,
            "pendingSelection": pending_selection,
            "pendingSales": pending_sales,
            "completedSales": completed_sales,
            "remainingBids": remaining_bids,
            "hasUnlimitedBids": has_unlimited_bids
        }
        
        return Response(data)

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
