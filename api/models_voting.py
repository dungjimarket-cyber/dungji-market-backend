from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

class BidVote(models.Model):
    """
    입찰에 대한 참여자 투표 모델
    공구 마감 후 12시간 동안 참여자들이 원하는 판매자의 입찰을 선택
    """
    participant = models.ForeignKey('User', on_delete=models.CASCADE, related_name='bid_votes', verbose_name='투표자')
    groupbuy = models.ForeignKey('GroupBuy', on_delete=models.CASCADE, related_name='bid_votes', verbose_name='공구')
    bid = models.ForeignKey('Bid', on_delete=models.CASCADE, related_name='votes', verbose_name='선택한 입찰')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='투표 일시')
    
    class Meta:
        verbose_name = '입찰 투표'
        verbose_name_plural = '입찰 투표 목록'
        unique_together = ('participant', 'groupbuy')  # 한 공구에 한 번만 투표 가능
        
    def __str__(self):
        return f"{self.participant.username} -> {self.bid.seller.username} ({self.groupbuy.title})"
    
    def clean(self):
        """투표 유효성 검증"""
        # 공구 상태가 voting이 아니면 투표 불가
        if self.groupbuy.status != 'voting':
            raise ValidationError('현재 투표 기간이 아닙니다.')
            
        # 투표 마감 시간이 지났으면 투표 불가
        if self.groupbuy.voting_end and timezone.now() > self.groupbuy.voting_end:
            raise ValidationError('투표 시간이 종료되었습니다.')
            
        # 참여자가 아니면 투표 불가
        if not self.groupbuy.participants.filter(id=self.participant.id).exists():
            raise ValidationError('공구 참여자만 투표할 수 있습니다.')
            
        # 선택한 입찰이 해당 공구의 입찰이 아니면 투표 불가
        if self.bid.groupbuy != self.groupbuy:
            raise ValidationError('잘못된 입찰 선택입니다.')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)