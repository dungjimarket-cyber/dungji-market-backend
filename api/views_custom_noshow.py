"""
커스텀 공구 노쇼 신고 관련 API 뷰
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from api.models_custom import CustomNoShowReport, CustomGroupBuy, CustomParticipant, CustomPenalty
from api.serializers_custom import CustomNoShowReportSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomNoShowReportViewSet(ModelViewSet):
    """
    커스텀 공구 노쇼 신고 관리 ViewSet
    """
    serializer_class = CustomNoShowReportSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # 파일 업로드 지원

    def get_queryset(self):
        """
        현재 사용자가 신고한 내역 또는 받은 신고 내역 조회
        """
        user = self.request.user
        queryset = CustomNoShowReport.objects.select_related(
            'reporter', 'reported_user', 'custom_groupbuy', 'participant'
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
            queryset = queryset.filter(custom_groupbuy_id=groupbuy_id)

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
        logger.info(f"커스텀 공구 노쇼 신고 생성: {instance.reporter} -> {instance.reported_user} ({instance.custom_groupbuy.title})")
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
        logger.info(f"커스텀 공구 노쇼 신고 수정: {instance.id} (수정 {instance.edit_count}회)")
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
                    'custom_groupbuy_id': item.get('custom_groupbuy'),
                    'custom_groupbuy_title': item.get('custom_groupbuy_title'),
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
        logger.info(f"커스텀 공구 노쇼 신고 생성: {instance.reporter} -> {instance.reported_user} ({instance.custom_groupbuy.title})")

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

        # 취소 가능 여부 확인 (pending 상태에서만 취소 가능)
        if report.status != 'pending':
            return Response({
                'error': '처리중 상태에서만 취소 가능합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        custom_groupbuy = report.custom_groupbuy
        message = '노쇼 신고가 취소되었습니다.'

        logger.info(f"커스텀 공구 노쇼 신고 취소 (사용자: {request.user.id}, 공구: {custom_groupbuy.id})")

        # 노쇼 신고 삭제
        report_id = report.id
        report.delete()

        logger.info(f"커스텀 공구 노쇼 신고 {report_id} 취소됨")

        return Response({
            'message': message,
            'groupbuy_status': custom_groupbuy.status
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

        custom_groupbuy = report.custom_groupbuy
        message = '노쇼 신고가 처리완료되었습니다.'

        # 노쇼 신고된 구매자 수 확인을 위한 통계만 수집
        confirmed_participants = CustomParticipant.objects.filter(
            custom_groupbuy=custom_groupbuy,
            status='confirmed'
        )
        confirmed_count = confirmed_participants.count()

        noshow_reports = CustomNoShowReport.objects.filter(
            custom_groupbuy=custom_groupbuy,
            status='completed'
        )

        noshow_buyer_ids = set()
        for noshow_report in noshow_reports:
            if noshow_report.noshow_buyers:
                noshow_buyer_ids.update(noshow_report.noshow_buyers)
            if noshow_report.reported_user:
                noshow_buyer_ids.add(noshow_report.reported_user.id)

        noshow_count = len(noshow_buyer_ids)

        logger.info(f"커스텀 공구 노쇼 신고 {report.id} 처리완료 (공구: {custom_groupbuy.id}, 노쇼: {noshow_count}/{confirmed_count})")

        return Response({
            'status': 'success',
            'message': message,
            'noshow_count': noshow_count,
            'confirmed_count': confirmed_count,
            'groupbuy_status': custom_groupbuy.status
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

        logger.info(f"커스텀 공구 노쇼 신고 {report.id} 보류 처리")

        return Response({
            'message': '노쇼 신고가 보류 처리되었습니다.',
            'status': report.status
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_custom_noshow_report_eligibility(request):
    """
    커스텀 공구 노쇼 신고 가능 여부 확인
    종료된 공구에 대해서만 신고 가능

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
        custom_groupbuy = CustomGroupBuy.objects.get(id=groupbuy_id)
        reported_user = User.objects.get(id=user_id)
    except (CustomGroupBuy.DoesNotExist, User.DoesNotExist):
        return Response({
            'error': '잘못된 공구 또는 사용자 ID입니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    # 종료된 공구에만 신고 가능
    if custom_groupbuy.status != 'completed':
        return Response({
            'eligible': False,
            'reason': '종료된 공구에만 노쇼 신고가 가능합니다.'
        })

    # 이미 신고했는지 확인
    existing_report = CustomNoShowReport.objects.filter(
        reporter=user,
        reported_user=reported_user,
        custom_groupbuy=custom_groupbuy
    ).exists()

    if existing_report:
        return Response({
            'eligible': False,
            'reason': '이미 해당 사용자를 신고했습니다.'
        })

    # 신고 유형별 자격 확인
    if report_type == 'buyer_noshow':
        # 판매자가 구매자를 신고
        if custom_groupbuy.seller != user:
            return Response({
                'eligible': False,
                'reason': '구매자 노쇼는 판매자(공구 생성자)만 신고할 수 있습니다.'
            })

        # 신고 대상이 참여자인지 확인
        is_participant = CustomParticipant.objects.filter(
            user=reported_user,
            custom_groupbuy=custom_groupbuy,
            status='confirmed'
        ).exists()

        if not is_participant:
            return Response({
                'eligible': False,
                'reason': '신고 대상이 해당 공구 참여자가 아닙니다.'
            })

    elif report_type == 'seller_noshow':
        # 구매자가 판매자를 신고
        # 신고자가 참여자인지 확인
        is_participant = CustomParticipant.objects.filter(
            user=user,
            custom_groupbuy=custom_groupbuy,
            status='confirmed'
        ).exists()

        if not is_participant:
            return Response({
                'eligible': False,
                'reason': '해당 공구에 참여하지 않았습니다.'
            })

        # 신고 대상이 판매자인지 확인
        if custom_groupbuy.seller != reported_user:
            return Response({
                'eligible': False,
                'reason': '신고 대상이 판매자가 아닙니다.'
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
def batch_report_custom_buyer_noshow(request):
    """
    판매자가 여러 구매자를 일괄 노쇼 신고 (커스텀 공구)

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

    groupbuy_id = request.data.get('groupbuy_id')
    reported_users = request.data.get('reported_users', [])

    if not groupbuy_id or not reported_users:
        return Response({
            'error': '필수 데이터가 누락되었습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        custom_groupbuy = CustomGroupBuy.objects.get(id=groupbuy_id)
    except CustomGroupBuy.DoesNotExist:
        return Response({
            'error': '존재하지 않는 공구입니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 종료된 공구만 신고 가능
    if custom_groupbuy.status != 'completed':
        return Response({
            'error': '종료된 공구에만 노쇼 신고가 가능합니다.'
        }, status=status.HTTP_403_FORBIDDEN)

    # 판매자(공구 생성자) 권한 확인
    if custom_groupbuy.seller != user:
        return Response({
            'error': '구매자 노쇼는 판매자만 신고할 수 있습니다.'
        }, status=status.HTTP_403_FORBIDDEN)

    # 참여자 목록 가져오기
    valid_participants = CustomParticipant.objects.filter(
        custom_groupbuy=custom_groupbuy,
        status='confirmed'
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
            existing_report = CustomNoShowReport.objects.filter(
                reporter=user,
                reported_user=reported_user,
                custom_groupbuy=custom_groupbuy
            ).exists()

            if existing_report:
                failed_reports.append({
                    'user_id': user_id,
                    'reason': '이미 신고된 사용자입니다.'
                })
                continue

            # 참여자 정보 가져오기
            participant = CustomParticipant.objects.get(
                user=reported_user,
                custom_groupbuy=custom_groupbuy,
                status='confirmed'
            )

            # 신고 생성
            report = CustomNoShowReport.objects.create(
                reporter=user,
                reported_user=reported_user,
                custom_groupbuy=custom_groupbuy,
                participant=participant,
                report_type='buyer_noshow',
                content=content
            )

            success_reports.append({
                'user_id': user_id,
                'report_id': report.id,
                'message': '신고가 접수되었습니다.'
            })

            logger.info(f"커스텀 공구 배치 노쇼 신고 생성: {user} -> {reported_user} ({custom_groupbuy.title})")

        except User.DoesNotExist:
            failed_reports.append({
                'user_id': user_id,
                'reason': '존재하지 않는 사용자입니다.'
            })
        except CustomParticipant.DoesNotExist:
            failed_reports.append({
                'user_id': user_id,
                'reason': '참여자 정보를 찾을 수 없습니다.'
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


class CustomPenaltyViewSet(ModelViewSet):
    """
    커스텀 공구 패널티 관리 ViewSet
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']  # 조회만 허용

    def get_queryset(self):
        """현재 사용자의 패널티 조회"""
        return CustomPenalty.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def check_active(self, request):
        """
        활성 패널티 확인

        Returns:
            {
                "has_active_penalty": true/false,
                "penalty": {
                    "type": "판매거부",
                    "reason": "사유",
                    "count": 1,
                    "end_date": "2025-10-31T10:43:01",
                    "remaining_text": "455시간 8분 남음",
                    "is_active": true
                }
            }
        """
        user = request.user

        # 활성 패널티 조회
        active_penalty = CustomPenalty.objects.filter(
            user=user,
            is_active=True,
            end_date__gt=timezone.now()
        ).first()

        if not active_penalty:
            return Response({
                'has_active_penalty': False,
                'penalty': None
            })

        # 남은 시간 계산
        remaining = active_penalty.end_date - timezone.now()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)

        # 이전 패널티 횟수 계산 (누적 횟수)
        penalty_count = CustomPenalty.objects.filter(
            user=user
        ).count()

        return Response({
            'has_active_penalty': True,
            'penalty': {
                'type': active_penalty.penalty_type,
                'reason': active_penalty.reason,
                'count': penalty_count,
                'end_date': active_penalty.end_date.isoformat(),
                'remaining_text': f"{hours}시간 {minutes}분 남음",
                'remaining_hours': hours,
                'remaining_minutes': minutes,
                'is_active': True
            }
        })
