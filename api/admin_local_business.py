"""
지역 업체 정보 Admin
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from django.http import HttpResponse
from django.contrib import messages
from django.utils.html import format_html
from django.core.management import call_command
from .models_local_business import (
    LocalBusinessCategory,
    LocalBusiness,
    LocalBusinessLink,
    LocalBusinessView
)
import io


@admin.register(LocalBusinessCategory)
class LocalBusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'name_en', 'google_place_type', 'order_index', 'is_active']
    list_editable = ['order_index', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'name_en']
    ordering = ['order_index', 'name']

    actions = ['init_categories']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('init-categories/', self.admin_site.admin_view(self.init_categories_view), name='init_local_business_categories_url'),
        ]
        return custom_urls + urls

    def init_categories_view(self, request):
        """카테고리 초기화 실행 (URL 직접 접속용)"""
        try:
            call_command('init_local_business_categories')
            self.message_user(request, "✅ 7개 업종 카테고리가 생성되었습니다!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ 오류 발생: {str(e)}", messages.ERROR)

        return redirect('../')

    def init_categories(self, request, queryset):
        """카테고리 초기화 액션"""
        try:
            call_command('init_local_business_categories')
            self.message_user(request, "카테고리가 초기화되었습니다.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"오류 발생: {str(e)}", messages.ERROR)

    init_categories.short_description = "📋 카테고리 초기화 (7개 업종 생성)"


@admin.register(LocalBusiness)
class LocalBusinessAdmin(admin.ModelAdmin):
    list_display = [
        'rank_badge',
        'name',
        'region_name',
        'category_name',
        'rating_display',
        'review_count',
        'website_display',
        'opening_hours_display',
        'view_count',
        'is_new',
        'is_verified',
        'last_synced_at'
    ]
    list_filter = ['region_name', 'category', 'is_verified', 'is_new']
    search_fields = ['name', 'address', 'phone_number', 'region_name']
    ordering = ['region_name', 'category', 'rank_in_region']
    readonly_fields = [
        'google_place_id',
        'latitude',
        'longitude',
        'popularity_score',
        'view_count',
        'last_synced_at',
        'created_at',
        'updated_at',
        'google_maps_link',
        'refresh_button',
        'photo_preview'
    ]

    fieldsets = (
        ('데이터 갱신', {
            'fields': ('refresh_button',),
            'description': '이 업체의 최신 정보를 Google Places API에서 가져옵니다.'
        }),
        ('기본 정보', {
            'fields': ('category', 'region_name', 'name', 'address', 'phone_number', 'website_url')
        }),
        ('평점 및 순위', {
            'fields': ('rating', 'review_count', 'popularity_score', 'rank_in_region')
        }),
        ('AI 요약', {
            'fields': ('editorial_summary',)
        }),
        ('이미지', {
            'fields': ('photo_preview', 'custom_photo', 'photo_url'),
            'description': 'custom_photo가 있으면 우선 표시, 없으면 Google photo_url 사용'
        }),
        ('상태', {
            'fields': ('is_verified', 'is_new', 'view_count')
        }),
        ('Google Places 정보', {
            'fields': ('google_place_id', 'latitude', 'longitude', 'google_maps_link'),
            'classes': ('collapse',)
        }),
        ('시스템', {
            'fields': ('last_synced_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['collect_region_businesses', 'collect_all_businesses', 'update_selected_businesses']

    def rank_badge(self, obj):
        """순위 배지"""
        if obj.rank_in_region == 1:
            return format_html('<span style="background: gold; padding: 2px 8px; border-radius: 4px; font-weight: bold;">🥇 1위</span>')
        elif obj.rank_in_region == 2:
            return format_html('<span style="background: silver; padding: 2px 8px; border-radius: 4px; font-weight: bold;">🥈 2위</span>')
        elif obj.rank_in_region == 3:
            return format_html('<span style="background: #cd7f32; padding: 2px 8px; border-radius: 4px; font-weight: bold; color: white;">🥉 3위</span>')
        else:
            return f"{obj.rank_in_region}위"
    rank_badge.short_description = '순위'

    # region_name은 이제 모델 필드이므로 메서드 불필요

    def category_name(self, obj):
        return f"{obj.category.icon} {obj.category.name}"
    category_name.short_description = '업종'

    def rating_display(self, obj):
        if obj.rating:
            return format_html('⭐ {}', obj.rating)
        return '-'
    rating_display.short_description = '평점'

    def website_display(self, obj):
        if obj.website_url:
            return format_html('<a href="{}" target="_blank">🌐</a>', obj.website_url)
        return '-'
    website_display.short_description = '웹사이트'

    def opening_hours_display(self, obj):
        if obj.opening_hours:
            # JSON 배열 형태로 저장된 영업시간을 파싱
            import json
            try:
                hours = json.loads(obj.opening_hours) if isinstance(obj.opening_hours, str) else obj.opening_hours
                if hours and len(hours) > 0:
                    return format_html('<span title="{}">{}</span>', '\n'.join(hours), hours[0][:20] + '...' if len(hours[0]) > 20 else hours[0])
            except:
                pass
        return '-'
    opening_hours_display.short_description = '영업시간'

    def google_maps_link(self, obj):
        if obj.google_maps_url:
            return format_html('<a href="{}" target="_blank">Google 지도에서 보기</a>', obj.google_maps_url)
        return '-'
    google_maps_link.short_description = 'Google 지도'

    def photo_preview(self, obj):
        """사진 미리보기"""
        if obj.custom_photo and obj.custom_photo.name:
            try:
                return format_html(
                    '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px;"><br>'
                    '<small style="color: #666;">S3 파일: {}</small>',
                    obj.custom_photo.url,
                    obj.custom_photo.name
                )
            except:
                pass

        if obj.photo_url:
            # photo_url에 API 키 추가
            from django.conf import settings
            photo_url_with_key = f"{obj.photo_url}&key={settings.GOOGLE_PLACES_API_KEY}" if '?' in obj.photo_url else obj.photo_url
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px;"><br>'
                '<small style="color: #666;">Google URL (백업용)</small>',
                photo_url_with_key
            )
        return format_html('<span style="color: #999;">사진 없음</span>')
    photo_preview.short_description = '사진 미리보기'

    def refresh_button(self, obj):
        if obj.pk:
            url = f'/admin/api/localbusiness/{obj.pk}/refresh/'
            return format_html(
                '<a class="button" href="{}" style="padding: 10px 15px; background: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block;">'
                '🔄 데이터 갱신하기</a>'
                '<p style="color: #666; margin-top: 10px; font-size: 12px;">Google Places API에서 최신 정보를 가져와 업데이트합니다.</p>',
                url
            )
        return '-'
    refresh_button.short_description = '데이터 갱신'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('collect-businesses/', self.admin_site.admin_view(self.collect_v2_view), name='collect_local_businesses'),
            path('validate-businesses/', self.admin_site.admin_view(self.validate_businesses_view), name='validate_local_businesses'),
            path('<path:object_id>/refresh/', self.admin_site.admin_view(self.refresh_business_view), name='refresh_local_business'),
        ]
        return custom_urls + urls

    def collect_region_businesses(self, request, queryset):
        """선택한 지역의 업체 수집"""
        # 선택된 업체들의 지역 추출
        regions = set(queryset.values_list('region_name', flat=True))

        if not regions:
            self.message_user(request, "지역을 선택해주세요.", messages.WARNING)
            return

        try:
            for region in regions:
                call_command('collect_local_businesses', region=region, limit=5)

            self.message_user(
                request,
                f"{len(regions)}개 지역의 업체 정보를 수집했습니다.",
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"오류 발생: {str(e)}", messages.ERROR)

    collect_region_businesses.short_description = "🔄 선택한 지역의 업체 정보 다시 수집"

    def collect_all_businesses(self, request, queryset):
        """전체 업체 수집 (주의: API 비용 발생)"""
        if not request.POST.get('confirm'):
            self.message_user(
                request,
                "전체 수집은 API 비용이 발생합니다. 다시 한 번 실행하여 확인해주세요.",
                messages.WARNING
            )
            return

        try:
            call_command('collect_local_businesses', limit=5)
            self.message_user(request, "전체 지역 업체 정보를 수집했습니다.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"오류 발생: {str(e)}", messages.ERROR)

    collect_all_businesses.short_description = "⚠️ 전체 지역 업체 수집 (API 비용 주의)"

    def update_selected_businesses(self, request, queryset):
        """선택한 업체 정보만 업데이트"""
        count = queryset.count()
        if count > 20:
            self.message_user(
                request,
                f"한 번에 20개까지만 업데이트할 수 있습니다. (선택: {count}개)",
                messages.WARNING
            )
            return

        # TODO: 선택한 업체들의 Place ID로 API 호출하여 업데이트
        self.message_user(request, "개별 업체 업데이트 기능은 준비 중입니다.", messages.INFO)

    update_selected_businesses.short_description = "🔄 선택한 업체 정보 업데이트"

    def collect_v2_view(self, request):
        """프론트엔드 방식 데이터 수집 페이지"""
        from django.template.response import TemplateResponse
        from django.conf import settings

        # collect_local_businesses.py의 TARGET_REGIONS와 동일한 리스트
        from .management.commands.collect_local_businesses import (
            SEOUL_DISTRICTS, GYEONGGI_CITIES, INCHEON_DISTRICTS,
            BUSAN_DISTRICTS, DAEGU_DISTRICTS, DAEJEON_DISTRICTS,
            GWANGJU_DISTRICTS, ULSAN_DISTRICTS,
            GANGWON_CITIES, CHUNGBUK_CITIES, CHUNGNAM_CITIES,
            JEONBUK_CITIES, JEONNAM_CITIES,
            GYEONGBUK_CITIES, GYEONGNAM_CITIES, JEJU_CITIES
        )

        # 서울 세부 그룹
        seoul_gangbuk = ['강북구', '노원구', '도봉구', '동대문구', '마포구',
                        '서대문구', '성동구', '성북구', '용산구', '은평구',
                        '종로구', '중구', '중랑구']
        seoul_gangnam = ['강남구', '강동구', '강서구', '관악구', '광진구',
                        '구로구', '금천구', '동작구', '서초구', '송파구',
                        '양천구', '영등포구']

        # 경기 세부 그룹 (3개로 세분화)
        gyeonggi_north = ['의정부시', '동두천시', '파주시', '고양시', '양주시',
                         '포천시', '연천군', '가평군', '남양주시', '구리시']
        gyeonggi_west = ['김포시', '부천시', '광명시', '시흥시', '안산시',
                        '안양시', '군포시', '의왕시', '과천시', '성남시']
        gyeonggi_east_south = ['하남시', '광주시', '여주시', '이천시', '용인시',
                              '수원시', '화성시', '오산시', '평택시', '안성시', '양평군']

        # 지역 그룹별로 정리
        region_groups = [
            {'name': '📍 서울 전체', 'regions': [f'서울특별시 {d}' for d in SEOUL_DISTRICTS]},
            {'name': '📍 서울 강북', 'regions': [f'서울특별시 {d}' for d in seoul_gangbuk]},
            {'name': '📍 서울 강남', 'regions': [f'서울특별시 {d}' for d in seoul_gangnam]},
            {'name': '📍 경기 전체', 'regions': [f'경기도 {c}' for c in GYEONGGI_CITIES]},
            {'name': '📍 경기 북부', 'regions': [f'경기도 {c}' for c in gyeonggi_north]},
            {'name': '📍 경기 서부', 'regions': [f'경기도 {c}' for c in gyeonggi_west]},
            {'name': '📍 경기 동남부', 'regions': [f'경기도 {c}' for c in gyeonggi_east_south]},
            {'name': '📍 인천광역시', 'regions': [f'인천광역시 {d}' for d in INCHEON_DISTRICTS]},
            {'name': '📍 부산광역시', 'regions': [f'부산광역시 {d}' for d in BUSAN_DISTRICTS]},
            {'name': '📍 대구광역시', 'regions': [f'대구광역시 {d}' for d in DAEGU_DISTRICTS]},
            {'name': '📍 대전광역시', 'regions': [f'대전광역시 {d}' for d in DAEJEON_DISTRICTS]},
            {'name': '📍 광주광역시', 'regions': [f'광주광역시 {d}' for d in GWANGJU_DISTRICTS]},
            {'name': '📍 울산광역시', 'regions': [f'울산광역시 {d}' for d in ULSAN_DISTRICTS]},
            {'name': '📍 세종특별자치시', 'regions': ['세종특별자치시']},
            {'name': '📍 강원특별자치도', 'regions': [f'강원특별자치도 {c}' for c in GANGWON_CITIES]},
            {'name': '📍 충청북도', 'regions': [f'충청북도 {c}' for c in CHUNGBUK_CITIES]},
            {'name': '📍 충청남도', 'regions': [f'충청남도 {c}' for c in CHUNGNAM_CITIES]},
            {'name': '📍 전북특별자치도', 'regions': [f'전북특별자치도 {c}' for c in JEONBUK_CITIES]},
            {'name': '📍 전라남도', 'regions': [f'전라남도 {c}' for c in JEONNAM_CITIES]},
            {'name': '📍 경상북도', 'regions': [f'경상북도 {c}' for c in GYEONGBUK_CITIES]},
            {'name': '📍 경상남도', 'regions': [f'경상남도 {c}' for c in GYEONGNAM_CITIES]},
            {'name': '📍 제주특별자치도', 'regions': [f'제주특별자치도 {c}' for c in JEJU_CITIES]},
        ]

        # 카테고리 목록
        categories = LocalBusinessCategory.objects.filter(is_active=True).order_by('order_index')

        # API 키 가져오기 (환경변수에서만)
        api_key = settings.GOOGLE_PLACES_API_KEY

        context = {
            **self.admin_site.each_context(request),
            'title': '지역 업체 정보 수집 (Google API)',
            'region_groups': region_groups,
            'categories': categories,
            'google_api_key': api_key,
            'opts': self.model._meta,
        }

        return TemplateResponse(
            request,
            'admin/local_business_collect_v2.html',
            context
        )

    def refresh_business_view(self, request, object_id):
        """개별 업체 데이터 갱신"""
        try:
            # 업체 조회
            business = LocalBusiness.objects.get(pk=object_id)

            # Google Places API 호출 (views_local_business.py의 로직 재사용)
            from .views_local_business import LocalBusinessViewSet
            viewset = LocalBusinessViewSet()

            # Google Places API에서 최신 데이터 가져오기
            import requests
            from django.conf import settings

            url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.nationalPhoneNumber,places.googleMapsUri,places.photos,places.editorialSummary,places.reviews"
            }

            # 검색 쿼리: 업체명 + 주소로 정확도 높이기
            search_query = f"{business.name} {business.address}"

            body = {
                "textQuery": search_query,
                "languageCode": "ko",
                "maxResultCount": 1
            }

            response = requests.post(url, json=body, headers=headers, timeout=10)

            if response.status_code != 200:
                self.message_user(request, f"Google API 오류: {response.status_code}", messages.ERROR)
                return redirect(f'/admin/api/localbusiness/{object_id}/change/')

            data = response.json()
            places = data.get('places', [])

            if not places:
                self.message_user(request, "Google Places에서 업체를 찾을 수 없습니다.", messages.WARNING)
                return redirect(f'/admin/api/localbusiness/{object_id}/change/')

            place = places[0]

            # 기본 정보 업데이트
            business.name = place.get('displayName', {}).get('text', business.name)
            business.address = place.get('formattedAddress', business.address)
            business.phone_number = place.get('nationalPhoneNumber', business.phone_number)
            business.rating = place.get('rating')
            business.review_count = place.get('userRatingCount', 0)
            business.google_maps_url = place.get('googleMapsUri', business.google_maps_url)

            # 위치 정보 업데이트
            location = place.get('location', {})
            if location:
                business.latitude = str(location.get('latitude', business.latitude))
                business.longitude = str(location.get('longitude', business.longitude))

            # popularity_score 재계산
            rating = business.rating or 0
            review_count = business.review_count or 0
            C = 10
            m = 4.0
            import math
            bayesian_avg = (C * m + review_count * rating) / (C + review_count)
            log_scale = math.log10(review_count + 1)
            business.popularity_score = bayesian_avg * log_scale

            # AI 요약 생성 (리뷰가 있는 경우만)
            reviews = place.get('reviews', [])
            if reviews:
                from .utils_ai_summary import generate_business_summary

                reviews_data = [
                    {
                        'text': review.get('text', {}).get('text', ''),
                        'rating': review.get('rating', 0)
                    }
                    for review in reviews[:5]
                ]

                summary, error = generate_business_summary(reviews_data, business.name)
                if summary:
                    business.editorial_summary = summary

            # 이미지 업데이트 (이미지가 없는 경우만)
            if not business.custom_photo:
                photos = place.get('photos', [])
                if photos:
                    photo_name = photos[0].get('name')
                    if photo_name:
                        photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?key={settings.GOOGLE_PLACES_API_KEY}&maxHeightPx=800&maxWidthPx=800"

                        # 이미지 다운로드 및 저장
                        photo_result = viewset.download_and_save_photo(
                            photo_url,
                            business.name,
                            business.google_place_id
                        )

                        if photo_result:
                            content_file, filename = photo_result
                            business.custom_photo.save(filename, content_file, save=False)

            # 마지막 동기화 시간 업데이트
            from django.utils import timezone
            business.last_synced_at = timezone.now()

            # 저장
            business.save()

            self.message_user(
                request,
                f"✅ {business.name} 데이터가 갱신되었습니다. (평점: {business.rating}, 리뷰: {business.review_count}개)",
                messages.SUCCESS
            )

        except LocalBusiness.DoesNotExist:
            self.message_user(request, "업체를 찾을 수 없습니다.", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"오류 발생: {str(e)}", messages.ERROR)

        return redirect(f'/admin/api/localbusiness/{object_id}/change/')

    def validate_businesses_view(self, request):
        """OpenAI로 잘못 분류된 업체 검증 및 삭제"""
        from django.template.response import TemplateResponse
        from django.http import JsonResponse
        from django.conf import settings
        import openai

        if request.method == 'POST':
            # AJAX 요청 처리
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            if not is_ajax:
                self.message_user(request, "잘못된 요청입니다.", messages.ERROR)
                return redirect('..')

            action = request.POST.get('action')

            # 검증 시작
            if action == 'validate':
                validation_mode = request.POST.get('validation_mode', 'category')
                category_id = request.POST.get('category')
                regions = request.POST.getlist('regions[]')

                try:
                    # 필터링
                    businesses = LocalBusiness.objects.all()
                    if category_id:
                        businesses = businesses.filter(category_id=category_id)
                    if regions:
                        businesses = businesses.filter(region_name__in=regions)

                    # 웹사이트 검증 모드인 경우 website_url이 있는 업체만
                    if validation_mode == 'website':
                        businesses = businesses.exclude(website_url__isnull=True).exclude(website_url='')

                    # 중복 검증 모드인 경우 중복 이름이 있는 업체만
                    elif validation_mode == 'duplicate':
                        from django.db.models import Count
                        # 중복된 이름 찾기
                        duplicate_names = LocalBusiness.objects.values('name').annotate(
                            count=Count('id')
                        ).filter(count__gt=1).values_list('name', flat=True)

                        businesses = businesses.filter(name__in=duplicate_names).order_by('name')

                    # OpenAI 검증
                    openai.api_key = settings.OPENAI_API_KEY
                    invalid_businesses = []

                    for business in businesses[:50]:  # 한 번에 최대 50개
                        if validation_mode == 'duplicate':
                            # 중복 업체명 검증 모드
                            business_name = business.name
                            business_address = business.address
                            category_name = business.category.name

                            # 같은 이름의 다른 업체들 찾기
                            duplicates = LocalBusiness.objects.filter(name=business_name).exclude(id=business.id)
                            duplicate_info = "\n".join([
                                f"- {dup.name} ({dup.category.name}) - {dup.address}"
                                for dup in duplicates[:5]
                            ])

                            # OpenAI에 중복 검증 요청
                            prompt = f"""
