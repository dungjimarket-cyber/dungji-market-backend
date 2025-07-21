from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from .models import GroupBuy, Bid
from .models_voting import BidVote
from .serializers_bid import BidSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vote_for_bid(request, groupbuy_id):
    """
    입찰에 투표하기
    """
    groupbuy = get_object_or_404(GroupBuy, id=groupbuy_id)
    bid_id = request.data.get('bid_id')
    
    if not bid_id:
        return Response(
            {'detail': '입찰을 선택해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    bid = get_object_or_404(Bid, id=bid_id, groupbuy=groupbuy)
    
    # 공구 상태 확인
    if groupbuy.status != 'voting':
        return Response(
            {'detail': '현재 투표 기간이 아닙니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 투표 시간 확인
    if groupbuy.voting_end and timezone.now() > groupbuy.voting_end:
        return Response(
            {'detail': '투표 시간이 종료되었습니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 참여자 확인
    if not groupbuy.participants.filter(id=request.user.id).exists():
        return Response(
            {'detail': '공구 참여자만 투표할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # 이미 투표했는지 확인
    existing_vote = BidVote.objects.filter(
        participant=request.user,
        groupbuy=groupbuy
    ).first()
    
    if existing_vote:
        # 기존 투표 수정
        existing_vote.bid = bid
        existing_vote.save()
        message = '투표가 수정되었습니다.'
    else:
        # 새로운 투표 생성
        BidVote.objects.create(
            participant=request.user,
            groupbuy=groupbuy,
            bid=bid
        )
        message = '투표가 완료되었습니다.'
    
    return Response({
        'message': message,
        'bid_id': bid.id
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_vote(request, groupbuy_id):
    """
    현재 사용자의 투표 상태 확인
    """
    groupbuy = get_object_or_404(GroupBuy, id=groupbuy_id)
    
    vote = BidVote.objects.filter(
        participant=request.user,
        groupbuy=groupbuy
    ).first()
    
    if not vote:
        return Response(
            {'detail': '아직 투표하지 않았습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response({
        'bid_id': vote.bid.id,
        'bid': BidSerializer(vote.bid).data,
        'voted_at': vote.created_at
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_voting_results(request, groupbuy_id):
    """
    공구의 투표 결과 조회
    - 투표 중: 현재 투표 수만 표시
    - 투표 종료: 상세 결과 표시
    """
    groupbuy = get_object_or_404(GroupBuy, id=groupbuy_id)
    
    # 참여자 또는 공구 생성자만 조회 가능
    is_participant = groupbuy.participants.filter(id=request.user.id).exists()
    is_creator = groupbuy.creator == request.user
    
    if not (is_participant or is_creator):
        return Response(
            {'detail': '권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # 입찰별 투표 수 집계
    bid_votes = Bid.objects.filter(groupbuy=groupbuy).annotate(
        vote_count=Count('votes')
    ).order_by('-vote_count')
    
    total_votes = BidVote.objects.filter(groupbuy=groupbuy).count()
    total_participants = groupbuy.current_participants
    
    # 투표가 종료되었는지 확인
    voting_ended = (
        groupbuy.status != 'voting' or 
        (groupbuy.voting_end and timezone.now() > groupbuy.voting_end)
    )
    
    results = []
    for bid in bid_votes:
        result = {
            'bid_id': bid.id,
            'seller': {
                'id': bid.seller.id,
                'username': bid.seller.username,
                'business_name': getattr(bid.seller, 'business_name', None)
            },
            'bid_type': bid.bid_type,
            'amount': bid.amount,
            'vote_count': bid.vote_count,
            'percentage': round((bid.vote_count / total_votes * 100) if total_votes > 0 else 0, 1)
        }
        
        # 투표가 종료된 경우에만 상세 정보 제공
        if voting_ended:
            result['is_winner'] = bid.vote_count == bid_votes.first().vote_count if bid_votes else False
        
        results.append(result)
    
    return Response({
        'voting_ended': voting_ended,
        'total_participants': total_participants,
        'total_votes': total_votes,
        'participation_rate': round((total_votes / total_participants * 100) if total_participants > 0 else 0, 1),
        'results': results,
        'voting_end_time': groupbuy.voting_end
    })