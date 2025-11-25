"""
상담 질문 플로우 모델
업종별 단계적 질문과 선택지를 정의
"""
from django.db import models


class ConsultationFlow(models.Model):
    """업종별 상담 질문 플로우"""

    category = models.ForeignKey(
        'api.LocalBusinessCategory',
        on_delete=models.CASCADE,
        related_name='consultation_flows',
        verbose_name='업종'
    )

    step_number = models.PositiveIntegerField(
        verbose_name='단계 번호',
        help_text='1부터 시작'
    )

    question = models.CharField(
        max_length=100,
        verbose_name='질문',
        help_text='예: 상담 목적, 사업 형태'
    )

    is_required = models.BooleanField(
        default=True,
        verbose_name='필수 여부'
    )

    # 조건부 표시 (특정 이전 선택지 선택 시에만 표시)
    depends_on_step = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='의존 단계',
        help_text='특정 단계의 선택에 따라 표시'
    )

    depends_on_options = models.JSONField(
        default=list,
        blank=True,
        verbose_name='의존 선택지',
        help_text='해당 선택지가 선택되었을 때만 표시 (option key 목록)'
    )

    order_index = models.IntegerField(
        default=0,
        verbose_name='정렬 순서'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_consultation_flow'
        verbose_name = '상담 질문 플로우'
        verbose_name_plural = '상담 질문 플로우'
        ordering = ['category', 'step_number', 'order_index']
        unique_together = ['category', 'step_number']

    def __str__(self):
        return f"{self.category.name} - Step {self.step_number}: {self.question}"


class ConsultationFlowOption(models.Model):
    """질문별 선택지"""

    flow = models.ForeignKey(
        ConsultationFlow,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='질문 플로우'
    )

    key = models.CharField(
        max_length=50,
        verbose_name='선택지 키',
        help_text='프로그래밍용 키 (영문)'
    )

    label = models.CharField(
        max_length=50,
        verbose_name='선택지 라벨',
        help_text='사용자에게 표시될 텍스트'
    )

    icon = models.CharField(
        max_length=10,
        blank=True,
        default='',
        verbose_name='아이콘'
    )

    description = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='설명',
        help_text='선택지에 대한 추가 설명'
    )

    is_custom_input = models.BooleanField(
        default=False,
        verbose_name='직접 입력 옵션',
        help_text='True면 텍스트 입력창 표시'
    )

    order_index = models.IntegerField(
        default=0,
        verbose_name='정렬 순서'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_consultation_flow_option'
        verbose_name = '상담 선택지'
        verbose_name_plural = '상담 선택지'
        ordering = ['flow', 'order_index']

    def __str__(self):
        return f"{self.flow.question} - {self.label}"