다음 업체가 실제로 존재하는 업체인지, 아니면 중복 등록인지 판단해주세요.

현재 업체:
- 이름: {business_name}
- 업종: {category_name}
- 주소: {business_address}

같은 이름의 다른 업체들:
{duplicate_info}

다음 경우 "DUPLICATE"로 답변하세요:
1. 주소가 거의 동일한데 중복 등록된 경우
2. 프랜차이즈가 아닌데 같은 이름이 여러 지역에 있는 경우 (의심스러운 경우)
3. 명백히 잘못 등록된 경우

다음 경우 "VALID"로 답변하세요:
1. 프랜차이즈 업체인 경우 (스타벅스, 맥도날드 등)
2. 같은 이름이지만 주소가 명확히 다른 별개의 업체인 경우
3. 판단이 애매한 경우

"VALID" 또는 "DUPLICATE"로만 답변하세요.
"""

                            response = openai.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "당신은 중복 업체 검증 전문가입니다. VALID 또는 DUPLICATE로만 답변하세요."},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0,
                                max_tokens=10
                            )

                            answer = response.choices[0].message.content.strip().upper()

                            if 'DUPLICATE' in answer:
                                invalid_businesses.append({
                                    'id': business.id,
                                    'name': business.name,
                                    'category': business.category.name,
                                    'region': business.region_name,
                                    'address': business.address,
                                    'issue': '중복 의심'
                                })

                        elif validation_mode == 'website':
                            # 웹사이트 검증 모드
                            business_name = business.name
                            website_url = business.website_url

                            # OpenAI에 웹사이트 유효성 검증 요청
                            prompt = f"""
