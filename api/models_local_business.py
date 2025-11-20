"""
지역 전문업체 정보 모델
Google Places API 기반 지역별 업체 정보 제공
"""
from django.db import models
from django.contrib.auth import get_user_model
from api.models_region import Region

User = get_user_model()


class LocalBusinessCategory(models.Model):
    """전문 업종 카테고리"""

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='업종명'
    )

    name_en = models.CharField(
        max_length=50,
        verbose_name='영문명',
        help_text='Google Places 검색용'
    )

    icon = models.CharField(
        max_length=50,
        default='🏢',
        verbose_name='아이콘'
    )

    google_place_type = models.CharField(
        max_length=100,
        verbose_name='Google Place Type',
        help_text='예: lawyer, accounting, real_estate_agency'
    )

    description = models.TextField(
        blank=True,
        verbose_name='설명'
    )

    order_index = models.IntegerField(
        default=0,
        verbose_name='정렬순서'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'local_business_category'
        verbose_name = '지역업체 카테고리'
        verbose_name_plural = '지역업체 카테고리'
        ordering = ['order_index', 'name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class LocalBusiness(models.Model):
    """지역 전문업체 정보"""

    category = models.ForeignKey(
        LocalBusinessCategory,
        on_delete=models.CASCADE,
        related_name='businesses',
        verbose_name='업종'
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='local_businesses',
        verbose_name='지역'
    )

    # 기본 정보
    name = models.CharField(
        max_length=200,
        verbose_name='업체명'
    )

    address = models.CharField(
        max_length=300,
        verbose_name='주소'
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='전화번호'
    )

    # Google Places 정보
    google_place_id = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Google Place ID'
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        verbose_name='위도'
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        verbose_name='경도'
    )

    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='평점'
    )

    review_count = models.IntegerField(
        default=0,
        verbose_name='리뷰 수'
    )

    google_maps_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='구글 지도 URL'
    )

    photo_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='대표 사진 URL'
    )

    # 랭킹 정보
    popularity_score = models.FloatField(
        default=0,
        verbose_name='인기도 점수',
        help_text='베이지안 평균 기반'
    )

    rank_in_region = models.IntegerField(
        default=999,
        verbose_name='지역 내 순위',
        help_text='해당 지역+카테고리 내 순위 (1~5)'
    )

    # 메타 정보
    is_verified = models.BooleanField(
        default=False,
        verbose_name='업체 인증',
        help_text='업체에서 직접 인증한 경우'
    )

    is_new = models.BooleanField(
        default=False,
        verbose_name='신규 업체',
        help_text='리뷰 10개 이하 또는 최근 등록'
    )

    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name='조회수'
    )

    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='마지막 동기화 시간'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'local_business'
        verbose_name = '지역 업체'
        verbose_name_plural = '지역 업체'
        ordering = ['region', 'category', 'rank_in_region']
        indexes = [
            models.Index(fields=['region', 'category', 'rank_in_region']),
            models.Index(fields=['google_place_id']),
            models.Index(fields=['is_new', '-created_at']),
            models.Index(fields=['-popularity_score']),
        ]

    def __str__(self):
        return f"{self.name} ({self.region.name})"


class LocalBusinessLink(models.Model):
    """업체 관련 외부 링크 (뉴스/블로그/리뷰)"""

    LINK_TYPE_CHOICES = [
        ('news', '뉴스'),
        ('blog', '블로그'),
        ('review', '리뷰'),
        ('community', '커뮤니티'),
    ]

    business = models.ForeignKey(
        LocalBusiness,
        on_delete=models.CASCADE,
        related_name='links',
        verbose_name='업체'
    )

    link_type = models.CharField(
        max_length=20,
        choices=LINK_TYPE_CHOICES,
        verbose_name='링크 유형'
    )

    title = models.CharField(
        max_length=300,
        verbose_name='제목'
    )

    url = models.URLField(
        max_length=1000,
        unique=True,
        verbose_name='URL'
    )

    source = models.CharField(
        max_length=50,
        verbose_name='출처',
        help_text='네이버, 구글, 다음 등'
    )

    published_at = models.DateField(
        null=True,
        blank=True,
        verbose_name='작성일'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'local_business_link'
        verbose_name = '업체 외부 링크'
        verbose_name_plural = '업체 외부 링크'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['business', '-published_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.source})"


class LocalBusinessView(models.Model):
    """업체 조회 기록 (통계용)"""

    business = models.ForeignKey(
        LocalBusiness,
        on_delete=models.CASCADE,
        related_name='view_logs',
        verbose_name='업체'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='사용자'
    )

    ip_address = models.GenericIPAddressField(
        verbose_name='IP 주소'
    )

    viewed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='조회 시간'
    )

    class Meta:
        db_table = 'local_business_view'
        verbose_name = '업체 조회 기록'
        verbose_name_plural = '업체 조회 기록'
        indexes = [
            models.Index(fields=['business', '-viewed_at']),
            models.Index(fields=['-viewed_at']),
        ]

    def __str__(self):
        return f"{self.business.name} - {self.viewed_at}"
