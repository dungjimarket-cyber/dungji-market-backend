"""
전문가 프로필 및 상담 매칭 모델
"""
from django.db import models
from django.conf import settings


class ExpertProfile(models.Model):
    """
    전문가 회원 프로필 - User와 1:1 연결
    """
    STATUS_CHOICES = [
        ('pending', '승인대기'),
        ('verified', '승인됨'),
        ('rejected', '거절됨'),
        ('suspended', '정지'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expert_profile',
        verbose_name='사용자'
    )
    category = models.ForeignKey(
        'LocalBusinessCategory',
        on_delete=models.CASCADE,
        related_name='experts',
        verbose_name='업종'
    )

    # 기본 정보
    representative_name = models.CharField(max_length=100, verbose_name='대표자명')

    # 사업자 정보 (선택)
    is_business = models.BooleanField(default=False, verbose_name='사업자 여부')
    business_name = models.CharField(max_length=255, blank=True, verbose_name='상호명')
    business_number = models.CharField(max_length=20, blank=True, verbose_name='사업자등록번호')
    business_license_image = models.URLField(blank=True, verbose_name='사업자등록증 이미지')

    # 자격 정보 (선택)
    license_number = models.CharField(max_length=50, blank=True, verbose_name='자격번호')
    license_image = models.URLField(blank=True, verbose_name='자격증 이미지')

    # 활동 지역 (다중 선택, 필수)
    regions = models.ManyToManyField(
        'Region',
        related_name='expert_profiles',
        verbose_name='활동 지역'
    )

    # 연락처
    contact_phone = models.CharField(max_length=20, verbose_name='연락처')
    contact_email = models.EmailField(blank=True, verbose_name='이메일')

    # 프로필
    profile_image = models.URLField(blank=True, verbose_name='프로필 이미지')
    tagline = models.CharField(max_length=100, blank=True, verbose_name='한줄 소개')
    introduction = models.TextField(blank=True, verbose_name='상세 소개')

    # 상태 (즉시 활성화 - 관리자 승인 불필요)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='verified',
        verbose_name='상태'
    )
    is_receiving_requests = models.BooleanField(
        default=True,
        verbose_name='상담 요청 수신 여부'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        verbose_name = '전문가 프로필'
        verbose_name_plural = '전문가 프로필 관리'
        ordering = ['-created_at']

    def __str__(self):
        business_info = f" ({self.business_name})" if self.business_name else ""
        return f"{self.representative_name}{business_info} - {self.category.name}"


class ConsultationMatch(models.Model):
    """
    상담 요청 ↔ 전문가 매칭
    """
    STATUS_CHOICES = [
        ('pending', '대기중'),       # 전문가에게 새 요청으로 표시
        ('replied', '답변함'),       # 전문가가 답변 완료
        ('connected', '연결됨'),     # 고객이 연결 승인 → 연락처 공개
        ('completed', '완료'),       # 상담 완료
    ]

    consultation = models.ForeignKey(
        'ConsultationRequest',
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name='상담 요청'
    )
    expert = models.ForeignKey(
        ExpertProfile,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name='전문가'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='상태'
    )

    # 전문가 답변 시 입력 (선택)
    expert_message = models.TextField(blank=True, verbose_name='전문가 메시지')
    available_time = models.CharField(max_length=200, blank=True, verbose_name='상담 가능 시간')

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name='답변 시점')
    connected_at = models.DateTimeField(null=True, blank=True, verbose_name='연결 시점')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='완료 시점')

    class Meta:
        verbose_name = '상담 매칭'
        verbose_name_plural = '상담 매칭 관리'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['consultation', 'expert'],
                name='unique_consultation_expert_match'
            )
        ]

    def __str__(self):
        return f"{self.consultation} - {self.expert.representative_name} ({self.get_status_display()})"
