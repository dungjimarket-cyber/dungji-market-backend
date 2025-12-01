"""
전문가 프로필 및 상담 매칭 API 뷰
"""
from datetime import timedelta
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.conf import settings

from .models import User
from .models_expert import ExpertProfile, ConsultationMatch
from .models_consultation import ConsultationRequest
from .models_local_business import LocalBusinessCategory
from .models_region import Region
from .serializers_expert import (
    ExpertProfileSerializer,
    ExpertProfilePublicSerializer,
    ExpertProfileWithContactSerializer,
    ConsultationMatchSerializer,
    ConsultationMatchDetailSerializer,
    ExpertReplySerializer,
    ConsultationRequestForExpertSerializer,
    ConsultationRequestForCustomerSerializer,
)
from .utils.expert_matching import (
    send_consultation_replied_notification,
    send_consultation_connected_notification,
)
from .utils.s3_upload import upload_to_s3


class IsExpert(permissions.BasePermission):
    """전문가 권한 체크"""
    message = '전문가만 접근 가능합니다.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'expert' and
            hasattr(request.user, 'expert_profile')
        )


class ExpertProfileViewSet(viewsets.ModelViewSet):
    """
    전문가 프로필 API

    - GET /api/expert/profile/ : 내 프로필 조회
    - PUT /api/expert/profile/ : 프로필 수정
    - PATCH /api/expert/profile/receiving/ : 상담 수신 토글
    """
    serializer_class = ExpertProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExpertProfile.objects.filter(user=self.request.user).prefetch_related('regions')

    def get_object(self):
        return get_object_or_404(
            ExpertProfile.objects.prefetch_related('regions'),
            user=self.request.user
        )

    def list(self, request, *args, **kwargs):
        """내 전문가 프로필 조회"""
        try:
            profile = self.get_object()
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except:
            return Response(
                {'detail': '전문가 프로필이 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request, *args, **kwargs):
        """전문가 프로필 생성 (회원가입 시)"""
        if hasattr(request.user, 'expert_profile'):
            return Response(
                {'detail': '이미 전문가 프로필이 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # 사용자 role을 expert로 변경
            request.user.role = 'expert'
            request.user.save(update_fields=['role'])

            # 프로필 생성
            serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """프로필 수정"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['patch'], url_path='receiving')
    def toggle_receiving(self, request):
        """상담 수신 여부 토글"""
        profile = self.get_object()
        profile.is_receiving_requests = not profile.is_receiving_requests
        profile.save(update_fields=['is_receiving_requests'])
        return Response({
            'is_receiving_requests': profile.is_receiving_requests,
            'message': '상담 수신이 {}되었습니다.'.format(
                '활성화' if profile.is_receiving_requests else '비활성화'
            )
        })


class ExpertRequestsViewSet(viewsets.ViewSet):
    """
    전문가용 상담 요청 API

    - GET /api/expert/requests/ : 내게 온 상담 요청 목록
    - GET /api/expert/requests/{id}/ : 상담 요청 상세
    - POST /api/expert/requests/{id}/reply/ : 답변하기
    - POST /api/expert/requests/{id}/complete/ : 상담 완료
    """
    permission_classes = [IsExpert]

    def list(self, request):
        """내게 온 상담 요청 목록"""
        expert_profile = request.user.expert_profile

        # 상태별 필터링
        status_filter = request.query_params.get('status', None)

        # 7일 전 기준 시간
        seven_days_ago = timezone.now() - timedelta(days=7)

        matches = ConsultationMatch.objects.filter(
            expert=expert_profile
        ).select_related('consultation', 'consultation__category')

        if status_filter:
            matches = matches.filter(status=status_filter)

        # 상태별 그룹핑 (pending은 7일 이내만 표시)
        pending_matches = matches.filter(
            status='pending',
            created_at__gte=seven_days_ago
        )
        replied_matches = matches.filter(status='replied')
        connected_matches = matches.filter(status='connected')
        completed_matches = matches.filter(status='completed')

        # 7일 초과 pending 건 제외한 상담 요청 ID 목록
        valid_matches = matches.exclude(
            Q(status='pending') & Q(created_at__lt=seven_days_ago)
        )
        consultation_ids = valid_matches.values_list('consultation_id', flat=True)
        consultations = ConsultationRequest.objects.filter(id__in=consultation_ids)

        serializer = ConsultationRequestForExpertSerializer(
            consultations, many=True, context={'request': request}
        )

        return Response({
            'results': serializer.data,
            'counts': {
                'pending': pending_matches.count(),
                'replied': replied_matches.count(),
                'connected': connected_matches.count(),
                'completed': completed_matches.count(),
            }
        })

    def retrieve(self, request, pk=None):
        """상담 요청 상세"""
        expert_profile = request.user.expert_profile

        match = get_object_or_404(
            ConsultationMatch,
            consultation_id=pk,
            expert=expert_profile
        )

        serializer = ConsultationRequestForExpertSerializer(
            match.consultation, context={'request': request}
        )

        return Response({
            'consultation': serializer.data,
            'match': ConsultationMatchDetailSerializer(match).data
        })

    @action(detail=True, methods=['post'], url_path='reply')
    def reply(self, request, pk=None):
        """답변하기"""
        expert_profile = request.user.expert_profile

        match = get_object_or_404(
            ConsultationMatch,
            consultation_id=pk,
            expert=expert_profile
        )

        serializer = ExpertReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 최초 답변 여부 판단
        is_first_reply = (match.status == 'pending')

        # 내용 업데이트 (필드가 없으면 기존 값 유지)
        match.expert_message = serializer.validated_data.get('expert_message', match.expert_message or '')
        match.available_time = serializer.validated_data.get('available_time', match.available_time or '')

        # 최초 답변이면 상태/시간 갱신, 이후엔 상태 유지하고 내용만 갱신
        if is_first_reply:
            match.status = 'replied'
            match.replied_at = timezone.now()

        match.save()

        # 최초 답변일 때만 고객 알림 발송 (중복 발송 방지)
        if is_first_reply:
            try:
                send_consultation_replied_notification(match)
            except Exception:
                # 알림 실패해도 답변은 성공으로 처리
                pass

        return Response({
            'detail': '답변이 저장되었습니다.',
            'match': ConsultationMatchDetailSerializer(match).data
        })

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """상담 완료"""
        expert_profile = request.user.expert_profile

        match = get_object_or_404(
            ConsultationMatch,
            consultation_id=pk,
            expert=expert_profile
        )

        if match.status != 'connected':
            return Response(
                {'detail': '연결된 상담만 완료할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        match.status = 'completed'
        match.completed_at = timezone.now()
        match.save()

        return Response({
            'detail': '상담이 완료되었습니다.',
            'match': ConsultationMatchDetailSerializer(match).data
        })


class CustomerConsultationsViewSet(viewsets.ViewSet):
    """
    고객용 상담 내역 API

    - GET /api/my/consultations/ : 내 상담 요청 목록
    - GET /api/my/consultations/{id}/ : 상담 요청 상세
    - GET /api/my/consultations/{id}/experts/ : 답변한 전문가 목록
    - POST /api/my/consultations/{id}/experts/{expert_id}/connect/ : 연결하기
    - POST /api/my/consultations/{id}/complete/ : 상담 완료
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """내 상담 요청 목록"""
        import re
        user = request.user
        phone = user.phone_number

        # 전화번호 정규화 (하이픈 제거)
        normalized_phone = re.sub(r'[^0-9]', '', phone) if phone else None

        # user ID 또는 phone 둘 중 하나로 조회
        q_filter = Q(user=user)
        if normalized_phone:
            # 정규화된 전화번호로 비교 (DB에 저장된 값도 정규화)
            q_filter |= Q(phone=phone)
            q_filter |= Q(phone=normalized_phone)
            # 하이픈 포함 형식도 체크
            if len(normalized_phone) == 11:
                formatted_phone = f"{normalized_phone[:3]}-{normalized_phone[3:7]}-{normalized_phone[7:]}"
                q_filter |= Q(phone=formatted_phone)

        consultations = ConsultationRequest.objects.filter(
            q_filter
        ).select_related('category').prefetch_related('matches__expert').distinct().order_by('-created_at')

        serializer = ConsultationRequestForCustomerSerializer(
            consultations, many=True, context={'request': request}
        )

        return Response({'results': serializer.data})

    def retrieve(self, request, pk=None):
        """상담 요청 상세"""
        import re
        user = request.user
        phone = user.phone_number
        normalized_phone = re.sub(r'[^0-9]', '', phone) if phone else None

        # user ID 또는 phone 둘 중 하나로 조회
        q_filter = Q(user=user)
        if normalized_phone:
            q_filter |= Q(phone=phone)
            q_filter |= Q(phone=normalized_phone)
            if len(normalized_phone) == 11:
                formatted_phone = f"{normalized_phone[:3]}-{normalized_phone[3:7]}-{normalized_phone[7:]}"
                q_filter |= Q(phone=formatted_phone)

        consultation = get_object_or_404(
            ConsultationRequest.objects.filter(q_filter),
            id=pk
        )

        serializer = ConsultationRequestForCustomerSerializer(
            consultation, context={'request': request}
        )

        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='experts')
    def experts(self, request, pk=None):
        """답변한 전문가 목록"""
        import re
        user = request.user
        phone = user.phone_number
        normalized_phone = re.sub(r'[^0-9]', '', phone) if phone else None

        # user ID 또는 phone 둘 중 하나로 조회
        q_filter = Q(user=user)
        if normalized_phone:
            q_filter |= Q(phone=phone)
            q_filter |= Q(phone=normalized_phone)
            if len(normalized_phone) == 11:
                formatted_phone = f"{normalized_phone[:3]}-{normalized_phone[3:7]}-{normalized_phone[7:]}"
                q_filter |= Q(phone=formatted_phone)

        consultation = get_object_or_404(
            ConsultationRequest.objects.filter(q_filter),
            id=pk
        )

        matches = consultation.matches.filter(
            status__in=['replied', 'connected', 'completed']
        ).select_related('expert')

        serializer = ConsultationMatchDetailSerializer(matches, many=True)

        return Response({'results': serializer.data})

    @action(detail=True, methods=['post'], url_path=r'experts/(?P<expert_id>\d+)/connect')
    def connect(self, request, pk=None, expert_id=None):
        """전문가와 연결하기"""
        import re
        user = request.user
        phone = user.phone_number
        normalized_phone = re.sub(r'[^0-9]', '', phone) if phone else None

        # user ID 또는 phone 둘 중 하나로 조회
        q_filter = Q(user=user)
        if normalized_phone:
            q_filter |= Q(phone=phone)
            q_filter |= Q(phone=normalized_phone)
            if len(normalized_phone) == 11:
                formatted_phone = f"{normalized_phone[:3]}-{normalized_phone[3:7]}-{normalized_phone[7:]}"
                q_filter |= Q(phone=formatted_phone)

        consultation = get_object_or_404(
            ConsultationRequest.objects.filter(q_filter),
            id=pk
        )

        match = get_object_or_404(
            ConsultationMatch,
            consultation=consultation,
            expert_id=expert_id
        )

        if match.status != 'replied':
            return Response(
                {'detail': '답변한 전문가만 연결할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        match.status = 'connected'
        match.connected_at = timezone.now()
        match.save()

        # 전문가에게 알림 발송
        try:
            send_consultation_connected_notification(match)
        except Exception as e:
            # 알림 실패해도 연결은 성공으로 처리
            pass

        # 연결된 전문가 정보 반환 (연락처 포함)
        expert_data = ExpertProfileWithContactSerializer(match.expert).data

        return Response({
            'detail': '전문가와 연결되었습니다.',
            'expert': expert_data,
            'match': ConsultationMatchDetailSerializer(match).data
        })

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """상담 완료"""
        import re
        user = request.user
        phone = user.phone_number
        normalized_phone = re.sub(r'[^0-9]', '', phone) if phone else None

        # user ID 또는 phone 둘 중 하나로 조회
        q_filter = Q(user=user)
        if normalized_phone:
            q_filter |= Q(phone=phone)
            q_filter |= Q(phone=normalized_phone)
            if len(normalized_phone) == 11:
                formatted_phone = f"{normalized_phone[:3]}-{normalized_phone[3:7]}-{normalized_phone[7:]}"
                q_filter |= Q(phone=formatted_phone)

        consultation = get_object_or_404(
            ConsultationRequest.objects.filter(q_filter),
            id=pk
        )

        # 연결된 매칭이 있는지 확인
        connected_match = consultation.matches.filter(status='connected').first()
        if not connected_match:
            return Response(
                {'detail': '연결된 상담이 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        connected_match.status = 'completed'
        connected_match.completed_at = timezone.now()
        connected_match.save()

        return Response({
            'detail': '상담이 완료되었습니다.',
            'match': ConsultationMatchDetailSerializer(connected_match).data
        })


class ExpertRegisterView(APIView):
    """
    전문가 회원가입 API

    POST /api/auth/register-expert/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """전문가 회원가입"""
        if request.user.role == 'expert':
            return Response(
                {'detail': '이미 전문가로 등록되어 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(request.user, 'expert_profile'):
            return Response(
                {'detail': '이미 전문가 프로필이 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ExpertProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # 사용자 role을 expert로 변경
            request.user.role = 'expert'

            # 전문가 등록 시 입력한 첫 번째 지역을 기본 프로필 지역으로 설정
            region_codes = request.data.get('region_codes', [])
            update_fields = ['role']
            if region_codes and not request.user.address_region:
                first_region = Region.objects.filter(code=region_codes[0]).first()
                if first_region:
                    request.user.address_region = first_region
                    request.user.region_last_changed_at = timezone.now()
                    update_fields.extend(['address_region', 'region_last_changed_at'])

            request.user.save(update_fields=update_fields)

            # 프로필 생성
            serializer.save(user=request.user)

        return Response({
            'detail': '전문가 등록이 완료되었습니다.',
            'profile': serializer.data
        }, status=status.HTTP_201_CREATED)


class ExpertProfileImageUploadView(APIView):
    """
    전문가 프로필 이미지 업로드 API

    POST /api/expert/profile/image/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """프로필 이미지 업로드"""
        if 'image' not in request.FILES:
            return Response(
                {'detail': '이미지 파일이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        image_file = request.FILES['image']

        # 파일 크기 검증 (5MB 이하)
        if image_file.size > 5 * 1024 * 1024:
            return Response(
                {'detail': '이미지 크기는 5MB 이하여야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 파일 타입 검증
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if image_file.content_type not in allowed_types:
            return Response(
                {'detail': 'JPG, PNG, GIF, WEBP 형식만 지원됩니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # S3에 업로드
        image_url = upload_to_s3(image_file, 'expert-profiles')

        if not image_url:
            # S3 비활성화 또는 실패 시 로컬 저장 처리
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import uuid

            ext = image_file.name.split('.')[-1]
            filename = f'expert-profiles/{uuid.uuid4().hex}.{ext}'
            path = default_storage.save(filename, ContentFile(image_file.read()))
            image_url = default_storage.url(path)

        return Response({
            'image_url': image_url,
            'message': '이미지가 업로드되었습니다.'
        }, status=status.HTTP_201_CREATED)
