# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0089_unifiedbump'),
    ]

    operations = [
        migrations.CreateModel(
            name='NoShowObjection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='이의제기 내용')),
                ('evidence_image_1', models.FileField(blank=True, null=True, upload_to='noshow_objections/%Y/%m/', verbose_name='증빙자료 1')),
                ('evidence_image_2', models.FileField(blank=True, null=True, upload_to='noshow_objections/%Y/%m/', verbose_name='증빙자료 2')),
                ('evidence_image_3', models.FileField(blank=True, null=True, upload_to='noshow_objections/%Y/%m/', verbose_name='증빙자료 3')),
                ('status', models.CharField(choices=[('pending', '처리중'), ('processing', '검토중'), ('resolved', '해결'), ('rejected', '거부')], default='pending', max_length=20, verbose_name='상태')),
                ('admin_comment', models.TextField(blank=True, verbose_name='관리자 답변')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='처리일시')),
                ('noshow_report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='objections', to='api.noshowreport', verbose_name='노쇼 신고')),
                ('objector', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='noshow_objections', to=settings.AUTH_USER_MODEL, verbose_name='이의제기자')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_objections', to=settings.AUTH_USER_MODEL, verbose_name='처리한 관리자')),
            ],
            options={
                'verbose_name': '노쇼 이의제기',
                'verbose_name_plural': '노쇼 이의제기 관리',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='noshowobjection',
            constraint=models.UniqueConstraint(fields=('noshow_report', 'objector'), name='unique_objection_per_report'),
        ),
    ]