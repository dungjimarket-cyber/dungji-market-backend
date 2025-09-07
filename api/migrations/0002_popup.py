# Generated manually for Popup model
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import django.utils.timezone
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0075_rename_payment_tables'),
    ]

    operations = [
        migrations.CreateModel(
            name='Popup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='관리용 제목', max_length=200, verbose_name='팝업 제목')),
                ('is_active', models.BooleanField(default=True, help_text='팝업 표시 여부', verbose_name='활성화')),
                ('priority', models.IntegerField(default=0, help_text='높은 숫자가 먼저 표시됨', verbose_name='우선순위')),
                ('popup_type', models.CharField(choices=[('image', '이미지'), ('text', '텍스트'), ('mixed', '이미지 + 텍스트')], default='image', help_text='팝업 표시 형식', max_length=10, verbose_name='팝업 타입')),
                ('content', models.TextField(blank=True, help_text='텍스트 또는 혼합 타입에서 사용', null=True, verbose_name='팝업 내용')),
                ('image', models.ImageField(blank=True, help_text='이미지 또는 혼합 타입에서 사용', null=True, upload_to='popups/%Y/%m/', verbose_name='팝업 이미지')),
                ('link_url', models.URLField(blank=True, help_text='팝업 클릭 시 이동할 URL', null=True, verbose_name='링크 URL')),
                ('link_target', models.CharField(choices=[('_self', '현재 창'), ('_blank', '새 창')], default='_blank', max_length=10, verbose_name='링크 열기 방식')),
                ('position', models.CharField(choices=[('center', '중앙'), ('top', '상단'), ('bottom', '하단'), ('custom', '사용자 지정')], default='center', max_length=10, verbose_name='팝업 위치')),
                ('position_x', models.IntegerField(blank=True, help_text='사용자 지정 위치의 X 좌표 (픽셀)', null=True, verbose_name='X 좌표')),
                ('position_y', models.IntegerField(blank=True, help_text='사용자 지정 위치의 Y 좌표 (픽셀)', null=True, verbose_name='Y 좌표')),
                ('width', models.IntegerField(default=500, help_text='팝업 창 너비 (픽셀, 200-1200)', validators=[django.core.validators.MinValueValidator(200), django.core.validators.MaxValueValidator(1200)], verbose_name='팝업 너비')),
                ('height', models.IntegerField(default=600, help_text='팝업 창 높이 (픽셀, 200-900, 이미지 팝업은 자동 조정)', validators=[django.core.validators.MinValueValidator(200), django.core.validators.MaxValueValidator(900)], verbose_name='팝업 높이')),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now, help_text='팝업 표시 시작일시', verbose_name='시작일시')),
                ('end_date', models.DateTimeField(blank=True, help_text='팝업 표시 종료일시 (비어있으면 계속 표시)', null=True, verbose_name='종료일시')),
                ('show_on_main', models.BooleanField(default=True, help_text='메인 페이지에서 팝업 표시', verbose_name='메인 페이지 표시')),
                ('show_on_mobile', models.BooleanField(default=True, help_text='모바일 환경에서 팝업 표시', verbose_name='모바일 표시')),
                ('show_today_close', models.BooleanField(default=True, help_text='오늘 하루 보지 않기 옵션 표시', verbose_name='오늘 하루 보지 않기')),
                ('show_week_close', models.BooleanField(default=False, help_text='일주일 보지 않기 옵션 표시', verbose_name='일주일 보지 않기')),
                ('show_pages', models.JSONField(blank=True, default=list, help_text='팝업을 표시할 페이지 경로 목록 (비어있으면 모든 페이지)', verbose_name='표시할 페이지')),
                ('exclude_pages', models.JSONField(blank=True, default=list, help_text='팝업을 표시하지 않을 페이지 경로 목록', verbose_name='제외할 페이지')),
                ('view_count', models.IntegerField(default=0, help_text='팝업 표시 횟수', verbose_name='조회수')),
                ('click_count', models.IntegerField(default=0, help_text='팝업 클릭 횟수', verbose_name='클릭수')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='popups', to=settings.AUTH_USER_MODEL, verbose_name='작성자')),
            ],
            options={
                'verbose_name': '팝업',
                'verbose_name_plural': '팝업 등록',
                'ordering': ['-priority', '-created_at'],
            },
        ),
    ]