"""
MyPage API Views for Used Phone Trading
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Q, Avg, Sum
from django.contrib.auth import get_user_model
from used_phones.models import UsedPhone, UsedPhoneOffer
from api.models_unified_simple import UnifiedFavorite
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mypage_profile(request):
    """마이페이지 프로필 정보 조회"""
    user = request.user
    
    # 프로필 정보
    profile_data = {
        'id': user.id,
        'username': user.username,
        'nickname': user.nickname if hasattr(user, 'nickname') else user.username,
        'email': user.email,
        'phone_number': user.phone_number,
        'phone_verified': user.phone_verified if hasattr(user, 'phone_verified') else False,
        'profile_image': user.profile_image if hasattr(user, 'profile_image') else None,
        'role': user.role if hasattr(user, 'role') else 'buyer',
        'address_region': {
            'id': user.address_region.id,
            'name': user.address_region.name,
            'full_name': user.address_region.full_name
        } if user.address_region else None,
        'address_detail': user.address_detail if hasattr(user, 'address_detail') else None,
        'created_at': user.date_joined,
    }
    
    # 판매자 추가 정보
    if user.role == 'seller':
        profile_data.update({
            'business_number': user.business_number if hasattr(user, 'business_number') else None,
            'representative_name': user.representative_name if hasattr(user, 'representative_name') else None,
            'is_business_verified': user.is_business_verified if hasattr(user, 'is_business_verified') else False,
            'is_remote_sales': user.is_remote_sales if hasattr(user, 'is_remote_sales') else False,
            'average_rating': user.average_rating if hasattr(user, 'average_rating') else None,
            'review_count': user.review_count if hasattr(user, 'review_count') else 0,
        })
    
    return Response(profile_data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def mypage_update_profile(request):
    """마이페이지 프로필 수정"""
    user = request.user
    data = request.data
    
    # 수정 가능한 필드
    updatable_fields = ['nickname', 'email', 'phone_number', 'address_detail']
    
    for field in updatable_fields:
        if field in data:
            setattr(user, field, data[field])
    
    # 지역 정보 업데이트
    if 'address_region_id' in data:
        from api.models import Region
        try:
            region = Region.objects.get(id=data['address_region_id'])
            user.address_region = region
        except Region.DoesNotExist:
            return Response(
                {'error': '유효하지 않은 지역입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # 프로필 이미지 업데이트
    if 'profile_image' in request.FILES:
        # TODO: 이미지 업로드 처리
        pass
    
    user.save()
    
    return Response({'message': '프로필이 수정되었습니다.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mypage_stats(request):
    """마이페이지 통계 정보 조회"""
    user = request.user
    
    # 판매 통계
    active_sales = UsedPhone.objects.filter(
        seller=user,
        status='active'
    ).count()
    
    trading_sales = UsedPhone.objects.filter(
        seller=user,
        status='trading'
    ).count()
    
    completed_sales = UsedPhone.objects.filter(
        seller=user,
        status='sold'
    ).count()
    
    # 구매 통계
    sent_offers = UsedPhoneOffer.objects.filter(
        buyer=user,
        status='pending'
    ).count()
    
    accepted_offers = UsedPhoneOffer.objects.filter(
        buyer=user,
        status='accepted'
    ).count()
    
    # 찜 통계
    favorites_count = UnifiedFavorite.objects.filter(
        user=user,
        item_type='phone'
    ).count()
    
    # 받은 제안 통계 (판매자인 경우)
    received_offers_count = 0
    if hasattr(user, 'used_phones'):
        user_phones = user.used_phones.filter(status__in=['active', 'trading'])
        received_offers_count = UsedPhoneOffer.objects.filter(
            phone__in=user_phones,
            status='pending'
        ).count()
    
    stats_data = {
        'sales': {
            'active': active_sales,
            'trading': trading_sales,
            'completed': completed_sales,
            'total': active_sales + trading_sales + completed_sales,
            'received_offers': received_offers_count,
        },
        'purchases': {
            'sent_offers': sent_offers,
            'accepted_offers': accepted_offers,
            'favorites': favorites_count,
        },
        'trade': {
            'total_sales': completed_sales,
            'total_purchases': accepted_offers,
            'total_trades': completed_sales + accepted_offers,
        }
    }
    
    return Response(stats_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mypage_reviews_received(request):
    """받은 거래 후기 조회"""
    # TODO: 거래 후기 모델 구현 후 작성
    return Response({'results': []})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mypage_reviews_pending(request):
    """작성 대기 중인 거래 후기 조회"""
    from used_phones.models import UsedPhone, UsedPhoneTransaction
    from used_electronics.models import UsedElectronics, ElectronicsTransaction
    from api.models_unified_simple import UnifiedReview

    pending_reviews = []

    # 휴대폰 거래 중 후기 미작성 건
    phone_transactions = UsedPhoneTransaction.objects.filter(
        Q(seller=request.user) | Q(buyer=request.user),
        status='completed'
    ).select_related('phone', 'seller', 'buyer')

    for transaction in phone_transactions:
        # 이미 리뷰를 작성했는지 확인
        has_review = UnifiedReview.objects.filter(
            item_type='phone',
            transaction_id=transaction.id,
            reviewer=request.user
        ).exists()

        if not has_review:
            # 거래 상대방 결정
            is_seller = transaction.seller == request.user
            partner = transaction.buyer if is_seller else transaction.seller

            pending_reviews.append({
                'transaction_id': transaction.id,
                'item_type': 'phone',
                'item_id': transaction.phone.id,
                'item_name': f"{transaction.phone.brand} {transaction.phone.model_name}",
                'partner_name': partner.nickname if hasattr(partner, 'nickname') else partner.username,
                'partner_id': partner.id,
                'is_seller': is_seller,
                'completed_date': transaction.updated_at.isoformat() if transaction.updated_at else transaction.created_at.isoformat(),
            })

    # 전자제품 거래 중 후기 미작성 건
    electronics_transactions = ElectronicsTransaction.objects.filter(
        Q(seller=request.user) | Q(buyer=request.user),
        status='completed'
    ).select_related('electronics', 'seller', 'buyer')

    for transaction in electronics_transactions:
        # 이미 리뷰를 작성했는지 확인
        has_review = UnifiedReview.objects.filter(
            item_type='electronics',
            transaction_id=transaction.id,
            reviewer=request.user
        ).exists()

        if not has_review:
            # 거래 상대방 결정
            is_seller = transaction.seller == request.user
            partner = transaction.buyer if is_seller else transaction.seller

            pending_reviews.append({
                'transaction_id': transaction.id,
                'item_type': 'electronics',
                'item_id': transaction.electronics.id,
                'item_name': f"{transaction.electronics.brand} {transaction.electronics.model_name}",
                'partner_name': partner.nickname if hasattr(partner, 'nickname') else partner.username,
                'partner_id': partner.id,
                'is_seller': is_seller,
                'completed_date': transaction.updated_at.isoformat() if transaction.updated_at else transaction.created_at.isoformat(),
            })

    # 최신 거래순으로 정렬
    pending_reviews.sort(key=lambda x: x['completed_date'], reverse=True)

    return Response({
        'results': pending_reviews,
        'count': len(pending_reviews)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mypage_create_review(request):
    """거래 후기 작성"""
    # TODO: 거래 후기 모델 구현 후 작성
    return Response({'message': '리뷰가 작성되었습니다.'})