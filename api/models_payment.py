"""
결제 관련 모델
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Payment(models.Model):
    """결제 정보 모델"""
    
    PAYMENT_METHOD_CHOICES = [
        ('inicis', '이니시스'),
        ('kakao', '카카오페이'),
        ('naver', '네이버페이'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('waiting_deposit', '입금대기'),  # 무통장입금 대기
        ('completed', '완료'),
        ('failed', '실패'),
        ('cancelled', '취소'),
        ('refunded', '환불'),
    ]
    
    # 기본 정보
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='사용자'
    )
    order_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='주문번호'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name='결제수단'
    )
    
    # 결제 정보
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name='결제금액'
    )
    product_name = models.CharField(
        max_length=200,
        verbose_name='상품명'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='상태'
    )
    
    # 구매자 정보
    buyer_name = models.CharField(
        max_length=100,
        verbose_name='구매자명',
        blank=True
    )
    buyer_tel = models.CharField(
        max_length=20,
        verbose_name='구매자 전화번호',
        blank=True
    )
    buyer_email = models.EmailField(
        verbose_name='구매자 이메일',
        blank=True
    )
    
    # PG사 정보
    tid = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='거래번호'
    )
    payment_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='결제 데이터'
    )
    
    # 가상계좌 정보 (무통장입금용)
    vbank_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='입금은행명'
    )
    vbank_num = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='입금계좌번호'
    )
    vbank_date = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='입금기한'
    )
    vbank_holder = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='예금주명'
    )
    
    # 취소/환불 정보
    cancel_reason = models.TextField(
        blank=True,
        verbose_name='취소 사유'
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='취소일시'
    )
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name='환불금액'
    )
    
    # 타임스탬프
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='완료일시'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )
    
    class Meta:
        db_table = 'payments'
        verbose_name = '결제'
        verbose_name_plural = '결제 목록'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['order_id']),
            models.Index(fields=['tid']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.product_name} ({self.amount}원)"
    
    @property
    def is_completed(self):
        """결제 완료 여부"""
        return self.status == 'completed'
    
    @property
    def is_refundable(self):
        """환불 가능 여부"""
        # 완료된 결제이고 아직 환불되지 않은 경우
        return self.status == 'completed' and not self.refund_amount