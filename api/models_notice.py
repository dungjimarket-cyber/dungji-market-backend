"""
공지사항 모델
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Notice(models.Model):
    """공지사항 모델"""
    
    CATEGORY_CHOICES = [
        ('general', '일반공지'),
        ('event', '이벤트'),
        ('update', '업데이트'),
        ('maintenance', '점검안내'),
        ('important', '중요공지'),
    ]
    
    title = models.CharField(
        max_length=200,
        verbose_name='제목'
    )
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general',
        verbose_name='카테고리'
    )
    
    content = models.TextField(
        verbose_name='내용 (HTML)',
        help_text='HTML 태그를 사용할 수 있습니다.'
    )
    
    summary = models.TextField(
        max_length=500,
        blank=True,
        verbose_name='요약',
        help_text='목록에 표시될 간단한 요약 (선택사항)'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notices',
        verbose_name='작성자'
    )
    
    is_pinned = models.BooleanField(
        default=False,
        verbose_name='상단 고정',
        help_text='상단에 고정할 중요 공지사항'
    )
    
    is_published = models.BooleanField(
        default=True,
        verbose_name='게시 여부'
    )
    
    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name='조회수'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='작성일'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일'
    )
    
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='게시일',
        help_text='미래 날짜를 설정하면 예약 게시됩니다.'
    )
    
    # SEO 필드
    meta_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='메타 제목',
        help_text='SEO를 위한 메타 제목 (비워두면 제목 사용)'
    )
    
    meta_description = models.TextField(
        max_length=500,
        blank=True,
        verbose_name='메타 설명',
        help_text='SEO를 위한 메타 설명'
    )
    
    # 이미지 필드
    thumbnail = models.ImageField(
        upload_to='notices/thumbnails/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='썸네일 이미지'
    )
    
    # 메인 노출 관련 필드
    show_in_main = models.BooleanField(
        default=False,
        verbose_name='메인 화면 노출',
        help_text='메인 화면에 노출할지 여부'
    )
    
    DISPLAY_TYPE_CHOICES = [
        ('banner', '배너 이미지'),
        ('text', '텍스트 공지'),
        ('both', '배너 + 텍스트'),
        ('popup', '팝업'),
    ]
    
    display_type = models.CharField(
        max_length=10,
        choices=DISPLAY_TYPE_CHOICES,
        default='text',
        verbose_name='노출 방식',
        help_text='메인 화면 노출 방식'
    )
    
    main_banner_image = models.ImageField(
        upload_to='notices/banners/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='메인 배너 이미지',
        help_text='메인 화면 배너 이미지 (권장: 1200x400)'
    )
    
    banner_link = models.URLField(
        blank=True,
        null=True,
        verbose_name='배너 클릭 링크',
        help_text='배너 클릭 시 이동할 URL (비워두면 공지사항 상세 페이지로 이동)'
    )
    
    main_display_order = models.IntegerField(
        default=0,
        verbose_name='메인 노출 순서',
        help_text='숫자가 작을수록 먼저 표시 (0이 가장 먼저)'
    )
    
    # 팝업 관련 필드
    POPUP_TYPE_CHOICES = [
        ('text', '텍스트 팝업'),
        ('image', '이미지 팝업'),
        ('mixed', '텍스트 + 이미지'),
    ]
    
    popup_type = models.CharField(
        max_length=10,
        choices=POPUP_TYPE_CHOICES,
        default='text',
        verbose_name='팝업 타입',
        help_text='팝업 표시 형식'
    )
    
    popup_width = models.IntegerField(
        default=500,
        verbose_name='팝업 너비',
        help_text='팝업 창 너비 (픽셀)'
    )
    
    popup_height = models.IntegerField(
        default=600,
        verbose_name='팝업 높이',
        help_text='팝업 창 높이 (픽셀, 이미지 팝업의 경우 자동 조정)'
    )
    
    popup_image = models.ImageField(
        upload_to='notices/popups/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='팝업 이미지',
        help_text='팝업에 표시할 이미지 (이미지/혼합 타입에서 사용)'
    )
    
    popup_link = models.URLField(
        blank=True,
        null=True,
        verbose_name='팝업 클릭 링크',
        help_text='팝업 클릭 시 이동할 URL'
    )
    
    popup_link_target = models.CharField(
        max_length=10,
        choices=[
            ('_self', '현재 창'),
            ('_blank', '새 창'),
        ],
        default='_blank',
        verbose_name='링크 열기 방식',
        help_text='팝업 링크 클릭 시 열기 방식'
    )
    
    popup_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='팝업 종료일시',
        help_text='이 시간 이후에는 팝업이 자동으로 표시되지 않음'
    )
    
    popup_show_today_close = models.BooleanField(
        default=True,
        verbose_name='오늘 하루 보지 않기 표시',
        help_text='오늘 하루 보지 않기 옵션 표시 여부'
    )
    
    class Meta:
        verbose_name = '공지사항'
        verbose_name_plural = '공지사항'
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['-is_pinned', '-created_at']),
            models.Index(fields=['is_published', 'published_at']),
            models.Index(fields=['show_in_main', 'main_display_order']),
        ]
    
    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"
    
    def save(self, *args, **kwargs):
        # 게시 시 published_at 자동 설정
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    
    def increase_view_count(self):
        """조회수 증가"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    @property
    def is_new(self):
        """신규 공지 여부 (7일 이내)"""
        if not self.published_at:
            return False
        return (timezone.now() - self.published_at).days <= 7


class NoticeImage(models.Model):
    """공지사항 이미지 (본문에 삽입용)"""
    
    notice = models.ForeignKey(
        Notice,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='공지사항'
    )
    
    image = models.ImageField(
        upload_to='notices/images/%Y/%m/',
        verbose_name='이미지'
    )
    
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='캡션'
    )
    
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='업로드 일시'
    )
    
    class Meta:
        verbose_name = '공지사항 이미지'
        verbose_name_plural = '공지사항 이미지'
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"{self.notice.title} - 이미지 {self.pk}"


class NoticeComment(models.Model):
    """공지사항 댓글 (선택적 기능)"""
    
    notice = models.ForeignKey(
        Notice,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='공지사항'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notice_comments',
        verbose_name='작성자'
    )
    
    content = models.TextField(
        verbose_name='내용'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 여부'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='작성일'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일'
    )
    
    class Meta:
        verbose_name = '공지사항 댓글'
        verbose_name_plural = '공지사항 댓글'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.author.username} - {self.notice.title[:20]}"