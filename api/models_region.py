from django.db import models

class Region(models.Model):
    """
    지역 정보를 저장하는 모델
    법정동 코드 체계를 기반으로 지역 정보를 계층적으로 저장
    """
    LEVEL_CHOICES = (
        (0, '시/도'),
        (1, '시/군/구'),
        (2, '읍/면/동'),
    )
    
    code = models.CharField(max_length=10, primary_key=True, verbose_name='법정동코드')
    name = models.CharField(max_length=100, verbose_name='지역명')
    full_name = models.CharField(max_length=200, verbose_name='전체 지역명')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='children', verbose_name='상위 지역')
    level = models.IntegerField(choices=LEVEL_CHOICES, verbose_name='지역 레벨')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    
    class Meta:
        verbose_name = '지역'
        verbose_name_plural = '지역 목록'
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['parent']),
            models.Index(fields=['level']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.code})"
    
    def get_children(self):
        """하위 지역 목록 반환"""
        return self.children.filter(is_active=True).order_by('code')
    
    def get_ancestors(self):
        """상위 지역 목록 반환 (자신 포함)"""
        ancestors = []
        current = self
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors
