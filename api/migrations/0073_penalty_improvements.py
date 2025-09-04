# Generated migration file for Penalty model improvements

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0072_noshow_report_cancellation_fields'),
    ]

    operations = [
        # Add new fields to Penalty model
        migrations.AddField(
            model_name='penalty',
            name='duration_hours',
            field=models.PositiveIntegerField(default=24, help_text='시간 단위로 입력 (예: 24, 48, 72)', verbose_name='패널티 기간(시간)'),
        ),
        migrations.AddField(
            model_name='penalty',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='penalties_created', to=settings.AUTH_USER_MODEL, verbose_name='등록자'),
        ),
        migrations.AddField(
            model_name='penalty',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='등록일'),
            preserve_default=False,
        ),
        
        # Modify existing fields
        migrations.AlterField(
            model_name='penalty',
            name='penalty_type',
            field=models.CharField(help_text='예: 노쇼, 판매포기, 기타', max_length=20, verbose_name='페널티 유형'),
        ),
        migrations.AlterField(
            model_name='penalty',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='종료일'),
        ),
        
        # Update Meta options
        migrations.AlterModelOptions(
            name='penalty',
            options={'ordering': ['-created_at', '-start_date'], 'verbose_name': '노쇼 패널티', 'verbose_name_plural': '노쇼 패널티 관리'},
        ),
        
        # Remove unique constraint if it exists
        migrations.RemoveConstraint(
            model_name='penalty',
            name='unique_penalty',
        ),
    ]