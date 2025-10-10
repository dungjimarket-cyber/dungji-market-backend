"""
커스텀 특가 시리얼라이저
"""
from rest_framework import serializers
from api.models_custom import (
    CustomGroupBuy,
    CustomGroupBuyImage,
    CustomParticipant,
    CustomFavorite,
    CustomGroupBuyRegion
)
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomGroupBuyImageSerializer(serializers.ModelSerializer):
    """공구 이미지 시리얼라이저"""

    imageUrl = serializers.SerializerMethodField()

    class Meta:
        model = CustomGroupBuyImage
        fields = ['id', 'image_url', 'imageUrl', 'is_primary', 'order_index', 'created_at']
        read_only_fields = ['id', 'image_url', 'created_at']

    def get_imageUrl(self, obj):
        """프론트엔드 호환성을 위한 imageUrl 필드"""
        # ImageField 우선, 없으면 image_url 폴백
        if obj.image:
            return obj.image.url
        return obj.image_url if obj.image_url else None


class CustomGroupBuyListSerializer(serializers.ModelSerializer):
    """공구 목록 시리얼라이저"""

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    final_price = serializers.SerializerMethodField()
    is_completed = serializers.BooleanField(read_only=True)
    seller_name = serializers.CharField(read_only=True)
    seller_type = serializers.CharField(read_only=True)
    primary_image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    regions = serializers.SerializerMethodField()

    class Meta:
        model = CustomGroupBuy
        fields = [
            'id', 'title', 'type', 'type_display', 'categories', 'regions', 'usage_guide',
            'pricing_type', 'products', 'original_price', 'discount_rate', 'final_price',
            'target_participants', 'current_participants', 'is_completed',
            'status', 'status_display', 'expired_at',
            'seller_name', 'seller_type',
            'primary_image', 'view_count', 'favorite_count', 'is_favorited',
            'created_at'
        ]

    def get_final_price(self, obj):
        """최종 가격 반환 (여러 상품 지원)"""
        final_price = obj.final_price
        if isinstance(final_price, list):
            if len(final_price) == 1:
                # 상품이 1개면 숫자로 반환 (목록 호환성)
                return final_price[0]
            elif len(final_price) > 1:
                # 여러 개면 범위 반환
                return {
                    'min': min(final_price),
                    'max': max(final_price),
                    'prices': final_price
                }
        elif isinstance(final_price, int):
            return final_price
        return None

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            # ImageField 우선, 없으면 image_url 폴백
            if primary_image.image:
                return primary_image.image.url
            return primary_image.image_url if primary_image.image_url else None
        first_image = obj.images.first()
        if first_image:
            # ImageField 우선, 없으면 image_url 폴백
            if first_image.image:
                return first_image.image.url
            return first_image.image_url if first_image.image_url else None
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CustomFavorite.objects.filter(
                user=request.user,
                custom_groupbuy=obj
            ).exists()
        return False

    def get_regions(self, obj):
        region_links = CustomGroupBuyRegion.objects.filter(
            custom_groupbuy=obj
        ).select_related('region', 'region__parent')

        result = []
        for region_link in region_links:
            region = region_link.region
            if region:
                display_name = region.name
                if region.parent:
                    parent_name = region.parent.name
                    display_name = f"{parent_name} {region.name}"

                result.append({
                    'code': region.code,
                    'name': region.name,
                    'full_name': display_name
                })

        return result


