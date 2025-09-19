# Generated manually for penalty system update

from django.db import migrations, models
from django.db.models import F


def convert_days_to_hours(apps, schema_editor):
    """기존 duration_days를 duration_hours로 변환"""
    UsedPhonePenalty = apps.get_model('used_phones', 'UsedPhonePenalty')
    for penalty in UsedPhonePenalty.objects.all():
        if hasattr(penalty, 'duration_days') and penalty.duration_days:
            penalty.duration_hours = penalty.duration_days * 24
            penalty.save(update_fields=['duration_hours'])


def reverse_convert(apps, schema_editor):
    """롤백 시 duration_hours를 duration_days로 변환"""
    UsedPhonePenalty = apps.get_model('used_phones', 'UsedPhonePenalty')
    for penalty in UsedPhonePenalty.objects.all():
        if hasattr(penalty, 'duration_hours') and penalty.duration_hours:
            penalty.duration_days = penalty.duration_hours // 24
            penalty.save(update_fields=['duration_days'])


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0015_add_minimum_offer_price'),  # 이전 마이그레이션 번호 확인 필요
    ]

    operations = [
        # duration_hours 필드 추가
        migrations.AddField(
            model_name='usedphonepenalty',
            name='duration_hours',
            field=models.IntegerField(
                default=24,  # 기본값 1일
                verbose_name='패널티시간',
                help_text='시간 단위로 입력 (예: 24시간 = 1일, 168시간 = 7일)'
            ),
            preserve_default=False,
        ),

        # 데이터 변환
        migrations.RunPython(convert_days_to_hours, reverse_convert),

        # end_date 필드 제거
        migrations.RemoveField(
            model_name='usedphonepenalty',
            name='end_date',
        ),

        # duration_days 필드 제거
        migrations.RemoveField(
            model_name='usedphonepenalty',
            name='duration_days',
        ),
    ]