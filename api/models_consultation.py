"""
무료 상담 신청 관련 모델
"""
from django.db import models
from django.conf import settings


class ConsultationType(models.Model):
    """업종별 상담 유형"""
    category = models.ForeignKey(
        'LocalBusinessCategory',
        on_delete=models.CASCADE,
        related_name='consultation_types',
        verbose_name='업종'
    )
    name = models.CharField(max_length=100, verbose_name='상담 유형명')
    description = models.TextField(blank=True, verbose_name='설명')
    icon = models.CharField(max_length=10, default='💬', verbose_name='아이콘')
    order_index = models.IntegerField(default=0, verbose_name='정렬순서')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_consultation_type'
        ordering = ['category', 'order_index']
        verbose_name = '상담 유형'
        verbose_name_plural = '상담 유형'

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class ConsultationRequest(models.Model):
    """무료 상담 신청"""
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('contacted', '연락완료'),
        ('completed', '상담완료'),
        ('cancelled', '취소'),
    ]

    # 신청자 정보 (비회원 가능)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='consultation_requests',
        verbose_name='회원'
    )
    name = models.CharField(max_length=50, verbose_name='이름')
    phone = models.CharField(max_length=20, verbose_name='연락처')
    email = models.EmailField(blank=True, verbose_name='이메일')

    # 상담 정보
    category = models.ForeignKey(
        'LocalBusinessCategory',
        on_delete=models.CASCADE,
        related_name='consultation_requests',
        verbose_name='업종'
    )
    consultation_type = models.ForeignKey(
        ConsultationType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='requests',
        verbose_name='상담 유형'
    )
    region = models.CharField(max_length=50, verbose_name='희망 지역')

    # 상담 내용
    content = models.TextField(verbose_name='상담 내용')
    ai_summary = models.TextField(blank=True, verbose_name='AI 정리 내용')
    ai_recommended_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name='AI 추천 상담 유형'
    )

    # 상태 관리
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='상태'
    )
    admin_note = models.TextField(blank=True, verbose_name='관리자 메모')

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='신청일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    contacted_at = models.DateTimeField(null=True, blank=True, verbose_name='연락일시')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='완료일시')

    class Meta:
        db_table = 'api_consultation_request'
        ordering = ['-created_at']
        verbose_name = '상담 신청'
        verbose_name_plural = '상담 신청'

    def __str__(self):
        return f"[{self.get_status_display()}] {self.name} - {self.category.name} ({self.created_at.strftime('%Y-%m-%d')})"
