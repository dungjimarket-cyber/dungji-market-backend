from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class NicknameChangeHistory(models.Model):
    """
    닉네임 변경 이력을 관리하는 모델
    30일 동안 2회까지만 변경 가능하도록 제한
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='nickname_changes',
        verbose_name='사용자'
    )
    old_nickname = models.CharField(
        max_length=15,
        verbose_name='이전 닉네임'
    )
    new_nickname = models.CharField(
        max_length=15,
        verbose_name='새 닉네임'
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='변경 일시'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP 주소'
    )
    
    class Meta:
        verbose_name = '닉네임 변경 이력'
        verbose_name_plural = '닉네임 변경 이력'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['user', '-changed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.old_nickname} → {self.new_nickname} ({self.changed_at})"
    
    @classmethod
    def can_change_nickname(cls, user):
        """
        사용자가 닉네임을 변경할 수 있는지 확인
        30일 이내에 2회까지만 변경 가능
        """
        # 30일 전 날짜 계산
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # 최근 30일 이내의 변경 횟수 확인
        recent_changes = cls.objects.filter(
            user=user,
            changed_at__gte=thirty_days_ago
        ).count()
        
        return recent_changes < 2
    
    @classmethod
    def get_remaining_changes(cls, user):
        """
        남은 변경 가능 횟수 반환
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_changes = cls.objects.filter(
            user=user,
            changed_at__gte=thirty_days_ago
        ).count()
        
        return max(0, 2 - recent_changes)
    
    @classmethod
    def get_next_available_date(cls, user):
        """
        다음 변경 가능 날짜 반환
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # 최근 30일 이내의 변경 기록을 날짜 순으로 가져오기
        recent_changes = cls.objects.filter(
            user=user,
            changed_at__gte=thirty_days_ago
        ).order_by('changed_at')
        
        if recent_changes.count() < 2:
            return timezone.now()  # 지금 변경 가능
        
        # 가장 오래된 변경 기록으로부터 30일 후
        oldest_change = recent_changes.first()
        return oldest_change.changed_at + timedelta(days=30)