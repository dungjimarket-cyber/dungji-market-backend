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
        
        # 공구 상태 확인 (voting 상태여야 함)
        if groupbuy.status not in ['voting', 'final_selection']:
            return Response(
                {'error': '최종선택이 가능한 상태가 아닙니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최종선택 기간 확인 (투표 종료 후 12시간 이내)
        if groupbuy.final_selection_end:
            deadline = groupbuy.final_selection_end
            if timezone.now() > deadline:
                return Response(
                    {'error': '최종선택 기간이 종료되었습니다.'},
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
            
            # 모든 참여자가 최종선택을 완료했는지 확인
            check_all_decisions_completed(groupbuy)
        
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
        if groupbuy.status not in ['voting', 'final_selection', 'seller_confirmation']:
            return Response(
                {'error': '최종선택이 가능한 상태가 아닙니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최종선택 기간 확인
        if groupbuy.final_selection_end:
            deadline = groupbuy.final_selection_end
            if timezone.now() > deadline:
                return Response(
                    {'error': '최종선택 기간이 종료되었습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 낙찰된 입찰 조회
        bid = Bid.objects.get(
            groupbuy=groupbuy,
            seller=user,
            is_selected=True
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
            
            # 판매포기시 패널티 부과
            if decision == 'cancelled':
                user.penalty_count += 1  # 패널티 횟수 증가
                user.save()
                penalty_message = " 판매포기로 패널티가 부과되었습니다."
            else:
                penalty_message = ""
            
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
            
            # 모든 선택이 완료되었는지 확인
            check_all_decisions_completed(groupbuy)
        
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
                    'deadline': groupbuy.final_selection_end
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
                    is_selected=True
                )
                return Response({
                    'role': 'seller',
                    'decision': bid.final_decision,
                    'decision_at': bid.final_decision_at,
                    'deadline': groupbuy.final_selection_end
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
            
            winning_bid = Bid.objects.filter(groupbuy=groupbuy, is_selected=True).first()
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
            bid = Bid.objects.filter(groupbuy=groupbuy, seller=user, is_selected=True).first()
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


def check_all_decisions_completed(groupbuy):
    """
    모든 참여자와 판매자의 최종선택이 완료되었는지 확인하고
    완료된 경우 공구 상태를 업데이트
    """
    # 구매자들의 최종선택 확인
    participations = Participation.objects.filter(groupbuy=groupbuy)
    buyer_decisions_completed = all(p.final_decision != 'pending' for p in participations)
    
    # 판매자의 최종선택 확인
    winning_bid = Bid.objects.filter(groupbuy=groupbuy, is_selected=True).first()
    seller_decision_completed = winning_bid and winning_bid.final_decision != 'pending'
    
    # 모두 완료된 경우 공구 상태 업데이트
    if buyer_decisions_completed and seller_decision_completed:
        groupbuy.status = 'completed'
        groupbuy.save()
        
        # 완료 알림 발송
        message = f"{groupbuy.title} 공구의 최종선택이 모두 완료되었습니다."
        
        # 모든 참여자에게 알림
        for participation in participations:
            Notification.objects.create(
                user=participation.user,
                groupbuy=groupbuy,
                message=message
            )
        
        # 판매자에게도 알림
        if winning_bid:
            Notification.objects.create(
                user=winning_bid.seller,
                groupbuy=groupbuy,
                message=message
            )


