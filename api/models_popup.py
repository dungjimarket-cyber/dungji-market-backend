"""
팝업 관련 모델
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class Popup(models.Model):
    """팝업 모델"""
    
    POPUP_TYPE_CHOICES = [
        ('image', '이미지'),
        ('text', '텍스트'),
        ('mixed', '이미지 + 텍스트'),
    ]
    
    POSITION_CHOICES = [
        ('center', '중앙'),
        ('top', '상단'),
        ('bottom', '하단'),
        ('custom', '사용자 지정'),
    ]
    
    # 기본 정보
    title = models.CharField(
        max_length=200,
        verbose_name='팝업 제목',
        help_text='관리용 제목'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화',
        help_text='팝업 표시 여부'
    )
    
    priority = models.IntegerField(
        default=0,
        verbose_name='우선순위',
        help_text='높은 숫자가 먼저 표시됨'
    )
    
    # 팝업 타입 및 내용
    popup_type = models.CharField(
        max_length=10,
        choices=POPUP_TYPE_CHOICES,
        default='image',
        verbose_name='팝업 타입',
        help_text='팝업 표시 형식'
    )
    
    content = models.TextField(
        blank=True,
        null=True,
        verbose_name='팝업 내용',
        help_text='텍스트 또는 혼합 타입에서 사용'
    )
    
    image = models.ImageField(
        upload_to='popups/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='팝업 이미지',
        help_text='이미지 또는 혼합 타입에서 사용'
    )
    
    # 링크 설정
    link_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='링크 URL',
        help_text='팝업 클릭 시 이동할 URL'
    )
    
    link_target = models.CharField(
        max_length=10,
        choices=[
            ('_self', '현재 창'),
            ('_blank', '새 창'),
        ],
        default='_blank',
        verbose_name='링크 열기 방식'
    )
    
    # 디스플레이 설정
    position = models.CharField(
        max_length=10,
        choices=POSITION_CHOICES,
        default='center',
        verbose_name='팝업 위치'
    )
    
    position_x = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='X 좌표',
        help_text='사용자 지정 위치의 X 좌표 (픽셀)'
    )
    
    position_y = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Y 좌표',
        help_text='사용자 지정 위치의 Y 좌표 (픽셀)'
    )
    
    width = models.IntegerField(
        default=500,
        validators=[MinValueValidator(200), MaxValueValidator(1200)],
        verbose_name='팝업 너비',
        help_text='팝업 창 최대 너비 (픽셀, 200-1200) - 화면 크기에 따라 자동 조절됨'
    )
    
    height = models.IntegerField(
        default=600,
        validators=[MinValueValidator(200), MaxValueValidator(900)],
        verbose_name='팝업 높이',
        help_text='팝업 창 최대 높이 (픽셀, 200-900) - 이미지는 화면의 70%까지만 표시, 비율 유지됨'
    )
    
    # 표시 조건
    start_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='시작일시',
        help_text='팝업 표시 시작일시'
    )
    
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='종료일시',
        help_text='팝업 표시 종료일시 (비어있으면 계속 표시)'
    )
    
    # 페이지별 표시 설정 (체크박스)
    show_on_main = models.BooleanField(
        default=True,
        verbose_name='메인 페이지',
        help_text='메인 페이지에서 팝업 표시'
    )

    show_on_groupbuy_list = models.BooleanField(
        default=False,
        verbose_name='공구 목록',
        help_text='공구(견적) 목록 페이지에서 표시'
    )

    show_on_groupbuy_detail = models.BooleanField(
        default=False,
        verbose_name='공구 상세',
        help_text='공구(견적) 상세 페이지에서 표시'
    )

    show_on_used_list = models.BooleanField(
        default=False,
        verbose_name='중고거래 목록',
        help_text='중고거래 목록 페이지에서 표시'
    )

    show_on_used_detail = models.BooleanField(
        default=False,
        verbose_name='중고거래 상세',
        help_text='중고거래 상세 페이지에서 표시'
    )

    show_on_mypage = models.BooleanField(
        default=False,
        verbose_name='마이페이지',
        help_text='마이페이지에서 표시'
    )

    show_on_mobile = models.BooleanField(
        default=True,
        verbose_name='모바일 표시',
        help_text='모바일 환경에서 팝업 표시'
    )

    hide_on_twa_app = models.BooleanField(
        default=False,
        verbose_name='웹에서만 표시',
        help_text='Play Store 앱(TWA)에서 팝업을 표시하지 않음 (웹에서만 표시)'
    )

    show_only_on_twa_app = models.BooleanField(
        default=False,
        verbose_name='앱에서만 표시',
        help_text='Play Store 앱(TWA)에서만 팝업을 표시 (웹에서는 숨김)'
    )

    # 사용자 옵션
    show_today_close = models.BooleanField(
        default=True,
        verbose_name='오늘 하루 보지 않기',
        help_text='오늘 하루 보지 않기 옵션 표시'
    )
    
    show_week_close = models.BooleanField(
        default=False,
        verbose_name='일주일 보지 않기',
        help_text='일주일 보지 않기 옵션 표시'
    )
    
    # 페이지별 표시 설정 (DEPRECATED - 체크박스 필드 사용)
    # 마이그레이션 후 제거 예정
    show_pages = models.JSONField(
        default=list,
        blank=True,
        verbose_name='[구버전] 표시할 페이지',
        help_text='(사용하지 마세요) 위의 체크박스를 사용하세요'
    )

    exclude_pages = models.JSONField(
        default=list,
        blank=True,
        verbose_name='[구버전] 제외할 페이지',
        help_text='(사용하지 마세요) 위의 체크박스를 사용하세요'
    )
    
    # 통계
    view_count = models.IntegerField(
        default=0,
        verbose_name='조회수',
        help_text='팝업 표시 횟수'
    )
    
    click_count = models.IntegerField(
        default=0,
        verbose_name='클릭수',
        help_text='팝업 클릭 횟수'
    )
    
    # 메타 정보
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='작성자',
        related_name='popups'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )
    
    class Meta:
        verbose_name = '팝업'
        verbose_name_plural = '팝업 등록'
        ordering = ['-priority', '-created_at']
        
    def __str__(self):
        return f"[{'활성' if self.is_active else '비활성'}] {self.title}"
    
    def is_valid_period(self):
        """현재 시간이 팝업 표시 기간인지 확인"""
        now = timezone.now()
        if self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True
    
    def increment_view_count(self):
        """조회수 증가"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_click_count(self):
        """클릭수 증가"""
        self.click_count += 1
        self.save(update_fields=['click_count'])