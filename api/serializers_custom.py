"""
커스텀 특가 시리얼라이저
"""
from rest_framework import serializers
from api.models_custom import (
    CustomGroupBuy,
    CustomGroupBuyImage,
    CustomParticipant,
    CustomFavorite,
    CustomGroupBuyRegion,
    CustomNoShowReport
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
    deal_type_display = serializers.CharField(source='get_deal_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    final_price = serializers.SerializerMethodField()
    is_completed = serializers.BooleanField(read_only=True)
    seller_name = serializers.CharField(read_only=True)
    seller_type = serializers.CharField(read_only=True)
    primary_image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = CustomGroupBuy
        fields = [
            'id', 'title', 'type', 'type_display', 'deal_type', 'deal_type_display',
            'categories', 'location', 'usage_guide',
            'pricing_type', 'products', 'product_name', 'original_price', 'discount_rate', 'final_price',
            'target_participants', 'current_participants', 'is_completed',
            'status', 'status_display', 'expired_at',
            'seller_name', 'seller_type',
            'online_discount_type',  # 할인 제공 방식 추가
            'discount_url',  # 기간특가 링크
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


class CustomGroupBuyDetailSerializer(serializers.ModelSerializer):
    """공구 상세 시리얼라이저"""

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    deal_type_display = serializers.CharField(source='get_deal_type_display', read_only=True)
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

    class Meta:
        model = CustomGroupBuy
        fields = [
            'id', 'title', 'description', 'type', 'type_display',
            'deal_type', 'deal_type_display',
            'categories', 'location', 'location_detail', 'usage_guide',
            'pricing_type', 'products', 'product_name', 'original_price', 'discount_rate', 'final_price',
            'target_participants', 'current_participants', 'is_completed',
            'max_wait_hours', 'expired_at', 'completed_at',
            'seller_decision_deadline',
            'discount_valid_days', 'discount_valid_until',
            'allow_partial_sale',
            'seller', 'seller_name', 'seller_type', 'is_business_verified',
            'online_discount_type', 'online_discount_type_display',
            'discount_url', 'discount_codes',  # ← 할인 정보 추가
            'description_link_previews',  # ← 기간특가 설명 내 링크 미리보기
            'phone_number',
            'meta_title', 'meta_image', 'meta_description', 'meta_price',
            'status', 'status_display',
            'view_count', 'favorite_count', 'discount_url_clicks',
            'images', 'is_favorited', 'is_participated',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'seller', 'current_participants', 'expired_at',
            'completed_at', 'seller_decision_deadline',
            'discount_valid_until', 'status',
            'view_count', 'favorite_count', 'discount_url_clicks', 'created_at', 'updated_at'
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

    class Meta:
        model = CustomGroupBuy
        fields = [
            'id', 'title', 'description', 'type', 'categories', 'usage_guide',
            'deal_type', 'pricing_type', 'products', 'original_price', 'discount_rate',
            'target_participants', 'max_wait_hours', 'expired_at',
            'discount_valid_days', 'allow_partial_sale',
            'online_discount_type', 'discount_url', 'discount_codes',
            'description_link_previews',
            'location', 'location_detail', 'phone_number',
            'images', 'new_images', 'existing_image_ids'
        ]

    def __init__(self, *args, **kwargs):
        """수정 시 수정 불가 필드를 optional로 변경"""
        super().__init__(*args, **kwargs)

        # update 시에는 수정 불가 필드들을 optional로 만듦
        if self.instance is not None:
            # instance가 있으면 update 모드
            self.fields['type'].required = False
            self.fields['target_participants'].required = False
            self.fields['discount_codes'].required = False

    def validate(self, data):
        # update 모드인지 확인 (instance가 있으면 update)
        is_update = self.instance is not None

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

        # 카테고리 검증 (전송된 경우만)
        categories = data.get('categories')
        if categories is not None:
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

        # 기간특가 분기 처리
        deal_type = data.get('deal_type', 'participant_based')

        if deal_type == 'time_based':
            # 상품설명 내 링크 미리보기 생성 (선택적)
            description = data.get('description', '')
            if description:
                import re
                # URL 패턴 찾기
                url_pattern = r'https?://[^\s<>"\'()]+'
                urls = re.findall(url_pattern, description)

                # 중복 제거
                unique_urls = list(dict.fromkeys(urls))

                # 미리보기 생성
                previews = []
                from api.services.link_preview_service import LinkPreviewService
                for url in unique_urls:
                    try:
                        metadata = LinkPreviewService.extract_metadata(url)
                        previews.append(metadata)
                    except Exception as e:
                        logger.warning(f"링크 미리보기 생성 실패: {url} - {e}")
                        continue

                data['description_link_previews'] = previews

            # 기간특가용 값 설정
            data['target_participants'] = None  # null 허용으로 변경
            data['online_discount_type'] = None
            # pricing_type은 프론트엔드에서 보낸 값 유지 (single_product, all_products 등)
            data['allow_partial_sale'] = False  # 기간특가는 부분 판매 불가

            # 기간특가도 일반 검증 진행 (가격 정보 등)

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

        elif pricing_type == 'coupon_only':
            # 쿠폰전용: 가격 정보 불필요
            # 온라인/오프라인 모두 할인 제공 방식 선택 가능
            pass

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
            # 중복 허용 (동일한 코드를 여러 참여자에게 제공 가능)
            # if len(set(discount_codes)) != len(discount_codes):
            #     raise serializers.ValidationError({
            #         'discount_codes': '중복된 할인코드가 있습니다.'
            #     })
            for code in discount_codes:
                if len(str(code)) > 500:
                    raise serializers.ValidationError({
                        'discount_codes': '각 할인코드는 최대 500자까지 입력 가능합니다.'
                    })


        # update 시 instance 값 참조
        current_type = data.get('type', self.instance.type if is_update else None)
        current_target_participants = data.get('target_participants', self.instance.target_participants if is_update else 0)

        # 온라인 공구 검증 (생성 시에만 검증, 수정 시에는 type이 없으므로 스킵)
        # 기간특가는 할인 제공 방식 선택 불필요
        if current_type == 'online' and not is_update and deal_type != 'time_based':
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
                if len(codes) < current_target_participants:
                    raise serializers.ValidationError({
                        'discount_codes': f'할인코드 개수가 목표 인원보다 적습니다.'
                    })

        # 오프라인 공구 검증 (생성 시에만 검증, 수정 시에는 type이 없으므로 스킵)
        if current_type == 'offline' and not is_update:
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
            if len(codes) < current_target_participants:
                raise serializers.ValidationError({
                    'discount_codes': f'할인코드 개수가 목표 인원보다 적습니다. (필요: {current_target_participants}, 보유: {len(codes)})'
                })

        return data

    def create(self, validated_data):
        from django.db import transaction
        from api.services.image_service import ImageService
        import logging

        logger = logging.getLogger(__name__)

        images_data = validated_data.pop('images', [])

        logger.info(f"[CustomGroupBuy Create] images count: {len(images_data)}")

        # 기간특가 처리: 메인 링크 미리보기 생성
        deal_type = validated_data.get('deal_type', 'participant_based')
        if deal_type == 'time_based':
            discount_url = validated_data.get('discount_url')
            if discount_url:
                try:
                    from api.services.link_preview_service import LinkPreviewService
                    metadata = LinkPreviewService.extract_metadata(discount_url)

                    # 메타 필드에 저장
                    validated_data['meta_title'] = metadata.get('title', '')
                    validated_data['meta_image'] = metadata.get('image', '')
                    validated_data['meta_description'] = metadata.get('description', '')

                    logger.info(f"[기간특가] 메인 링크 미리보기 생성 완료: {discount_url}")
                except Exception as e:
                    logger.warning(f"[기간특가] 메인 링크 미리보기 생성 실패: {discount_url} - {e}")

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

        # 수정 불가능한 필드 제거 (방어적 처리)
        # type, target_participants는 수정 불가능
        # deal_type도 수정 불가능 (생성 시 결정)
        # 할인 정보(discount_codes, discount_url, discount_valid_days)는 수정 가능
        validated_data.pop('type', None)
        validated_data.pop('target_participants', None)
        validated_data.pop('deal_type', None)

        # 기간특가 처리: discount_url이 변경된 경우 메인 링크 미리보기 재생성
        if instance.deal_type == 'time_based':
            discount_url = validated_data.get('discount_url')
            # discount_url이 명시적으로 전달되고, 기존 값과 다른 경우
            if discount_url and discount_url != instance.discount_url:
                try:
                    from api.services.link_preview_service import LinkPreviewService
                    metadata = LinkPreviewService.extract_metadata(discount_url)

                    # 메타 필드 업데이트
                    validated_data['meta_title'] = metadata.get('title', '')
                    validated_data['meta_image'] = metadata.get('image', '')
                    validated_data['meta_description'] = metadata.get('description', '')

                    logger.info(f"[기간특가] 메인 링크 미리보기 재생성 완료: {discount_url}")
                except Exception as e:
                    logger.warning(f"[기간특가] 메인 링크 미리보기 재생성 실패: {discount_url} - {e}")

            # 설명이 변경된 경우 링크 미리보기 재생성
            description = validated_data.get('description')
            if description and description != instance.description:
                import re
                url_pattern = r'https?://[^\s<>"\'()]+'
                urls = re.findall(url_pattern, description)
                unique_urls = list(dict.fromkeys(urls))

                previews = []
                from api.services.link_preview_service import LinkPreviewService
                for url in unique_urls:
                    try:
                        metadata = LinkPreviewService.extract_metadata(url)
                        previews.append(metadata)
                    except Exception as e:
                        logger.warning(f"링크 미리보기 생성 실패: {url} - {e}")
                        continue

                validated_data['description_link_previews'] = previews
                logger.info(f"[기간특가] 설명 내 링크 미리보기 재생성 완료: {len(previews)}개")

        # 이미지 관련 데이터 추출 (전자제품 방식)
        images_data = validated_data.pop('images', None)  # 기존 방식 호환
        new_images_data = validated_data.pop('new_images', None)
        existing_image_ids = validated_data.pop('existing_image_ids', None)

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

            # 이미지 업데이트 - 중고거래 방식 (is_primary는 건드리지 않음)
            if new_images_data is not None or existing_image_ids is not None:
                logger.info(f"[이미지 수정 시작] existing_image_ids: {existing_image_ids}, new_images: {len(new_images_data) if new_images_data else 0}")

                # 유지할 이미지와 삭제할 이미지 구분
                if existing_image_ids:
                    # 정수 변환
                    existing_ids = [int(id) for id in existing_image_ids if id]

                    # 기존 이미지 중 existing_image_ids에 없는 것만 삭제
                    deleted = instance.images.exclude(id__in=existing_ids)
                    deleted_count = deleted.count()
                    deleted.delete()
                    logger.info(f"[이미지 삭제] {deleted_count}개 삭제 (유지: {len(existing_ids)}개)")

                    # 유지된 이미지들의 순서 재정렬 + 대표사진 설정
                    # unique constraint 충돌 방지: 2단계 업데이트 (임시값 → 실제값)

                    # 1단계: 먼저 임시 order_index로 변경 (충돌 방지)
                    images_to_update = []
                    for idx, img_id in enumerate(existing_ids):
                        img = CustomGroupBuyImage.objects.get(id=img_id)
                        img.order_index = 1000 + idx  # 임시 순서
                        images_to_update.append(img)
                    CustomGroupBuyImage.objects.bulk_update(images_to_update, ['order_index'])
                    logger.info(f"[1단계] 임시 순서로 변경 완료")

                    # 2단계: 실제 순서 + is_primary 설정
                    images_to_update = []
                    for idx, img_id in enumerate(existing_ids):
                        img = CustomGroupBuyImage.objects.get(id=img_id)
                        img.order_index = idx
                        img.is_primary = (idx == 0)
                        images_to_update.append(img)
                        logger.info(f"[2단계 준비] ID {img_id} → order_index={idx}, is_primary={idx == 0}")

                    CustomGroupBuyImage.objects.bulk_update(images_to_update, ['order_index', 'is_primary'])
                    logger.info(f"[순서 재정렬 완료] {len(images_to_update)}개 이미지 (대표사진: {existing_ids[0] if existing_ids else 'N/A'})")
                else:
                    # existing_image_ids가 없으면 모든 기존 이미지 삭제
                    deleted_count = instance.images.all().delete()[0]
                    logger.info(f"[모든 기존 이미지 삭제] {deleted_count}개")

                # 새 이미지 추가
                existing_count = len(existing_image_ids) if existing_image_ids else 0
                if new_images_data:
                    for idx, image in enumerate(new_images_data):
                        try:
                            CustomGroupBuyImage.objects.create(
                                custom_groupbuy=instance,
                                image=image,
                                is_primary=(existing_count == 0 and idx == 0),  # 기존 이미지가 없고 첫 번째면 primary
                                order_index=existing_count + idx  # 기존 이미지 다음 순서
                            )
                            logger.info(f"[새 이미지 추가] {idx + 1}/{len(new_images_data)}")
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

    user_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    custom_groupbuy = CustomGroupBuyListSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    discount_valid_until = serializers.SerializerMethodField()

    class Meta:
        model = CustomParticipant
        fields = [
            'id', 'user', 'user_id', 'user_name', 'phone_number', 'custom_groupbuy',
            'participated_at', 'participation_code',
            'discount_code', 'discount_url',
            'discount_used', 'discount_used_at', 'discount_valid_until',
            'status', 'status_display'
        ]
        read_only_fields = [
            'id', 'user', 'user_id', 'participated_at', 'participation_code',
            'discount_code', 'discount_url', 'discount_valid_until'
        ]

    def get_user_name(self, obj):
        """닉네임이 비어있으면 '회원{id}' 형식으로 반환"""
        if obj.user.nickname:
            return obj.user.nickname
        return f"회원{obj.user.id}"

    def get_discount_valid_until(self, obj):
        """공구의 할인 유효기간 반환"""
        return obj.custom_groupbuy.discount_valid_until


class CustomFavoriteSerializer(serializers.ModelSerializer):
    """찜 시리얼라이저"""

    groupbuy = CustomGroupBuyListSerializer(source='custom_groupbuy', read_only=True)

    class Meta:
        model = CustomFavorite
        fields = ['id', 'custom_groupbuy', 'groupbuy', 'created_at']
        read_only_fields = ['id', 'created_at']


class CustomNoShowReportSerializer(serializers.ModelSerializer):
    """커스텀 공구 노쇼 신고 시리얼라이저"""
    reporter_name = serializers.CharField(source='reporter.username', read_only=True)
    reported_user_name = serializers.CharField(source='reported_user.username', read_only=True)
    reported_user_nickname = serializers.CharField(source='reported_user.nickname', read_only=True)
    reported_user_phone = serializers.CharField(source='reported_user.phone_number', read_only=True)
    custom_groupbuy_title = serializers.CharField(source='custom_groupbuy.title', read_only=True)

    class Meta:
        model = CustomNoShowReport
        fields = ['id', 'reporter', 'reporter_name', 'reported_user', 'reported_user_name',
                 'reported_user_nickname', 'reported_user_phone',
                 'custom_groupbuy', 'custom_groupbuy_title', 'participant', 'report_type',
                 'content', 'evidence_image', 'evidence_image_2', 'evidence_image_3',
                 'status', 'admin_comment', 'created_at',
                 'updated_at', 'processed_at', 'processed_by', 'edit_count',
                 'last_edited_at', 'noshow_buyers']
        read_only_fields = ['id', 'reporter', 'status', 'admin_comment', 'created_at',
                           'updated_at', 'processed_at', 'processed_by', 'edit_count',
                           'last_edited_at']

    def validate(self, data):
        """유효성 검사"""
        user = self.context['request'].user
        custom_groupbuy = data.get('custom_groupbuy')
        reported_user = data.get('reported_user')
        report_type = data.get('report_type')

        # 기간특가는 노쇼 신고 불가
        if custom_groupbuy.deal_type == 'time_based':
            raise serializers.ValidationError({
                'custom_groupbuy': '기간 특가는 노쇼 신고 대상이 아닙니다.'
            })

        # 쿠폰전용은 노쇼 신고 불가
        if custom_groupbuy.pricing_type == 'coupon_only':
            raise serializers.ValidationError({
                'custom_groupbuy': '쿠폰전용 공구는 노쇼 신고 대상이 아닙니다.'
            })

        # 자기 자신 신고 방지
        if user == reported_user:
            raise serializers.ValidationError({
                'reported_user': '자기 자신을 신고할 수 없습니다.'
            })

        # 신고 유형별 검증
        if report_type == 'buyer_noshow':
            # 구매자 노쇼: 판매자가 구매자를 신고
            # 커스텀 공구에서는 판매자가 공구 생성자인지 확인
            if custom_groupbuy.seller != user:
                raise serializers.ValidationError({
                    'report_type': '구매자 노쇼는 판매자(공구 생성자)만 신고할 수 있습니다.'
                })

            # 신고 대상이 참여자인지 확인
            participant = CustomParticipant.objects.filter(
                user=reported_user,
                custom_groupbuy=custom_groupbuy,
                status='confirmed'
            ).first()

            if not participant:
                raise serializers.ValidationError({
                    'reported_user': '신고 대상이 해당 공구 참여자가 아닙니다.'
                })

            data['participant'] = participant

        elif report_type == 'seller_noshow':
            # 판매자 노쇼: 구매자가 판매자를 신고
            # 신고자가 참여자인지 확인
            participant = CustomParticipant.objects.filter(
                user=user,
                custom_groupbuy=custom_groupbuy,
                status='confirmed'
            ).first()

            if not participant:
                raise serializers.ValidationError({
                    'custom_groupbuy': '해당 공구에 참여하지 않았습니다.'
                })

            # 신고 대상이 판매자인지 확인
            if custom_groupbuy.seller != reported_user:
                raise serializers.ValidationError({
                    'reported_user': '신고 대상이 판매자가 아닙니다.'
                })

            data['participant'] = participant

        return data