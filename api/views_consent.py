from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import ParticipantConsent, Participation, GroupBuy, Bid
from .serializers import ParticipantConsentSerializer, ParticipantConsentUpdateSerializer
import logging

logger = logging.getLogger(__name__)


class ParticipantConsentViewSet(viewsets.ModelViewSet):
    """참여자 동의 관련 ViewSet"""
    serializer_class = ParticipantConsentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """현재 사용자의 동의 요청만 조회"""
        user = self.request.user
        return ParticipantConsent.objects.filter(
            participation__user=user
        ).select_related('participation', 'bid', 'participation__groupbuy')
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """대기 중인 동의 요청 목록"""
        pending_consents = self.get_queryset().filter(
            status='pending',
            consent_deadline__gt=timezone.now()
        )
        
        # 만료된 동의 요청 자동 업데이트
        expired_consents = self.get_queryset().filter(
            status='pending',
            consent_deadline__lte=timezone.now()
        )
        for consent in expired_consents:
            consent.check_expiry()
        
        serializer = self.get_serializer(pending_consents, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """동의 상태 업데이트 (동의/거부)"""
        consent = self.get_object()
        
        # 이미 처리된 동의인지 확인
        if consent.status != 'pending':
            return Response(
                {'error': '이미 처리된 동의 요청입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 만료 확인
        if consent.check_expiry():
            return Response(
                {'error': '동의 기한이 만료되었습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ParticipantConsentUpdateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.update(consent, serializer.validated_data)
            
            # 공구의 모든 동의 상태 확인
            groupbuy = consent.participation.groupbuy
            consent_status = groupbuy.check_all_consents()
            
            # 모든 참여자가 동의했거나 진행 가능한 경우
            if consent_status['can_proceed']:
                # 동의하지 않은 참여자 제외 처리
                disagreed_participations = Participation.objects.filter(
                    groupbuy=groupbuy,
                    consent__status__in=['disagreed', 'expired']
                )
                for participation in disagreed_participations:
                    participation.delete()
                    logger.info(f"참여자 {participation.user.username}이(가) 공구 {groupbuy.title}에서 제외되었습니다.")
                
                # 공구 상태 업데이트
                groupbuy.status = 'seller_confirmation'
                groupbuy.save()
            
            response_serializer = ParticipantConsentSerializer(consent)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def groupbuy_status(self, request):
        """특정 공구의 동의 현황 조회"""
        groupbuy_id = request.query_params.get('groupbuy_id')
        if not groupbuy_id:
            return Response(
                {'error': 'groupbuy_id가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        groupbuy = get_object_or_404(GroupBuy, id=groupbuy_id)
        
        # 사용자가 해당 공구의 참여자인지 확인
        if not Participation.objects.filter(groupbuy=groupbuy, user=request.user).exists():
            return Response(
                {'error': '해당 공구의 참여자가 아닙니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        consent_status = groupbuy.check_all_consents()
        
        # 개별 동의 상태 추가
        consents = ParticipantConsent.objects.filter(
            participation__groupbuy=groupbuy
        ).select_related('participation__user')
        
        consent_details = []
        for consent in consents:
            consent_details.append({
                'user': consent.participation.user.username,
                'status': consent.get_status_display(),
                'agreed_at': consent.agreed_at,
                'disagreed_at': consent.disagreed_at
            })
        
        return Response({
            'summary': consent_status,
            'details': consent_details
        })


@action(detail=True, methods=['post'], url_path='start-consent')
def start_consent_process(request, pk=None):
    """관리자가 특정 공구의 동의 프로세스를 시작"""
    groupbuy = get_object_or_404(GroupBuy, pk=pk)
    
    # 관리자 권한 확인
    if not request.user.is_staff:
        return Response(
            {'error': '관리자 권한이 필요합니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # 선택된 제안 확인
    bid_id = request.data.get('bid_id')
    if not bid_id:
        return Response(
            {'error': 'bid_id가 필요합니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    selected_bid = get_object_or_404(Bid, id=bid_id, groupbuy=groupbuy)
    
    # 동의 프로세스 시작
    consent_hours = request.data.get('consent_hours', 24)
    groupbuy.start_consent_process(selected_bid, consent_hours)
    
    return Response({
        'message': f'동의 프로세스가 시작되었습니다. 마감: {consent_hours}시간 후',
        'groupbuy_id': groupbuy.id,
        'selected_bid_id': selected_bid.id
    })