다음 업체의 웹사이트가 유효한지 판단해주세요.

업체명: {business_name}
웹사이트: {website_url}

다음 중 하나라도 해당되면 "INVALID"로 답변하세요:
1. URL이 명백히 잘못되었거나 형식이 이상한 경우
2. URL이 업체와 전혀 관련 없어 보이는 경우
3. URL이 만료되었을 가능성이 높은 경우 (예: 오래된 블로그, 개인 페이지 등)
4. URL이 공공기관, 포털사이트, 검색엔진 등인 경우

웹사이트가 정상적이고 업체와 관련이 있어 보이면 "VALID", 아니면 "INVALID"로만 답변하세요.
판단이 애매하면 "VALID"로 답변하세요.

예시:
- "김앤장 법률사무소" + "https://www.kimchang.com" → VALID
- "세무법인 나무" + "https://blog.naver.com/user123" → INVALID (개인 블로그)
- "건축사사무소" + "https://www.google.com" → INVALID (관련 없음)
"""

                            response = openai.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "당신은 웹사이트 유효성 검증 전문가입니다. VALID 또는 INVALID로만 답변하세요."},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0,
                                max_tokens=10
                            )

                            answer = response.choices[0].message.content.strip().upper()

                            if 'INVALID' in answer:
                                invalid_businesses.append({
                                    'id': business.id,
                                    'name': business.name,
                                    'category': business.category.name,
                                    'region': business.region_name,
                                    'address': business.address,
                                    'website_url': website_url,
                                    'issue': '유효하지 않은 웹사이트'
                                })
                        else:
                            # 업종 검증 모드 (기존 로직)
                            category_name = business.category.name
                            business_name = business.name

                            # OpenAI에 검증 요청
                            prompt = f"""
