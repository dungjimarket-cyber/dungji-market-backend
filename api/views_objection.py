"""
노쇼 이의제기 관련 API 뷰
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import NoShowObjection, NoShowReport
from .serializers import NoShowObjectionSerializer
from django.db.models import Q
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class NoShowObjectionViewSet(ModelViewSet):
    """
    노쇼 이의제기 관리 ViewSet
    """
    serializer_class = NoShowObjectionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # 파일 업로드 지원
    
    def get_queryset(self):
        """
        현재 사용자가 제출한 이의제기 또는 관리자의 경우 모든 이의제기 조회
        """
        user = self.request.user
        
        if user.is_staff or user.role == 'admin':
            # 관리자는 모든 이의제기 조회 가능
            queryset = NoShowObjection.objects.all()
        else:
            # 일반 사용자는 본인이 제출한 이의제기만 조회
            queryset = NoShowObjection.objects.filter(objector=user)
        
        # 상태별 필터링
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 노쇼 신고별 필터링
        report_id = self.request.query_params.get('report_id')
        if report_id:
            queryset = queryset.filter(noshow_report_id=report_id)
        
        return queryset.select_related(
            'noshow_report', 'objector', 'processed_by',
            'noshow_report__groupbuy', 'noshow_report__reporter', 
            'noshow_report__reported_user'
        ).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        이의제기 생성 (파일 업로드 처리 포함)
        """
        # 데이터 복사
        data = request.data.copy()
        
        # 파일 처리
        files_to_save = {}
        
        # 파일들 처리 (최대 3개)
        for i in range(1, 4):
            file_key = f'evidence_image_{i}'
            if file_key in request.FILES:
                files_to_save[file_key] = request.FILES[file_key]
        
        # 시리얼라이저로 유효성 검사
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        # 파일과 함께 저장
        instance = serializer.save(objector=request.user, **files_to_save)
        
        # 로깅
        logger.info(f"이의제기 생성: {instance.objector} -> 신고 #{instance.noshow_report.id}")
        logger.info(f"파일 업로드: evidence_1={bool(instance.evidence_image_1)}, "
                   f"evidence_2={bool(instance.evidence_image_2)}, "
                   f"evidence_3={bool(instance.evidence_image_3)}")
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def process(self, request, pk=None):
        """관리자가 이의제기 처리"""
        objection = self.get_object()
        
        if objection.status in ['resolved', 'rejected']:
            return Response({
                'error': '이미 처리된 이의제기입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        action_type = request.data.get('action')  # 'resolve' or 'reject'
        admin_comment = request.data.get('admin_comment', '')
        
        if action_type not in ['resolve', 'reject']:
            return Response({
                'error': 'action은 resolve 또는 reject여야 합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 이의제기 상태 업데이트
        objection.status = 'resolved' if action_type == 'resolve' else 'rejected'
        objection.admin_comment = admin_comment
        objection.processed_at = timezone.now()
        objection.processed_by = request.user
        objection.save()
        
        # 이의제기가 인정된 경우 노쇼 신고 처리
        if action_type == 'resolve':
            noshow_report = objection.noshow_report
            
            # 노쇼 신고를 보류 상태로 변경
            noshow_report.status = 'on_hold'
            noshow_report.admin_comment = f"이의제기 인정: {admin_comment}"
            noshow_report.save()
            
            logger.info(f"이의제기 #{objection.id} 인정 - 노쇼 신고 #{noshow_report.id} 보류 처리")
            
            message = '이의제기가 인정되어 노쇼 신고가 보류 처리되었습니다.'
        else:
            logger.info(f"이의제기 #{objection.id} 거부")
            message = '이의제기가 거부되었습니다.'
        
        return Response({
            'status': 'success',
            'message': message,
            'objection_status': objection.status,
            'admin_comment': objection.admin_comment
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def with_report(self, request, pk=None):
        """관리자가 이의제기와 원본 노쇼 신고를 함께 조회"""
        objection = self.get_object()
        noshow_report = objection.noshow_report
        
        # 이의제기 데이터
        objection_data = NoShowObjectionSerializer(objection).data
        
        # 노쇼 신고 데이터
        from .serializers import NoShowReportSerializer
        report_data = NoShowReportSerializer(noshow_report).data
        
        return Response({
            'objection': objection_data,
            'noshow_report': report_data
        })
    
    def update(self, request, *args, **kwargs):
        """
        이의제기 수정 (1회 제한)
        """
        objection = self.get_object()
        
        # 본인 확인
        if objection.objector != request.user:
            return Response({
                'error': '본인의 이의제기만 수정할 수 있습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 취소된 이의제기 수정 불가
        if objection.is_cancelled:
            return Response({
                'error': '취소된 이의제기는 수정할 수 없습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 이미 처리된 이의제기 수정 불가
        if objection.status in ['resolved', 'rejected']:
            return Response({
                'error': '이미 처리된 이의제기는 수정할 수 없습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 수정 횟수 체크
        if objection.edit_count >= 1:
            return Response({
                'error': '이의제기는 1회만 수정 가능합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 데이터 업데이트
        data = request.data.copy()
        files_to_save = {}
        
        # 파일 처리
        for i in range(1, 4):
            file_key = f'evidence_image_{i}'
            if file_key in request.FILES:
                files_to_save[file_key] = request.FILES[file_key]
        
        # 시리얼라이저로 업데이트
        serializer = self.get_serializer(objection, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # 파일과 함께 저장
        instance = serializer.save(**files_to_save)
        
        # 수정 횟수 증가 (직접 업데이트)
        instance.edit_count = objection.edit_count + 1
        instance.save(update_fields=['edit_count'])
        
        logger.info(f"이의제기 수정: #{objection.id} by {request.user.username}")
        
        return Response({
            'status': 'success',
            'message': '이의제기가 수정되었습니다.',
            'data': serializer.data,
            'edit_count': instance.edit_count
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """
        이의제기 취소
        """
        objection = self.get_object()
        
        # 본인 확인
        if objection.objector != request.user:
            return Response({
                'error': '본인의 이의제기만 취소할 수 있습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 이미 취소된 경우
        if objection.is_cancelled:
            return Response({
                'error': '이미 취소된 이의제기입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 이미 처리된 이의제기 취소 불가
        if objection.status in ['resolved', 'rejected']:
            return Response({
                'error': '이미 처리된 이의제기는 취소할 수 없습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 취소 사유
        cancellation_reason = request.data.get('cancellation_reason', '')
        
        # 취소 처리
        objection.is_cancelled = True
        objection.cancelled_at = timezone.now()
        objection.cancellation_reason = cancellation_reason
        objection.save()
        
        logger.info(f"이의제기 취소: #{objection.id} by {request.user.username}")
        
        return Response({
            'status': 'success',
            'message': '이의제기가 취소되었습니다.',
            'cancelled_at': objection.cancelled_at,
            'cancellation_reason': objection.cancellation_reason
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_objection_eligibility(request, report_id):
    """
    특정 노쇼 신고에 대한 이의제기 가능 여부 확인
    """
    try:
        report = NoShowReport.objects.get(id=report_id)
        
        # 피신고자인지 확인
        if report.reported_user != request.user:
            return Response({
                'eligible': False,
                'reason': '본인이 받은 신고에 대해서만 이의제기할 수 있습니다.'
            })
        
        # 이미 이의제기가 있는지 확인 (취소된 것 제외)
        existing_objection = NoShowObjection.objects.filter(
            noshow_report=report,
            objector=request.user,
            is_cancelled=False
        ).first()
        
        if existing_objection:
            return Response({
                'eligible': False,
                'reason': '이미 이의제기를 하셨습니다.',
                'existing_objection': NoShowObjectionSerializer(existing_objection).data
            })
        
        return Response({
            'eligible': True,
            'message': '이의제기가 가능합니다.'
        })
        
    except NoShowReport.DoesNotExist:
        return Response({
            'error': '노쇼 신고를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)