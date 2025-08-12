from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class RemoteSalesCertification(models.Model):
    """비대면 판매 인증 관리 모델"""
    
    STATUS_CHOICES = (
        ('pending', '심사중'),
        ('approved', '승인'),
        ('rejected', '거절'),
        ('expired', '만료'),
    )
    
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='remote_sales_certifications',
        verbose_name='판매자'
    )
    
    # 인증 서류
    certification_file = models.URLField(verbose_name='인증서 파일 URL')
    business_license_file = models.URLField(null=True, blank=True, verbose_name='사업자등록증 URL')
    
    # 상태 관리
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='상태'
    )
    
    # 심사 정보
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='제출일시')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='심사일시')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='승인일시')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='만료일시')
    
    # 심사자 정보
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_certifications',
        verbose_name='심사자'
    )
    
    # 거절 사유
    rejection_reason = models.TextField(blank=True, verbose_name='거절 사유')
    
    # 메모
    admin_notes = models.TextField(blank=True, verbose_name='관리자 메모')
    
    class Meta:
        verbose_name = '비대면 판매 인증'
        verbose_name_plural = '비대면 판매 인증'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['status', 'submitted_at']),
        ]
    
    def __str__(self):
        return f'{self.seller.username} - {self.get_status_display()} ({self.submitted_at.strftime("%Y-%m-%d")})'
    
    def approve(self, user, expires_days=365):
        """인증 승인"""
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.approved_at = timezone.now()
        self.reviewed_by = user
        self.expires_at = timezone.now() + timedelta(days=expires_days)
        self.save()
        
        # 사용자 정보 업데이트
        self.seller.remote_sales_verified = True
        self.seller.remote_sales_verification_date = self.approved_at
        self.seller.remote_sales_expiry_date = self.expires_at
        self.seller.remote_sales_certification = self.certification_file
        self.seller.save()
        
        return True
    
    def reject(self, user, reason):
        """인증 거절"""
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.reviewed_by = user
        self.rejection_reason = reason
        self.save()
        
        # 사용자 정보 업데이트
        self.seller.remote_sales_verified = False
        self.seller.remote_sales_verification_date = None
        self.seller.remote_sales_expiry_date = None
        self.seller.save()
        
        return True
    
    def is_valid(self):
        """유효한 인증인지 확인"""
        if self.status != 'approved':
            return False
        if self.expires_at and self.expires_at < timezone.now():
            self.status = 'expired'
            self.save()
            return False
        return True
    
    @classmethod
    def get_active_certification(cls, seller):
        """활성 인증 가져오기"""
        return cls.objects.filter(
            seller=seller,
            status='approved',
            expires_at__gt=timezone.now()
        ).first()