"""
통합 찜/후기 API Views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q
from .models_unified_simple import UnifiedFavorite, UnifiedReview
from used_phones.models import UsedPhone, UsedPhoneTransaction, UsedPhoneOffer
from used_electronics.models import UsedElectronics, ElectronicsTransaction, ElectronicsOffer
from django.contrib.auth import get_user_model

User = get_user_model()


# ========== 찜 관련 API ==========

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request):
    """찜하기 토글 (휴대폰/전자제품 통합)"""
    item_type = request.data.get('item_type')  # 'phone' or 'electronics'
    item_id = request.data.get('item_id')

    if not item_type or not item_id:
        return Response({'error': 'item_type과 item_id가 필요합니다.'}, status=400)

    if item_type not in ['phone', 'electronics']:
        return Response({'error': '잘못된 item_type입니다.'}, status=400)

    # 상품 존재 여부 확인
    if item_type == 'phone':
        item = get_object_or_404(UsedPhone, id=item_id)
    else:
        item = get_object_or_404(UsedElectronics, id=item_id)

    # 찜 토글
    favorite, created = UnifiedFavorite.objects.get_or_create(
        user=request.user,
        item_type=item_type,
        item_id=item_id
    )

    if not created:
        favorite.delete()
        is_favorited = False
        message = "찜이 해제되었습니다."

        # 찜 카운트 감소
        if hasattr(item, 'favorite_count'):
            item.favorite_count = max(0, item.favorite_count - 1)
            item.save(update_fields=['favorite_count'])
    else:
        is_favorited = True
        message = "찜이 추가되었습니다."

        # 찜 카운트 증가
        if hasattr(item, 'favorite_count'):
            item.favorite_count += 1
            item.save(update_fields=['favorite_count'])

    return Response({
        'is_favorited': is_favorited,
        'message': message,
        'favorite_count': getattr(item, 'favorite_count', 0)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def favorite_status(request, item_type, item_id):
    """특정 상품 찜 여부 확인"""
    if item_type not in ['phone', 'electronics']:
        return Response({'error': '잘못된 item_type입니다.'}, status=400)

    is_favorited = UnifiedFavorite.objects.filter(
        user=request.user,
        item_type=item_type,
        item_id=item_id
    ).exists()

    return Response({'is_favorited': is_favorited})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_favorites(request):
    """내 찜 목록 (휴대폰/전자제품 통합)"""
    item_type = request.GET.get('type', 'all')  # 'all', 'phone', 'electronics'

    favorites = UnifiedFavorite.objects.filter(user=request.user)

    if item_type != 'all':
        favorites = favorites.filter(item_type=item_type)

    result = []
    for favorite in favorites:
        item = favorite.get_item()
        if item:
            item_data = {
                'favorite_id': favorite.id,
                'item_type': favorite.item_type,
                'item_id': favorite.item_id,
                'created_at': favorite.created_at,
            }

            if favorite.item_type == 'phone':
                item_data.update({
                    'brand': item.brand,
                    'model': item.model,
                    'storage': item.storage,
                    'price': item.price,
                    'status': item.status,
                    'condition_grade': item.condition_grade,
                    'image_url': item.images.first().image.url if item.images.exists() else None,
                })
            else:  # electronics
                item_data.update({
                    'subcategory': item.subcategory,
                    'brand': item.brand,
                    'model_name': item.model_name,
                    'price': item.price,
                    'status': item.status,
                    'condition_grade': item.condition_grade,
                    'image_url': item.images.first().image.url if item.images.exists() else None,
                })

            result.append(item_data)

    return Response({'favorites': result, 'count': len(result)})


# ========== 후기 관련 API ==========

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request):
    """거래 후기 작성 (휴대폰/전자제품 통합)"""
    print(f"[UNIFIED REVIEW] Request data: {request.data}")
    print(f"[UNIFIED REVIEW] User: {request.user}")

    item_type = request.data.get('item_type')  # 'phone' or 'electronics'
    transaction_id = request.data.get('transaction_id', request.data.get('transaction'))
    rating = request.data.get('rating', 5)
    comment = request.data.get('comment', '')

    # 추가 평가 항목
    is_punctual = request.data.get('is_punctual', False)
    is_friendly = request.data.get('is_friendly', False)
    is_honest = request.data.get('is_honest', False)
    is_fast_response = request.data.get('is_fast_response', False)

    if not item_type:
        return Response({'error': 'item_type이 필요합니다.'}, status=400)

    if item_type not in ['phone', 'electronics']:
        return Response({'error': '잘못된 item_type입니다.'}, status=400)

    # transaction_id가 없거나 0인 경우 처리
    if not transaction_id or transaction_id == 0:
        if item_type == 'electronics':
            # 전자제품: offer_id로 시도
            offer_id = request.data.get('offer_id')
            if offer_id:
                print(f"[UNIFIED REVIEW] No transaction_id, trying with offer_id: {offer_id}")
                try:
                    offer = ElectronicsOffer.objects.get(id=offer_id, status='accepted')
                    electronics = offer.electronics

                    # 트랜잭션 찾기 (OneToOne 직접 접근)
                    try:
                        transaction = electronics.transaction
                        if transaction.status == 'cancelled':
                            transaction = None
                    except ElectronicsTransaction.DoesNotExist:
                        transaction = None

                    if not transaction:
                        # 트랜잭션 생성
                        transaction = ElectronicsTransaction.objects.create(
                            electronics=electronics,
                            seller=electronics.seller,
                            buyer=offer.buyer,
                            final_price=offer.offer_price,
                            status='completed',
                            seller_completed=True,
                            buyer_completed=True
                        )
                        print(f"[UNIFIED REVIEW] Created transaction {transaction.id} from offer {offer_id}")
                    transaction_id = transaction.id
                except ElectronicsOffer.DoesNotExist:
                    return Response(
                        {'error': f'제안 {offer_id}를 찾을 수 없습니다.'},
                        status=404
                    )
            else:
                return Response(
                    {'error': 'transaction_id 또는 offer_id가 필요합니다.'},
                    status=400
                )
        else:
            # 휴대폰: phone_id로 시도
            phone_id = request.data.get('phone_id')
            if phone_id:
                print(f"[UNIFIED REVIEW] No transaction_id, trying with phone_id: {phone_id}")
                try:
                    phone = UsedPhone.objects.get(id=phone_id)
                    # 해당 폰의 가장 최근 트랜잭션 찾기
                    transaction = UsedPhoneTransaction.objects.filter(
                        phone=phone
                    ).exclude(status='cancelled').order_by('-created_at').first()

                    if transaction:
                        transaction_id = transaction.id
                        print(f"[UNIFIED REVIEW] Found transaction {transaction_id} for phone {phone_id}")
                    else:
                        # 트랜잭션이 없으면 accepted offer로 생성
                        accepted_offer = UsedPhoneOffer.objects.filter(
                            phone=phone,
                            status='accepted'
                        ).first()

                        if accepted_offer:
                            transaction = UsedPhoneTransaction.objects.create(
                                phone=phone,
                                seller=phone.seller,
                                buyer=accepted_offer.buyer,
                                price=accepted_offer.offered_price,
                                status='completed'
                            )
                            transaction_id = transaction.id
                            print(f"[UNIFIED REVIEW] Created transaction {transaction_id} for phone {phone_id}")
                        else:
                            return Response(
                                {'error': f'폰 {phone_id}에 대한 거래 정보를 찾을 수 없습니다.'},
                                status=404
                            )
                except UsedPhone.DoesNotExist:
                    return Response(
                        {'error': f'폰 {phone_id}를 찾을 수 없습니다.'},
                        status=404
                    )
            else:
                return Response(
                    {'error': 'transaction_id 또는 phone_id가 필요합니다.'},
                    status=400
                )

    # 거래 확인
    if item_type == 'phone':
        transaction = get_object_or_404(UsedPhoneTransaction, id=transaction_id)
    else:
        transaction = get_object_or_404(ElectronicsTransaction, id=transaction_id)

    # 권한 확인 (구매자 또는 판매자만 작성 가능)
    if request.user not in [transaction.buyer, transaction.seller]:
        return Response({'error': '해당 거래의 참여자만 후기를 작성할 수 있습니다.'}, status=403)

    # 이미 작성한 후기가 있는지 확인
    existing_review = UnifiedReview.objects.filter(
        item_type=item_type,
        transaction_id=transaction_id,
        reviewer=request.user
    ).exists()

    if existing_review:
        return Response({'error': '이미 후기를 작성했습니다.'}, status=400)

    # 상대방 결정
    if request.user == transaction.buyer:
        reviewee = transaction.seller
        is_from_buyer = True
    else:
        reviewee = transaction.buyer
        is_from_buyer = False

    # 후기 생성
    review = UnifiedReview.objects.create(
        item_type=item_type,
        transaction_id=transaction_id,
        reviewer=request.user,
        reviewee=reviewee,
        rating=rating,
        comment=comment,
        is_punctual=is_punctual,
        is_friendly=is_friendly,
        is_honest=is_honest,
        is_fast_response=is_fast_response,
        is_from_buyer=is_from_buyer
    )

    return Response({
        'id': review.id,
        'message': '후기가 작성되었습니다.',
        'rating': review.rating,
        'reviewee': reviewee.username
    }, status=201)


@api_view(['GET'])
def user_reviews(request, username):
    """특정 사용자가 받은 후기 목록"""
    user = get_object_or_404(User, username=username)

    reviews = UnifiedReview.objects.filter(reviewee=user)

    # 통계
    stats = reviews.aggregate(
        total_count=Count('id'),
        average_rating=Avg('rating'),
        rating_5=Count('id', filter=Q(rating=5)),
        rating_4=Count('id', filter=Q(rating=4)),
        rating_3=Count('id', filter=Q(rating=3)),
        rating_2=Count('id', filter=Q(rating=2)),
        rating_1=Count('id', filter=Q(rating=1)),
        punctual_count=Count('id', filter=Q(is_punctual=True)),
        friendly_count=Count('id', filter=Q(is_friendly=True)),
        honest_count=Count('id', filter=Q(is_honest=True)),
        fast_response_count=Count('id', filter=Q(is_fast_response=True)),
    )

    # 후기 목록
    review_list = []
    for review in reviews[:50]:  # 최근 50개만
        transaction = review.get_transaction()
        if transaction:
            if review.item_type == 'phone':
                item_info = f"{transaction.phone.brand} {transaction.phone.model}"
            else:
                item_info = f"{transaction.electronics.brand} {transaction.electronics.model_name}"
        else:
            item_info = "상품 정보 없음"

        review_list.append({
            'id': review.id,
            'item_type': review.item_type,
            'item_info': item_info,
            'reviewer': review.reviewer.username,
            'rating': review.rating,
            'comment': review.comment,
            'is_punctual': review.is_punctual,
            'is_friendly': review.is_friendly,
            'is_honest': review.is_honest,
            'is_fast_response': review.is_fast_response,
            'is_from_buyer': review.is_from_buyer,
            'created_at': review.created_at,
        })

    return Response({
        'stats': stats,
        'reviews': review_list
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_review_written(request, item_type, transaction_id):
    """후기 작성 여부 확인"""
    if item_type not in ['phone', 'electronics']:
        return Response({'error': '잘못된 item_type입니다.'}, status=400)

    written = UnifiedReview.objects.filter(
        item_type=item_type,
        transaction_id=transaction_id,
        reviewer=request.user
    ).exists()

    return Response({'written': written})