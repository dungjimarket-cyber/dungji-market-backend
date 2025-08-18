from django.db import models
from django.contrib.auth.models import AbstractUser


class Inquiry(models.Model):
    """문의사항 모델"""
    STATUS_CHOICES = [
        ('pending', '답변대기'),
        ('answered', '답변완료'),
    ]
    
    user = models.ForeignKey(
        'User', 
        on_delete=models.CASCADE, 
        verbose_name='작성자'
    )
    title = models.CharField(max_length=200, verbose_name='제목')
    content = models.TextField(verbose_name='문의 내용')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='상태'
    )
    answer = models.TextField(blank=True, null=True, verbose_name='답변 내용')
    answered_at = models.DateTimeField(blank=True, null=True, verbose_name='답변 일시')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성 일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 일시')
    
    class Meta:
        db_table = 'api_inquiry'
        verbose_name = '문의사항'
        verbose_name_plural = '문의사항'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.title} - {self.user.username}'