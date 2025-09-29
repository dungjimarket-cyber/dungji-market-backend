"""
SMS 알림 시스템 모델
실제 문자 발송을 관리하는 독립적인 시스템
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class SMSNotification(models.Model):
    """SMS 알림 로그 및 관리"""

    # SMS 타입 정의
    SMS_TYPE_CHOICES = [
        # 중고거래
        ('price_offer_received', '가격제안 도착'),
        ('price_offer_accepted', '가격제안 수락'),

        # 공구 - 구매자 프로세스
        ('buyer_selection_request', '구매자 최종선택 요청'),
        ('buyer_selection_complete', '구매자 최종선택 완료'),

        # 공구 - 판매자 프로세스
        ('seller_decision_request', '판매자 최종결정 요청'),
        ('seller_decision_complete', '판매자 최종결정 완료'),

        # 기타 (추후 확장용)
        ('trade_complete', '거래 완료'),
        ('groupbuy_cancelled', '공구 취소'),
    ]

    STATUS_CHOICES = [
        ('pending', '발송 대기'),
        ('sent', '발송 완료'),
        ('failed', '발송 실패'),
        ('cancelled', '발송 취소'),
    ]

    # 기본 정보
    sms_type = models.CharField(
        max_length=30,
        choices=SMS_TYPE_CHOICES,
        verbose_name='SMS 타입'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='발송 상태'
    )

    # 수신자 정보
    recipient = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_sms',
        verbose_name='수신자'
    )
    phone_number = models.CharField(
        max_length=15,
        verbose_name='수신 번호'
    )

    # 발신자 정보 (거래 상대방)
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_sms',
        verbose_name='발신 트리거 사용자'
    )

    # 메시지 내용
    message = models.TextField(verbose_name='메시지 내용')
    template_params = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='템플릿 파라미터'
    )

    # 관련 객체 참조 (Generic하게 처리)
    related_model = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='관련 모델'
    )
    related_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='관련 객체 ID'
    )

    # 발송 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='발송 시간')

    # 오류 정보
    error_message = models.TextField(blank=True, verbose_name='오류 메시지')
    retry_count = models.IntegerField(default=0, verbose_name='재시도 횟수')

    # 메타 정보
    is_test = models.BooleanField(default=False, verbose_name='테스트 발송')

    class Meta:
        db_table = 'sms_notifications'
        verbose_name = 'SMS 알림'
        verbose_name_plural = 'SMS 알림'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sms_type', 'status']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_sms_type_display()} - {self.phone_number} ({self.get_status_display()})"

    def mark_as_sent(self):
        """발송 완료 처리"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])

    def mark_as_failed(self, error_message):
        """발송 실패 처리"""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'retry_count'])

    @property
    def can_retry(self):
        """재시도 가능 여부"""
        return self.status == 'failed' and self.retry_count < 3