업체명과 업종을 보고 명백히 일치하지 않으면 무조건 "NO"로 답변하세요.

업체명: {business_name}
업종: {category_name}

**핵심 원칙: 업체명에서 해당 업종을 명확히 유추할 수 있어야 YES**

업체명을 보고 상식적으로 판단했을 때:
- 업체명이 해당 업종과 전혀 관련 없어 보이면 → NO
- 업체명이 다른 업종을 암시하면 → NO
- 업체명만으로 업종을 알 수 없고 애매하면 → NO
- 업체명이 해당 업종과 명확히 연결되면 → YES

**반드시 NO로 답변해야 하는 경우:**

1. **공공기관**: 세무서, 세관, 구청, 시청, 동주민센터, 경찰서, 소방서, 우체국 등
2. **업종 명백히 불일치**:
   - "치킨", "카페", "음식점", "편의점", "약국" 등이 들어간 업체명
   - 업체명에 전혀 다른 업종이 명시된 경우
3. **세무사/회계사 업종**: "세무서" 포함 시 (공공기관)
4. **청소 전문**: "세탁", "빨래방", "드라이클리닝", "코인워시" 등 세탁업 관련
5. **이사 전문**: "창고", "보관", "스토리지", "물류", "컨테이너" 등 물류/보관업 관련

