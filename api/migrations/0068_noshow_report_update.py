# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0067_add_multiple_evidence_images'),
    ]

    operations = [
        # 상태값 변경
        migrations.AlterField(
            model_name='noshowreport',
            name='status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('pending', '처리중'),
                    ('completed', '처리완료'),
                    ('on_hold', '보류중'),
                ],
                default='pending',
                verbose_name='처리 상태'
            ),
        ),
        # 수정 관련 필드 추가
        migrations.AddField(
            model_name='noshowreport',
            name='edit_count',
            field=models.IntegerField(default=0, verbose_name='수정 횟수'),
        ),
        migrations.AddField(
            model_name='noshowreport',
            name='last_edited_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='마지막 수정 시간'),
        ),
        # 노쇼 구매자 목록 필드 추가
        migrations.AddField(
            model_name='noshowreport',
            name='noshow_buyers',
            field=models.JSONField(default=list, blank=True, verbose_name='노쇼 구매자 목록'),
        ),
    ]