from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from .models import GroupBuy, Participation, Bid, User
from .models import Notification
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buyer_final_decision(request, groupbuy_id):
    """
    구매자의 최종선택 처리 (구매확정/구매포기)
    """
    user = request.user
    decision = request.data.get('decision')  # 'confirmed' or 'cancelled'
    
    if decision not in ['confirmed', 'cancelled']:
        return Response(
            {'error': '올바르지 않은 선택입니다. confirmed 또는 cancelled 중 선택해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # 공구 조회
        groupbuy = GroupBuy.objects.get(id=groupbuy_id)
        
        # 공구 상태 확인
        if groupbuy.status == 'completed':
            # 이미 완료된 공구의 경우, 사용자의 최종선택 상태를 확인
            try:
                participation = Participation.objects.get(user=user, groupbuy=groupbuy)
                if participation.final_decision == 'confirmed':
                    return Response(
                        {'message': '이미 구매확정을 완료한 공구입니다.'},
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {'error': '이미 종료된 공구입니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Participation.DoesNotExist:
                return Response(
                    {'error': '참여하지 않은 공구입니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif groupbuy.status not in ['final_selection_buyers']:
            return Response(
                {'error': '구매자 최종선택이 가능한 상태가 아닙니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 구매자 최종선택 기간 확인 (12시간)
        if groupbuy.final_selection_end:
            deadline = groupbuy.final_selection_end
            if timezone.now() > deadline:
                return Response(
                    {'error': '구매자 최종선택 기간이 종료되었습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 참여 정보 조회
        participation = Participation.objects.get(user=user, groupbuy=groupbuy)
        
        # 이미 최종선택을 한 경우
        if participation.final_decision != 'pending':
            return Response(
                {'error': '이미 최종선택을 완료했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최종선택 처리
        with transaction.atomic():
            participation.final_decision = decision
            participation.final_decision_at = timezone.now()
            participation.save()
            
            # 알림 발송
            if decision == 'confirmed':
                message = f"{groupbuy.title} 공구를 구매확정하셨습니다. 판매자 정보는 마이페이지에서 확인하세요."
            else:
                message = f"{groupbuy.title} 공구를 구매포기하셨습니다."
            
            Notification.objects.create(
                user=user,
                groupbuy=groupbuy,
                message=message
            )
            
            # 모든 구매자가 최종선택을 완료했는지 확인
            check_buyer_decisions_completed(groupbuy)
        
        return Response({
            'success': True,
            'decision': decision,
            'message': '최종선택이 완료되었습니다.'
        })
        
    except GroupBuy.DoesNotExist:
        return Response(
            {'error': '공구를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Participation.DoesNotExist:
        return Response(
            {'error': '해당 공구에 참여하지 않았습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"구매자 최종선택 오류: {str(e)}")
        return Response(
            {'error': '최종선택 처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seller_final_decision(request, groupbuy_id):
    """
    판매자의 최종선택 처리 (판매확정/판매포기)
    """
    user = request.user
    decision = request.data.get('decision')  # 'confirmed' or 'cancelled'
    
    if decision not in ['confirmed', 'cancelled']:
        return Response(
            {'error': '올바르지 않은 선택입니다. confirmed 또는 cancelled 중 선택해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # 공구 조회
        groupbuy = GroupBuy.objects.get(id=groupbuy_id)
        
        # 공구 상태 확인
        if groupbuy.status == 'completed':
            # 이미 완료된 공구의 경우, 판매자의 최종선택 상태를 확인
            try:
                bid = Bid.objects.get(seller=user, groupbuy=groupbuy, is_selected=True)
                if bid.final_decision == 'confirmed':
                    return Response(
                        {'message': '이미 판매확정을 완료한 공구입니다.'},
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {'error': '이미 종료된 공구입니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Bid.DoesNotExist:
                return Response(
                    {'error': '낙찰받지 못한 공구입니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif groupbuy.status not in ['final_selection_seller']:
            return Response(
                {'error': '판매자 최종선택이 가능한 상태가 아닙니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 판매자 최종선택 기간 확인 (6시간)
        if groupbuy.seller_selection_end:
            deadline = groupbuy.seller_selection_end
            if timezone.now() > deadline:
                return Response(
                    {'error': '판매자 최종선택 기간이 종료되었습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 낙찰된 입찰 조회
        bid = Bid.objects.get(
            groupbuy=groupbuy,
            seller=user,
            status='selected'
        )
        
        # 이미 최종선택을 한 경우
        if bid.final_decision != 'pending':
            return Response(
                {'error': '이미 최종선택을 완료했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최종선택 처리
        with transaction.atomic():
            bid.final_decision = decision
            bid.final_decision_at = timezone.now()
            bid.save()
            
            # 판매포기시 패널티 처리
            penalty_message = ""
            if decision == 'cancelled':
                # 구매 확정률 계산
                confirmed_count = groupbuy.participation_set.filter(final_decision='confirmed').count()
                total_count = groupbuy.participation_set.count()
                confirmation_rate = confirmed_count / total_count if total_count > 0 else 0
                
                # 50% 초과인 경우에만 패널티 부과
                if confirmation_rate > 0.5:
                    try:
                        user_profile = user.userprofile
                        user_profile.penalty_points += 10
                        user_profile.save()
                        penalty_message = f" 판매포기로 패널티 10점이 부과되었습니다. (구매확정률: {int(confirmation_rate*100)}%)"
                    except:
                        pass
                else:
                    penalty_message = f" 구매확정률이 50% 이하여서 패널티가 면제되었습니다. (구매확정률: {int(confirmation_rate*100)}%)"
                    
                    # 입찰권 환불 처리 (단품 입찰권만, 무제한 구독권 제외)
                    if bid.bid_token and bid.bid_token.token_type == 'single':
                        try:
                            # 입찰권 상태를 다시 활성으로 변경
                            bid.bid_token.status = 'active'
                            bid.bid_token.used_at = None
                            bid.bid_token.used_for = None
                            bid.bid_token.save()
                            
                            # 입찰과 입찰권 연결 해제
                            bid.bid_token = None
                            bid.save()
                            
                            penalty_message += " 사용한 입찰권이 환불되었습니다."
                            logger.info(f"입찰권 환불 완료 - 사용자: {user.id}, 공구: {groupbuy.id}")
                        except Exception as e:
                            logger.error(f"입찰권 환불 실패: {str(e)}")
                            # 환불 실패해도 계속 진행
            
            # 알림 발송
            if decision == 'confirmed':
                message = f"{groupbuy.title} 공구를 판매확정하셨습니다. 구매자 정보는 마이페이지에서 확인하세요."
            else:
                message = f"{groupbuy.title} 공구를 판매포기하셨습니다.{penalty_message}"
            
            Notification.objects.create(
                user=user,
                groupbuy=groupbuy,
                message=message
            )
            
            # 판매자 최종선택 완료 처리
            check_seller_decision_completed(groupbuy)
        
        return Response({
            'success': True,
            'decision': decision,
            'message': '최종선택이 완료되었습니다.'
        })
        
    except GroupBuy.DoesNotExist:
        return Response(
            {'error': '공구를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Bid.DoesNotExist:
        return Response(
            {'error': '낙찰된 입찰을 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"판매자 최종선택 오류: {str(e)}")
        return Response(
            {'error': '최종선택 처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_final_decision_status(request, groupbuy_id):
    """
    현재 사용자의 최종선택 상태 조회
    """
    user = request.user
    
    try:
        groupbuy = GroupBuy.objects.get(id=groupbuy_id)
        
        # 구매자인 경우
        if user.role == 'buyer':
            try:
                participation = Participation.objects.get(user=user, groupbuy=groupbuy)
                return Response({
                    'role': 'buyer',
                    'decision': participation.final_decision,
                    'decision_at': participation.final_decision_at,
                    'deadline': groupbuy.final_selection_end,
                    'groupbuy_status': groupbuy.status
                })
            except Participation.DoesNotExist:
                return Response({
                    'error': '해당 공구에 참여하지 않았습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # 판매자인 경우
        elif user.role == 'seller':
            try:
                bid = Bid.objects.get(
                    groupbuy=groupbuy,
                    seller=user,
                    status='selected'
                )
                return Response({
                    'role': 'seller',
                    'decision': bid.final_decision,
                    'decision_at': bid.final_decision_at,
                    'deadline': groupbuy.seller_selection_end,
                    'groupbuy_status': groupbuy.status
                })
            except Bid.DoesNotExist:
                return Response({
                    'error': '낙찰된 입찰이 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
        
        else:
            return Response({
                'error': '권한이 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
            
    except GroupBuy.DoesNotExist:
        return Response(
            {'error': '공구를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_contact_info(request, groupbuy_id):
    """
    최종선택 완료 후 연락처 정보 조회
    """
    user = request.user
    
    try:
        groupbuy = GroupBuy.objects.get(id=groupbuy_id)
        
        # 구매자인 경우 - 판매자 정보 조회
        if user.role == 'buyer':
            participation = Participation.objects.filter(user=user, groupbuy=groupbuy).first()
            if not participation or participation.final_decision != 'confirmed':
                return Response(
                    {'error': '구매확정 후에만 연락처를 확인할 수 있습니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            winning_bid = Bid.objects.filter(groupbuy=groupbuy, status='selected').first()
            if winning_bid and winning_bid.seller:
                seller = winning_bid.seller
                return Response({
                    'role': 'seller',
                    'name': seller.username,
                    'phone': seller.phone_number,
                    'business_name': seller.business_name if hasattr(seller, 'business_name') else None,
                    'business_number': seller.business_number if hasattr(seller, 'business_number') else None,
                    'address': seller.address_detail if hasattr(seller, 'address_detail') else None
                })
        
        # 판매자인 경우 - 구매자들 정보 조회
        elif user.role == 'seller':
            bid = Bid.objects.filter(groupbuy=groupbuy, seller=user, status='selected').first()
            if not bid or bid.final_decision != 'confirmed':
                return Response(
                    {'error': '판매확정 후에만 연락처를 확인할 수 있습니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            participations = Participation.objects.filter(
                groupbuy=groupbuy,
                final_decision='confirmed'
            ).select_related('user')
            
            buyers_info = []
            for p in participations:
                buyers_info.append({
                    'name': p.user.username,
                    'phone': p.user.phone_number,
                    'address': p.user.address_detail if hasattr(p.user, 'address_detail') else None
                })
            
            return Response({
                'role': 'buyers',
                'buyers': buyers_info,
                'total_count': len(buyers_info)
            })
        
        else:
            return Response(
                {'error': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
    except GroupBuy.DoesNotExist:
        return Response(
            {'error': '공구를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )


def check_buyer_decisions_completed(groupbuy):
    """
    모든 구매자의 최종선택이 완료되었는지 확인하고
    완료된 경우 판매자 최종선택 단계로 전환
    """
    # 구매자들의 최종선택 확인
    participations = Participation.objects.filter(groupbuy=groupbuy)
    buyer_decisions_completed = all(p.final_decision != 'pending' for p in participations)
    
    if buyer_decisions_completed:
        confirmed_count = participations.filter(final_decision='confirmed').count()
        total_count = participations.count()
        
        if confirmed_count > 0:
            # 판매자 최종선택 단계로 전환
            groupbuy.status = 'final_selection_seller'
            groupbuy.seller_selection_end = timezone.now() + timezone.timedelta(hours=6)
            groupbuy.save()
            
            # 판매자에게 알림
            winning_bid = Bid.objects.filter(groupbuy=groupbuy, status='selected').first()
            if winning_bid:
                Notification.objects.create(
                    user=winning_bid.seller,
                    groupbuy=groupbuy,
                    message=f"{groupbuy.title} 공구의 판매자 최종 선택이 시작되었습니다. 6시간 내에 판매 확정/포기를 선택해주세요. (구매확정: {confirmed_count}/{total_count}명)"
                )
        else:
            # 구매 확정자가 없으면 공구 취소
            groupbuy.status = 'cancelled'
            groupbuy.save()


def check_seller_decision_completed(groupbuy):
    """
    판매자의 최종선택이 완료되었는지 확인하고
    공구를 완료 또는 취소 처리
    """
    winning_bid = Bid.objects.filter(groupbuy=groupbuy, status='selected').first()
    
    if winning_bid and winning_bid.final_decision != 'pending':
        confirmed_participants = groupbuy.participation_set.filter(final_decision='confirmed').exists()
        
        if confirmed_participants and winning_bid.final_decision == 'confirmed':
            # 공구 성공
            groupbuy.status = 'completed'
            groupbuy.save()
            
            # 성공 알림
            message = f"{groupbuy.title} 공구가 성공적으로 완료되었습니다!"
            
            # 구매 확정한 참여자들에게 알림
            confirmed_participations = groupbuy.participation_set.filter(final_decision='confirmed')
            for participation in confirmed_participations:
                Notification.objects.create(
                    user=participation.user,
                    groupbuy=groupbuy,
                    message=message
                )
        else:
            # 공구 취소
            groupbuy.status = 'cancelled'
            groupbuy.save()


