"""
상담 신청 관련 API ViewSet
"""
import logging
from django.db import models, transaction
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models_consultation import ConsultationType, ConsultationRequest
from .models_consultation_flow import ConsultationFlow, ConsultationFlowOption
from .models_local_business import LocalBusinessCategory
from .serializers_consultation import (
    ConsultationTypeSerializer,
    ConsultationRequestCreateSerializer,
    ConsultationRequestListSerializer,
    ConsultationRequestDetailSerializer,
    AIAssistRequestSerializer,
    ConsultationFlowListSerializer,
    AIPolishRequestSerializer,
    ConsultationFlowAdminSerializer,
    ConsultationFlowOptionAdminSerializer,
)
from .utils.ai_consultation import get_consultation_assist, polish_consultation_content, generate_consultation_flow

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
        if self.action in ['create', 'ai_assist', 'ai_polish']:
            # 상담 신청 및 AI 정리/다듬기는 누구나 가능
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

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def ai_polish(self, request):
        """
        AI 문장 다듬기
        - 탭 선택 결과를 자연스러운 문장으로 변환
        - 비회원도 사용 가능
        """
        serializer = AIPolishRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category = serializer.validated_data['category']
        selections = serializer.validated_data['selections']
        additional_content = serializer.validated_data.get('additional_content', '')

        # AI 다듬기 실행
        result = polish_consultation_content(
            category_name=category.name,
            selections=selections,
            additional_content=additional_content
        )

        logger.info(f"AI 문장 다듬기 요청: {category.name}")

        return Response(result)


# 통합 카테고리 → 실제 DB 카테고리 매핑
# 키: 프론트에서 전달되는 값 (카테고리명 또는 문자열 ID)
MERGED_CATEGORY_MAPPING = {
    # 카테고리명으로 조회 시
    '세무·회계': ['세무사', '회계사'],
    '법률 서비스': ['변호사', '법무사'],
    '청소·이사': ['청소업체', '이사업체'],
    # 문자열 ID로 조회 시 (프론트에서 category.id 전달)
    'tax_accounting': ['세무사', '회계사'],
    'legal_service': ['변호사', '법무사'],
    'cleaning_moving': ['청소업체', '이사업체'],
}