**예시 (엄격 적용):**

✅ YES (명확히 일치):
- "김앤장 법률사무소" + 업종 "변호사"
- "깨끗한 청소 서비스" + 업종 "청소 전문"
- "하나로 이삿짐센터" + 업종 "이사 전문"
- "세무법인 나무" + 업종 "세무사"
- "현대 자동차 정비" + 업종 "정비소"

❌ NO (불일치/의심):
- "스타벅스" + 업종 "변호사" → 완전히 다른 업종
- "하남시청" + 업종 "회계사" → 공공기관
- "강남세무서" + 업종 "세무사" → 공공기관
- "다올창고" + 업종 "이사 전문" → 창고업
- "크린세탁소" + 업종 "청소 전문" → 세탁업
- "24시 편의점" + 업종 "휴대폰 대리점" → 전혀 다름
- "맥도날드" + 업종 "인테리어" → 전혀 다름
- "ABC 주식회사" + 업종 "변호사" → 업종 불명확

의심스럽거나 업체명만으로 해당 업종인지 확신할 수 없으면 무조건 "NO"로 답변하세요.
"""

                            response = openai.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "당신은 업체 분류 검증 전문가입니다. YES 또는 NO로만 답변하세요."},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0,
                                max_tokens=10
                            )

                            answer = response.choices[0].message.content.strip().upper()

                            if 'NO' in answer:
                                invalid_businesses.append({
                                    'id': business.id,
                                    'name': business.name,
                                    'category': category_name,
                                    'region': business.region_name,
                                    'address': business.address,
                                })

                    return JsonResponse({
                        'status': 'success',
                        'invalid_count': len(invalid_businesses),
                        'invalid_businesses': invalid_businesses,
                        'total_checked': businesses.count()
                    })

                except Exception as e:
                    return JsonResponse({
                        'status': 'error',
                        'message': str(e)
                    }, status=500)

            # 삭제 실행
            elif action == 'delete':
                business_ids = request.POST.getlist('business_ids[]')
                validation_mode = request.POST.get('validation_mode', 'category')

                try:
                    if validation_mode == 'website':
                        # 웹사이트 검증 모드: website_url 필드만 비우기
                        updated_count = LocalBusiness.objects.filter(
                            id__in=business_ids
                        ).update(website_url=None)

                        return JsonResponse({
                            'status': 'success',
                            'deleted_count': updated_count,
                            'mode': 'website'
                        })
                    else:
                        # 업종/중복 검증 모드: 업체 자체를 삭제
                        deleted_count = LocalBusiness.objects.filter(id__in=business_ids).delete()[0]

                        return JsonResponse({
                            'status': 'success',
                            'deleted_count': deleted_count,
                            'mode': validation_mode
                        })

                except Exception as e:
                    return JsonResponse({
                        'status': 'error',
                        'message': str(e)
                    }, status=500)

        # GET 요청: 검증 페이지 표시 (데이터 수집 페이지와 동일한 로직)
        from .management.commands.collect_local_businesses import (
            SEOUL_DISTRICTS, GYEONGGI_CITIES, INCHEON_DISTRICTS,
            BUSAN_DISTRICTS, DAEGU_DISTRICTS, DAEJEON_DISTRICTS,
            GWANGJU_DISTRICTS, ULSAN_DISTRICTS,
            GANGWON_CITIES, CHUNGBUK_CITIES, CHUNGNAM_CITIES,
            JEONBUK_CITIES, JEONNAM_CITIES,
            GYEONGBUK_CITIES, GYEONGNAM_CITIES, JEJU_CITIES
        )

        # 서울 세부 그룹
        seoul_gangbuk = ['강북구', '노원구', '도봉구', '동대문구', '마포구',
                        '서대문구', '성동구', '성북구', '용산구', '은평구',
                        '종로구', '중구', '중랑구']
        seoul_gangnam = ['강남구', '강동구', '강서구', '관악구', '광진구',
                        '구로구', '금천구', '동작구', '서초구', '송파구',
                        '양천구', '영등포구']

        # 경기 세부 그룹 (3개로 세분화)
        gyeonggi_north = ['의정부시', '동두천시', '파주시', '고양시', '양주시',
                         '포천시', '연천군', '가평군', '남양주시', '구리시']
        gyeonggi_west = ['김포시', '부천시', '광명시', '시흥시', '안산시',
                        '안양시', '군포시', '의왕시', '과천시', '성남시']
        gyeonggi_east_south = ['하남시', '광주시', '여주시', '이천시', '용인시',
                              '수원시', '화성시', '오산시', '평택시', '안성시', '양평군']

        # 지역 그룹별로 정리
        region_groups = [
            {'name': '📍 서울 전체', 'regions': [f'서울특별시 {d}' for d in SEOUL_DISTRICTS]},
            {'name': '📍 서울 강북', 'regions': [f'서울특별시 {d}' for d in seoul_gangbuk]},
            {'name': '📍 서울 강남', 'regions': [f'서울특별시 {d}' for d in seoul_gangnam]},
            {'name': '📍 경기 전체', 'regions': [f'경기도 {c}' for c in GYEONGGI_CITIES]},
            {'name': '📍 경기 북부', 'regions': [f'경기도 {c}' for c in gyeonggi_north]},
            {'name': '📍 경기 서부', 'regions': [f'경기도 {c}' for c in gyeonggi_west]},
            {'name': '📍 경기 동남부', 'regions': [f'경기도 {c}' for c in gyeonggi_east_south]},
            {'name': '📍 인천광역시', 'regions': [f'인천광역시 {d}' for d in INCHEON_DISTRICTS]},
            {'name': '📍 부산광역시', 'regions': [f'부산광역시 {d}' for d in BUSAN_DISTRICTS]},
            {'name': '📍 대구광역시', 'regions': [f'대구광역시 {d}' for d in DAEGU_DISTRICTS]},
            {'name': '📍 대전광역시', 'regions': [f'대전광역시 {d}' for d in DAEJEON_DISTRICTS]},
            {'name': '📍 광주광역시', 'regions': [f'광주광역시 {d}' for d in GWANGJU_DISTRICTS]},
            {'name': '📍 울산광역시', 'regions': [f'울산광역시 {d}' for d in ULSAN_DISTRICTS]},
            {'name': '📍 세종특별자치시', 'regions': ['세종특별자치시']},
            {'name': '📍 강원특별자치도', 'regions': [f'강원특별자치도 {c}' for c in GANGWON_CITIES]},
            {'name': '📍 충청북도', 'regions': [f'충청북도 {c}' for c in CHUNGBUK_CITIES]},
            {'name': '📍 충청남도', 'regions': [f'충청남도 {c}' for c in CHUNGNAM_CITIES]},
            {'name': '📍 전북특별자치도', 'regions': [f'전북특별자치도 {c}' for c in JEONBUK_CITIES]},
            {'name': '📍 전라남도', 'regions': [f'전라남도 {c}' for c in JEONNAM_CITIES]},
            {'name': '📍 경상북도', 'regions': [f'경상북도 {c}' for c in GYEONGBUK_CITIES]},
            {'name': '📍 경상남도', 'regions': [f'경상남도 {c}' for c in GYEONGNAM_CITIES]},
            {'name': '📍 제주특별자치도', 'regions': [f'제주특별자치도 {c}' for c in JEJU_CITIES]},
        ]

        categories = LocalBusinessCategory.objects.filter(is_active=True).order_by('order_index')

        context = {
            **self.admin_site.each_context(request),
            'title': '업체 데이터 검증 (OpenAI)',
            'region_groups': region_groups,
            'categories': categories,
            'opts': self.model._meta,
        }

        return TemplateResponse(
            request,
            'admin/local_business_validate.html',
            context
        )

    def changelist_view(self, request, extra_context=None):
        """목록 페이지에 커스텀 버튼 추가"""
        extra_context = extra_context or {}
        extra_context['show_collect_button'] = True
        extra_context['show_validate_button'] = True
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(LocalBusinessLink)
class LocalBusinessLinkAdmin(admin.ModelAdmin):
    list_display = ['business', 'link_type', 'title', 'source', 'published_at', 'created_at']
    list_filter = ['link_type', 'source']
    search_fields = ['business__name', 'title', 'url']
    ordering = ['-published_at', '-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business')


@admin.register(LocalBusinessView)
class LocalBusinessViewAdmin(admin.ModelAdmin):
    list_display = ['business', 'user', 'ip_address', 'viewed_at']
    list_filter = ['viewed_at']
    search_fields = ['business__name', 'user__email', 'ip_address']
    ordering = ['-viewed_at']
    readonly_fields = ['business', 'user', 'ip_address', 'viewed_at']

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business', 'user')
