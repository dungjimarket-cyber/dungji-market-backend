"""
상담 신청 관련 API ViewSet
"""
import logging
from django.db import models
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models_consultation import ConsultationType, ConsultationRequest
from .models_local_business import LocalBusinessCategory
from .serializers_consultation import (
    ConsultationTypeSerializer,
    ConsultationRequestCreateSerializer,
    ConsultationRequestListSerializer,
    ConsultationRequestDetailSerializer,
    AIAssistRequestSerializer,
)
from .utils.ai_consultation import get_consultation_assist

logger = logging.getLogger(__name__)


class ConsultationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    상담 유형 ViewSet (읽기 전용)
    - 비회원도 조회 가능
    """
    queryset = ConsultationType.objects.filter(is_active=True)
    serializer_class = ConsultationTypeSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # 카테고리 필터 (ID 또는 이름 지원)
        category_param = self.request.query_params.get('category')
        if category_param:
            # 숫자면 ID로, 아니면 이름으로 검색
            if category_param.isdigit():
                queryset = queryset.filter(category_id=int(category_param))
            else:
                # google_place_type 또는 name으로 검색
                from .models_local_business import LocalBusinessCategory
                try:
                    category = LocalBusinessCategory.objects.filter(
                        models.Q(google_place_type__iexact=category_param) |
                        models.Q(name__iexact=category_param) |
                        models.Q(name_en__iexact=category_param)
                    ).first()
                    if category:
                        queryset = queryset.filter(category=category)
                    else:
                        # 카테고리를 찾지 못하면 빈 결과
                        queryset = queryset.none()
                except Exception:
                    queryset = queryset.none()

        return queryset.select_related('category')


class ConsultationRequestViewSet(viewsets.ModelViewSet):
    """
    상담 신청 ViewSet
    - 비회원도 신청 가능 (create)
    - 목록/상세는 관리자만 조회 가능
    """
    queryset = ConsultationRequest.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return ConsultationRequestCreateSerializer
        elif self.action == 'list':
            return ConsultationRequestListSerializer
        return ConsultationRequestDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'ai_assist']:
            # 상담 신청 및 AI 정리는 누구나 가능
            return [permissions.AllowAny()]
        # 나머지는 관리자만
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        queryset = super().get_queryset()

        # 상태 필터
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 카테고리 필터
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # 지역 필터
        region = self.request.query_params.get('region')
        if region:
            queryset = queryset.filter(region__icontains=region)

        # 검색
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(content__icontains=search)
            )

        return queryset.select_related('category', 'consultation_type')

    def create(self, request, *args, **kwargs):
        """상담 신청 생성 (비회원 가능)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        logger.info(
            f"상담 신청 생성: {instance.name} - {instance.category.name} - {instance.region}"
        )

        return Response({
            'success': True,
            'message': '상담 신청이 완료되었습니다. 빠른 시일 내에 연락드리겠습니다.',
            'id': instance.id
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def ai_assist(self, request):
        """
        AI 내용 정리 및 상담 유형 추천
        - 비회원도 사용 가능
        """
        serializer = AIAssistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category = serializer.validated_data['category']
        content = serializer.validated_data['content']

        # 해당 카테고리의 상담 유형 조회
        consultation_types = ConsultationType.objects.filter(
            category=category,
            is_active=True
        ).values('id', 'name')

        available_types = list(consultation_types)

        if not available_types:
            return Response({
                'summary': content[:200],
                'recommended_types': []
            })

        # AI 정리 실행
        result = get_consultation_assist(
            category_name=category.name,
            content=content,
            available_types=available_types
        )

        logger.info(f"AI 상담 정리 요청: {category.name}")

        return Response(result)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def update_status(self, request, pk=None):
        """
        상담 상태 변경 (관리자 전용)
        """
        instance = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(ConsultationRequest.STATUS_CHOICES):
            return Response({
                'success': False,
                'message': '유효하지 않은 상태입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        old_status = instance.status
        instance.status = new_status

        # 상태별 타임스탬프 업데이트
        if new_status == 'contacted' and not instance.contacted_at:
            instance.contacted_at = timezone.now()
        elif new_status == 'completed' and not instance.completed_at:
            instance.completed_at = timezone.now()

        # 관리자 메모 업데이트
        admin_note = request.data.get('admin_note')
        if admin_note:
            instance.admin_note = admin_note

        instance.save()

        logger.info(
            f"상담 상태 변경: {instance.id} - {old_status} → {new_status}"
        )

        return Response({
            'success': True,
            'message': f'상태가 "{instance.get_status_display()}"(으)로 변경되었습니다.'
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def statistics(self, request):
        """
        상담 신청 통계 (관리자 전용)
        """
        from django.db.models import Count
        from django.db.models.functions import TruncDate

        total = ConsultationRequest.objects.count()

        # 상태별 통계
        by_status = dict(
            ConsultationRequest.objects.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )

        # 카테고리별 통계
        by_category = list(
            ConsultationRequest.objects.values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # 최근 7일 일별 통계
        from datetime import timedelta
        seven_days_ago = timezone.now() - timedelta(days=7)
        daily = list(
            ConsultationRequest.objects.filter(created_at__gte=seven_days_ago)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        return Response({
            'total': total,
            'by_status': by_status,
            'by_category': by_category,
            'daily': daily
        })
