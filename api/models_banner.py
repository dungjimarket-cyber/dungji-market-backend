from django.db import models
from django.contrib.auth import get_user_model
from .utils.s3_upload import upload_to_s3

User = get_user_model()

class Banner(models.Model):
    """메인 페이지 배너"""
    BANNER_TYPE_CHOICES = [
        ('event', '이벤트'),
        ('notice', '공지사항'),
        ('promotion', '프로모션'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='배너 제목')
    banner_type = models.CharField(max_length=20, choices=BANNER_TYPE_CHOICES, default='event', verbose_name='배너 타입')
    image = models.ImageField(upload_to='banners/', null=True, blank=True, verbose_name='배너 이미지')
    image_url = models.URLField(max_length=500, blank=True, verbose_name='배너 이미지 URL')
    link_url = models.URLField(max_length=500, blank=True, verbose_name='링크 URL', help_text='외부 링크 URL (선택사항)')
    event = models.ForeignKey('Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='banners', verbose_name='연결된 이벤트')
    order = models.IntegerField(default=0, verbose_name='표시 순서', help_text='낮은 숫자가 먼저 표시됩니다')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='시작일')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='종료일')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_banners', verbose_name='생성자')
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = '배너'
        verbose_name_plural = '배너'
    
    def __str__(self):
        return f"{self.title} ({self.get_banner_type_display()})"
    
    def save(self, *args, **kwargs):
        # S3에 이미지 업로드 - 새 이미지가 있으면 무조건 업로드
        if self.image:
            image_url = upload_to_s3(self.image, 'banners')
            if image_url:
                self.image_url = image_url
                self.image = None
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        """현재 시간 기준 유효한 배너인지 확인"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
            
        if self.start_date and now < self.start_date:
            return False
            
        if self.end_date and now > self.end_date:
            return False
            
        return True


class Event(models.Model):
    """이벤트"""
    EVENT_TYPE_CHOICES = [
        ('discount', '할인 이벤트'),
        ('gift', '사은품 이벤트'),
        ('point', '포인트 이벤트'),
        ('special', '특별 이벤트'),
        ('notice', '공지사항'),
    ]
    
    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('scheduled', '예정'),
        ('ongoing', '진행중'),
        ('ended', '종료'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='이벤트 제목')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='슬러그')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='special', verbose_name='이벤트 타입')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='상태')
    thumbnail = models.ImageField(upload_to='events/thumbnails/', null=True, blank=True, verbose_name='썸네일 이미지')
    thumbnail_url = models.URLField(max_length=500, blank=True, verbose_name='썸네일 URL')
    content_image = models.ImageField(upload_to='events/content/', null=True, blank=True, verbose_name='본문 이미지')
    content_image_url = models.URLField(max_length=500, blank=True, verbose_name='본문 이미지 URL')
    content = models.TextField(verbose_name='이벤트 내용', help_text='HTML 사용 가능')
    short_description = models.TextField(max_length=500, blank=True, verbose_name='간단 설명')
    start_date = models.DateTimeField(verbose_name='시작일')
    end_date = models.DateTimeField(verbose_name='종료일')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    view_count = models.IntegerField(default=0, verbose_name='조회수')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_events', verbose_name='생성자')
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = '이벤트'
        verbose_name_plural = '이벤트'
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # S3에 이미지 업로드
        # 썸네일 이미지 처리 - 새 이미지가 있으면 무조건 업로드
        if self.thumbnail:
            thumbnail_url = upload_to_s3(self.thumbnail, 'events/thumbnails')
            if thumbnail_url:
                self.thumbnail_url = thumbnail_url
                self.thumbnail = None
                
        # 본문 이미지 처리 - 새 이미지가 있으면 무조건 업로드        
        if self.content_image:
            content_image_url = upload_to_s3(self.content_image, 'events/content')
            if content_image_url:
                self.content_image_url = content_image_url
                self.content_image = None
                
        # 슬러그 자동 생성
        if not self.slug:
            from django.utils.text import slugify
            import uuid
            base_slug = slugify(self.title, allow_unicode=True)
            if not base_slug:
                base_slug = str(uuid.uuid4())[:8]
            self.slug = base_slug
            
            # 중복 체크
            counter = 1
            while Event.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
                
        # 상태 자동 업데이트
        from django.utils import timezone
        now = timezone.now()
        if self.start_date and self.end_date:
            if now < self.start_date:
                self.status = 'scheduled'
            elif now >= self.start_date and now <= self.end_date:
                self.status = 'ongoing'
            elif now > self.end_date:
                self.status = 'ended'
                
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        """현재 시간 기준 유효한 이벤트인지 확인"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
            
        if now < self.start_date:
            return False
            
        if now > self.end_date:
            return False
            
        return True
    
    def increment_view_count(self):
        """조회수 증가"""
        self.view_count += 1
        self.save(update_fields=['view_count'])