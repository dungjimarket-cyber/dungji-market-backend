"""
노쇼 신고 관련 API 뷰
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import NoShowReport, GroupBuy, User, Participation
from .serializers import NoShowReportSerializer
from django.db.models import Q
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class NoShowReportViewSet(ModelViewSet):
    """
    노쇼 신고 관리 ViewSet
    """
    serializer_class = NoShowReportSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # 파일 업로드 지원
    
    def get_queryset(self):
        """
        현재 사용자가 신고한 내역 또는 받은 신고 내역 조회
        """
        user = self.request.user
        queryset = NoShowReport.objects.select_related(
            'reporter', 'reported_user', 'groupbuy', 'bid', 'participation'
        )
        
        # 쿼리 파라미터로 필터링
        report_type = self.request.query_params.get('type')
        if report_type == 'made':
            # 내가 신고한 내역
            queryset = queryset.filter(reporter=user)
        elif report_type == 'received':
            # 내가 받은 신고 내역
            queryset = queryset.filter(reported_user=user)
        else:
            # 기본: 내가 관련된 모든 신고 내역
            queryset = queryset.filter(Q(reporter=user) | Q(reported_user=user))
        
        # 공구별 필터링
        groupbuy_id = self.request.query_params.get('groupbuy_id')
        if groupbuy_id:
            queryset = queryset.filter(groupbuy_id=groupbuy_id)
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        신고 생성 (파일 업로드 처리 포함)
        """
        # 기본 데이터 복사
        data = request.data.copy()
        
        # 파일 처리 - evidence_image_1, evidence_image_2, evidence_image_3 형식으로 오는 파일들 처리
        files_to_save = {}
        
        # 기존 evidence_image 필드 처리 (backward compatibility)
        if 'evidence_image' in request.FILES:
            files_to_save['evidence_image'] = request.FILES['evidence_image']
        
        # 새로운 형식의 파일들 처리 (evidence_image_1, evidence_image_2, evidence_image_3)
        for i in range(1, 4):
            file_key = f'evidence_image_{i}'
            if file_key in request.FILES:
                if i == 1:
                    files_to_save['evidence_image'] = request.FILES[file_key]
                elif i == 2:
                    files_to_save['evidence_image_2'] = request.FILES[file_key]
                elif i == 3:
                    files_to_save['evidence_image_3'] = request.FILES[file_key]
        
        # 시리얼라이저 생성
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        # 파일과 함께 저장
        instance = serializer.save(reporter=request.user, **files_to_save)
        
        # 로깅
        logger.info(f"노쇼 신고 생성: {instance.reporter} -> {instance.reported_user} ({instance.groupbuy.title})")
        logger.info(f"파일 업로드: evidence_image={bool(instance.evidence_image)}, "
                   f"evidence_image_2={bool(instance.evidence_image_2)}, "
                   f"evidence_image_3={bool(instance.evidence_image_3)}")
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """
        신고 수정 (파일 업로드 처리 포함)
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # 수정 가능 여부 확인
        if not instance.can_edit():
            return Response({
                'error': '수정할 수 없는 신고입니다. (처리중 상태에서만 1회 수정 가능)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 수정 권한 확인
        if instance.reporter != request.user:
            return Response({
                'error': '본인의 신고만 수정할 수 있습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 기본 데이터 복사
        data = request.data.copy()
        
        # 파일 처리
        files_to_save = {}
        
        # 기존 evidence_image 필드 처리
        if 'evidence_image' in request.FILES:
            files_to_save['evidence_image'] = request.FILES['evidence_image']
        
        # 새로운 형식의 파일들 처리
        for i in range(1, 4):
            file_key = f'evidence_image_{i}'
            if file_key in request.FILES:
                if i == 1:
                    files_to_save['evidence_image'] = request.FILES[file_key]
                elif i == 2:
                    files_to_save['evidence_image_2'] = request.FILES[file_key]
                elif i == 3:
                    files_to_save['evidence_image_3'] = request.FILES[file_key]
        
        # 시리얼라이저로 업데이트
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # 수정 횟수 및 시간 업데이트
        instance.edit_count += 1
        instance.last_edited_at = timezone.now()
        
        # 파일과 함께 저장
        instance = serializer.save(**files_to_save)
        
        # 로깅
        logger.info(f"노쇼 신고 수정: {instance.id} (수정 {instance.edit_count}회)")
        logger.info(f"파일 업로드: evidence_image={bool(instance.evidence_image)}, "
                   f"evidence_image_2={bool(instance.evidence_image_2)}, "
                   f"evidence_image_3={bool(instance.evidence_image_3)}")
        
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """
        신고 목록 조회 - 피신고 내역은 제한된 정보만 반환
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data
        
        # 피신고 내역은 제한된 정보만 반환
        report_type = request.query_params.get('type')
        if report_type == 'received':
            # 피신고 내역일 경우 민감한 정보 제거
            limited_data = []
            for item in data:
                limited_item = {
                    'id': item.get('id'),
                    'groupbuy_id': item.get('groupbuy'),
                    'groupbuy_title': item.get('groupbuy_title'),
                    'report_type': item.get('report_type'),
                    'status': item.get('status'),
                    'created_at': item.get('created_at'),
                    'processed_at': item.get('processed_at'),
                    'admin_comment': item.get('admin_comment'),
                    # 신고자 정보, 신고 내용, 증빙자료는 제외
                }
                limited_data.append(limited_item)
            data = limited_data
        
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)
    
    def perform_create(self, serializer):
        """
        신고 생성 시 신고자 자동 설정
        """
        serializer.save(reporter=self.request.user)
        
        # 노쇼 신고 알림 발송
        instance = serializer.instance
        logger.info(f"노쇼 신고 생성: {instance.reporter} -> {instance.reported_user} ({instance.groupbuy.title})")
        
        # TODO: 알림 서비스 연동
    
    @action(detail=True, methods=['get'])
    def can_edit(self, request, pk=None):
        """수정 가능 여부 확인"""
        report = self.get_object()
        
        if report.reporter != request.user:
            return Response({
                'can_edit': False, 
                'reason': '본인의 신고만 수정 가능합니다.'
            })
        
        if report.status != 'pending':
            status_label = dict(report.REPORT_STATUS_CHOICES).get(report.status, report.status)
            return Response({
                'can_edit': False, 
                'reason': f'{status_label} 상태에서는 수정할 수 없습니다.'
            })
        
        if report.edit_count >= 1:
            return Response({
                'can_edit': False, 
                'reason': '이미 1회 수정하였습니다. 재수정은 불가능합니다.'
            })
        
        return Response({
            'can_edit': True, 
            'edit_count': report.edit_count,
            'message': '수정 가능합니다. (1회만 가능)'
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """노쇼 신고 취소"""
        report = self.get_object()
        
        # 취소 권한 확인
        if report.reporter != request.user:
            return Response({
                'error': '본인의 신고만 취소할 수 있습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 취소 가능 여부 확인
        if not report.can_cancel():
            return Response({
                'error': '처리중 상태에서만 취소 가능합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        groupbuy = report.groupbuy
        message = ''
        
        # 신고자가 판매자인 경우: 공구를 판매완료로 변경
        if request.user.role == 'seller' or request.user.user_type == '판매':
            groupbuy.status = 'completed'
            groupbuy.completed_at = timezone.now()
            groupbuy.save()
            
            message = '노쇼 신고가 취소되었습니다. 공구가 판매완료로 처리되었습니다.'
            logger.info(f"판매자의 노쇼 신고 취소로 공구 {groupbuy.id} 판매완료 처리")
        
        # 신고자가 구매자인 경우: 구매완료 처리
        else:
            # 해당 구매자의 참여 정보 찾기
            participation = Participation.objects.filter(
                groupbuy=groupbuy,
                user=request.user
            ).first()
            
            if participation:
                participation.status = 'completed'
                participation.save()
                
                # 모든 구매자가 구매완료했는지 확인
                all_completed = not Participation.objects.filter(
                    groupbuy=groupbuy,
                    final_decision='confirmed'
                ).exclude(status='completed').exists()
                
                if all_completed:
                    groupbuy.status = 'completed'
                    groupbuy.completed_at = timezone.now()
                    groupbuy.save()
                    message = '노쇼 신고가 취소되었습니다. 구매완료 처리되었으며, 모든 거래가 완료되어 공구가 종료되었습니다.'
                else:
                    message = '노쇼 신고가 취소되었습니다. 구매완료 처리되었습니다.'
                
                logger.info(f"구매자의 노쇼 신고 취소로 구매완료 처리 (사용자: {request.user.id}, 공구: {groupbuy.id})")
        
        # 노쇼 신고 삭제
        report_id = report.id
        report.delete()
        
        logger.info(f"노쇼 신고 {report_id} 취소됨")
        
        return Response({
            'message': message,
            'groupbuy_status': groupbuy.status
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def confirm(self, request, pk=None):
        """관리자가 노쇼 신고 처리완료"""
        report = self.get_object()
        
        if report.status != 'pending':
            return Response({
                'error': '이미 처리된 신고입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 신고 상태를 처리완료로 변경
        report.status = 'completed'
        report.admin_comment = request.data.get('admin_comment', '')
        report.processed_at = timezone.now()
        report.processed_by = request.user
        report.save()
        
        # 해당 공구의 상태 처리
        groupbuy = report.groupbuy
        action_taken = 'confirmed_only'
        message = '노쇼 신고가 처리완료되었습니다.'
        
        # 신고 유형에 따라 처리 분기
        if report.report_type == 'seller_noshow':
            # 구매자가 판매자를 노쇼 신고한 경우 -> 공구 취소
            groupbuy.status = 'cancelled'
            groupbuy.cancellation_reason = '판매자 노쇼로 인한 공구 취소'
            groupbuy.save()
            
            action_taken = 'cancelled'
            message = '판매자 노쇼로 공구가 취소되었습니다.'
            
            logger.info(f"판매자 노쇼로 공구 {groupbuy.id} 취소 처리")
            
        else:
            # 판매자가 구매자를 노쇼 신고한 경우 (기존 로직)
            # 구매확정된 전체 참여자 수
            confirmed_participants = Participation.objects.filter(
                groupbuy=groupbuy,
                final_decision='confirmed'
            )
            confirmed_count = confirmed_participants.count()
            
            # 노쇼 신고된 구매자 수 (처리완료된 신고만)
            noshow_reports = NoShowReport.objects.filter(
                groupbuy=groupbuy,
                status='completed'
            )
            
            # 중복 제거된 노쇼 구매자 ID 목록
            noshow_buyer_ids = set()
            for noshow_report in noshow_reports:
                if noshow_report.noshow_buyers:
                    noshow_buyer_ids.update(noshow_report.noshow_buyers)
                # 기존 단일 신고 방식도 지원
                if noshow_report.reported_user:
                    noshow_buyer_ids.add(noshow_report.reported_user.id)
            
            noshow_count = len(noshow_buyer_ids)
            
            if confirmed_count > 0 and noshow_count == confirmed_count:
                # 전원 노쇼인 경우 -> 공구 취소
                groupbuy.status = 'cancelled'
                groupbuy.cancellation_reason = '구매자 전원 노쇼로 인한 공구 취소'
                groupbuy.save()
                
                action_taken = 'cancelled'
                message = '구매자 전원 노쇼로 공구가 취소되었습니다.'
                
                logger.info(f"공구 {groupbuy.id} 전원 노쇼로 취소 처리")
                
            elif noshow_count > 0 and noshow_count < confirmed_count:
                # 일부만 노쇼인 경우 -> 판매완료
                groupbuy.status = 'completed'
                groupbuy.completed_at = timezone.now()
                groupbuy.save()
                
                action_taken = 'completed'
                message = f'노쇼 {noshow_count}명 제외하고 거래가 완료되었습니다.'
                
                logger.info(f"공구 {groupbuy.id} 부분 노쇼로 판매완료 처리")
        
        return Response({
            'status': 'success',
            'action': action_taken,
            'message': message,
            'noshow_count': noshow_count,
            'confirmed_count': confirmed_count,
            'groupbuy_status': groupbuy.status
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def hold(self, request, pk=None):
        """관리자가 노쇼 신고를 보류중으로 변경"""
        report = self.get_object()
        
        if report.status == 'completed':
            return Response({
                'error': '이미 처리완료된 신고는 보류할 수 없습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        report.status = 'on_hold'
        report.admin_comment = request.data.get('admin_comment', '')
        report.processed_at = timezone.now()
        report.processed_by = request.user
        report.save()
        
        logger.info(f"노쇼 신고 {report.id} 보류 처리")
        
        return Response({
            'message': '노쇼 신고가 보류 처리되었습니다.',
            'status': report.status
        })
        # notification_service.send_noshow_report_notification(instance)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_noshow_report_eligibility(request):
    """
    노쇼 신고 가능 여부 확인
    
    Query Parameters:
    - groupbuy_id: 공구 ID
    - user_id: 신고 대상 사용자 ID
    - report_type: 신고 유형 (buyer_noshow, seller_noshow)
    """
    groupbuy_id = request.query_params.get('groupbuy_id')
    user_id = request.query_params.get('user_id')
    report_type = request.query_params.get('report_type')
    
    if not all([groupbuy_id, user_id, report_type]):
        return Response({
            'error': '필수 파라미터가 누락되었습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        groupbuy = GroupBuy.objects.get(id=groupbuy_id)
        reported_user = User.objects.get(id=user_id)
    except (GroupBuy.DoesNotExist, User.DoesNotExist):
        return Response({
            'error': '잘못된 공구 또는 사용자 ID입니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = request.user
    
    # 이미 신고했는지 확인
    existing_report = NoShowReport.objects.filter(
        reporter=user,
        reported_user=reported_user,
        groupbuy=groupbuy
    ).exists()
    
    if existing_report:
        return Response({
            'eligible': False,
            'reason': '이미 해당 사용자를 신고했습니다.'
        })
    
    # 신고 유형별 자격 확인
    if report_type == 'buyer_noshow':
        # 판매자가 구매자를 신고
        if user.role != 'seller':
            return Response({
                'eligible': False,
                'reason': '구매자 노쇼는 판매자만 신고할 수 있습니다.'
            })
        
        # 해당 공구에서 선택된 입찰이 있는지 확인
        from .models_bid import Bid
        selected_bid = Bid.objects.filter(
            groupbuy=groupbuy,
            seller=user,
            status='accepted'
        ).exists()
        
        if not selected_bid:
            return Response({
                'eligible': False,
                'reason': '해당 공구에서 선택된 입찰이 없습니다.'
            })
        
        # 신고 대상이 참여자인지 확인
        from .models import Participation
        is_participant = Participation.objects.filter(
            user=reported_user,
            groupbuy=groupbuy
        ).exists()
        
        if not is_participant:
            return Response({
                'eligible': False,
                'reason': '신고 대상이 해당 공구 참여자가 아닙니다.'
            })
        
    elif report_type == 'seller_noshow':
        # 구매자가 판매자를 신고
        if user.role != 'buyer':
            return Response({
                'eligible': False,
                'reason': '판매자 노쇼는 구매자만 신고할 수 있습니다.'
            })
        
        # 신고자가 참여자인지 확인
        from .models import Participation
        is_participant = Participation.objects.filter(
            user=user,
            groupbuy=groupbuy
        ).exists()
        
        if not is_participant:
            return Response({
                'eligible': False,
                'reason': '해당 공구에 참여하지 않았습니다.'
            })
        
        # 신고 대상이 선택된 판매자인지 확인
        from .models_bid import Bid
        is_selected_seller = Bid.objects.filter(
            groupbuy=groupbuy,
            seller=reported_user,
            status='accepted'
        ).exists()
        
        if not is_selected_seller:
            return Response({
                'eligible': False,
                'reason': '신고 대상이 선택된 판매자가 아닙니다.'
            })
    
    else:
        return Response({
            'eligible': False,
            'reason': '잘못된 신고 유형입니다.'
        })
    
    return Response({
        'eligible': True,
        'message': '노쇼 신고가 가능합니다.'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_report_buyer_noshow(request):
    """
    판매자가 여러 구매자를 일괄 노쇼 신고
    
    Request Body:
    {
        "groupbuy_id": 123,
        "reported_users": [
            {"user_id": 1, "content": "연락 두절"},
            {"user_id": 2, "content": "거래 불이행"}
        ]
    }
    """
    user = request.user
    
    # 판매자 권한 확인
    if user.role != 'seller':
        return Response({
            'error': '구매자 노쇼는 판매자만 신고할 수 있습니다.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    groupbuy_id = request.data.get('groupbuy_id')
    reported_users = request.data.get('reported_users', [])
    
    if not groupbuy_id or not reported_users:
        return Response({
            'error': '필수 데이터가 누락되었습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        groupbuy = GroupBuy.objects.get(id=groupbuy_id)
    except GroupBuy.DoesNotExist:
        return Response({
            'error': '존재하지 않는 공구입니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 해당 공구에서 선택된 입찰이 있는지 확인
    from .models_bid import Bid
    selected_bid = Bid.objects.filter(
        groupbuy=groupbuy,
        seller=user,
        status='accepted'
    ).first()
    
    if not selected_bid:
        return Response({
            'error': '해당 공구에서 선택된 입찰이 없습니다.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # 참여자 목록 가져오기
    from .models import Participation
    valid_participants = Participation.objects.filter(
        groupbuy=groupbuy
    ).values_list('user_id', flat=True)
    
    success_reports = []
    failed_reports = []
    
    for report_data in reported_users:
        user_id = report_data.get('user_id')
        content = report_data.get('content', '노쇼 신고')
        
        try:
            reported_user = User.objects.get(id=user_id)
            
            # 참여자인지 확인
            if user_id not in valid_participants:
                failed_reports.append({
                    'user_id': user_id,
                    'reason': '해당 공구 참여자가 아닙니다.'
                })
                continue
            
            # 이미 신고했는지 확인
            existing_report = NoShowReport.objects.filter(
                reporter=user,
                reported_user=reported_user,
                groupbuy=groupbuy
            ).exists()
            
            if existing_report:
                failed_reports.append({
                    'user_id': user_id,
                    'reason': '이미 신고된 사용자입니다.'
                })
                continue
            
            # 신고 생성
            report = NoShowReport.objects.create(
                reporter=user,
                reported_user=reported_user,
                groupbuy=groupbuy,
                bid=selected_bid,
                report_type='buyer_noshow',
                content=content
            )
            
            success_reports.append({
                'user_id': user_id,
                'report_id': report.id,
                'message': '신고가 접수되었습니다.'
            })
            
            logger.info(f"배치 노쇼 신고 생성: {user} -> {reported_user} ({groupbuy.title})")
            
        except User.DoesNotExist:
            failed_reports.append({
                'user_id': user_id,
                'reason': '존재하지 않는 사용자입니다.'
            })
        except Exception as e:
            failed_reports.append({
                'user_id': user_id,
                'reason': str(e)
            })
    
    return Response({
        'success': len(success_reports),
        'failed': len(failed_reports),
        'success_reports': success_reports,
        'failed_reports': failed_reports
    }, status=status.HTTP_201_CREATED if success_reports else status.HTTP_400_BAD_REQUEST)