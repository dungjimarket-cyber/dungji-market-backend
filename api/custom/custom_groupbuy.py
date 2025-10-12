from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q, F
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from api.models_custom import CustomGroupBuy, CustomParticipant, CustomFavorite, CustomGroupBuyRegion
from api.serializers_custom import (
    CustomGroupBuyListSerializer,
    CustomGroupBuyDetailSerializer,
    CustomGroupBuyCreateSerializer,
    CustomParticipantSerializer,
    CustomFavoriteSerializer
)
from api.services.image_service import ImageService
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_custom_categories(request):
    """커스텀 특가 카테고리 목록 조회"""
    categories = [
        {'value': value, 'label': label}
        for value, label in CustomGroupBuy.CATEGORY_CHOICES
    ]
    return Response({'categories': categories})


class CustomGroupBuyViewSet(viewsets.ModelViewSet):
    queryset = CustomGroupBuy.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return CustomGroupBuyListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CustomGroupBuyCreateSerializer
        return CustomGroupBuyDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """create 메서드 오버라이드 - 에러 디버깅 + DetailSerializer 반환"""
        from rest_framework import status
        from rest_framework.response import Response

        logger.info(f"[CREATE] Starting creation by user {request.user}")
        logger.info(f"[CREATE] Request data keys: {request.data.keys()}")
        logger.info(f"[CREATE] Request FILES keys: {request.FILES.keys()}")
        logger.info(f"[CREATE] Request content_type: {request.content_type}")

        # 이미지 파일 상세 로깅
        images = request.FILES.getlist('images')
        logger.info(f"[CREATE] Images from FILES.getlist: {len(images)} files")
        for idx, img in enumerate(images):
            logger.info(f"[CREATE] Image {idx}: name={img.name}, size={img.size}, content_type={img.content_type}")

        # 활성 패널티 체크
        from api.models_custom import CustomPenalty
        from django.utils import timezone
        active_penalty = CustomPenalty.objects.filter(
            user=request.user,
            is_active=True,
            end_date__gt=timezone.now()
        ).first()

        if active_penalty:
            remaining = active_penalty.end_date - timezone.now()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            return Response(
                {
                    'error': f'패널티 기간 중에는 공구를 등록할 수 없습니다.',
                    'penalty_info': {
                        'type': active_penalty.penalty_type,
                        'reason': active_penalty.reason,
                        'end_date': active_penalty.end_date.isoformat(),
                        'remaining_text': f"{hours}시간 {minutes}분 남음"
                    }
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # 활성 공구 개수 체크 (한 번에 하나만 등록 가능)
        active_count = CustomGroupBuy.objects.filter(
            seller=request.user,
            status__in=['recruiting', 'pending_seller']
        ).count()

        if active_count >= 1:
            return Response(
                {'error': '이미 진행 중인 공구가 있습니다. 기존 공구가 마감된 후 등록할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # DRF가 request.data에서 자동으로 파일 처리 (중고거래와 동일)
            serializer = self.get_serializer(data=request.data)
            logger.info(f"[CREATE] Serializer initial_data keys: {serializer.initial_data.keys() if hasattr(serializer, 'initial_data') else 'N/A'}")

            serializer.is_valid(raise_exception=True)
            logger.info(f"[CREATE] Serializer validated_data keys: {serializer.validated_data.keys()}")
            logger.info(f"[CREATE] Images in validated_data: {len(serializer.validated_data.get('images', []))}")

            logger.info(f"[CREATE] Calling perform_create")
            self.perform_create(serializer)

            # 생성된 instance를 DetailSerializer로 다시 직렬화 (중고거래 방식)
            instance = serializer.instance
            detail_serializer = CustomGroupBuyDetailSerializer(
                instance,
                context={'request': request}
            )

            headers = self.get_success_headers(detail_serializer.data)
            logger.info(f"[CREATE] Success - returning data with ID: {detail_serializer.data.get('id')}")

            return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except Exception as e:
            logger.error(f"[CREATE] Failed with error: {str(e)}", exc_info=True)
            return Response(
                {"error": f"생성 실패: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        """공구 생성"""
        logger.info(f"[PERFORM_CREATE] Called by user: {self.request.user}")

        # 공구 생성
        instance = serializer.save(seller=self.request.user)
        logger.info(f"[PERFORM_CREATE] Instance created - ID: {instance.id}, Title: {instance.title}")

    def perform_update(self, serializer):
        """공구 수정 - 이미지는 serializer에서 처리"""
        logger.info(f"perform_update called by user: {self.request.user}")
        instance = serializer.save()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.seller != request.user:
            return Response(
                {'error': '판매자만 수정할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 완료/취소/만료된 공구는 수정 불가
        if instance.status in ['completed', 'cancelled', 'expired']:
            return Response(
                {'error': '완료/취소/만료된 공구는 수정할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 항상 수정 불가능한 필드들
        restricted_fields = {
            'type': '온/오프라인 유형',
            'target_participants': '목표 인원',
        }

        for field, field_name in restricted_fields.items():
            if field in request.data:
                current_value = getattr(instance, field)
                new_value = request.data.get(field)

                # 값이 실제로 변경되는지 체크
                if str(current_value) != str(new_value):
                    return Response(
                        {'error': f'{field_name}은(는) 수정할 수 없습니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # 참여자가 있을 때는 제한적 수정만 가능
        if instance.current_participants > 0:
            allowed_fields = [
                'title', 'description', 'usage_guide',
                'discount_codes', 'discount_url', 'discount_valid_days'  # 할인 정보 수정 허용
            ]
            for field in request.data.keys():
                if field not in allowed_fields and field not in ['images', 'existing_image_ids', 'new_images']:
                    return Response(
                        {'error': '참여자가 있는 공구는 제목, 상세설명, 이용안내, 할인 정보만 수정 가능합니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        logger.info(f"=== CustomGroupBuy Update Request ===")
        logger.info(f"User: {request.user}")
        logger.info(f"Request data keys: {request.data.keys()}")
        logger.info(f"Request FILES keys: {request.FILES.keys()}")

        # DRF가 자동으로 FormData 파싱 (전자제품과 동일)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.seller != request.user:
            return Response(
                {'error': '판매자만 삭제할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if instance.current_participants > 0:
            return Response(
                {'error': '참여자가 있는 공구는 삭제할 수 없습니다. 취소 처리를 이용해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    # retrieve 메서드는 기본 ViewSet의 것을 사용 (커스터마이징 불필요)

    def get_queryset(self):
        queryset = CustomGroupBuy.objects.select_related('seller').prefetch_related(
            'images',
            'participants'
        )

        type_filter = self.request.query_params.get('type')
        if type_filter:
            queryset = queryset.filter(type=type_filter)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__contains=[category])

        # location 기반 검색 (주소 텍스트 검색)
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        seller_id = self.request.query_params.get('seller')
        if seller_id:
            if seller_id == 'me':
                if not self.request.user.is_authenticated:
                    return CustomGroupBuy.objects.none()
                queryset = queryset.filter(seller=self.request.user)
            else:
                queryset = queryset.filter(seller_id=seller_id)

        return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        # 목록 조회 시 만료된 공구들 일괄 체크
        from django.utils import timezone
        expired_groupbuys = CustomGroupBuy.objects.filter(
            status='recruiting',
            expired_at__lte=timezone.now()
        )
        for groupbuy in expired_groupbuys[:10]:  # 최대 10개만 체크 (성능 고려)
            try:
                groupbuy.check_expiration()
            except Exception:
                pass  # 에러 발생해도 목록 조회는 계속

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # 조회 시점에 만료 체크
        if instance.status == 'recruiting':
            instance.check_expiration()

        instance.view_count = F('view_count') + 1
        instance.save(update_fields=['view_count'])
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def participate(self, request, pk=None):
        groupbuy = self.get_object()
        user = request.user

        # 활성 패널티 체크
        from api.models_custom import CustomPenalty
        from django.utils import timezone
        active_penalty = CustomPenalty.objects.filter(
            user=user,
            is_active=True,
            end_date__gt=timezone.now()
        ).first()

        if active_penalty:
            remaining = active_penalty.end_date - timezone.now()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            return Response(
                {
                    'error': f'패널티 기간 중에는 공구에 참여할 수 없습니다.',
                    'penalty_info': {
                        'type': active_penalty.penalty_type,
                        'reason': active_penalty.reason,
                        'end_date': active_penalty.end_date.isoformat(),
                        'remaining_text': f"{hours}시간 {minutes}분 남음"
                    }
                },
                status=status.HTTP_403_FORBIDDEN
            )

        if groupbuy.seller == user:
            return Response(
                {'error': '판매자는 자신의 공구에 참여할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if groupbuy.status != 'recruiting':
            return Response(
                {'error': '모집 중인 공구만 참여 가능합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if CustomParticipant.objects.filter(custom_groupbuy=groupbuy, user=user).exists():
            return Response(
                {'error': '이미 참여한 공구입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.db import transaction

        with transaction.atomic():
            groupbuy = CustomGroupBuy.objects.select_for_update().get(pk=groupbuy.pk)

            participant = CustomParticipant.objects.create(
                custom_groupbuy=groupbuy,
                user=user
            )

            groupbuy.current_participants = F('current_participants') + 1
            groupbuy.save(update_fields=['current_participants'])
            groupbuy.refresh_from_db()

            if groupbuy.current_participants >= groupbuy.target_participants:
                groupbuy.complete_groupbuy()

        serializer = CustomParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel_participation(self, request, pk=None):
        groupbuy = self.get_object()
        user = request.user

        participant = CustomParticipant.objects.filter(
            custom_groupbuy=groupbuy,
            user=user
        ).first()

        if not participant:
            return Response(
                {'error': '참여 내역이 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if groupbuy.status == 'completed':
            return Response(
                {'error': '완료된 공구는 참여 취소할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if participant.discount_code or participant.discount_url:
            return Response(
                {'error': '할인코드가 이미 발급되어 취소할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.db import transaction

        with transaction.atomic():
            groupbuy = CustomGroupBuy.objects.select_for_update().get(pk=groupbuy.pk)

            participant.delete()

            groupbuy.current_participants = F('current_participants') - 1
            groupbuy.save(update_fields=['current_participants'])

        return Response({'message': '참여가 취소되었습니다.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def early_close(self, request, pk=None):
        groupbuy = self.get_object()

        try:
            groupbuy.early_close(request.user)
            serializer = self.get_serializer(groupbuy)
            return Response(serializer.data)
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def confirm_sale(self, request, pk=None):
        groupbuy = self.get_object()

        if groupbuy.seller != request.user:
            return Response(
                {'error': '판매자만 확정할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if groupbuy.status != 'pending_seller':
            return Response(
                {'error': '판매자 확정 대기 중인 공구만 확정 가능합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        groupbuy.complete_groupbuy()
        serializer = self.get_serializer(groupbuy)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel_sale(self, request, pk=None):
        groupbuy = self.get_object()

        if groupbuy.seller != request.user:
            return Response(
                {'error': '판매자만 취소할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if groupbuy.status != 'pending_seller':
            return Response(
                {'error': '판매자 확정 대기 중인 공구만 취소 가능합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        groupbuy.status = 'cancelled'
        groupbuy.save()

        serializer = self.get_serializer(groupbuy)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        groupbuy = self.get_object()
        user = request.user

        from django.db import transaction

        with transaction.atomic():
            if request.method == 'DELETE':
                deleted_count = CustomFavorite.objects.filter(
                    user=user,
                    custom_groupbuy=groupbuy
                ).delete()[0]

                if deleted_count > 0:
                    groupbuy.favorite_count = F('favorite_count') - 1
                    groupbuy.save(update_fields=['favorite_count'])
                    return Response({'favorited': False})
                else:
                    return Response({'favorited': False})

            else:
                favorite, created = CustomFavorite.objects.get_or_create(
                    user=user,
                    custom_groupbuy=groupbuy
                )

                if created:
                    groupbuy.favorite_count = F('favorite_count') + 1
                    groupbuy.save(update_fields=['favorite_count'])

                return Response({'favorited': True})

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def participants(self, request, pk=None):
        groupbuy = self.get_object()

        if groupbuy.seller != request.user:
            return Response(
                {'error': '판매자만 참여자 목록을 조회할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        participants = CustomParticipant.objects.filter(
            custom_groupbuy=groupbuy,
            status='confirmed'
        ).select_related('user').order_by('participated_at')

        serializer = CustomParticipantSerializer(participants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='participants/(?P<participant_id>[^/.]+)/toggle-used')
    def toggle_discount_used(self, request, pk=None, participant_id=None):
        groupbuy = self.get_object()

        if groupbuy.seller != request.user:
            return Response(
                {'error': '판매자만 할인코드 사용 상태를 변경할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            participant = CustomParticipant.objects.get(
                id=participant_id,
                custom_groupbuy=groupbuy,
                status='confirmed'
            )

            participant.discount_used = not participant.discount_used
            if participant.discount_used:
                participant.discount_used_at = timezone.now()
            else:
                participant.discount_used_at = None
            participant.save()

            serializer = CustomParticipantSerializer(participant)
            return Response(serializer.data)

        except CustomParticipant.DoesNotExist:
            return Response(
                {'error': '참여자를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )


class CustomParticipantViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomParticipantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = CustomParticipant.objects.filter(user=user)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-participated_at')

    @action(
        detail=True,
        methods=['get'],
        authentication_classes=[JWTAuthentication, SessionAuthentication],
        permission_classes=[IsAuthenticated]
    )
    def qr_code(self, request, pk=None):
        """오프라인 공구 할인코드 QR 생성 (세션/JWT 인증 모두 지원)"""
        from django.http import HttpResponse
        import qrcode
        from io import BytesIO

        participant = self.get_object()
        groupbuy = participant.custom_groupbuy

        # 본인 확인
        if participant.user != request.user:
            return Response(
                {'error': '본인의 QR 코드만 조회할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 오프라인 공구만 QR 생성 가능
        if groupbuy.type != 'offline':
            return Response(
                {'error': '오프라인 공구만 QR 코드를 생성할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 할인코드 발급된 경우만
        if not participant.discount_code:
            return Response(
                {'error': '할인코드가 발급되지 않았습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # QR 데이터: 참여코드|할인코드|공구ID
        qr_data = f"{participant.participation_code}|{participant.discount_code}|{groupbuy.id}"

        # QR 코드 생성
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # PNG 이미지로 반환
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        return HttpResponse(buffer.getvalue(), content_type='image/png')

    @action(detail=True, methods=['post'])
    def mark_used(self, request, pk=None):
        participant = self.get_object()

        if participant.discount_used:
            return Response(
                {'error': '이미 사용된 할인입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        participant.discount_used = True
        participant.discount_used_at = timezone.now()
        participant.save()

        serializer = self.get_serializer(participant)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def verify_discount(self, request):
        discount_code = request.data.get('discount_code')
        groupbuy_id = request.data.get('groupbuy_id')

        if not discount_code or not groupbuy_id:
            return Response(
                {'error': '할인코드와 공구 ID가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        groupbuy = CustomGroupBuy.objects.filter(id=groupbuy_id).first()
        if not groupbuy:
            return Response(
                {'error': '존재하지 않는 공구입니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if groupbuy.seller != request.user:
            return Response(
                {'error': '판매자만 할인코드를 검증할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        participant = CustomParticipant.objects.filter(
            custom_groupbuy=groupbuy,
            discount_code=discount_code,
            status='confirmed'
        ).first()

        if not participant:
            return Response(
                {'valid': False, 'error': '유효하지 않은 할인코드입니다.'},
                status=status.HTTP_200_OK
            )

        if participant.discount_used:
            return Response(
                {'valid': False, 'error': '이미 사용된 할인코드입니다.', 'used_at': participant.discount_used_at},
                status=status.HTTP_200_OK
            )

        if groupbuy.discount_valid_until and timezone.now() > groupbuy.discount_valid_until:
            return Response(
                {'valid': False, 'error': '유효기간이 만료된 할인코드입니다.'},
                status=status.HTTP_200_OK
            )

        # 검증만 하고 사용 처리는 하지 않음 (프론트에서 toggle_used API를 별도로 호출)
        return Response({
            'valid': True,
            'message': '할인코드가 검증되었습니다.',
            'user_name': participant.user.username,
            'participation_code': participant.participation_code,
            'discount_used': participant.discount_used,
            'discount_used_at': participant.discount_used_at
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def recent_completed(self, request):
        """최근 종료된 커스텀 공구 조회 (노쇼신고용)

        종료 후 15일 이내의 최근 3건 조회
        판매자/구매자 구분하여 조회
        """
        from datetime import timedelta

        user = request.user
        limit = int(request.query_params.get('limit', 3))

        # 15일 전 날짜 계산
        cutoff_date = timezone.now() - timedelta(days=15)

        logger.info(f"recent_completed called for custom groupbuy user: {user.id}")

        data = []

        try:
            # 판매자인 경우: 내가 생성하고 완료된 공구
            if hasattr(user, 'role') and user.role == 'seller':
                groupbuys = CustomGroupBuy.objects.filter(
                    seller=user,
                    status='completed',
                    completed_at__gte=cutoff_date
                ).prefetch_related('images').order_by('-completed_at')[:limit]

                for groupbuy in groupbuys:
                    try:
                        # 대표 이미지 가져오기
                        primary_image = groupbuy.images.filter(is_primary=True).first()
                        if not primary_image:
                            primary_image = groupbuy.images.first()

                        days_ago = (timezone.now() - groupbuy.completed_at).days

                        data.append({
                            'id': groupbuy.id,
                            'title': groupbuy.title,
                            'type': groupbuy.type,
                            'type_display': groupbuy.get_type_display(),
                            'primary_image': primary_image.image_url if primary_image else None,
                            'completed_at': groupbuy.completed_at.isoformat(),
                            'days_ago': days_ago,
                            'current_participants': groupbuy.current_participants
                        })
                    except Exception as e:
                        logger.error(f"Error processing completed groupbuy {groupbuy.id}: {e}")
                        continue

            # 구매자인 경우: 내가 참여하고 완료된 공구
            else:
                participants = CustomParticipant.objects.filter(
                    user=user,
                    status='confirmed'
                ).select_related('custom_groupbuy').filter(
                    custom_groupbuy__status='completed',
                    custom_groupbuy__completed_at__gte=cutoff_date
                ).order_by('-custom_groupbuy__completed_at')[:limit]

                for participant in participants:
                    try:
                        groupbuy = participant.custom_groupbuy

                        # 대표 이미지 가져오기
                        primary_image = groupbuy.images.filter(is_primary=True).first()
                        if not primary_image:
                            primary_image = groupbuy.images.first()

                        days_ago = (timezone.now() - groupbuy.completed_at).days

                        data.append({
                            'id': groupbuy.id,
                            'title': groupbuy.title,
                            'type': groupbuy.type,
                            'type_display': groupbuy.get_type_display(),
                            'primary_image': primary_image.image_url if primary_image else None,
                            'completed_at': groupbuy.completed_at.isoformat(),
                            'days_ago': days_ago,
                            'current_participants': groupbuy.current_participants,
                            'seller_name': groupbuy.seller.username,
                            'seller_id': groupbuy.seller.id
                        })
                    except Exception as e:
                        logger.error(f"Error processing participant {participant.id}: {e}")
                        continue

            logger.info(f"Found {len(data)} recent completed custom groupbuys")
            return Response(data)

        except Exception as e:
            logger.error(f"recent_completed error: {e}", exc_info=True)
            return Response(
                {'error': '최근 종료된 공구 조회에 실패했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomFavoriteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomFavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustomFavorite.objects.filter(user=self.request.user).order_by('-created_at')