class ConsultationFlowViewSet(viewsets.ReadOnlyModelViewSet):
    """
    상담 질문 플로우 ViewSet (읽기 전용)
    - 비회원도 조회 가능
    - 업종별 질문 플로우와 선택지 제공
    """
    queryset = ConsultationFlow.objects.filter(is_active=True)
    serializer_class = ConsultationFlowListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # 카테고리 필터 (필수)
        category_param = self.request.query_params.get('category')
        if category_param:
            if category_param.isdigit():
                queryset = queryset.filter(category_id=int(category_param))
            else:
                # 통합 카테고리인지 확인
                if category_param in MERGED_CATEGORY_MAPPING:
                    # 통합 카테고리면 실제 DB 카테고리 중 첫 번째 것의 플로우 반환
                    # (같은 플로우가 양쪽에 있으므로 하나만 반환)
                    actual_category_names = MERGED_CATEGORY_MAPPING[category_param]
                    try:
                        category = LocalBusinessCategory.objects.filter(
                            name__in=actual_category_names
                        ).first()
                        if category:
                            queryset = queryset.filter(category=category)
                        else:
                            queryset = queryset.none()
                    except Exception:
                        queryset = queryset.none()
                else:
                    # google_place_type 또는 name으로 검색
                    try:
                        category = LocalBusinessCategory.objects.filter(
                            models.Q(google_place_type__iexact=category_param) |
                            models.Q(name__iexact=category_param) |
                            models.Q(name_en__iexact=category_param)
                        ).first()
                        if category:
                            queryset = queryset.filter(category=category)
                        else:
                            queryset = queryset.none()
                    except Exception:
                        queryset = queryset.none()
        else:
            # 카테고리 필터 없으면 빈 결과
            queryset = queryset.none()

        return queryset.prefetch_related('options').order_by('step_number', 'order_index')

    def list(self, request, *args, **kwargs):
        """업종별 질문 플로우 목록"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # 활성 옵션만 필터링
        data = serializer.data
        for flow in data:
            flow['options'] = [
                opt for opt in flow['options']
                if opt.get('is_active', True) is not False
            ]

        return Response(data)


class ConsultationFlowAdminViewSet(viewsets.ModelViewSet):
    """
    상담 질문 플로우 관리자용 ViewSet (CRUD)
    - 관리자만 접근 가능
    - 플로우 생성, 수정, 삭제
    - AI 플로우 추천
    """
    queryset = ConsultationFlow.objects.all()
    serializer_class = ConsultationFlowAdminSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        # 카테고리 필터
        category_param = self.request.query_params.get('category')
        if category_param:
            if category_param.isdigit():
                queryset = queryset.filter(category_id=int(category_param))
            else:
                queryset = queryset.filter(
                    models.Q(category__name__iexact=category_param) |
                    models.Q(category__google_place_type__iexact=category_param)
                )

        # 활성 상태 필터
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.select_related('category').prefetch_related('options').order_by('category', 'step_number', 'order_index')

    def list(self, request, *args, **kwargs):
        """카테고리별 플로우 목록 (관리자용)"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """새 플로우 생성"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        logger.info(f"플로우 생성: {instance.category.name} - Step {instance.step_number}")

        return Response(
            self.get_serializer(instance).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """플로우 수정"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(f"플로우 수정: {instance.category.name} - Step {instance.step_number}")

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """플로우 삭제"""
        instance = self.get_object()
        category_name = instance.category.name
        step_number = instance.step_number

        # 연관된 옵션들도 함께 삭제 (CASCADE)
        instance.delete()

        logger.info(f"플로우 삭제: {category_name} - Step {step_number}")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='bulk-save')
    def bulk_save(self, request):
        """
        카테고리의 전체 플로우 일괄 저장
        - 기존 플로우 삭제 후 새로 생성
        """
        category_id = request.data.get('category_id')
        flows_data = request.data.get('flows', [])

        if not category_id:
            return Response(
                {'error': '카테고리 ID가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            category = LocalBusinessCategory.objects.get(id=category_id)
        except LocalBusinessCategory.DoesNotExist:
            return Response(
                {'error': '존재하지 않는 카테고리입니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            with transaction.atomic():
                # 기존 플로우 삭제
                ConsultationFlow.objects.filter(category=category).delete()

                # 새 플로우 생성
                created_flows = []
                for idx, flow_data in enumerate(flows_data):
                    options_data = flow_data.pop('options', [])

                    flow = ConsultationFlow.objects.create(
                        category=category,
                        step_number=flow_data.get('step_number', idx + 1),
                        question=flow_data.get('question', ''),
                        is_required=flow_data.get('is_required', True),
                        depends_on_step=flow_data.get('depends_on_step'),
                        depends_on_options=flow_data.get('depends_on_options', []),
                        order_index=flow_data.get('order_index', idx),
                        is_active=flow_data.get('is_active', True),
                    )

                    # 옵션 생성
                    for opt_idx, opt_data in enumerate(options_data):
                        ConsultationFlowOption.objects.create(
                            flow=flow,
                            key=opt_data.get('key', f'option_{opt_idx}'),
                            label=opt_data.get('label', ''),
                            icon=opt_data.get('icon', ''),
                            logo=opt_data.get('logo', ''),
                            description=opt_data.get('description', ''),
                            is_custom_input=opt_data.get('is_custom_input', False),
                            order_index=opt_data.get('order_index', opt_idx),
                            is_active=opt_data.get('is_active', True),
                        )

                    created_flows.append(flow)

                logger.info(f"플로우 일괄 저장: {category.name} - {len(created_flows)}개")

                return Response({
                    'success': True,
                    'message': f'{len(created_flows)}개의 플로우가 저장되었습니다.',
                    'flows': ConsultationFlowAdminSerializer(created_flows, many=True).data
                })

        except Exception as e:
            logger.error(f"플로우 일괄 저장 오류: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='ai-generate')
    def ai_generate(self, request):
        """
        AI로 플로우 추천받기
        - 카테고리와 키워드를 기반으로 질문 플로우 생성
        """
        category_id = request.data.get('category_id')
        keywords = request.data.get('keywords', '')
        reference_text = request.data.get('reference_text', '')

        if not category_id:
            return Response(
                {'error': '카테고리 ID가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            category = LocalBusinessCategory.objects.get(id=category_id)
        except LocalBusinessCategory.DoesNotExist:
            return Response(
                {'error': '존재하지 않는 카테고리입니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # AI 플로우 생성
        result = generate_consultation_flow(
            category_name=category.name,
            keywords=keywords,
            reference_text=reference_text
        )

        if not result.get('success'):
            return Response(
                {'error': result.get('error', 'AI 생성에 실패했습니다.')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        logger.info(f"AI 플로우 생성: {category.name} - {len(result.get('flows', []))}개")

        return Response(result)

    @action(detail=False, methods=['get'], url_path='categories')
    def get_categories(self, request):
        """플로우가 있는 카테고리 목록"""
        categories_with_flows = LocalBusinessCategory.objects.filter(
            consultation_flows__isnull=False
        ).distinct().values('id', 'name', 'icon')

        all_categories = LocalBusinessCategory.objects.filter(
            is_active=True
        ).values('id', 'name', 'icon')

        return Response({
            'all': list(all_categories),
            'with_flows': list(categories_with_flows)
        })


class ConsultationFlowOptionAdminViewSet(viewsets.ModelViewSet):
    """
    상담 선택지 관리자용 ViewSet
    """
    queryset = ConsultationFlowOption.objects.all()
    serializer_class = ConsultationFlowOptionAdminSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        # 플로우 필터
        flow_id = self.request.query_params.get('flow')
        if flow_id:
            queryset = queryset.filter(flow_id=flow_id)

        return queryset.select_related('flow').order_by('flow', 'order_index')
