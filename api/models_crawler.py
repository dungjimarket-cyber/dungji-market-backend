"""
크롤링 결과 저장 모델
"""

from django.db import models
from django.conf import settings
import json


class CrawlSession(models.Model):
    """크롤링 세션 (실행 기록)"""

    STATUS_CHOICES = [
        ('pending', '대기'),
        ('running', '실행 중'),
        ('completed', '완료'),
        ('failed', '실패'),
    ]

    CRAWLER_TYPE_CHOICES = [
        ('all', '전체'),
        ('lawyer', '변호사'),
        ('judicial_scrivener', '법무사'),
        ('tax_accountant', '세무사'),
        ('accountant', '공인회계사'),
        ('realtor', '공인중개사'),
        ('local_business', 'DB 업체 웹사이트'),
    ]

    crawler_type = models.CharField(
        max_length=30,
        choices=CRAWLER_TYPE_CHOICES,
        default='all',
        verbose_name='크롤러 유형'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='상태'
    )
    regions = models.JSONField(
        default=list,
        blank=True,
        verbose_name='검색 지역'
    )
    max_pages = models.IntegerField(
        default=5,
        verbose_name='최대 페이지'
    )

    # 결과
    total_count = models.IntegerField(default=0, verbose_name='총 수집')
    email_count = models.IntegerField(default=0, verbose_name='이메일 수')
    result_file = models.FileField(
        upload_to='crawler_results/',
        null=True,
        blank=True,
        verbose_name='결과 파일'
    )
    error_message = models.TextField(blank=True, verbose_name='오류 메시지')

    # 메타
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='실행자'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='완료일')

    class Meta:
        verbose_name = '크롤링 세션'
        verbose_name_plural = '크롤링 세션'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_crawler_type_display()} - {self.get_status_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class CrawlResult(models.Model):
    """크롤링 결과 (개별 데이터)"""

    CATEGORY_CHOICES = [
        ('lawyer', '변호사'),
        ('judicial_scrivener', '법무사'),
        ('tax_accountant', '세무사'),
        ('accountant', '공인회계사'),
        ('realtor', '공인중개사'),
        ('local_business', 'DB 업체'),
    ]

    session = models.ForeignKey(
        CrawlSession,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name='세션'
    )
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        verbose_name='업종'
    )

    # 기본 정보
    name = models.CharField(max_length=100, blank=True, verbose_name='성명/대표자')
    office_name = models.CharField(max_length=200, blank=True, verbose_name='사무소명')
    affiliation = models.CharField(max_length=200, blank=True, verbose_name='소속')
    address = models.TextField(blank=True, verbose_name='주소')
    region = models.CharField(max_length=50, blank=True, verbose_name='지역')

    # 연락처
    phone = models.CharField(max_length=20, blank=True, verbose_name='전화번호')
    email = models.EmailField(blank=True, verbose_name='이메일')
    website = models.URLField(blank=True, verbose_name='홈페이지')

    # 추가 정보
    specialty = models.CharField(max_length=200, blank=True, verbose_name='전문분야')
    extra_data = models.JSONField(default=dict, blank=True, verbose_name='추가 데이터')

    # 이메일 발송 상태
    email_sent = models.BooleanField(default=False, verbose_name='이메일 발송')
    email_sent_at = models.DateTimeField(null=True, blank=True, verbose_name='발송일')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='수집일')

    class Meta:
        verbose_name = '크롤링 결과'
        verbose_name_plural = '크롤링 결과'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['email']),
            models.Index(fields=['region']),
            models.Index(fields=['email_sent']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - {self.name or self.office_name}"


class EmailCampaign(models.Model):
    """이메일 캠페인"""

    STATUS_CHOICES = [
        ('draft', '작성 중'),
        ('scheduled', '예약'),
        ('sending', '발송 중'),
        ('completed', '완료'),
        ('failed', '실패'),
    ]

    name = models.CharField(max_length=200, verbose_name='캠페인명')
    subject = models.CharField(max_length=200, verbose_name='이메일 제목')
    content = models.TextField(verbose_name='이메일 내용')
    html_content = models.TextField(blank=True, verbose_name='HTML 내용')

    # 대상
    target_categories = models.JSONField(
        default=list,
        verbose_name='대상 업종'
    )
    target_regions = models.JSONField(
        default=list,
        verbose_name='대상 지역'
    )
    target_results = models.ManyToManyField(
        CrawlResult,
        blank=True,
        related_name='campaigns',
        verbose_name='발송 대상'
    )

    # 발송 정보
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='상태'
    )
    total_count = models.IntegerField(default=0, verbose_name='총 발송')
    success_count = models.IntegerField(default=0, verbose_name='성공')
    fail_count = models.IntegerField(default=0, verbose_name='실패')

    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='예약 시간')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='시작 시간')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='완료 시간')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='작성자'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        verbose_name = '이메일 캠페인'
        verbose_name_plural = '이메일 캠페인'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
