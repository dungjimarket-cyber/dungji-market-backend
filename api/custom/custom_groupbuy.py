from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
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
        elif self.action == 'create':
            return CustomGroupBuyCreateSerializer
        return CustomGroupBuyDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        active_count = CustomGroupBuy.objects.filter(
            seller=request.user,
            status__in=['recruiting', 'pending_seller']
        ).count()

        if active_count >= 10:
            return Response(
                {'error': '동시에 진행할 수 있는 공구는 최대 10개입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 중고거래 방식 - Serializer가 이미지 처리
        logger.info(f"=== CustomGroupBuy Create Request ===")
        logger.info(f"User: {request.user}")
        logger.info(f"Request data keys: {request.data.keys()}")
        logger.info(f"Request FILES keys: {request.FILES.keys()}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.seller != request.user:
            return Response(
                {'error': '판매자만 수정할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 참여자가 있을 때는 제목, 상세설명, 이용안내만 수정 가능
        if instance.current_participants > 0:
            allowed_fields = ['title', 'description', 'usage_guide']
            for field in request.data.keys():
                if field not in allowed_fields and field not in ['images', 'existing_images']:
                    return Response(
                        {'error': '참여자가 있는 공구는 제목, 상세설명, 이용안내만 수정 가능합니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # 중고거래 방식 - Serializer가 이미지 처리
        logger.info(f"=== CustomGroupBuy Update Request ===")
        logger.info(f"User: {request.user}")
        logger.info(f"Request data keys: {request.data.keys()}")
        logger.info(f"Request FILES keys: {request.FILES.keys()}")

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

    def get_queryset(self):
        queryset = CustomGroupBuy.objects.select_related('seller').prefetch_related(
            'images',
            'region_links__region__parent',
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

        region_code = self.request.query_params.get('region')
        if region_code:
            queryset = queryset.filter(
                region_links__region__code__startswith=region_code[:5]
            ).distinct()

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
            user=user,
            status='confirmed'
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

            participant.status = 'cancelled'
            participant.save()

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

        participant.discount_used = True
        participant.discount_used_at = timezone.now()
        participant.verified_by = request.user
        participant.save()

        return Response({
            'valid': True,
            'message': '할인코드가 검증되었습니다.',
            'user_name': participant.user.username,
            'participation_code': participant.participation_code,
            'verified_at': participant.discount_used_at
        })


class CustomFavoriteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomFavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustomFavorite.objects.filter(user=self.request.user).order_by('-created_at')