class CustomGroupBuyDetailSerializer(serializers.ModelSerializer):
    """공구 상세 시리얼라이저"""

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    online_discount_type_display = serializers.CharField(
        source='get_online_discount_type_display',
        read_only=True
    )
    final_price = serializers.SerializerMethodField()
    is_completed = serializers.BooleanField(read_only=True)
    seller_name = serializers.CharField(read_only=True)
    seller_type = serializers.CharField(read_only=True)
    is_business_verified = serializers.BooleanField(read_only=True)
    images = CustomGroupBuyImageSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_participated = serializers.SerializerMethodField()
    regions = serializers.SerializerMethodField()

    class Meta:
        model = CustomGroupBuy
        fields = [
            'id', 'title', 'description', 'type', 'type_display',
            'categories', 'regions', 'usage_guide',
            'pricing_type', 'products', 'original_price', 'discount_rate', 'final_price',
            'target_participants', 'current_participants', 'is_completed',
            'max_wait_hours', 'expired_at', 'completed_at',
            'seller_decision_deadline',
            'discount_valid_days', 'discount_valid_until',
            'allow_partial_sale',
            'seller', 'seller_name', 'seller_type', 'is_business_verified',
            'online_discount_type', 'online_discount_type_display',
            'location', 'location_detail', 'phone_number',
            'meta_title', 'meta_image', 'meta_description', 'meta_price',
            'status', 'status_display',
            'view_count', 'favorite_count',
            'images', 'is_favorited', 'is_participated',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'seller', 'current_participants', 'expired_at',
            'completed_at', 'seller_decision_deadline',
            'discount_valid_until', 'status',
            'view_count', 'favorite_count', 'created_at', 'updated_at'
        ]

    def get_final_price(self, obj):
        """최종 가격 반환 (여러 상품 지원)"""
        final_price = obj.final_price
        if isinstance(final_price, list):
            if len(final_price) == 1:
                # 상품이 1개면 숫자로 반환 (목록 호환성)
                return final_price[0]
            elif len(final_price) > 1:
                # 여러 개면 범위 반환
                return {
                    'min': min(final_price),
                    'max': max(final_price),
                    'prices': final_price
                }
        elif isinstance(final_price, int):
            return final_price
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CustomFavorite.objects.filter(
                user=request.user,
                custom_groupbuy=obj
            ).exists()
        return False

    def get_is_participated(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CustomParticipant.objects.filter(
                user=request.user,
                custom_groupbuy=obj,
                status='confirmed'
            ).exists()
        return False

    def get_regions(self, obj):
        region_links = CustomGroupBuyRegion.objects.filter(
            custom_groupbuy=obj
        ).select_related('region', 'region__parent')

        result = []
        for region_link in region_links:
            region = region_link.region
            if region:
                display_name = region.name
                if region.parent:
                    parent_name = region.parent.name
                    display_name = f"{parent_name} {region.name}"

                result.append({
                    'code': region.code,
                    'name': region.name,
                    'full_name': display_name
                })

        return result


class CustomGroupBuyCreateSerializer(serializers.ModelSerializer):
    """공구 생성 시리얼라이저"""

    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=10,
        help_text="최대 10개의 이미지를 업로드할 수 있습니다."
    )
    new_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=10,
        help_text="수정 시 새로 추가할 이미지 (전자제품/휴대폰 호환)"
    )
    existing_image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="수정 시 유지할 기존 이미지 ID 목록 (전자제품/휴대폰 호환)"
    )
    region_codes = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text='지역 코드 목록 (최대 3개)'
    )

    class Meta:
        model = CustomGroupBuy
        fields = [
            'id', 'title', 'description', 'type', 'categories', 'region_codes', 'usage_guide',
            'pricing_type', 'products', 'original_price', 'discount_rate',
            'target_participants', 'max_wait_hours', 'expired_at',
            'discount_valid_days', 'allow_partial_sale',
            'online_discount_type', 'discount_url', 'discount_codes',
            'location', 'location_detail', 'phone_number',
            'images', 'new_images', 'existing_image_ids'
        ]

    def validate(self, data):
        # 제목 길이 검증
        title = data.get('title', '')
        if len(title) > 50:
            raise serializers.ValidationError({
                'title': '제목은 최대 50자까지 입력 가능합니다.'
            })

        # 설명 길이 검증
        description = data.get('description', '')
        if len(description) > 5000:
            raise serializers.ValidationError({
                'description': '설명은 최대 5,000자까지 입력 가능합니다.'
            })

        # 이용안내 길이 검증
        usage_guide = data.get('usage_guide', '')
        if usage_guide and len(usage_guide) > 1000:
            raise serializers.ValidationError({
                'usage_guide': '이용안내는 최대 1,000자까지 입력 가능합니다.'
            })

        # 카테고리 검증
        categories = data.get('categories', [])
        if not categories:
            raise serializers.ValidationError({
                'categories': '최소 1개 이상의 카테고리를 선택해주세요.'
            })
        if len(categories) > 5:
            raise serializers.ValidationError({
                'categories': '카테고리는 최대 5개까지 선택 가능합니다.'
            })
        if len(set(categories)) != len(categories):
            raise serializers.ValidationError({
                'categories': '중복된 카테고리가 있습니다.'
            })

        # 유효한 카테고리인지 검증
        from api.models_custom import CustomGroupBuy
        valid_categories = [choice[0] for choice in CustomGroupBuy.CATEGORY_CHOICES]
        for category in categories:
            if category not in valid_categories:
                raise serializers.ValidationError({
                    'categories': f'유효하지 않은 카테고리입니다: {category}'
                })

        # products 필드 검증 (단일상품 여러 개)
        pricing_type = data.get('pricing_type', 'single_product')
        products = data.get('products', [])

        if pricing_type == 'single_product':
            if products:
                # products 필드 사용
                if len(products) > 10:
                    raise serializers.ValidationError({
                        'products': '상품은 최대 10개까지 등록 가능합니다.'
                    })
                if len(products) == 0:
                    raise serializers.ValidationError({
                        'products': '단일상품 유형은 최소 1개 이상의 상품이 필요합니다.'
                    })

                # 각 상품 검증
                for idx, product in enumerate(products):
                    if not isinstance(product, dict):
                        raise serializers.ValidationError({
                            'products': f'상품 {idx+1}: 올바른 형식이 아닙니다.'
                        })
                    if 'name' not in product or not product['name']:
                        raise serializers.ValidationError({
                            'products': f'상품 {idx+1}: 상품명은 필수입니다.'
                        })
                    if 'original_price' not in product or product['original_price'] <= 0:
                        raise serializers.ValidationError({
                            'products': f'상품 {idx+1}: 정가는 필수이며 0보다 커야 합니다.'
                        })
                    if 'discount_rate' not in product or not (0 <= product['discount_rate'] <= 100):
                        raise serializers.ValidationError({
                            'products': f'상품 {idx+1}: 할인율은 0~100 사이여야 합니다.'
                        })

        elif pricing_type == 'all_products':
            # 전품목 할인은 discount_rate만 필요
            discount_rate = data.get('discount_rate')
            if discount_rate is None:
                raise serializers.ValidationError({
                    'discount_rate': '전품목 할인 시 할인율은 필수입니다.'
                })

        # 이미지 개수 검증
        images = data.get('images', [])
        if images and len(images) > 10:
            raise serializers.ValidationError({
                'images': '이미지는 최대 10개까지 등록 가능합니다.'
            })

        # 할인코드 검증
        discount_codes = data.get('discount_codes', [])
        if discount_codes:
            if not all(str(code).strip() for code in discount_codes):
                raise serializers.ValidationError({
                    'discount_codes': '빈 할인코드는 등록할 수 없습니다.'
                })
            if len(set(discount_codes)) != len(discount_codes):
                raise serializers.ValidationError({
                    'discount_codes': '중복된 할인코드가 있습니다.'
                })
            for code in discount_codes:
                if len(str(code)) > 50:
                    raise serializers.ValidationError({
                        'discount_codes': '각 할인코드는 최대 50자까지 입력 가능합니다.'
                    })

        # 지역 검증 (ViewSet에서 처리하므로 여기서는 개수만 체크)
        region_codes = data.get('region_codes', [])
        if region_codes and len(region_codes) > 3:
            raise serializers.ValidationError({
                'region_codes': '최대 3개까지 지역을 선택할 수 있습니다.'
            })

        # 온라인 공구 검증
        if data.get('type') == 'online':
            if not data.get('online_discount_type'):
                raise serializers.ValidationError({
                    'online_discount_type': '온라인 공구는 할인 제공 방식이 필수입니다.'
                })

            discount_type = data.get('online_discount_type')
            if discount_type in ['link_only', 'both'] and not data.get('discount_url'):
                raise serializers.ValidationError({
                    'discount_url': '할인링크 제공 시 링크가 필수입니다.'
                })

            if discount_type in ['code_only', 'both']:
                codes = data.get('discount_codes', [])
                if not codes:
                    raise serializers.ValidationError({
                        'discount_codes': '할인코드 제공 시 코드가 필수입니다.'
                    })
                if len(codes) < data.get('target_participants', 0):
                    raise serializers.ValidationError({
                        'discount_codes': f'할인코드 개수가 목표 인원보다 적습니다.'
                    })

        # 오프라인 공구 검증
        if data.get('type') == 'offline':
            # regions 필드 체크 (프론트엔드는 regions로 전송)
            regions = self.initial_data.get('regions', []) if hasattr(self, 'initial_data') else []
            if not regions and not region_codes:
                raise serializers.ValidationError({
                    'regions': '오프라인 공구는 지역 선택이 필수입니다.'
                })
            if not data.get('location'):
                raise serializers.ValidationError({
                    'location': '오프라인 공구는 매장 위치가 필수입니다.'
                })
            if not data.get('phone_number'):
                raise serializers.ValidationError({
                    'phone_number': '오프라인 공구는 연락처가 필수입니다.'
                })
            if not data.get('discount_valid_days'):
                raise serializers.ValidationError({
                    'discount_valid_days': '오프라인 공구는 할인 유효기간이 필수입니다.'
                })

            codes = data.get('discount_codes', [])
            if not codes:
                raise serializers.ValidationError({
                    'discount_codes': '오프라인 공구는 할인코드가 필수입니다.'
                })
            if len(codes) < data.get('target_participants', 0):
                raise serializers.ValidationError({
                    'discount_codes': f'할인코드 개수가 목표 인원보다 적습니다. (필요: {data.get("target_participants")}, 보유: {len(codes)})'
                })

        return data

    def create(self, validated_data):
        from django.db import transaction
        from api.services.image_service import ImageService
        import logging

        logger = logging.getLogger(__name__)

        images_data = validated_data.pop('images', [])
        validated_data.pop('region_codes', None)  # ViewSet에서 처리 (없을 수도 있음)

        logger.info(f"[CustomGroupBuy Create] images count: {len(images_data)}")

        # 단일상품일 때 구버전 필드에도 복사 (Admin 가독성)
        pricing_type = validated_data.get('pricing_type', 'single_product')
        products = validated_data.get('products', [])

        if pricing_type == 'single_product' and products and len(products) > 0:
            first_product = products[0]
            validated_data['original_price'] = first_product.get('original_price')
            validated_data['discount_rate'] = first_product.get('discount_rate')
            logger.info(f"[단일상품] 구버전 필드에 복사 - 정가: {validated_data['original_price']}, 할인율: {validated_data['discount_rate']}")

        with transaction.atomic():
            groupbuy = CustomGroupBuy.objects.create(
                **validated_data
            )

            # 이미지 처리 (중고폰 방식과 동일)
            for index, image in enumerate(images_data):
                try:
                    # ImageField에 직접 저장 (중고거래 방식)
                    groupbuy_image = CustomGroupBuyImage.objects.create(
                        custom_groupbuy=groupbuy,
                        image=image,
                        is_primary=(index == 0),
                        order_index=index
                    )
                    logger.info(f"[이미지 저장 완료] ID: {groupbuy_image.id}, 순서: {index}")
                except Exception as e:
                    logger.error(f"[이미지 처리 실패] index={index}, error={e}", exc_info=True)

        return groupbuy

    def update(self, instance, validated_data):
        from django.db import transaction
        from api.services.image_service import ImageService
        import logging

        logger = logging.getLogger(__name__)

        # 이미지 관련 데이터 추출 (전자제품 방식)
        images_data = validated_data.pop('images', None)  # 기존 방식 호환
        new_images_data = validated_data.pop('new_images', None)
        existing_image_ids = validated_data.pop('existing_image_ids', None)
        validated_data.pop('region_codes', None)  # ViewSet에서 처리

        logger.info(f"[CustomGroupBuy Update] images: {len(images_data) if images_data else 0}, new_images: {len(new_images_data) if new_images_data else 0}, existing_ids: {existing_image_ids}")

        # 단일상품일 때 구버전 필드에도 복사 (Admin 가독성)
        pricing_type = validated_data.get('pricing_type', instance.pricing_type)
        products = validated_data.get('products', instance.products)

        if pricing_type == 'single_product' and products and len(products) > 0:
            first_product = products[0]
            validated_data['original_price'] = first_product.get('original_price')
            validated_data['discount_rate'] = first_product.get('discount_rate')
            logger.info(f"[단일상품] 구버전 필드에 복사 - 정가: {validated_data['original_price']}, 할인율: {validated_data['discount_rate']}")

        with transaction.atomic():
            # 기본 필드 업데이트
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # 이미지 업데이트 - 전자제품/휴대폰 방식
            if new_images_data is not None or existing_image_ids is not None:
                logger.info(f"[이미지 수정 시작] existing_image_ids: {existing_image_ids}, new_images: {len(new_images_data) if new_images_data else 0}")

                # 유지할 이미지와 삭제할 이미지 구분
                if existing_image_ids:
                    # 기존 이미지 상태 확인
                    before_images = list(instance.images.all().values('id', 'order_index', 'is_primary'))
                    logger.info(f"[수정 전 이미지] {before_images}")

                    # 기존 이미지 중 existing_image_ids에 없는 것만 삭제
                    deleted = instance.images.exclude(id__in=existing_image_ids)
                    deleted_ids = list(deleted.values_list('id', flat=True))
                    deleted.delete()
                    logger.info(f"[삭제된 이미지 ID] {deleted_ids}")

                    # 유지된 이미지들의 순서 재정렬 (전자제품과 동일)
                    logger.info(f"[순서 재정렬 시작] existing_image_ids 순서: {existing_image_ids}")
                    for idx, img_id in enumerate(existing_image_ids):
                        logger.info(f"[재정렬] ID {img_id} → order_index={idx}, is_primary={idx == 0}")
                        CustomGroupBuyImage.objects.filter(id=img_id).update(
                            order_index=idx,
                            is_primary=(idx == 0)
                        )

                    # 재정렬 후 상태 확인
                    after_images = list(instance.images.all().values('id', 'order_index', 'is_primary'))
                    logger.info(f"[재정렬 후 이미지] {after_images}")
                else:
                    # existing_image_ids가 없으면 모든 기존 이미지 삭제
                    deleted_count = instance.images.all().delete()[0]
                    logger.info(f"[모든 기존 이미지 삭제] {deleted_count}개")

                # 새 이미지 추가
                if new_images_data:
                    # 기존 이미지의 최대 order_index 값 찾기
                    from django.db.models import Max
                    max_order = instance.images.aggregate(max_order=Max('order_index'))['max_order'] or -1

                    for idx, image in enumerate(new_images_data):
                        try:
                            CustomGroupBuyImage.objects.create(
                                custom_groupbuy=instance,
                                image=image,
                                is_primary=(max_order == -1 and idx == 0),  # 기존 이미지가 없으면 첫 번째를 primary로
                                order_index=max_order + idx + 1
                            )
                            logger.info(f"[이미지 저장 완료] 새 이미지 {idx + 1}/{len(new_images_data)}")
                        except Exception as e:
                            logger.error(f"[이미지 처리 실패] index={idx}, error={e}", exc_info=True)
            elif images_data is not None:
                # 기존 방식 호환 (images 필드로 온 경우)
                instance.images.all().delete()

                # 새 이미지 생성
                for index, image in enumerate(images_data):
                    try:
                        # ImageField에 직접 저장 (중고거래 방식)
                        groupbuy_image = CustomGroupBuyImage.objects.create(
                            custom_groupbuy=instance,
                            image=image,
                            is_primary=(index == 0),
                            order_index=index
                        )
                        logger.info(f"[이미지 저장 완료] ID: {groupbuy_image.id}, 순서: {index}")
                    except Exception as e:
                        logger.error(f"[이미지 처리 실패] index={index}, error={e}", exc_info=True)

        return instance


class CustomParticipantSerializer(serializers.ModelSerializer):
    """참여자 시리얼라이저"""

    user_name = serializers.CharField(source='user.username', read_only=True)
    groupbuy_title = serializers.CharField(source='custom_groupbuy.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CustomParticipant
        fields = [
            'id', 'user', 'user_name', 'custom_groupbuy', 'groupbuy_title',
            'participated_at', 'participation_code',
            'discount_code', 'discount_url',
            'discount_used', 'discount_used_at',
            'status', 'status_display'
        ]
        read_only_fields = [
            'id', 'user', 'participated_at', 'participation_code',
            'discount_code', 'discount_url'
        ]


class CustomFavoriteSerializer(serializers.ModelSerializer):
    """찜 시리얼라이저"""

    groupbuy = CustomGroupBuyListSerializer(source='custom_groupbuy', read_only=True)

    class Meta:
        model = CustomFavorite
        fields = ['id', 'custom_groupbuy', 'groupbuy', 'created_at']
        read_only_fields = ['id', 'created_at']